#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]
METHODS = ("reference-vroom", "alis")

class ConvergenceError(RuntimeError):
    pass

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ConvergenceError(f"expected JSON object: {path}")
    return value

def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"

def method_summary(values: list[float], node_mean: list[float], node_std: list[float] | None = None) -> dict[str, Any]:
    if len(values) < 2 or any(not math.isfinite(v) or v <= 0 for v in values):
        raise ConvergenceError("at least two positive finite independent block values are required")
    if len(node_mean) != len(CIE) or any(not math.isfinite(v) or v < 0 for v in node_mean):
        raise ConvergenceError("invalid node mean vector")
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    cv = sd / mean
    rsem = cv / math.sqrt(len(values))
    reported_available = bool(node_std) and len(node_std) == len(CIE) and any(float(v) > 0 for v in node_std)
    reported = None
    if reported_available:
        weights = [r * w for r, w in zip(node_mean, CIE)]
        total = sum(weights)
        if total > 0:
            reported = sum(weight * (float(s) / r if r > 0 else math.inf) for r, s, weight in zip(node_mean, node_std, weights)) / total
    return {
        "blockCount": len(values),
        "valuesCdM2": values,
        "meanCdM2": mean,
        "sampleStandardDeviationCdM2": sd,
        "coefficientOfVariation": cv,
        "relativeStandardErrorOfMean": rsem,
        "reportedNodeStdAvailable": reported_available,
        "photopicWeightedReportedRelativeStd": reported,
        "nodeMeanRadiance": node_mean,
    }

def node_fraction(alis: list[float], vroom: list[float], interval: list[float]) -> tuple[float, list[float]]:
    ratios = [a / v if v > 0 else math.inf for a, v in zip(alis, vroom)]
    weights = [v * c for v, c in zip(vroom, CIE)]
    total = sum(weights)
    if total <= 0:
        raise ConvergenceError("nonpositive VROOM photopic weight")
    inside = sum(w for r, w in zip(ratios, weights) if interval[0] <= r <= interval[1]) / total
    return inside, ratios

def classify(methods: dict[str, dict[str, Any]], rules: dict[str, Any]) -> dict[str, Any]:
    vroom = methods["reference-vroom"]
    alis = methods["alis"]
    ratio = alis["meanCdM2"] / vroom["meanCdM2"]
    interval = rules["integratedMeanRatioAlisToVroomClosedInterval"]
    fraction, ratios = node_fraction(alis["nodeMeanRadiance"], vroom["nodeMeanRadiance"], interval)
    threshold = rules.get("maximumRelativeStandardErrorOfMean", 0.10)
    noisy = any(methods[m]["relativeStandardErrorOfMean"] > threshold for m in METHODS)
    agreement = interval[0] <= ratio <= interval[1] and fraction >= rules["minimumVroomPhotopicWeightFractionNodeRatioInsideInterval"]
    classification = "NEEDS_MORE_PRECISION" if noisy else ("SCREENING_AGREEMENT" if agreement else "SCREENING_DISCREPANCY")
    return {
        "classification": classification,
        "meanRatioAlisToVroom": ratio,
        "vroomPhotopicWeightFractionNodeRatioInsideInterval": fraction,
        "nodeMeanRatiosAlisToVroom": ratios,
        "maximumRelativeStandardErrorOfMean": threshold,
    }

def reanalyze_stage_two(screening: dict[str, Any]) -> dict[str, Any]:
    rules = {
        "integratedMeanRatioAlisToVroomClosedInterval": [0.5, 2.0],
        "minimumVroomPhotopicWeightFractionNodeRatioInsideInterval": 0.80,
        "maximumRelativeStandardErrorOfMean": 0.10,
    }
    results = []
    for item in screening.get("geometryResults", []):
        if item.get("carriedForwardFromPilot"):
            results.append({**item, "convergenceMetricVersion": 2, "classificationV2": item.get("classification")})
            continue
        methods = {}
        for method in METHODS:
            old = item["methodStatistics"][method]
            node_std = None
            if old.get("photopicWeightedReportedRelativeStd") not in (None, 0):
                node_std = []
            methods[method] = method_summary(old["valuesCdM2"], old["nodeMeanRadiance"], node_std)
        decision = classify(methods, rules)
        results.append({
            "groupId": item["groupId"],
            "carriedForwardFromPilot": False,
            "blocksPerMethodAnalyzed": item["blocksPerMethodAnalyzed"],
            "methodStatisticsV2": methods,
            **decision,
            "classificationV1": item["classification"],
            "classificationV2": decision["classification"],
        })
    counts: dict[str, int] = {}
    for item in results:
        key = item.get("classificationV2")
        counts[key] = counts.get(key, 0) + 1
    return {
        "schemaVersion": 1,
        "stageId": "cross-geometry-convergence-v2",
        "status": "REANALYZED_WITH_MEAN_UNCERTAINTY",
        "sourceStageId": screening.get("stageId"),
        "sourceCombinedCaseResultCount": screening.get("combinedCaseResultCount"),
        "sourceCombinedConfiguredMcPhotonsSum": screening.get("combinedConfiguredMcPhotonsSum"),
        "metricChange": {
            "oldGate": "coefficient of variation of independent blocks and node-reported standard deviation",
            "newGate": "relative standard error of the independent-block mean; raw CV retained only as a noise diagnostic",
            "alisNodeStdTreatment": "all-zero ALIS mc.rad.std.spc is unavailable, not zero uncertainty",
        },
        "rules": rules,
        "geometryResults": results,
        "classificationCountsV2": counts,
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screening", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reanalyze_stage_two(load(args.screening))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump(result))
    print(dump(result), end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
