from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from authorization_guard import require, validate_enabled_document
from freshness import consumed_marker, matching_marker, validate_dispatch

SHA40 = re.compile(r'^[0-9a-f]{40}$')


class GuardRefusal(RuntimeError):
    pass


def _guard_require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardRefusal(message)


def raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_pairing_manifest(core, manifest: dict[str, Any]) -> list[int]:
    core.validate_manifest(manifest)
    by_group: dict[str, list[dict[str, Any]]] = {}
    for case in manifest['cases']:
        by_group.setdefault(case['groupId'], []).append(case)
    _guard_require(len(by_group) == 72, 'expected 72 comparison groups')
    seen_group_seeds: set[int] = set()
    for group_id, rows in by_group.items():
        _guard_require(len(rows) == 8, f'{group_id}: expected eight family/season states')
        seeds = {int(r['seed']) for r in rows}
        _guard_require(len(seeds) == 1, f'{group_id}: common-random-number seed drift')
        seed = next(iter(seeds))
        _guard_require(seed not in seen_group_seeds, f'{group_id}: seed reused across comparison groups')
        seen_group_seeds.add(seed)
    ordered_group_seeds = [int(group['seed']) for group in manifest.get('groups', []) if isinstance(group, dict)]
    _guard_require(len(ordered_group_seeds) == 72 and len(set(ordered_group_seeds)) == 72, 'manifest group seed ledger invalid')
    _guard_require(tuple(ordered_group_seeds) == tuple(core.CANDIDATE_GROUP_SEEDS), 'manifest group seeds differ from preregistered candidate ledger')
    return ordered_group_seeds


