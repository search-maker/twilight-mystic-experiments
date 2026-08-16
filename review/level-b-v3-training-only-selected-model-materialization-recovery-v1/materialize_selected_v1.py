#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
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
EXPECTED_PREFIT_SHA = '8e3928634c3d297974c07533bed3bbfa24783f14ed55391fd318f817282d9a8e'
SELECTED_ID = 'resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1'


class Refusal(RuntimeError):
    pass


def req(c: bool, m: str) -> None:
    if not c:
        raise Refusal(m)


def load(path: Path) -> dict[str, Any]:
    v = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(v, dict), f'object required: {path}')
    return v


def canonical_sha(value: dict[str, Any], omit: str | None = None) -> str:
    body = dict(value)
    if omit:
        body.pop(omit, None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def recovery_spec(recovery: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    evidence = recovery['sourceSelectionEvidence']
    req(evidence['auditedSelectionStatus'] == 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', 'source selection verdict drift')
    req(evidence['auditedEligibleCandidateCount'] == 145, 'source eligible count drift')
    req(evidence['selectedCandidateId'] == SELECTED_ID, 'selected candidate id drift')
    s = evidence['selectedSpec']
    expected = {
        'familyId': 'ridge-primary-local-residual-idw-shape-fixed-idw',
        'kind': 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW',
        'complexityRank': 9,
        'primaryBasis': 'PHYSICAL_COMPACT_16_TERMS',
        'primaryRidge': 1e-5,
        'shapeCoordinates': 'V1_IDW_COS_COORDINATES',
        'shapeNeighbors': 4,
        'shapePower': 1.0,
        'residualCoordinateSystem': 'V1_IDW_COS_COORDINATES',
        'residualNeighbors': 6,
        'residualPower': 1.0,
        'residualShrinkage': 1.0,
    }
    req(s == expected, 'selected spec drift')
    new = protocol['candidateDefinition']['newFamily']
    req(s['primaryRidge'] in new['primaryRidgeValues'], 'selected ridge not frozen')
    req(s['residualCoordinateSystem'] in new['residualCoordinateSystems'], 'selected coordinates not frozen')
    req(s['residualNeighbors'] in new['residualNeighbors'], 'selected neighbors not frozen')
    req(s['residualPower'] in new['residualPowers'], 'selected power not frozen')
    req(s['residualShrinkage'] in new['residualShrinkage'], 'selected shrinkage not frozen')
    req((s['shapeNeighbors'], s['shapePower'], s['shapeCoordinates']) == (4, 1.0, 'V1_IDW_COS_COORDINATES'), 'shape spec drift')
    return {
        'candidateId': SELECTED_ID,
        'familyId': s['familyId'],
        'kind': s['kind'],
        'complexityRank': s['complexityRank'],
        'primaryBasis': s['primaryBasis'],
        'primaryRidge': s['primaryRidge'],
        'neighbors': s['shapeNeighbors'],
        'power': s['shapePower'],
        'shapeCoordinates': s['shapeCoordinates'],
        'residualCoordinateSystem': s['residualCoordinateSystem'],
        'residualNeighbors': s['residualNeighbors'],
        'residualPower': s['residualPower'],
        'residualShrinkage': s['residualShrinkage'],
    }


def validate_static() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    recovery = load(RECOVERY)
    req(recovery['recoveryContractSha256'] == canonical_sha(recovery, 'recoveryContractSha256') == EXPECTED_RECOVERY_SHA, 'recovery contract hash drift')
    req(recovery['governance'] == 'MYSTIC-STATE-0071', 'governance drift')
    sem = recovery['materializationSemantics']
    for k in ('candidateSearchAuthorized', 'candidateEnumerationAuthorized', 'crossValidationAuthorized', 'gateReevaluationAuthorized', 'rankingAuthorized', 'selectionChangeAuthorized', 'selectedSpecMayChange', 'selectedCandidateIdMayChange', 'shapePredictorMayChange', 'trainingDataMayChange', 'newMysticSolverExecutionAuthorized', 'ordinal27MayBeRead', 'protectedValidationAuthorized', 'protectedValuesMayBeRead', 'productionPromotionAuthorized', 'workerBLaneReactivated', 'workerCLaneReactivated'):
        req(sem[k] is False, f'forbidden recovery surface opened: {k}')
    req(sem['selectedFinalModelFitOnAll58TrainingRecordsAuthorized'] is True and sem['selectedModelReconstructionMustBeDeterministic'] is True, 'materialization authorization drift')
    protocol = load(PREFIT)
    req(protocol['protocolSha256'] == canonical_sha(protocol, 'protocolSha256') == EXPECTED_PREFIT_SHA, 'prefit hash drift')
    spec = recovery_spec(recovery, protocol)
    return recovery, protocol, spec


def validate_dataset(path: Path, recovery: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    raw = path.read_bytes()
    req(hashlib.sha256(raw).hexdigest() == EXPECTED_DATASET_BYTE_SHA, 'dataset byte hash drift')
    d = json.loads(raw)
    req(isinstance(d, dict), 'dataset object required')
    body = dict(d)
    stored = body.pop('datasetSha256', None)
    req(stored == EXPECTED_DATASET_SHA == recovery['trainingSource']['datasetCanonicalSha256'], 'dataset canonical identity drift')
    req(hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest() == stored, 'dataset self-hash drift')
    req(d.get('geometryCount') == 58 and d.get('protectedHoldoutRecordCount') == 0 and len(d.get('records') or []) == 58, 'dataset role/dimension drift')
    req([str(r.get('geometryId')) for r in d['records']] == protocol['roleIsolation']['trainingGeometryIds'], 'training geometry IDs/order drift')
    req(not any(str(r.get('geometryId', '')).startswith('v0070-holdout-') for r in d['records']), 'ordinal27 record present')
    return d


def materialize(dataset_path: Path, output_dir: Path) -> None:
    req(np.__version__ == '2.3.2', f'numpy version drift: {np.__version__}')
    recovery, protocol, selected = validate_static()
    dataset = validate_dataset(dataset_path, recovery, protocol)
    trainer = load_module('lbv3_trainer_for_materialization', IMPL / 'train_v1.py')
    engine = load_module('lbv3_engine_for_materialization', IMPL / 'engine_v1.py')
    legacy = trainer.load_legacy()
    effective = trainer.effective_legacy_protocol(legacy)
    records = trainer.validate_dataset(dataset, protocol, legacy, effective)
    req(len(records) == 58, '58 validated records required')
    scales = np.asarray(effective['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    base_model = legacy.v2.fit_candidate(records, trainer.base_spec(selected), scales)
    model = engine.make_hybrid_model(
        records,
        base_model,
        selected,
        lambda record: np.asarray(legacy.v2.targets_and_shape_se(record, scales)[0], dtype=np.float64),
        lambda m, geometry: np.asarray(legacy.v2.predict(m, geometry), dtype=np.float64),
    )
    req(model['kind'] == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'materialized model kind drift')
    req(len(model['fitGeometryIdsInStableOrder']) == len(model['residualCoordinates']) == len(model['residualTargets']) == 58, 'materialized support count drift')
    max_primary = 0.0
    max_shape = 0.0
    for r in records:
        truth = np.asarray(legacy.v2.targets_and_shape_se(r, scales)[0], dtype=np.float64)
        base = np.asarray(legacy.v2.predict(base_model, r['geometry']), dtype=np.float64)
        pred = np.asarray(engine.predict_hybrid(model, r['geometry'], lambda m, g: np.asarray(legacy.v2.predict(m, g), dtype=np.float64)), dtype=np.float64)
        req(pred.shape == (13,) and np.all(np.isfinite(pred)), 'nonfinite materialized prediction')
        max_primary = max(max_primary, float(np.max(np.abs(pred[:3] - truth[:3]))))
        max_shape = max(max_shape, float(np.max(np.abs(pred[3:] - base[3:]))))
    req(max_primary <= 1e-12, f'exact-match primary materialization drift: {max_primary}')
    req(max_shape == 0.0, f'shape changed during materialization: {max_shape}')
    artifact = {
        'schemaVersion': 1,
        'artifactId': 'level-b-v3-training-only-selected-model-materialization-v1',
        'status': 'TRAINING_ONLY_CHANGED_MODEL_FROZEN_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE',
        'governance': 'MYSTIC-STATE-0071',
        'sourceSelectionEvidence': recovery['sourceSelectionEvidence'],
        'sourceTrainingDatasetCanonicalSha256': EXPECTED_DATASET_SHA,
        'trainingGeometryCount': 58,
        'selectedSpec': selected,
        'materializationDiagnostics': {
            'candidateSearchPerformed': False,
            'candidateEnumerationPerformed': False,
            'crossValidationFoldEvaluationsPerformed': 0,
            'rankingPerformed': False,
            'maxTrainingExactMatchPrimaryAbsoluteLogError': max_primary,
            'maxShapePredictionChangeVsFrozenBase': max_shape,
        },
        'model': model,
        'protectedValidationAuthorized': False,
        'futureFreshValidationGovernanceRequired': True,
        'productionPromotionAuthorized': False,
        'workerBLaneReactivated': False,
        'workerCLaneReactivated': False,
    }
    artifact['artifactCanonicalSha256'] = canonical_sha(artifact)
    result = {
        'schemaVersion': 1,
        'resultId': 'level-b-v3-training-only-selected-model-materialization-result-v1',
        'status': 'MATERIALIZED_AUDITED_CHANGED_WIN_MODEL_TRAINING_ONLY',
        'governance': 'MYSTIC-STATE-0071',
        'sourceFitRunId': recovery['sourceSelectionEvidence']['fitRunId'],
        'sourceFitJobId': recovery['sourceSelectionEvidence']['fitJobId'],
        'sourceAuditedSelectionStatus': recovery['sourceSelectionEvidence']['auditedSelectionStatus'],
        'sourceAuditedEligibleCandidateCount': recovery['sourceSelectionEvidence']['auditedEligibleCandidateCount'],
        'selectedCandidateId': SELECTED_ID,
        'selectedSpec': selected,
        'modelArtifactCanonicalSha256': artifact['artifactCanonicalSha256'],
        'modelCanonicalSha256': model['modelCanonicalSha256'],
        'candidateSearchPerformedInRecovery': False,
        'candidateEnumerationPerformedInRecovery': False,
        'crossValidationFoldEvaluationsPerformedInRecovery': 0,
        'rankingPerformedInRecovery': False,
        'protectedValidationAuthorized': False,
        'futureFreshValidationGovernanceRequired': True,
        'newMysticSolverExecutionPerformed': False,
        'ordinal27ValuesRead': False,
        'productionPromotionAuthorized': False,
        'workerBLaneReactivated': False,
        'workerCLaneReactivated': False,
    }
    result['resultSha256'] = canonical_sha(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'model-artifact-materialization-v1.json').write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    (output_dir / 'materialization-result-v1.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('self-test')
    m = sub.add_parser('materialize')
    m.add_argument('--dataset', type=Path, required=True)
    m.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    try:
        recovery, protocol, selected = validate_static()
        if args.cmd == 'self-test':
            print(json.dumps({'status': 'PASS', 'selectedCandidateId': SELECTED_ID, 'selectedSpec': selected, 'recoveryContractSha256': recovery['recoveryContractSha256']}, sort_keys=True))
        else:
            materialize(args.dataset, args.output_dir)
        return 0
    except Exception as e:
        print(json.dumps({'status': 'REFUSED', 'reason': str(e)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
