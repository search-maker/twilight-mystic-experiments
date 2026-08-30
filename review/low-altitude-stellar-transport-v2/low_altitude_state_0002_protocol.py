#!/usr/bin/env python3
"""Result-blind preregistration for LOWALT-STELLAR-STATE-0002.

This successor exists because LOWALT-STELLAR-STATE-0001 reached an admissible
terminal protected FAIL. The numerical protected residuals from that state are
opened evidence and are explicitly forbidden inputs to this design.

STATE-0002 therefore fixes one a-priori representation from spherical-path and
atmospheric-scale numerical considerations only: a dense direct-optical-depth
LUT on geometric target altitude, observer elevation, and AOD. It does not use
csc(h) extrapolation and does not introduce a fitted Chapman formula.
"""
from __future__ import annotations

import json
import math
from typing import Any

SCIENTIFIC_STATE = "LOWALT-STELLAR-STATE-0002"
PREDECESSOR_STATE = "LOWALT-STELLAR-STATE-0001"
PREDECESSOR_TERMINAL_CLASSIFICATION_COMMENT_ID = 5469231719
SOURCE_V32_RUNTIME_PATH = "generated/level-b-stellar-v32/stellar-transport-v32-zenith-lut.json"
SOURCE_V32_RUNTIME_SHA256 = "0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2"

WAVELENGTH_NM = tuple(range(380, 781))
TRAINING_ALTITUDE_DEG = tuple(round(0.25 + 0.125 * i, 6) for i in range(38))
LOWER_ASSET_ALTITUDE_DEG = (*TRAINING_ALTITUDE_DEG, 5.0)
ELEVATION_KNOTS_M = tuple(float(x) for x in range(0, 2501, 250))
AOD_KNOTS = (0.05, 0.10, 0.20, 0.30, 0.40)

# Wholly fresh protected axes: none of these altitude/elevation/AOD coordinates
# is copied from either opened STATE-0001 protected matrix. Exact full cases are
# disjoint from training and the inherited 5-deg seam.
PROTECTED_ALTITUDE_DEG = (
    0.3125, 0.6875, 1.0625, 1.4375, 1.8125, 2.3125,
    2.8125, 3.3125, 3.8125, 4.3125, 4.8125,
)
PROTECTED_ELEVATION_M = (125.0, 625.0, 1125.0, 1875.0, 2375.0)
PROTECTED_AOD550 = (0.0625, 0.125, 0.225, 0.325)
REPRESENTATIVE_LIBRARY_NUMBERS = (1, 26, 45)

EXPECTED_TRAINING_SPECTRA = len(TRAINING_ALTITUDE_DEG) * len(ELEVATION_KNOTS_M) * len(AOD_KNOTS)
EXPECTED_SEAM_SPECTRA = len(ELEVATION_KNOTS_M) * len(AOD_KNOTS)
EXPECTED_PROTECTED_SPECTRA = len(PROTECTED_ALTITUDE_DEG) * len(PROTECTED_ELEVATION_M) * len(PROTECTED_AOD550)
EXPECTED_PROTECTED_COMPARISONS = EXPECTED_PROTECTED_SPECTRA * len(REPRESENTATIVE_LIBRARY_NUMBERS)
MAX_ABS_ERROR_MAG_LIMIT = 0.025
RMS_ERROR_MAG_LIMIT = 0.010
PREREGISTERED_MIN_CANDIDATE_GEOMETRIC_ALTITUDE_DEG = 0.25
EXACT_HORIZON_SUPPORTED = False

# A-priori mesh rationale. 8 km is a conventional order-of-magnitude lower-
# atmosphere density scale height; 6371 km is the mean Earth radius. The
# spherical near-horizon angular scale sqrt(2H/R) is ~2.87 deg. The 0.125-deg
# altitude spacing is therefore <5% of that characteristic scale, while the
# 250-m elevation spacing is 3.125% of an 8-km scale height. These values are
# protocol constants, not fitted outputs.
REFERENCE_EARTH_RADIUS_KM = 6371.0
REFERENCE_ATMOSPHERIC_SCALE_HEIGHT_KM = 8.0
CHARACTERISTIC_SPHERICAL_ANGLE_DEG = math.degrees(
    math.sqrt(2.0 * REFERENCE_ATMOSPHERIC_SCALE_HEIGHT_KM / REFERENCE_EARTH_RADIUS_KM)
)
MAX_ALTITUDE_STEP_DEG = 0.125
MAX_ELEVATION_STEP_M = 250.0

