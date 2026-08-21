from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from freshness import (
    authorization_branch,
    consumed_marker,
    dispatch_branch,
    execution_key,
    matching_marker,
    positive_candidate_claims,
)


AUTHORIZATION_PATH = "experiments/aerosol-optical-property-sensitivity-v1/authorization.json"
CASE_ARTIFACT_PREFIX = "aops-v1-case-"
GENERIC_CONSUMED = re.compile(r"^ORDINAL([0-9]+)_.+_DISPATCH_CONSUMED$", re.I)
ORDINAL_TOKEN = re.compile(r"ordinal[-_:#]?([0-9]+)", re.I)


class SurfaceRefusal(RuntimeError):
    pass


def request_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def pages(url: str, token: str, list_key: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        sep = "&" if "?" in url else "?"
        value = request_json(f"{url}{sep}per_page=100&page={page}", token)
        rows = value.get(list_key, []) if list_key else value
        if not isinstance(rows, list):
            raise SurfaceRefusal(f"GitHub response missing list: {list_key or 'root'}")
        out.extend(rows)
        if len(rows) < 100:
            return out
        page += 1


def collect(repository: str, token: str) -> dict[str, Any]:
    base = f"https://api.github.com/repos/{repository}"
    issues_and_prs = pages(base + "/issues?state=all", token)
    issues = [row for row in issues_and_prs if "pull_request" not in row]
    return {
        "branches": pages(base + "/branches", token),
        "runs": pages(base + "/actions/runs", token, "workflow_runs"),
        "artifacts": pages(base + "/actions/artifacts", token, "artifacts"),
        "pulls": pages(base + "/pulls?state=all", token),
        "issues": issues,
        "issueComments": pages(base + "/issues/comments", token),
        "pullReviewComments": pages(base + "/pulls/comments", token),
        "commitComments": pages(base + "/comments", token),
        "issue60Comments": pages(base + "/issues/60/comments", token),
    }


def _row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "path", "head_branch", "display_title", "title", "body"):
        value = row.get(key)
        if isinstance(value, str):
            parts.append(value)
    head = row.get("head") or {}
    if isinstance(head, dict) and isinstance(head.get("ref"), str):
        parts.append(head["ref"])
    return "\n".join(parts)


def _related_pr_number(row: dict[str, Any]) -> int | None:
    for key in ("issue_url", "pull_request_url"):
        value = str(row.get(key) or "")
        match = re.search(r"/(?:issues|pulls)/([1-9][0-9]*)$", value)
        if match:
            return int(match.group(1))
    return None


def _ordinals(text: str) -> list[int]:
    return [int(m.group(1)) for m in ORDINAL_TOKEN.finditer(text or "")]


def latest_consumed_or_dispatched_ordinal(
    payload: dict[str, Any],
    *,
    candidate_ordinal: int | None = None,
    candidate_dispatch_branch: str | None = None,
) -> int | None:
    values: list[int] = []
    for row in payload.get("issue60Comments", []):
        body = str(row.get("body") or "").strip()
        match = GENERIC_CONSUMED.fullmatch(body)
        if match:
            value = int(match.group(1))
            if candidate_ordinal is None or value != candidate_ordinal:
                values.append(value)
    for row in payload.get("branches", []):
        name = str(row.get("name") or "")
        if name == candidate_dispatch_branch:
            continue
        if name.startswith("dispatch/"):
            values.extend(x for x in _ordinals(name) if x != candidate_ordinal)
    for row in payload.get("runs", []):
        name = str(row.get("head_branch") or "")
        if name == candidate_dispatch_branch:
            continue
        if name.startswith("dispatch/"):
            values.extend(x for x in _ordinals(name) if x != candidate_ordinal)
    return max(values) if values else None


