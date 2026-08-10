#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FILES = {
    'protocol': 'full-spectrum-estimator-pilot-preregistration-v2.json',
    'executionManifest': 'full-spectrum-estimator-pilot-execution-manifest-v4.json',
    'normalizer': 'normalize_full_spectrum_estimator_pilot_results_v6.py',
    'analysis': 'analyze_full_spectrum_estimator_pilot_v4.py',
    'renderer': 'render_full_spectrum_estimator_pilot_inputs_v5.py',
    'rendererReport': 'rendered-review-v5/renderer-review-report.json',
    'seedAudit': 'full-spectrum-estimator-pilot-seed-collision-audit-v4.json',
    'identityAudit': 'full-spectrum-estimator-pilot-identity-collision-audit-v4.json',
    'acquisitionContract': 'full-spectrum-estimator-pilot-acquisition-contract-v4.json',
    'grid': 'wavelength-grid-1nm.dat',
    'physicalAudit': 'full-spectrum-estimator-pilot-physical-input-audit-v1.json',
    'integrationCore': 'build_full_spectrum_training_handoff.py',
    'sourceAdmissionReport': 'full-spectrum-training-admission-complete-v1.json',
    'preauthorizationGuard': 'full_spectrum_estimator_pilot_preauthorization_guard_v2.py',
}
OUT = ROOT / 'full-spectrum-estimator-pilot-preauthorization-contract-v2.json'


def raw(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def canon(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


protocol = json.loads((ROOT / FILES['protocol']).read_text())
execution = json.loads((ROOT / FILES['executionManifest']).read_text())
report = json.loads((ROOT / FILES['rendererReport']).read_text())
seed = json.loads((ROOT / FILES['seedAudit']).read_text())
identity = json.loads((ROOT / FILES['identityAudit']).read_text())
acquisition = json.loads((ROOT / FILES['acquisitionContract']).read_text())
admission = json.loads((ROOT / FILES['sourceAdmissionReport']).read_text())

expected = {
    'protocol': ('protocolSha256', '7ca0923204452ab203249dfd060dd5fef5465c48a20ba529c0a20748e0152434', protocol),
    'execution': ('manifestSha256', 'be81c717cd943415ac51dc2b5356010b3d584b5279228c525d2defccc4680e0f', execution),
    'renderer': ('reportSha256', 'f6658e9d7a19fb5c6ec7acfc2a6be12b608445e9a75aee100c80426cba31efa1', report),
    'seed': ('auditSha256', 'e0f4c61c0d1920e115a72aae12cfc4ff00ee596dbe1173dc78314ac085e7a538', seed),
    'identity': ('auditSha256', 'fc08e3abc3fb2ae1ef0ad5d72982141fd538610f2de8d3e0f174599f692ed620', identity),
    'acquisition': ('contractSha256', 'd14e03e12cb4c045fc7d19f94a73bd13101c51b4ac758210f89e89cf1c70dee6', acquisition),
    'admission': ('reportSha256', 'a043fa6c0a5e7ec282d887a4febe01277e0a0a20c82bff65ccb127705b40e0cf', admission),
}
for label, (key, wanted, value) in expected.items():
    if value.get(key) != wanted:
        raise SystemExit(f'{label} self-hash drift')
    if canon({k: v for k, v in value.items() if k != key}) != wanted:
        raise SystemExit(f'{label} canonical self-hash mismatch')

if execution.get('caseCount') != 44 or execution.get('configuredPhotonHistoriesSum') != 5_600_000_000:
    raise SystemExit('execution design drift')
if report.get('caseCount') != 44 or report.get('allPhysicalFingerprintsMatchHistorical') is not True:
    raise SystemExit('renderer evidence drift')
if (seed.get('exactSourceUniverse', {}).get('sourceSeedCount') != 166
        or seed.get('exactSourceUniverse', {}).get('sourceUniqueSeedCount') != 166
        or seed.get('candidateUniverse', {}).get('candidateSeedCount') != 44
        or seed.get('candidateUniverse', {}).get('candidateUniqueSeedCount') != 44
        or seed.get('collisionResults', {}).get('sourceCandidateSeedIntersectionCount') != 0):
    raise SystemExit('seed audit universe drift')
if identity.get('candidateIdentity', {}).get('globalScientificOrdinal') != 14:
    raise SystemExit('candidate identity drift')

body = {
    'schemaVersion': 1,
    'contractId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-contract-v2',
    'status': 'REVIEW_ONLY_FAIL_CLOSED_NOT_AN_AUTHORIZATION',
    'repository': 'search-maker/twilight-mystic-experiments',
    'protocolId': protocol['protocolId'],
    'protocolSha256': protocol['protocolSha256'],
    'executionManifestId': execution['manifestId'],
    'executionManifestSha256': execution['manifestSha256'],
    'candidateIdentity': identity['candidateIdentity'],
    'latestKnownConsumedScientificOrdinal': 13,
    'latestKnownConsumedScientificRun': 31070968611,
    'reviewedPreparationMainSha': identity['liveMainAtAudit'],
    'staticFileRawSha256': {key: raw(rel) for key, rel in FILES.items()},
    'staticEvidenceSelfHashes': {
        'rendererReport': report['reportSha256'],
        'rendererCasesCanonicalSha256': report['casesCanonicalSha256'],
        'seedAudit': seed['auditSha256'],
        'identityAudit': identity['auditSha256'],
        'acquisitionContract': acquisition['contractSha256'],
        'sourceAdmissionReport': admission['reportSha256'],
    },
    'requiredFreshPreauthorizationContext': {
        'issue60RefreshRequired': True,
        'noSupersedingDirectiveRequired': True,
        'packagePublishedToDedicatedReviewBranchRequired': True,
        'reviewPrRequired': True,
        'reviewChecksPassedRequired': True,
        'reviewHeadFileHashesMustMatchStaticFileRawSha256': True,
        'liveMainMustEqualReviewedBaseMainAtAuthorization': True,
        'candidateExecutionKeyCodeIssuePrCollisionCountExactly': 0,
        'candidateAuthorizationBranchCurrentExists': False,
        'candidateDispatchBranchCurrentExists': False,
        'candidateAuthorizationBranchHistoricalRunCountExactly': 0,
        'candidateDispatchBranchHistoricalRunCountExactly': 0,
        'candidateExactCaseArtifactCountExactly': 0,
        'candidateTerminalArtifactCountExactly': 0,
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
        'screeningDataMayNotBecomeFinalConfirmationData': True,
        'modelFittingAuthorized': False,
        'holdoutOpeningAuthorized': False,
        'tier2Authorized': False,
        'productionAuthorization': False,
    },
    'supersedesLocalPreauthorizationContract': {
        'contractId': 'public-tier1-full-spectrum-estimator-pilot-preauthorization-contract-v1',
        'contractSha256': '34fec92fa75fb2e42123ffe3995f7f3a4b4f04224059f30ff8e12dfe45157e60',
        'executionOccurred': False,
        'authorizationOccurred': False,
        'reason': 'v1 was bound to pre-v4 execution/renderer evidence and was never published or used; v2 binds the complete current review surface and portable guard dependencies before publication',
    },
    'authorizationPermittedByThisContract': False,
    'dispatchPermittedByThisContract': False,
    'solverExecutionPerformed': False,
}
body['contractSha256'] = canon(body)
OUT.write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + '\n')
print(json.dumps({'contractSha256': body['contractSha256'], 'rawSha256': raw(OUT.name), 'staticFileCount': len(FILES)}, indent=2))
