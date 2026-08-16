#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np

import engine_v1 as engine

ROOT = Path(__file__).resolve().parents[2]
LEGACY_TRAIN = ROOT / 'review/level-b-v2-training-implementation-v3-densified58/train_v3.py'
LEGACY_PREFIT = ROOT / 'review/level-b-v2-training-prefit-freeze-v3-densified58/protocol-v3.json'
EXPECTED_DATASET_SHA256 = '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435'
EXPECTED_PROTOCOL_SHA256 = '8e3928634c3d297974c07533bed3bbfa24783f14ed55391fd318f817282d9a8e'
SHAPE_METRICS = (
    'looMeanRawShapeNrmse',
    'looWorstRawShapeNrmseReportOnly',
    'looWorstUncertaintyAdjustedShapeNrmse',
    'looWorstUncertaintyAdjustedSingleCoefficientError',
    'boundaryWorstRawShapeNrmse',
)
FOLD_SHAPE_METRICS = (
    'rawShapeNrmse',
    'uncertaintyAdjustedShapeNrmse',
    'worstUncertaintyAdjustedSingleCoefficientError',
)


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot load module: {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_legacy():
    return load_module('level_b_v2_densified58_frozen_engine_for_v3', LEGACY_TRAIN)


def effective_legacy_protocol(legacy) -> dict[str, Any]:
    old = load_json(LEGACY_PREFIT)
    return legacy.effective_protocol(old)


def base_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        'familyId': str(spec['familyId']),
        'kind': 'RIDGE_PRIMARY_IDW_SHAPE',
        'complexityRank': int(spec['complexityRank']),
        'primaryBasis': 'PHYSICAL_COMPACT_16_TERMS',
        'primaryRidge': float(spec['primaryRidge']),
        'neighbors': 4,
        'power': 1.0,
    }


