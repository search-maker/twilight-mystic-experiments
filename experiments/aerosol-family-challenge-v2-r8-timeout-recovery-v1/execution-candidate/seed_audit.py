from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

CANDIDATE_SEED = 371960104
STAGE_ID = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
PREREGISTRATION_PR_NUMBER = 286
PREREGISTRATION_PR_HEAD = "002b671089c5a7f27f7d65781ce78e4cb9981150"
DISPATCH_BRANCH_RE = re.compile(r"^dispatch/aerosol-family-challenge-v2-r8-timeout-recovery-v1-ordinal-([1-9][0-9]*)$")
PUBLISHER_WORKFLOW = "aerosol-family-v2-r8-timeout-recovery-v1-dispatch-publisher.yml"
TOKEN_RE = re.compile(r"(?<![0-9_])[0-9_]{7,20}(?![0-9_])")
MUTABLE_KEYS = frozenset({
    "created_at", "updated_at", "started_at", "completed_at", "run_started_at",
    "status", "state", "state_reason", "conclusion", "run_attempt", "merge_commit_sha",
    "expires_at",
})
ALLOWED_TRACKED_PREFIXES = (
    "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/",
    "evidence/aerosol-family-challenge-v2-r8-timeout-recovery-v1/",
)
ALLOWED_TRACKED_EXACT = frozenset({
    "tests/test_aerosol_family_r8_timeout_recovery_v1.py",
    "tests/test_aerosol_family_r8_timeout_recovery_activation_v1.py",
    ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-preauthorization.yml",
    ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-authorization-review.yml",
    ".github/workflows/aerosol-family-v2-r8-timeout-recovery-v1-execution.yml",
})


