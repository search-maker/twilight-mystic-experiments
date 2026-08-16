#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Callable, Iterable

import numpy as np

CONTROL_FAMILY = 'v2-frozen-control-ridge-primary-compact-shape-idw-k4-p1'
NEW_FAMILY = 'ridge-primary-local-residual-idw-shape-fixed-idw'


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_protocol(protocol: dict[str, Any]) -> None:
    req(protocol.get('governance') == 'MYSTIC-STATE-0071', 'governance drift')
    req(protocol.get('protocolId') == 'level-b-v3-training-only-prefit-freeze-v2', 'protocol id drift')
    req(protocol.get('protocolSha256') == '8e3928634c3d297974c07533bed3bbfa24783f14ed55391fd318f817282d9a8e', 'protocol hash binding drift')
    req(protocol['candidateDefinition']['candidateCountRequired'] == 145, 'candidate count drift')
    req(protocol['roleIsolation']['trainingGeometryCountRequired'] == 58, 'training geometry count drift')
    req(protocol['crossValidation']['totalFoldCountRequired'] == 73, 'fold count drift')
    req(protocol['closedBoundaries']['newMysticSolverExecutionAuthorized'] is False, 'MYSTIC opened')
    req(protocol['closedBoundaries']['protectedValidationAuthorized'] is False, 'protected validation opened')
    control = protocol['candidateDefinition']['control']
    new = protocol['candidateDefinition']['newFamily']
    req(control['familyId'] == CONTROL_FAMILY and control['complexityRank'] == 7, 'control identity drift')
    req(new['familyId'] == NEW_FAMILY and new['complexityRank'] == 9, 'new family identity drift')
    req(new['residualDistanceMetric'] == 'EUCLIDEAN_L2_FLOAT64', 'distance metric drift')
    req(new['residualNeighborOrdering'] == 'ASCENDING_DISTANCE_STABLE_PRESERVE_FIT_RECORD_ORDER_ON_EQUAL_DISTANCE', 'neighbor ordering drift')
    req(new['residualWeightDefinition'] == 'FOR_NONZERO_NEIGHBORS_WEIGHT=1/(distance**power); NORMALIZE_WEIGHTS_TO_SUM_1', 'weight semantics drift')
    req(protocol['selection']['newCandidateMustStrictlyOutrankControl'] is True, 'strict control comparison drift')
    req(protocol['selection']['shapeMetricsMustBeIdenticalAcrossAllCandidates'] is True, 'shape invariance drift')


