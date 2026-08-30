#!/usr/bin/env python3
"""Solver-free Phase-B contract for LOWALT-STELLAR-STATE-0001.

Frozen by Issue #60 comment 5467228174 after Phase-A exec002 established
numerical representability through 0.25 deg. This module contains no solver
execution path and does not authorize opening protected results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from typing import Any

SCIENTIFIC_STATE = "LOWALT-STELLAR-STATE-0001"
PHASE_B_FREEZE_COMMENT_ID = 5467228174
BASE_PUBLIC_MAIN = "30ec5d1c37a3228b56a959e3b44afebd763a8563"
SOURCE_V32_RUNTIME_PATH = "generated/level-b-stellar-v32/stellar-transport-v32-zenith-lut.json"
SOURCE_V32_RUNTIME_SHA256 = "0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2"

WAVELENGTH_NM = tuple(range(380, 781))
TRAINING_ALTITUDE_DEG = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5)
LOWER_ASSET_ALTITUDE_DEG = (*TRAINING_ALTITUDE_DEG, 5.0)
ELEVATION_KNOTS_M = (0.0, 500.0, 1250.0, 2000.0, 2500.0)
AOD_KNOTS = (0.05, 0.10, 0.20, 0.30, 0.40)
PROTECTED_ALTITUDE_DEG = (0.34375, 0.59375, 0.84375, 1.1875, 1.6875, 2.1875, 2.6875, 3.1875, 3.6875, 4.1875, 4.6875)
PROTECTED_ELEVATION_M = (187.5, 781.25, 1531.25, 2187.5)
PROTECTED_AOD550 = (0.06875, 0.1375, 0.2375, 0.3375)
REPRESENTATIVE_LIBRARY_NUMBERS = (1, 26, 45)

EXPECTED_TRAINING_SPECTRA = 275
EXPECTED_SEAM_SPECTRA = 25
EXPECTED_PROTECTED_SPECTRA = 176
EXPECTED_PROTECTED_COMPARISONS = 528
MAX_ABS_ERROR_MAG_LIMIT = 0.025
RMS_ERROR_MAG_LIMIT = 0.010
V32_MAX_SUPPORTED_DEG = 90.0
HISTORICAL_PROTECTED_MIN_ALTITUDE_DEG = {
    "MYSTIC-STATE-0077": 6.25,
    "MYSTIC-STATE-0081-v2": 5.0,
    "MYSTIC-STATE-0081-v3": 5.0,
    "MYSTIC-STATE-0081-v3.2": 5.0,
}


class PhaseBRefusal(RuntimeError):
    pass


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise PhaseBRefusal(f"{name} must be finite")
    return number


def coord(h: float, e: float, a: float) -> tuple[float, float, float]:
    return (round(float(h), 9), round(float(e), 9), round(float(a), 9))


def case(h: float, e: float, a: float) -> dict[str, float]:
    return {
        "targetGeometricAltitudeDeg": float(h),
        "sourceZenithAngleDeg": 90.0 - float(h),
        "observerElevationM": float(e),
        "aod550": float(a),
    }


def build_training_cases() -> list[dict[str, float]]:
    return [case(h, e, a) for h in TRAINING_ALTITUDE_DEG for e in ELEVATION_KNOTS_M for a in AOD_KNOTS]


def build_seam_cases() -> list[dict[str, float]]:
    return [case(5.0, e, a) for e in ELEVATION_KNOTS_M for a in AOD_KNOTS]


def build_protected_cases() -> list[dict[str, float]]:
    return [case(h, e, a) for h in PROTECTED_ALTITUDE_DEG for e in PROTECTED_ELEVATION_M for a in PROTECTED_AOD550]


def validate_frozen_universe() -> None:
    training = build_training_cases()
    seam = build_seam_cases()
    protected = build_protected_cases()
    if len(training) != EXPECTED_TRAINING_SPECTRA or len(seam) != EXPECTED_SEAM_SPECTRA or len(protected) != EXPECTED_PROTECTED_SPECTRA:
        raise PhaseBRefusal("frozen Phase-B case count drift")
    tk = {coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in training}
    sk = {coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in seam}
    pk = {coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in protected}
    if len(tk) != len(training) or len(sk) != len(seam) or len(pk) != len(protected):
        raise PhaseBRefusal("duplicate Phase-B coordinates")
    if tk & sk or tk & pk or sk & pk:
        raise PhaseBRefusal("training/seam/protected coordinate collision")
    if max(PROTECTED_ALTITUDE_DEG) >= 5.0:
        raise PhaseBRefusal("fresh protected matrix escaped the <5 deg domain")
    for identity, old_floor in HISTORICAL_PROTECTED_MIN_ALTITUDE_DEG.items():
        if max(PROTECTED_ALTITUDE_DEG) >= old_floor:
            raise PhaseBRefusal(f"fresh protected matrix can collide with {identity}")
    if len(protected) * len(REPRESENTATIVE_LIBRARY_NUMBERS) != EXPECTED_PROTECTED_COMPARISONS:
        raise PhaseBRefusal("protected Johnson-V comparison count drift")
    if MAX_ABS_ERROR_MAG_LIMIT != 0.025 or RMS_ERROR_MAG_LIMIT != 0.010:
        raise PhaseBRefusal("acceptance gate drift")


def _tau_spectrum(values: object, label: str) -> list[float]:
    if not isinstance(values, list) or len(values) != len(WAVELENGTH_NM):
        raise PhaseBRefusal(f"{label} must contain exactly 401 optical depths")
    out: list[float] = []
    for raw in values:
        tau = finite(label, raw)
        if tau < 0.0:
            raise PhaseBRefusal(f"{label} contains negative optical depth")
        transmission = math.exp(-tau)
        if not math.isfinite(transmission) or not 0.0 < transmission <= 1.0:
            raise PhaseBRefusal(f"{label} unresolved: epsilon substitution is forbidden")
        out.append(tau)
    return out


def validate_training_results(rows: list[dict[str, Any]]) -> dict[tuple[float, float, float], list[float]]:
    expected = {coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in build_training_cases()}
    observed: dict[tuple[float, float, float], list[float]] = {}
    for row in rows:
        key = coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"])
        if key in observed:
            raise PhaseBRefusal("duplicate training result")
        observed[key] = _tau_spectrum(row.get("directOpticalDepth"), f"training{key}")
    if set(observed) != expected:
        raise PhaseBRefusal("training result universe incomplete or drifted")
    return observed


def extract_v32_five_degree_seam(runtime: dict[str, Any]) -> dict[tuple[float, float, float], list[float]]:
    axes = runtime.get("axes") or {}
    altitudes = [float(x) for x in axes.get("targetAltitudeDeg", [])]
    elevations = [float(x) for x in axes.get("observerElevationM", [])]
    aods = [float(x) for x in axes.get("aod550", [])]
    wavelengths = [int(x) for x in runtime.get("wavelengthNm", [])]
    spectra = runtime.get("directOpticalDepth")
    if 5.0 not in altitudes or tuple(elevations) != ELEVATION_KNOTS_M or tuple(aods) != AOD_KNOTS or tuple(wavelengths) != WAVELENGTH_NM:
        raise PhaseBRefusal("authoritative v3.2 axis contract drift")
    if not isinstance(spectra, list) or len(spectra) != len(altitudes) * len(elevations) * len(aods):
        raise PhaseBRefusal("authoritative v3.2 spectrum count drift")
    hi = altitudes.index(5.0)
    seam: dict[tuple[float, float, float], list[float]] = {}
    for ei, elevation in enumerate(elevations):
        for ai, aod in enumerate(aods):
            index = ((hi * len(elevations)) + ei) * len(aods) + ai
            seam[coord(5.0, elevation, aod)] = _tau_spectrum(spectra[index], f"v32Seam[{ei},{ai}]")
    if len(seam) != EXPECTED_SEAM_SPECTRA:
        raise PhaseBRefusal("authoritative 5-deg seam count drift")
    return seam


def assemble_lower_runtime(training_rows: list[dict[str, Any]], source_v32_runtime: dict[str, Any]) -> dict[str, Any]:
    validate_frozen_universe()
    training = validate_training_results(training_rows)
    seam = extract_v32_five_degree_seam(source_v32_runtime)
    spectra: list[list[float]] = []
    for h in LOWER_ASSET_ALTITUDE_DEG:
        for e in ELEVATION_KNOTS_M:
            for a in AOD_KNOTS:
                key = coord(h, e, a)
                spectra.append(list(training[key] if h < 5.0 else seam[key]))
    runtime = {
        "schemaVersion": 1,
        "quantity": "level-b-stellar-direct-optical-depth-lut-lower-extension",
        "scientificState": SCIENTIFIC_STATE,
        "axes": {"targetAltitudeDeg": list(LOWER_ASSET_ALTITUDE_DEG), "observerElevationM": list(ELEVATION_KNOTS_M), "aod550": list(AOD_KNOTS)},
        "wavelengthNm": list(WAVELENGTH_NM),
        "directOpticalDepth": spectra,
        "representation": {"interpolatedQuantity": "direct-optical-depth", "targetAltitudeCoordinate": "identity-geometric-altitude-deg", "targetAltitudeInterpolation": "linear", "observerElevationInterpolation": "linear", "aod550Interpolation": "linear", "cscExtrapolationBelow5Deg": False},
        "routing": {"lowerProviderMinInclusiveDeg": 0.25, "lowerProviderMaxExclusiveDeg": 5.0, "exactFiveAndAboveProvider": "authoritative-v3.2", "outsideSupport": "STELLAR_SPECTRAL_RUNTIME_OOD", "exactHorizonSupported": False},
        "provenance": {"phaseBFreezeIssue60CommentId": PHASE_B_FREEZE_COMMENT_ID, "sourceV32RuntimePath": SOURCE_V32_RUNTIME_PATH, "sourceV32RuntimeSha256": SOURCE_V32_RUNTIME_SHA256, "freshTrainingSpectrumCount": EXPECTED_TRAINING_SPECTRA, "inheritedFiveDegreeSeamSpectrumCount": EXPECTED_SEAM_SPECTRA, "protectedResultsOpened": False, "productionAuthorized": False, "postResultRetuningPerformed": False},
    }
    validate_lower_runtime(runtime, source_v32_runtime)
    return runtime


def validate_lower_runtime(runtime: dict[str, Any], source_v32_runtime: dict[str, Any] | None = None) -> None:
    axes = runtime.get("axes") or {}
    if tuple(float(x) for x in axes.get("targetAltitudeDeg", [])) != LOWER_ASSET_ALTITUDE_DEG:
        raise PhaseBRefusal("lower altitude axis drift")
    if tuple(float(x) for x in axes.get("observerElevationM", [])) != ELEVATION_KNOTS_M or tuple(float(x) for x in axes.get("aod550", [])) != AOD_KNOTS:
        raise PhaseBRefusal("lower atmosphere axes drift")
    if tuple(int(x) for x in runtime.get("wavelengthNm", [])) != WAVELENGTH_NM:
        raise PhaseBRefusal("lower wavelength grid drift")
    rep = runtime.get("representation") or {}
    if rep.get("targetAltitudeCoordinate") != "identity-geometric-altitude-deg" or rep.get("cscExtrapolationBelow5Deg") is not False:
        raise PhaseBRefusal("forbidden lower-altitude representation drift")
    spectra = runtime.get("directOpticalDepth")
    expected = len(LOWER_ASSET_ALTITUDE_DEG) * len(ELEVATION_KNOTS_M) * len(AOD_KNOTS)
    if not isinstance(spectra, list) or len(spectra) != expected:
        raise PhaseBRefusal("lower spectrum count drift")
    for index, spectrum in enumerate(spectra):
        _tau_spectrum(spectrum, f"lower[{index}]")
    if source_v32_runtime is not None:
        seam = extract_v32_five_degree_seam(source_v32_runtime)
        seam_hi = len(LOWER_ASSET_ALTITUDE_DEG) - 1
        for ei, e in enumerate(ELEVATION_KNOTS_M):
            for ai, a in enumerate(AOD_KNOTS):
                index = ((seam_hi * len(ELEVATION_KNOTS_M)) + ei) * len(AOD_KNOTS) + ai
                if spectra[index] != seam[coord(5.0, e, a)]:
                    raise PhaseBRefusal("5-deg seam is not content-identical to authoritative v3.2")


def _bracket(axis: tuple[float, ...], value: float) -> tuple[int, int, float]:
    q = finite("interpolation coordinate", value)
    if q < axis[0] or q > axis[-1]:
        raise PhaseBRefusal("interpolation coordinate outside support")
    if q == axis[-1]:
        return len(axis) - 2, len(axis) - 1, 1.0
    for i in range(len(axis) - 1):
        if axis[i] <= q <= axis[i + 1]:
            return i, i + 1, (q - axis[i]) / (axis[i + 1] - axis[i])
    raise PhaseBRefusal("interpolation bracket failure")


def interpolate_lower_tau(runtime: dict[str, Any], target_geometric_altitude_deg: float, observer_elevation_m: float, aod550: float) -> list[float]:
    validate_lower_runtime(runtime)
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    if not 0.25 <= h < 5.0:
        raise PhaseBRefusal("lower provider only serves [0.25,5)")
    hb = _bracket(LOWER_ASSET_ALTITUDE_DEG, h)
    eb = _bracket(ELEVATION_KNOTS_M, observer_elevation_m)
    ab = _bracket(AOD_KNOTS, aod550)
    spectra = runtime["directOpticalDepth"]
    n_e, n_a = len(ELEVATION_KNOTS_M), len(AOD_KNOTS)
    out: list[float] = []
    for wi in range(len(WAVELENGTH_NM)):
        def c(hi: int, ei: int, ai: int) -> float:
            return float(spectra[((hi * n_e) + ei) * n_a + ai][wi])
        lo0 = c(hb[0], eb[0], ab[0]) + (c(hb[0], eb[0], ab[1]) - c(hb[0], eb[0], ab[0])) * ab[2]
        lo1 = c(hb[0], eb[1], ab[0]) + (c(hb[0], eb[1], ab[1]) - c(hb[0], eb[1], ab[0])) * ab[2]
        hi0 = c(hb[1], eb[0], ab[0]) + (c(hb[1], eb[0], ab[1]) - c(hb[1], eb[0], ab[0])) * ab[2]
        hi1 = c(hb[1], eb[1], ab[0]) + (c(hb[1], eb[1], ab[1]) - c(hb[1], eb[1], ab[0])) * ab[2]
        lo = lo0 + (lo1 - lo0) * eb[2]
        hi = hi0 + (hi1 - hi0) * eb[2]
        tau = finite("interpolatedDirectOpticalDepth", lo + (hi - lo) * hb[2])
        t = math.exp(-tau)
        if tau < 0.0 or not math.isfinite(t) or not 0.0 < t <= 1.0:
            raise PhaseBRefusal("interpolated transmission numerically unresolved")
        out.append(tau)
    return out


def route_provider(target_geometric_altitude_deg: float) -> str:
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    if 0.25 <= h < 5.0:
        return "LOWALT_STELLAR_V1_CANDIDATE"
    if 5.0 <= h <= V32_MAX_SUPPORTED_DEG:
        return "AUTHORITATIVE_STELLAR_V32"
    return "STELLAR_SPECTRAL_RUNTIME_OOD"


def _metrics(values: list[float]) -> dict[str, Any]:
    if not values:
        raise PhaseBRefusal("empty validation metric set")
    max_abs = max(abs(x) for x in values)
    rms = math.sqrt(sum(x * x for x in values) / len(values))
    return {"comparisonCount": len(values), "maxAbsDeltaAvMag": max_abs, "rmsDeltaAvMag": rms, "passed": max_abs <= MAX_ABS_ERROR_MAG_LIMIT and rms <= RMS_ERROR_MAG_LIMIT}


def evaluate_protected_deltas(rows: list[dict[str, Any]]) -> dict[str, Any]:
    validate_frozen_universe()
    expected = {(coord(c["targetGeometricAltitudeDeg"], c["observerElevationM"], c["aod550"]), lib) for c in build_protected_cases() for lib in REPRESENTATIVE_LIBRARY_NUMBERS}
    observed: dict[tuple[tuple[float, float, float], int], float] = {}
    for row in rows:
        key = (coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"]), int(row["libraryNumber"]))
        if key in observed:
            raise PhaseBRefusal("duplicate protected comparison")
        observed[key] = finite("deltaAvMag", row["deltaAvMag"])
    if set(observed) != expected or len(observed) != EXPECTED_PROTECTED_COMPARISONS:
        raise PhaseBRefusal("protected comparison universe incomplete or drifted")
    overall = _metrics(list(observed.values()))
    per_altitude = {str(h): _metrics([v for (k, _lib), v in observed.items() if k[0] == h]) for h in PROTECTED_ALTITUDE_DEG}
    passed = overall["passed"] and all(m["passed"] for m in per_altitude.values())
    return {"scientificState": SCIENTIFIC_STATE, "status": "PROTECTED_VALIDATION_PASS" if passed else "PROTECTED_VALIDATION_FAIL", "overall": overall, "byProtectedAltitudeDeg": per_altitude, "minimumSupportedGeometricAltitudeIfPassDeg": 0.25, "exactHorizonSupported": False, "productionAuthorized": False, "postResultFloorBackSelectionAuthorized": False}


def review_ledger() -> dict[str, Any]:
    validate_frozen_universe()
    payload = {
        "schemaVersion": 1,
        "scientificState": SCIENTIFIC_STATE,
        "basePublicMain": BASE_PUBLIC_MAIN,
        "phaseBFreezeIssue60CommentId": PHASE_B_FREEZE_COMMENT_ID,
        "solverExecutionAuthorized": False,
        "protectedResultsOpened": False,
        "productionAuthorized": False,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "representation": {"interpolatedQuantity": "direct-optical-depth", "targetAltitudeCoordinate": "identity-geometric-altitude-deg", "cscExtrapolationBelow5Deg": False},
        "counts": {"freshTrainingSpectra": 275, "inheritedFiveDegreeSeamSpectra": 25, "protectedSpectra": 176, "protectedJohnsonVComparisons": 528},
        "routing": {"lowerCandidateIntervalDeg": "[0.25,5)", "exactFiveAndAboveProvider": "authoritative-v3.2", "outsideSupport": "STELLAR_SPECTRAL_RUNTIME_OOD", "exactHorizonSupported": False},
        "failureSemantics": {"zeroOrUnderflowTransmission": "TERMINAL_REFUSAL", "epsilonSubstitutionAllowed": False, "sameIdentityRetryAllowed": False},
        "acceptance": {"maxAbsDeltaAvMag": 0.025, "rmsDeltaAvMag": 0.010, "globalAndEveryAltitudeIntervalMustPass": True, "postResultFloorBackSelectionAuthorized": False},
        "sourceV32Runtime": {"path": SOURCE_V32_RUNTIME_PATH, "sha256": SOURCE_V32_RUNTIME_SHA256},
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["ledgerSha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-ledger", action="store_true")
    args = parser.parse_args()
    if not args.emit_ledger:
        parser.error("review-only CLI requires --emit-ledger; no solver execution action exists")
    print(json.dumps(review_ledger(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
