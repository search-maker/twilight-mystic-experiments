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
    parser.add_argument("--absolute-result", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--asiv-runtime", type=Path, required=True)
    parser.add_argument("--extrema-evaluator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    absolute = json.loads(args.absolute_result.read_text(encoding="utf-8"))
    if dataset["selection"]["rowCount"] != 48 or len(dataset["rows"]) != 48:
        raise ValueError("frozen Koomen benchmark cardinality drift")
    if absolute.get("benchmarkId") != "koomen-1952-maryland-photopic-48-v1":
        raise ValueError("absolute benchmark result identity drift")

    extrema = load_module(args.extrema_evaluator, "frozen_extrema_for_shape_grid")
    base = extrema.load_base_runtime(args.base_runtime)
    asiv = extrema.load_asiv_runtime(args.asiv_runtime)

    result_rows = {row["cellId"]: row for row in absolute["rows"]}
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
        abs3 = result_rows[row3["cellId"]]
        abs6 = result_rows[row6["cellId"]]
        l3 = float(row3["observedPhotopicLuminanceCdM2"])
        l6 = float(row6["observedPhotopicLuminanceCdM2"])
        observed = math.log(l6 / l3)
        rec = {
            "relativeAzimuthDeg": az,
            "targetAltitudeDeg": alt,
            "observerElevationM": float(row3["observerElevationM"]),
            "observedLogL6OverL3": observed,
            "observedFactorL3OverL6": l3 / l6,
            "d3CellId": row3["cellId"],
            "d6CellId": row6["cellId"],
        }
        support3 = bool(abs3.get("support", {}).get("supportedAcrossEntireInterval"))
        support6 = bool(abs6.get("support", {}).get("supportedAcrossEntireInterval"))
        if not (support3 and support6):
            rec["status"] = "PAIR_UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL"
            pairs.append(rec)
            continue

        scenario_ranges = {}
        all_values = []
        for scenario in SCENARIOS:
            values = []
            for aod in aod_grid:
                p3 = extrema._point_prediction(
                    base, asiv,
                    3.0, alt, az, float(row3["observerElevationM"]), aod,
                )
                p6 = extrema._point_prediction(
                    base, asiv,
                    6.0, alt, az, float(row6["observerElevationM"]), aod,
                )
                value = float(p6[scenario][0]) - float(p3[scenario][0])
                values.append(value)
                all_values.append(value)
            scenario_ranges[scenario] = [min(values), max(values)]

        lo = min(all_values)
        hi = max(all_values)
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
