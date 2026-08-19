from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')
REVIEW_PROOF_ARTIFACT_NAME = 'aerosol-family-v2-r6-freeze-proof'
AUDIT_MODES = {'review-freeze', 'authorization-recheck'}
SURFACE_KEYS = (
    'branches', 'runs', 'artifacts', 'pulls', 'issues',
    'issueComments', 'pullReviewComments', 'commitComments', 'issue60Comments',
)
SNAPSHOT_ID_SURFACES = tuple(key for key in SURFACE_KEYS if key != 'branches')

# These fields describe the observation/transport lifecycle rather than the
# collision surface. They are intentionally removed recursively before the
# two-pass fingerprint so a run changing from queued to completed (or a
# timestamp advancing while pagination is in flight) does not create a false
# instability. All identifiers, names, hashes, bodies and other content are
# retained because any of them can carry candidate-seed evidence.
MUTABLE_OPERATIONAL_KEYS = frozenset({
    'created_at', 'updated_at', 'started_at', 'completed_at',
    'run_started_at', 'run_completed_at', 'cancelled_at', 'expires_at',
    'status', 'state', 'state_reason', 'conclusion', 'run_attempt',
})


def req_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def pages(url: str, token: str, list_key: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    while True:
        sep = '&' if '?' in url else '?'
        data = req_json(f'{url}{sep}per_page=100&page={page}', token)
        rows = data.get(list_key, []) if list_key else data
        if not isinstance(rows, list):
            raise RuntimeError(f'GitHub response missing list: {list_key or "root"}')
        out.extend(rows)
        if len(rows) < 100:
            return out
        page += 1


def seed_literals(value: Any, candidates: set[int]) -> list[int]:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False) if not isinstance(value, str) else value
    hits: set[int] = set()
    for token in TOKEN_RE.findall(text):
        normalized = token.replace('_', '')
        if normalized.isdigit() and int(normalized) in candidates:
            hits.add(int(normalized))
    return sorted(hits)


def _without_current_audit_self_metadata(context: dict[str, Any], current_run_id: int | None) -> dict[str, Any]:
    """Return the collision universe with only this audit run's own Actions metadata removed.

    The current audit run necessarily appears while it is enumerating repository-global metadata.
    Its own run row and any artifact metadata emitted by that same run are self-evidence, not
    historical seed-use evidence. No other row is excluded.
    """
    out: dict[str, Any] = {}
    for key in SURFACE_KEYS:
        rows = context.get(key)
        if not isinstance(rows, list):
            raise ValueError(f'repository-global context requires {key} array')
        kept = []
        for row in rows:
            if current_run_id is not None and key == 'runs' and int(row.get('id') or 0) == current_run_id:
                continue
            if current_run_id is not None and key == 'artifacts':
                wr = row.get('workflow_run') or {}
                if int(wr.get('id') or 0) == current_run_id:
                    continue
            kept.append(row)
        out[key] = kept
    return out


def _canonical_collision_value(value: Any, key: str | None = None) -> Any:
    """Canonicalize collision-relevant GitHub data, ignoring only lifecycle noise."""
    if isinstance(value, dict):
        return {
            name: _canonical_collision_value(value[name], name)
            for name in sorted(value)
            if name not in MUTABLE_OPERATIONAL_KEYS
        }
    if isinstance(value, list):
        normalized = [_canonical_collision_value(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False),
        )
    return value


def _numeric_row_id(row: dict[str, Any], surface_key: str) -> int:
    try:
        value = int(row.get('id') or 0)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f'{surface_key} row lacks a numeric id required for snapshot fencing') from exc
    if value <= 0:
        raise RuntimeError(f'{surface_key} row lacks a positive id required for snapshot fencing')
    return value


def _dedupe_rows_by_id(rows: list[dict[str, Any]], surface_key: str) -> list[dict[str, Any]]:
    """Collapse pagination duplicates while refusing conflicting content for one stable row id."""
    by_id: dict[int, dict[str, Any]] = {}
    canonical_by_id: dict[int, Any] = {}
    for row in rows:
        row_id = _numeric_row_id(row, surface_key)
        canonical = _canonical_collision_value(row)
        if row_id in canonical_by_id and canonical_by_id[row_id] != canonical:
            raise RuntimeError(f'{surface_key} row {row_id} changed within one complete enumeration')
        by_id[row_id] = row
        canonical_by_id[row_id] = canonical
    return [by_id[row_id] for row_id in sorted(by_id)]


