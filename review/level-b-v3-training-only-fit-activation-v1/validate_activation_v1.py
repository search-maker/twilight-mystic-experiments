#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED_CONTRACT_SHA = 'd7615323b94e5eca205277d6c7759f4241fa919b3b93bc899c7d829e3860fec1'


def req(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def canonical_sha(value: dict[str, Any], field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


c = load(HERE / 'activation-contract-v1.json')
req(c['contractSha256'] == canonical_sha(c, 'contractSha256') == EXPECTED_CONTRACT_SHA, 'activation contract self-hash drift')
req(c['activationId'] == 'level-b-v3-training-only-fit-activation-v1', 'activation id drift')
req(c['status'] == 'REVIEW_ONLY_ONE_USE_TRAINING_FIT_ACTIVATION_NO_DISPATCH', 'activation status drift')
req(c['governance'] == 'MYSTIC-STATE-0071', 'governance drift')
req(c['sourceMainAtReview'] == '9634ec2cb9c4481c13fe1c9e4b6e3cdf9a89898a', 'source main drift')
req(c['branches'] == {
    'review': 'review/level-b-v3-training-only-fit-activation-v1',
    'authorization': 'authorization/level-b-v3-training-only-fit-v1',
    'fit': 'fit/level-b-v3-training-only-v1',
}, 'branch identity drift')

s = c['sourceBindings']
paths = {
    'prefitV2GitBlobSha': ROOT / s['prefitV2Path'],
    'implementationDescriptorGitBlobSha': ROOT / s['implementationDescriptorPath'],
    'engineGitBlobSha': ROOT / s['enginePath'],
    'trainerGitBlobSha': ROOT / s['trainerPath'],
}
for field, path in paths.items():
    req(path.is_file(), f'missing bound source: {path}')
    req(blob_sha(path) == s[field], f'Git blob drift: {field}')
req(file_sha(ROOT / s['enginePath']) == s['engineSourceSha256'], 'engine byte SHA drift')
req(file_sha(ROOT / s['trainerPath']) == s['trainerSourceSha256'], 'trainer byte SHA drift')
prefit = load(ROOT / s['prefitV2Path'])
impl = load(ROOT / s['implementationDescriptorPath'])
req(prefit['protocolSha256'] == canonical_sha(prefit, 'protocolSha256') == s['prefitV2CanonicalSha256'], 'prefit canonical hash drift')
req(impl['descriptorSha256'] == canonical_sha(impl, 'descriptorSha256') == s['implementationDescriptorCanonicalSha256'], 'implementation descriptor hash drift')
req(prefit['candidateDefinition']['candidateCountRequired'] == c['frozenFit']['candidateCount'] == 145, 'candidate count drift')
req(prefit['candidateDefinition']['newFamily']['candidateCount'] == c['frozenFit']['changedCandidateCount'] == 144, 'changed candidate count drift')
req(prefit['crossValidation']['totalFoldCountRequired'] == c['frozenFit']['cvFoldCount'] == 73, 'CV fold count drift')
req(prefit['sourceBindings']['expandedDatasetSha256'] == c['trainingSource']['datasetCanonicalSha256'], 'dataset canonical binding drift')
req(prefit['roleIsolation']['trainingGeometryCountRequired'] == c['trainingSource']['trainingGeometryCount'] == 58, 'training geometry count drift')
req(prefit['roleIsolation']['protectedRecordCountRequired'] == c['trainingSource']['protectedHoldoutRecordCount'] == 0, 'protected record count drift')

t = c['trainingSource']
expected_training = {
    'workflowRunId': 31827007009,
    'workflowRunAttempt': 1,
    'workflowConclusion': 'success',
    'workflowHeadSha': '6ffae96ad6054d380f26e6d3a2d17917ba01900f',
    'artifactId': 9229229366,
    'artifactName': 'level-b-v2-training-fit-v3-densified58-6ffae96ad6054d380f26e6d3a2d17917ba01900f',
    'artifactDigest': 'sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a',
    'datasetMember': 'training-representation-dataset-v3-densified58.json',
    'datasetMemberByteSha256': '1cf31f1a80ce4ae1f39b9e750616093f6cfa927d10e258f81fe9fc0e58f0ea69',
    'datasetCanonicalSha256': '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435',
    'trainingGeometryCount': 58,
    'protectedHoldoutRecordCount': 0,
}
req(t == expected_training, 'training source identity drift')
req(c['frozenFit']['pythonVersion'] == '3.12.4' and c['frozenFit']['numpyVersion'] == '2.3.2', 'runtime drift')
a = c['authorizationAndDispatch']
req(a['authorizationPath'] == 'review/level-b-v3-training-only-fit-activation-v1/authorization-v1.json', 'authorization path drift')
req(a['oneFileDraftAuthorizationRequired'] and a['authorizationMustBeDirectChildOfLiveMain'], 'authorization shape weakened')
req(a['authorizationReviewRunAttemptRequired'] == a['fitRunAttemptRequired'] == 1, 'attempt identity drift')
req(a['automaticDispatch'] is False and a['githubRerunAllowed'] is False and a['retryAllowed'] is False and a['resumeAllowed'] is False, 'one-use boundary weakened')
req(a['markerPrefix'] == 'AUTHORIZED-LEVEL-B-V3-TRAINING-ONLY-FIT | MYSTIC-STATE-0071 | ', 'marker prefix drift')

r = c['reviewBoundaries']
req(r == {
    'activationReviewMayDownloadTrainingArtifact': False,
    'activationReviewMayFit': False,
    'activationReviewMayReadOrdinal27': False,
    'authorizationReviewMayDownloadExactTrainingArtifact': True,
    'authorizationReviewMayFit': False,
    'authorizationReviewMayReadOrdinal27': False,
}, 'review boundaries drift')
f = c['fitBoundaries']
req(f['trainingArtifactMayBeRead'] is True and f['exactTrainingArtifactOnly'] is True, 'training source access drift')
for key in (
    'newMysticSolverExecutionAuthorized', 'protectedValidationAuthorized', 'protectedValuesMayBeRead',
    'ordinal27MayBeRead', 'newTrainingDataAuthorized', 'thresholdChangeAuthorized', 'supportChangeAuthorized',
    'productionPromotionAuthorized', 'workerBLaneReactivated', 'workerCLaneReactivated',
):
    req(f[key] is False, f'closed fit boundary opened: {key}')
d = c['resultDisposition']
req(d['ifNoEligibleCandidate'] == 'TERMINATE_0071_NO_ELIGIBLE_TRAINING_ONLY_MODEL_NO_NEW_VALIDATION', 'no-eligible exit drift')
req(d['ifControlWins'] == 'TERMINATE_0071_NO_TRAINING_ONLY_EVIDENCE_FOR_CHANGE_NO_NEW_VALIDATION', 'control exit drift')
req(d['ifChangedCandidateWins'] == 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', 'changed-win exit drift')
req(d['futureProtectedValidationRequiresSeparateGovernance'] and d['futureRetunedValidationMustUseCompletelyFreshUntouchedSource'] and d['ordinal27RemainsDiagnosticOnly'], 'future validation boundary weakened')
print('PASS: MYSTIC-STATE-0071 one-use training-only fit activation is exact-source-bound, prefit/implementation-bound, and protected-science closed')
