#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import math
from pathlib import Path

SCENARIOS = ("native", "continental", "maritime", "desert", "desert_spheroids")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def certify_observed_dims_faster(pair_mod, model_mod, base, asiv, *, alt, raz, observed_delta,
                                  elev=30.0, aod_lo=0.05, aod_hi=0.40,
                                  max_depth=50, max_nodes=400000):
    """Prove observed_delta < model_delta for every admitted AOD and scenario.

    model_delta is ln L(6 deg) - ln L(3 deg), with the same AOD and same
    aerosol scenario at both solar depressions. Interval arithmetic is outward
    rounded by the already-reviewed evaluator helpers. Unlike full extrema
    certification, a node stops as soon as its conservative lower bound is
    already above the published observed value.
    """
    fixed3 = model_mod._geometry_fixed(3.0, alt, raz, elev)
    fixed6 = model_mod._geometry_fixed(6.0, alt, raz, elev)
    x_lo, x_hi = model_mod._x_aod(aod_lo), model_mod._x_aod(aod_hi)
    base_rows = [
        {"coord": coord, "target": target, "id": index}
        for index, (coord, target) in enumerate(zip(base["residualCoordinates"], base["residualTargets"]))
    ]

    cuts = {x_lo, x_hi}
    for fixed in (fixed3, fixed6):
        cuts.update(model_mod._pairwise_crossings(fixed, base_rows, "coord", 4, x_lo, x_hi))
        cuts.update(model_mod._pairwise_crossings(fixed[:3], asiv["training"], "coord", 3, x_lo, x_hi))
        for row in base_rows:
            if all(fixed[j] == row["coord"][j] for j in range(4)) and x_lo < row["coord"][4] < x_hi:
                cuts.add(row["coord"][4])
        for row in asiv["training"]:
            if all(fixed[j] == row["coord"][j] for j in range(3)) and x_lo < row["coord"][3] < x_hi:
                cuts.add(row["coord"][3])
    cuts = sorted(cuts)

    nodes = 0
    max_depth_seen = 0
    minimum_certified_separation = math.inf
    failures = []
    violating_examples = []

    def aod_from_x(x):
        return model_mod.AOD_MIN + x * (model_mod.AOD_MAX - model_mod.AOD_MIN)

    # Partition boundaries are part of the closed AOD interval. Check them
    # explicitly using a downward-rounded point value before proving interiors.
    for x in cuts:
        aod = aod_from_x(x)
        p3 = model_mod._point_prediction(base, asiv, 3.0, alt, raz, elev, aod)
        p6 = model_mod._point_prediction(base, asiv, 6.0, alt, raz, elev, aod)
        for scenario in SCENARIOS:
            value = p6[scenario][0] - p3[scenario][0]
            lower = model_mod._down(value)
            separation = lower - observed_delta
            minimum_certified_separation = min(minimum_certified_separation, separation)
            if separation <= 0.0:
                failures.append("BOUNDARY_POINT_NOT_STRICTLY_ABOVE_OBSERVED")
                if len(violating_examples) < 8:
                    violating_examples.append({
                        "kind": "boundaryPoint",
                        "aod550": aod,
                        "scenario": scenario,
                        "modelDelta": value,
                        "observedDelta": observed_delta,
                    })
                return {
                    "algorithmId": "CERTIFIED_OBSERVED_FASTER_SEPARATION_INTERVAL_BNB_V1",
                    "certifiedObservedDimsFasterThanAllModel": False,
                    "aod550Interval": [aod_lo, aod_hi],
                    "sameAodRequired": True,
                    "sameScenarioRequired": True,
                    "partitionBreakpoints": len(cuts),
                    "branchNodes": nodes,
                    "maximumDepth": max_depth_seen,
                    "minimumCertifiedSeparationLog": minimum_certified_separation,
                    "failures": failures,
                    "violatingExamples": violating_examples,
                }

    def recurse(lo, hi, depth):
        nonlocal nodes, max_depth_seen, minimum_certified_separation
        nodes += 1
        max_depth_seen = max(max_depth_seen, depth)
        if nodes > max_nodes:
            failures.append("MAX_NODES")
            return False

        b3 = pair_mod._scenario_bounds(model_mod, base, asiv, base_rows,
                                       sun=3.0, alt=alt, raz=raz, elev=elev,
                                       fixed=fixed3, lo=lo, hi=hi)
        b6 = pair_mod._scenario_bounds(model_mod, base, asiv, base_rows,
                                       sun=6.0, alt=alt, raz=raz, elev=elev,
                                       fixed=fixed6, lo=lo, hi=hi)
        deltas = {s: pair_mod._subtract_interval(model_mod, b6[s], b3[s]) for s in SCENARIOS}

        min_sep_here = min(interval.lo - observed_delta for interval in deltas.values())
        if min_sep_here > 0.0:
            minimum_certified_separation = min(minimum_certified_separation, min_sep_here)
            return True

        # If an entire scenario interval is already at/below the observation,
        # the desired directional proposition is false for this node.
        for scenario, interval in deltas.items():
            if interval.hi <= observed_delta:
                failures.append("MODEL_INTERVAL_NOT_SLOWER_THAN_OBSERVED")
                if len(violating_examples) < 8:
                    violating_examples.append({
                        "kind": "interval",
                        "aod550": [aod_from_x(lo), aod_from_x(hi)],
                        "scenario": scenario,
                        "modelDeltaInterval": [interval.lo, interval.hi],
                        "observedDelta": observed_delta,
                    })
                return False

        if depth >= max_depth:
            failures.append("MAX_DEPTH_WITH_OVERLAP")
            return False

        midpoint = (lo + hi) / 2.0
        return recurse(lo, midpoint, depth + 1) and recurse(midpoint, hi, depth + 1)

    ok = True
    for lo, hi in zip(cuts, cuts[1:]):
        if hi > lo and not recurse(lo, hi, 0):
            ok = False
            break

    return {
        "algorithmId": "CERTIFIED_OBSERVED_FASTER_SEPARATION_INTERVAL_BNB_V1",
        "certifiedObservedDimsFasterThanAllModel": bool(ok and not failures and minimum_certified_separation > 0.0),
        "aod550Interval": [aod_lo, aod_hi],
        "sameAodRequired": True,
        "sameScenarioRequired": True,
        "partitionBreakpoints": len(cuts),
        "branchNodes": nodes,
        "maximumDepth": max_depth_seen,
        "minimumCertifiedSeparationLog": minimum_certified_separation if math.isfinite(minimum_certified_separation) else None,
        "failures": failures,
        "violatingExamples": violating_examples,
    }


