#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any

STAGE_ID = "twilight-observation-v1"


class CalibrationRefusal(RuntimeError):
    pass


def finite(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise CalibrationRefusal(f"{name} must be finite")
    return float(value)


def calibrated_camera_radiance(
    calibration: dict[str, Any], sample: dict[str, Any]
) -> dict[str, Any]:
    if calibration.get("modelType") != "dark-subtracted-linear-radiance-v1":
        raise CalibrationRefusal("unsupported camera calibration model")
    exposure = finite(sample.get("exposureSeconds"), "exposureSeconds")
    counts = finite(sample.get("meanCounts"), "meanCounts")
    dark_rate = finite(calibration.get("darkCountsPerSecond"), "darkCountsPerSecond")
    gain = finite(
        calibration.get("radiancePerCountPerSecond"), "radiancePerCountPerSecond"
    )
    if exposure <= 0 or gain <= 0:
        raise CalibrationRefusal("exposure and gain must be positive")
    corrected_rate = counts / exposure - dark_rate
    if corrected_rate <= 0:
        raise CalibrationRefusal("dark-subtracted signal is not positive")
    radiance = corrected_rate * gain
    relative_se = finite(sample.get("relativeStandardError"), "relativeStandardError")
    if relative_se < 0:
        raise CalibrationRefusal("relativeStandardError cannot be negative")
    return {
        "modelType": calibration["modelType"],
        "spectralBandId": calibration.get("spectralBandId"),
        "radiance": radiance,
        "radianceStandardError": radiance * relative_se,
        "calibrationId": calibration.get("calibrationId"),
    }


def calibrated_sqm_luminance(
    calibration: dict[str, Any], sample: dict[str, Any]
) -> dict[str, Any]:
    if calibration.get("modelType") != "sqm-log-luminance-v1":
        raise CalibrationRefusal("unsupported SQM calibration model")
    sqm = finite(sample.get("sqmMagPerArcsec2"), "sqmMagPerArcsec2")
    zero_point = finite(calibration.get("zeroPointCdM2"), "zeroPointCdM2")
    offset = finite(calibration.get("magnitudeOffset"), "magnitudeOffset")
    if zero_point <= 0:
        raise CalibrationRefusal("zeroPointCdM2 must be positive")
    luminance = zero_point * 10 ** (-0.4 * (sqm + offset))
    magnitude_se = finite(
        sample.get("magnitudeStandardError"), "magnitudeStandardError"
    )
    if magnitude_se < 0:
        raise CalibrationRefusal("magnitudeStandardError cannot be negative")
    log_se = math.log(10) * 0.4 * magnitude_se
    return {
        "modelType": calibration["modelType"],
        "photopicLuminanceCdM2": luminance,
        "logStandardError": log_se,
        "calibrationId": calibration.get("calibrationId"),
        "boundary": "zero point and spectral response must come from an independently reviewed calibration",
    }
