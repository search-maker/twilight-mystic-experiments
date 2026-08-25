#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

SCENARIOS = ("native", "continental", "maritime", "desert", "desert_spheroids")
AOD_GRID = tuple(0.05 + 0.005 * i for i in range(71))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def interval_miss(value, lo, hi):
    if lo <= value <= hi:
        return 0.0
    return value - lo if value < lo else value - hi


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--base-runtime', type=Path, required=True)
    p.add_argument('--asiv-runtime', type=Path, required=True)
    p.add_argument('--support-evaluator', type=Path, required=True)
    p.add_argument('--extrema-evaluator', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()

    support_mod = load_module(a.support_evaluator, 'koomen_grid_support')
    model_mod = load_module(a.extrema_evaluator, 'koomen_grid_model')
    base_support = support_mod.load_bound_runtime(a.base_runtime)
    base = model_mod.load_base_runtime(a.base_runtime)
    asiv = model_mod.load_asiv_runtime(a.asiv_runtime)
    data = json.loads(a.dataset.read_text())
    assert len(data['rows']) == data['selection']['rowCount'] == 48

    absolute = []
    prediction_cache = {}
    for row in data['rows']:
        key = (float(row['sunDepressionDeg']), float(row['targetAltitudeDeg']), float(row['relativeAzimuthDeg']))
        support = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_support['supportCoordinates'],
            sun_depression_deg=key[0], target_altitude_deg=key[1], relative_azimuth_deg=key[2],
            observer_elevation_m=30.0, aod550_min=0.05, aod550_max=0.40,
        )
        rec = {'cellId': row['cellId'], 'geometry': key, 'support': support,
               'observedCdM2': row['observedPhotopicLuminanceCdM2']}
        if not support['supportedAcrossEntireInterval']:
            rec['status'] = 'UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL'
            absolute.append(rec)
            continue
        scenario_values = {s: [] for s in SCENARIOS}
        for aod in AOD_GRID:
            pred = model_mod._point_prediction(base, asiv, key[0], key[1], key[2], 30.0, aod)
            prediction_cache[(key[0], key[1], key[2], round(aod, 6))] = pred
            for s in SCENARIOS:
                scenario_values[s].append(pred[s][0])
        lo = min(min(v) for v in scenario_values.values())
        hi = max(max(v) for v in scenario_values.values())
        obs = math.log(float(row['observedPhotopicLuminanceCdM2']))
        miss = interval_miss(obs, lo, hi)
        rec.update({
            'status': 'GRID_DIAGNOSTIC_EVALUATED',
            'gridAodStep': 0.005,
            'modelUnionLogGridMinMax': [lo, hi],
            'modelUnionCdM2GridMinMax': [math.exp(lo), math.exp(hi)],
            'signedGridMissLog': miss,
            'absoluteGridMissLog': abs(miss),
            'scenarioLogGridMinMax': {s: [min(v), max(v)] for s, v in scenario_values.items()},
        })
        absolute.append(rec)

    by_geom = {}
    for row in data['rows']:
        by_geom.setdefault((float(row['targetAltitudeDeg']), float(row['relativeAzimuthDeg'])), {})[int(row['sunDepressionDeg'])] = row
    shape = []
    for (alt, raz), pair in sorted(by_geom.items()):
        if 3 not in pair or 6 not in pair:
            continue
        obs3 = float(pair[3]['observedPhotopicLuminanceCdM2'])
        obs6 = float(pair[6]['observedPhotopicLuminanceCdM2'])
        obs_delta = math.log(obs6 / obs3)
        deltas = []
        scenario_ranges = {}
        for s in SCENARIOS:
            vals = []
            for aod in AOD_GRID:
                p3 = prediction_cache.get((3.0, alt, raz, round(aod, 6)))
                p6 = prediction_cache.get((6.0, alt, raz, round(aod, 6)))
                if p3 is None:
                    p3 = model_mod._point_prediction(base, asiv, 3.0, alt, raz, 30.0, aod)
                if p6 is None:
                    p6 = model_mod._point_prediction(base, asiv, 6.0, alt, raz, 30.0, aod)
                vals.append(p6[s][0] - p3[s][0])
            scenario_ranges[s] = [min(vals), max(vals)]
            deltas.extend(vals)
        lo, hi = min(deltas), max(deltas)
        miss = interval_miss(obs_delta, lo, hi)
        shape.append({
            'targetAltitudeDeg': alt, 'relativeAzimuthDeg': raz,
            'observedLogL6OverL3': obs_delta,
            'observedFactorL3OverL6': obs3 / obs6,
            'modelSameAodSameScenarioLogL6OverL3GridMinMax': [lo, hi],
            'modelFactorL3OverL6GridMinMax': [math.exp(-hi), math.exp(-lo)],
            'signedGridMissLog': miss,
            'scenarioLogRatioGridMinMax': scenario_ranges,
        })

    abs_eval = [r for r in absolute if r['status'] == 'GRID_DIAGNOSTIC_EVALUATED']
    out = {
        'schemaVersion': 1,
        'diagnosticId': 'koomen-1952-maryland-fixed-aod-grid-diagnostic-v1',
        'claimClass': 'DIAGNOSTIC_ONLY_NOT_CERTIFIED_NOT_STRICT_VALIDATION',
        'aodGrid': {'min': 0.05, 'max': 0.40, 'step': 0.005, 'count': 71},
        'scenarioSet': list(SCENARIOS),
        'absolute': {
            'evaluatedCount': len(abs_eval),
            'outsideGridEnvelopeCount': sum(r['signedGridMissLog'] != 0 for r in abs_eval),
            'rows': absolute,
        },
        'shape': {
            'pairCount': len(shape),
            'outsideSameAodSameScenarioGridEnvelopeCount': sum(r['signedGridMissLog'] != 0 for r in shape),
            'pairs': shape,
        },
        'boundary': {
            'gridExtremaAreCertified': False,
            'formalPassFailAuthorized': False,
            'pandoraTargetDataUsed': False,
            'modelRetuningAuthorized': False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'absoluteEvaluatedCount': out['absolute']['evaluatedCount'],
        'absoluteOutsideGridEnvelopeCount': out['absolute']['outsideGridEnvelopeCount'],
        'shapePairCount': out['shape']['pairCount'],
        'shapeOutsideGridEnvelopeCount': out['shape']['outsideSameAodSameScenarioGridEnvelopeCount'],
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
