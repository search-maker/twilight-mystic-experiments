#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-observation-v1"
API_VERSION = "visibility-signal-margin-v1"


class VisibilityRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise VisibilityRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def positive(value: Any, name: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise VisibilityRefusal(f"{name} must be finite and positive")
    return float(value)


def probability_from_signals(request: dict[str, Any]) -> dict[str, Any]:
    if (
        request.get("schemaVersion") != 1
        or request.get("stageId") != STAGE_ID
        or request.get("apiVersion") != API_VERSION
    ):
        raise VisibilityRefusal("wrong API header")
    star_signal = positive(request.get("starSignal"), "starSignal")
    background_signal = positive(
        request.get("backgroundSignalInDetectionAperture"),
        "backgroundSignalInDetectionAperture",
    )
    threshold_contrast = positive(request.get("thresholdContrast"), "thresholdContrast")
    observer_sigma = positive(
        request.get("observerLogMarginSigma"), "observerLogMarginSigma"
    )
    model_domain = request.get("modelDomain")
    if model_domain not in {"synthetic", "calibrated", "validated"}:
        raise VisibilityRefusal("invalid modelDomain")
    contrast = star_signal / background_signal
    log_margin = math.log(contrast / threshold_contrast)
    probability = 1.0 / (1.0 + math.exp(-log_margin / observer_sigma))
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "apiVersion": API_VERSION,
        "status": "EVALUATED",
        "modelDomain": model_domain,
        "contrast": contrast,
        "thresholdContrast": threshold_contrast,
        "logContrastMargin": log_margin,
        "visibilityProbability": probability,
        "limitingFactor": (
            "background" if contrast < threshold_contrast else "observer-threshold-or-other"
        ),
        "boundary": "transparent signal-margin model only; upstream star/background signal calibration and threshold validation remain separate obligations",
    }


def first_crossing(
    samples: list[dict[str, Any]], probability_threshold: float
) -> dict[str, Any]:
    if not 0 < probability_threshold < 1:
        raise VisibilityRefusal("probability threshold must be between zero and one")
    if len(samples) < 2:
        raise VisibilityRefusal("at least two ordered samples are required")
    evaluated = []
    prior_time = None
    for sample in samples:
        minute = sample.get("minutesAfterSunset")
        if (
            not isinstance(minute, (int, float))
            or isinstance(minute, bool)
            or not math.isfinite(float(minute))
        ):
            raise VisibilityRefusal("minutesAfterSunset must be finite")
        minute = float(minute)
        if prior_time is not None and minute <= prior_time:
            raise VisibilityRefusal("samples must be strictly increasing in time")
        prior_time = minute
        result = probability_from_signals(sample["request"])
        evaluated.append((minute, result["visibilityProbability"]))
    for (left_time, left_probability), (right_time, right_probability) in zip(
        evaluated, evaluated[1:]
    ):
        if left_probability < probability_threshold <= right_probability:
            fraction = (probability_threshold - left_probability) / (
                right_probability - left_probability
            )
            return {
                "status": "CROSSING_FOUND",
                "probabilityThreshold": probability_threshold,
                "estimatedMinutesAfterSunset": left_time
                + fraction * (right_time - left_time),
                "bracket": [left_time, right_time],
                "boundary": "linear interpolation in probability; uncertainty must be propagated by the caller",
            }
    return {
        "status": "NO_CROSSING_IN_WINDOW",
        "probabilityThreshold": probability_threshold,
        "evaluatedRangeMinutesAfterSunset": [evaluated[0][0], evaluated[-1][0]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = probability_from_signals(load_json(args.input))
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
