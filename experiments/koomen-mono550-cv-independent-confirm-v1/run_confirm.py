#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

STAGE = "koomen-mono550-cv-independent-confirm-v1"
EXECUTION_KEY = "koomen-mono550-cv-independent-confirm-v1:scientific:58"
ISSUE = 874
ROW = 27
BASES = [1621000000, 1622000000, 1623000000, 1624000000, 1625000000, 1626000000]
SEED_OFFSET = 996
PHOTONS = 5_000_000
MAX_CALLS = 144
MAX_HISTORIES = 720_000_000
ORD57_RUN = 33586620132
ORD57_HEAD = "41c6eef48703944629099c29931de85dab3cf875"
ORD57_ARTIFACT = 9830445231
ORD57_DIGEST = "sha256:cc3004e0484f9d2c842ba04441bf0e8283e96c3844a82da9d873b1c4760ebabe"
ORD57_RESULT_COMMENT = 5503872374
EXPECTED_ORD56_RUNNER_BLOB = "f79e7606509285bc3b0eaa42c0aaa8b973610574"
DIRECTIONS = [
    {"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "label": "center", "role": "center"},
    {"directionIndex": 101, "thetaDeg": 0.15, "relativeAzimuthDeg": 22.5, "label": "ring015_phi0225", "role": "target"},
    {"directionIndex": 102, "thetaDeg": 0.30, "relativeAzimuthDeg": 90.0, "label": "ring030_phi0900", "role": "target"},
    {"directionIndex": 103, "thetaDeg": 0.45, "relativeAzimuthDeg": 157.5, "label": "ring045_phi1575", "role": "target"},
    {"directionIndex": 104, "thetaDeg": 0.60, "relativeAzimuthDeg": 225.0, "label": "ring060_phi2250", "role": "target"},
    {"directionIndex": 105, "thetaDeg": 0.75, "relativeAzimuthDeg": 292.5, "label": "ring075_phi2925", "role": "target"},
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
        raise Failure("geometry/case universe changed")
    if m.get("arms") != ["alis550", "mono550"]:
        raise Failure("arm universe changed")
    if m.get("replicateSeedBases") != BASES or m.get("seedOffset") != SEED_OFFSET:
        raise Failure("fresh seed universe changed")
    if m.get("photonsPerDirectionPerCaseArm") != PHOTONS:
        raise Failure("photon level changed")
    if m.get("maximumSolverCalls") != MAX_CALLS or m.get("maximumConfiguredPhotonHistories") != MAX_HISTORIES:
        raise Failure("maximum budget changed")

    g = m.get("geometrySelectionRule", {})
    if g.get("ringThetaDeg") != [0.15, 0.30, 0.45, 0.60, 0.75]:
        raise Failure("ring lattice changed")
    if g.get("azimuthSpacingDeg") != 22.5 or g.get("formula") != "phi_k=22.5+67.5*(k-1), k=1..5":
        raise Failure("geometry-only selection rule changed")
    if g.get("selectedPhiDeg") != [22.5, 90.0, 157.5, 225.0, 292.5]:
        raise Failure("selected azimuths changed")

    p = m.get("predecessor", {})
    if p.get("issue") != 870 or p.get("pr") != 872 or p.get("runId") != ORD57_RUN or p.get("headSha") != ORD57_HEAD:
        raise Failure("ordinal57 predecessor identity changed")
    if p.get("analysisArtifactId") != ORD57_ARTIFACT or p.get("analysisArtifactDigest") != ORD57_DIGEST:
        raise Failure("ordinal57 artifact provenance changed")
    if p.get("resultCommentId") != ORD57_RESULT_COMMENT:
        raise Failure("ordinal57 result comment changed")
    if p.get("classification") != "MONO550_CV_5M_SCALE_EQUIVALENT_AND_PRECISION_ELIGIBLE":
        raise Failure("ordinal57 classification changed")
    if p.get("equivalenceFailures") != 0 or p.get("equivalenceQuantityCount") != 10 or p.get("precisionFailures") != 0 or p.get("precisionQuantityCount") != 4:
        raise Failure("ordinal57 gate counts changed")

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
    if fr.get("headSha") != "058284d17a632c1c76dbbf7a58229a186445cb87" or fr.get("blobSha") != EXPECTED_ORD56_RUNNER_BLOB:
        raise Failure("frozen ordinal56 runner binding changed")

    a = m.get("analysis", {})
    if a.get("primaryMethodConsistencyToleranceMag") != 0.03 or a.get("precisionTargetSeMag") != 0.03:
        raise Failure("analysis threshold changed")
    if a.get("absoluteEquivalenceQuantityCount") != 12 or a.get("directionalDeltaEquivalenceQuantityCount") != 10 or a.get("equivalenceQuantityCount") != 22 or a.get("controlVariateQuantityCount") != 10:
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
