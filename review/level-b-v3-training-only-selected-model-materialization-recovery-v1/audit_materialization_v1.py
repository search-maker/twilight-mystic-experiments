#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IMPL = ROOT / 'review/level-b-v3-training-only-implementation-v1'
PREFIT = ROOT / 'review/level-b-v3-training-only-prefit-freeze-v2/protocol-v2.json'
RECOVERY = Path(__file__).resolve().parent / 'recovery-v1.json'
EXPECTED_RECOVERY_SHA = 'b8b58b5877a4a9c01e3d63b478900b29cd81225ceb3137b0e1396775d3d22e93'
EXPECTED_DATASET_SHA = '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435'
EXPECTED_DATASET_BYTE_SHA = '1cf31f1a80ce4ae1f39b9e750616093f6cfa927d10e258f81fe9fc0e58f0ea69'
SELECTED_ID = 'resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1'


def req(c: bool, m: str) -> None:
    if not c:
        raise SystemExit(m)


def load(path: Path) -> dict[str, Any]:
    v = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(v, dict), f'object required: {path}')
    return v


def csha(value: dict[str, Any], omit: str) -> str:
    body = dict(value); body.pop(omit, None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot load {path}')
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try: spec.loader.exec_module(mod)
    finally: sys.path.pop(0)
    return mod


def expected_spec(recovery: dict[str, Any]) -> dict[str, Any]:
    s = recovery['sourceSelectionEvidence']['selectedSpec']
    req(recovery['sourceSelectionEvidence']['selectedCandidateId'] == SELECTED_ID, 'selected candidate evidence drift')
    return {
        'candidateId': SELECTED_ID,
        'familyId': s['familyId'], 'kind': s['kind'], 'complexityRank': s['complexityRank'],
        'primaryBasis': s['primaryBasis'], 'primaryRidge': s['primaryRidge'],
        'neighbors': s['shapeNeighbors'], 'power': s['shapePower'], 'shapeCoordinates': s['shapeCoordinates'],
        'residualCoordinateSystem': s['residualCoordinateSystem'], 'residualNeighbors': s['residualNeighbors'],
        'residualPower': s['residualPower'], 'residualShrinkage': s['residualShrinkage'],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    recovery = load(RECOVERY)
    req(recovery['recoveryContractSha256'] == csha(recovery, 'recoveryContractSha256') == EXPECTED_RECOVERY_SHA, 'recovery hash drift')
    protocol = load(PREFIT)
    raw = args.dataset.read_bytes(); req(hashlib.sha256(raw).hexdigest() == EXPECTED_DATASET_BYTE_SHA, 'dataset byte hash drift')
    dataset = json.loads(raw); body = dict(dataset); h = body.pop('datasetSha256')
    req(h == EXPECTED_DATASET_SHA and hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest() == h, 'dataset canonical drift')
    req(dataset['geometryCount'] == 58 and dataset['protectedHoldoutRecordCount'] == 0 and len(dataset['records']) == 58, 'dataset role drift')
    req([str(r['geometryId']) for r in dataset['records']] == protocol['roleIsolation']['trainingGeometryIds'], 'training IDs drift')
    artifact = load(args.output_dir / 'model-artifact-materialization-v1.json')
    result = load(args.output_dir / 'materialization-result-v1.json')
    req(artifact['artifactCanonicalSha256'] == csha(artifact, 'artifactCanonicalSha256'), 'artifact self hash drift')
    req(result['resultSha256'] == csha(result, 'resultSha256'), 'result self hash drift')
    req(artifact['status'] == 'TRAINING_ONLY_CHANGED_MODEL_FROZEN_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', 'artifact status drift')
    req(result['status'] == 'MATERIALIZED_AUDITED_CHANGED_WIN_MODEL_TRAINING_ONLY', 'result status drift')
    req(artifact['governance'] == result['governance'] == 'MYSTIC-STATE-0071', 'governance drift')
    req(artifact['sourceSelectionEvidence'] == recovery['sourceSelectionEvidence'], 'selection evidence drift')
    spec = expected_spec(recovery)
    req(artifact['selectedSpec'] == result['selectedSpec'] == spec, 'selected spec drift')
    req(result['selectedCandidateId'] == SELECTED_ID and result['sourceAuditedEligibleCandidateCount'] == 145, 'source audited verdict drift')
    for key in ('candidateSearchPerformedInRecovery','candidateEnumerationPerformedInRecovery','rankingPerformedInRecovery'):
        req(result[key] is False, f'forbidden recovery action occurred: {key}')
    req(result['crossValidationFoldEvaluationsPerformedInRecovery'] == 0, 'CV rerun occurred')
    d = artifact['materializationDiagnostics']
    req(d['candidateSearchPerformed'] is False and d['candidateEnumerationPerformed'] is False and d['rankingPerformed'] is False and d['crossValidationFoldEvaluationsPerformed'] == 0, 'artifact recovery diagnostics drift')
    trainer = module('lbv3_trainer_for_independent_materialization_audit', IMPL / 'train_v1.py')
    engine = module('lbv3_engine_for_independent_materialization_audit', IMPL / 'engine_v1.py')
    legacy = trainer.load_legacy(); effective = trainer.effective_legacy_protocol(legacy)
    records = trainer.validate_dataset(dataset, protocol, legacy, effective)
    scales = np.asarray(effective['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    expected_base = legacy.v2.fit_candidate(records, trainer.base_spec(spec), scales)
    actual_model = artifact['model']
    req(actual_model['kind'] == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'model kind drift')
    req(actual_model['baseModel'] == expected_base, 'base model reconstruction drift')
    req(actual_model['residualCoordinateSystem'] == 'V1_IDW_COS_COORDINATES', 'residual coordinate system drift')
    req((actual_model['residualNeighbors'], actual_model['residualPower'], actual_model['residualShrinkage']) == (6, 1.0, 1.0), 'residual hyperparameter drift')
    req(actual_model['fitGeometryIdsInStableOrder'] == [str(r['geometryId']) for r in records], 'fit ID order drift')
    expected_coords = [engine.residual_coordinates(r['geometry'], 'V1_IDW_COS_COORDINATES').tolist() for r in records]
    req(actual_model['residualCoordinates'] == expected_coords, 'residual coordinates drift')
    expected_residuals = []
    for r in records:
        truth = np.asarray(legacy.v2.targets_and_shape_se(r, scales)[0], dtype=np.float64)
        base = np.asarray(legacy.v2.predict(expected_base, r['geometry']), dtype=np.float64)
        expected_residuals.append((truth[:3] - base[:3]).tolist())
    req(actual_model['residualTargets'] == expected_residuals, 'residual target reconstruction drift')
    model_body = dict(actual_model); model_hash = model_body.pop('modelCanonicalSha256')
    req(hashlib.sha256(json.dumps(model_body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest() == model_hash, 'model canonical hash drift')
    req(result['modelCanonicalSha256'] == model_hash and result['modelArtifactCanonicalSha256'] == artifact['artifactCanonicalSha256'], 'result model binding drift')
    max_primary = 0.0; max_shape = 0.0
    for r in records:
        truth = np.asarray(legacy.v2.targets_and_shape_se(r, scales)[0], dtype=np.float64)
        base = np.asarray(legacy.v2.predict(expected_base, r['geometry']), dtype=np.float64)
        pred = np.asarray(engine.predict_hybrid(actual_model, r['geometry'], lambda m,g: np.asarray(legacy.v2.predict(m,g), dtype=np.float64)), dtype=np.float64)
        max_primary = max(max_primary, float(np.max(np.abs(pred[:3] - truth[:3]))))
        max_shape = max(max_shape, float(np.max(np.abs(pred[3:] - base[3:]))))
    req(max_primary <= 1e-12 and max_shape == 0.0, 'materialized prediction invariant drift')
    req(abs(d['maxTrainingExactMatchPrimaryAbsoluteLogError'] - max_primary) <= 1e-18, 'primary diagnostic drift')
    req(d['maxShapePredictionChangeVsFrozenBase'] == max_shape, 'shape diagnostic drift')
    for obj in (artifact, result):
        req(obj['protectedValidationAuthorized'] is False and obj['futureFreshValidationGovernanceRequired'] is True and obj['productionPromotionAuthorized'] is False, 'closed boundary drift')
        req(obj['workerBLaneReactivated'] is False and obj['workerCLaneReactivated'] is False, 'worker lane opened')
    req(result['newMysticSolverExecutionPerformed'] is False and result['ordinal27ValuesRead'] is False, 'forbidden science read/execution')
    print(json.dumps({'status':'PASS','selectedCandidateId':SELECTED_ID,'modelCanonicalSha256':model_hash,'artifactCanonicalSha256':artifact['artifactCanonicalSha256'],'resultSha256':result['resultSha256'],'crossValidationFoldEvaluationsPerformedInRecovery':0}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