def candidate_specs(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    validate_protocol(protocol)
    c = protocol['candidateDefinition']['control']
    n = protocol['candidateDefinition']['newFamily']
    out: list[dict[str, Any]] = [{
        'candidateId': 'control-v2-frozen',
        'familyId': c['familyId'],
        'kind': c['kind'],
        'complexityRank': int(c['complexityRank']),
        'primaryBasis': c['primaryBasis'],
        'primaryRidge': float(c['primaryRidge']),
        'neighbors': int(c['shapeNeighbors']),
        'power': float(c['shapePower']),
        'shapeCoordinates': c['shapeCoordinates'],
    }]
    for coordinate_system in n['residualCoordinateSystems']:
        for primary_ridge in n['primaryRidgeValues']:
            for neighbors in n['residualNeighbors']:
                for power in n['residualPowers']:
                    for shrinkage in n['residualShrinkage']:
                        cid = (
                            f"resid-{coordinate_system}-r{float(primary_ridge):.12g}"
                            f"-k{int(neighbors)}-p{float(power):.12g}-a{float(shrinkage):.12g}"
                        )
                        out.append({
                            'candidateId': cid,
                            'familyId': n['familyId'],
                            'kind': n['kind'],
                            'complexityRank': int(n['complexityRank']),
                            'primaryBasis': n['primaryBasis'],
                            'primaryRidge': float(primary_ridge),
                            'residualCoordinateSystem': coordinate_system,
                            'residualNeighbors': int(neighbors),
                            'residualPower': float(power),
                            'residualShrinkage': float(shrinkage),
                            'neighbors': int(n['shapePredictorFixed']['neighbors']),
                            'power': float(n['shapePredictorFixed']['power']),
                            'shapeCoordinates': n['shapePredictorFixed']['coordinates'],
                        })
    req(len(out) == 145, 'exactly 145 candidates required')
    req(sum(x['familyId'] == NEW_FAMILY for x in out) == 144, 'exactly 144 changed candidates required')
    req(out[0]['familyId'] == CONTROL_FAMILY, 'control must be first')
    req(len({x['candidateId'] for x in out}) == 145, 'candidate ids must be unique')
    return out


def residual_coordinates(geometry: dict[str, Any], system: str) -> np.ndarray:
    sun = float(geometry['sunDepressionDeg'])
    alt = float(geometry['targetAltitudeDeg'])
    az = float(geometry['relativeAzimuthDeg'])
    elev = float(geometry['observerElevationM'])
    aod = float(geometry['aod550'])
    req(all(math.isfinite(x) for x in (sun, alt, az, elev, aod)), 'nonfinite geometry')
    req(aod > 0.0, 'positive AOD required')
    if system == 'PHYSICAL_NORMALIZED_IDW_COORDINATES':
        out = np.array([
            (sun - 2.0) / 8.5,
            math.sin(alt * math.pi / 180.0),
            (math.cos(az * math.pi / 180.0) + 1.0) / 2.0,
            elev / 2500.0,
            math.log(aod / 0.05) / math.log(8.0),
        ], dtype=np.float64)
    elif system == 'V1_IDW_COS_COORDINATES':
        out = np.array([
            (sun - 2.0) / 8.5,
            (alt - 5.0) / 75.0,
            (math.cos(az * math.pi / 180.0) + 1.0) / 2.0,
            elev / 2500.0,
            (aod - 0.05) / 0.35,
        ], dtype=np.float64)
    else:
        raise Refusal(f'unknown residual coordinate system: {system}')
    req(out.shape == (5,) and np.all(np.isfinite(out)), 'invalid residual coordinate')
    return out


def idw_residual(
    fit_coordinates: np.ndarray,
    fit_residuals: np.ndarray,
    query_coordinate: np.ndarray,
    neighbors: int,
    power: float,
) -> np.ndarray:
    coords = np.asarray(fit_coordinates, dtype=np.float64)
    residuals = np.asarray(fit_residuals, dtype=np.float64)
    query = np.asarray(query_coordinate, dtype=np.float64)
    req(coords.ndim == 2 and coords.shape[1] == 5, 'fit coordinate shape drift')
    req(residuals.ndim == 2 and residuals.shape == (coords.shape[0], 3), 'fit residual shape drift')
    req(query.shape == (5,), 'query coordinate shape drift')
    req(coords.shape[0] > 0 and 1 <= int(neighbors) <= coords.shape[0], 'invalid neighbor count')
    req(float(power) > 0.0 and math.isfinite(float(power)), 'invalid IDW power')
    req(np.all(np.isfinite(coords)) and np.all(np.isfinite(residuals)) and np.all(np.isfinite(query)), 'nonfinite IDW input')
    distances = np.sqrt(np.sum((coords - query[None, :]) ** 2, axis=1, dtype=np.float64), dtype=np.float64)
    order = np.argsort(distances, kind='stable')
    first = int(order[0])
    if float(distances[first]) == 0.0:
        return residuals[first].copy()
    idx = order[:int(neighbors)]
    d = distances[idx]
    weights = 1.0 / (d ** float(power))
    weights = weights / np.sum(weights, dtype=np.float64)
    result = np.sum(residuals[idx] * weights[:, None], axis=0, dtype=np.float64)
    req(result.shape == (3,) and np.all(np.isfinite(result)), 'invalid IDW residual result')
    return result


def apply_primary_residual(base_prediction: Iterable[float], residual: Iterable[float], shrinkage: float) -> np.ndarray:
    base = np.asarray(list(base_prediction), dtype=np.float64)
    corr = np.asarray(list(residual), dtype=np.float64)
    req(base.shape == (13,), '13-target base prediction required')
    req(corr.shape == (3,), '3-primary residual required')
    alpha = float(shrinkage)
    req(alpha in (0.25, 0.5, 0.75, 1.0), 'unfrozen shrinkage')
    out = base.copy()
    out[:3] = base[:3] + alpha * corr
    req(np.array_equal(out[3:], base[3:]), 'shape changed by primary residual correction')
    return out


def training_gate_checks(row: dict[str, Any], gates: dict[str, Any]) -> dict[str, bool]:
    return {
        'looMeanPrimary': float(row['looMeanPrimaryMale']) <= float(gates['looMeanPrimaryMaleMax']),
        'looWorstSinglePrimary': float(row['looWorstSinglePrimaryLogError']) <= float(gates['looWorstSinglePrimaryLogErrorMax']),
        'looMeanRawShape': float(row['looMeanRawShapeNrmse']) <= float(gates['looMeanRawShapeNrmseMax']),
        'looWorstUncertaintyAdjustedShape': float(row['looWorstUncertaintyAdjustedShapeNrmse']) <= float(gates['looWorstUncertaintyAdjustedShapeNrmseMax']),
        'looWorstUncertaintyAdjustedSingleCoefficient': float(row['looWorstUncertaintyAdjustedSingleCoefficientError']) <= float(gates['looWorstUncertaintyAdjustedSingleCoefficientErrorMax']),
        'boundaryWorstPrimary': float(row['boundaryWorstPrimaryMale']) <= float(gates['boundaryWorstPrimaryMaleMax']),
        'boundaryWorstRawShape': float(row['boundaryWorstRawShapeNrmse']) <= float(gates['boundaryWorstRawShapeNrmseMax']),
        'looPrimaryBaselineImprovement': float(row['looPrimaryImprovementVsBaselineFraction']) >= float(gates['looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction']),
    }


def primary_stress_score(row: dict[str, Any], gates: dict[str, Any]) -> float:
    mean_ratio = float(row['looMeanPrimaryMale']) / float(gates['looMeanPrimaryMaleMax'])
    worst_ratio = float(row['looWorstSinglePrimaryLogError']) / float(gates['looWorstSinglePrimaryLogErrorMax'])
    boundary_ratio = float(row['boundaryWorstPrimaryMale']) / float(gates['boundaryWorstPrimaryMaleMax'])
    return float(max(mean_ratio, worst_ratio, boundary_ratio) + 0.10 * mean_ratio)


def legacy_overall_score(row: dict[str, Any], gates: dict[str, Any]) -> float:
    mean_primary = float(row['looMeanPrimaryMale']) / float(gates['looMeanPrimaryMaleMax'])
    worst_primary = float(row['looWorstSinglePrimaryLogError']) / float(gates['looWorstSinglePrimaryLogErrorMax'])
    mean_shape = float(row['looMeanRawShapeNrmse']) / float(gates['looMeanRawShapeNrmseMax'])
    worst_ua_shape = float(row['looWorstUncertaintyAdjustedShapeNrmse']) / float(gates['looWorstUncertaintyAdjustedShapeNrmseMax'])
    worst_ua_single = float(row['looWorstUncertaintyAdjustedSingleCoefficientError']) / float(gates['looWorstUncertaintyAdjustedSingleCoefficientErrorMax'])
    boundary_primary = float(row['boundaryWorstPrimaryMale']) / float(gates['boundaryWorstPrimaryMaleMax'])
    boundary_shape = float(row['boundaryWorstRawShapeNrmse']) / float(gates['boundaryWorstRawShapeNrmseMax'])
    return float(max(mean_primary, worst_primary, mean_shape, worst_ua_shape, worst_ua_single, boundary_primary, boundary_shape) + 0.10 * (mean_primary + mean_shape))


def hyperparameter_key(row: dict[str, Any]) -> tuple[Any, ...]:
    if row['familyId'] == CONTROL_FAMILY:
        return ('', float(row.get('primaryRidge', 1e-5)), 0, 0.0, 0.0)
    req(row['familyId'] == NEW_FAMILY, 'unknown family in ranking')
    return (
        str(row['residualCoordinateSystem']),
        float(row['primaryRidge']),
        int(row['residualNeighbors']),
        float(row['residualPower']),
        float(row['residualShrinkage']),
    )


def ranking_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        float(row['primaryStressScore']),
        float(row['legacyOverallSelectionScore']),
        float(row['boundaryWorstPrimaryMale']),
        float(row['looWorstSinglePrimaryLogError']),
        float(row['looMeanPrimaryMale']),
        int(row['complexityRank']),
        str(row['familyId']),
        hyperparameter_key(row),
    )


