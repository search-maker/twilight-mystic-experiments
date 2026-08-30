from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1'
AUTH = REVIEW / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002-authorization.json'
CONTRACT = REVIEW / 'lunar-finite-disk-transfer-kernel-sensitivity-v1.json'


def main() -> None:
    a = json.loads(AUTH.read_text())
    c = json.loads(CONTRACT.read_text())

    assert a['authorizationId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002-authorization'
    assert a['executionId'] == 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002'
    assert a['status'] == 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_NOT_DISPATCHED_PENDING_SOLVER_FREE_REVIEW'

    source = a['sourceReview']
    assert source['finiteDiskContractId'] == c['contractId']
    assert source['finiteDiskContractGitBlobSha1'] == 'e235dcac8f3c307764d207b9111e9ab2011acb82'
    assert source['authorizationRecheckPr'] == 746
    assert source['authorizationRecheckHead'] == '7698d3f58756650be5ffcfd41d277dadbbba1874'
    assert source['authorizationRecheckRunId'] == 33340294645
    assert source['authorizationRecheckRunAttempt'] == 1
    assert source['authorizationRecheckJobId'] == 99334573867
    assert source['authorizationRecheckConclusion'] == 'success'
    assert source['authorizationRecheckArtifactId'] == 9740536985
    assert source['authorizationRecheckArtifactDigest'] == 'sha256:3949d8b0b9d7ef7b9a689613b4088a96a82a79c2a04f284ec44eeb64df1bc713'
    assert source['authorizationRecheckStatus'] == 'PASS_LUNAR_FINITE_DISK_EXEC002_AUTHORIZATION_TIME_RECHECK_ZERO_RUNTIME'
    assert source['authorizationRecheckProofPayloadSha256'] == 'a926a708780141e737bf628701e755fa65483f9f4a790a203e4dfc818365d8c9'

    prior = a['priorFreshnessEvidence']
    assert prior['reviewPr'] == 745
    assert prior['reviewHead'] == 'f675749e838c55385f907dd8f85000c2a607951e'
    assert prior['runId'] == 33337886233
    assert prior['runAttempt'] == 1
    assert prior['jobId'] == 99328019674
    assert prior['artifactId'] == 9739969664
    assert prior['artifactDigest'] == 'sha256:fa1ed884e21b59dee7a3013cfb2fd84ab3c3cd8f2befaca1f1ed26fb5b44e858'
    assert prior['controlStatus'] == 'PASS_LUNAR_FINITE_DISK_EXEC002_FRESH_SEED_AND_PAGINATED_RELEASE_CONTROL'
    assert prior['candidateSeedCount'] == 198
    assert prior['candidateSeedCanonicalSha256'] == '30350e6986b554d09bcd77e9095cb871dd634a80a4f219cca29d0fc0b8249e84'
    assert prior['candidateRowsCanonicalSha256'] == '7dbb4cbe6c34ffad668eb63ad051bd7319d68e56ea1b3c4e540d70eda23b1c95'

    predecessor = a['consumedPredecessor']
    assert predecessor['executionId'].endswith('exec001')
    assert predecessor['runId'] == 33303099872
    assert predecessor['consumed'] is True
    assert predecessor['rerunRetryResumeForbidden'] is True
    assert predecessor['resultsExist'] is False

    frozen = a['frozenExecution']
    assert frozen['wavelengthNm'] == c['numericalDesign']['wavelengthNm'] == 550.0
    assert frozen['moonCenterZenithDeg'] == c['physicalGeometry']['moonCenterZenithDeg'] == 30.0
    assert frozen['targetAltitudeDeg'] == c['physicalGeometry']['targetAltitudeDeg'] == 45.0
    assert frozen['targetRelativeAzimuthToMoonCenterDeg'] == c['physicalGeometry']['targetRelativeAzimuthToMoonCenterDeg']
    assert frozen['observerElevationM'] == c['physicalGeometry']['observerElevationM']
    assert frozen['lunarAngularRadiusDeg'] == c['physicalGeometry']['expectedAngularRadiusDeg']
    assert frozen['directionSamplesPerAtmosphereTargetConfiguration'] == 33
    assert frozen['atmosphereTargetConfigurationCount'] == 6
    assert frozen['totalDirectionalCases'] == 198
    assert frozen['photonHistoriesPerDirectionalCase'] == 5_000_000
    assert frozen['totalPhotonHistories'] == 990_000_000
    assert frozen['candidateSeedCount'] == 198
    assert frozen['candidateSeedCanonicalSha256'] == prior['candidateSeedCanonicalSha256']
    assert frozen['candidateSeedRowsCanonicalSha256'] == prior['candidateRowsCanonicalSha256']
    assert frozen['candidateSeedLiteralsMustNotBeLogged'] is True
    assert frozen['uvspecSha256'] == c['runtimeAndAtmosphere']['uvspecSha256']
    assert frozen['libRadtranDataTreeSha256'] == c['runtimeAndAtmosphere']['libRadtranDataTreeSha256']
    assert frozen['scientificDesignChangedFromExec001'] is False

    result = a['resultContract']
    assert result['acceptanceThreshold'] is None
    assert result['resultDependentPointSourceAcceptanceForbidden'] is True
    assert result['finiteMoonDiskValidatedByThisExecution'] is False
    assert result['mandatorySpectralFollowOnRequiredBeforeAnyBroadbandFiniteDiskAdequacyClaim'] is True
    assert result['mandatorySpectralFollowOnWavelengthsNm'] == [450.0, 650.0, 750.0]
    assert result['allSixConfigurationsRequiredInSpectralFollowOn'] is True
    assert result['applicationInterpretationMustUsePreregisteredStarsvisibilityGate'] is True

    rules = a['oneShotRules']
    assert rules['githubRunAttemptMustEqual'] == 1
    assert rules['githubRerunForbidden'] is True
    assert rules['retryForbidden'] is True
    assert rules['resumeForbidden'] is True
    assert rules['seedMappingAllocatedOnlyToThisExecutionIdentityAfterReviewPass'] is True
    assert rules['seedReuseForbiddenAfterAnyExecutionAttempt'] is True
    assert rules['resultOpeningOnlyThroughFrozenEvaluator'] is True
    assert rules['fullPaginatedIssue60ReleaseBarrierRequired'] is True

    authorization = a['authorization']
    assert authorization['candidateSeedUniverseAllocatedToExecutionIdentityAfterSolverFreeReviewPass'] is True
    assert authorization['scientificSolverExecutionAuthorizedAfterSolverFreeReviewPass'] is True
    assert authorization['dispatchCreated'] is False
    assert authorization['freshIssue60FenceCheckRequiredImmediatelyBeforeDispatchMutation'] is True
    assert authorization['authorizationTimeRepositoryGlobalRecheckAlreadyPassedForBoundCandidateUniverse'] is True
    assert authorization['controlProofItselfAuthorizesNoDispatch'] is True

    assert all(value is False for value in a['protectedBoundaries'].values())
    print('lunar finite-disk exec002 authorization tests passed')


if __name__ == '__main__':
    main()
