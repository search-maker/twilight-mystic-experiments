#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

SCENARIOS = ("native", "continental", "maritime", "desert", "desert_spheroids")
GRID_COUNT = 1001
AOD_MIN = 0.05
AOD_MAX = 0.40


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def signed_interval_miss(value: float, lo: float, hi: float) -> float:
    if lo <= value <= hi:
        return 0.0
    if value < lo:
        return value - lo
    return value - hi


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--asiv-runtime", type=Path, required=True)
    parser.add_argument("--support-evaluator", type=Path, required=True)
    parser.add_argument("--extrema-evaluator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    if dataset["selection"]["rowCount"] != 48 or len(dataset["rows"]) != 48:
        raise ValueError("frozen Koomen benchmark cardinality drift")

    support_mod = load_module(args.support_evaluator, "frozen_support_for_shape_grid")
    extrema = load_module(args.extrema_evaluator, "frozen_extrema_for_shape_grid")
    base_for_support = support_mod.load_bound_runtime(args.base_runtime)
    base = extrema.load_base_runtime(args.base_runtime)
    asiv = extrema.load_asiv_runtime(args.asiv_runtime)

    by_key = {}
    for row in dataset["rows"]:
        key = (float(row["relativeAzimuthDeg"]), float(row["targetAltitudeDeg"]))
        by_key.setdefault(key, {})[int(row["sunDepressionDeg"])] = row

    aod_grid = [AOD_MIN + (AOD_MAX - AOD_MIN) * i / (GRID_COUNT - 1) for i in range(GRID_COUNT)]
    pairs = []
    outside = []
    evaluated = 0

    for (az, alt), pair in sorted(by_key.items()):
        if 3 not in pair or 6 not in pair:
            continue
        row3 = pair[3]
        row6 = pair[6]
        elev = float(row3["observerElevationM"])
        if float(row6["observerElevationM"]) != elev:
            raise ValueError("matched Koomen pair elevation drift")
        l3 = float(row3["observedPhotopicLuminanceCdM2"])
        l6 = float(row6["observedPhotopicLuminanceCdM2"])
        observed = math.log(l6 / l3)

        support3 = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_for_support["supportCoordinates"],
            sun_depression_deg=3.0,
            target_altitude_deg=alt,
            relative_azimuth_deg=az,
            observer_elevation_m=elev,
            aod550_min=AOD_MIN,
            aod550_max=AOD_MAX,
        )
        support6 = support_mod.exact_max_nearest_support_distance(
            support_coordinates=base_for_support["supportCoordinates"],
            sun_depression_deg=6.0,
            target_altitude_deg=alt,
            relative_azimuth_deg=az,
            observer_elevation_m=elev,
            aod550_min=AOD_MIN,
            aod550_max=AOD_MAX,
        )

        rec = {
            "relativeAzimuthDeg": az,
            "targetAltitudeDeg": alt,
            "observerElevationM": elev,
            "observedLogL6OverL3": observed,
            "observedFactorL3OverL6": l3 / l6,
            "d3CellId": row3["cellId"],
            "d6CellId": row6["cellId"],
            "d3Support": support3,
            "d6Support": support6,
        }
        if not (support3["supportedAcrossEntireInterval"] and support6["supportedAcrossEntireInterval"]):
            rec["status"] = "PAIR_UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL"
            pairs.append(rec)
            continue

        values_by_scenario = {scenario: [] for scenario in SCENARIOS}
        for aod in aod_grid:
            p3 = extrema._point_prediction(base, asiv, 3.0, alt, az, elev, aod)
            p6 = extrema._point_prediction(base, asiv, 6.0, alt, az, elev, aod)
            for scenario in SCENARIOS:
                values_by_scenario[scenario].append(float(p6[scenario][0]) - float(p3[scenario][0]))

        scenario_ranges = {
            scenario: [min(values), max(values)]
            for scenario, values in values_by_scenario.items()
        }
        lo = min(bounds[0] for bounds in scenario_ranges.values())
        hi = max(bounds[1] for bounds in scenario_ranges.values())
        miss = signed_interval_miss(observed, lo, hi)
        rec.update({
            "status": "DENSE_GRID_SAME_AOD_SCENARIO_DIAGNOSTIC_EVALUATED",
            "modelLogL6OverL3GridUnion": [lo, hi],
            "modelFactorL3OverL6GridUnion": [math.exp(-hi), math.exp(-lo)],
            "scenarioLogL6OverL3GridRanges": scenario_ranges,
            "signedGridMissLog": miss,
            "absoluteGridMissLog": abs(miss),
            "absoluteGridMissMagEquivalent": abs(miss) * (2.5 / math.log(10.0)),
            "observedInsideGridUnion": miss == 0.0,
        })
        evaluated += 1
        if miss != 0.0:
            outside.append(rec)
        pairs.append(rec)

    output = {
        "schemaVersion": 1,
        "diagnosticId": "koomen-1952-same-aod-scenario-twilight-shape-grid-v1",
        "claimClass": "DENSE_GRID_DIAGNOSTIC_ONLY_NOT_CERTIFIED",
        "grid": {
            "aod550Min": AOD_MIN,
            "aod550Max": AOD_MAX,
            "count": GRID_COUNT,
            "spacing": "LINEAR_IN_AOD550_INCLUSIVE_ENDPOINTS",
            "sameAodUsedForD3AndD6": True,
            "sameScenarioUsedForD3AndD6": True,
        },
        "pairCount": len(pairs),
        "evaluatedPairCount": evaluated,
        "outsideGridUnionCount": len(outside),
        "insideGridUnionCount": evaluated - len(outside),
        "pairs": pairs,
        "interpretationBoundary": {
            "formalPassFailAuthorized": False,
            "certifiedShapeClaimAuthorized": False,
            "diagnosticCanIdentifyDirectionAndGeometryOfShapeMismatch": True,
            "modelRetuningAuthorized": False,
            "strictModernRealSkyValidationClaimAuthorized": False,
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "diagnosticId": output["diagnosticId"],
        "pairCount": output["pairCount"],
        "evaluatedPairCount": output["evaluatedPairCount"],
        "outsideGridUnionCount": output["outsideGridUnionCount"],
        "insideGridUnionCount": output["insideGridUnionCount"],
    }, indent=2, sort_keys=True))
    for rec in outside:
        print(json.dumps({
            "relativeAzimuthDeg": rec["relativeAzimuthDeg"],
            "targetAltitudeDeg": rec["targetAltitudeDeg"],
            "observedLogL6OverL3": rec["observedLogL6OverL3"],
            "modelLogL6OverL3GridUnion": rec["modelLogL6OverL3GridUnion"],
            "signedGridMissLog": rec["signedGridMissLog"],
            "absoluteGridMissMagEquivalent": rec["absoluteGridMissMagEquivalent"],
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
