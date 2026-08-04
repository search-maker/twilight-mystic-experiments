from __future__ import annotations
from copy import deepcopy
from contracts import OBSERVATION_API_ID, RADIANCE_API_ID, SCHEMA_VERSION, SPECTRAL_GRID_NM, canonical_hash

PROVENANCE = {
    "createdBy": "contract-test",
    "createdAtUtc": "2026-08-04T12:00:00Z",
    "sourceSystem": "synthetic-fixture",
    "sourceRecordId": "synthetic-record-001",
    "transformHistory": [],
}


def observation(role: str = "calibration") -> dict:
    value = {
        "schemaVersion": SCHEMA_VERSION,
        "apiId": OBSERVATION_API_ID,
        "observationId": f"obs-{role}-001",
        "role": role,
        "usedForTuning": False,
        "roleHistory": [{"role": role, "effectiveAtUtc": "2026-08-04T12:00:00Z", "actor": "contract-test", "reason": "initial immutable assignment"}],
        "timestampUtc": "2026-08-04T00:30:00Z",
        "site": {"siteId": "site-001", "latitudeDeg": 40.7, "longitudeDeg": -74.0, "observerElevationM": 12.0, "observerElevationSemantics": "site-altitude-above-sea-level; observer-at-local-surface"},
        "targetGeometry": {"altitudeDeg": 30.0, "azimuthDeg": 90.0, "relativeAzimuthDeg": 90.0},
        "solarGeometry": {"sunDepressionDeg": 6.0, "solarAzimuthDeg": 270.0},
        "atmosphere": {"aod550": 0.15, "aodSource": "measured-nearest-hour", "relativeHumidityPercent": 55.0, "cloud": {"fraction": 0.0, "assessment": "clear", "notes": "synthetic fixture"}, "glareOrHalo": "none", "profileId": "profile-midlatitude-summer"},
        "acquisition": {"method": "naked-eye", "instrumentId": None, "calibrationId": None, "screenFree": True},
        "starObservations": [{"starId": "hip-001", "visible": True, "confidence": 0.8, "catalogMagnitude": 1.2, "colorIndexBv": 0.65}],
        "confidence": 0.8,
        "notes": "synthetic-only reproducible fixture",
        "provenance": deepcopy(PROVENANCE),
    }
    value["canonicalHash"] = canonical_hash(value)
    return value


def radiance_request() -> dict:
    value = {
        "schemaVersion": SCHEMA_VERSION,
        "apiId": RADIANCE_API_ID,
        "requestId": "request-001",
        "sunDepressionDeg": 6.0,
        "targetAltitudeDeg": 30.0,
        "relativeAzimuthDeg": 90.0,
        "observerElevationM": 12.0,
        "siteAltitudeSemantics": "site-altitude-above-sea-level; sensor-at-local-surface",
        "sensorHeightAboveLocalSurfaceM": 0,
        "aod550": 0.15,
        "atmosphericProfileId": "profile-midlatitude-summer",
        "albedo": 0.2,
        "spectralNodeRequestNm": SPECTRAL_GRID_NM,
        "modelVersionRequest": "surrogate-artifact-exact-version-required",
        "uncertaintyRequirements": {"required": True, "minimumCoverageFactor": 2.0},
        "provenance": deepcopy(PROVENANCE),
    }
    value["canonicalRequestHash"] = canonical_hash(value)
    return value