def generic_evaluate(
    records: list[dict[str, Any]],
    spec: dict[str, Any],
    legacy,
    effective: dict[str, Any],
    scales: np.ndarray,
    gates: dict[str, Any],
    enforce_counts: bool,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    loo_primary: list[float] = []
    loo_single: list[float] = []
    loo_raw: list[float] = []
    loo_ua: list[float] = []
    loo_uasing: list[float] = []
    loo_base: list[float] = []
    for fold in legacy.folds58(records, effective, enforce_counts):
        fit = [records[i] for i in fold['fit']]
        bspec = base_spec(spec)
        model = legacy.v2.fit_candidate(fit, bspec, scales)
        base_mean = np.mean(np.vstack([legacy.v2.targets_and_shape_se(r, scales)[0] for r in fit]), axis=0)
        fit_coords: np.ndarray | None = None
        fit_residuals: np.ndarray | None = None
        if spec['familyId'] == engine.NEW_FAMILY:
            fit_coords = np.vstack([engine.residual_coordinates(r['geometry'], str(spec['residualCoordinateSystem'])) for r in fit])
            residual_rows: list[np.ndarray] = []
            for r in fit:
                truth, _ = legacy.v2.targets_and_shape_se(r, scales)
                pred = legacy.v2.predict(model, r['geometry'])
                residual_rows.append(np.asarray(truth[:3] - pred[:3], dtype=np.float64))
            fit_residuals = np.vstack(residual_rows)
        primary: list[float] = []
        single: list[float] = []
        raw: list[float] = []
        ua: list[float] = []
        uasing: list[float] = []
        basep: list[float] = []
        for idx in fold['val']:
            truth, uncertainty = legacy.v2.targets_and_shape_se(records[idx], scales)
            pred = np.asarray(legacy.v2.predict(model, records[idx]['geometry']), dtype=np.float64)
            if spec['familyId'] == engine.NEW_FAMILY:
                assert fit_coords is not None and fit_residuals is not None
                corr = engine.idw_residual(
                    fit_coords,
                    fit_residuals,
                    engine.residual_coordinates(records[idx]['geometry'], str(spec['residualCoordinateSystem'])),
                    int(spec['residualNeighbors']),
                    float(spec['residualPower']),
                )
                pred = engine.apply_primary_residual(pred, corr, float(spec['residualShrinkage']))
            pe = np.abs(pred[:3] - truth[:3])
            se = pred[3:] - truth[3:]
            denom = np.sqrt(1.0 + uncertainty * uncertainty)
            primary.append(float(np.mean(pe)))
            single.append(float(np.max(pe)))
            raw.append(float(np.sqrt(np.mean(se * se))))
            ua.append(float(np.sqrt(np.mean((se / denom) ** 2))))
            uasing.append(float(np.max(np.abs(se) / denom)))
            basep.append(float(np.mean(np.abs(base_mean[:3] - truth[:3]))))
        row = {
            'fold': fold['name'],
            'kind': fold['kind'],
            'count': len(fold['val']),
            'primaryMale': float(np.mean(primary)),
            'worstSinglePrimaryLogError': max(single),
            'rawShapeNrmse': float(np.mean(raw)),
            'uncertaintyAdjustedShapeNrmse': float(np.mean(ua)),
            'worstUncertaintyAdjustedSingleCoefficientError': max(uasing),
        }
        rows.append(row)
        if fold['kind'] == 'loo':
            loo_primary += primary
            loo_single += single
            loo_raw += raw
            loo_ua += ua
            loo_uasing += uasing
            loo_base += basep
    req(len(loo_primary) == 58, 'LOO count drift')
    boundary = [row for row in rows if row['kind'] == 'boundary']
    baseline = float(np.mean(loo_base))
    mean_primary = float(np.mean(loo_primary))
    mean_raw = float(np.mean(loo_raw))
    improvement = 1.0 - mean_primary / baseline
    metrics = {
        'looMeanPrimaryMale': mean_primary,
        'looWorstSinglePrimaryLogError': max(loo_single),
        'looMeanRawShapeNrmse': mean_raw,
        'looWorstRawShapeNrmseReportOnly': max(loo_raw),
        'looWorstUncertaintyAdjustedShapeNrmse': max(loo_ua),
        'looWorstUncertaintyAdjustedSingleCoefficientError': max(loo_uasing),
        'boundaryWorstPrimaryMale': max(row['primaryMale'] for row in boundary),
        'boundaryWorstRawShapeNrmse': max(row['rawShapeNrmse'] for row in boundary),
        'looFoldMatchedTrainingMeanBaselinePrimaryMale': baseline,
        'looPrimaryImprovementVsBaselineFraction': improvement,
    }
    result = engine.finalize_result(spec, metrics, gates)
    result['foldMetrics'] = rows
    return result


def assert_control_parity(ours: dict[str, Any], legacy_result: dict[str, Any]) -> None:
    metric_keys = (
        'looMeanPrimaryMale', 'looWorstSinglePrimaryLogError', 'looMeanRawShapeNrmse',
        'looWorstRawShapeNrmseReportOnly', 'looWorstUncertaintyAdjustedShapeNrmse',
        'looWorstUncertaintyAdjustedSingleCoefficientError', 'boundaryWorstPrimaryMale',
        'boundaryWorstRawShapeNrmse', 'looFoldMatchedTrainingMeanBaselinePrimaryMale',
        'looPrimaryImprovementVsBaselineFraction',
    )
    for key in metric_keys:
        req(ours[key] == legacy_result[key], f'control metric parity drift: {key}')
    req(ours['gateChecks'] == legacy_result['gateChecks'], 'control gate parity drift')
    req(ours['eligible'] == legacy_result['eligible'], 'control eligibility parity drift')
    req(ours['legacyOverallSelectionScore'] == legacy_result['selectionScore'], 'control legacy score parity drift')
    req(ours['foldMetrics'] == legacy_result['foldMetrics'], 'control fold metric parity drift')


def assert_shape_invariance(results: list[dict[str, Any]]) -> None:
    control = next(r for r in results if r['familyId'] == engine.CONTROL_FAMILY)
    control_folds = {r['fold']: r for r in control['foldMetrics']}
    for result in results:
        for key in SHAPE_METRICS:
            req(result[key] == control[key], f'shape aggregate drift: {result["candidateId"]} {key}')
        folds = {r['fold']: r for r in result['foldMetrics']}
        req(folds.keys() == control_folds.keys(), 'shape fold universe drift')
        for name in folds:
            for key in FOLD_SHAPE_METRICS:
                req(folds[name][key] == control_folds[name][key], f'shape fold drift: {result["candidateId"]} {name} {key}')


def evaluate_all(records: list[dict[str, Any]], protocol: dict[str, Any], enforce_counts: bool) -> tuple[list[dict[str, Any]], Any, dict[str, Any], np.ndarray]:
    engine.validate_protocol(protocol)
    legacy = load_legacy()
    effective = effective_legacy_protocol(legacy)
    scales = np.asarray(effective['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    specs = engine.candidate_specs(protocol)
    results: list[dict[str, Any]] = []
    for spec in specs:
        results.append(generic_evaluate(records, spec, legacy, effective, scales, protocol['trainingOnlyReadinessGates'], enforce_counts))
    legacy_control = legacy.evaluate_candidate58(records, base_spec(specs[0]), effective, scales, enforce_counts)
    assert_control_parity(results[0], legacy_control)
    assert_shape_invariance(results)
    return results, legacy, effective, scales


def validate_dataset(dataset: dict[str, Any], protocol: dict[str, Any], legacy, effective: dict[str, Any]) -> list[dict[str, Any]]:
    req(dataset.get('datasetSha256') == EXPECTED_DATASET_SHA256, 'expanded dataset identity drift')
    body = dict(dataset)
    body.pop('datasetSha256', None)
    req(engine.canonical_sha(body) == EXPECTED_DATASET_SHA256, 'expanded dataset self-hash drift')
    req(dataset.get('geometryCount') == 58 and dataset.get('representationFeatureCount') == 13, 'dataset dimension drift')
    req(dataset.get('protectedHoldoutRecordCount') == 0, 'protected record entered training dataset')
    records = dataset.get('records') or []
    req(len(records) == 58, '58 records required')
    expected_ids = list(protocol['roleIsolation']['trainingGeometryIds'])
    req([str(r.get('geometryId')) for r in records] == expected_ids, 'training IDs/order drift')
    scales = np.asarray(effective['sourceTrainingRepresentation']['nullspaceCoefficientScales'], dtype=np.float64)
    for record in records:
        legacy.v2.targets_and_shape_se(record, scales)
    return records


def selected_spec_view(best: dict[str, Any] | None) -> dict[str, Any] | None:
    if best is None:
        return None
    keys = (
        'candidateId', 'familyId', 'kind', 'complexityRank', 'primaryBasis', 'primaryRidge',
        'neighbors', 'power', 'shapeCoordinates', 'residualCoordinateSystem', 'residualNeighbors',
        'residualPower', 'residualShrinkage', 'primaryStressScore', 'legacyOverallSelectionScore',
    )
    return {key: best[key] for key in keys if key in best}


def execute(protocol: dict[str, Any], dataset_path: Path, output: Path) -> None:
    req(np.__version__ == '2.3.2', f'numpy version drift: {np.__version__}')
    req(protocol.get('protocolSha256') == EXPECTED_PROTOCOL_SHA256, 'protocol v2 hash drift')
    legacy = load_legacy()
    effective = effective_legacy_protocol(legacy)
    dataset = load_json(dataset_path)
    records = validate_dataset(dataset, protocol, legacy, effective)
    results, legacy2, effective2, scales = evaluate_all(records, protocol, enforce_counts=True)
    req(legacy2 is not None and effective2 is not None, 'legacy evaluation unavailable')
    status, best, ordered = engine.select_candidate(results, protocol)
    selection = {
        'schemaVersion': 1,
        'stageId': 'level-b-v3-training-only-selection-v1',
        'status': status,
        'governance': 'MYSTIC-STATE-0071',
        'protocolId': protocol['protocolId'],
        'protocolSha256': protocol['protocolSha256'],
        'sourceExpandedDatasetSha256': EXPECTED_DATASET_SHA256,
        'trainingGeometryCount': 58,
        'cvFoldCount': 73,
        'candidateCount': 145,
        'eligibleCandidateCount': sum(bool(r['eligible']) for r in ordered),
        'selectedCandidate': selected_spec_view(best),
        'candidates': ordered,
        'protectedValidationOpened': False,
        'newMysticSolverExecutionPerformed': False,
    }
    selection['selectionSha256'] = engine.canonical_sha(selection)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'training-selection-v1.json', selection)
    if status != 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE':
        result = {
            'schemaVersion': 1,
            'stageId': 'level-b-v3-training-only-result-v1',
            'status': status,
            'governance': 'MYSTIC-STATE-0071',
            'sourceExpandedDatasetSha256': EXPECTED_DATASET_SHA256,
            'trainingSelectionSha256': selection['selectionSha256'],
            'changedModelArtifactWritten': False,
            'protectedValidationAuthorized': False,
            'futureFreshValidationGovernanceRequired': True,
            'newMysticSolverExecutionPerformed': False,
            'productionPromotionAuthorized': False,
            'workerBLaneReactivated': False,
            'workerCLaneReactivated': False,
        }
        result['resultSha256'] = engine.canonical_sha(result)
        write_json(output / 'training-result-v1.json', result)
        return
    assert best is not None
    bspec = base_spec(best)
    base_model = legacy.v2.fit_candidate(records, bspec, scales)
    hybrid = engine.make_hybrid_model(
        records,
        base_model,
        best,
        lambda record: np.asarray(legacy.v2.targets_and_shape_se(record, scales)[0], dtype=np.float64),
        lambda model, geometry: np.asarray(legacy.v2.predict(model, geometry), dtype=np.float64),
    )
    artifact = {
        'schemaVersion': 1,
        'stageId': 'level-b-v3-training-only-model-v1',
        'status': 'TRAINING_ONLY_CHANGED_MODEL_FROZEN_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE',
        'governance': 'MYSTIC-STATE-0071',
        'protocolId': protocol['protocolId'],
        'protocolSha256': protocol['protocolSha256'],
        'sourceExpandedDatasetSha256': EXPECTED_DATASET_SHA256,
        'trainingSelectionSha256': selection['selectionSha256'],
        'trainingGeometryCount': 58,
        'selectedSpec': selected_spec_view(best),
        'model': hybrid,
        'protectedValidationAuthorized': False,
        'futureFreshValidationGovernanceRequired': True,
        'productionPromotionAuthorized': False,
    }
    artifact['artifactCanonicalSha256'] = engine.canonical_sha(artifact)
    write_json(output / 'model-artifact-v1.json', artifact)
    result = {
        'schemaVersion': 1,
        'stageId': 'level-b-v3-training-only-result-v1',
        'status': status,
        'governance': 'MYSTIC-STATE-0071',
        'sourceExpandedDatasetSha256': EXPECTED_DATASET_SHA256,
        'trainingSelectionSha256': selection['selectionSha256'],
        'changedModelArtifactWritten': True,
        'modelArtifactCanonicalSha256': artifact['artifactCanonicalSha256'],
        'modelCanonicalSha256': hybrid['modelCanonicalSha256'],
        'selectedSpec': selected_spec_view(best),
        'selectedTrainingMetrics': {key: best[key] for key in (
            'primaryStressScore', 'legacyOverallSelectionScore', 'looMeanPrimaryMale',
            'looWorstSinglePrimaryLogError', 'boundaryWorstPrimaryMale', 'looMeanRawShapeNrmse',
            'looWorstUncertaintyAdjustedShapeNrmse', 'looWorstUncertaintyAdjustedSingleCoefficientError',
            'boundaryWorstRawShapeNrmse', 'looPrimaryImprovementVsBaselineFraction',
        )},
        'protectedValidationAuthorized': False,
        'futureFreshValidationGovernanceRequired': True,
        'newMysticSolverExecutionPerformed': False,
        'productionPromotionAuthorized': False,
        'workerBLaneReactivated': False,
        'workerCLaneReactivated': False,
    }
    result['resultSha256'] = engine.canonical_sha(result)
    write_json(output / 'training-result-v1.json', result)


def synthetic(protocol: dict[str, Any]) -> dict[str, Any]:
    req(np.__version__ == '2.3.2', f'numpy version drift: {np.__version__}')
    legacy = load_legacy()
    effective = effective_legacy_protocol(legacy)
    records = legacy.synthetic_records(effective)
    req(len(records) == 58, 'synthetic 58-record fixture drift')
    results, _, _, _ = evaluate_all(records, protocol, enforce_counts=False)
    status, best, ordered = engine.select_candidate(results, protocol)
    return {
        'status': 'SYNTHETIC_IMPLEMENTATION_PASS',
        'candidateCount': len(results),
        'changedCandidateCount': sum(r['familyId'] == engine.NEW_FAMILY for r in results),
        'cvFoldCount': len(legacy.folds58(records, effective, enforce_counts=False)),
        'controlEligible': bool(results[0]['eligible']),
        'selectionOutcome': status,
        'selectedCandidate': None if best is None else best['candidateId'],
        'shapeInvariantAcrossCandidateCount': len(ordered),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('synthetic')
    s.add_argument('--protocol', type=Path, required=True)
    x = sub.add_parser('execute')
    x.add_argument('--protocol', type=Path, required=True)
    x.add_argument('--dataset', type=Path, required=True)
    x.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        protocol = load_json(args.protocol)
        engine.validate_protocol(protocol)
        if args.cmd == 'synthetic':
            print(json.dumps(synthetic(protocol), sort_keys=True))
        else:
            execute(protocol, args.dataset, args.output)
        return 0
    except Exception as error:
        print(json.dumps({'status': 'REFUSED', 'reason': str(error)}, sort_keys=True), file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
