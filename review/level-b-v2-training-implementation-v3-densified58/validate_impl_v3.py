#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
IMPL = HERE / 'implementation-v3.json'
PREFIT = ROOT / 'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json'
G2_TRAIN = ROOT / 'review/level-b-v2-training-implementation-v2/train_v2.py'
G2_PROTOCOL = ROOT / 'review/level-b-v2-training-prefit-freeze-v2/protocol-v2.json'
G2_RESULT = ROOT / 'review/level-b-v2-training-fit-result-v2/result-v2.json'
REP_ANALYZER = ROOT / 'review/core-training-spectral-representation-v2/analyze_v2.py'
PREREG = ROOT / 'review/mystic-state-0069-local-training-densification-v1/protocol-v1.json'
EXEC = ROOT / 'review/mystic-state-0069-ordinal23-result-v1/result-v1.json'
EXPECTED = {
    PREFIT: '42a3e1cc6974c03e1f659d5f886b664cfa23cf6a',
    G2_TRAIN: 'bd0d20ebaaf77a8780dbfa021cfaa49bf3e2d0be',
    G2_PROTOCOL: '91ab4c109a209d3ee9ee24e327c554739cd9dd6c',
    G2_RESULT: '70161120e96afa3bbfd7a16239f8233ad159e266',
    REP_ANALYZER: 'a82188dab1377c1af33ce0c4c23fa0a382f2978f',
    PREREG: 'd47bceb9b415ca8ebf14f6014207fd1310b4809c',
    EXEC: '958fbfa72d36cad0082075d9048a7a1caa2fadcd',
}


def req(condition, message):
    if not condition:
        raise SystemExit('REFUSED: ' + message)


def blob(path: Path) -> str:
    return subprocess.check_output(['git', 'rev-parse', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT, text=True).strip()


d = json.loads(IMPL.read_text())
req((d.get('schemaVersion'), d.get('implementationId'), d.get('status'), d.get('governance')) == (3, 'level-b-v2-training-implementation-v3-densified58', 'REVIEW_ONLY_DENSIFIED58_IMPLEMENTATION_SYNTHETIC_ONLY_NO_ORDINAL23_VALUES_READ', 'MYSTIC-STATE-0069'), 'implementation identity drift')
req(d.get('sourceMainAtImplementationReview') == 'd32ed0c6a123d140f7a4ec24e571ddb0a11b2f12', 'implementation base drift')
for path, expected in EXPECTED.items():
    req(blob(path) == expected, f'git blob drift: {path}')

p = d['prefitFreeze']
req((p['protocolGitBlobSha'], p['protocolSha256'], p['trainingGeometryCount'], p['sourceCaseCount'], p['candidateCount'], p['cvFoldCount']) == ('42a3e1cc6974c03e1f659d5f886b664cfa23cf6a', 'eaf8d1d047fa5a336027a18b3cddd015943f4a28fd58c568fac233f819baaf73', 58, 166, 230, 73), 'prefit binding drift')

g = d['inheritedGeneration2Engine']
req((g['trainerGitBlobSha'], g['protocolGitBlobSha'], g['terminalResultGitBlobSha'], g['terminalResultRemainsFailed']) == ('bd0d20ebaaf77a8780dbfa021cfaa49bf3e2d0be', '91ab4c109a209d3ee9ee24e327c554739cd9dd6c', '70161120e96afa3bbfd7a16239f8233ad159e266', True), 'generation2 engine binding drift')

r = d['representationExtension']
req((r['legacyRepresentationArtifactId'], r['legacyDatasetCanonicalSha256'], r['representationPackageSha256'], r['representationAnalyzerGitBlobSha']) == (9208203541, 'bb7908426d9d545f43c082aebbaab1829a486e2962d0b9ee34a5e8bef5390133', '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763', 'a82188dab1377c1af33ce0c4c23fa0a382f2978f'), 'representation binding drift')
for key in ('basisRefitAllowed', 'integrationWeightRecomputationAllowed', 'pcaRecomputationAllowed'):
    req(r[key] is False, f'representation boundary opened: {key}')
req(r['legacy44RecordsMustRemainValueExact'] is True, 'legacy record mutation allowed')

o = d['ordinal23TrainingSource']
req((o['workflowRunId'], o['workflowRunAttempt'], o['headSha'], o['inventoryArtifactId'], o['inventorySelfSha256'], o['manifestSha256']) == (31814698818, 1, '5eead3cd62ce08a016dcc1b4126d66b4f7dfdbf0', 9224754905, 'ae2356b618679cd33cefd3115ca23cd8eff6091be5f936fc93f0fcf609a99455', 'eb1817b25a59af305076f0afa24d5f6ba6f4571fb4748ed638071edc4557f2ea'), 'ordinal23 source binding drift')
req(o['ordinal22ValuesMayBeRead'] is False, 'ordinal22 source opened')

review = d['reviewSurface']
for key in ('pullRequestMayDownloadLegacyRealArtifact', 'pullRequestMayDownloadOrdinal23CaseArtifacts', 'pullRequestMayReadOrdinal23ScientificValues', 'pullRequestMayExecuteRealSelectionOrFit'):
    req(review[key] is False, f'review boundary opened: {key}')
req(review['pullRequestMayExecuteSyntheticFits'] is True and review['reviewJobActionsPermission'] == 'NONE', 'synthetic review contract drift')

a = d['activationSurface']
req((a['activationBranch'], a['activationFile'], a['githubRunAttemptRequired'], a['githubRerunRetryResumeAllowed']) == ('postprocess/level-b-v2-training-fit-v3-densified58', 'review/level-b-v2-training-implementation-v3-densified58/activation.json', 1, False), 'activation identity drift')
req(a['activationMustBeDirectChildOfLiveMain'] is True and a['activationDiffMustContainOnlyActivationFile'] is True, 'activation freshness guard drift')
req(a['activationMayOpenOrdinal23TrainingValues'] is True and a['activationMayReadOrdinal22'] is False and a['activationMayExecuteMystic'] is False, 'activation scientific boundary drift')

b = d['boundaries']
req(b['generation2ResultRemainsFailed'] is True and b['freshProtectedValidationSourceRequiredAfterAnyModelFreeze'] is True, 'historical/future validation boundary drift')
for key in ('ordinal22ValuesMayBeRead', 'protectedValidationAuthorized', 'newMysticSolverExecutionAuthorized', 'productionPromotionAuthorized', 'workerBLaneReactivated', 'workerCLaneReactivated'):
    req(b[key] is False, f'closed boundary opened: {key}')

print('VALID_DENSIFIED58_IMPLEMENTATION_V3_BINDING')
