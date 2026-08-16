#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED_RECOVERY_SHA = 'b8b58b5877a4a9c01e3d63b478900b29cd81225ceb3137b0e1396775d3d22e93'
EXPECTED_MATERIALIZER_SHA = 'f7cb19d2bdbb66977d5061d5ec23c8cfde4263ba95f63cc9550af90d7c7d0dfc'
EXPECTED_AUDITOR_SHA = '2b32f49de789e85653a07f71b5018d3270dd53878740fccb9b50ec727ce926f8'


def req(c: bool, m: str) -> None:
    if not c:
        raise SystemExit(m)


def load(path: Path) -> dict[str, Any]:
    v = json.loads(path.read_text(encoding='utf-8')); req(isinstance(v, dict), f'object required: {path}'); return v


def csha(v: dict[str, Any], omit: str) -> str:
    b = dict(v); b.pop(omit, None)
    return hashlib.sha256(json.dumps(b, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def fsha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path: Path) -> str:
    raw = path.read_bytes(); return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


r = load(HERE / 'recovery-v1.json')
req(r['recoveryContractSha256'] == csha(r, 'recoveryContractSha256') == EXPECTED_RECOVERY_SHA, 'recovery contract self-hash drift')
req(r['status'] == 'REVIEW_ONLY_POST_SELECTION_MODEL_MATERIALIZATION_NO_RESELECTION', 'recovery status drift')
req(r['governance'] == 'MYSTIC-STATE-0071', 'governance drift')
req(r['sourceMainAtReview'] == '4204b925b18346f4325682528b511b6d67378665', 'source main drift')
e = r['sourceSelectionEvidence']
req((e['fitRunId'], e['fitRunAttempt'], e['fitJobId'], e['authorizationHeadSha']) == (31924262989, 1, 95109323854, 'bd568ada4e05dea6bcf68223778a5d4f6a0fce56'), 'source fit identity drift')
req(e['fitStepConclusion'] == e['independentAuditStepConclusion'] == 'success' and e['workflowConclusion'] == 'failure', 'source step conclusions drift')
req(e['workflowFailureReason'] == 'SHALLOW_CHECKOUT_MISSING_PARENT_FOR_HEAD_CARET', 'source failure classification drift')
req(e['auditedSelectionStatus'] == 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', 'audited verdict drift')
req(e['auditedEligibleCandidateCount'] == 145 and e['selectedCandidateId'] == 'resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1', 'selected evidence drift')
req(e['selectedSpec'] == {
    'familyId':'ridge-primary-local-residual-idw-shape-fixed-idw','kind':'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW','complexityRank':9,
    'primaryBasis':'PHYSICAL_COMPACT_16_TERMS','primaryRidge':1e-5,'shapeCoordinates':'V1_IDW_COS_COORDINATES','shapeNeighbors':4,'shapePower':1.0,
    'residualCoordinateSystem':'V1_IDW_COS_COORDINATES','residualNeighbors':6,'residualPower':1.0,'residualShrinkage':1.0,
}, 'selected spec drift')
t = r['trainingSource']
req(t == {
    'sourceRunId':31827007009,'sourceRunAttempt':1,'sourceHeadSha':'6ffae96ad6054d380f26e6d3a2d17917ba01900f','artifactId':9229229366,
    'artifactName':'level-b-v2-training-fit-v3-densified58-6ffae96ad6054d380f26e6d3a2d17917ba01900f','artifactDigest':'sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a',
    'datasetMember':'training-representation-dataset-v3-densified58.json','datasetMemberByteSha256':'1cf31f1a80ce4ae1f39b9e750616093f6cfa927d10e258f81fe9fc0e58f0ea69',
    'datasetCanonicalSha256':'58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435','trainingGeometryCount':58,'protectedHoldoutRecordCount':0,
}, 'training source drift')
s = r['sourceBindings']
for field, path_field in (
    ('prefitV2GitBlobSha','prefitV2Path'),('implementationDescriptorGitBlobSha','implementationDescriptorPath'),('engineGitBlobSha','enginePath'),('trainerGitBlobSha','trainerPath')):
    p = ROOT / s[path_field]; req(p.is_file(), f'missing bound source: {p}'); req(blob(p) == s[field], f'Git blob drift: {field}')
req(fsha(ROOT / s['enginePath']) == s['engineSourceSha256'], 'engine source hash drift')
req(fsha(ROOT / s['trainerPath']) == s['trainerSourceSha256'], 'trainer source hash drift')
prefit = load(ROOT / s['prefitV2Path']); impl = load(ROOT / s['implementationDescriptorPath'])
req(prefit['protocolSha256'] == csha(prefit, 'protocolSha256') == s['prefitV2CanonicalSha256'], 'prefit canonical drift')
req(impl['descriptorSha256'] == csha(impl, 'descriptorSha256') == s['implementationDescriptorCanonicalSha256'], 'implementation descriptor drift')
sem = r['materializationSemantics']
for k in ('candidateSearchAuthorized','candidateEnumerationAuthorized','crossValidationAuthorized','gateReevaluationAuthorized','rankingAuthorized','selectionChangeAuthorized','selectedSpecMayChange','selectedCandidateIdMayChange','shapePredictorMayChange','trainingDataMayChange','newMysticSolverExecutionAuthorized','ordinal27MayBeRead','protectedValidationAuthorized','protectedValuesMayBeRead','productionPromotionAuthorized','workerBLaneReactivated','workerCLaneReactivated'):
    req(sem[k] is False, f'forbidden materialization surface opened: {k}')
req(sem['selectedFinalModelFitOnAll58TrainingRecordsAuthorized'] is True and sem['selectedModelReconstructionMustBeDeterministic'] is True, 'materialization permission drift')
a = r['authorizationAndDispatch']
req(a['oneFileDraftAuthorizationRequired'] and a['authorizationMustBeDirectChildOfLiveMain'] and a['automaticDispatch'] is False, 'authorization shape drift')
req(a['authorizationReviewRunAttemptRequired'] == a['materializationRunAttemptRequired'] == 1, 'attempt drift')
req(a['githubRerunAllowed'] is False and a['retryAllowed'] is False and a['resumeAllowed'] is False, 'retry boundary opened')
req(fsha(HERE / 'materialize_selected_v1.py') == EXPECTED_MATERIALIZER_SHA, 'materializer source SHA drift')
req(fsha(HERE / 'audit_materialization_v1.py') == EXPECTED_AUDITOR_SHA, 'auditor source SHA drift')
for path in (HERE / 'materialize_selected_v1.py', HERE / 'audit_materialization_v1.py'):
    text = path.read_text(encoding='utf-8')
    for forbidden in ('candidate_specs(', 'folds58(', 'evaluate_all(', 'generic_evaluate(', 'select_candidate(', 'evaluate_candidate58('):
        req(forbidden not in text, f'reselection surface found in {path.name}: {forbidden}')
print('PASS: selected-model materialization recovery is source-bound, audited-verdict-bound, and contains no candidate/CV/ranking reselection surface')
