#!/usr/bin/env python3
"""Result-blind successor protocol for near-horizon stellar direct transport.

LOWALT-STELLAR-STATE-0001 is immutable failed protected evidence.  This module
creates a wholly new scientific identity whose representation/grid selection is
based only on geometry, deterministic solver training, and a separate new
model-selection set.  It intentionally has no solver execution path and reads
no protected residual or error value from STATE-0001.

The candidate family is fixed a priori as nested dyadic refinement of the
already-defined physical domain.  Direct optical depth remains the interpolated
quantity in topocentric vacuum/geometric target altitude.  No csc(h)
extrapolation and no refraction are introduced.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, getcontext
import importlib.util
import json
from pathlib import Path
from typing import Any

getcontext().prec = 40

HERE = Path(__file__).resolve().parent
STATE1_PATH = HERE.parent / "low-altitude-stellar-transport-v1" / "low_altitude_phase_b.py"
SPEC = importlib.util.spec_from_file_location("low_alt_state1_domain_only", STATE1_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load inherited physical-domain constants")
state1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(state1)

SCIENTIFIC_STATE = "LOWALT-STELLAR-STATE-0002"
PROTOCOL_ID = "low-altitude-stellar-state-0002-nested-dyadic-refinement-v1"
PREDECESSOR_STATE = "LOWALT-STELLAR-STATE-0001"
PREDECESSOR_TERMINAL_ISSUE60_COMMENT_ID = 5469231719
SOURCE_V32_RUNTIME_PATH = state1.SOURCE_V32_RUNTIME_PATH
SOURCE_V32_RUNTIME_SHA256 = state1.SOURCE_V32_RUNTIME_SHA256
WAVELENGTH_NM = tuple(state1.WAVELENGTH_NM)
REPRESENTATIVE_LIBRARY_NUMBERS = tuple(state1.REPRESENTATIVE_LIBRARY_NUMBERS)

BASE_ALTITUDE_DEG = tuple(float(x) for x in state1.LOWER_ASSET_ALTITUDE_DEG)
BASE_ELEVATION_M = tuple(float(x) for x in state1.ELEVATION_KNOTS_M)
BASE_AOD550 = tuple(float(x) for x in state1.AOD_KNOTS)

# Nested candidates are frozen before any STATE-0002 solver result exists.
# AOD is deliberately not refined: for a fixed aerosol vertical profile the
# direct-beam aerosol optical depth scales affinely with its AOD normalization.
# The independent model-selection set stress-tests that assumption; if it does
# not meet the frozen gate, STATE-0002 terminates rather than adding AOD knots.
REFINEMENT_LEVELS = (
    {"id": "L1", "altitudeSubdivision": 2, "elevationSubdivision": 1, "aodSubdivision": 1},
    {"id": "L2", "altitudeSubdivision": 4, "elevationSubdivision": 2, "aodSubdivision": 1},
    {"id": "L3", "altitudeSubdivision": 8, "elevationSubdivision": 4, "aodSubdivision": 1},
)

# Model selection is deliberately separate from all dyadic training nodes.
MODEL_SELECTION_FRACTIONS = (Decimal(1) / Decimal(3), Decimal(2) / Decimal(3))
MODEL_SELECTION_MAX_ABS_MAG = 0.0125
MODEL_SELECTION_RMS_MAG = 0.005
EXPECTED_MODEL_SELECTION_SPECTRA = 1408
EXPECTED_MODEL_SELECTION_COMPARISONS = 4224

# Final protected values are frozen now, before model selection, and use
# non-dyadic/non-third rational offsets.  One point in every base cell along
# each axis gives 11 x 4 x 4 = 176 fresh protected atmospheres.
FINAL_PROTECTED_ALTITUDE_FRACTION = Decimal(2) / Decimal(7)
FINAL_PROTECTED_ELEVATION_FRACTION = Decimal(3) / Decimal(7)
FINAL_PROTECTED_AOD_FRACTION = Decimal(4) / Decimal(7)
EXPECTED_FINAL_PROTECTED_SPECTRA = 176
EXPECTED_FINAL_PROTECTED_COMPARISONS = 528
FINAL_MAX_ABS_MAG = 0.025
FINAL_RMS_MAG = 0.010

MIN_CANDIDATE_GEOMETRIC_ALTITUDE_DEG = 0.25
LOWER_PROVIDER_MAX_EXCLUSIVE_DEG = 5.0
EXACT_HORIZON_SUPPORTED = False

# Coordinate-only records of already opened predecessor matrices.  No residual,
# pass/fail-by-point, or observed-error value is present or consumed here.
OPENED_STATE1_V1_ALTITUDE = (
    0.34375, 0.59375, 0.84375, 1.1875, 1.6875, 2.1875,
    2.6875, 3.1875, 3.6875, 4.1875, 4.6875,
)
OPENED_STATE1_V1_ELEVATION = (187.5, 781.25, 1531.25, 2187.5)
OPENED_STATE1_V1_AOD = (0.06875, 0.1375, 0.2375, 0.3375)
OPENED_STATE1_V2_ALTITUDE = (
    0.375, 0.625, 0.875, 1.25, 1.75, 2.25,
    2.75, 3.25, 3.75, 4.25, 4.75,
)
OPENED_STATE1_V2_ELEVATION = (250.0, 875.0, 1625.0, 2250.0)
OPENED_STATE1_V2_AOD = (0.075, 0.15, 0.25, 0.35)


class State0002ProtocolRefusal(RuntimeError):
    pass


def _d(value: float | int | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _canonical(value: Decimal) -> float:
    # 12 decimal places are far below any scientific scale used here while
    # making cross-language JSON coordinates deterministic.
    return float(value.quantize(Decimal("0.000000000001")))


def _coord(h: float, e: float, a: float) -> tuple[float, float, float]:
    return (round(float(h), 12), round(float(e), 12), round(float(a), 12))


def _subdivide_axis(base: tuple[float, ...], factor: int) -> tuple[float, ...]:
    if factor < 1 or factor & (factor - 1):
        raise State0002ProtocolRefusal("refinement subdivision must be a positive power of two")
    values: list[float] = []
    for i in range(len(base) - 1):
        left, right = _d(base[i]), _d(base[i + 1])
        for j in range(factor):
            if i or j:
                pass
            value = left + (right - left) * Decimal(j) / Decimal(factor)
            if not values or _canonical(value) != values[-1]:
                values.append(_canonical(value))
    values.append(float(base[-1]))
    return tuple(values)


def _interior_axis(base: tuple[float, ...], fractions: tuple[Decimal, ...]) -> tuple[float, ...]:
    values: list[float] = []
    for left_raw, right_raw in zip(base[:-1], base[1:]):
        left, right = _d(left_raw), _d(right_raw)
        for fraction in fractions:
            if not Decimal(0) < fraction < Decimal(1):
                raise State0002ProtocolRefusal("interior fraction escaped (0,1)")
            values.append(_canonical(left + (right - left) * fraction))
    return tuple(values)


def _single_fraction_axis(base: tuple[float, ...], fraction: Decimal) -> tuple[float, ...]:
    return _interior_axis(base, (fraction,))


def training_axes(level_id: str) -> dict[str, tuple[float, ...]]:
    level = next((row for row in REFINEMENT_LEVELS if row["id"] == level_id), None)
    if level is None:
        raise State0002ProtocolRefusal(f"unknown refinement level: {level_id}")
    return {
        "targetGeometricAltitudeDeg": _subdivide_axis(BASE_ALTITUDE_DEG, int(level["altitudeSubdivision"])),
        "observerElevationM": _subdivide_axis(BASE_ELEVATION_M, int(level["elevationSubdivision"])),
        "aod550": _subdivide_axis(BASE_AOD550, int(level["aodSubdivision"])),
    }


def training_cases(level_id: str) -> list[dict[str, float]]:
    axes = training_axes(level_id)
    return [
        {
            "targetGeometricAltitudeDeg": h,
            "sourceZenithAngleDeg": 90.0 - h,
            "observerElevationM": e,
            "aod550": a,
        }
        for h in axes["targetGeometricAltitudeDeg"] if h < 5.0
        for e in axes["observerElevationM"]
        for a in axes["aod550"]
    ]


def model_selection_axes() -> dict[str, tuple[float, ...]]:
    return {
        "targetGeometricAltitudeDeg": _interior_axis(BASE_ALTITUDE_DEG, MODEL_SELECTION_FRACTIONS),
        "observerElevationM": _interior_axis(BASE_ELEVATION_M, MODEL_SELECTION_FRACTIONS),
        "aod550": _interior_axis(BASE_AOD550, MODEL_SELECTION_FRACTIONS),
    }


def model_selection_cases() -> list[dict[str, float]]:
    axes = model_selection_axes()
    return [
        {
            "targetGeometricAltitudeDeg": h,
            "sourceZenithAngleDeg": 90.0 - h,
            "observerElevationM": e,
            "aod550": a,
        }
        for h in axes["targetGeometricAltitudeDeg"]
        for e in axes["observerElevationM"]
        for a in axes["aod550"]
    ]


def final_protected_axes() -> dict[str, tuple[float, ...]]:
    return {
        "targetGeometricAltitudeDeg": _single_fraction_axis(BASE_ALTITUDE_DEG, FINAL_PROTECTED_ALTITUDE_FRACTION),
        "observerElevationM": _single_fraction_axis(BASE_ELEVATION_M, FINAL_PROTECTED_ELEVATION_FRACTION),
        "aod550": _single_fraction_axis(BASE_AOD550, FINAL_PROTECTED_AOD_FRACTION),
    }


def final_protected_cases() -> list[dict[str, float]]:
    axes = final_protected_axes()
    return [
        {
            "targetGeometricAltitudeDeg": h,
            "sourceZenithAngleDeg": 90.0 - h,
            "observerElevationM": e,
            "aod550": a,
        }
        for h in axes["targetGeometricAltitudeDeg"]
        for e in axes["observerElevationM"]
        for a in axes["aod550"]
    ]


def _keys(rows: list[dict[str, float]]) -> set[tuple[float, float, float]]:
    return {
        _coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"])
        for row in rows
    }


def _opened_keys(alt: tuple[float, ...], elev: tuple[float, ...], aod: tuple[float, ...]) -> set[tuple[float, float, float]]:
    return {_coord(h, e, a) for h in alt for e in elev for a in aod}


def expected_training_spectra(level_id: str) -> int:
    return len(training_cases(level_id))


def select_level_from_model_selection(metrics_by_level: dict[str, dict[str, Any]]) -> str | None:
    """Apply the frozen coarsest-passing rule to non-protected metrics only."""
    for level in REFINEMENT_LEVELS:
        level_id = str(level["id"])
        metrics = metrics_by_level.get(level_id)
        if metrics is None:
            return None
        if metrics.get("comparisonCount") != EXPECTED_MODEL_SELECTION_COMPARISONS:
            raise State0002ProtocolRefusal(f"{level_id} model-selection comparison count drift")
        overall = metrics.get("overall") or {}
        intervals = metrics.get("byBaseAltitudeInterval") or {}
        if (
            float(overall.get("maxAbsDeltaAvMag", float("inf"))) <= MODEL_SELECTION_MAX_ABS_MAG
            and float(overall.get("rmsDeltaAvMag", float("inf"))) <= MODEL_SELECTION_RMS_MAG
            and len(intervals) == len(BASE_ALTITUDE_DEG) - 1
            and all(
                float(row.get("maxAbsDeltaAvMag", float("inf"))) <= MODEL_SELECTION_MAX_ABS_MAG
                and float(row.get("rmsDeltaAvMag", float("inf"))) <= MODEL_SELECTION_RMS_MAG
                for row in intervals.values()
            )
        ):
            return level_id
    return None


def validate_protocol() -> None:
    if BASE_ALTITUDE_DEG[0] != 0.25 or BASE_ALTITUDE_DEG[-1] != 5.0:
        raise State0002ProtocolRefusal("physical altitude domain drift")
    if BASE_ELEVATION_M != (0.0, 500.0, 1250.0, 2000.0, 2500.0):
        raise State0002ProtocolRefusal("observer-elevation domain drift")
    if BASE_AOD550 != (0.05, 0.1, 0.2, 0.3, 0.4):
        raise State0002ProtocolRefusal("AOD domain drift")
    if SOURCE_V32_RUNTIME_SHA256 != "0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2":
        raise State0002ProtocolRefusal("authoritative v3.2 identity drift")
    if WAVELENGTH_NM != tuple(range(380, 781)):
        raise State0002ProtocolRefusal("spectral grid drift")
    if REFINEMENT_LEVELS != (
        {"id": "L1", "altitudeSubdivision": 2, "elevationSubdivision": 1, "aodSubdivision": 1},
        {"id": "L2", "altitudeSubdivision": 4, "elevationSubdivision": 2, "aodSubdivision": 1},
        {"id": "L3", "altitudeSubdivision": 8, "elevationSubdivision": 4, "aodSubdivision": 1},
    ):
        raise State0002ProtocolRefusal("refinement family drift")
    expected_training = {"L1": 550, "L2": 1980, "L3": 7480}
    for level_id, count in expected_training.items():
        rows = training_cases(level_id)
        if len(rows) != count or len(_keys(rows)) != count:
            raise State0002ProtocolRefusal(f"{level_id} training count/uniqueness drift")
        axes = training_axes(level_id)
        if axes["targetGeometricAltitudeDeg"][0] != 0.25 or axes["targetGeometricAltitudeDeg"][-1] != 5.0:
            raise State0002ProtocolRefusal(f"{level_id} altitude boundary drift")
        if any(h <= 0.0 for h in axes["targetGeometricAltitudeDeg"]):
            raise State0002ProtocolRefusal("horizon entered training grid")

    model_rows = model_selection_cases()
    protected_rows = final_protected_cases()
    if len(model_rows) != EXPECTED_MODEL_SELECTION_SPECTRA or len(_keys(model_rows)) != EXPECTED_MODEL_SELECTION_SPECTRA:
        raise State0002ProtocolRefusal("model-selection universe drift")
    if len(model_rows) * len(REPRESENTATIVE_LIBRARY_NUMBERS) != EXPECTED_MODEL_SELECTION_COMPARISONS:
        raise State0002ProtocolRefusal("model-selection photometry count drift")
    if len(protected_rows) != EXPECTED_FINAL_PROTECTED_SPECTRA or len(_keys(protected_rows)) != EXPECTED_FINAL_PROTECTED_SPECTRA:
        raise State0002ProtocolRefusal("final protected universe drift")
    if len(protected_rows) * len(REPRESENTATIVE_LIBRARY_NUMBERS) != EXPECTED_FINAL_PROTECTED_COMPARISONS:
        raise State0002ProtocolRefusal("final protected photometry count drift")

    model_keys = _keys(model_rows)
    protected_keys = _keys(protected_rows)
    if model_keys & protected_keys:
        raise State0002ProtocolRefusal("model-selection/final-protected collision")
    for level in REFINEMENT_LEVELS:
        train_keys = _keys(training_cases(str(level["id"])))
        if train_keys & model_keys or train_keys & protected_keys:
            raise State0002ProtocolRefusal("training collides with model-selection or final protected")

    opened_v1 = _opened_keys(OPENED_STATE1_V1_ALTITUDE, OPENED_STATE1_V1_ELEVATION, OPENED_STATE1_V1_AOD)
    opened_v2 = _opened_keys(OPENED_STATE1_V2_ALTITUDE, OPENED_STATE1_V2_ELEVATION, OPENED_STATE1_V2_AOD)
    if model_keys & opened_v1 or model_keys & opened_v2:
        raise State0002ProtocolRefusal("model-selection reuses an opened predecessor protected coordinate")
    if protected_keys & opened_v1 or protected_keys & opened_v2:
        raise State0002ProtocolRefusal("final protected reuses an opened predecessor protected coordinate")

    # Stronger final-holdout proof: not even one axis value is reused from the
    # two opened predecessor protected matrices.
    fp = final_protected_axes()
    if set(fp["targetGeometricAltitudeDeg"]) & (set(OPENED_STATE1_V1_ALTITUDE) | set(OPENED_STATE1_V2_ALTITUDE)):
        raise State0002ProtocolRefusal("final protected altitude axis reuses opened predecessor value")
    if set(fp["observerElevationM"]) & (set(OPENED_STATE1_V1_ELEVATION) | set(OPENED_STATE1_V2_ELEVATION)):
        raise State0002ProtocolRefusal("final protected elevation axis reuses opened predecessor value")
    if set(fp["aod550"]) & (set(OPENED_STATE1_V1_AOD) | set(OPENED_STATE1_V2_AOD)):
        raise State0002ProtocolRefusal("final protected AOD axis reuses opened predecessor value")

    if MODEL_SELECTION_MAX_ABS_MAG != 0.0125 or MODEL_SELECTION_RMS_MAG != 0.005:
        raise State0002ProtocolRefusal("internal model-selection gate drift")
    if FINAL_MAX_ABS_MAG != 0.025 or FINAL_RMS_MAG != 0.010:
        raise State0002ProtocolRefusal("final protected gate drift")
    if EXACT_HORIZON_SUPPORTED is not False:
        raise State0002ProtocolRefusal("horizon support drift")


def ledger() -> dict[str, Any]:
    validate_protocol()
    return {
        "schemaVersion": 1,
        "scientificState": SCIENTIFIC_STATE,
        "protocolId": PROTOCOL_ID,
        "predecessorState": PREDECESSOR_STATE,
        "predecessorTerminalIssue60CommentId": PREDECESSOR_TERMINAL_ISSUE60_COMMENT_ID,
        "predecessorProtectedResidualsUsedForDesign": False,
        "predecessorProtectedPerAltitudePassPatternUsedForDesign": False,
        "mysticState0077ResidualsUsedForDesign": False,
        "taylorOrJerusalemUsed": False,
        "desiredFirstSeeingTimeUsed": False,
        "physicalBasis": {
            "solver": "sdisort",
            "geometry": "pseudo-spherical",
            "targetAltitudeBasis": "topocentric-vacuum-geometric",
            "interpolatedQuantity": "direct-optical-depth",
            "targetAltitudeCoordinate": "identity-geometric-altitude-deg",
            "refractionAppliedInRadiativeTransfer": False,
            "cscExtrapolationBelow5Deg": False,
            "wavelengthNm": [380, 780, 1],
            "aodRefinementRationale": "direct-beam aerosol optical depth is affine in fixed-profile AOD normalization; separate model-selection stress test is mandatory",
        },
        "domain": {
            "candidateMinGeometricAltitudeDeg": MIN_CANDIDATE_GEOMETRIC_ALTITUDE_DEG,
            "lowerProviderMaxExclusiveDeg": LOWER_PROVIDER_MAX_EXCLUSIVE_DEG,
            "observerElevationM": list(BASE_ELEVATION_M),
            "aod550": list(BASE_AOD550),
            "exactHorizonSupported": False,
            "exactFiveAndAboveProvider": "authoritative-v3.2",
            "sourceV32RuntimeSha256": SOURCE_V32_RUNTIME_SHA256,
        },
        "nestedTrainingLevels": [
            {
                **level,
                "trainingSpectrumCount": expected_training_spectra(str(level["id"])),
                "fiveDegreeSeamRegenerated": False,
            }
            for level in REFINEMENT_LEVELS
        ],
        "modelSelection": {
            "fractionsWithinEveryBaseInterval": ["1/3", "2/3"],
            "atmosphericSpectrumCount": EXPECTED_MODEL_SELECTION_SPECTRA,
            "johnsonVComparisonCount": EXPECTED_MODEL_SELECTION_COMPARISONS,
            "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
            "maxAbsDeltaAvMagLimit": MODEL_SELECTION_MAX_ABS_MAG,
            "rmsDeltaAvMagLimit": MODEL_SELECTION_RMS_MAG,
            "globalAndEveryBaseAltitudeIntervalMustPass": True,
            "selectionRule": "first/coarsest nested level L1->L2->L3 satisfying the complete frozen model-selection gate",
            "ifNoLevelPasses": "TERMINATE_STATE_0002_WITHOUT_OPENING_FINAL_PROTECTED",
            "protectedResultsUsed": False,
        },
        "finalProtected": {
            "selectionFractions": {"altitude": "2/7", "elevation": "3/7", "aod550": "4/7"},
            "axes": {key: list(values) for key, values in final_protected_axes().items()},
            "atmosphericSpectrumCount": EXPECTED_FINAL_PROTECTED_SPECTRA,
            "johnsonVComparisonCount": EXPECTED_FINAL_PROTECTED_COMPARISONS,
            "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
            "maxAbsDeltaAvMagLimit": FINAL_MAX_ABS_MAG,
            "rmsDeltaAvMagLimit": FINAL_RMS_MAG,
            "globalAndEveryProtectedAltitudeMustPass": True,
            "opened": False,
        },
        "failureSemantics": {
            "zeroOrUnderflowDirectTransmission": "TERMINAL_NUMERICAL_REFUSAL",
            "positiveEpsilonSubstitutionAllowed": False,
            "postProtectedRetuningAllowed": False,
            "postProtectedFloorBackSelectionAllowed": False,
            "sameProtectedIdentityRetryAllowed": False,
            "githubProtectedRerunAllowed": False,
        },
        "claimBoundary": {
            "minimumSupportedGeometricAltitudeIfFinalProtectedPassDeg": 0.25,
            "minimumSupportedGeometricAltitudeBeforeFinalProtectedPassDeg": 5.0,
            "exactHorizonSupported": False,
            "applicationSupportChanged": False,
            "productionAuthorized": False,
        },
        "solverExecutionAuthorizedByThisModule": False,
        "modelSelectionOpenedByThisModule": False,
        "finalProtectedOpenedByThisModule": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-ledger", action="store_true")
    args = parser.parse_args()
    if not args.emit_ledger:
        parser.error("review-only protocol supports only --emit-ledger")
    print(json.dumps(ledger(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
