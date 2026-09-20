#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

STAGE = "koomen-mono550-cv-confirm-v1"
EXECUTION_KEY = "koomen-mono550-cv-confirm-v1:scientific:58"
ISSUE = 873
ROW = 27
BASES = [1621000000, 1622000000, 1623000000, 1624000000, 1625000000, 1626000000]
SEED_OFFSET = 996
PHOTONS = 5_000_000
MAX_CALLS = 72
MAX_HISTORIES = 360_000_000
ORD56_HEAD = "058284d17a632c1c76dbbf7a58229a186445cb87"
EXPECTED_ORD56_RUNNER_BLOB = "f79e7606509285bc3b0eaa42c0aaa8b973610574"
DIRECTIONS = [
    {"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "label": "center", "role": "center"},
    {"directionIndex": 14, "thetaDeg": 0.15, "relativeAzimuthDeg": 22.5, "label": "inner_015_0225", "role": "target"},
    {"directionIndex": 18, "thetaDeg": 0.75, "relativeAzimuthDeg": 292.5, "label": "outer_075_2925", "role": "target"},
]


class Failure(RuntimeError):
    pass


def load_frozen_runner(path: Path):
    spec = importlib.util.spec_from_file_location("ordinal56_frozen_runner", path)
    if spec is None or spec.loader is None:
        raise Failure(f"cannot import frozen ordinal56 runner {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(path: Path):
    m = json.loads(path.read_text())
    if m.get("stageId") != STAGE or m.get("executionKey") != EXECUTION_KEY:
        raise Failure("wrong ordinal58 manifest identity")
    if m.get("issue") != ISSUE or m.get("row") != ROW:
        raise Failure("issue/row changed")
    if m.get("directions") != DIRECTIONS or m.get("cases") != ["baseline", "profile"]:
        raise Failure("independent geometry/case universe changed")
    if m.get("arms") != ["alis550", "mono550"]:
        raise Failure("arm universe changed")
    if m.get("replicateSeedBases") != BASES or m.get("seedOffset") != SEED_OFFSET:
        raise Failure("fresh seed universe changed")
    if m.get("photonsPerDirectionPerCaseArm") != PHOTONS:
        raise Failure("5M photon regime changed")
    if m.get("maximumSolverCalls") != MAX_CALLS or m.get("maximumConfiguredPhotonHistories") != MAX_HISTORIES:
        raise Failure("maximum budget changed")

    g = m.get("geometrySelection", {})
    if g.get("ordinal50DirectionalValuesUsed") is not False:
        raise Failure("ordinal50 values entered geometry selection")
    for key in ("ordinal53CardinalTargetsReused", "ordinal54HoldoutTargetsReused", "ordinal56Or57TargetCoordinatesReused"):
        if g.get(key) is not False:
            raise Failure(f"fresh-geometry prohibition changed: {key}")
    if g.get("directionIndicesAreCompatibilityIdentifiersOnly") is not True:
        raise Failure("direction-index compatibility declaration changed")

    method = m.get("method", {})
    if method.get("common") != ["mc_spherical 1D", "mc_vroom on", "mc_escape on"]:
        raise Failure("common estimator changed")
    if method.get("alis550") != {"wavelengthNm": [380, 780], "mcSpectralIsNm": 550.0}:
        raise Failure("ALIS550 arm changed")
    if method.get("mono550") != {"wavelengthNm": [550, 550], "mcSpectralIs": False}:
        raise Failure("MONO550 arm changed")
    if method.get("controlVariateFormula") != "D_CV=(D_CIE-D_A)+D_M":
        raise Failure("control-variate formula changed")

    fr = m.get("ordinal56FrozenRunner", {})
    if fr.get("headSha") != ORD56_HEAD or fr.get("blobSha") != EXPECTED_ORD56_RUNNER_BLOB:
        raise Failure("frozen ordinal56 runner binding changed")

    a = m.get("analysis", {})
    if a.get("primaryMethodConsistencyToleranceMag") != 0.03 or a.get("precisionTargetSeMag") != 0.03:
        raise Failure("analysis threshold changed")
    if a.get("absoluteEquivalenceQuantityCount") != 6 or a.get("directionalDeltaEquivalenceQuantityCount") != 4 or a.get("controlVariateQuantityCount") != 4:
        raise Failure("analysis quantity universe changed")
    if a.get("controlVariateFormula") != "D_CV=(D_CIE-D_A)+D_M":
        raise Failure("analysis formula changed")
    for key in ("fitTaylor", "fitAcceptance", "fitFov", "fitSpectralResponse", "fitOffset", "fitAtmosphere", "fitAod", "fitProfile", "fitAnyParameter"):
        if a.get(key) is not False:
            raise Failure(f"fitting prohibition changed: {key}")

    b = m.get("boundaries", {})
    for key in (
        "TaylorResidualUsed", "ordinal54Salvage", "importanceWavelengthRetuned",
        "historicalAcceptanceInvented", "exactHistoricalSpectralResponseClaimed",
        "physicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized",
        "full81DirectionGridExecuted", "productionAuthorized", "adaptivePhotonExtensionAuthorized",
    ):
        if b.get(key) is not False:
            raise Failure(f"boundary changed: {key}")
    return m


def main():
    frozen_path = Path(os.environ.get("ORD56_FROZEN_RUNNER", "frozen-source/ordinal56_run_sentinel.py"))
    module = load_frozen_runner(frozen_path)
    module.STAGE = STAGE
    module.EXECUTION_KEY = EXECUTION_KEY
    module.BASES = list(BASES)
    module.SEED_OFFSET = SEED_OFFSET
    module.PHOTONS = PHOTONS
    module.DIRECTIONS = list(DIRECTIONS)
    module.load_manifest = validate_manifest
    module.main()


if __name__ == "__main__":
    main()
