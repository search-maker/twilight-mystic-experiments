#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-v1"


class SelectorRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SelectorRefusal(f"expected JSON object: {path}")
    return value


def number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise SelectorRefusal(f"{name} must be finite")
    return float(value)


def select(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schemaVersion") != 1 or payload.get("stageId") != STAGE_ID:
        raise SelectorRefusal("wrong schemaVersion or stageId")
    points = payload.get("points")
    policy = payload.get("policy")
    if not isinstance(points, list) or len(points) < 3 or not isinstance(policy, dict):
        raise SelectorRefusal("at least three points and a policy are required")
    maximum_new = int(policy.get("maximumNewPoints", 3))
    maximum_interval = number(
        policy.get("maximumSunDepressionIntervalDeg", 2.0), "maximum interval"
    )
    target_log_error = number(
        policy.get("targetInterpolationLogError", 0.05), "target log error"
    )
    normalized = []
    seen: set[float] = set()
    for point in points:
        x = number(point.get("sunDepressionDeg"), "sunDepressionDeg")
        luminance = number(point.get("photopicLuminanceCdM2"), "photopicLuminanceCdM2")
        uncertainty = number(point.get("logStandardError"), "logStandardError")
        if luminance <= 0 or uncertainty < 0 or x in seen:
            raise SelectorRefusal(
                "points require unique depth, positive luminance, non-negative uncertainty"
            )
        seen.add(x)
        normalized.append({"x": x, "y": math.log(luminance), "u": uncertainty})
    normalized.sort(key=lambda item: item["x"])
    slopes = [
        (right["y"] - left["y"]) / (right["x"] - left["x"])
        for left, right in zip(normalized, normalized[1:])
    ]
    candidates: list[dict[str, Any]] = []
    for index, (left, right) in enumerate(zip(normalized, normalized[1:])):
        width = right["x"] - left["x"]
        curvature = 0.0
        if index > 0:
            curvature = max(
                curvature, abs(slopes[index] - slopes[index - 1]) * width / 8.0
            )
        if index + 1 < len(slopes):
            curvature = max(
                curvature, abs(slopes[index + 1] - slopes[index]) * width / 8.0
            )
        uncertainty = max(left["u"], right["u"])
        estimated_error = uncertainty + curvature
        requires = width > maximum_interval or estimated_error > target_log_error
        priority = max(width / maximum_interval, estimated_error / target_log_error)
        if requires:
            candidates.append(
                {
                    "sunDepressionDeg": (left["x"] + right["x"]) / 2.0,
                    "leftDepthDeg": left["x"],
                    "rightDepthDeg": right["x"],
                    "intervalWidthDeg": width,
                    "estimatedInterpolationLogError": estimated_error,
                    "priority": priority,
                    "reason": "interval width and/or curvature-plus-uncertainty exceeds frozen target",
                }
            )
    selected = sorted(
        candidates, key=lambda item: (-item["priority"], item["sunDepressionDeg"])
    )[:maximum_new]
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "SELECTION_COMPLETE",
        "scientificExecution": False,
        "selectedPoints": selected,
        "candidateCount": len(candidates),
        "boundary": "adaptive proposal only; selected points require a later exact manifest and authorization",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = select(load_json(args.input))
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