def _candidate_identity_conflicts(
    payload: dict[str, Any],
    ordinal: int,
    *,
    current_pr: int | None,
    current_run_id: int | None,
    allow_authorization_branch: bool,
    allow_dispatch_branch: bool,
    allow_exact_marker: tuple[str, str, int] | None,
) -> list[str]:
    auth = authorization_branch(ordinal)
    dispatch = dispatch_branch(ordinal)
    allowed_branches = set()
    if allow_authorization_branch:
        allowed_branches.add(auth)
    if allow_dispatch_branch:
        allowed_branches.add(dispatch)
    conflicts: list[str] = []

    for row in payload.get("branches", []):
        name = str(row.get("name") or "")
        if name.startswith(("authorization/", "dispatch/")) and ordinal in _ordinals(name) and name not in allowed_branches:
            conflicts.append(f"branch:{name}")

    for row in payload.get("pulls", []):
        number = int(row.get("number") or 0)
        head = str(((row.get("head") or {}).get("ref") or ""))
        if ordinal not in _ordinals(head) or not head.startswith(("authorization/", "dispatch/")):
            continue
        if current_pr is not None and number == current_pr and head == auth and allow_authorization_branch:
            continue
        if head not in allowed_branches:
            conflicts.append(f"pull:{number}:{head}")

    for row in payload.get("runs", []):
        run_id = int(row.get("id") or 0)
        if current_run_id is not None and run_id == current_run_id:
            continue
        head = str(row.get("head_branch") or "")
        if ordinal not in _ordinals(head) or not head.startswith(("authorization/", "dispatch/")):
            continue
        if head not in allowed_branches:
            conflicts.append(f"run:{run_id}:{head}")

    for row in payload.get("issue60Comments", []):
        body = str(row.get("body") or "").strip()
        marker = re.match(rf"^ORDINAL{ordinal}_.+_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED(?:\s|$)", body, re.I)
        consumed = re.match(rf"^ORDINAL{ordinal}_.+_DISPATCH_CONSUMED$", body, re.I)
        if not marker and not consumed:
            continue
        allowed = False
        if marker and allow_exact_marker is not None:
            head, parent, pr_number = allow_exact_marker
            allowed = matching_marker(body, ordinal, head, parent, pr_number)
        if consumed and allow_dispatch_branch and body.lower() == consumed_marker(ordinal).lower():
            allowed = True
        if not allowed:
            conflicts.append(f"issue60:{row.get('id')}:{body}")
    return sorted(set(conflicts))


