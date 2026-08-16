#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np

import engine_v1 as engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    engine.validate_protocol(protocol)
    specs = engine.candidate_specs(protocol)
    assert len(specs) == 145
    assert sum(x['familyId'] == engine.NEW_FAMILY for x in specs) == 144
    assert specs[0]['complexityRank'] == 7
    assert all(x['complexityRank'] == 9 for x in specs[1:])

    geometry = {
        'sunDepressionDeg': 10.5,
        'targetAltitudeDeg': 30.0,
        'relativeAzimuthDeg': 180.0,
        'observerElevationM': 2500.0,
        'aod550': 0.4,
    }
    physical = engine.residual_coordinates(geometry, 'PHYSICAL_NORMALIZED_IDW_COORDINATES')
    v1 = engine.residual_coordinates(geometry, 'V1_IDW_COS_COORDINATES')
    assert np.allclose(physical, [1.0, 0.5, 0.0, 1.0, 1.0], rtol=0.0, atol=1e-15)
    assert np.allclose(v1, [1.0, 25.0 / 75.0, 0.0, 1.0, 1.0], rtol=0.0, atol=1e-15)

    coordinates = np.array([
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [2, 0, 0, 0, 0],
    ], dtype=np.float64)
    residuals = np.array([
        [1, 2, 3],
        [9, 9, 9],
        [3, 4, 5],
        [5, 6, 7],
    ], dtype=np.float64)
    assert np.array_equal(engine.idw_residual(coordinates, residuals, np.zeros(5), 4, 1.0), residuals[0])
    query = np.array([0.5, 0, 0, 0, 0], dtype=np.float64)
    assert np.allclose(engine.idw_residual(coordinates, residuals, query, 3, 1.0), np.mean(residuals[:3], axis=0), rtol=0.0, atol=1e-15)

    base = np.arange(13, dtype=np.float64)
    corrected = engine.apply_primary_residual(base, [2, -4, 6], 0.5)
    assert np.array_equal(corrected[3:], base[3:])
    assert np.array_equal(corrected[:3], np.array([1, -1, 5], dtype=np.float64))

    gates = protocol['trainingOnlyReadinessGates']
    metrics = {
        'looMeanPrimaryMale': 0.1,
        'looWorstSinglePrimaryLogError': 0.2,
        'looMeanRawShapeNrmse': 0.5,
        'looWorstUncertaintyAdjustedShapeNrmse': 0.6,
        'looWorstUncertaintyAdjustedSingleCoefficientError': 1.0,
        'boundaryWorstPrimaryMale': 0.2,
        'boundaryWorstRawShapeNrmse': 1.0,
        'looPrimaryImprovementVsBaselineFraction': 0.8,
    }
    control = engine.finalize_result(specs[0], metrics, gates)
    changed = engine.finalize_result(specs[1], metrics, gates)
    status, best, _ = engine.select_candidate([control] + [copy.deepcopy(changed) for _ in range(144)], protocol)
    assert status == 'NO_TRAINING_ONLY_EVIDENCE_FOR_CHANGED_MODEL_NO_NEW_VALIDATION'
    assert best is not None and best['familyId'] == engine.CONTROL_FAMILY

    results = [control]
    for index, spec in enumerate(specs[1:]):
        values = dict(metrics)
        if index == 0:
            values.update(looMeanPrimaryMale=0.05, looWorstSinglePrimaryLogError=0.1, boundaryWorstPrimaryMale=0.1)
        else:
            values['boundaryWorstPrimaryMale'] = 0.31
        results.append(engine.finalize_result(spec, values, gates))
    status, best, _ = engine.select_candidate(results, protocol)
    assert status == 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE'
    assert best is not None and best['candidateId'] == specs[1]['candidateId']

    bad = []
    for spec in specs:
        values = dict(metrics)
        values['boundaryWorstPrimaryMale'] = 0.31
        bad.append(engine.finalize_result(spec, values, gates))
    status, best, _ = engine.select_candidate(bad, protocol)
    assert status == 'NO_ELIGIBLE_LEVEL_B_V3_TRAINING_ONLY_MODEL_NO_NEW_VALIDATION'
    assert best is None

    records = [
        {
            'geometryId': 'a',
            'geometry': {'sunDepressionDeg': 2, 'targetAltitudeDeg': 5, 'relativeAzimuthDeg': 0, 'observerElevationM': 0, 'aod550': 0.05},
            'truth': np.arange(13, dtype=float),
        },
        {
            'geometryId': 'b',
            'geometry': {'sunDepressionDeg': 10.5, 'targetAltitudeDeg': 80, 'relativeAzimuthDeg': 180, 'observerElevationM': 2500, 'aod550': 0.4},
            'truth': np.arange(13, dtype=float) + 1.0,
        },
    ]
    def target(record):
        return record['truth']
    def predict(model, geometry):
        return np.arange(13, dtype=float) + float(model.get('offset', 0.0))
    selected = dict(specs[1])
    selected['residualNeighbors'] = 2
    selected['residualPower'] = 1.0
    selected['residualShrinkage'] = 0.5
    model = engine.make_hybrid_model(records, {'offset': 0.0}, selected, target, predict)
    prediction = engine.predict_hybrid(model, records[0]['geometry'], predict)
    assert np.array_equal(prediction[3:], np.arange(13, dtype=float)[3:])
    assert np.array_equal(prediction[:3], np.arange(3, dtype=float))

    print('PASS: 145-candidate deterministic residual-IDW engine, tie/exit rules, and primary-only model semantics')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
