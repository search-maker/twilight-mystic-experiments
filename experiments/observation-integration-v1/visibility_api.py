#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any

from contracts import ContractError, canonical_sha256, require_number
from radiance_api import RadianceProvider, validate_request

PHOTOPIC_WEIGHTS = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


def photopic_luminance(response: dict[str, Any]) -> float:
    values = response["radianceWm2SrNm"]
    return 683.002 * 10.0 * sum(value * weight for value, weight in zip(values, PHOTOPIC_WEIGHTS, strict=True))


def predict_visibility(request: dict[str, Any], provider: RadianceProvider) -> dict[str, Any]:
    if request.get("schemaVersion") != 1 or request.get("apiId") != "star-visibility-integration-v1":
        raise ContractError("visibility request header mismatch")
    radiance_request = validate_request(request.get("radianceRequest"))
    magnitude = require_number(request.get("catalogMagnitude"), "catalogMagnitude", -30.0, 30.0)
    extinction = require_number(request.get("extinctionMagnitude"), "extinctionMagnitude", 0.0, 10.0)
    color = require_number(request.get("colorIndexBv", 0.7), "colorIndexBv", -1.0, 5.0)
    adaptation = require_number(request.get("observerAdaptationOffsetMagnitude", 0.0), "observerAdaptationOffsetMagnitude", -3.0, 3.0)
    provider_response = provider.predict(radiance_request)
    luminance = photopic_luminance(provider_response)
    altitude = radiance_request["targetAltitudeDeg"]
    threshold_magnitude = (
        6.35
        - 1.20 * math.log10(max(luminance, 1e-12) / 0.001)
        - 0.65 * (1.0 - math.sin(math.radians(altitude)))
        - 0.08 * abs(color - 0.7)
        + adaptation
    )
    apparent_magnitude = magnitude + extinction
    margin = threshold_magnitude - apparent_magnitude
    probability = 1.0 / (1.0 + math.exp(-margin / 0.35))
    return {
        "schemaVersion": 1,
        "apiId": "star-visibility-integration-v1",
        "requestSha256": canonical_sha256(request),
        "providerId": provider_response["providerId"],
        "backgroundLuminanceCdM2": luminance,
        "apparentMagnitude": apparent_magnitude,
        "syntheticThresholdMagnitude": threshold_magnitude,
        "visibilityMarginMagnitude": margin,
        "syntheticVisibilityProbability": probability,
        "outOfDomain": provider_response["outOfDomain"],
        "syntheticOnly": True,
        "scientificVisibilityModelInstalled": False,
        "boundary": "end-to-end integration contract only; threshold and probability are synthetic placeholders",
    }
