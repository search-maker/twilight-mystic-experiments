from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from freshness import (
    authorization_branch,
    dispatch_branch,
    execution_key,
    matching_marker,
    positive_candidate_claims,
)

ORDINAL_RE = re.compile(r"ordinal[-_]?([0-9]+)", re.I)
CASE_ARTIFACT_PREFIX = "aerosol-family-v2-r7-case-"
AUTHORIZATION_PATH = "experiments/aerosol-family-challenge-v2-r7/authorization.json"
AUTHORIZATION_REVIEW_WORKFLOW = ".github/workflows/aerosol-family-v2-r7-authorization-review.yml"
REQUIRED_MAIN_PATHS = (
    "experiments/aerosol-family-challenge-v2-r7/execution-candidate/authorization_guard.py",
    "experiments/aerosol-family-challenge-v2-r7/execution-candidate/dispatch_guard.py",
    "experiments/aerosol-family-challenge-v2-r7/execution-candidate/freshness.py",
    "experiments/aerosol-family-challenge-v2-r7/execution-candidate/guard.py",
    "experiments/aerosol-family-challenge-v2-r7/execution-candidate/executor.py",
    "experiments/aerosol-family-challenge-v2-r7/execution-candidate/transport-contract.v3.json",
    "experiments/aerosol-family-challenge-v2-r7/repository_global_seed_scan.py",
    "experiments/aerosol-family-challenge-v2-r7/tracked_tree_seed_scan.py",
    "experiments/aerosol-family-challenge-v2-r7/merge_seed_proof.py",
    ".github/workflows/aerosol-family-v2-r7-authorization-review.yml",
    ".github/workflows/aerosol-family-v2-r7-execution.yml",
)


class SurfaceRefusal(RuntimeError):
    pass