def request_json(url: str, token: str) -> Any:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def pages(url: str, token: str, list_key: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        sep = "&" if "?" in url else "?"
        value = request_json(f"{url}{sep}per_page=100&page={page}", token)
        current = value.get(list_key, []) if list_key else value
        if not isinstance(current, list):
            raise RuntimeError(f"GitHub response missing list: {list_key or 'root'}")
        rows.extend(current)
        if len(current) < 100:
            return rows
        page += 1


def collect(repository: str, token: str) -> dict[str, list[dict[str, Any]]]:
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


def verify_dispatch_publisher(repository: str, token: str, expected_branch: str, expected_head: str, current_run_id: int | None) -> dict[str, Any] | None:
    match = DISPATCH_BRANCH_RE.fullmatch(expected_branch)
    if match is None:
        return None
    if current_run_id is None:
        raise RuntimeError("dispatch-head audit requires current science run id")
    ordinal = int(match.group(1))
    if ordinal <= 34:
        raise RuntimeError("dispatch-head audit refuses consumed/nonfresh ordinal")
    request_branch = f"status/aerosol-family-v2-r8-timeout-recovery-v1-dispatch-publisher-ordinal-{ordinal}"
    base = f"https://api.github.com/repos/{repository}"
    publisher: dict[str, Any] | None = None
    request_head = ""
    for _ in range(150):
        branches = pages(base + "/branches", token)
        request_rows = [row for row in branches if str(row.get("name") or "") == request_branch]
        if len(request_rows) > 1:
            raise RuntimeError("duplicate publisher request branch identity")
        if len(request_rows) == 1:
            request_head = str(((request_rows[0].get("commit") or {}).get("sha") or ""))
            runs = pages(base + f"/actions/workflows/{PUBLISHER_WORKFLOW}/runs?branch={request_branch}&event=push", token, "workflow_runs")
            same = [row for row in runs if row.get("head_branch") == request_branch and row.get("head_sha") == request_head]
            if len(same) > 1:
                raise RuntimeError("publisher request identity has multiple workflow runs")
            if len(same) == 1:
                row = same[0]
                attempt = int(row.get("run_attempt") or 0)
                if attempt != 1:
                    raise RuntimeError("publisher request identity was rerun")
                if row.get("status") == "completed":
                    if row.get("conclusion") != "success":
                        raise RuntimeError(f"publisher run terminal non-success: {row.get('conclusion')}")
                    publisher = row
                    break
        time.sleep(2)
    if publisher is None:
        raise RuntimeError("timed out waiting for exact successful publisher before scientific preflight")
    publisher_run_id = int(publisher.get("id") or 0)
    artifacts = pages(base + f"/actions/runs/{publisher_run_id}/artifacts", token, "artifacts")
    expected_name = f"afc2-r8-timeout-recovery-v1-dispatch-publisher-ordinal-{ordinal}"
    good = [row for row in artifacts if row.get("name") == expected_name and not row.get("expired", False)]
    if len(good) != 1:
        raise RuntimeError(f"exact successful publisher artifact required once, got {len(good)}")
    if int(((good[0].get("workflow_run") or {}).get("id") or 0)) != publisher_run_id:
        raise RuntimeError("publisher artifact run binding drift")
    return {
        "dispatchPublisherVerified": True,
        "dispatchPublisherRequestBranch": request_branch,
        "dispatchPublisherRequestHead": request_head,
        "dispatchPublisherRunId": publisher_run_id,
        "dispatchPublisherRunAttempt": 1,
        "dispatchPublisherArtifactId": int(good[0].get("id") or 0),
        "dispatchPublisherArtifactName": expected_name,
        "dispatchPublisherArtifactDigest": good[0].get("digest"),
        "scienceRunIdObservedByAudit": current_run_id,
        "scienceAuthorizationHead": expected_head,
    }


def contains_candidate(value: Any) -> bool:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    for token in TOKEN_RE.findall(text):
        normalized = token.replace("_", "")
        if normalized.isdigit() and int(normalized) == CANDIDATE_SEED:
            return True
    return False


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items()) if k not in MUTABLE_KEYS}
    if isinstance(value, list):
        vals = [canonical(v) for v in value]
        return sorted(vals, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return value


def filtered_context(context: dict[str, list[dict[str, Any]]], current_run_id: int | None) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for key, rows in context.items():
        kept: list[dict[str, Any]] = []
        for row in rows:
            if current_run_id and key == "runs" and int(row.get("id") or 0) == current_run_id:
                continue
            if current_run_id and key == "artifacts" and int(((row.get("workflow_run") or {}).get("id") or 0)) == current_run_id:
                continue
            kept.append(row)
        out[key] = kept
    return out


def context_sha(context: dict[str, list[dict[str, Any]]], current_run_id: int | None) -> str:
    data = canonical(filtered_context(context, current_run_id))
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def allowed_preregistration_pull(row: dict[str, Any]) -> bool:
    return (
        int(row.get("number") or 0) == PREREGISTRATION_PR_NUMBER
        and str(((row.get("head") or {}).get("sha") or "")) == PREREGISTRATION_PR_HEAD
        and str(row.get("title") or "") == "Preregister AFC2 R8 targeted timeout recovery v1"
    )


def metadata_collisions(context: dict[str, list[dict[str, Any]]], current_run_id: int | None) -> list[dict[str, Any]]:
    filtered = filtered_context(context, current_run_id)
    collisions: list[dict[str, Any]] = []
    for surface, rows in filtered.items():
        for row in rows:
            if surface == "pulls" and allowed_preregistration_pull(row):
                continue
            if contains_candidate(canonical(row)):
                collisions.append({
                    "surface": surface,
                    "id": str(row.get("id") or row.get("number") or row.get("name") or row.get("url") or ""),
                })
    return collisions


def tracked_collisions(repo_root: Path) -> list[str]:
    import subprocess
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo_root)
    collisions: list[str] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        rel = item.decode("utf-8")
        path = repo_root / rel
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if not contains_candidate(text):
            continue
        if rel in ALLOWED_TRACKED_EXACT or any(rel.startswith(prefix) for prefix in ALLOWED_TRACKED_PREFIXES):
            continue
        collisions.append(rel)
    return sorted(collisions)


