#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-observation-v1"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ObservationRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ObservationRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def number(value: Any, name: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ObservationRefusal(f"{name} must be finite")
    result = float(value)
    if result < minimum or result > maximum:
        raise ObservationRefusal(f"{name} outside [{minimum}, {maximum}]")
    return result


def identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ObservationRefusal(f"invalid {name}")
    return value


def parse_utc(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ObservationRefusal("timestampUtc must be an ISO-8601 UTC string ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ObservationRefusal("invalid timestampUtc") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise ObservationRefusal("timestampUtc is not UTC")
    return parsed.isoformat().replace("+00:00", "Z")


def stable_session_split(session_id: str, salt: str, validation_fraction: float) -> str:
    if not isinstance(salt, str) or not salt or not 0 < validation_fraction < 1:
        raise ObservationRefusal("split salt and validation fraction are invalid")
    digest = hashlib.sha256(f"{salt}\0{session_id}".encode()).digest()
    fraction = int.from_bytes(digest[:8], "big") / 2**64
    return "validation" if fraction < validation_fraction else "calibration"


def validate(
    record: dict[str, Any], split_salt: str, validation_fraction: float
) -> dict[str, Any]:
    if record.get("schemaVersion") != 1 or record.get("stageId") != STAGE_ID:
        raise ObservationRefusal("wrong schemaVersion or stageId")
    observation_id = identifier(record.get("observationId"), "observationId")
    session_id = identifier(record.get("sessionId"), "sessionId")
    observer_id = identifier(record.get("observerPseudonym"), "observerPseudonym")
    timestamp = parse_utc(record.get("timestampUtc"))

    location = record.get("location")
    pointing = record.get("pointing")
    atmosphere = record.get("atmosphere")
    quality = record.get("quality")
    source = record.get("source")
    if not all(
        isinstance(value, dict)
        for value in (location, pointing, atmosphere, quality, source)
    ):
        raise ObservationRefusal(
            "location, pointing, atmosphere, quality, and source must be objects"
        )

    normalized_location = {
        "latitudeDeg": number(location.get("latitudeDeg"), "latitudeDeg", -90, 90),
        "longitudeDeg": number(
            location.get("longitudeDeg"), "longitudeDeg", -180, 180
        ),
        "observerElevationM": number(
            location.get("observerElevationM"), "observerElevationM", -500, 10000
        ),
        "horizontalAccuracyM": number(
            location.get("horizontalAccuracyM"), "horizontalAccuracyM", 0, 100000
        ),
    }
    normalized_pointing = {
        "altitudeDeg": number(pointing.get("altitudeDeg"), "altitudeDeg", -5, 90),
        "azimuthDeg": number(pointing.get("azimuthDeg"), "azimuthDeg", 0, 360),
        "angularRadiusDeg": number(
            pointing.get("angularRadiusDeg"), "angularRadiusDeg", 0.01, 90
        ),
        "sunDepressionDeg": number(
            pointing.get("sunDepressionDeg"), "sunDepressionDeg", -10, 30
        ),
        "relativeSolarAzimuthDeg": number(
            pointing.get("relativeSolarAzimuthDeg"),
            "relativeSolarAzimuthDeg",
            0,
            360,
        ),
    }
    normalized_atmosphere = {
        "cloudFraction": number(
            atmosphere.get("cloudFraction"), "cloudFraction", 0, 1
        ),
        "aod550": (
            None
            if atmosphere.get("aod550") is None
            else number(atmosphere.get("aod550"), "aod550", 0, 5)
        ),
        "aodSource": atmosphere.get("aodSource"),
        "waterVaporCm": (
            None
            if atmosphere.get("waterVaporCm") is None
            else number(atmosphere.get("waterVaporCm"), "waterVaporCm", 0, 20)
        ),
        "notes": atmosphere.get("notes", ""),
    }
    if normalized_atmosphere["aod550"] is not None and not isinstance(
        normalized_atmosphere["aodSource"], str
    ):
        raise ObservationRefusal("aodSource is required when aod550 is present")

    instrument_type = source.get("instrumentType")
    if instrument_type not in {
        "calibrated-camera",
        "spectrometer",
        "sqm",
        "naked-eye",
    }:
        raise ObservationRefusal("unsupported instrumentType")
    calibration_id = source.get("calibrationId")
    if instrument_type != "naked-eye":
        identifier(calibration_id, "calibrationId")
    elif calibration_id is not None:
        raise ObservationRefusal("naked-eye observation must not claim calibrationId")

    raw_hashes = source.get("rawFileSha256", [])
    if not isinstance(raw_hashes, list) or any(
        not isinstance(value, str) or not SHA256_RE.fullmatch(value)
        for value in raw_hashes
    ):
        raise ObservationRefusal(
            "rawFileSha256 must contain lowercase SHA-256 values"
        )
    if instrument_type != "naked-eye" and not raw_hashes:
        raise ObservationRefusal(
            "instrument observation requires at least one raw file hash"
        )

    usable = quality.get("usable")
    if not isinstance(usable, bool):
        raise ObservationRefusal("quality.usable must be boolean")
    exclusion_reasons = quality.get("exclusionReasons", [])
    if not isinstance(exclusion_reasons, list) or any(
        not isinstance(value, str) for value in exclusion_reasons
    ):
        raise ObservationRefusal("exclusionReasons must be an array of strings")
    if usable and exclusion_reasons:
        raise ObservationRefusal("usable observation cannot have exclusion reasons")
    if not usable and not exclusion_reasons:
        raise ObservationRefusal("excluded observation requires at least one reason")

    assigned_split = stable_session_split(
        session_id, split_salt, validation_fraction
    )
    claimed_split = record.get("datasetRole")
    if claimed_split is not None and claimed_split != assigned_split:
        raise ObservationRefusal("datasetRole conflicts with frozen session split")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "VALIDATED",
        "observationId": observation_id,
        "sessionId": session_id,
        "observerPseudonym": observer_id,
        "timestampUtc": timestamp,
        "datasetRole": assigned_split,
        "location": normalized_location,
        "pointing": normalized_pointing,
        "atmosphere": normalized_atmosphere,
        "quality": {"usable": usable, "exclusionReasons": exclusion_reasons},
        "source": {
            "instrumentType": instrument_type,
            "calibrationId": calibration_id,
            "rawFileSha256": raw_hashes,
        },
        "boundary": "metadata validation only; no claim that the observation or calibration is scientifically valid",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split-salt", required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    args = parser.parse_args()
    try:
        result = validate(
            load_json(args.input), args.split_salt, args.validation_fraction
        )
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
