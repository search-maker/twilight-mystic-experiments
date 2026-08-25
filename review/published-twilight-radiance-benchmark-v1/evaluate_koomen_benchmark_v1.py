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


def signed_interval_miss(value: float, lo: float, hi: float) -> float:
    if lo <= value <= hi:
        return 0.0
    if value < lo:
        return value - lo
    return value - hi


def evaluate_row(task):
    index, row, paths = task
    support_mod = load_module(Path(paths["supportEvaluator"]), f"frozen_exact_aod_support_{index}")
    extrema_mod = load_module(Path(paths["extremaEvaluator"]), f"frozen_certified_aod_extrema_{index}")
    base_for_support = support_mod.load_bound_runtime(Path(paths["baseRuntime"]))
    base = extrema_mod.load_base_runtime(Path(paths["baseRuntime"]))
    asiv = extrema_mod.load_asiv_runtime(Path(paths["asivRuntime"]))

    kwargs = dict(
        sun_depression_deg=float(row["sunDepressionDeg"]),
        target_altitude_deg=float(row["targetAltitudeDeg"]),
        relative_azimuth_deg=float(row["relativeAzimuthDeg"]),
        observer_elevation_m=float(row["observerElevationM"]),
        aod550_min=0.05,
        aod550_max=0.40,
    )
    support = support_mod.exact_max_nearest_support_distance(
        support_coordinates=base_for_support["supportCoordinates"],
        **kwargs,
    )
    record = {
        "cellId": row["cellId"],
        "geometry": {
            "sunDepressionDeg": row["sunDepressionDeg"],
            "targetAltitudeDeg": row["targetAltitudeDeg"],
            "relativeAzimuthDeg": row["relativeAzimuthDeg"],
            "observerElevationM": row["observerElevationM"],
        },
        "observedPhotopicLuminanceCdM2": row["observedPhotopicLuminanceCdM2"],
        "observedLogPhotopic": math.log(float(row["observedPhotopicLuminanceCdM2"])),
        "support": support,
    }
    if not support["supportedAcrossEntireInterval"]:
        record["status"] = "UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL"
        return index, record

    extrema = extrema_mod.certified_extrema(
        base,
        asiv,
        sun=float(row["sunDepressionDeg"]),
        alt=float(row["targetAltitudeDeg"]),
        raz=float(row["relativeAzimuthDeg"]),
        elev=float(row["observerElevationM"]),
        aod_lo=0.05,
        aod_hi=0.40,
        log_tolerance=1e-4,
        max_depth=50,
        max_nodes=250000,
    )
    if not extrema["certified"]:
        record["status"] = "EXTREMA_NOT_CERTIFIED"
        record["extrema"] = extrema
        return index, record

    scenario_results = extrema["scenarios"]
    union_lo = min(scenario_results[scenario]["photopic"]["outerMin"] for scenario in SCENARIOS)
    union_hi = max(scenario_results[scenario]["photopic"]["outerMax"] for scenario in SCENARIOS)
    observed_log = record["observedLogPhotopic"]
    miss = signed_interval_miss(observed_log, union_lo, union_hi)
    record.update({
        "status": "CERTIFIED_FULL_AOD_SCENARIO_ENVELOPE_EVALUATED",
        "modelPhotopicUnionLogOuter": [union_lo, union_hi],
        "modelPhotopicUnionCdM2Outer": [math.exp(union_lo), math.exp(union_hi)],
        "signedSetMissLog": miss,
        "absoluteSetMissLog": abs(miss),
        "absoluteSetMissMagEquivalent": abs(miss) * (2.5 / math.log(10.0)),
        "scenarioPhotopicOuter": {
            scenario: [
                scenario_results[scenario]["photopic"]["outerMin"],
                scenario_results[scenario]["photopic"]["outerMax"],
            ]
            for scenario in SCENARIOS
        },
        "certification": {
            "algorithmId": extrema["algorithmId"],
            "logTolerance": extrema["logTolerance"],
            "partitionBreakpoints": extrema["partitionBreakpoints"],
            "branchNodes": extrema["branchNodes"],
            "maximumDepth": extrema["maximumDepth"],
        },
    })
    return index, record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--asiv-runtime", type=Path, required=True)
    parser.add_argument("--support-evaluator", type=Path, required=True)
    parser.add_argument("--extrema-evaluator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    if dataset["selection"]["rowCount"] != 48 or len(dataset["rows"]) != 48:
        raise ValueError("frozen Koomen benchmark cardinality drift")
    if args.workers < 1 or args.workers > 8:
        raise ValueError("workers must be between 1 and 8; parallelism changes execution speed only")

    paths = {
        "baseRuntime": str(args.base_runtime),
        "asivRuntime": str(args.asiv_runtime),
        "supportEvaluator": str(args.support_evaluator),
        "extremaEvaluator": str(args.extrema_evaluator),
    }
    tasks = [(i, row, paths) for i, row in enumerate(dataset["rows"])]
    results_by_index = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(evaluate_row, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            index, record = future.result()
            results_by_index[index] = record
            print(f"completed {index + 1:02d}/48 {record['cellId']} {record['status']}", flush=True)

    rows_out = [results_by_index[i] for i in range(48)]
    supported_count = sum(row["status"] != "UNSUPPORTED_ACROSS_FULL_AOD_INTERVAL" for row in rows_out)
    certified_rows = [row for row in rows_out if row["status"] == "CERTIFIED_FULL_AOD_SCENARIO_ENVELOPE_EVALUATED"]
    uncertified_count = sum(row["status"] == "EXTREMA_NOT_CERTIFIED" for row in rows_out)
    outside_count = sum(row["signedSetMissLog"] != 0 for row in certified_rows)
    abs_misses = [row["absoluteSetMissLog"] for row in certified_rows]

    by_key = {}
    for row in dataset["rows"]:
        key = (float(row["relativeAzimuthDeg"]), float(row["targetAltitudeDeg"]))
        by_key.setdefault(key, {})[int(row["sunDepressionDeg"])] = row
    shape = []
    for (az, alt), pair in sorted(by_key.items()):
        if 3 not in pair or 6 not in pair:
            continue
        l3 = float(pair[3]["observedPhotopicLuminanceCdM2"])
        l6 = float(pair[6]["observedPhotopicLuminanceCdM2"])
        shape.append({
            "relativeAzimuthDeg": az,
            "targetAltitudeDeg": alt,
            "observedLogL6OverL3": math.log(l6 / l3),
            "observedFactorL3OverL6": l3 / l6,
            "modelPairedShapeCertificationStatus": "NOT_YET_CERTIFIED_IN_V1",
        })

    result = {
        "schemaVersion": 1,
        "benchmarkId": "koomen-1952-maryland-photopic-48-v1",
        "claimClass": "PUBLISHED_OPEN_DIAGNOSTIC_BENCHMARK_NOT_STRICT_HOLDOUT_VALIDATION",
        "aod550Interval": [0.05, 0.40],
        "scenarioSet": list(SCENARIOS),
        "rowCount": len(dataset["rows"]),
        "supportedAcrossEntireAodIntervalCount": supported_count,
        "certifiedEnvelopeEvaluatedCount": len(certified_rows),
        "extremaUncertifiedCount": uncertified_count,
        "certifiedEnvelopeOutsideCount": outside_count,
        "certifiedEnvelopeInsideOrBoundaryCount": len(certified_rows) - outside_count,
        "maximumAbsoluteSetMissLog": max(abs_misses) if abs_misses else None,
        "maximumAbsoluteSetMissMagEquivalent": (max(abs_misses) * (2.5 / math.log(10.0))) if abs_misses else None,
        "executionParallelism": {
            "workers": args.workers,
            "note": "Parallelism changes execution scheduling only; every cell uses the same frozen support/extrema algorithm and tolerance."
        },
        "rows": rows_out,
        "observedTwilightShapePairs": shape,
        "interpretationBoundary": {
            "outsideFullAodScenarioEnvelopeIsStrongHistoricalInconsistency": True,
            "insideFullAodScenarioEnvelopeIsOnlyBroadConsistency": True,
            "formalShapePassFailAuthorized": False,
            "modelRetuningAuthorized": False,
            "strictModernRealSkyValidationClaimAuthorized": False,
        },
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "benchmarkId",
        "rowCount",
        "supportedAcrossEntireAodIntervalCount",
        "certifiedEnvelopeEvaluatedCount",
        "extremaUncertifiedCount",
        "certifiedEnvelopeOutsideCount",
        "certifiedEnvelopeInsideOrBoundaryCount",
        "maximumAbsoluteSetMissLog",
        "maximumAbsoluteSetMissMagEquivalent",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