def finalize_result(spec: dict[str, Any], metrics: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    out = {**copy.deepcopy(spec), **copy.deepcopy(metrics)}
    checks = training_gate_checks(out, gates)
    out['gateChecks'] = checks
    out['eligible'] = bool(all(checks.values()))
    out['primaryStressScore'] = primary_stress_score(out, gates)
    out['legacyOverallSelectionScore'] = legacy_overall_score(out, gates)
    return out


def select_candidate(results: list[dict[str, Any]], protocol: dict[str, Any]) -> tuple[str, dict[str, Any] | None, list[dict[str, Any]]]:
    validate_protocol(protocol)
    req(len(results) == 145, '145 evaluated candidates required')
    req(sum(r['familyId'] == CONTROL_FAMILY for r in results) == 1, 'one control result required')
    req(sum(r['familyId'] == NEW_FAMILY for r in results) == 144, '144 changed results required')
    eligible = sorted([r for r in results if r['eligible']], key=ranking_key)
    ordered = sorted(results, key=lambda r: (not bool(r['eligible']), *ranking_key(r)))
    if not eligible:
        return 'NO_ELIGIBLE_LEVEL_B_V3_TRAINING_ONLY_MODEL_NO_NEW_VALIDATION', None, ordered
    best = eligible[0]
    control = next(r for r in results if r['familyId'] == CONTROL_FAMILY)
    if best['familyId'] == CONTROL_FAMILY:
        return 'NO_TRAINING_ONLY_EVIDENCE_FOR_CHANGED_MODEL_NO_NEW_VALIDATION', best, ordered
    req(ranking_key(best) < ranking_key(control), 'changed candidate did not strictly outrank control')
    return 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', best, ordered


def make_hybrid_model(
    fit_records: list[dict[str, Any]],
    base_model: dict[str, Any],
    selected_spec: dict[str, Any],
    target_callback: Callable[[dict[str, Any]], np.ndarray],
    base_predict_callback: Callable[[dict[str, Any], dict[str, Any]], np.ndarray],
) -> dict[str, Any]:
    req(selected_spec['familyId'] == NEW_FAMILY, 'hybrid model requires changed family')
    system = str(selected_spec['residualCoordinateSystem'])
    coords: list[list[float]] = []
    residuals: list[list[float]] = []
    for record in fit_records:
        truth = np.asarray(target_callback(record), dtype=np.float64)
        base = np.asarray(base_predict_callback(base_model, record['geometry']), dtype=np.float64)
        req(truth.shape == (13,) and base.shape == (13,), '13-target callbacks required')
        coords.append(residual_coordinates(record['geometry'], system).tolist())
        residuals.append((truth[:3] - base[:3]).tolist())
    model = {
        'kind': 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW',
        'baseModel': copy.deepcopy(base_model),
        'residualCoordinateSystem': system,
        'residualCoordinates': coords,
        'residualTargets': residuals,
        'residualNeighbors': int(selected_spec['residualNeighbors']),
        'residualPower': float(selected_spec['residualPower']),
        'residualShrinkage': float(selected_spec['residualShrinkage']),
        'fitGeometryIdsInStableOrder': [str(r['geometryId']) for r in fit_records],
    }
    model['modelCanonicalSha256'] = canonical_sha(model)
    return model


def predict_hybrid(
    model: dict[str, Any],
    geometry: dict[str, Any],
    base_predict_callback: Callable[[dict[str, Any], dict[str, Any]], np.ndarray],
) -> np.ndarray:
    req(model.get('kind') == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'hybrid model kind drift')
    base = np.asarray(base_predict_callback(model['baseModel'], geometry), dtype=np.float64)
    query = residual_coordinates(geometry, str(model['residualCoordinateSystem']))
    corr = idw_residual(
        np.asarray(model['residualCoordinates'], dtype=np.float64),
        np.asarray(model['residualTargets'], dtype=np.float64),
        query,
        int(model['residualNeighbors']),
        float(model['residualPower']),
    )
    return apply_primary_residual(base, corr, float(model['residualShrinkage']))
