#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import math
from pathlib import Path

SCENARIOS = ("native", "continental", "maritime", "desert", "desert_spheroids")
CONTRASTS = ("continental", "maritime", "desert", "desert_spheroids")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _subtract_interval(mod, left, right):
    return mod.Interval(mod._down(left.lo - right.hi), mod._up(left.hi - right.lo))


def _scenario_bounds(mod, base, asiv, base_rows, *, sun, alt, raz, elev, fixed, lo, hi):
    midpoint = (lo + hi) / 2.0
    base_selected = mod._neighbors(mod._base_query(fixed, midpoint), base_rows, 6, "coord", "id")
    asiv_selected = mod._neighbors(mod._asiv_query(fixed, midpoint), asiv["training"], 8, "coord", "cellId")
    aod_lo = mod.AOD_MIN + lo * (mod.AOD_MAX - mod.AOD_MIN)
    aod_hi = mod.AOD_MIN + hi * (mod.AOD_MAX - mod.AOD_MIN)

    polynomial = mod._primary_poly_bound(base, sun, alt, raz, elev, aod_lo, aod_hi, 0)
    residual = mod._idw_bound(base_rows, "coord", "target", fixed, 4, base_selected, lo, hi, 1, 0)
    native = polynomial.add(residual)
    bounds = {"native": native}
    for contrast_index, scenario in enumerate(CONTRASTS):
        contrast = mod._idw_bound(
            asiv["training"], "coord", "target", fixed[:3], 3, asiv_selected,
            lo, hi, 2, contrast_index * 3,
        )
        bounds[scenario] = native.add(contrast)
    return bounds


