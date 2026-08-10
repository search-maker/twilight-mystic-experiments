#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SystemExit(f'expected JSON object: {path}')
    return value


def build(root: Path) -> dict[str, Any]:
    files = {
        'protocol': 'full-spectrum-estimator-pilot-preregistration-v2.json',
        'screeningAnalysisProtocol': 'full-spectrum-estimator-pilot-screening-analysis-preregistration-v4.json',
        'executionManifest': 'full-spectrum-estimator-pilot-execution-manifest-v4.json',
        'normalizer': 'normalize_full_spectrum_estimator_pilot_results_v6.py',
        'analysis': 'analyze_full_spectrum_estimator_pilot_v6.py',
        'renderer': 'render_full_spectrum_estimator_pilot_inputs_v5.py',
        'rendererReport': 'rendered-review-v5/renderer-review-report.json',
        'seedAudit': 'full-spectrum-estimator-pilot-seed-collision-audit-v4.json',
        'identityAudit': 'full-spectrum-estimator-pilot-identity-collision-audit-v4.json',
        'acquisitionContract': 'full-spectrum-estimator-pilot-acquisition-contract-v4.json',
        'grid': 'wavelength-grid-1nm.dat',
        'physicalAudit': 'full-spectrum-estimator-pilot-physical-input-audit-v1.json',
        'integrationCore': 'build_full_spectrum_training_handoff.py',
        'sourceAdmissionReport': 'full-spectrum-training-admission-complete-v1.json',
        'preauthorizationGuard': 'full_spectrum_estimator_pilot_preauthorization_guard_v4.py',
        'reviewCheckRunner': 'run_review_checks.py',
        'analysisTest': 'test_full_spectrum_estimator_pilot_analysis_v6.py',
        'artifactContractTest': 'test_full_spectrum_estimator_pilot_artifact_contract_v5.py',
        'directiveSurfaceTest': 'test_full_spectrum_estimator_pilot_directive_surface_v6.py',
        'frozenEvidenceTest': 'test_full_spectrum_estimator_pilot_frozen_evidence_verifiers_v1.py',
        'preauthorizationTest': 'test_full_spectrum_estimator_pilot_preauthorization_guard_v4.py',
        'protocolTest': 'test_full_spectrum_estimator_pilot_protocol_v2.py',
        'portabilityTest': 'test_full_spectrum_estimator_pilot_review_portability_v1.py',
        'acquisitionVerifier': 'verify_full_spectrum_estimator_pilot_acquisition_contract_v4.py',
        'executionVerifier': 'verify_full_spectrum_estimator_pilot_execution_manifest_v4.py',
        'identityVerifier': 'verify_full_spectrum_estimator_pilot_identity_collision_audit_v4.py',
        'seedVerifier': 'verify_full_spectrum_estimator_pilot_seed_collision_audit_v4.py',
    }
    for rel in files.values():
        if not (root / rel).is_file():
            raise SystemExit(f'missing static review file: {rel}')

    protocol = load(root / files['protocol'])
    analysis_protocol = load(root / files['screeningAnalysisProtocol'])
    execution = load(root / files['executionManifest'])
    report = load(root / files['rendererReport'])
    seed = load(root / files['seedAudit'])
    identity = load(root / files['identityAudit'])
    acquisition = load(root / files['acquisitionContract'])
    admission = load(root / files['sourceAdmissionReport'])

    checks = [
        (protocol, 'protocolSha256'),
        (analysis_protocol, 'analysisProtocolSha256'),
        (execution, 'manifestSha256'),
        (report, 'reportSha256'),
        (seed, 'auditSha256'),
        (identity, 'auditSha256'),
        (acquisition, 'contractSha256'),
        (admission, 'reportSha256'),
    ]
    for value, key in checks:
        if value.get(key) != canon({k: v for k, v in value.items() if k != key}):
            raise SystemExit(f'{key} canonical self-hash mismatch')

    if (
        analysis_protocol['acquisitionProtocolSha256'] != protocol['protocolSha256']
        or analysis_protocol['executionManifestSha256'] != execution['manifestSha256']
        or analysis_protocol['sourceAdmissionReportSha256'] != admission['reportSha256']
    ):
        raise SystemExit('analysis protocol binding drift')
    if execution.get('caseCount') != 44 or execution.get('configuredPhotonHistoriesSum') != 5_600_000_000:
        raise SystemExit('execution design drift')
    if report.get('caseCount') != 44 or report.get('allPhysicalFingerprintsMatchHistorical') is not True:
        raise SystemExit('renderer evidence drift')

    runner = root / files['reviewCheckRunner']
    test_modules = [
        'test_full_spectrum_estimator_pilot_analysis_v6',
        'test_full_spectrum_estimator_pilot_artifact_contract_v5',
        'test_full_spectrum_estimator_pilot_directive_surface_v6',
        'test_full_spectrum_estimator_pilot_frozen_evidence_verifiers_v1',
        'test_full_spectrum_estimator_pilot_preauthorization_guard_v4',
        'test_full_spectrum_estimator_pilot_protocol_v2',
        'test_full_spectrum_estimator_pilot_review_portability_v1',
    ]

    static_files = {
        key: {'path': rel, 'rawSha256': raw(root / rel)} for key, rel in files.items()
    }
    body = {
        'schemaVersion': 1,
        'contractId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-contract-v4',
        'status': 'REVIEW_ONLY_FAIL_CLOSED_NOT_AN_AUTHORIZATION',
        'repository': 'search-maker/twilight-mystic-experiments',
        'protocolId': protocol['protocolId'],
        'protocolSha256': protocol['protocolSha256'],
        'screeningAnalysisProtocolId': analysis_protocol['analysisProtocolId'],
        'screeningAnalysisProtocolSha256': analysis_protocol['analysisProtocolSha256'],
        'executionManifestId': execution['manifestId'],
        'executionManifestSha256': execution['manifestSha256'],
        'candidateIdentity': identity['candidateIdentity'],
        'latestKnownConsumedScientificOrdinal': 13,
        'latestKnownConsumedScientificRun': 31070968611,
        'reviewedPreparationMainSha': identity['liveMainAtAudit'],
        'staticFiles': static_files,
        'staticEvidenceSelfHashes': {
            'rendererReport': report['reportSha256'],
            'rendererCasesCanonicalSha256': report['casesCanonicalSha256'],
            'seedAudit': seed['auditSha256'],
            'identityAudit': identity['auditSha256'],
            'acquisitionContract': acquisition['contractSha256'],
            'sourceAdmissionReport': admission['reportSha256'],
            'screeningAnalysisBaseline': analysis_protocol['historicalFirstTwoScreeningBaseline']['geometryBaselinesCanonicalSha256'],
        },
        'reviewPackageCiContract': {
            'workflowPath': '.github/workflows/contract.yml',
            'jobName': 'non-scientific-contract',
            'checkRunnerPath': 'review/full-spectrum-estimator-pilot-v2/run_review_checks.py',
            'checkRunnerRawSha256': raw(runner),
            'expectedTestCount': 39,
            'testModules': test_modules,
            'workflowRunAttemptExactly': 1,
            'scientificExecutionPerformed': False,
        },
        'requiredFreshPreauthorizationContext': {
            'issue60RefreshRequired': True,
            'noSupersedingDirectiveRequired': True,
            'packagePublishedToDedicatedReviewBranchRequired': True,
            'reviewPrRequired': True,
            'reviewPackageCiMustPassOnExactHead': True,
            'liveMainMustEqualReviewedBaseMainAtAuthorization': True,
            'candidateExecutionKeyCodeIssuePrCollisionCountExactly': 0,
            'candidateAuthorizationBranchCurrentExists': False,
            'candidateDispatchBranchCurrentExists': False,
            'candidateAuthorizationBranchHistoricalRunCountExactly': 0,
            'candidateDispatchBranchHistoricalRunCountExactly': 0,
            'candidateExactCaseArtifactCountExactly': 0,
            'candidateTerminalArtifactCountExactly': 0,
            'candidateGlobalOrdinalExactly': 14,
            'latestConsumedScientificOrdinalExactly': 13,
            'candidateGlobalOrdinalReservationCountExactly': 0,
            'candidateGlobalOrdinalAuthorizationCountExactly': 0,
            'candidateGlobalOrdinalScientificRunCountExactly': 0,
            'candidateGlobalOrdinalAuthorizationBranchCountExactly': 0,
            'candidateGlobalOrdinalDispatchBranchCountExactly': 0,
            'candidateGlobalOrdinalTerminalArtifactCountExactly': 0,
            'exactHistoricalSourceSeedCount': 166,
            'exactHistoricalUniqueSeedCount': 166,
            'candidateSeedCount': 44,
            'candidateUniqueSeedCount': 44,
            'sourceCandidateSeedIntersectionCount': 0,
            'runtimeIdentityMustMatchExecutionManifest': True,
            'renderer44InputHashesMustMatchReviewedReport': True,
            'rendererCasesCanonicalSha256MustMatchReviewedReport': True,
        },
        'authorizationCreationRules': {
            'preflightMayOnlyPermitCreatingAuthorizationFile': True,
            'authorizationCommitMustBeSeparate': True,
            'authorizationCommitMustBeUnmerged': True,
            'authorizationChangedFileCountExactly': 1,
            'authorizationParentMustEqualReviewedPackageHead': True,
            'authorizationOrdinalExactly': 14,
            'executionKeyMustEqualCandidate': True,
            'authorizationMustNotChangeProtocolManifestRendererAnalysisRuntimeSeedsOrThresholds': True,
            'screeningAnalysisProtocolMustRemainExact': True,
            'freshGlobalOrdinalRecheckMustPass': True,
            'exactReviewPackageCiMustPass': True,
        },
        'dispatchRules': {
            'authorizationCommitGuardMustPassBeforeDispatch': True,
            'workflowRunAttemptExactly': 1,
            'githubRerunAllowed': False,
            'retryAllowed': False,
            'resumeAllowed': False,
            'oneDispatchMaximum': True,
            'duplicateRunGuardMustRunBeforeSyntaxOrSolver': True,
            'runtimeIdentityCheckBeforeSyntaxOrSolver': True,
            'syntaxChecksPerCaseMaximum': 1,
            'solverExecutionsPerCaseMaximum': 1,
            'automaticContinuation': False,
        },
        'scientificBoundary': {
            'pilotScreeningOnly': True,
            'twoBlockRsemInferential': False,
            'sameNHistoricalComparatorRequiredForVarianceGain': True,
            'fullAdaptiveHistoricalRsemForbiddenForVarianceGainThreshold': True,
            'anyPrimaryChannelFreshZeroBlocksCandidateClassification': True,
            'nonProblemPrimaryChannelVarianceNonDegradationRequired': True,
            'screeningDataMayNotBecomeFinalConfirmationData': True,
            'modelFittingAuthorized': False,
            'holdoutOpeningAuthorized': False,
            'tier2Authorized': False,
            'productionAuthorization': False,
        },
        'supersedesPreauthorizationContract': {
            'contractId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-contract-v3',
            'executionOccurred': False,
            'authorizationOccurred': False,
            'pilotResultValuesOpened': False,
            'reason': 'v4 binds the channel-specific zero fix, same-n/non-degradation screening protocol, fresh global-ordinal recheck, and exact review-package CI contract before any pilot result exists.',
        },
        'authorizationPermittedByThisContract': False,
        'dispatchPermittedByThisContract': False,
        'solverExecutionPerformed': False,
    }
    body['contractSha256'] = canon(body)
    return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    body = build(root)
    output = args.output or root / 'full-spectrum-estimator-pilot-preauthorization-contract-v4.json'
    output.write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({
        'contractSha256': body['contractSha256'],
        'rawSha256': raw(output),
        'staticFileCount': len(body['staticFiles']),
        'expectedTestCount': body['reviewPackageCiContract']['expectedTestCount'],
    }, indent=2))


if __name__ == '__main__':
    main()
