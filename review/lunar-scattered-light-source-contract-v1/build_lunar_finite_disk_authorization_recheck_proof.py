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
CONTRACT_PATH = HERE / 'lunar-finite-disk-authorization-recheck-v1.json'
SEED_LEDGER_PATH = HERE / 'lunar_finite_disk_seed_ledger.py'
SCANNER_WRAPPER_PATH = HERE / 'lunar_repository_global_seed_scan.py'
FINITE_DISK_CONTRACT_PATH = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1.json'
SHA40 = re.compile(r'^[0-9a-f]{40}$')


class Refusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def _load_seed_module():
    spec = importlib.util.spec_from_file_location('lunar_fd_auth_seed_ledger', SEED_LEDGER_PATH)
    if spec is None or spec.loader is None:
        raise Refusal('cannot import replacement seed ledger')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _require_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text())
    if contract.get('schemaVersion') != 1 or contract.get('contractId') != 'lunar-finite-disk-authorization-recheck-v1':
        raise Refusal('authorization recheck contract identity drift')
    if contract.get('status') != 'FROZEN_ZERO_RUNTIME_AUTHORIZATION_RECHECK_ONLY':
        raise Refusal('authorization recheck contract status drift')
    protected = contract.get('protectedBoundaries') or {}
    for key in (
        'solverExecutionAllowed', 'uvspecOrMysticAllowed', 'candidateSeedLiteralsMayBePrinted',
        'candidateSeedsMayBeCommittedToGit', 'taylorResidualUsed', 'jerusalemResidualUsed',
        'parameterFitOrTuningAllowed', 'finiteDiskAdequacyClaimAllowed',
        'empiricalAtmosphericMoonlightValidationClaimAllowed', 'totalSkyValidationClaimAllowed',
        'productionAuthorized',
    ):
        if protected.get(key) is not False:
            raise Refusal(f'protected boundary drift: {key}')
    return contract


def _verify_bound_files(contract: dict[str, Any]) -> None:
    finite = contract['finiteDiskExperimentBinding']
    replacement = contract['replacementSeedBinding']
    if git_blob_sha1(FINITE_DISK_CONTRACT_PATH) != finite['contractGitBlobSha1']:
        raise Refusal('finite-disk experiment contract bytes drift')
    if git_blob_sha1(SEED_LEDGER_PATH) != replacement['ledgerGitBlobSha1AtFreshnessReview']:
        raise Refusal('replacement seed ledger bytes drift')
    if git_blob_sha1(SCANNER_WRAPPER_PATH) != replacement['repositoryGlobalScannerWrapperGitBlobSha1AtFreshnessReview']:
        raise Refusal('repository-global scanner wrapper bytes drift')
    finite_contract = json.loads(FINITE_DISK_CONTRACT_PATH.read_text())
    if finite_contract.get('contractId') != finite['contractId']:
        raise Refusal('finite-disk contract id drift')
    if finite_contract.get('numericalDesign', {}).get('wavelengthNm') != finite['wavelengthNm']:
        raise Refusal('finite-disk wavelength drift')
    if finite_contract.get('directionSampling', {}).get('totalDirectionalCases') != finite['directionalCaseCount']:
        raise Refusal('finite-disk case count drift')
    if finite_contract.get('numericalDesign', {}).get('photonHistoriesPerDirectionalCase') != finite['photonHistoriesPerDirectionalCase']:
        raise Refusal('finite-disk photon budget drift')


def _verify_prior_proof(contract: dict[str, Any], prior_proof: dict[str, Any]) -> None:
    parent = contract['parentState']
    required_equal = {
        'status': parent['seedFreshnessProofStatus'],
        'auditedHead': parent['seedFreshnessReviewHead'],
        'candidateSeedCount': parent['candidateSeedCount'],
        'candidateSeedCanonicalSha256': parent['candidateSeedCanonicalSha256'],
        'candidateRowsCanonicalSha256': parent['candidateRowsCanonicalSha256'],
    }
    for key, expected in required_equal.items():
        if prior_proof.get(key) != expected:
            raise Refusal(f'prior seed freshness proof drift: {key}')
    if prior_proof.get('repositoryGlobalCollisionCount') != 0:
        raise Refusal('prior seed freshness proof contained a collision')
    if prior_proof.get('repositoryGlobalDoubleEnumerationStableAllBatches') is not True:
        raise Refusal('prior seed freshness global enumeration was not stable')
    if prior_proof.get('authorizationTimeRepositoryGlobalRecheckRequired') is not True:
        raise Refusal('prior proof no longer requires authorization-time recheck')
    if prior_proof.get('candidateSeedsAppliedToCases') is not False:
        raise Refusal('prior proof says candidate seeds were already applied')
    if prior_proof.get('solverExecutionAuthorized') is not False:
        raise Refusal('prior proof unexpectedly authorized solver execution')


