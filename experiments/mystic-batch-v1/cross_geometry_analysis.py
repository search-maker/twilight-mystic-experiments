#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
METHODS = ("reference-vroom", "alis")
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


class AnalysisFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AnalysisFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def mean_cv(values: list[float]) -> tuple[float, float]:
    if len(values) < 2 or any(not math.isfinite(value) or value <= 0 for value in values):
        raise AnalysisFailure("two positive finite values required")
    mean = statistics.fmean(values)
    return mean, statistics.stdev(values) / mean


def node_means(records: list[dict[str, Any]], field: str) -> list[float]:
    vectors = [record.get(field) for record in records]
    if any(not isinstance(vector, list) or len(vector) != len(CIE) for vector in vectors):
        raise AnalysisFailure(f"invalid {field} vector")
    return [statistics.fmean(float(vector[index]) for vector in vectors) for index in range(len(CIE))]


def analyze_geometry(group_id: str, records: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    methods = {method: [record for record in records if record.get("method") == method] for method in METHODS}
    required_blocks = contract["requiredBlocksPerMethodPerGeometry"]
    if any(len(methods[method]) != required_blocks for method in METHODS):
        return {"groupId": group_id, "classification": "STRUCTURAL_OR_EXECUTION_FAILURE", "reason": "wrong method/block count"}
    if any(record.get("status") != "COMPLETED" for record in records):
        return {"groupId": group_id, "classification": "STRUCTURAL_OR_EXECUTION_FAILURE", "reason": "incomplete case"}

    stats: dict[str, Any] = {}
    for method in METHODS:
        values = [float(record["selectedPhotopicContributionCdM2"]) for record in methods[method]]
        mean, cv = mean_cv(values)
        radiance = node_means(methods[method], "selectedNodeRadiance")
        std = node_means(methods[method], "selectedNodeStdRadiance")
        weights = [value * cie for value, cie in zip(radiance, CIE)]
        total_weight = sum(weights)
        if total_weight <= 0:
            raise AnalysisFailure("nonpositive photopic weight")
        reported = sum(weight * (sigma / value if value > 0 else math.inf) for value, sigma, weight in zip(radiance, std, weights)) / total_weight
        stats[method] = {
            "valuesCdM2": values,
            "meanCdM2": mean,
            "coefficientOfVariation": cv,
            "photopicWeightedReportedRelativeStd": reported,
            "nodeMeanRadiance": radiance
        }

    ratio = stats["alis"]["meanCdM2"] / stats["reference-vroom"]["meanCdM2"]
    interval = contract["screeningRules"]["integratedMeanRatioAlisToVroomClosedInterval"]
    alis_nodes = stats["alis"]["nodeMeanRadiance"]
    vroom_nodes = stats["reference-vroom"]["nodeMeanRadiance"]
    ratios = [alis / vroom if vroom > 0 else math.inf for alis, vroom in zip(alis_nodes, vroom_nodes)]
    weights = [value * cie for value, cie in zip(vroom_nodes, CIE)]
    fraction = sum(weight for ratio_value, weight in zip(ratios, weights) if interval[0] <= ratio_value <= interval[1]) / sum(weights)
    rules = contract["screeningRules"]
    noisy = any(
        stats[method]["coefficientOfVariation"] > rules["maximumWithinMethodCoefficientOfVariation"]
        or stats[method]["photopicWeightedReportedRelativeStd"] > rules["maximumPhotopicWeightedReportedRelativeStd"]
        for method in METHODS
    )
    agreement = interval[0] <= ratio <= interval[1] and fraction >= rules["minimumVroomPhotopicWeightFractionNodeRatioInsideInterval"]
    if noisy:
        classification = "NEEDS_MORE_BLOCKS"
    elif agreement:
        classification = "SCREENING_AGREEMENT"
    else:
        classification = "SCREENING_DISCREPANCY"
    return {
        "groupId": group_id,
        "classification": classification,
        "methodStatistics": stats,
        "meanRatioAlisToVroom": ratio,
        "vroomPhotopicWeightFractionNodeRatioInsideInterval": fraction,
        "nodeMeanRatiosAlisToVroom": ratios,
        "recommendedAdditionalFreshBlocksPerMethod": contract["stageTwoRule"]["additionalFreshBlocksPerMethod"] if classification != "SCREENING_AGREEMENT" else 0
    }


def analyze(manifest_path: Path, contract_path: Path, records_path: Path) -> dict[str, Any]:
    manifest = load(manifest_path)
    contract = load(contract_path)
    payload = load(records_path)
    if manifest.get("stageId") != STAGE_ID or contract.get("stageId") != STAGE_ID:
        raise AnalysisFailure("stage mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        raise AnalysisFailure("records missing")
    cases = {case["caseId"]: case for case in manifest["cases"]}
    enriched: list[dict[str, Any]] = []
    for record in records:
        case = cases.get(record.get("caseId"))
        if case is None:
            raise AnalysisFailure(f"unplanned case: {record.get('caseId')}")
        enriched.append({**record, "groupId": case["groupId"], "method": case["method"], "block": case["block"]})
    expected_ids = set(cases)
    actual_ids = {record["caseId"] for record in enriched}
    if actual_ids != expected_ids or len(enriched) != len(expected_ids):
        raise AnalysisFailure("case set is incomplete or duplicated")
    groups = sorted({case["groupId"] for case in cases.values()})
    results = [analyze_geometry(group, [record for record in enriched if record["groupId"] == group], contract) for group in groups]
    counts = {classification: sum(result["classification"] == classification for result in results) for classification in contract["classifications"]}
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "SCREENING_ANALYZED",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "geometryResults": results,
        "classificationCounts": counts,
        "boundary": contract["boundary"]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze(args.manifest, args.contract, args.records)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
