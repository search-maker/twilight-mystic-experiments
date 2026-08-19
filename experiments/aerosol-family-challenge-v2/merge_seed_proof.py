from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

SHA40 = re.compile(r'^[0-9a-f]{40}$')


def canon(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--design', type=Path, required=True)
    ap.add_argument('--candidate-seed-ledger', type=Path, required=True)
    ap.add_argument('--tracked', type=Path, required=True)
    ap.add_argument('--repository-global', type=Path, required=True)
    ap.add_argument('--repo-head', required=True)
    ap.add_argument('--source-base-main-sha', required=True)
    ap.add_argument('--current-run-id', type=int, required=True)
    ap.add_argument('--audit-mode', choices=['review-freeze', 'authorization-recheck'], required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if not SHA40.fullmatch(a.repo_head) or not SHA40.fullmatch(a.source_base_main_sha):
        raise SystemExit('invalid git SHA binding')
    d = json.loads(a.design.read_text())
    ledger = json.loads(a.candidate_seed_ledger.read_text())
    t = json.loads(a.tracked.read_text())
    r = json.loads(a.repository_global.read_text())
    seeds = d['groupSeeds']
    if ledger.get('candidateSeeds') != seeds:
        raise SystemExit('candidate seed ledger/design mismatch')
    tree_count = t.get('trackedTreeExternalCollisionCount')
    future_evidence_present_count = t.get('futureEvidenceSelfLedgerPathCountPresent')
    run_count = r.get('repositoryGlobalCollisionCount')
    counts_valid = isinstance(tree_count, int) and isinstance(run_count, int)
    collisions = tree_count + run_count if counts_valid else None
    if r.get('auditMode') != a.audit_mode:
        raise SystemExit('repository-global audit mode mismatch')
    prior_review_proof_count = r.get('priorReviewProofArtifactCount')
    review_proof_identity_fresh = r.get('reviewProofIdentityFresh')
    review_identity_ok = (
        a.audit_mode == 'authorization-recheck'
        or (
            prior_review_proof_count == 0
            and review_proof_identity_fresh is True
            and future_evidence_present_count == 0
        )
    )
    all_surface_flags = all(
        r.get(key) is True
        for key in (
            'allStatePullRequestsInspected',
            'allStateIssuesInspected',
            'allRepositoryIssueCommentsInspected',
            'allRepositoryPullReviewCommentsInspected',
            'allRepositoryCommitCommentsInspected',
        )
    )
    stable_double_enumeration = (
        r.get('repositoryGlobalDoubleEnumerationStable') is True
        and r.get('repositoryGlobalEnumerationPassCount') == 2
        and isinstance(r.get('repositoryGlobalStableContextSha256'), str)
        and len(r.get('repositoryGlobalStableContextSha256')) == 64
    )
    audited_branch_binding_ok = (
        r.get('auditedBranchHeadMatchesRepositoryHead') is True
        and r.get('repositoryHeadExpected') == a.repo_head
        and r.get('auditedBranchHeadShaObserved') == a.repo_head
        and isinstance(r.get('auditedBranchName'), str)
        and bool(r.get('auditedBranchName'))
    )
    passed = (
        t.get('exactHeadTrackedTreeByteScanPassed') is True
        and r.get('repositoryGlobalCollisionSurfaceScanPassed') is True
        and all_surface_flags
        and stable_double_enumeration
        and audited_branch_binding_ok
        and review_identity_ok
        and collisions == 0
    )
    out = {
        'schemaVersion': 2,
        'stageId': 'aerosol-family-challenge-v2-seed-audit',
        'status': 'PASSED_EXACT_HEAD_TRACKED_TREE_AND_REPOSITORY_GLOBAL_COLLISION_SURFACES_NEGATIVE_CHECK' if passed else 'INCOMPLETE_OR_COLLIDING_REFUSE_FREEZE',
        'repositoryFullName': 'search-maker/twilight-mystic-experiments',
        'auditMode': a.audit_mode,
        'auditedBranchName': r.get('auditedBranchName'),
        'auditedBranchHeadShaObserved': r.get('auditedBranchHeadShaObserved'),
        'auditedBranchHeadMatchesRepositoryHead': audited_branch_binding_ok,
        'priorReviewProofArtifactCount': prior_review_proof_count,
        'reviewProofIdentityFresh': review_proof_identity_fresh,
        'reviewProofArtifactName': r.get('reviewProofArtifactName'),
        'repositoryHead': a.repo_head,
        'sourceBaseMainSha': a.source_base_main_sha,
        'candidateSeedCount': len(seeds),
        'candidateFirstSeed': seeds[0],
        'candidateLastSeed': seeds[-1],
        'candidateSeedCanonicalSha256': canon(seeds),
        'candidateSeedLedgerRawSha256': hashlib.sha256(a.candidate_seed_ledger.read_bytes()).hexdigest(),
        'candidateSeedDerivationNamespace': ledger.get('namespace'),
        'auditedDesignRawSha256': hashlib.sha256(a.design.read_bytes()).hexdigest(),
        'exactHeadTrackedTreeByteScanPassed': t.get('exactHeadTrackedTreeByteScanPassed') is True,
        'trackedFileCount': t.get('trackedFileCount'),
        'trackedTreeExternalCollisionCount': tree_count,
        'futureEvidenceSelfLedgerPathsPresent': t.get('futureEvidenceSelfLedgerPathsPresent'),
        'futureEvidenceSelfLedgerPathCountPresent': future_evidence_present_count,
        'repositoryGlobalCollisionSurfaceScanPassed': r.get('repositoryGlobalCollisionSurfaceScanPassed') is True,
        'repositoryGlobalDoubleEnumerationStable': stable_double_enumeration,
        'repositoryGlobalEnumerationPassCount': r.get('repositoryGlobalEnumerationPassCount'),
        'repositoryGlobalStableContextSha256': r.get('repositoryGlobalStableContextSha256'),
        'currentAuditRunSelfMetadataExclusion': r.get('currentAuditRunSelfMetadataExclusion'),
        'branchCountEnumerated': r.get('branchCountEnumerated'),
        'workflowRunCountEnumerated': r.get('workflowRunCountEnumerated'),
        'artifactMetadataCountEnumerated': r.get('artifactMetadataCountEnumerated'),
        'allStatePullRequestCountEnumerated': r.get('allStatePullRequestCountEnumerated'),
        'allStateIssueCountEnumerated': r.get('allStateIssueCountEnumerated'),
        'repositoryIssueCommentCountEnumerated': r.get('repositoryIssueCommentCountEnumerated'),
        'repositoryPullReviewCommentCountEnumerated': r.get('repositoryPullReviewCommentCountEnumerated'),
        'repositoryCommitCommentCountEnumerated': r.get('repositoryCommitCommentCountEnumerated'),
        'issue60CommentCountEnumerated': r.get('issue60CommentCountEnumerated'),
        'allStatePullRequestsInspected': r.get('allStatePullRequestsInspected') is True,
        'allStateIssuesInspected': r.get('allStateIssuesInspected') is True,
        'allRepositoryIssueCommentsInspected': r.get('allRepositoryIssueCommentsInspected') is True,
        'allRepositoryPullReviewCommentsInspected': r.get('allRepositoryPullReviewCommentsInspected') is True,
        'allRepositoryCommitCommentsInspected': r.get('allRepositoryCommitCommentsInspected') is True,
        'repositoryGlobalCollisionCount': run_count,
        'rawHistoricalArtifactBytesRequiredForThisGate': False,
        'externalCollisionCount': collisions,
        'excludedCurrentAuditRunId': a.current_run_id,
        'authorizationPermitted': False,
        'authorizationTimeRecheckStillRequired': True,
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