def _request_json(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def _pages(url: str, token: str, list_key: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        sep = "&" if "?" in url else "?"
        value = _request_json(f"{url}{sep}per_page=100&page={page}", token)
        current = value.get(list_key, []) if list_key else value
        if not isinstance(current, list):
            raise SurfaceRefusal(f"GitHub response missing list: {list_key or 'root'}")
        rows.extend(current)
        if len(current) < 100:
            return rows
        page += 1


def _exists(url: str, token: str) -> bool:
    try:
        _request_json(url, token)
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def collect(repository: str, token: str) -> dict[str, Any]:
    base = f"https://api.github.com/repos/{repository}"
    issues_and_prs = _pages(base + "/issues?state=all", token)
    issues = [row for row in issues_and_prs if "pull_request" not in row]
    return {
        "branches": _pages(base + "/branches", token),
        "runs": _pages(base + "/actions/runs", token, "workflow_runs"),
        "artifacts": _pages(base + "/actions/artifacts", token, "artifacts"),
        "pulls": _pages(base + "/pulls?state=all", token),
        "issues": issues,
        "issueComments": _pages(base + "/issues/comments", token),
        "pullReviewComments": _pages(base + "/pulls/comments", token),
        "commitComments": _pages(base + "/comments", token),
        "issue60Comments": _pages(base + "/issues/60/comments", token),
    }


def _row_text(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "path", "head_branch", "display_title", "title", "body"):
        value = row.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def _ordinal_from_text(text: str) -> list[int]:
    return [int(m.group(1)) for m in ORDINAL_RE.finditer(text or "")]


def _latest_consumed_ordinal(payload: dict[str, Any], candidate_dispatch: str) -> int | None:
    values: list[int] = []
    for branch in payload.get("branches", []):
        name = str(branch.get("name") or "")
        if name == candidate_dispatch:
            continue
        if name.startswith("dispatch/"):
            values.extend(_ordinal_from_text(name))
    for run in payload.get("runs", []):
        name = str(run.get("head_branch") or "")
        if name == candidate_dispatch:
            continue
        if name.startswith("dispatch/"):
            values.extend(_ordinal_from_text(name))
    consumed = re.compile(r"^ORDINAL([0-9]+)_.+_DISPATCH_CONSUMED$", re.I)
    for comment in payload.get("issue60Comments", []):
        line = str(comment.get("body") or "").strip()
        match = consumed.fullmatch(line)
        if match:
            values.append(int(match.group(1)))
    return max(values) if values else None


def _failed_authorization_ref_reusable(
    auth_branch_name: str,
    auth_head: str | None,
    pulls: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> bool:
    """Return true only for one closed/unmerged authorization PR with one failed attempt-1 review.

    This permits the named authorization ref to advance to a fresh direct-child authorization
    commit after its failed head has been preserved separately. It never makes the failed head,
    review run, or scientific identity reusable.
    """
    if not auth_head:
        return False

    matching_prs: list[dict[str, Any]] = []
    for pr in pulls:
        head = pr.get("head") or {}
        if head.get("ref") == auth_branch_name and head.get("sha") == auth_head:
            matching_prs.append(pr)
    closed_unmerged = [
        pr for pr in matching_prs
        if pr.get("state") == "closed" and pr.get("merged_at") is None
    ]
    if len(closed_unmerged) != 1 or any(pr.get("state") == "open" for pr in matching_prs):
        return False

    review_runs = [
        run for run in runs
        if (run.get("head_branch") or "") == auth_branch_name
        and (run.get("head_sha") or "") == auth_head
        and (run.get("path") or "") == AUTHORIZATION_REVIEW_WORKFLOW
        and (run.get("event") or "") == "pull_request"
    ]
    if len(review_runs) != 1:
        return False
    review = review_runs[0]
    return (
        int(review.get("run_attempt") or 0) == 1
        and review.get("status") == "completed"
        and review.get("conclusion") == "failure"
    )


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
) -> dict[str, Any]:
    auth_branch = authorization_branch(ordinal)
    dispatch = dispatch_branch(ordinal)
    key = execution_key(ordinal)

    branches = payload.get("branches", [])
    runs = payload.get("runs", [])
    artifacts = payload.get("artifacts", [])
    pulls = payload.get("pulls", [])
    issues = payload.get("issues", [])
    issue_comments = payload.get("issueComments", [])
    review_comments = payload.get("pullReviewComments", [])
    commit_comments = payload.get("commitComments", [])
    issue60_comments = payload.get("issue60Comments", [])

    branch_by_name = {str(row.get("name") or ""): row for row in branches}
    auth_row = branch_by_name.get(auth_branch)
    dispatch_row = branch_by_name.get(dispatch)
    auth_head = str(((auth_row or {}).get("commit") or {}).get("sha") or "") or None
    dispatch_head = str(((dispatch_row or {}).get("commit") or {}).get("sha") or "") or None

    candidate_runs: list[int] = []
    for run in runs:
        run_id = int(run.get("id") or 0)
        if current_run_id is not None and run_id == int(current_run_id):
            continue
        text = json.dumps(run, sort_keys=True, ensure_ascii=False)
        if str(run.get("head_branch") or "") == dispatch or key in text:
            candidate_runs.append(run_id)

    key_use_rows: set[tuple[str, str]] = set()
    surfaces = (
        ("branch", branches),
        ("run", runs),
        ("artifact", artifacts),
        ("pull", pulls),
        ("issue", issues),
        ("issue-comment", issue_comments),
        ("pull-review-comment", review_comments),
        ("commit-comment", commit_comments),
        ("issue60-comment", issue60_comments),
    )
    for surface, rows in surfaces:
        for row in rows:
            if surface == "run" and current_run_id is not None and int(row.get("id") or 0) == int(current_run_id):
                continue
            if surface == "pull" and current_pr is not None and int(row.get("number") or 0) == int(current_pr):
                continue
            if key in json.dumps(row, sort_keys=True, ensure_ascii=False):
                identity = str(row.get("id") or row.get("number") or row.get("name") or row.get("url") or "")
                key_use_rows.add((surface, identity))

    positive: set[str] = set()
    for row in pulls:
        if current_pr is not None and int(row.get("number") or 0) == int(current_pr):
            continue
        positive.update(positive_candidate_claims(_row_text(row), ordinal))

    issue60_comment_ids = {
        str(row.get("id") or "")
        for row in issue60_comments
        if row.get("id")
    }
    for row in issues:
        positive.update(positive_candidate_claims(_row_text(row), ordinal))
    for row in issue_comments:
        if str(row.get("id") or "") in issue60_comment_ids:
            continue
        positive.update(positive_candidate_claims(_row_text(row), ordinal))
    for rows in (review_comments, commit_comments):
        for row in rows:
            positive.update(positive_candidate_claims(_row_text(row), ordinal))
    for row in issue60_comments:
        body = str(row.get("body") or "")
        if marker_head and marker_parent and current_pr and matching_marker(body, ordinal, marker_head, marker_parent, current_pr):
            continue
        positive.update(positive_candidate_claims(body, ordinal))

    marker_bodies: list[str] = []
    if marker_head and marker_parent and current_pr:
        for row in issue60_comments:
            body = str(row.get("body") or "").strip()
            if matching_marker(body, ordinal, marker_head, marker_parent, current_pr):
                marker_bodies.append(body)

    latest = _latest_consumed_ordinal(payload, dispatch)
    case_artifact_names = sorted(
        str(row.get("name") or "")
        for row in artifacts
        if str(row.get("name") or "").startswith(CASE_ARTIFACT_PREFIX)
        and not (
            current_run_id is not None
            and int(((row.get("workflow_run") or {}).get("id") or 0)) == int(current_run_id)
        )
    )

    return {
        "latestPriorConsumedScientificOrdinal": latest,
        "nextAvailableScientificOrdinal": None if latest is None else latest + 1,
        "candidatePriorScientificRunCount": len(candidate_runs),
        "candidatePriorScientificRunIds": sorted(candidate_runs),
        "candidateExecutionKeyPriorUseCount": len(key_use_rows),
        "candidateExecutionKeyPriorUseRows": sorted(f"{a}:{b}" for a, b in key_use_rows),
        "positiveCandidateClaimsExcludingCurrent": len(positive),
        "positiveCandidateClaimTexts": sorted(positive),
        "authorizationBranchExists": auth_row is not None,
        "authorizationBranchHeadSha": auth_head,
        "authorizationBranchReusableAfterFailedReview": _failed_authorization_ref_reusable(
            auth_branch, auth_head, pulls, runs
        ),
        "dispatchBranchExists": dispatch_row is not None,
        "dispatchBranchHeadSha": dispatch_head,
        "activeAuthorizationPathOnMainExists": active_authorization_path_on_main_exists,
        "matchingAuthorizationMarkers": len(marker_bodies),
        "matchingAuthorizationMarkerBodies": marker_bodies,
        "priorCaseArtifactNames": case_artifact_names,
        "issue60CommentBodies": [str(row.get("body") or "") for row in issue60_comments],
        "allBranchesInspected": True,
        "allActionsRunsInspected": True,
        "allActionsArtifactsInspected": True,
        "allStatePullRequestsInspected": True,
        "allStateIssuesInspected": True,
        "allRepositoryIssueCommentsInspected": True,
        "allRepositoryPullReviewCommentsInspected": True,
        "allRepositoryCommitCommentsInspected": True,
        "issue60AndCommentsInspected": True,
        "candidateCodePathsOnMainInspected": candidate_code_paths_on_main_inspected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--current-pr", type=int)
    parser.add_argument("--current-run-id", type=int)
    parser.add_argument("--marker-head")
    parser.add_argument("--marker-parent")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    authorization = json.loads(args.authorization.read_text())
    ordinal = authorization.get("scientificOrdinal")
    if not isinstance(ordinal, int) or ordinal <= 0:
        raise SystemExit("authorization scientificOrdinal invalid")

    payload = collect(args.repository, token)
    base = f"https://api.github.com/repos/{args.repository}"
    active_exists = _exists(
        base + "/contents/" + urllib.parse.quote(AUTHORIZATION_PATH, safe="/") + "?ref=main",
        token,
    )
    required_ok = all(
        _exists(base + "/contents/" + urllib.parse.quote(path, safe="/") + "?ref=main", token)
        for path in REQUIRED_MAIN_PATHS
    )
    out = build_surface(
        payload,
        ordinal,
        current_pr=args.current_pr,
        current_run_id=args.current_run_id,
        marker_head=args.marker_head,
        marker_parent=args.marker_parent,
        active_authorization_path_on_main_exists=active_exists,
        candidate_code_paths_on_main_inspected=required_ok,
    )
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
