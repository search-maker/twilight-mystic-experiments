#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ALLOWED_LANES = {
    "PANDORA209_S2_JOHNSON_V_ONLY_V1": {"spectrometers": {2}, "requires_pairing": False},
    "PANDORA209_S1S2_THREE_CHANNEL_V1": {"spectrometers": {1, 2}, "requires_pairing": True},
}
ALLOWED_ARRAYS = {
    "LEVEL1.DATA",
    "LEVEL1.UNCERTAINTY",
    "LEVEL1.UNCERTAINTY.INSTRUMENT",
}
REQUIRED_BINDINGS = (
    "metadataUniverseCanonicalSha256",
    "admissionClassificationCanonicalSha256",
    "calibrationBindingCanonicalSha256",
    "operationPointingPairingBindingCanonicalSha256",
    "externalAodQcSupportClassificationCanonicalSha256",
    "measurementIntegrationBindingCanonicalSha256",
    "modelScenarioExtremaBindingCanonicalSha256",
    "numericAcceptanceGateBindingCanonicalSha256",
    "backgroundRuleBindingCanonicalSha256",
)
REQUIRED_OBJECT_FIELDS = (
    "sourceObjectId",
    "sourcePathOrProviderObjectId",
    "siteId",
    "instrumentId",
    "spectrometerId",
    "exposureIdentity",
    "metadataIdentitySha256",
    "calibrationBindingId",
    "operationBindingId",
    "protectedArrays",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def canonical_sha256(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def require_text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def require_sha256(value, label: str) -> str:
    text = require_text(value, label)
    if not SHA256_RE.fullmatch(text):
        raise ValueError(f"{label} must be lowercase SHA-256 hex")
    return text


def validate_prevalue_manifest(manifest: dict) -> dict:
    if manifest.get("schemaVersion") != 1:
        raise ValueError("schemaVersion must be 1")
    dataset_freeze_id = require_text(manifest.get("datasetFreezeId"), "datasetFreezeId")
    lane_id = require_text(manifest.get("laneId"), "laneId")
    if lane_id not in ALLOWED_LANES:
        raise ValueError(f"unsupported laneId: {lane_id}")
    require_text(manifest.get("createdAtUtc"), "createdAtUtc")

    bindings = manifest.get("preValueBindings")
    if not isinstance(bindings, dict):
        raise ValueError("preValueBindings must be an object")
    for key in REQUIRED_BINDINGS:
        require_sha256(bindings.get(key), f"preValueBindings.{key}")

    objects = manifest.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError("objects must be a non-empty list")
    source_ids = []
    seen = set()
    spec_seen = set()
    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            raise ValueError(f"objects[{index}] must be an object")
        for field in REQUIRED_OBJECT_FIELDS:
            if field not in obj:
                raise ValueError(f"objects[{index}].{field} missing")
        source_id = require_text(obj["sourceObjectId"], f"objects[{index}].sourceObjectId")
        if source_id in seen:
            raise ValueError(f"duplicate sourceObjectId: {source_id}")
        seen.add(source_id)
        source_ids.append(source_id)
        require_text(obj["sourcePathOrProviderObjectId"], f"objects[{index}].sourcePathOrProviderObjectId")
        require_text(obj["siteId"], f"objects[{index}].siteId")
        if obj["siteId"] != "Izana":
            raise ValueError("v1 opening lanes are source-scoped to Izana")
        require_text(obj["instrumentId"], f"objects[{index}].instrumentId")
        if str(obj["instrumentId"]) != "209":
            raise ValueError("v1 opening lanes are instrument-scoped to Pandora209")
        spec = obj["spectrometerId"]
        if not isinstance(spec, int) or spec not in ALLOWED_LANES[lane_id]["spectrometers"]:
            raise ValueError(f"objects[{index}].spectrometerId not allowed for {lane_id}")
        spec_seen.add(spec)
        require_text(obj["exposureIdentity"], f"objects[{index}].exposureIdentity")
        require_sha256(obj["metadataIdentitySha256"], f"objects[{index}].metadataIdentitySha256")
        require_text(obj["calibrationBindingId"], f"objects[{index}].calibrationBindingId")
        require_text(obj["operationBindingId"], f"objects[{index}].operationBindingId")
        arrays = obj["protectedArrays"]
        if not isinstance(arrays, list) or not arrays:
            raise ValueError(f"objects[{index}].protectedArrays must be non-empty")
        if len(set(arrays)) != len(arrays):
            raise ValueError(f"objects[{index}].protectedArrays contains duplicates")
        if not set(arrays).issubset(ALLOWED_ARRAYS):
            raise ValueError(f"objects[{index}].protectedArrays contains an unapproved array")
        if "LEVEL1.DATA" not in arrays:
            raise ValueError(f"objects[{index}] must explicitly name LEVEL1.DATA")
        forbidden = {
            "targetValueSha256",
            "targetRadianceSha256",
            "targetStatistics",
            "observedRadiance",
            "modelResidual",
        }
        if forbidden.intersection(obj):
            raise ValueError(f"objects[{index}] contains a target-outcome field before opening")

    if source_ids != sorted(source_ids):
        raise ValueError("objects must be lexicographically ordered by sourceObjectId")
    if ALLOWED_LANES[lane_id]["requires_pairing"] and spec_seen != {1, 2}:
        raise ValueError("three-channel lane must contain both spectrometer identities")
    if lane_id == "PANDORA209_S2_JOHNSON_V_ONLY_V1" and spec_seen != {2}:
        raise ValueError("Johnson-V-only lane may contain spectrometer 2 only")

    authorization = manifest.get("authorization")
    if not isinstance(authorization, dict):
        raise ValueError("authorization must be an object")
    # The pre-value manifest itself must NEVER authorize opening. Authorization
    # is a separate exact-hash-bound reviewed artifact.
    if authorization.get("targetOpeningAuthorized") is not False:
        raise ValueError("pre-value manifest must have targetOpeningAuthorized=false")
    if authorization.get("separateAuthorizationArtifactRequired") is not True:
        raise ValueError("separateAuthorizationArtifactRequired must be true")

    return {
        "valid": True,
        "datasetFreezeId": dataset_freeze_id,
        "laneId": lane_id,
        "objectCount": len(objects),
        "manifestCanonicalSha256": canonical_sha256(manifest),
        "targetOpeningAuthorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    result = validate_prevalue_manifest(load_json(args.manifest))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
