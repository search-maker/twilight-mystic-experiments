#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-v1"


class AllocationRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AllocationRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def positive_number(value: Any, name: str, allow_zero: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise AllocationRefusal(f"{name} must be finite")
    number = float(value)
    if number < 0 or (not allow_zero and number == 0):
        raise AllocationRefusal(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return number


def positive_int(value: Any, name: str, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise AllocationRefusal(f"{name} must be an integer >= {minimum}")
    return value


def allocate(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schemaVersion") != 1 or payload.get("stageId") != STAGE_ID:
        raise AllocationRefusal("wrong schemaVersion or stageId")
    policy = payload.get("policy")
    cases = payload.get("cases")
    if not isinstance(policy, dict) or not isinstance(cases, list) or not cases:
        raise AllocationRefusal("policy must be an object and cases a non-empty array")

    pilot_blocks = positive_int(policy.get("pilotBlocks"), "policy.pilotBlocks", 2)
    maximum_blocks = positive_int(
        policy.get("maximumTotalBlocks"), "policy.maximumTotalBlocks", pilot_blocks
    )
    target_relative_se = positive_number(
        policy.get("targetRelativeStandardError"), "policy.targetRelativeStandardError"
    )
    target_time_minutes = positive_number(
        policy.get("targetTimeUncertaintyMinutes"), "policy.targetTimeUncertaintyMinutes"
    )
    if maximum_blocks < pilot_blocks:
        raise AllocationRefusal("maximumTotalBlocks cannot be smaller than pilotBlocks")

    seen_ids: set[str] = set()
    recommendations: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise AllocationRefusal("each case must be an object")
        case_id = case.get("caseId")
        if not isinstance(case_id, str) or not case_id or case_id in seen_ids:
            raise AllocationRefusal("caseId must be a unique non-empty string")
        seen_ids.add(case_id)
        values = case.get("independentBlockLuminance")
        seeds = case.get("blockSeeds")
        if not isinstance(values, list) or not isinstance(seeds, list) or len(values) != len(seeds):
            raise AllocationRefusal(f"{case_id}: block values and seeds must be equal-length arrays")
        if len(values) != pilot_blocks:
            raise AllocationRefusal(f"{case_id}: exactly pilotBlocks independent values are required")
        if len(set(seeds)) != len(seeds) or any(
            not isinstance(seed, int) or isinstance(seed, bool) or seed <= 0 for seed in seeds
        ):
            raise AllocationRefusal(f"{case_id}: block seeds must be unique positive integers")
        numeric = [
            positive_number(value, f"{case_id}.independentBlockLuminance") for value in values
        ]
        log_values = [math.log(value) for value in numeric]
        log_std = statistics.stdev(log_values)
        mean_luminance = statistics.fmean(numeric)
        slope = abs(
            positive_number(
                case.get("absoluteLogLuminanceSlopePerMinute"),
                f"{case_id}.absoluteLogLuminanceSlopePerMinute",
            )
        )
        direct_log_se_limit = math.log1p(target_relative_se)
        downstream_log_se_limit = slope * target_time_minutes
        effective_log_se_limit = min(direct_log_se_limit, downstream_log_se_limit)
        if effective_log_se_limit <= 0:
            required = maximum_blocks
        else:
            required = math.ceil((log_std / effective_log_se_limit) ** 2)
            required = max(pilot_blocks, min(maximum_blocks, required))
        current_log_se = log_std / math.sqrt(pilot_blocks)
        estimated_time_uncertainty = current_log_se / slope
        capped = required == maximum_blocks and current_log_se > effective_log_se_limit
        recommendations.append(
            {
                "caseId": case_id,
                "pilotBlocks": pilot_blocks,
                "recommendedTotalBlocks": required,
                "additionalIndependentBlocks": required - pilot_blocks,
                "maximumTotalBlocks": maximum_blocks,
                "meanPilotLuminance": mean_luminance,
                "sampleLogStandardDeviation": log_std,
                "currentLogStandardError": current_log_se,
                "currentApproximateRelativeStandardError": math.expm1(current_log_se),
                "currentEstimatedTimeUncertaintyMinutes": estimated_time_uncertainty,
                "effectiveTargetLogStandardError": effective_log_se_limit,
                "allocationCapped": capped,
                "rule": "one preregistered second-stage allocation; every added block requires a fresh seed",
            }
        )
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "ALLOCATED",
        "scientificExecution": False,
        "twoStageOnly": True,
        "policy": policy,
        "recommendations": recommendations,
        "boundary": "allocation proposal only; no MYSTIC execution and no sequential stopping beyond the single second stage",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = allocate(load_json(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}),
            end="",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
