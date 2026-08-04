#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-two-v1"
OUTPUT_STAGE_ID = "cross-geometry-convergence-v2"
AGREEMENT_INTERVAL = (0.75, 1.25)
MAX_RELATIVE_STANDARD_ERROR = 0.10
MIN_NODE_WEIGHT_FRACTION = 0.80


class ConvergenceFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ConvergenceFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def replicate_stats(values: Any) -> dict[str, float | int]:
    if not isinstance(values, list) or len(values) < 2:
        raise ConvergenceFailure("at least two replicate values are required")
    numeric = [float(value) for value in values]
    if any(not math.isfinite(value) or value <= 0 for value in numeric):
        raise ConvergenceFailure("replicate values must be positive and finite")
    mean = statistics.fmean(numeric)
    sd = statistics.stdev(numeric)
    cv = sd / mean
    rsem = cv / math.sqrt(len(numeric))
    return {
        "replicateCount": len(numeric),
        "meanCdM2": mean,
        "sampleStandardDeviationCdM2": sd,
        "coefficientOfVariation": cv,
        "relativeStandardErrorOfMean": rsem,
    }


def classify(result: dict[str, Any]) -> dict[str, Any]:
    methods = result.get("methodStatistics")
    if not isinstance(methods, dict):
        raise ConvergenceFailure(f"method statistics missing for {result.get('groupId')}")
    alis = replicate_stats(methods.get("alis", {}).get("valuesCdM2"))
    vroom = replicate_stats(methods.get("reference-vroom", {}).get("valuesCdM2"))
    ratio = alis["meanCdM2"] / vroom["meanCdM2"]
    ratio_rsem = math.sqrt(
        float(alis["relativeStandardErrorOfMean"]) ** 2
        + float(vroom["relativeStandardErrorOfMean"]) ** 2
    )
    node_fraction = float(result.get("vroomPhotopicWeightFractionNodeRatioInsideInterval", 0.0))
    alis_reported = float(methods.get("alis", {}).get("photopicWeightedReportedRelativeStd", 0.0))
    vroom_reported = float(methods.get("reference-vroom", {}).get("photopicWeightedReportedRelativeStd", 0.0))
    group = result.get("groupId")

    converged = (
        float(alis["relativeStandardErrorOfMean"]) <= MAX_RELATIVE_STANDARD_ERROR
        and float(vroom["relativeStandardErrorOfMean"]) <= MAX_RELATIVE_STANDARD_ERROR
        and ratio_rsem <= MAX_RELATIVE_STANDARD_ERROR
        and AGREEMENT_INTERVAL[0] <= ratio <= AGREEMENT_INTERVAL[1]
        and node_fraction >= MIN_NODE_WEIGHT_FRACTION
    )
    if converged:
        classification = "CONVERGED_SCREENING_AGREEMENT"
        next_action = "NO_MORE_MONTE_CARLO_FOR_THIS_GEOMETRY"
    elif group == "g05-mid-opposite-low" and float(vroom["relativeStandardErrorOfMean"]) <= MAX_RELATIVE_STANDARD_ERROR:
        classification = "ADDITIONAL_ALIS_BLOCKS_REQUIRED"
        next_action = "RUN_TWO_FRESH_ALIS_BLOCKS_ONLY"
    elif group in {"g01-reference-bridge", "g06-late-opposite-high-aerosol"}:
        classification = "ALIS_IMPORTANCE_WAVELENGTH_DIAGNOSIS_REQUIRED"
        next_action = "RUN_VROOM_BLOCKS_5_6_AND_ALIS_500_550_600_DIAGNOSTICS"
    else:
        classification = "TECHNICAL_DIAGNOSIS_REQUIRED"
        next_action = "DO_NOT_ADD_BLIND_BLOCKS"

    return {
        "groupId": group,
        "classification": classification,
        "nextAction": next_action,
        "meanRatioAlisToVroom": ratio,
        "ratioRelativeStandardError": ratio_rsem,
        "vroomPhotopicWeightFractionNodeRatioInsideLegacyInterval": node_fraction,
        "methodStatistics": {"alis": alis, "reference-vroom": vroom},
        "reportedStdDiagnostics": {
            "alisPhotopicWeightedReportedRelativeStd": alis_reported,
            "alisReportedStdUsable": alis_reported > 0.0,
            "vroomPhotopicWeightedReportedRelativeStd": vroom_reported,
            "primaryConvergenceMetric": "independent-replicate relative standard error of the mean",
        },
    }


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("stageId") != STAGE_ID or payload.get("status") != "STAGE_TWO_SCREENING_ANALYZED":
        raise ConvergenceFailure("wrong Stage-2 screening header")
    if payload.get("combinedCaseResultCount") != 40 or payload.get("combinedConfiguredMcPhotonsSum") != 800_000_000:
        raise ConvergenceFailure("Stage-2 accounting changed")
    results = payload.get("geometryResults")
    if not isinstance(results, list) or len(results) != 6:
        raise ConvergenceFailure("expected six geometry results")
    corrected = [classify(result) for result in results]
    counts: dict[str, int] = {}
    for item in corrected:
        counts[item["classification"]] = counts.get(item["classification"], 0) + 1
    stage_three = [item["groupId"] for item in corrected if item["classification"] != "CONVERGED_SCREENING_AGREEMENT"]
    return {
        "schemaVersion": 1,
        "stageId": OUTPUT_STAGE_ID,
        "status": "CORRECTED_CONVERGENCE_ANALYZED",
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "sourceStageId": STAGE_ID,
        "sourceCaseResultCount": 40,
        "sourceConfiguredMcPhotonsSum": 800_000_000,
        "rules": {
            "agreementMeanRatioClosedInterval": list(AGREEMENT_INTERVAL),
            "maximumRelativeStandardErrorOfMean": MAX_RELATIVE_STANDARD_ERROR,
            "minimumVroomPhotopicWeightFractionInsideLegacyNodeInterval": MIN_NODE_WEIGHT_FRACTION,
            "alisZeroReportedStdIsNotTreatedAsZeroUncertainty": True,
            "coefficientOfVariationIsNotAStoppingMetric": True,
        },
        "geometryResults": corrected,
        "classificationCounts": counts,
        "stageThreeGeometryIds": stage_three,
        "boundary": "This corrects the Monte Carlo stopping diagnostic. It does not establish physical validity, observational validity, production permission, or a final ALIS reference wavelength.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze(load(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": OUTPUT_STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
