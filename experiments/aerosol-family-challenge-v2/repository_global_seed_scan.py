from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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

# These fields describe the observation/transport lifecycle rather than the
# collision surface.  They are intentionally removed recursively before the
# two-pass fingerprint so a run changing from queued to completed (or a
# timestamp advancing while pagination is in flight) does not create a false
# instability.  All identifiers, names, hashes, bodies and other content are
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


def canonical_collision_context(context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    """Return deterministic, collision-relevant rows for all audited surfaces.

    Row identities and every non-operational field/content are retained; only
    lifecycle timestamps/status fields are omitted.  Sorting rows and nested
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
            'repository-global metadata changed between two complete enumerations; refuse this audit and rerun from a fresh attempt-1 workflow run'
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
            'all repository branches metadata',
            'all repository Actions run metadata except the current audit run self-row',
            'all repository Actions artifact metadata except metadata produced by the current audit run itself',
            'all-state pull request metadata and bodies',
            'all-state issue metadata and bodies',
            'all repository issue comments',
            'all repository pull-review comments',
            'all repository commit comments',
            'all Issue #60 comments',
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


def collect_stable(repository: str, issue_number: int, token: str, current_run_id: int | None) -> tuple[dict[str, Any], str]:
    first = collect(repository, issue_number, token)
    second = collect(repository, issue_number, token)
    stable_sha = require_two_pass_stability(first, second, current_run_id)
    return second, stable_sha


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
    context, stable_sha = collect_stable(args.repository, args.issue_number, token, args.current_run_id)
    out = evaluate_context(
        context,
        set(seeds),
        args.current_run_id,
        stable_double_enumeration_passed=True,
        stable_context_sha256_value=stable_sha,
        audit_mode=args.audit_mode,
        expected_branch_name=args.expected_branch_name,
        expected_repo_head=args.expected_repo_head,
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
