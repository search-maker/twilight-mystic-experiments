#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-three-v1"
BATCH_ID = "cross-geometry-stage-three-diagnostics-v1"
PHOTONS = 20_000_000

GEOMETRIES = [
    {"geometryId": "g01-reference-bridge", "sunDepressionDeg": 12.0, "targetAltitudeDeg": 10.0, "relativeAzimuthDeg": 120.0, "observerElevationM": 0.0, "aod550": 0.15},
    {"geometryId": "g05-mid-opposite-low", "sunDepressionDeg": 8.0, "targetAltitudeDeg": 10.0, "relativeAzimuthDeg": 180.0, "observerElevationM": 0.0, "aod550": 0.15},
    {"geometryId": "g06-late-opposite-high-aerosol", "sunDepressionDeg": 12.0, "targetAltitudeDeg": 45.0, "relativeAzimuthDeg": 180.0, "observerElevationM": 0.0, "aod550": 0.30},
]


class ProposalFailure(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ProposalFailure(f"expected JSON object: {path}")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def make_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def add(case_id: str, group: str, method: str, block: int, seed: int, importance: float | None = None) -> None:
        item: dict[str, Any] = {
            "ordinal": len(cases) + 1,
            "caseId": case_id,
            "groupId": group,
            "method": method,
            "block": block,
            "seed": seed,
            "photonHistories": PHOTONS,
        }
        if importance is not None:
            item["alisSpectralImportanceSamplingNm"] = importance
        cases.append(item)

    for group, code, vseed, aseed in (
        ("g01-reference-bridge", "g01", 79300, 79500),
        ("g06-late-opposite-high-aerosol", "g06", 79350, 79550),
    ):
        add(f"cg3-{code}-vroom-b5", group, "reference-vroom", 5, vseed + 1)
        add(f"cg3-{code}-vroom-b6", group, "reference-vroom", 6, vseed + 2)
        for importance, suffix, offset in ((500.0, "is500", 1), (550.0, "is550", 11), (600.0, "is600", 21)):
            for replicate in range(1, 4):
                add(
                    f"cg3-{code}-alis-{suffix}-r{replicate}",
                    group,
                    "alis",
                    4 + replicate,
                    aseed + offset + replicate - 1,
                    importance,
                )

    add("cg3-g05-alis-b5", "g05-mid-opposite-low", "alis", 5, 79541, 405.0)
    add("cg3-g05-alis-b6", "g05-mid-opposite-low", "alis", 6, 79542, 405.0)
    return cases


def build(convergence_path: Path, provenance_path: Path) -> dict[str, Any]:
    convergence = load(convergence_path)
    provenance = load(provenance_path)
    if convergence.get("stageId") != "cross-geometry-convergence-v2" or convergence.get("status") != "CORRECTED_CONVERGENCE_ANALYZED":
        raise ProposalFailure("corrected convergence report did not pass")
    expected_counts = {
        "ADDITIONAL_ALIS_BLOCKS_REQUIRED": 1,
        "ALIS_IMPORTANCE_WAVELENGTH_DIAGNOSIS_REQUIRED": 2,
        "CONVERGED_SCREENING_AGREEMENT": 3,
    }
    if convergence.get("classificationCounts") != expected_counts:
        raise ProposalFailure("corrected convergence classification counts changed")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_STAGE_TWO_FROZEN":
        raise ProposalFailure("Stage-3 source provenance did not pass")
    cases = make_cases()
    seeds = [case["seed"] for case in cases]
    if len(cases) != 24 or len(set(seeds)) != 24:
        raise ProposalFailure("Stage-3 case or seed accounting changed")
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": BATCH_ID,
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
        "sourceConvergenceRawSha256": sha(convergence_path),
        "sourceProvenanceRawSha256": sha(provenance_path),
        "selectedGeometryIds": ["g01-reference-bridge", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol"],
        "notRerunGeometryIds": ["g02-early-near-low", "g03-early-perpendicular-high", "g04-mid-perpendicular"],
        "diagnosticDesign": {
            "g01AndG06": {
                "referenceVroomFreshBlocks": [5, 6],
                "alisImportanceSamplingCandidatesNm": [500.0, 550.0, 600.0],
                "freshReplicatesPerCandidate": 3,
                "purpose": "separate ALIS importance-wavelength efficiency or approximation effects from ordinary Monte Carlo noise",
            },
            "g05": {
                "alisImportanceSamplingNm": 405.0,
                "freshBlocks": [5, 6],
                "purpose": "complete six-block ALIS mean because the four-block relative standard error was only slightly above 10 percent",
            },
            "g04": {"action": "no rerun", "reason": "corrected ratio relative standard error is 6.46 percent and the mean ratio is 0.893"},
        },
        "cases": cases,
        "geometries": GEOMETRIES,
        "frozenInputs": {
            "albedo": 0.15,
            "defaultAlisSpectralImportanceSamplingNm": 405.0,
            "wavelengthDomainNm": [380, 780],
            "diagnosticNodesNm": [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660],
            "molecularAbsorption": "crs",
            "mcSpherical": "1D",
            "dataPaths": {
                "atmosphere": {"root": "libRadtranData", "path": "atmmod/afglus.dat"},
                "solarFlux": {"root": "libRadtranData", "path": "solar_flux/atlas_plus_modtran"},
                "wavelengthGrid": {"root": "repository", "path": "experiments/reference-vroom-v1/wavelength-grid.dat"},
            },
        },
        "runtime": {
            "kind": "micromamba-lock",
            "exactPackageSpec": "rubin-libradtran=2.0.6=py312pl5321he9373c2_1",
            "containerImageDigest": None,
            "uvspecSha256": "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3",
            "uvspecHelpSha256": "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548",
            "libRadtranDataTreeSha256": "ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7",
            "atmosphereSha256": "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5",
            "runtimeLockRawSha256": "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5",
        },
        "limits": {
            "maximumCases": 24,
            "maximumConfiguredMcPhotonsSum": 480_000_000,
            "maximumParallel": 6,
            "perCaseTimeoutSeconds": 900,
        },
        "analysisRules": {
            "primaryNoiseMetric": "independent-replicate relative standard error of the mean",
            "maximumRelativeStandardErrorOfMean": 0.10,
            "candidateMeanRatioAlisToVroomClosedInterval": [0.75, 1.25],
            "candidateSelection": "lowest relative standard error among candidates passing ratio and spectral-shape screens",
            "ifNoCandidatePasses": "TECHNICAL_ALIS_DIAGNOSIS_REQUIRED",
            "automaticAdditionalBlocksAfterStageThreeForbidden": True,
        },
        "boundary": "Stage-3 is a bounded diagnostic and convergence batch. It cannot authorize a production engine, LUT, surrogate, default-model change, or observational-validity claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--convergence", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build(args.convergence, args.provenance)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