def worker(task):
    index, alt, raz, obs3, obs6, paths = task
    support_mod = load_module(Path(paths["support"]), f"sep_support_{index}")
    model_mod = load_module(Path(paths["model"]), f"sep_model_{index}")
    pair_mod = load_module(Path(paths["pair"]), f"sep_pair_{index}")
    base_support = support_mod.load_bound_runtime(Path(paths["base"]))
    base = model_mod.load_base_runtime(Path(paths["base"]))
    asiv = model_mod.load_asiv_runtime(Path(paths["asiv"]))

    support = {}
    for dep in (3.0, 6.0):
        support[str(int(dep))] = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_support["supportCoordinates"],
            sun_depression_deg=dep,
            target_altitude_deg=alt,
            relative_azimuth_deg=raz,
            observer_elevation_m=30.0,
            aod550_min=0.05,
            aod550_max=0.40,
        )
    admitted = all(v["supportedAcrossEntireInterval"] for v in support.values())
    observed_delta = math.log(obs6 / obs3)
    rec = {
        "targetAltitudeDeg": alt,
        "relativeAzimuthDeg": raz,
        "observedLogL6OverL3": observed_delta,
        "observedFactorL3OverL6": obs3 / obs6,
        "support": support,
        "supportQualified": admitted,
    }
    if not admitted:
        rec["status"] = "PAIR_NOT_SUPPORTED_ACROSS_FULL_AOD_INTERVAL"
        return index, rec

    cert = certify_observed_dims_faster(
        pair_mod, model_mod, base, asiv,
        alt=alt, raz=raz, observed_delta=observed_delta,
    )
    rec["separationCertificate"] = cert
    rec["status"] = (
        "CERTIFIED_OBSERVED_DIMS_FASTER_THAN_ALL_MODEL"
        if cert["certifiedObservedDimsFasterThanAllModel"]
        else "DIRECTIONAL_SEPARATION_NOT_CERTIFIED"
    )
    return index, rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--base-runtime', type=Path, required=True)
    p.add_argument('--asiv-runtime', type=Path, required=True)
    p.add_argument('--support-evaluator', type=Path, required=True)
    p.add_argument('--extrema-evaluator', type=Path, required=True)
    p.add_argument('--pair-evaluator', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    if not 1 <= a.workers <= 8:
        raise ValueError('workers must be 1..8')

    data = json.loads(a.dataset.read_text(encoding='utf-8'))
    by_geom = {}
    for row in data['rows']:
        key = (float(row['targetAltitudeDeg']), float(row['relativeAzimuthDeg']))
        by_geom.setdefault(key, {})[int(row['sunDepressionDeg'])] = float(row['observedPhotopicLuminanceCdM2'])
    pairs = [(alt, raz, d[3], d[6]) for (alt, raz), d in sorted(by_geom.items()) if 3 in d and 6 in d]
    assert len(pairs) == 24

    paths = {
        'base': str(a.base_runtime), 'asiv': str(a.asiv_runtime),
        'support': str(a.support_evaluator), 'model': str(a.extrema_evaluator),
        'pair': str(a.pair_evaluator),
    }
    result_map = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(worker, (i, *pair, paths)) for i, pair in enumerate(pairs)]
        for future in concurrent.futures.as_completed(futures):
            i, rec = future.result()
            result_map[i] = rec
            print(f"completed {i+1:02d}/24 alt={rec['targetAltitudeDeg']} az={rec['relativeAzimuthDeg']} {rec['status']}", flush=True)

    rows = [result_map[i] for i in range(24)]
    qualified = [r for r in rows if r['supportQualified']]
    certified = [r for r in qualified if r['status'] == 'CERTIFIED_OBSERVED_DIMS_FASTER_THAN_ALL_MODEL']
    not_certified = [r for r in qualified if r['status'] == 'DIRECTIONAL_SEPARATION_NOT_CERTIFIED']
    min_sep = min(
        (r['separationCertificate']['minimumCertifiedSeparationLog'] for r in certified),
        default=None,
    )
    out = {
        'schemaVersion': 1,
        'resultId': 'koomen-1952-maryland-shape-separation-certificate-v1',
        'claimClass': 'DIRECTIONAL_INTERVAL_CERTIFICATE_AGAINST_PUBLISHED_HISTORICAL_DATA_NOT_STRICT_MODERN_VALIDATION',
        'pairCount': 24,
        'supportQualifiedPairCount': len(qualified),
        'certifiedObservedDimsFasterPairCount': len(certified),
        'directionalSeparationNotCertifiedPairCount': len(not_certified),
        'minimumCertifiedSeparationLogAcrossCertifiedPairs': min_sep,
        'rows': rows,
        'boundary': {
            'pandoraTargetDataUsed': False,
            'historicalPublishedValuesAlreadyOpen': True,
            'strictModernValidationClaimAuthorized': False,
            'modelRetuningAuthorized': False,
            'productionAuthorization': False,
            'fullModelExtremaComputed': False,
            'certificateQuestionOnly': 'Is observed ln(L6/L3) strictly smaller than every frozen same-AOD same-scenario model prediction?'
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in (
        'pairCount','supportQualifiedPairCount','certifiedObservedDimsFasterPairCount',
        'directionalSeparationNotCertifiedPairCount','minimumCertifiedSeparationLogAcrossCertifiedPairs'
    )}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
