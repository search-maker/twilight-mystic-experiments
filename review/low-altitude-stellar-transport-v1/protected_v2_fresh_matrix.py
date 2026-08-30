#!/usr/bin/env python3
"""Result-blind fresh protected matrix for LOWALT-STELLAR-STATE-0001.

The original protected matrix was opened under governance-ineligible provenance
and is diagnostic-only. This successor matrix is defined a priori as the exact
geometric center of every trilinear interpolation cell in the already-frozen
STATE-0001 lower candidate grid. It changes no training knot, representation,
solver geometry, spectrum, acceptance threshold, or support claim.

This module is review-only. It has no solver execution path and does not open
protected results.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PHASE_B_PATH = HERE / "low_altitude_phase_b.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b_for_fresh_protected_v2", PHASE_B_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load frozen Phase-B contract")
phase_b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase_b)

PROTOCOL_ID = "low-altitude-stellar-protected-v2-fresh-cell-centers"
SCIENTIFIC_STATE = phase_b.SCIENTIFIC_STATE
COORDINATOR_CORRECTION_ISSUE60_COMMENT_ID = 5468736357
INADMISSIBLE_V1_PROTECTED_STAGE_ID = "low-altitude-stellar-phase-b-protected-validation-v1"

# Immutable record of the previously opened, governance-ineligible matrix.
# These values are used only for collision refusal; no old result value is read.
INADMISSIBLE_V1_ALTITUDE_DEG = (
    0.34375, 0.59375, 0.84375, 1.1875, 1.6875, 2.1875,
    2.6875, 3.1875, 3.6875, 4.1875, 4.6875,
)
INADMISSIBLE_V1_ELEVATION_M = (187.5, 781.25, 1531.25, 2187.5)
INADMISSIBLE_V1_AOD550 = (0.06875, 0.1375, 0.2375, 0.3375)

# Fresh result-blind matrix: exact center of each adjacent interpolation-cell
# interval on each axis. There are 11 x 4 x 4 = 176 atmospheric cases.
PROTECTED_ALTITUDE_DEG = (
    0.375, 0.625, 0.875, 1.25, 1.75, 2.25,
    2.75, 3.25, 3.75, 4.25, 4.75,
)
PROTECTED_ELEVATION_M = (250.0, 875.0, 1625.0, 2250.0)
PROTECTED_AOD550 = (0.075, 0.15, 0.25, 0.35)
REPRESENTATIVE_LIBRARY_NUMBERS = phase_b.REPRESENTATIVE_LIBRARY_NUMBERS
EXPECTED_PROTECTED_SPECTRA = 176
EXPECTED_PROTECTED_COMPARISONS = 528
MAX_ABS_ERROR_MAG_LIMIT = phase_b.MAX_ABS_ERROR_MAG_LIMIT
RMS_ERROR_MAG_LIMIT = phase_b.RMS_ERROR_MAG_LIMIT


class FreshProtectedV2Refusal(RuntimeError):
    pass


def _midpoints(axis: tuple[float, ...]) -> tuple[float, ...]:
    # Derive cell centers from the canonical decimal spelling of the frozen
    # axes, rather than from binary-float addition. This keeps values such as
    # the midpoint of 0.10 and 0.20 canonically equal to the frozen 0.15 while
    # changing no scientific coordinate.
    two = Decimal("2")
    return tuple(
        float((Decimal(str(axis[i])) + Decimal(str(axis[i + 1]))) / two)
        for i in range(len(axis) - 1)
    )


def _coord(h: float, e: float, a: float) -> tuple[float, float, float]:
    return phase_b.coord(h, e, a)


def build_protected_cases() -> list[dict[str, float]]:
    return [
        phase_b.case(h, e, a)
        for h in PROTECTED_ALTITUDE_DEG
        for e in PROTECTED_ELEVATION_M
        for a in PROTECTED_AOD550
    ]


def inadmissible_v1_keys() -> set[tuple[float, float, float]]:
    return {
        _coord(h, e, a)
        for h in INADMISSIBLE_V1_ALTITUDE_DEG
        for e in INADMISSIBLE_V1_ELEVATION_M
        for a in INADMISSIBLE_V1_AOD550
    }


def fresh_keys() -> set[tuple[float, float, float]]:
    return {
        _coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"])
        for row in build_protected_cases()
    }


def validate_protocol() -> None:
    # Scientific rationale is entirely grid-derived and was fixed without any
    # protected residual: exact centers of every trilinear interpolation cell.
    if PROTECTED_ALTITUDE_DEG != _midpoints(tuple(float(x) for x in phase_b.LOWER_ASSET_ALTITUDE_DEG)):
        raise FreshProtectedV2Refusal("fresh protected altitude axis is not exact lower-grid cell centers")
    if PROTECTED_ELEVATION_M != _midpoints(tuple(float(x) for x in phase_b.ELEVATION_KNOTS_M)):
        raise FreshProtectedV2Refusal("fresh protected elevation axis is not exact cell centers")
    if PROTECTED_AOD550 != _midpoints(tuple(float(x) for x in phase_b.AOD_KNOTS)):
        raise FreshProtectedV2Refusal("fresh protected AOD axis is not exact cell centers")

    rows = build_protected_cases()
    keys = fresh_keys()
    if len(rows) != EXPECTED_PROTECTED_SPECTRA or len(keys) != EXPECTED_PROTECTED_SPECTRA:
        raise FreshProtectedV2Refusal("fresh protected spectrum count/uniqueness drift")
    if len(rows) * len(REPRESENTATIVE_LIBRARY_NUMBERS) != EXPECTED_PROTECTED_COMPARISONS:
        raise FreshProtectedV2Refusal("fresh protected Johnson-V comparison count drift")

    training = {
        _coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
        for r in phase_b.build_training_cases()
    }
    seam = {
        _coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
        for r in phase_b.build_seam_cases()
    }
    if keys & training or keys & seam:
        raise FreshProtectedV2Refusal("fresh protected matrix collides with training or exact-5 seam")
    if keys & inadmissible_v1_keys():
        raise FreshProtectedV2Refusal("fresh protected matrix reuses an opened v1 protected coordinate")

    # Axis-level disjointness provides a stronger simple proof than triple-only
    # disjointness: not one fresh coordinate value is reused on any dimension.
    if set(PROTECTED_ALTITUDE_DEG) & set(INADMISSIBLE_V1_ALTITUDE_DEG):
        raise FreshProtectedV2Refusal("fresh altitude axis reuses v1 protected value")
    if set(PROTECTED_ELEVATION_M) & set(INADMISSIBLE_V1_ELEVATION_M):
        raise FreshProtectedV2Refusal("fresh elevation axis reuses v1 protected value")
    if set(PROTECTED_AOD550) & set(INADMISSIBLE_V1_AOD550):
        raise FreshProtectedV2Refusal("fresh AOD axis reuses v1 protected value")

    if not all(0.25 < h < 5.0 for h in PROTECTED_ALTITUDE_DEG):
        raise FreshProtectedV2Refusal("fresh protected altitude escaped candidate interpolation interior")
    if MAX_ABS_ERROR_MAG_LIMIT != 0.025 or RMS_ERROR_MAG_LIMIT != 0.010:
        raise FreshProtectedV2Refusal("acceptance threshold drift")
    if REPRESENTATIVE_LIBRARY_NUMBERS != (1, 26, 45):
        raise FreshProtectedV2Refusal("representative Pickles identity drift")


def metric(values: list[float]) -> dict[str, Any]:
    if not values:
        raise FreshProtectedV2Refusal("empty protected metric set")
    max_abs = max(abs(float(x)) for x in values)
    rms = (sum(float(x) * float(x) for x in values) / len(values)) ** 0.5
    return {
        "comparisonCount": len(values),
        "maxAbsDeltaAvMag": max_abs,
        "rmsDeltaAvMag": rms,
        "passed": max_abs <= MAX_ABS_ERROR_MAG_LIMIT and rms <= RMS_ERROR_MAG_LIMIT,
    }


def evaluate_deltas(rows: list[dict[str, Any]]) -> dict[str, Any]:
    validate_protocol()
    expected = {
        (_coord(c["targetGeometricAltitudeDeg"], c["observerElevationM"], c["aod550"]), lib)
        for c in build_protected_cases()
        for lib in REPRESENTATIVE_LIBRARY_NUMBERS
    }
    observed: dict[tuple[tuple[float, float, float], int], float] = {}
    for row in rows:
        key = (
            _coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"]),
            int(row["libraryNumber"]),
        )
        if key in observed:
            raise FreshProtectedV2Refusal("duplicate fresh protected comparison")
        value = float(row["deltaAvMag"])
        if not (-float("inf") < value < float("inf")):
            raise FreshProtectedV2Refusal("non-finite fresh protected delta")
        observed[key] = value
    if set(observed) != expected or len(observed) != EXPECTED_PROTECTED_COMPARISONS:
        raise FreshProtectedV2Refusal("fresh protected comparison universe incomplete or drifted")

    overall = metric(list(observed.values()))
    per_altitude = {
        str(h): metric([v for (coord_and_lib, v) in observed.items() if coord_and_lib[0][0] == h])
        for h in PROTECTED_ALTITUDE_DEG
    }
    passed = overall["passed"] and all(item["passed"] for item in per_altitude.values())
    return {
        "scientificState": SCIENTIFIC_STATE,
        "protocolId": PROTOCOL_ID,
        "status": "PROTECTED_VALIDATION_PASS" if passed else "PROTECTED_VALIDATION_FAIL",
        "overall": overall,
        "byProtectedAltitudeDeg": per_altitude,
        "minimumSupportedGeometricAltitudeIfPassDeg": 0.25 if passed else None,
        "exactHorizonSupported": False,
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
    }


def review_ledger() -> dict[str, Any]:
    validate_protocol()
    payload = {
        "schemaVersion": 1,
        "protocolId": PROTOCOL_ID,
        "scientificState": SCIENTIFIC_STATE,
        "coordinatorCorrectionIssue60CommentId": COORDINATOR_CORRECTION_ISSUE60_COMMENT_ID,
        "inadmissibleV1ProtectedStageId": INADMISSIBLE_V1_PROTECTED_STAGE_ID,
        "matrixSelectionBasis": "exact-geometric-center-of-every-frozen-trilinear-interpolation-cell",
        "protectedResidualsUsedForMatrixSelection": False,
        "inadmissibleV1NumericalResultsUsed": False,
        "mysticState0077ResidualsUsed": False,
        "taylorOrJerusalemUsed": False,
        "protectedSolverExecutionAuthorized": False,
        "protectedResultsOpened": False,
        "trainingOrRepresentationChanged": False,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "axes": {
            "targetGeometricAltitudeDeg": list(PROTECTED_ALTITUDE_DEG),
            "observerElevationM": list(PROTECTED_ELEVATION_M),
            "aod550": list(PROTECTED_AOD550),
        },
        "counts": {
            "freshProtectedAtmosphericSpectra": EXPECTED_PROTECTED_SPECTRA,
            "freshProtectedJohnsonVComparisons": EXPECTED_PROTECTED_COMPARISONS,
        },
        "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
        "acceptance": {
            "maxAbsDeltaAvMag": MAX_ABS_ERROR_MAG_LIMIT,
            "rmsDeltaAvMag": RMS_ERROR_MAG_LIMIT,
            "globalAndEveryAltitudeCellCenterMustPass": True,
            "postResultFloorBackSelectionAuthorized": False,
        },
        "seamRequirement": {
            "exactFiveDegreeContentIdentityRequired": True,
            "exactFiveDegreeProvider": "authoritative-v3.2",
        },
        "claimBoundary": {
            "minimumSupportedGeometricAltitudeIfPassDeg": 0.25,
            "exactHorizonSupported": False,
            "productionAuthorized": False,
            "applicationSupportChanged": False,
        },
        "failureSemantics": {
            "zeroOrUnderflowDirectTransmission": "TERMINAL_REFUSAL",
            "positiveEpsilonSubstitutionAllowed": False,
            "sameIdentityRetryAllowed": False,
            "githubRerunAllowed": False,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["ledgerSha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-ledger", action="store_true")
    args = parser.parse_args()
    if not args.emit_ledger:
        parser.error("review-only CLI requires --emit-ledger; protected execution is intentionally absent")
    print(json.dumps(review_ledger(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