def evaluate(
    core,
    freeze_record: dict[str, Any],
    manifest: dict[str, Any],
    authorization: dict[str, Any],
    live_seed_audit: dict[str, Any],
    context: dict[str, Any],
    paths: dict[str, Path],
) -> dict[str, Any]:
    manifest_group_seeds = validate_pairing_manifest(core, manifest)
    _guard_require(freeze_record.get('status') == 'FROZEN_REVIEW_PACKAGE_NOT_AUTHORIZATION', 'freeze record missing or stale')
    _guard_require(freeze_record.get('scientificExecutionAuthorized') is False and freeze_record.get('solverExecutionAuthorized') is False, 'freeze record illegally authorized execution')
    _guard_require(freeze_record.get('manifestRawSha256') == raw_sha(paths['manifest']), 'manifest/freeze hash mismatch')
    _guard_require(freeze_record.get('authorizationTimeSeedRecheckStillRequired') is True, 'authorization-time seed recheck boundary drift')

    head = context.get('headSha')
    parent = context.get('parentSha')
    ordinal = authorization.get('scientificOrdinal')
    _guard_require(isinstance(head, str) and SHA40.fullmatch(head) is not None, 'context head SHA invalid')
    _guard_require(isinstance(parent, str) and SHA40.fullmatch(parent) is not None, 'context parent SHA invalid')
    try:
        validate_enabled_document(authorization, parent, paths)
    except Exception as exc:
        raise GuardRefusal(str(exc)) from exc
    _guard_require(authorization.get('exactAuthorizationCommit') is None, 'authorization document must not self-embed head SHA')
    _guard_require(context.get('githubActions') is True and context.get('eventName') == 'push' and context.get('runAttempt') == 1, 'not exact attempt-1 GitHub push context')
    _guard_require(context.get('refName') == authorization.get('dispatchBranch'), 'dispatch branch drift')
    _guard_require(context.get('dispatchBranchHeadSha') == head, 'dispatch branch does not point to exact authorization head')
    _guard_require(head == context.get('authorizationHead'), 'dispatch head differs from reviewed authorization head')
    _guard_require(parent == authorization.get('exactAuthorizationParentCommit'), 'authorization parent drift')
    _guard_require(context.get('authorizationCommitParentCount') == 1, 'authorization commit must have exactly one parent')
    _guard_require(context.get('authorizationCommitChangedPaths') == ['experiments/aerosol-family-challenge-v2-r7/authorization.json'], 'authorization commit changed unexpected paths')
    pr = context.get('pr') or {}
    _guard_require(pr.get('state') == 'open' and pr.get('draft') is True and pr.get('merged') is False, 'authorization PR no longer Draft/open/unmerged')
    _guard_require(pr.get('headSha') == head and pr.get('headBranch') == authorization.get('authorizationBranch'), 'authorization PR head/branch drift')
    review = context.get('authorizationReview') or {}
    _guard_require(review.get('status') == 'AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME', 'zero-runtime authorization review pass missing')
    _guard_require(review.get('headSha') == head and review.get('prNumber') == pr.get('number'), 'authorization review identity drift')
    _guard_require(review.get('runAttempt') == 1 and review.get('conclusion') == 'success', 'exact successful attempt-1 authorization review required')
    _guard_require(review.get('scientificRuntimeSetupPerformed') is False and review.get('scientificExecutionPerformed') is False, 'authorization review executed scientific runtime')
    try:
        validate_dispatch(context.get('freshness') or {}, ordinal, head, post_dispatch=True)
    except Exception as exc:
        raise GuardRefusal(str(exc)) from exc
    markers = context.get('issue60Markers') or []
    _guard_require(len(markers) == 1 and matching_marker(markers[0], ordinal, head, parent, int(pr.get('number') or 0)), 'exact Issue #60 authorization marker missing/drifted')
    _guard_require(context.get('priorRunsOnDispatch') == [], 'dispatch identity already has a prior run')
    prior_artifacts = context.get('priorCaseArtifactNames')
    _guard_require(isinstance(prior_artifacts, list) and not any(str(x).startswith('aerosol-family-v2-r7-case-') for x in prior_artifacts), 'prior aerosol-family case artifact exists')
    comments = context.get('issue60Comments')
    marker = consumed_marker(ordinal)
    _guard_require(isinstance(comments, list) and not any(marker.lower() in str(x).lower() for x in comments), 'dispatch consumed marker already exists')

    _guard_require(live_seed_audit.get('status') == 'PASSED_EXACT_HEAD_TRACKED_TREE_AND_REPOSITORY_GLOBAL_COLLISION_SURFACES_NEGATIVE_CHECK', 'authorization-time seed audit did not pass')
    _guard_require(live_seed_audit.get('auditMode') == 'authorization-recheck', 'authorization-time seed audit must use authorization-recheck mode')
    _guard_require(live_seed_audit.get('candidateSeedCount') == 72, 'authorization-time seed audit candidate count drift')
    _guard_require(live_seed_audit.get('candidateFirstSeed') == manifest_group_seeds[0] and live_seed_audit.get('candidateLastSeed') == manifest_group_seeds[-1], 'authorization-time seed audit candidate endpoints drift')
    _guard_require(live_seed_audit.get('candidateSeedCanonicalSha256') == core.canonical_sha256(manifest_group_seeds), 'authorization-time seed audit candidate ledger drift')
    _guard_require(live_seed_audit.get('candidateSeedDerivationNamespace') == core.SEED_DERIVATION_NAMESPACE, 'authorization-time seed derivation namespace drift')
    _guard_require(live_seed_audit.get('repositoryHead') == head, 'authorization-time seed audit is not exact-head')
    _guard_require(live_seed_audit.get('auditedBranchName') == authorization.get('authorizationBranch'), 'authorization-time seed audit branch identity drift')
    _guard_require(live_seed_audit.get('auditedBranchHeadShaObserved') == head and live_seed_audit.get('auditedBranchHeadMatchesRepositoryHead') is True, 'authorization-time seed audit did not observe exact authorization branch head')
    _guard_require(live_seed_audit.get('sourceBaseMainSha') == core.PUBLIC_REPO_MAIN_SHA, 'authorization-time seed audit source base drift')
    _guard_require(live_seed_audit.get('exactHeadTrackedTreeByteScanPassed') is True, 'tracked-tree seed scan not passed')
    _guard_require(live_seed_audit.get('repositoryGlobalCollisionSurfaceScanPassed') is True, 'repository-global seed collision surface scan not passed')
    _guard_require(live_seed_audit.get('repositoryGlobalDoubleEnumerationStable') is True and live_seed_audit.get('repositoryGlobalEnumerationPassCount') == 2, 'repository-global seed audit was not a stable double enumeration')
    _guard_require(live_seed_audit.get('externalCollisionCount') == 0, 'seed collision detected')
    _guard_require(live_seed_audit.get('allStatePullRequestsInspected') is True, 'seed audit omitted all-state pull requests')
    _guard_require(live_seed_audit.get('allStateIssuesInspected') is True, 'seed audit omitted all-state issues')
    _guard_require(live_seed_audit.get('allRepositoryIssueCommentsInspected') is True, 'seed audit omitted repository issue comments')
    _guard_require(live_seed_audit.get('allRepositoryPullReviewCommentsInspected') is True, 'seed audit omitted pull review comments')
    _guard_require(live_seed_audit.get('excludedCurrentAuditRunId') == context.get('currentRunId'), 'only current pre-solver audit run may be excluded from archived-log scan')
    _guard_require(live_seed_audit.get('authorizationPermitted') is False, 'seed audit itself must never authorize execution')

    return {
        'schemaVersion': 2,
        'stageId': 'aerosol-family-challenge-v2-r7-execution-guard',
        'status': 'EXACT_ONE_USE_AEROSOL_FAMILY_V2_R7_DISPATCH_AUTHORIZED',
        'scientificOrdinal': ordinal,
        'executionKey': authorization['executionKey'],
        'authorizationCommitSha': head,
        'authorizationDocumentOwnCommitShaEmbedded': False,
        'manifestRawSha256': raw_sha(paths['manifest']),
        'freezeRecordRawSha256': raw_sha(paths['freeze']),
        'caseCount': 576,
        'comparisonGroupCount': 72,
        'configuredPhotonHistories': 11_520_000_000,
        'solverExecutionPermittedNow': True,
        'githubRerunAllowed': False,
        'retryAllowed': False,
        'resumeAllowed': False,
        'protectedHoldoutOpeningAuthorized': False,
        'productionPromotionAuthorized': False,
    }
