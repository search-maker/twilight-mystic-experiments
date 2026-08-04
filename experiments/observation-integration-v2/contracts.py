from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable

SCHEMA_VERSION = 2
OBSERVATION_API_ID = "mystic-observation-v2"
RADIANCE_API_ID = "mystic-radiance-v2"
VISIBILITY_API_ID = "star-visibility-integration-v2"
SPECTRAL_GRID_NM = [360, 380, 400, 420, 440, 460, 480, 500, 520, 540, 560, 580, 600, 650, 700]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_hash(value: Any, excluded_fields: Iterable[str] = ("canonicalHash", "canonicalRequestHash")) -> str:
    excluded = set(excluded_fields)

    def scrub(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: scrub(val) for key, val in item.items() if key not in excluded}
        if isinstance(item, list):
            return [scrub(val) for val in item]
        return item

    return hashlib.sha256(canonical_json(scrub(value)).encode("utf-8")).hexdigest()


def _finite(value: Any, name: str, low: float | None = None, high: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ContractError(f"{name} must be finite")
    result = float(value)
    if low is not None and result < low:
        raise ContractError(f"{name} must be >= {low}")
    if high is not None and result > high:
        raise ContractError(f"{name} must be <= {high}")
    return result


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ContractError(f"{name} is invalid")
    return value


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
        raise ContractError(f"{name} must be lowercase SHA-256")
    return value


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ContractError(f"{name} must be UTC RFC3339 ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{name} is malformed") from exc
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError(f"{name} must be UTC")
    return value


def _provenance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("provenance is required")
    required = ("createdBy", "createdAtUtc", "sourceSystem", "sourceRecordId", "transformHistory")
    missing = [field for field in required if field not in value]
    if missing:
        raise ContractError(f"malformed provenance: missing {missing}")
    _id(value["createdBy"], "provenance.createdBy")
    _timestamp(value["createdAtUtc"], "provenance.createdAtUtc")
    _id(value["sourceSystem"], "provenance.sourceSystem")
    _id(value["sourceRecordId"], "provenance.sourceRecordId")
    if not isinstance(value["transformHistory"], list):
        raise ContractError("provenance.transformHistory must be an array")
    for index, event in enumerate(value["transformHistory"]):
        if not isinstance(event, dict) or set(("atUtc", "actor", "action")) - set(event):
            raise ContractError(f"provenance.transformHistory[{index}] malformed")
        _timestamp(event["atUtc"], f"provenance.transformHistory[{index}].atUtc")
        _id(event["actor"], f"provenance.transformHistory[{index}].actor")
        if not isinstance(event["action"], str) or not event["action"].strip():
            raise ContractError(f"provenance.transformHistory[{index}].action required")
    return deepcopy(value)


def validate_observation(record: dict[str, Any], existing_ids: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ContractError("observation must be an object")
    if record.get("schemaVersion") != SCHEMA_VERSION or record.get("apiId") != OBSERVATION_API_ID:
        raise ContractError("observation header mismatch")
    observation_id = _id(record.get("observationId"), "observationId")
    if existing_ids is not None and observation_id in existing_ids:
        raise ContractError(f"duplicate observationId: {observation_id}")
    role = record.get("role")
    if role not in {"calibration", "validation"}:
        raise ContractError("role must be calibration or validation")
    tuning = record.get("usedForTuning")
    if not isinstance(tuning, bool):
        raise ContractError("usedForTuning must be boolean")
    if role == "validation" and tuning:
        raise ContractError("validation observation used for tuning is forbidden")
    role_history = record.get("roleHistory")
    if not isinstance(role_history, list) or not role_history:
        raise ContractError("roleHistory must preserve an explicit audit trail")
    for event in role_history:
        if not isinstance(event, dict) or set(("role", "effectiveAtUtc", "actor", "reason")) - set(event):
            raise ContractError("roleHistory event malformed")
        if event["role"] not in {"calibration", "validation"}:
            raise ContractError("roleHistory role invalid")
        _timestamp(event["effectiveAtUtc"], "roleHistory.effectiveAtUtc")
        _id(event["actor"], "roleHistory.actor")
        if not isinstance(event["reason"], str) or not event["reason"].strip():
            raise ContractError("roleHistory reason required")
    if role_history[-1]["role"] != role:
        raise ContractError("current role must match final roleHistory event")
    roles = [event["role"] for event in role_history]
    if "validation" in roles and role == "calibration" and len(role_history) < 2:
        raise ContractError("validation-to-calibration requires explicit audit trail")

    _timestamp(record.get("timestampUtc"), "timestampUtc")
    site = record.get("site")
    if not isinstance(site, dict):
        raise ContractError("site is required")
    _id(site.get("siteId"), "site.siteId")
    _finite(site.get("latitudeDeg"), "site.latitudeDeg", -90, 90)
    _finite(site.get("longitudeDeg"), "site.longitudeDeg", -180, 180)
    _finite(site.get("observerElevationM"), "site.observerElevationM", -500, 10000)
    if site.get("observerElevationSemantics") != "site-altitude-above-sea-level; observer-at-local-surface":
        raise ContractError("observer elevation semantics missing or contradictory")

    target = record.get("targetGeometry")
    solar = record.get("solarGeometry")
    if not isinstance(target, dict) or not isinstance(solar, dict):
        raise ContractError("targetGeometry and solarGeometry are required")
    _finite(target.get("altitudeDeg"), "targetGeometry.altitudeDeg", 0, 90)
    _finite(target.get("azimuthDeg"), "targetGeometry.azimuthDeg", 0, 360)
    _finite(target.get("relativeAzimuthDeg"), "targetGeometry.relativeAzimuthDeg", 0, 180)
    _finite(solar.get("sunDepressionDeg"), "solarGeometry.sunDepressionDeg", 0, 30)
    _finite(solar.get("solarAzimuthDeg"), "solarGeometry.solarAzimuthDeg", 0, 360)

    atmosphere = record.get("atmosphere")
    if not isinstance(atmosphere, dict):
        raise ContractError("atmosphere is required")
    _finite(atmosphere.get("aod550"), "atmosphere.aod550", 0, 5)
    if not isinstance(atmosphere.get("aodSource"), str) or not atmosphere["aodSource"].strip():
        raise ContractError("atmosphere.aodSource required")
    _finite(atmosphere.get("relativeHumidityPercent"), "atmosphere.relativeHumidityPercent", 0, 100)
    cloud = atmosphere.get("cloud")
    if not isinstance(cloud, dict):
        raise ContractError("cloud information required")
    _finite(cloud.get("fraction"), "atmosphere.cloud.fraction", 0, 1)
    if cloud.get("assessment") not in {"clear", "scattered", "broken", "overcast", "unknown"}:
        raise ContractError("cloud assessment invalid")
    if atmosphere.get("glareOrHalo") not in {"none", "glare", "halo", "both", "unknown"}:
        raise ContractError("glareOrHalo invalid")

    acquisition = record.get("acquisition")
    if not isinstance(acquisition, dict):
        raise ContractError("acquisition required")
    if acquisition.get("method") not in {"naked-eye", "camera", "spectrometer", "sqm", "other"}:
        raise ContractError("acquisition.method invalid")
    if not isinstance(acquisition.get("screenFree"), bool):
        raise ContractError("acquisition.screenFree must be boolean")
    for key in ("instrumentId", "calibrationId"):
        value = acquisition.get(key)
        if value is not None:
            _id(value, f"acquisition.{key}")

    stars = record.get("starObservations")
    if not isinstance(stars, list) or not stars:
        raise ContractError("starObservations must be non-empty")
    seen: set[str] = set()
    for star in stars:
        if not isinstance(star, dict):
            raise ContractError("star observation malformed")
        star_id = _id(star.get("starId"), "starId")
        if star_id in seen:
            raise ContractError(f"duplicate starId: {star_id}")
        seen.add(star_id)
        if not isinstance(star.get("visible"), bool):
            raise ContractError("star.visible must be boolean")
        _finite(star.get("confidence"), "star.confidence", 0, 1)
        _finite(star.get("catalogMagnitude"), "star.catalogMagnitude", -30, 30)
        color = star.get("colorIndexBv")
        if color is not None:
            _finite(color, "star.colorIndexBv", -1, 5)

    _finite(record.get("confidence"), "confidence", 0, 1)
    if not isinstance(record.get("notes"), str):
        raise ContractError("notes must be a string")
    _provenance(record.get("provenance"))
    expected = canonical_hash(record)
    if record.get("canonicalHash") != expected:
        raise ContractError("canonicalHash mismatch")
    return deepcopy(record)


def validate_radiance_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("radiance request must be an object")
    if request.get("schemaVersion") != SCHEMA_VERSION or request.get("apiId") != RADIANCE_API_ID:
        raise ContractError("radiance request header mismatch")
    _id(request.get("requestId"), "requestId")
    _finite(request.get("sunDepressionDeg"), "sunDepressionDeg", 0, 30)
    _finite(request.get("targetAltitudeDeg"), "targetAltitudeDeg", 0, 90)
    _finite(request.get("relativeAzimuthDeg"), "relativeAzimuthDeg", 0, 180)
    _finite(request.get("observerElevationM"), "observerElevationM", -500, 10000)
    semantics = request.get("siteAltitudeSemantics")
    if semantics != "site-altitude-above-sea-level; sensor-at-local-surface":
        raise ContractError("site altitude semantics missing or contradictory")
    if request.get("sensorHeightAboveLocalSurfaceM", 0) != 0:
        raise ContractError("sensorHeightAboveLocalSurfaceM contradicts site-altitude semantics")
    _finite(request.get("aod550"), "aod550", 0, 5)
    _id(request.get("atmosphericProfileId"), "atmosphericProfileId")
    _finite(request.get("albedo"), "albedo", 0, 1)
    grid = request.get("spectralNodeRequestNm")
    if grid != SPECTRAL_GRID_NM:
        raise ContractError("unsupported spectral grid")
    _id(request.get("modelVersionRequest"), "modelVersionRequest")
    uncertainty = request.get("uncertaintyRequirements")
    if uncertainty is not None:
        if not isinstance(uncertainty, dict) or not isinstance(uncertainty.get("required"), bool):
            raise ContractError("uncertaintyRequirements malformed")
    _provenance(request.get("provenance"))
    expected = canonical_hash(request)
    if request.get("canonicalRequestHash") != expected:
        raise ContractError("canonicalRequestHash mismatch")
    return deepcopy(request)


def validate_radiance_response(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ContractError("radiance response must be an object")
    if response.get("schemaVersion") != SCHEMA_VERSION or response.get("apiId") != RADIANCE_API_ID:
        raise ContractError("radiance response header mismatch")
    _sha(response.get("requestHash"), "requestHash")
    _id(response.get("modelId"), "modelId")
    _id(response.get("modelVersion"), "modelVersion")
    _sha(response.get("modelArtifactHash"), "modelArtifactHash")
    _sha(response.get("sourceDatasetHash"), "sourceDatasetHash")
    source_sha = response.get("sourceCodeSha")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ContractError("sourceCodeSha must be a 40-character git SHA")
    _timestamp(response.get("generatedAtUtc"), "generatedAtUtc")
    refusal = response.get("refusalReason")
    spectrum = response.get("spectrum")
    if refusal is None:
        if not isinstance(spectrum, list) or len(spectrum) != 15:
            raise ContractError("complete 15-node spectrum required")
        wavelengths = [node.get("wavelengthNm") for node in spectrum if isinstance(node, dict)]
        if wavelengths != SPECTRAL_GRID_NM:
            raise ContractError("spectrum grid mismatch")
        for node in spectrum:
            _finite(node.get("radiance"), "spectrum.radiance", 0)
        _finite(response.get("integratedPhotopicQuantity"), "integratedPhotopicQuantity", 0)
    else:
        if not isinstance(refusal, str) or not refusal.strip():
            raise ContractError("refusalReason malformed")
        if spectrum not in (None, []):
            raise ContractError("refused response must not contain a spectrum")
    uncertainty = response.get("uncertainty")
    if not isinstance(uncertainty, dict):
        raise ContractError("uncertainty required")
    _finite(uncertainty.get("standardUncertainty"), "uncertainty.standardUncertainty", 0)
    if not isinstance(response.get("uncertaintyMethod"), str) or not response["uncertaintyMethod"].strip():
        raise ContractError("uncertaintyMethod required")
    _finite(response.get("nearestTrainingDistance"), "nearestTrainingDistance", 0)
    if not isinstance(response.get("outOfDomain"), bool):
        raise ContractError("outOfDomain must be boolean")
    if not isinstance(response.get("warnings"), list):
        raise ContractError("warnings must be an array")
    if response.get("productionEligibility") not in {"forbidden", "not-validated", "eligible"}:
        raise ContractError("productionEligibility invalid")
    if response.get("observationValidationStatus") not in {"not-started", "partial", "validated", "failed"}:
        raise ContractError("observationValidationStatus invalid")
    if response["outOfDomain"]:
        if "OUT_OF_DOMAIN" not in response["warnings"]:
            raise ContractError("out-of-domain warning cannot be hidden")
        if response["productionEligibility"] == "eligible":
            raise ContractError("out-of-domain response cannot be production eligible")
    if response["observationValidationStatus"] != "validated" and response["productionEligibility"] == "eligible":
        raise ContractError("unvalidated response cannot claim production eligibility")
    return deepcopy(response)


def build_visibility_input(radiance_response: dict[str, Any], *, catalog_magnitude: float, color_information: dict[str, Any] | None, extinction_inputs: dict[str, Any], observer_adaptation_inputs: dict[str, Any]) -> dict[str, Any]:
    response = validate_radiance_response(radiance_response)
    result = {
        "schemaVersion": SCHEMA_VERSION,
        "apiId": VISIBILITY_API_ID,
        "catalogMagnitude": _finite(catalog_magnitude, "catalogMagnitude", -30, 30),
        "colorInformation": deepcopy(color_information),
        "extinctionInputs": deepcopy(extinction_inputs),
        "observerAdaptationInputs": deepcopy(observer_adaptation_inputs),
        "radianceSpectrum": deepcopy(response.get("spectrum")),
        "radianceUncertainty": deepcopy(response["uncertainty"]),
        "outOfDomain": response["outOfDomain"],
        "warnings": deepcopy(response["warnings"]),
        "modelProvenance": {
            "modelId": response["modelId"],
            "modelVersion": response["modelVersion"],
            "modelArtifactHash": response["modelArtifactHash"],
            "sourceDatasetHash": response["sourceDatasetHash"],
            "sourceCodeSha": response["sourceCodeSha"],
            "requestHash": response["requestHash"],
        },
        "syntheticOnly": True,
        "scientificVisibilityModelInstalled": False,
        "productionUseForbidden": True,
        "observationallyValidated": False,
    }
    if result["scientificVisibilityModelInstalled"] is not False or result["productionUseForbidden"] is not True:
        raise ContractError("scientific model or production readiness claim forbidden")
    return result


def synthetic_radiance_response(request: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_radiance_request(request)
    values = []
    for wavelength in SPECTRAL_GRID_NM:
        radiance = 1e-6 * (1 + wavelength / 1000) * (1 + normalized["aod550"]) / (1 + normalized["sunDepressionDeg"])
        values.append({"wavelengthNm": wavelength, "radiance": radiance})
    out_of_domain = normalized["sunDepressionDeg"] > 18 or normalized["aod550"] > 1
    warnings = ["SYNTHETIC_ONLY", "NOT_OBSERVATIONALLY_VALIDATED"]
    if out_of_domain:
        warnings.append("OUT_OF_DOMAIN")
    response = {
        "schemaVersion": SCHEMA_VERSION,
        "apiId": RADIANCE_API_ID,
        "requestHash": normalized["canonicalRequestHash"],
        "modelId": "synthetic-contract-provider",
        "modelVersion": "v2-test-only",
        "modelArtifactHash": "1" * 64,
        "sourceDatasetHash": "2" * 64,
        "sourceCodeSha": "3" * 40,
        "generatedAtUtc": "2026-08-04T12:00:00Z",
        "spectrum": values,
        "integratedPhotopicQuantity": sum(node["radiance"] for node in values),
        "uncertainty": {"standardUncertainty": 0.25, "coverageFactor": 2.0},
        "uncertaintyMethod": "synthetic-fixed-contract-value",
        "nearestTrainingDistance": 0.75 if not out_of_domain else 2.5,
        "outOfDomain": out_of_domain,
        "refusalReason": None,
        "warnings": warnings,
        "productionEligibility": "forbidden",
        "observationValidationStatus": "not-started",
    }
    return validate_radiance_response(response)
