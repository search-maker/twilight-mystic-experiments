from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1'
AUTH = REVIEW / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001-authorization.json'
SEED_LEDGER = REVIEW / 'lunar_finite_disk_seed_ledger.py'
PLANNER = REVIEW / 'lunar_finite_disk_transfer_kernel_sensitivity.py'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    a = json.loads(AUTH.read_text())
    assert a['authorizationId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001-authorization'
    assert a['executionId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001'
    assert a['status'] == 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_NOT_DISPATCHED'

    source = a['sourceReview']
    assert source['finiteDiskReviewPr'] == 682
    assert source['finiteDiskContractGitBlobSha1'] == 'e235dcac8f3c307764d207b9111e9ab2011acb82'
    assert source['authorizationRecheckPr'] == 686
    assert source['authorizationRecheckHead'] == '885c978b4349a0967056856724f5f8ea87bf5141'
    assert source['authorizationRecheckRunId'] == 33301829750
    assert source['authorizationRecheckRunAttempt'] == 1
    assert source['authorizationRecheckJobId'] == 99231316637
    assert source['authorizationRecheckConclusion'] == 'success'
    assert source['authorizationRecheckArtifactId'] == 9729425504
    assert source['authorizationRecheckArtifactDigest'] == 'sha256:52691f5eaa6b7337d02a845f76cc5601a3ac8f0274ff02329391fd965141200a'
    assert source['authorizationRecheckStatus'] == 'PASS_AUTHORIZATION_TIME_REPOSITORY_GLOBAL_SEED_RECHECK_ZERO_RUNTIME'

    prior = a['priorFreshnessEvidence']
    assert prior['artifactId'] == 9728990224
    assert prior['artifactDigest'] == 'sha256:fcd3cc6bf2039f41c692c0bbf60f9bf50a2b441792ab94b5f8de62c7fbd25d51'

    seed_mod = load_module('lunar_fd_exec001_seed_ledger_test', SEED_LEDGER)
    ledger = seed_mod.validate_ledger()
    assert ledger['candidateSeedCount'] == 198
    assert ledger['candidateSeedCanonicalSha256'] == prior['candidateSeedCanonicalSha256']
    assert ledger['candidateRowsCanonicalSha256'] == prior['candidateRowsCanonicalSha256']
    assert ledger['candidateSeedCanonicalSha256'] == a['frozenExecution']['replacementSeedCanonicalSha256']
    assert ledger['candidateRowsCanonicalSha256'] == a['frozenExecution']['replacementSeedRowsCanonicalSha256']
    assert ledger['allSeedsOutsideRetiredRange'] is True

    planner = load_module('lunar_fd_exec001_planner_test', PLANNER)
    plan = planner.validate_plan()
    assert plan['caseCount'] == 198
    assert plan['geometryCount'] == 6
    assert plan['directionsPerGeometry'] == 33
    assert abs(plan['lunarAngularRadiusDeg'] - a['frozenExecution']['lunarAngularRadiusDeg']) < 1e-15

    frozen = a['frozenExecution']
    assert frozen['wavelengthNm'] == 550.0
    assert frozen['totalDirectionalCases'] == 198
    assert frozen['photonHistoriesPerDirectionalCase'] == 5_000_000
    assert frozen['totalPhotonHistories'] == 990_000_000
    assert frozen['retiredDisclosedSeedRangeMayExecute'] is False
    assert frozen['mcVroom'] is False
    assert frozen['physicalResolvedDiskWeightAssigned'] is False

    result = a['resultContract']
    assert result['acceptanceThreshold'] is None
    assert result['resultDependentPointSourceAcceptanceForbidden'] is True
    assert result['finiteMoonDiskValidatedByThisExecution'] is False
    assert result['mandatorySpectralFollowOnRequiredBeforeAnyBroadbandFiniteDiskAdequacyClaim'] is True
    assert result['mandatorySpectralFollowOnWavelengthsNm'] == [450.0, 650.0, 750.0]
    assert result['allSixConfigurationsRequiredInSpectralFollowOn'] is True

    rules = a['oneShotRules']
    assert rules['githubRunAttemptMustEqual'] == 1
    assert rules['githubRerunForbidden'] is True
    assert rules['retryForbidden'] is True
    assert rules['resumeForbidden'] is True
    assert rules['seedMappingAllocatedOnlyToThisExecutionIdentity'] is True
    assert rules['postResultAcceptanceThresholdIntroductionForbidden'] is True
    assert rules['resultOpeningOnlyThroughFrozenEvaluator'] is True

    authorization = a['authorization']
    assert authorization['candidateSeedUniverseAllocatedToExecutionIdentity'] is True
    assert authorization['scientificSolverExecutionAuthorized'] is True
    assert authorization['dispatchCreated'] is False
    assert authorization['resultOpeningAuthorizedOnlyByFrozenEvaluator'] is True
    assert authorization['freshIssue60FenceCheckRequiredImmediatelyBeforeDispatchMutation'] is True

    assert all(value is False for value in a['protectedBoundaries'].values())
    print('lunar finite-disk exec001 authorization tests passed')


if __name__ == '__main__':
    main()
