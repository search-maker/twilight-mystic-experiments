#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Protocol

from contracts import ContractError, canonical_sha256, require_number

WAVELENGTHS_NM = [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660]


class RadianceProvider(Protocol):
    provider_id: str

    def predict(self, request: dict[str, Any]) -> dict[str, Any]: ...


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("radiance request must be an object")
    expected = {"schemaVersion": 1, "apiId": "twilight-radiance-spectrum-v1"}
    stale = {key: (request.get(key), value) for key, value in expected.items() if request.get(key) != value}
    if stale:
        raise ContractError(f"radiance request header mismatch: {stale}")
    return {
        "schemaVersion": 1,
        "apiId": "twilight-radiance-spectrum-v1",
        "sunDepressionDeg": require_number(request.get("sunDepressionDeg"), "sunDepressionDeg", -5.0, 30.0),
        "targetAltitudeDeg": require_number(request.get("targetAltitudeDeg"), "targetAltitudeDeg", 0.0, 90.0),
        "relativeAzimuthDeg": require_number(request.get("relativeAzimuthDeg"), "relativeAzimuthDeg", 0.0, 180.0),
        "aod550": require_number(request.get("aod550"), "aod550", 0.0, 5.0),
        "observerElevationM": require_number(request.get("observerElevationM"), "observerElevationM", -500.0, 10000.0),
        "wavelengthsNm": WAVELENGTHS_NM,
    }


def validate_response(response: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ContractError("radiance response must be an object")
    if response.get("schemaVersion") != 1 or response.get("apiId") != "twilight-radiance-spectrum-v1":
        raise ContractError("radiance response header mismatch")
    if response.get("requestSha256") != canonical_sha256(request):
        raise ContractError("radiance response is not bound to the request")
    values = response.get("radianceWm2SrNm")
    uncertainty = response.get("oneSigmaWm2SrNm")
    if not isinstance(values, list) or not isinstance(uncertainty, list):
        raise ContractError("radiance arrays are missing")
    if len(values) != len(WAVELENGTHS_NM) or len(uncertainty) != len(WAVELENGTHS_NM):
        raise ContractError("radiance arrays have the wrong length")
    for index, (value, sigma) in enumerate(zip(values, uncertainty, strict=True)):
        require_number(value, f"radiance[{index}]", 0.0)
        require_number(sigma, f"uncertainty[{index}]", 0.0)
    if not isinstance(response.get("outOfDomain"), bool):
        raise ContractError("outOfDomain must be boolean")
    if not isinstance(response.get("syntheticOnly"), bool):
        raise ContractError("syntheticOnly must be boolean")
    return response


class SyntheticRadianceProvider:
    provider_id = "analytic-synthetic-radiance-provider-v1"

    def predict(self, request: dict[str, Any]) -> dict[str, Any]:
        normalized = validate_request(request)
        depression = normalized["sunDepressionDeg"]
        altitude = normalized["targetAltitudeDeg"]
        azimuth = math.radians(normalized["relativeAzimuthDeg"])
        aod = normalized["aod550"]
        elevation = normalized["observerElevationM"]
        base_log = (
            -3.7
            - 0.34 * depression
            + 0.006 * altitude
            + 0.18 * math.cos(azimuth)
            - 1.1 * aod
            + 0.00005 * elevation
        )
        values: list[float] = []
        sigmas: list[float] = []
        for wavelength in WAVELENGTHS_NM:
            spectral_shape = 0.0017 * (wavelength - 555) + 0.09 * math.exp(-((wavelength - 600) / 55) ** 2)
            value = math.exp(base_log + spectral_shape)
            values.append(value)
            sigmas.append(value * (0.025 + 0.0015 * abs(wavelength - 555) / 10))
        response = {
            "schemaVersion": 1,
            "apiId": "twilight-radiance-spectrum-v1",
            "providerId": self.provider_id,
            "requestSha256": canonical_sha256(normalized),
            "wavelengthsNm": WAVELENGTHS_NM,
            "radianceWm2SrNm": values,
            "oneSigmaWm2SrNm": sigmas,
            "outOfDomain": depression < 3.0 or depression > 18.0 or aod > 0.5 or elevation > 3000.0,
            "syntheticOnly": True,
            "boundary": "analytic test provider; not MYSTIC, observations, or production radiance",
        }
        return validate_response(response, normalized)
