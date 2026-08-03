#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any

STAGE_ID = "observation-integration-v1"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")


class ContractError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_number(value: Any, name: str, low: float | None = None, high: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ContractError(f"{name} must be finite")
    result = float(value)
    if low is not None and result < low:
        raise ContractError(f"{name} must be >= {low}")
    if high is not None and result > high:
        raise ContractError(f"{name} must be <= {high}")
    return result


def require_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ContractError(f"{name} is invalid")
    return value


def require_timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{name} must be UTC RFC3339 ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{name} is not a valid timestamp") from exc
    return value


def validate_observation(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ContractError("observation must be an object")
    expected = {"schemaVersion": 1, "stageId": STAGE_ID}
    stale = {key: (record.get(key), value) for key, value in expected.items() if record.get(key) != value}
    if stale:
        raise ContractError(f"observation header mismatch: {stale}")
    observation_id = require_id(record.get("observationId"), "observationId")
    role = record.get("role")
    if role not in {"calibration", "validation"}:
        raise ContractError("role must be calibration or validation")
    used_for_tuning = record.get("usedForParameterTuning")
    if not isinstance(used_for_tuning, bool):
        raise ContractError("usedForParameterTuning must be boolean")
    if role == "validation" and used_for_tuning:
        raise ContractError("validation observations cannot be used for parameter tuning")
    timestamp = require_timestamp(record.get("timestampUtc"), "timestampUtc")

    location = record.get("location")
    if not isinstance(location, dict):
        raise ContractError("location must be an object")
    normalized_location = {
        "latitudeDeg": require_number(location.get("latitudeDeg"), "latitudeDeg", -90.0, 90.0),
        "longitudeDeg": require_number(location.get("longitudeDeg"), "longitudeDeg", -180.0, 180.0),
        "observerElevationM": require_number(location.get("observerElevationM"), "observerElevationM", -500.0, 10000.0),
        "siteId": require_id(location.get("siteId"), "siteId"),
    }

    geometry = record.get("geometry")
    if not isinstance(geometry, dict):
        raise ContractError("geometry must be an object")
    normalized_geometry = {
        "sunDepressionDeg": require_number(geometry.get("sunDepressionDeg"), "sunDepressionDeg", -5.0, 30.0),
        "targetAltitudeDeg": require_number(geometry.get("targetAltitudeDeg"), "targetAltitudeDeg", 0.0, 90.0),
        "targetAzimuthDeg": require_number(geometry.get("targetAzimuthDeg"), "targetAzimuthDeg", 0.0, 360.0),
        "relativeAzimuthDeg": require_number(geometry.get("relativeAzimuthDeg"), "relativeAzimuthDeg", 0.0, 180.0),
    }

    conditions = record.get("conditions")
    if not isinstance(conditions, dict):
        raise ContractError("conditions must be an object")
    aod = conditions.get("aod550Estimate")
    normalized_conditions = {
        "cloudFraction": require_number(conditions.get("cloudFraction"), "cloudFraction", 0.0, 1.0),
        "aod550Estimate": None if aod is None else require_number(aod, "aod550Estimate", 0.0, 5.0),
        "aodSource": conditions.get("aodSource"),
        "humidityPercent": require_number(conditions.get("humidityPercent"), "humidityPercent", 0.0, 100.0),
        "haloOrGlarePresent": conditions.get("haloOrGlarePresent"),
        "notes": conditions.get("notes", ""),
    }
    if normalized_conditions["aod550Estimate"] is not None and not isinstance(normalized_conditions["aodSource"], str):
        raise ContractError("aodSource is required when aod550Estimate is present")
    if not isinstance(normalized_conditions["haloOrGlarePresent"], bool):
        raise ContractError("haloOrGlarePresent must be boolean")
    if not isinstance(normalized_conditions["notes"], str):
        raise ContractError("conditions.notes must be a string")

    acquisition = record.get("acquisition")
    if not isinstance(acquisition, dict):
        raise ContractError("acquisition must be an object")
    method = acquisition.get("method")
    if method not in {"calibrated-spectrum", "calibrated-camera", "sqm", "naked-eye"}:
        raise ContractError("unsupported acquisition method")
    instrument_id = acquisition.get("instrumentId")
    calibration_id = acquisition.get("calibrationId")
    if method != "naked-eye":
        require_id(instrument_id, "instrumentId")
        require_id(calibration_id, "calibrationId")
    elif instrument_id is not None or calibration_id is not None:
        raise ContractError("naked-eye acquisition must not claim instrument calibration")
    screen_free = acquisition.get("screenFreeDuringObservation")
    if not isinstance(screen_free, bool):
        raise ContractError("screenFreeDuringObservation must be boolean")

    stars = record.get("starObservations")
    if not isinstance(stars, list) or not stars:
        raise ContractError("starObservations must be a non-empty array")
    normalized_stars: list[dict[str, Any]] = []
    star_ids: set[str] = set()
    for star in stars:
        if not isinstance(star, dict):
            raise ContractError("star observation must be an object")
        star_id = require_id(star.get("starId"), "starId")
        if star_id in star_ids:
            raise ContractError(f"duplicate starId: {star_id}")
        star_ids.add(star_id)
        observed = star.get("observed")
        if not isinstance(observed, bool):
            raise ContractError("star observed must be boolean")
        first_seen = star.get("firstSeenUtc")
        if observed:
            require_timestamp(first_seen, "firstSeenUtc")
        elif first_seen is not None:
            raise ContractError("unobserved star cannot have firstSeenUtc")
        normalized_stars.append(
            {
                "starId": star_id,
                "catalogMagnitude": require_number(star.get("catalogMagnitude"), "catalogMagnitude", -30.0, 30.0),
                "colorIndexBv": None if star.get("colorIndexBv") is None else require_number(star.get("colorIndexBv"), "colorIndexBv", -1.0, 5.0),
                "observed": observed,
                "firstSeenUtc": first_seen,
                "confidence": require_number(star.get("confidence"), "confidence", 0.0, 1.0),
            }
        )

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "observationId": observation_id,
        "role": role,
        "usedForParameterTuning": used_for_tuning,
        "timestampUtc": timestamp,
        "location": normalized_location,
        "geometry": normalized_geometry,
        "conditions": normalized_conditions,
        "acquisition": {
            "method": method,
            "instrumentId": instrument_id,
            "calibrationId": calibration_id,
            "screenFreeDuringObservation": screen_free,
        },
        "starObservations": normalized_stars,
    }