def ordinal_observations(context: dict[str, list[dict[str, Any]]], *, ignore_branch: str | None = None, ignore_pr: int | None = None, current_run_id: int | None = None) -> list[dict[str, Any]]:
    pattern = re.compile(r"ordinal[-_:# ]*([1-9][0-9]*)", re.I)
    rows: list[dict[str, Any]] = []
    def add(surface: str, identity: str, text: str) -> None:
        for match in pattern.finditer(text):
            rows.append({"surface": surface, "id": identity, "ordinal": int(match.group(1))})
    for row in context.get("branches", []):
        name = str(row.get("name") or "")
        if name == ignore_branch:
            continue
        if name.startswith(("authorization/", "dispatch/")):
            add("branch", name, name)
    for row in context.get("runs", []):
        if current_run_id and int(row.get("id") or 0) == current_run_id:
            continue
        head = str(row.get("head_branch") or "")
        if head == ignore_branch:
            continue
        if head.startswith(("authorization/", "dispatch/")):
            add("run", str(row.get("id") or ""), head)
    for row in context.get("pulls", []):
        if ignore_pr and int(row.get("number") or 0) == ignore_pr:
            continue
        head = str(((row.get("head") or {}).get("ref") or ""))
        if head == ignore_branch:
            continue
        if head.startswith(("authorization/", "dispatch/")):
            add("pull", str(row.get("number") or ""), head)
    exact_marker = re.compile(r"^ORDINAL([1-9][0-9]*)_.+(?:AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED|AUTHORIZATION_RETIRED_UNDISPATCHED|DISPATCH_CONSUMED)(?:\s|$)", re.I)
    for row in context.get("issue60Comments", []):
        body = str(row.get("body") or "").strip()
        match = exact_marker.match(body)
        if match:
            rows.append({"surface": "issue60-marker", "id": str(row.get("id") or ""), "ordinal": int(match.group(1))})
    return rows


def audit(repository: str, token: str, repo_root: Path, expected_branch: str, expected_head: str, current_run_id: int | None = None, *, ignore_branch_for_ordinal: str | None = None, ignore_pr_for_ordinal: int | None = None) -> dict[str, Any]:
    publisher = verify_dispatch_publisher(repository, token, expected_branch, expected_head, current_run_id)
    first = collect(repository, token)
    second = collect(repository, token)
    first_sha = context_sha(first, current_run_id)
    second_sha = context_sha(second, current_run_id)
    if first_sha != second_sha:
        raise RuntimeError("repository-global collision surface changed between complete enumerations")
    branches = [row for row in second["branches"] if str(row.get("name") or "") == expected_branch]
    if len(branches) != 1 or str(((branches[0].get("commit") or {}).get("sha") or "")) != expected_head:
        raise RuntimeError("audited branch does not point to exact expected head")
    meta = metadata_collisions(second, current_run_id)
    tracked = tracked_collisions(repo_root)
    if meta or tracked:
        raise RuntimeError(f"candidate seed collision: metadata={meta} tracked={tracked}")
    observations = ordinal_observations(second, ignore_branch=ignore_branch_for_ordinal, ignore_pr=ignore_pr_for_ordinal, current_run_id=current_run_id)
    max_ordinal = max((int(row["ordinal"]) for row in observations), default=0)
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID + "-seed-and-global-identity-audit",
        "status": "PASS_STABLE_DOUBLE_ENUMERATION_NO_EXTERNAL_SEED_COLLISION",
        "candidateSeed": CANDIDATE_SEED,
        "repository": repository,
        "auditedBranch": expected_branch,
        "auditedHead": expected_head,
        "currentRunIdExcluded": current_run_id,
        "stableCollisionContextSha256": second_sha,
        "externalMetadataCollisionCount": 0,
        "trackedTreeExternalCollisionCount": 0,
        "preregistrationSelfEvidencePrNumber": PREREGISTRATION_PR_NUMBER,
        "preregistrationSelfEvidencePrHead": PREREGISTRATION_PR_HEAD,
        "globalOrdinalMaxObservedExcludingCurrentCandidate": max_ordinal,
        "nextGlobalOrdinal": max_ordinal + 1,
        "ordinalObservations": observations,
        "dispatchPublisherVerified": publisher is not None,
    }
    if publisher is not None:
        result["dispatchPublisherEvidence"] = publisher
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--current-run-id", type=int)
    parser.add_argument("--ignore-branch-for-ordinal")
    parser.add_argument("--ignore-pr-for-ordinal", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    result = audit(args.repository, token, args.repository_root, args.expected_branch, args.expected_head, args.current_run_id, ignore_branch_for_ordinal=args.ignore_branch_for_ordinal, ignore_pr_for_ordinal=args.ignore_pr_for_ordinal)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "nextGlobalOrdinal": result["nextGlobalOrdinal"], "auditedHead": result["auditedHead"], "dispatchPublisherVerified": result["dispatchPublisherVerified"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
