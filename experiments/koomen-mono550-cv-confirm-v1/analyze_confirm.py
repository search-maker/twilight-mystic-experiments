#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import tempfile
from pathlib import Path

STAGE = "koomen-mono550-cv-confirm-v1"
EXECUTION_KEY = "koomen-mono550-cv-confirm-v1:scientific:58"
OLD_STAGE = "koomen-mono550-cv-sentinel-v1"
OLD_KEY = "koomen-mono550-cv-sentinel-v1:scientific:56"
REPS = 6
CASES = ["baseline", "profile"]
DIRECTION_IDS = [0, 14, 18]
DIRECTIONS = [
    {"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "label": "center", "role": "center"},
    {"directionIndex": 14, "thetaDeg": 0.15, "relativeAzimuthDeg": 22.5, "label": "inner_015_0225", "role": "target"},
    {"directionIndex": 18, "thetaDeg": 0.75, "relativeAzimuthDeg": 292.5, "label": "outer_075_2925", "role": "target"},
]
BASES = [1621000000, 1622000000, 1623000000, 1624000000, 1625000000, 1626000000]
PHOTONS = 5_000_000
OLD_PHOTONS = 1_000_000
CLASS_MAP = {
    "MONO550_CV_SENTINEL_EQUIVALENT_AND_PRECISION_ELIGIBLE": "MONO550_CV_INDEPENDENT_GEOMETRY_CONFIRM_PASS",
    "MONO550_CV_SENTINEL_EQUIVALENT_BUT_PRECISION_INELIGIBLE": "MONO550_CV_INDEPENDENT_GEOMETRY_CONFIRM_PRECISION_FAIL",
    "MONO550_CV_SENTINEL_NOT_EQUIVALENT": "MONO550_CV_INDEPENDENT_GEOMETRY_CONFIRM_NOT_EQUIVALENT",
    "MONO550_CV_SENTINEL_INVALID": "MONO550_CV_INDEPENDENT_GEOMETRY_CONFIRM_INVALID",
}


class Failure(RuntimeError):
    pass


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("ordinal56_frozen_analyzer", path)
    if spec is None or spec.loader is None:
        raise Failure(f"cannot import frozen ordinal56 analyzer {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same_direction(a, b):
    return (
        int(a.get("directionIndex")) == int(b["directionIndex"])
        and float(a.get("thetaDeg")) == float(b["thetaDeg"])
        and float(a.get("relativeAzimuthDeg")) == float(b["relativeAzimuthDeg"])
        and a.get("label") == b["label"]
        and a.get("role") == b["role"]
    )


def validate_and_normalize_results(root: Path, norm: Path):
    files = sorted(root.rglob("sentinel-result.json"))
    if len(files) != REPS:
        raise Failure(f"expected {REPS} ordinal58 result files, got {len(files)}")
    reps = set()
    for p in files:
        x = json.loads(p.read_text())
        if x.get("stageId") != STAGE or x.get("executionKey") != EXECUTION_KEY or x.get("status") != "COMPLETED":
            raise Failure(f"bad ordinal58 identity/status in {p}")
        rep = int(x.get("replicate", -1))
        if rep not in range(1, REPS + 1) or rep in reps:
            raise Failure("duplicate/out-of-range replicate")
        reps.add(rep)
        if int(x.get("row", -1)) != 27:
            raise Failure("row changed")
        if int(x.get("seedBase", -1)) != BASES[rep - 1]:
            raise Failure("fresh seed-base universe changed")
        if int(x.get("photonsPerDirectionPerCaseArm", -1)) != PHOTONS:
            raise Failure("5M photon regime changed")
        if x.get("methodCommon") != "mc_vroom on + mc_escape on":
            raise Failure("common estimator changed")
        if float(x.get("alisImportanceCenterNm", -1)) != 550.0 or float(x.get("monoWavelengthNm", -1)) != 550.0:
            raise Failure("spectral estimator identity changed")
        if len(x.get("directions", [])) != len(DIRECTIONS) or not all(same_direction(got, exp) for got, exp in zip(x["directions"], DIRECTIONS)):
            raise Failure("fresh independent geometry mismatch")
        for key in (
            "TaylorResidualUsed", "ordinal54Salvage", "importanceWavelengthRetuned",
            "physicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized",
            "full81DirectionGridAuthorized", "productionAuthorized",
        ):
            if x.get(key) is not False:
                raise Failure(f"boundary changed: {key}")
        results = x.get("results", {})
        if set(results) != {"alis550", "mono550"}:
            raise Failure("arm universe changed")
        for arm in ("alis550", "mono550"):
            if set(results[arm]) != set(CASES):
                raise Failure("case universe changed")
            for case in CASES:
                rows = results[arm][case]
                if [int(r["directionIndex"]) for r in rows] != DIRECTION_IDS:
                    raise Failure("direction identifier universe/order changed")
                if len(rows) != len(DIRECTIONS) or not all(same_direction(got, exp) for got, exp in zip(rows, DIRECTIONS)):
                    raise Failure("result-row fresh geometry mismatch")

        # Metadata-only compatibility view for the exact frozen ordinal56 analyzer.
        # Numerical Q/runtime/seed/geometry values remain untouched; the frozen analyzer itself
        # keys targets by the retained compatibility identifiers 0/14/18.
        y = json.loads(json.dumps(x))
        y["stageId"] = OLD_STAGE
        y["executionKey"] = OLD_KEY
        y["photonsPerDirectionPerCaseArm"] = OLD_PHOTONS
        d = norm / f"rep{rep}"
        d.mkdir(parents=True, exist_ok=False)
        (d / "sentinel-result.json").write_text(json.dumps(y, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if reps != set(range(1, REPS + 1)):
        raise Failure("replicate universe incomplete")


def invalid_summary(error: str):
    return {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "classification": "MONO550_CV_INDEPENDENT_GEOMETRY_CONFIRM_INVALID",
        "validUniverse": False,
        "error": error,
        "TaylorResidualUsed": False,
        "ordinal54Salvage": False,
        "importanceWavelengthRetuned": False,
        "physicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridExecuted": False,
        "productionAuthorized": False,
        "adaptivePhotonExtensionAuthorized": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--ordinal56-analyzer", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    compact = []
    old = None
    try:
        old = load_module(a.ordinal56_analyzer)
        with tempfile.TemporaryDirectory(prefix="ord58-normalized-") as td:
            norm = Path(td)
            validate_and_normalize_results(a.results_root, norm)
            summary, compact = old.analyze(norm)
        old_class = summary.get("classification")
        if old_class not in CLASS_MAP:
            raise Failure(f"unexpected frozen ordinal56 analyzer classification {old_class!r}")
        summary["schemaVersion"] = 1
        summary["stageId"] = STAGE
        summary["executionKey"] = EXECUTION_KEY
        summary["classification"] = CLASS_MAP[old_class]
        summary["photonsPerDirectionPerCaseArm"] = PHOTONS
        summary["independentGeometry"] = DIRECTIONS
        summary["ordinal56FrozenAnalyzerClassificationBeforeTranslation"] = old_class
        summary["metadataCompatibilityAdapter"] = {
            "oldStageId": OLD_STAGE,
            "oldExecutionKey": OLD_KEY,
            "oldPhotonMetadata": OLD_PHOTONS,
            "changedFieldsOnly": ["stageId", "executionKey", "photonsPerDirectionPerCaseArm"],
            "numericalResultValuesChanged": False,
            "geometryValuesChangedInCompatibilityView": False,
            "directionIndicesAreIdentifiersOnly": True,
        }
        summary["full81DirectionGridExecuted"] = False
        summary["adaptivePhotonExtensionAuthorized"] = False
    except Failure as exc:
        summary = invalid_summary(str(exc))
        compact = []
    except Exception as exc:
        if old is not None and isinstance(exc, getattr(old, "Failure", ())):
            summary = invalid_summary(str(exc))
            compact = []
        else:
            raise

    (a.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    if compact:
        keys = ["kind", "case", "directionIndex", "n", "meanMag", "sdMag", "seMag", "ci95LowMag", "ci95HighMag", "pass"]
        with (a.output / "compact.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(compact)
    print(json.dumps({
        "classification": summary["classification"],
        "validUniverse": summary["validUniverse"],
        "equivalenceFailureCount": summary.get("equivalenceFailureCount"),
        "precisionFailureCount": summary.get("precisionFailureCount"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