def _verify_ledger(contract: dict[str, Any]) -> tuple[dict[str, Any], list[list[int]]]:
    seed_mod = _load_seed_module()
    ledger = seed_mod.validate_ledger()
    parent = contract['parentState']
    seeds = [int(x) for x in ledger['candidateSeeds']]
    rows = ledger['candidateRows']
    if ledger.get('candidateSeedCount') != 198 or len(seeds) != 198 or len(set(seeds)) != 198 or len(rows) != 198:
        raise Refusal('replacement candidate universe drift')
    if ledger.get('candidateSeedCanonicalSha256') != parent['candidateSeedCanonicalSha256']:
        raise Refusal('candidate seed hash differs from frozen prior proof')
    if ledger.get('candidateRowsCanonicalSha256') != parent['candidateRowsCanonicalSha256']:
        raise Refusal('candidate row hash differs from frozen prior proof')
    if ledger.get('candidateSeedCanonicalSha256') != canonical_sha256(seeds):
        raise Refusal('candidate seed canonical hash internally inconsistent')
    if ledger.get('candidateRowsCanonicalSha256') != canonical_sha256(rows):
        raise Refusal('candidate rows canonical hash internally inconsistent')
    if ledger.get('allSeedsOutsideRetiredRange') is not True:
        raise Refusal('candidate seed overlaps retired disclosed range')
    if ledger.get('candidateSeedsAppliedToCases') is not False:
        raise Refusal('candidate ledger says seeds are already applied')
    batches = seed_mod.audit_batches(seeds)
    if len(batches) != 3 or any(len(batch) != 72 or len(set(batch)) != 72 for batch in batches):
        raise Refusal('authorization recheck scanner batch construction drift')
    if set().union(*(set(batch) for batch in batches)) != set(seeds):
        raise Refusal('authorization recheck batches do not cover all candidates')
    return ledger, batches


def _verify_global(report: dict[str, Any], batch_index: int, expected_head: str) -> None:
    if report.get('auditMode') != 'authorization-recheck':
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
        raise Refusal(f'global batch {batch_index} branch head mismatch')
    if report.get('repositoryHeadExpected') != expected_head or report.get('auditedBranchHeadShaObserved') != expected_head:
        raise Refusal(f'global batch {batch_index} exact-head binding drift')
    if report.get('repositoryGlobalPostFenceCandidateSeedCollisionCount') not in (0, None):
        raise Refusal(f'global batch {batch_index} post-fence candidate collision exists')


def build(prior_proof: dict[str, Any], global_reports: list[dict[str, Any]], expected_head: str) -> dict[str, Any]:
    if SHA40.fullmatch(expected_head) is None:
        raise Refusal('expected head must be a lowercase 40-character SHA')
    if len(global_reports) != 3:
        raise Refusal('exactly three authorization-recheck scanner reports required')
    contract = _require_contract()
    _verify_bound_files(contract)
    _verify_prior_proof(contract, prior_proof)
    ledger, batches = _verify_ledger(contract)
    for index, report in enumerate(global_reports, start=1):
        _verify_global(report, index, expected_head)

    return {
        'schemaVersion': 1,
        'stageId': 'lunar-finite-disk-authorization-recheck-v1',
        'status': contract['classificationOnPass'],
        'auditedHead': expected_head,
        'priorFreshnessReview': {
            'runId': contract['parentState']['seedFreshnessRunId'],
            'runAttempt': contract['parentState']['seedFreshnessRunAttempt'],
            'artifactName': contract['parentState']['seedFreshnessArtifactName'],
            'artifactId': contract['parentState']['seedFreshnessArtifactId'],
            'artifactDigest': contract['parentState']['seedFreshnessArtifactDigest'],
            'proofStatus': contract['parentState']['seedFreshnessProofStatus'],
            'auditedHead': contract['parentState']['seedFreshnessReviewHead'],
        },
        'finiteDiskContractGitBlobSha1': contract['finiteDiskExperimentBinding']['contractGitBlobSha1'],
        'candidateSeedCount': 198,
        'candidateSeedCanonicalSha256': ledger['candidateSeedCanonicalSha256'],
        'candidateRowsCanonicalSha256': ledger['candidateRowsCanonicalSha256'],
        'auditBatchCanonicalSha256': [canonical_sha256(batch) for batch in batches],
        'auditBatchCount': 3,
        'auditBatchSize': 72,
        'scannerCoverageUniqueCandidateCount': 198,
        'repositoryGlobalCollisionCount': 0,
        'repositoryGlobalDoubleEnumerationStableAllBatches': True,
        'repositoryGlobalStableContextSha256ByBatch': [r.get('repositoryGlobalStableContextSha256') for r in global_reports],
        'repositoryGlobalSnapshotFenceSha256ByBatch': [r.get('repositoryGlobalSnapshotFenceSha256') for r in global_reports],
        'repositoryGlobalPostFenceArrivalCountsByBatch': [r.get('repositoryGlobalPostFenceArrivalCounts') or {} for r in global_reports],
        'candidateSeedState': 'AUTHORIZATION_RECHECK_PASSED_STILL_UNAPPLIED',
        'candidateSeedsAppliedToCases': False,
        'scientificOrdinalAllocated': False,
        'scientificExecutionAuthorizationCreated': False,
        'dispatchCreated': False,
        'solverExecuted': False,
        'solverExecutionAuthorized': False,
        'resultOpened': False,
        'resultOpeningAuthorized': False,
        'finiteDiskAdequacyClaimed': False,
        'empiricalAtmosphericMoonlightValidated': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
        'nextAction': contract['nextActionOnPass'],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--prior-proof', type=Path, required=True)
    parser.add_argument('--global-report', action='append', type=Path, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = build(
        json.loads(args.prior_proof.read_text()),
        [json.loads(path.read_text()) for path in args.global_report],
        args.expected_head,
    )
    args.output.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
