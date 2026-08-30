from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SEED_LEDGER_PATH = HERE / 'lunar_finite_disk_seed_ledger.py'
SHA40 = re.compile(r'^[0-9a-f]{40}$')


class Refusal(RuntimeError):
    pass


def _load_seed_module():
    spec = importlib.util.spec_from_file_location('lunar_finite_disk_seed_proof_ledger', SEED_LEDGER_PATH)
    if spec is None or spec.loader is None:
        raise Refusal('cannot import replacement seed ledger')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def _validate_tracked(report: dict[str, Any], batch_index: int) -> None:
    if report.get('candidateSeedCount') != 72:
        raise Refusal(f'tracked-tree batch {batch_index} candidate count drift')
    if report.get('trackedTreeExternalCollisionCount') != 0:
        raise Refusal(f'tracked-tree batch {batch_index} candidate collision exists')
    if report.get('exactHeadTrackedTreeByteScanPassed') is not True:
        raise Refusal(f'tracked-tree batch {batch_index} byte scan failed')
    if report.get('requiredSelfLedgerPathsPresent') is not True:
        raise Refusal(f'tracked-tree batch {batch_index} self-ledger policy failed')
    if report.get('selfLedgerHitCount') != 0:
        raise Refusal(f'tracked-tree batch {batch_index} unexpectedly found candidate literals')


def _validate_global(report: dict[str, Any], batch_index: int, expected_head: str) -> None:
    if report.get('auditMode') != 'review-freeze':
        raise Refusal(f'global batch {batch_index} audit mode drift')
    if report.get('candidateSeedCount') != 72:
        raise Refusal(f'global batch {batch_index} candidate count drift')
    if report.get('repositoryGlobalCollisionCount') != 0:
        raise Refusal(f'global batch {batch_index} candidate collision exists')
    if report.get('repositoryGlobalCollisionSurfaceScanPassed') is not True:
        raise Refusal(f'global batch {batch_index} collision scan failed')
    if report.get('repositoryGlobalDoubleEnumerationStable') is not True:
        raise Refusal(f'global batch {batch_index} double enumeration unstable')
    if report.get('auditedBranchHeadMatchesRepositoryHead') is not True:
        raise Refusal(f'global batch {batch_index} audited branch head mismatch')
    if report.get('repositoryHeadExpected') != expected_head:
        raise Refusal(f'global batch {batch_index} expected head drift')
    if report.get('auditedBranchHeadShaObserved') != expected_head:
        raise Refusal(f'global batch {batch_index} observed head drift')
    if report.get('priorReviewProofArtifactCount') != 0:
        raise Refusal(f'global batch {batch_index} review-proof identity already existed')
    if report.get('reviewProofIdentityFresh') is not True:
        raise Refusal(f'global batch {batch_index} review-proof identity is not fresh')
    if report.get('repositoryGlobalPostFenceCandidateSeedCollisionCount') not in (0, None):
        raise Refusal(f'global batch {batch_index} post-fence candidate collision exists')


def build(tracked_reports: list[dict[str, Any]], global_reports: list[dict[str, Any]], expected_head: str) -> dict[str, Any]:
    if SHA40.fullmatch(expected_head) is None:
        raise Refusal('expected head must be a 40-character lowercase SHA')
    if len(tracked_reports) != 3 or len(global_reports) != 3:
        raise Refusal('exactly three bound 72-seed scan batches required')

    seed_mod = _load_seed_module()
    ledger = seed_mod.validate_ledger()
    seeds = [int(value) for value in ledger['candidateSeeds']]
    rows = ledger['candidateRows']
    batches = seed_mod.audit_batches(seeds)
    if ledger.get('status') != 'CANDIDATE_ONLY_ARTIFACT_ONLY_NOT_APPLIED_NOT_AUTHORIZED':
        raise Refusal('replacement candidate ledger status drift')
    if ledger.get('candidateSeedCount') != 198 or len(rows) != 198 or len(set(seeds)) != 198:
        raise Refusal('replacement candidate universe drift')
    if ledger.get('trackedCandidateSeedLedger') is not False:
        raise Refusal('replacement candidate seed literals unexpectedly tracked')
    if ledger.get('allSeedsOutsideRetiredRange') is not True:
        raise Refusal('replacement candidate overlaps retired disclosed range')
    if ledger.get('candidateSeedCanonicalSha256') != canonical_sha256(seeds):
        raise Refusal('replacement candidate seed canonical hash drift')
    if ledger.get('candidateRowsCanonicalSha256') != canonical_sha256(rows):
        raise Refusal('replacement candidate row canonical hash drift')
    batch_hashes = [canonical_sha256(batch) for batch in batches]
    if ledger.get('auditBatchCanonicalSha256') != batch_hashes:
        raise Refusal('replacement audit batch hash drift')
    if set().union(*(set(batch) for batch in batches)) != set(seeds):
        raise Refusal('three scanner batches do not cover exact 198-candidate universe')

    for index, report in enumerate(tracked_reports, start=1):
        _validate_tracked(report, index)
    for index, report in enumerate(global_reports, start=1):
        _validate_global(report, index, expected_head)

    return {
        'schemaVersion': 1,
        'stageId': 'lunar-finite-disk-transfer-kernel-sensitivity-v1-replacement-seed-freshness-review',
        'status': 'PASS_REPLACEMENT_CANDIDATE_SEEDS_FRESH_REVIEW_ONLY_NOT_ALLOCATED',
        'auditedHead': expected_head,
        'candidateSeedCount': 198,
        'candidateSeedCanonicalSha256': ledger['candidateSeedCanonicalSha256'],
        'candidateRowsCanonicalSha256': ledger['candidateRowsCanonicalSha256'],
        'auditBatchCanonicalSha256': batch_hashes,
        'auditBatchCount': 3,
        'auditBatchSize': 72,
        'scannerCoverageUniqueCandidateCount': 198,
        'scannerCoverageIncludes18IntentionalRepeatedCandidatesInFinalBatch': True,
        'allSeedsOutsideRetiredDisclosedRange': True,
        'retiredPriorCandidateRangeMayEverExecute': False,
        'trackedTreeExternalCollisionCount': 0,
        'repositoryGlobalCollisionCount': 0,
        'repositoryGlobalCollisionSurfaceScanPassed': True,
        'repositoryGlobalDoubleEnumerationStableAllBatches': True,
        'repositoryGlobalStableContextSha256ByBatch': [r.get('repositoryGlobalStableContextSha256') for r in global_reports],
        'repositoryGlobalSnapshotFenceSha256ByBatch': [r.get('repositoryGlobalSnapshotFenceSha256') for r in global_reports],
        'repositoryGlobalPostFenceArrivalCountsByBatch': [r.get('repositoryGlobalPostFenceArrivalCounts') or {} for r in global_reports],
        'candidateSeedsTrackedInGit': False,
        'candidateSeedsAppliedToCases': False,
        'scientificOrdinalAllocated': False,
        'authorizationCreated': False,
        'dispatchCreated': False,
        'scientificExecutionAuthorized': False,
        'solverExecutionAuthorized': False,
        'resultOpeningAuthorized': False,
        'productionAuthorized': False,
        'authorizationTimeRepositoryGlobalRecheckRequired': True,
        'authorizationTimeRetiredRangeRefusalRequired': True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tracked-report', action='append', type=Path, required=True)
    parser.add_argument('--global-report', action='append', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = build(
        [json.loads(path.read_text()) for path in args.tracked_report],
        [json.loads(path.read_text()) for path in args.global_report],
        args.expected_head,
    )
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
