#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import os
from pathlib import Path

STAGE = "koomen-mono550-cv-scale-5m-v1"
EXECUTION_KEY = "koomen-mono550-cv-scale-5m-v1:scientific:57"
ISSUE = 870
ROW = 27
BASES = [1611000000, 1612000000, 1613000000, 1614000000, 1615000000, 1616000000]
SEED_OFFSET = 996
PHOTONS = 5_000_000
MAX_CALLS = 72
MAX_HISTORIES = 360_000_000
ORD56_RUN = 33585842755
ORD56_HEAD = "058284d17a632c1c76dbbf7a58229a186445cb87"
ORD56_ARTIFACT = 9830086548
ORD56_DIGEST = "sha256:7fc10298ad3df738c8b2914d195dd92802f2a59d213e5271fdb5faeffb493bf4"
ORD56_RESULT_COMMENT = 5503742872
ORD56_N = 1_000_000
ORD56_WORST_SE = 0.0642911565
TARGET_SE = 0.030
EXPECTED_ORD56_RUNNER_BLOB = "f79e7606509285bc3b0eaa42c0aaa8b973610574"
DIRECTIONS = [
    {"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "label": "center", "role": "center"},
    {"directionIndex": 14, "thetaDeg": 0.375, "relativeAzimuthDeg": 180.0, "label": "mid_180", "role": "target"},
    {"directionIndex": 18, "thetaDeg": 0.75, "relativeAzimuthDeg": 315.0, "label": "edge_315", "role": "target"},
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
        raise Failure("wrong ordinal57 manifest identity")
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

    p = m.get("planning", {})
    if p.get("ordinal56RunId") != ORD56_RUN or p.get("ordinal56HeadSha") != ORD56_HEAD:
        raise Failure("ordinal56 run provenance changed")
    if p.get("ordinal56AnalysisArtifactId") != ORD56_ARTIFACT or p.get("ordinal56AnalysisArtifactDigest") != ORD56_DIGEST:
        raise Failure("ordinal56 analysis artifact provenance changed")
    if p.get("ordinal56ResultCommentId") != ORD56_RESULT_COMMENT:
        raise Failure("ordinal56 result-comment provenance changed")
    if p.get("ordinal56Photons") != ORD56_N or p.get("ordinal56WorstCvSeMag") != ORD56_WORST_SE or p.get("precisionTargetSeMag") != TARGET_SE:
        raise Failure("planning inputs changed")
    required = ORD56_N * (ORD56_WORST_SE / TARGET_SE) ** 2
    chosen = int(math.ceil(required / 1_000_000.0) * 1_000_000)
    if chosen != PHOTONS or p.get("chosenPhotons") != PHOTONS:
        raise Failure("frozen whole-million planning rule no longer yields 5M")
    if abs(float(p.get("requiredPhotons")) - required) > 1.0:
        raise Failure("recorded required-photon calculation changed materially")
    predicted = ORD56_WORST_SE * math.sqrt(ORD56_N / PHOTONS)
    if abs(float(p.get("predictedWorstSeMagAtChosenN")) - predicted) > 1e-9:
        raise Failure("recorded planning prediction changed")

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
    if a.get("primaryMethodConsistencyToleranceMag") != TARGET_SE or a.get("precisionTargetSeMag") != TARGET_SE:
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
        "full81DirectionGridAuthorized", "productionAuthorized", "adaptivePhotonExtensionAuthorized",
    ):
        if b.get(key) is not False:
            raise Failure(f"boundary changed: {key}")
    return m


def main():
    frozen_path = Path(os.environ.get("ORD56_FROZEN_RUNNER", "frozen-source/ordinal56_run_sentinel.py"))
    module = load_frozen_runner(frozen_path)

    # Keep the exact ordinal56 rendering, spectral mutation, execution, parsing, and output machinery.
    # Change only the fresh ordinal57 identity, seed bases, fixed 5M budget, and strict manifest validator.
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
