#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

STAGE = "koomen-81grid-map-recovery-v1"
EXECUTION_KEY = "koomen-81grid-map-recovery-v1:scientific:60"
ISSUE = 879
BASES = [1641000000, 1642000000, 1643000000, 1644000000, 1645000000, 1646000000]
ROWS = list(range(18, 28))
CASES = ["baseline", "profile"]
RINGS = [0.15, 0.30, 0.45, 0.60, 0.75]
FULL_AZ = [22.5 * i for i in range(16)]
EXEC_AZ = [22.5 * i for i in range(9)]
PHOTONS_BY_ROW = {
    18: 1_000_000, 19: 1_000_000, 20: 1_000_000,
    21: 2_000_000, 22: 2_000_000, 23: 2_000_000,
    24: 5_000_000, 25: 5_000_000, 26: 5_000_000, 27: 5_000_000,
}


class Failure(RuntimeError):
    pass


def load_frozen(path: Path):
    spec = importlib.util.spec_from_file_location("ordinal59_frozen_runner", path)
    if spec is None or spec.loader is None:
        raise Failure(f"cannot import frozen ordinal59 runner {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(path: Path):
    m = json.loads(path.read_text())
    if m.get("stageId") != STAGE or m.get("executionKey") != EXECUTION_KEY or m.get("issue") != ISSUE:
        raise Failure("wrong ordinal60 manifest identity")
    rec = m.get("recoveryFrom", {})
    if rec.get("issue") != 877 or rec.get("pr") != 878 or rec.get("preregistrationHead") != "c7c4a376450c99c8c57e760e23b6c719bc8a2ead" or rec.get("scienceHead") != "85a2439955cd0d2d7205aaff1c6dad9d54cdf7f9":
        raise Failure("ordinal59 recovery provenance changed")
    if rec.get("runId") != 33589493896 or rec.get("runAttempt") != 1 or rec.get("failedJobId") != 100120402180 or rec.get("terminalCommentId") != 5504216341:
        raise Failure("ordinal59 failed-run evidence changed")
    if rec.get("classification") != "FAIL_CLOSED_ORDINAL59_PREFLIGHT_DEPENDENCY_ORDER__ZERO_SOLVER__ZERO_RESULT" or rec.get("solverCalls") != 0 or rec.get("spectra") != 0 or rec.get("scientificResults") != 0:
        raise Failure("ordinal59 zero-result status changed")
    sub = m.get("frozenOrdinal59Substrate", {})
    if sub.get("headSha") != "c7c4a376450c99c8c57e760e23b6c719bc8a2ead" or sub.get("runnerBlob") != "3966e6318a0d433bba7920ead94decd978130ac0" or sub.get("analyzerBlob") != "b5288d5619de88c6661ccfbb61fc858a774ef80c":
        raise Failure("frozen ordinal59 substrate changed")
    if m.get("rows") != ROWS or m.get("cases") != CASES:
        raise Failure("row/case universe changed")
    fg = m.get("fullGrid", {})
    if fg.get("ringRadiiDeg") != RINGS or fg.get("azimuthsDeg") != FULL_AZ or fg.get("directionCount") != 81:
        raise Failure("full grid changed")
    sym = m.get("modelSymmetryReduction", {})
    if sym.get("executedAzimuthsDegPerRing") != EXEC_AZ or sym.get("executedDirectionCount") != 46 or sym.get("uniqueNonCenterExpectationCount") != 45 or sym.get("mirroredDirectionCount") != 35:
        raise Failure("symmetry reduction changed")
    mm = m.get("mystic", {})
    if mm.get("replicateSeedBases") != BASES or mm.get("derivedSeedOffset") != 997:
        raise Failure("fresh seed universe changed")
    if {int(k): int(v) for k, v in mm.get("photonsPerDirectionPerCaseByRow", {}).items()} != PHOTONS_BY_ROW:
        raise Failure("photon schedule changed")
    if mm.get("maximumSolverCalls") != 5520 or mm.get("maximumConfiguredPhotonHistories") != 16008000000 or mm.get("adaptiveExtensionAuthorized") is not False:
        raise Failure("maximum budget changed")
    if mm.get("method") != "direct ALIS" or mm.get("wavelengthNm") != [380,780] or float(mm.get("mcSpectralIsNm", -1)) != 550.0 or mm.get("mcVroom") != "on" or mm.get("mcEscapeExplicit") != "on":
        raise Failure("estimator changed")
    a = m.get("analysis", {})
    if a.get("replicateCount") != 6 or a.get("df") != 5 or a.get("familySize") != 45 or float(a.get("familyAlpha", -1)) != 0.05 or abs(float(a.get("studentTBonferroniCritical", -1)) - 6.712593092914674) > 1e-14:
        raise Failure("analysis family changed")
    if a.get("deltaDefinition") != "-2.5*log10(Q_target/Q_center)" or a.get("sampleMeanMinMaxDecisional") is not False:
        raise Failure("analysis semantics changed")
    for key in ("fitTaylor", "fitAcceptance", "fitFov", "fitSpectralResponse", "fitOffset", "fitAtmosphere", "fitAod", "fitProfile", "fitAnyParameter"):
        if a.get(key) is not False:
            raise Failure(f"fitting prohibition changed: {key}")
    c = m.get("classification", {})
    if c.get("valid") != "KOOMEN_81GRID_SIMULTANEOUS_SUPPORT_MAP_VALID" or c.get("invalid") != "KOOMEN_81GRID_SIMULTANEOUS_SUPPORT_MAP_INVALID" or c.get("numericalWidthPassFailThreshold") is not None:
        raise Failure("classification contract changed")
    b = m.get("boundaries", {})
    for key in ("TaylorResidualUsed", "historicalAcceptanceInvented", "exactHistoricalSpectralResponseClaimed", "exactHistoricalTemporalResponseClaimed", "continuousSupportExtremaClaimed", "rawSampledExtremaUsedDecisively", "importanceWavelengthRetuned", "quadraticSurrogateRehabilitated", "causalTaylorKoomenFractionClaimed", "productionAuthorized", "levelBAuthorized", "humanVisionChanged"):
        if b.get(key) is not False:
            raise Failure(f"boundary changed: {key}")
    return m


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--frozen-runner", type=Path, required=True)
    known, remaining = ap.parse_known_args()
    frozen = load_frozen(known.frozen_runner)
    frozen.STAGE = STAGE
    frozen.EXECUTION_KEY = EXECUTION_KEY
    frozen.ISSUE = ISSUE
    frozen.BASES = list(BASES)
    frozen.load_manifest = validate_manifest
    sys.argv = [sys.argv[0]] + remaining
    frozen.main()


if __name__ == "__main__":
    main()