def certify_pair(mod, base, asiv, *, alt, raz, elev=30.0, aod_lo=0.05, aod_hi=0.40,
                 log_tolerance=1e-4, max_depth=50, max_nodes=400000):
    fixed3 = mod._geometry_fixed(3.0, alt, raz, elev)
    fixed6 = mod._geometry_fixed(6.0, alt, raz, elev)
    x_lo, x_hi = mod._x_aod(aod_lo), mod._x_aod(aod_hi)
    base_rows = [
        {"coord": coord, "target": target, "id": index}
        for index, (coord, target) in enumerate(zip(base["residualCoordinates"], base["residualTargets"]))
    ]

    cuts = {x_lo, x_hi}
    for fixed in (fixed3, fixed6):
        cuts.update(mod._pairwise_crossings(fixed, base_rows, "coord", 4, x_lo, x_hi))
        cuts.update(mod._pairwise_crossings(fixed[:3], asiv["training"], "coord", 3, x_lo, x_hi))
        for row in base_rows:
            if all(fixed[j] == row["coord"][j] for j in range(4)) and x_lo < row["coord"][4] < x_hi:
                cuts.add(row["coord"][4])
        for row in asiv["training"]:
            if all(fixed[j] == row["coord"][j] for j in range(3)) and x_lo < row["coord"][3] < x_hi:
                cuts.add(row["coord"][3])
    cuts = sorted(cuts)

    result = {
        s: {"outerMin": math.inf, "innerMin": math.inf, "innerMax": -math.inf, "outerMax": -math.inf}
        for s in SCENARIOS
    }
    failures = []
    nodes = 0
    max_depth_seen = 0

    def aod_from_x(x):
        return mod.AOD_MIN + x * (mod.AOD_MAX - mod.AOD_MIN)

    def absorb_point(x):
        aod = aod_from_x(x)
        p3 = mod._point_prediction(base, asiv, 3.0, alt, raz, elev, aod)
        p6 = mod._point_prediction(base, asiv, 6.0, alt, raz, elev, aod)
        for s in SCENARIOS:
            value = p6[s][0] - p3[s][0]
            row = result[s]
            row["innerMin"] = min(row["innerMin"], value)
            row["innerMax"] = max(row["innerMax"], value)
            row["outerMin"] = min(row["outerMin"], value)
            row["outerMax"] = max(row["outerMax"], value)

    for x in cuts:
        absorb_point(x)

    def recurse(lo, hi, depth):
        nonlocal nodes, max_depth_seen
        nodes += 1
        max_depth_seen = max(max_depth_seen, depth)
        if nodes > max_nodes:
            failures.append("MAX_NODES")
            return

        b3 = _scenario_bounds(mod, base, asiv, base_rows, sun=3.0, alt=alt, raz=raz, elev=elev,
                              fixed=fixed3, lo=lo, hi=hi)
        b6 = _scenario_bounds(mod, base, asiv, base_rows, sun=6.0, alt=alt, raz=raz, elev=elev,
                              fixed=fixed6, lo=lo, hi=hi)
        delta_bounds = {s: _subtract_interval(mod, b6[s], b3[s]) for s in SCENARIOS}
        max_width = max(v.width for v in delta_bounds.values())
        midpoint = (lo + hi) / 2.0

        if max_width <= log_tolerance:
            absorb_point(midpoint)
            for s, interval in delta_bounds.items():
                row = result[s]
                row["outerMin"] = min(row["outerMin"], interval.lo)
                row["outerMax"] = max(row["outerMax"], interval.hi)
            return

        if depth >= max_depth:
            failures.append(f"MAX_DEPTH:{lo:.17g}:{hi:.17g}")
            absorb_point(midpoint)
            for s, interval in delta_bounds.items():
                row = result[s]
                row["outerMin"] = min(row["outerMin"], interval.lo)
                row["outerMax"] = max(row["outerMax"], interval.hi)
            return

        recurse(lo, midpoint, depth + 1)
        recurse(midpoint, hi, depth + 1)

    for lo, hi in zip(cuts, cuts[1:]):
        if hi > lo:
            recurse(lo, hi, 0)

    certified = not failures
    for s in SCENARIOS:
        row = result[s]
        if math.isinf(row["outerMin"]):
            row["outerMin"] = row["innerMin"]
            row["outerMax"] = row["innerMax"]
        row["minCertificationGap"] = row["innerMin"] - row["outerMin"]
        row["maxCertificationGap"] = row["outerMax"] - row["innerMax"]
        if row["minCertificationGap"] > log_tolerance * 1.0001 or row["maxCertificationGap"] > log_tolerance * 1.0001:
            certified = False

    return {
        "algorithmId": "CERTIFIED_SAME_AOD_SAME_SCENARIO_TWILIGHT_SHAPE_INTERVAL_BNB_V1",
        "quantity": "ln_photopic_L_at_6deg_minus_ln_photopic_L_at_3deg",
        "aod550Interval": [aod_lo, aod_hi],
        "sameAodRequired": True,
        "sameScenarioRequired": True,
        "logTolerance": log_tolerance,
        "partitionBreakpoints": len(cuts),
        "branchNodes": nodes,
        "maximumDepth": max_depth_seen,
        "certified": certified,
        "failures": failures,
        "scenarios": result,
    }