def _dedupe_branches(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    canonical_by_name: dict[str, Any] = {}
    for row in rows:
        name = str(row.get('name') or '')
        if not name:
            raise RuntimeError('branch row lacks a stable name required for snapshot fencing')
        canonical = _canonical_collision_value(row)
        if name in canonical_by_name and canonical_by_name[name] != canonical:
            raise RuntimeError(f'branch {name} changed within one complete enumeration')
        by_name[name] = row
        canonical_by_name[name] = canonical
    return [by_name[name] for name in sorted(by_name)]


def build_snapshot_fence(context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    """Fence the exact first-enumeration universe while allowing later harmless append-only churn.

    Branches are fenced by the complete first-pass branch-name set. Other GitHub surfaces are
    fenced by their first-pass high-water numeric row id. The current audit run's own Actions
    row/artifacts are removed before the fence is constructed.
    """
    filtered = _without_current_audit_self_metadata(context, current_run_id)
    branch_names = [str(row.get('name') or '') for row in _dedupe_branches(filtered['branches'])]
    max_ids: dict[str, int] = {}
    for key in SNAPSHOT_ID_SURFACES:
        rows = _dedupe_rows_by_id(filtered[key], key)
        max_ids[key] = max((_numeric_row_id(row, key) for row in rows), default=0)
    return {
        'mode': 'FIRST_COMPLETE_ENUMERATION_HIGH_WATER_V1',
        'branchNames': branch_names,
        'maxIds': max_ids,
    }


def apply_snapshot_fence(
    context: dict[str, Any],
    fence: dict[str, Any],
    current_run_id: int | None = None,
) -> dict[str, Any]:
    """Return only rows belonging to the first-pass snapshot fence.

    Rows created after the fence are ignored for stability only. Existing fenced rows must remain
    present and byte-semantically stable after lifecycle normalization, so edits/deletions and
    branch-head movement still fail the two-pass comparison.
    """
    filtered = _without_current_audit_self_metadata(context, current_run_id)
    expected_branches = {str(name) for name in fence.get('branchNames', [])}
    branches = _dedupe_branches(filtered['branches'])
    branch_map = {str(row.get('name') or ''): row for row in branches}
    missing = sorted(expected_branches - set(branch_map))
    if missing:
        raise RuntimeError(f'snapshot-fenced branches disappeared during audit: {missing}')

    out: dict[str, Any] = {
        'branches': [branch_map[name] for name in sorted(expected_branches)],
    }
    max_ids = fence.get('maxIds')
    if not isinstance(max_ids, dict):
        raise ValueError('snapshot fence requires maxIds object')
    for key in SNAPSHOT_ID_SURFACES:
        high_water = int(max_ids.get(key, 0) or 0)
        rows = _dedupe_rows_by_id(filtered[key], key)
        out[key] = [row for row in rows if _numeric_row_id(row, key) <= high_water]
    return out


def post_fence_rows(
    context: dict[str, Any],
    fence: dict[str, Any],
    current_run_id: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return rows that arrived after the first-pass snapshot fence."""
    filtered = _without_current_audit_self_metadata(context, current_run_id)
    expected_branches = {str(name) for name in fence.get('branchNames', [])}
    branches = _dedupe_branches(filtered['branches'])
    out: dict[str, list[dict[str, Any]]] = {
        'branches': [row for row in branches if str(row.get('name') or '') not in expected_branches],
    }
    max_ids = fence.get('maxIds')
    if not isinstance(max_ids, dict):
        raise ValueError('snapshot fence requires maxIds object')
    for key in SNAPSHOT_ID_SURFACES:
        high_water = int(max_ids.get(key, 0) or 0)
        rows = _dedupe_rows_by_id(filtered[key], key)
        out[key] = [row for row in rows if _numeric_row_id(row, key) > high_water]
    return out


def find_post_fence_seed_collisions(
    context: dict[str, Any],
    fence: dict[str, Any],
    candidates: set[int],
    current_run_id: int | None = None,
) -> list[dict[str, Any]]:
    """Fail closed if a newly arrived row itself carries a candidate seed literal."""
    external: list[dict[str, Any]] = []
    for key, rows in post_fence_rows(context, fence, current_run_id).items():
        for row in rows:
            canonical = _canonical_collision_value(row)
            hits = seed_literals(canonical, candidates)
            if hits:
                row_id = str(row.get('id') or row.get('number') or row.get('name') or row.get('url') or '')
                external.append({'surface': key, 'id': row_id, 'seeds': hits})
    return external


def external_review_proof_artifacts(
    context: dict[str, Any],
    current_run_id: int | None = None,
) -> list[dict[str, Any]]:
    filtered = _without_current_audit_self_metadata(context, current_run_id)
    return [
        row for row in filtered['artifacts']
        if str(row.get('name') or '') == REVIEW_PROOF_ARTIFACT_NAME
    ]


def canonical_collision_context(context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    """Return deterministic, collision-relevant rows for all audited surfaces.

    Row identities and every non-operational field/content are retained; only
    lifecycle timestamps/status fields are omitted. Sorting rows and nested
    arrays makes pagination/order drift harmless without weakening evidence
    detection for names, heads, bodies, comments, or candidate-seed values.
    """
    filtered = _without_current_audit_self_metadata(context, current_run_id)
    return {
        key: _canonical_collision_value(filtered[key])
        for key in SURFACE_KEYS
    }


def stable_context_sha256(context: dict[str, Any], current_run_id: int | None = None) -> str:
    normalized = canonical_collision_context(context, current_run_id)
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def require_two_pass_stability(first: dict[str, Any], second: dict[str, Any], current_run_id: int | None = None) -> str:
    first_sha = stable_context_sha256(first, current_run_id)
    second_sha = stable_context_sha256(second, current_run_id)
    if first_sha != second_sha:
        raise RuntimeError(
            'snapshot-fenced repository-global metadata changed between two complete enumerations; refuse this audit and start a fresh attempt-1 workflow run'
        )
    return second_sha


def evaluate_context(
    context: dict[str, Any],
    candidates: set[int],
    current_run_id: int | None = None,
    *,
    stable_double_enumeration_passed: bool = False,
    stable_context_sha256_value: str | None = None,
    audit_mode: str = 'review-freeze',
    expected_branch_name: str | None = None,
    expected_repo_head: str | None = None,
    snapshot_fence: dict[str, Any] | None = None,
    post_fence_arrival_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    if audit_mode not in AUDIT_MODES:
        raise ValueError(f'unsupported audit mode: {audit_mode}')
    if len(candidates) != 72:
        raise ValueError('exactly 72 candidate seeds required')
    filtered = _without_current_audit_self_metadata(context, current_run_id)
    canonical = canonical_collision_context(context, current_run_id)

    matching_audited_branches = [
        row for row in filtered['branches']
        if expected_branch_name is not None and str(row.get('name') or '') == expected_branch_name
    ]
    observed_audited_branch_head = None
    if len(matching_audited_branches) == 1:
        observed_audited_branch_head = str((matching_audited_branches[0].get('commit') or {}).get('sha') or '') or None
    audited_branch_head_matches = (
        expected_branch_name is not None
        and expected_repo_head is not None
        and len(matching_audited_branches) == 1
        and observed_audited_branch_head == expected_repo_head
    )

    prior_review_proof_artifacts = [
        row for row in filtered['artifacts']
        if str(row.get('name') or '') == REVIEW_PROOF_ARTIFACT_NAME
    ]
    prior_review_proof_artifact_count = len(prior_review_proof_artifacts)
    review_proof_identity_fresh = prior_review_proof_artifact_count == 0 if audit_mode == 'review-freeze' else None

    external: list[dict[str, Any]] = []
    seen_surface_ids: set[tuple[str, str]] = set()
    for surface, rows in (
        ('branch-metadata', canonical['branches']),
        ('workflow-run-metadata', canonical['runs']),
        ('artifact-metadata', canonical['artifacts']),
        ('all-state-pull-request-metadata-and-body', canonical['pulls']),
        ('all-state-issue-metadata-and-body', canonical['issues']),
        ('repository-issue-comment', canonical['issueComments']),
        ('repository-pull-review-comment', canonical['pullReviewComments']),
        ('repository-commit-comment', canonical['commitComments']),
        ('issue60-comment', canonical['issue60Comments']),
    ):
        for row in rows:
            row_id = str(row.get('id') or row.get('number') or row.get('name') or row.get('url') or '')
            dedupe_key = (surface, row_id)
            if dedupe_key in seen_surface_ids:
                continue
            seen_surface_ids.add(dedupe_key)
            hits = seed_literals(row, candidates)
            if hits:
                external.append({'surface': surface, 'id': row_id, 'seeds': hits})

    fence_value = snapshot_fence or {}
    fence_sha = hashlib.sha256(
        json.dumps(fence_value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest() if fence_value else None

    return {
        'branchCountEnumerated': len(filtered['branches']),
        'workflowRunCountEnumerated': len(filtered['runs']),
        'artifactMetadataCountEnumerated': len(filtered['artifacts']),
        'allStatePullRequestCountEnumerated': len(filtered['pulls']),
        'allStateIssueCountEnumerated': len(filtered['issues']),
        'repositoryIssueCommentCountEnumerated': len(filtered['issueComments']),
        'repositoryPullReviewCommentCountEnumerated': len(filtered['pullReviewComments']),
        'repositoryCommitCommentCountEnumerated': len(filtered['commitComments']),
        'issue60CommentCountEnumerated': len(filtered['issue60Comments']),
        'auditMode': audit_mode,
        'auditedBranchName': expected_branch_name,
        'repositoryHeadExpected': expected_repo_head,
        'auditedBranchHeadShaObserved': observed_audited_branch_head,
        'auditedBranchHeadMatchesRepositoryHead': audited_branch_head_matches,
        'priorReviewProofArtifactCount': prior_review_proof_artifact_count,
        'reviewProofIdentityFresh': review_proof_identity_fresh,
        'reviewProofArtifactName': REVIEW_PROOF_ARTIFACT_NAME,
        'candidateSeedCount': len(candidates),
        'repositoryGlobalCollisionCount': len(external),
        'collisions': external,
        'repositoryGlobalCollisionSurfaceScanPassed': not external,
        'repositoryGlobalDoubleEnumerationStable': stable_double_enumeration_passed,
        'repositoryGlobalEnumerationPassCount': 2 if stable_double_enumeration_passed else 1,
        'repositoryGlobalStableContextSha256': stable_context_sha256_value,
        'repositoryGlobalSnapshotFence': snapshot_fence,
        'repositoryGlobalSnapshotFenceSha256': fence_sha,
        'repositoryGlobalPostFenceArrivalCounts': post_fence_arrival_counts or {},
        'repositoryGlobalPostFenceCandidateSeedCollisionCount': 0,
        'postFenceArrivalsDeferredToMandatoryAuthorizationRecheck': True,
        'currentAuditRunSelfMetadataExclusion': {
            'runId': current_run_id,
            'workflowRunMetadataExcluded': current_run_id is not None,
            'sameRunArtifactMetadataExcluded': current_run_id is not None,
            'allOtherMetadataExcluded': False,
        },
        'allStatePullRequestsInspected': True,
        'allStateIssuesInspected': True,
        'allRepositoryIssueCommentsInspected': True,
        'allRepositoryPullReviewCommentsInspected': True,
        'allRepositoryCommitCommentsInspected': True,
        'surfaceContract': [
            'first-pass-fenced repository branches metadata with original branch heads stable across both complete enumerations',
            'first-pass-fenced repository Actions run metadata except the current audit run self-row',
            'first-pass-fenced repository Actions artifact metadata except metadata produced by the current audit run itself',
            'first-pass-fenced all-state pull request metadata and bodies',
            'first-pass-fenced all-state issue metadata and bodies',
            'first-pass-fenced repository issue comments',
            'first-pass-fenced repository pull-review comments',
            'first-pass-fenced repository commit comments',
            'first-pass-fenced Issue #60 comments',
            'post-fence arrivals are ignored only for snapshot stability and are scanned immediately for candidate-seed literals',
        ],
        'rawHistoricalArtifactBytesRequiredForThisGate': False,
        'authorizationTimeRecheckStillRequired': True,
    }


def collect(repository: str, issue_number: int, token: str) -> dict[str, Any]:
    base = f'https://api.github.com/repos/{repository}'
    issues_and_prs = pages(base + '/issues?state=all', token)
    # The Issues REST endpoint includes pull requests. Keep an actual issue-only array because
    # pull requests are independently and explicitly enumerated by /pulls?state=all.
    issues_only = [row for row in issues_and_prs if 'pull_request' not in row]
    return {
        'branches': pages(base + '/branches', token),
        'runs': pages(base + '/actions/runs', token, 'workflow_runs'),
        'artifacts': pages(base + '/actions/artifacts', token, 'artifacts'),
        'pulls': pages(base + '/pulls?state=all', token),
        'issues': issues_only,
        'issueComments': pages(base + '/issues/comments', token),
        'pullReviewComments': pages(base + '/pulls/comments', token),
        'commitComments': pages(base + '/comments', token),
        'issue60Comments': pages(base + f'/issues/{issue_number}/comments', token),
    }


def collect_stable(
    repository: str,
    issue_number: int,
    token: str,
    current_run_id: int | None,
    candidates: set[int],
    audit_mode: str,
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, int]]:
    first_raw = collect(repository, issue_number, token)
    fence = build_snapshot_fence(first_raw, current_run_id)
    first = apply_snapshot_fence(first_raw, fence, current_run_id)

    second_raw = collect(repository, issue_number, token)
    post_fence = post_fence_rows(second_raw, fence, current_run_id)
    post_fence_counts = {key: len(rows) for key, rows in post_fence.items()}
    post_fence_collisions = find_post_fence_seed_collisions(second_raw, fence, candidates, current_run_id)
    if post_fence_collisions:
        raise RuntimeError(
            'candidate seed appeared on repository-global metadata created after the snapshot fence; refuse this audit'
        )
    if audit_mode == 'review-freeze' and external_review_proof_artifacts(second_raw, current_run_id):
        raise RuntimeError('review-freeze proof artifact already exists outside the current audit run')

    second = apply_snapshot_fence(second_raw, fence, current_run_id)
    stable_sha = require_two_pass_stability(first, second)
    return second, stable_sha, fence, post_fence_counts


def final_expected_branch_head(repository: str, branch_name: str, token: str) -> str:
    encoded = urllib.parse.quote(branch_name, safe='')
    row = req_json(f'https://api.github.com/repos/{repository}/branches/{encoded}', token)
    return str((row.get('commit') or {}).get('sha') or '')


def final_review_proof_artifacts(repository: str, token: str, current_run_id: int | None) -> list[dict[str, Any]]:
    rows = pages(f'https://api.github.com/repos/{repository}/actions/artifacts', token, 'artifacts')
    context = {key: [] for key in SURFACE_KEYS}
    context['artifacts'] = rows
    return external_review_proof_artifacts(context, current_run_id)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repository', required=True)
    ap.add_argument('--issue-number', type=int, default=60)
    ap.add_argument('--candidate-seed-ledger', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--current-run-id', type=int)
    ap.add_argument('--audit-mode', choices=sorted(AUDIT_MODES), required=True)
    ap.add_argument('--expected-branch-name', required=True)
    ap.add_argument('--expected-repo-head', required=True)
    args = ap.parse_args()
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise SystemExit('GITHUB_TOKEN required')
    ledger = json.loads(args.candidate_seed_ledger.read_text())
    seeds = ledger.get('candidateSeeds') if isinstance(ledger, dict) else None
    if not isinstance(seeds, list) or len(seeds) != 72 or len(set(seeds)) != 72:
        raise SystemExit('candidate seed ledger must contain exactly 72 unique seeds')
    candidates = set(seeds)

    context, stable_sha, snapshot_fence, post_fence_counts = collect_stable(
        args.repository,
        args.issue_number,
        token,
        args.current_run_id,
        candidates,
        args.audit_mode,
    )

    final_head = final_expected_branch_head(args.repository, args.expected_branch_name, token)
    if final_head != args.expected_repo_head:
        raise RuntimeError(
            f'audited branch moved before proof completion: expected {args.expected_repo_head}, observed {final_head}'
        )
    if args.audit_mode == 'review-freeze' and final_review_proof_artifacts(
        args.repository, token, args.current_run_id
    ):
        raise RuntimeError('review-freeze proof artifact appeared before proof completion')

    out = evaluate_context(
        context,
        candidates,
        args.current_run_id,
        stable_double_enumeration_passed=True,
        stable_context_sha256_value=stable_sha,
        audit_mode=args.audit_mode,
        expected_branch_name=args.expected_branch_name,
        expected_repo_head=args.expected_repo_head,
        snapshot_fence=snapshot_fence,
        post_fence_arrival_counts=post_fence_counts,
    )
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    passed = (
        out['repositoryGlobalCollisionSurfaceScanPassed']
        and out['repositoryGlobalDoubleEnumerationStable']
        and out['auditedBranchHeadMatchesRepositoryHead'] is True
    )
    if args.audit_mode == 'review-freeze':
        passed = passed and out['priorReviewProofArtifactCount'] == 0 and out['reviewProofIdentityFresh'] is True
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