def build_surface(
    payload: dict[str, Any],
    ordinal: int,
    *,
    current_pr: int | None = None,
    current_run_id: int | None = None,
    marker_head: str | None = None,
    marker_parent: str | None = None,
    active_authorization_path_on_main_exists: bool = False,
    candidate_code_paths_on_main_inspected: bool = True,
    candidate_seed_authorization_recheck_passed: bool = False,
    allow_authorization_branch: bool = False,
    allow_dispatch_branch: bool = False,
) -> dict[str, Any]:
    auth = authorization_branch(ordinal)
    dispatch = dispatch_branch(ordinal)
    key = execution_key(ordinal)
    branches = payload.get("branches", [])
    runs = payload.get("runs", [])
    artifacts = payload.get("artifacts", [])
    pulls = payload.get("pulls", [])
    issue60 = payload.get("issue60Comments", [])
    branch_by_name = {str(row.get("name") or ""): row for row in branches}
    auth_row = branch_by_name.get(auth)
    dispatch_row = branch_by_name.get(dispatch)
    auth_head = str(((auth_row or {}).get("commit") or {}).get("sha") or "") or None
    dispatch_head = str(((dispatch_row or {}).get("commit") or {}).get("sha") or "") or None

    exact_marker_info = None
    if marker_head and marker_parent and current_pr:
        exact_marker_info = (marker_head, marker_parent, current_pr)
    conflicts = _candidate_identity_conflicts(
        payload,
        ordinal,
        current_pr=current_pr,
        current_run_id=current_run_id,
        allow_authorization_branch=allow_authorization_branch,
        allow_dispatch_branch=allow_dispatch_branch,
        allow_exact_marker=exact_marker_info,
    )

    candidate_runs: list[int] = []
    for run in runs:
        run_id = int(run.get("id") or 0)
        if current_run_id is not None and run_id == current_run_id:
            continue
        if str(run.get("head_branch") or "") == dispatch:
            candidate_runs.append(run_id)

    key_uses: set[tuple[str, str]] = set()
    surfaces = (
        ("branch", branches),
        ("run", runs),
        ("artifact", artifacts),
        ("pull", pulls),
        ("issue", payload.get("issues", [])),
        ("issue-comment", payload.get("issueComments", [])),
        ("pull-review-comment", payload.get("pullReviewComments", [])),
        ("commit-comment", payload.get("commitComments", [])),
        ("issue60-comment", issue60),
    )
    for surface, rows in surfaces:
        for row in rows:
            if surface == "run" and current_run_id is not None and int(row.get("id") or 0) == current_run_id:
                continue
            if surface == "pull" and current_pr is not None and int(row.get("number") or 0) == current_pr:
                continue
            if surface in ("issue-comment", "pull-review-comment") and current_pr is not None and _related_pr_number(row) == current_pr:
                continue
            if key in json.dumps(row, sort_keys=True, ensure_ascii=False):
                identity = str(row.get("id") or row.get("number") or row.get("name") or row.get("url") or "")
                key_uses.add((surface, identity))

    positive: set[str] = set()
    for row in pulls:
        if current_pr is not None and int(row.get("number") or 0) == current_pr:
            continue
        positive.update(positive_candidate_claims(_row_text(row), ordinal))
    issue60_ids = {str(row.get("id") or "") for row in issue60 if row.get("id")}
    for row in payload.get("issues", []):
        positive.update(positive_candidate_claims(_row_text(row), ordinal))
    for row in payload.get("issueComments", []):
        if str(row.get("id") or "") in issue60_ids:
            continue
        if current_pr is not None and _related_pr_number(row) == current_pr:
            continue
        positive.update(positive_candidate_claims(_row_text(row), ordinal))
    for rows in (payload.get("pullReviewComments", []), payload.get("commitComments", [])):
        for row in rows:
            if current_pr is not None and _related_pr_number(row) == current_pr:
                continue
            positive.update(positive_candidate_claims(_row_text(row), ordinal))
    marker_bodies: list[str] = []
    for row in issue60:
        body = str(row.get("body") or "").strip()
        if exact_marker_info and matching_marker(body, ordinal, *exact_marker_info):
            marker_bodies.append(body)
            continue
        if body.lower() == consumed_marker(ordinal).lower() and allow_dispatch_branch:
            continue
        positive.update(positive_candidate_claims(body, ordinal))

    current_consumed = [
        str(row.get("body") or "").strip()
        for row in issue60
        if str(row.get("body") or "").strip().lower() == consumed_marker(ordinal).lower()
    ]
    latest = latest_consumed_or_dispatched_ordinal(
        payload,
        candidate_ordinal=ordinal,
        candidate_dispatch_branch=dispatch,
    )
    if latest is None:
        raise SurfaceRefusal("cannot derive latest prior global scientific ordinal")
    if latest >= ordinal:
        raise SurfaceRefusal("candidate ordinal is not above latest prior consumed/dispatched ordinal")

    case_artifacts = sorted(
        str(row.get("name") or "")
        for row in artifacts
        if str(row.get("name") or "").startswith(CASE_ARTIFACT_PREFIX)
        and not (
            current_run_id is not None
            and int(((row.get("workflow_run") or {}).get("id") or 0)) == current_run_id
        )
    )

    return {
        "latestPriorConsumedScientificOrdinal": latest,
        "nextAvailableScientificOrdinal": ordinal,
        "candidatePriorScientificRunCount": len(candidate_runs),
        "candidatePriorScientificRunIds": sorted(candidate_runs),
        "candidateExecutionKeyPriorUseCount": len(key_uses),
        "candidateExecutionKeyPriorUseRows": sorted(f"{a}:{b}" for a, b in key_uses),
        "positiveCandidateClaimsExcludingCurrent": len(positive) + len(conflicts),
        "positiveCandidateClaimTexts": sorted(positive) + conflicts,
        "authorizationBranchExists": auth_row is not None,
        "authorizationBranchHeadSha": auth_head,
        "authorizationBranchReusableAfterFailedReview": False,
        "dispatchBranchExists": dispatch_row is not None,
        "dispatchBranchHeadSha": dispatch_head,
        "activeAuthorizationPathOnMainExists": active_authorization_path_on_main_exists,
        "matchingAuthorizationMarkers": len(marker_bodies),
        "matchingAuthorizationMarkerBodies": marker_bodies,
        "currentConsumedMarkerCount": len(current_consumed),
        "currentConsumedMarkerBodies": current_consumed,
        "priorCaseArtifactNames": case_artifacts,
        "issue60CommentBodies": [str(row.get("body") or "") for row in issue60],
        "candidateSeedAuthorizationRecheckPassed": candidate_seed_authorization_recheck_passed,
        "allBranchesInspected": True,
        "allActionsRunsInspected": True,
        "allActionsArtifactsInspected": True,
        "allStatePullRequestsInspected": True,
        "allStateIssuesInspected": True,
        "allRepositoryIssueCommentsInspected": True,
        "allRepositoryPullReviewCommentsInspected": True,
        "issue60AndCommentsInspected": True,
        "candidateCodePathsOnMainInspected": candidate_code_paths_on_main_inspected,
    }