def worker(task):
    index, alt, raz, obs3, obs6, paths = task
    support_mod = load_module(Path(paths["support"]), f"shape_support_{index}")
    mod = load_module(Path(paths["model"]), f"shape_model_{index}")
    base_support = support_mod.load_bound_runtime(Path(paths["base"]))
    base = mod.load_base_runtime(Path(paths["base"]))
    asiv = mod.load_asiv_runtime(Path(paths["asiv"]))

    support = {}
    for dep in (3.0, 6.0):
        support[str(int(dep))] = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_support["supportCoordinates"],
            sun_depression_deg=dep, target_altitude_deg=alt, relative_azimuth_deg=raz,
            observer_elevation_m=30.0, aod550_min=0.05, aod550_max=0.40,
        )
    admitted = all(v["supportedAcrossEntireInterval"] for v in support.values())
    rec = {
        "targetAltitudeDeg": alt,
        "relativeAzimuthDeg": raz,
        "observedLogL6OverL3": math.log(obs6 / obs3),
        "observedFactorL3OverL6": obs3 / obs6,
        "support": support,
        "supportQualified": admitted,
    }
    if not admitted:
        rec["status"] = "PAIR_NOT_SUPPORTED_ACROSS_FULL_AOD_INTERVAL"
        return index, rec

    cert = certify_pair(mod, base, asiv, alt=alt, raz=raz)
    rec["certification"] = cert
    if not cert["certified"]:
        rec["status"] = "PAIR_SHAPE_EXTREMA_NOT_CERTIFIED"
        return index, rec

    lo = min(cert["scenarios"][s]["outerMin"] for s in SCENARIOS)
    hi = max(cert["scenarios"][s]["outerMax"] for s in SCENARIOS)
    obs = rec["observedLogL6OverL3"]
    miss = 0.0 if lo <= obs <= hi else (obs - lo if obs < lo else obs - hi)
    rec.update({
        "status": "CERTIFIED_PAIRED_SHAPE_EVALUATED",
        "modelLogL6OverL3UnionOuter": [lo, hi],
        "modelFactorL3OverL6UnionOuter": [math.exp(-hi), math.exp(-lo)],
        "signedSetMissLog": miss,
        "absoluteSetMissLog": abs(miss),
        "direction": "OBSERVED_DIMS_FASTER_THAN_MODEL" if miss < 0 else ("OBSERVED_DIMS_SLOWER_THAN_MODEL" if miss > 0 else "INSIDE_MODEL_ENVELOPE"),
    })
    return index, rec


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--base-runtime', type=Path, required=True)
    p.add_argument('--asiv-runtime', type=Path, required=True)
    p.add_argument('--support-evaluator', type=Path, required=True)
    p.add_argument('--extrema-evaluator', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    if not 1 <= a.workers <= 8:
        raise ValueError('workers must be 1..8')

    data = json.loads(a.dataset.read_text())
    by_geom = {}
    for row in data['rows']:
        key = (float(row['targetAltitudeDeg']), float(row['relativeAzimuthDeg']))
        by_geom.setdefault(key, {})[int(row['sunDepressionDeg'])] = float(row['observedPhotopicLuminanceCdM2'])
    pairs = [(alt, raz, d[3], d[6]) for (alt, raz), d in sorted(by_geom.items()) if 3 in d and 6 in d]
    assert len(pairs) == 24
    paths = {'base': str(a.base_runtime), 'asiv': str(a.asiv_runtime),
             'support': str(a.support_evaluator), 'model': str(a.extrema_evaluator)}
    tasks = [(i, *pair, paths) for i, pair in enumerate(pairs)]
    result_map = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        futs = [pool.submit(worker, task) for task in tasks]
        for fut in concurrent.futures.as_completed(futs):
            i, rec = fut.result()
            result_map[i] = rec
            print(f"completed {i+1:02d}/24 alt={rec['targetAltitudeDeg']} az={rec['relativeAzimuthDeg']} {rec['status']}", flush=True)
    rows = [result_map[i] for i in range(24)]
    qualified = [r for r in rows if r['supportQualified']]
    certified = [r for r in qualified if r['status'] == 'CERTIFIED_PAIRED_SHAPE_EVALUATED']
    outside = [r for r in certified if r['signedSetMissLog'] != 0]
    faster = [r for r in outside if r['signedSetMissLog'] < 0]
    slower = [r for r in outside if r['signedSetMissLog'] > 0]
    out = {
        "schemaVersion": 1,
        "resultId": "koomen-1952-maryland-certified-paired-shape-v1",
        "claimClass": "MATHEMATICALLY_CERTIFIED_MODEL_SHAPE_ENVELOPE_AGAINST_PUBLISHED_HISTORICAL_DATA_NOT_STRICT_MODERN_VALIDATION",
        "pairCount": 24,
        "supportQualifiedPairCount": len(qualified),
        "certifiedPairCount": len(certified),
        "uncertifiedQualifiedPairCount": len(qualified) - len(certified),
        "outsideCertifiedEnvelopeCount": len(outside),
        "insideCertifiedEnvelopeCount": len(certified) - len(outside),
        "observedDimsFasterCount": len(faster),
        "observedDimsSlowerCount": len(slower),
        "rows": rows,
        "boundary": {
            "pandoraTargetDataUsed": False,
            "historicalPublishedValuesAlreadyOpen": True,
            "strictModernValidationClaimAuthorized": False,
            "modelRetuningAuthorized": False,
            "productionAuthorization": False,
        },
    }
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({k: out[k] for k in (
        'pairCount','supportQualifiedPairCount','certifiedPairCount','uncertifiedQualifiedPairCount',
        'outsideCertifiedEnvelopeCount','insideCertifiedEnvelopeCount','observedDimsFasterCount','observedDimsSlowerCount'
    )}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