OPENED_STATE_0001_PROTECTED_ALTITUDES = {
    0.34375, 0.59375, 0.84375, 1.1875, 1.6875, 2.1875,
    2.6875, 3.1875, 3.6875, 4.1875, 4.6875,
    0.375, 0.625, 0.875, 1.25, 1.75, 2.25, 2.75, 3.25,
    3.75, 4.25, 4.75,
}
OPENED_STATE_0001_PROTECTED_ELEVATIONS = {
    187.5, 781.25, 1531.25, 2187.5, 250.0, 875.0, 1625.0, 2250.0,
}
OPENED_STATE_0001_PROTECTED_AODS = {
    0.06875, 0.1375, 0.2375, 0.3375, 0.075, 0.15, 0.25, 0.35,
}


class ProtocolRefusal(RuntimeError):
    pass


def coord(h: float, e: float, a: float) -> tuple[float, float, float]:
    return round(float(h), 9), round(float(e), 9), round(float(a), 9)


def _cases(altitudes, elevations, aods):
    return [coord(h, e, a) for h in altitudes for e in elevations for a in aods]


def validate_protocol() -> dict[str, Any]:
    if TRAINING_ALTITUDE_DEG[0] != 0.25 or TRAINING_ALTITUDE_DEG[-1] != 4.875:
        raise ProtocolRefusal("training altitude endpoints drift")
    if any(abs((b - a) - 0.125) > 1e-12 for a, b in zip(TRAINING_ALTITUDE_DEG, TRAINING_ALTITUDE_DEG[1:])):
        raise ProtocolRefusal("training altitude mesh must be exact 0.125-deg spacing")
    if ELEVATION_KNOTS_M != tuple(float(x) for x in range(0, 2501, 250)):
        raise ProtocolRefusal("elevation mesh drift")
    if AOD_KNOTS != (0.05, 0.10, 0.20, 0.30, 0.40):
        raise ProtocolRefusal("AOD mesh drift")
    if EXPECTED_TRAINING_SPECTRA != 2090 or EXPECTED_SEAM_SPECTRA != 55:
        raise ProtocolRefusal("training/seam count drift")
    if EXPECTED_PROTECTED_SPECTRA != 220 or EXPECTED_PROTECTED_COMPARISONS != 660:
        raise ProtocolRefusal("protected count drift")
    if MAX_ABS_ERROR_MAG_LIMIT != 0.025 or RMS_ERROR_MAG_LIMIT != 0.010:
        raise ProtocolRefusal("acceptance gate drift")
    if PREREGISTERED_MIN_CANDIDATE_GEOMETRIC_ALTITUDE_DEG != 0.25 or EXACT_HORIZON_SUPPORTED is not False:
        raise ProtocolRefusal("support boundary drift")
    if MAX_ALTITUDE_STEP_DEG / CHARACTERISTIC_SPHERICAL_ANGLE_DEG >= 0.05:
        raise ProtocolRefusal("a-priori altitude mesh no longer <5% of spherical characteristic scale")
    if MAX_ELEVATION_STEP_M / (REFERENCE_ATMOSPHERIC_SCALE_HEIGHT_KM * 1000.0) > 0.03125 + 1e-15:
        raise ProtocolRefusal("a-priori elevation mesh no longer <=3.125% of reference scale height")

    training = set(_cases(TRAINING_ALTITUDE_DEG, ELEVATION_KNOTS_M, AOD_KNOTS))
    seam = set(_cases((5.0,), ELEVATION_KNOTS_M, AOD_KNOTS))
    protected = set(_cases(PROTECTED_ALTITUDE_DEG, PROTECTED_ELEVATION_M, PROTECTED_AOD550))
    if len(training) != EXPECTED_TRAINING_SPECTRA or len(seam) != EXPECTED_SEAM_SPECTRA or len(protected) != EXPECTED_PROTECTED_SPECTRA:
        raise ProtocolRefusal("duplicate protocol coordinates")
    if training & seam or training & protected or seam & protected:
        raise ProtocolRefusal("training/seam/protected collision")
    if set(PROTECTED_ALTITUDE_DEG) & OPENED_STATE_0001_PROTECTED_ALTITUDES:
        raise ProtocolRefusal("fresh protected altitude axis reuses opened predecessor altitude")
    if set(PROTECTED_ELEVATION_M) & OPENED_STATE_0001_PROTECTED_ELEVATIONS:
        raise ProtocolRefusal("fresh protected elevation axis reuses opened predecessor elevation")
    if set(PROTECTED_AOD550) & OPENED_STATE_0001_PROTECTED_AODS:
        raise ProtocolRefusal("fresh protected AOD axis reuses opened predecessor AOD")
    if not all(0.25 < h < 5.0 for h in PROTECTED_ALTITUDE_DEG):
        raise ProtocolRefusal("protected altitude escaped lower domain")

    return {
        "scientificState": SCIENTIFIC_STATE,
        "predecessorState": PREDECESSOR_STATE,
        "predecessorTerminalClassificationCommentId": PREDECESSOR_TERMINAL_CLASSIFICATION_COMMENT_ID,
        "representation": {
            "quantity": "direct-optical-depth",
            "targetAltitudeBasis": "topocentric-vacuum-geometric",
            "targetAltitudeCoordinate": "identity-geometric-altitude-deg",
            "targetAltitudeInterpolation": "linear",
            "observerElevationInterpolation": "linear",
            "aod550Interpolation": "linear",
            "cscExtrapolationBelow5Deg": False,
            "fittedChapmanFormula": False,
            "pseudoSphericalReferenceSolver": "sdisort",
            "sourceZenithAngleRelation": "sza=90deg-targetGeometricAltitudeDeg",
            "refractionAppliedInRadiativeTransfer": False,
        },
        "meshRationale": {
            "referenceEarthRadiusKm": REFERENCE_EARTH_RADIUS_KM,
            "referenceAtmosphericScaleHeightKm": REFERENCE_ATMOSPHERIC_SCALE_HEIGHT_KM,
            "characteristicSphericalAngleDeg": CHARACTERISTIC_SPHERICAL_ANGLE_DEG,
            "altitudeStepDeg": MAX_ALTITUDE_STEP_DEG,
            "altitudeStepFractionOfCharacteristicScale": MAX_ALTITUDE_STEP_DEG / CHARACTERISTIC_SPHERICAL_ANGLE_DEG,
            "elevationStepM": MAX_ELEVATION_STEP_M,
            "elevationStepFractionOfReferenceScaleHeight": MAX_ELEVATION_STEP_M / (REFERENCE_ATMOSPHERIC_SCALE_HEIGHT_KM * 1000.0),
        },
        "trainingAltitudeDeg": list(TRAINING_ALTITUDE_DEG),
        "elevationKnotsM": list(ELEVATION_KNOTS_M),
        "aodKnots": list(AOD_KNOTS),
        "trainingSpectrumCount": EXPECTED_TRAINING_SPECTRA,
        "inheritedFiveDegreeSeamSpectrumCount": EXPECTED_SEAM_SPECTRA,
        "protectedAltitudeDeg": list(PROTECTED_ALTITUDE_DEG),
        "protectedElevationM": list(PROTECTED_ELEVATION_M),
        "protectedAod550": list(PROTECTED_AOD550),
        "protectedAtmosphericSpectrumCount": EXPECTED_PROTECTED_SPECTRA,
        "protectedJohnsonVComparisonCount": EXPECTED_PROTECTED_COMPARISONS,
        "representativeLibraryNumbers": list(REPRESENTATIVE_LIBRARY_NUMBERS),
        "maxAbsDeltaAvMagLimit": MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": RMS_ERROR_MAG_LIMIT,
        "globalAndEveryAltitudeProtectedSliceMustPass": True,
        "candidateMinGeometricAltitudeDeg": PREREGISTERED_MIN_CANDIDATE_GEOMETRIC_ALTITUDE_DEG,
        "exactHorizonSupported": EXACT_HORIZON_SUPPORTED,
        "fiveDegreeSeamContentIdentityRequired": True,
        "zeroOrUnderflowTransmissionSemantics": "NUMERICALLY_UNRESOLVED_FAIL_CLOSED",
        "positiveEpsilonSubstitutionAllowed": False,
        "sameIdentityRetryAllowed": False,
        "githubRerunAllowed": False,
        "postProtectedResultFloorSelectionAllowed": False,
        "postProtectedResultRetuningAllowed": False,
        "predecessorProtectedResidualsMayInformDesign": False,
        "taylorJerusalemOrHalachicTimesMayInformDesign": False,
        "avpsAerosolProfileScienceMixedIntoThisState": False,
        "applicationSupportChanged": False,
        "productionAuthorized": False,
        "protectedResultsOpened": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate_protocol(), indent=2, sort_keys=True))
