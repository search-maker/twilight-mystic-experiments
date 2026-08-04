#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-final-convergence-v1"
SELECTED = {"g01-reference-bridge", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol"}
DIAGNOSTIC_GROUPS = {"g01-reference-bridge", "g06-late-opposite-high-aerosol"}
REFERENCES_NM = (500.0, 550.0, 600.0)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case(case_id: str, group: str, method: str, ordinal: int, seed: int, block: int, purpose: str, ref: float | None = None) -> dict[str, Any]:
    result = {"caseId": case_id, "groupId": group, "method": method, "ordinal": ordinal, "seed": seed, "block": block, "photonHistories": 20_000_000, "purpose": purpose}
    if ref is not None:
        result["alisSpectralImportanceSamplingNm"] = ref
    return result


def build(stage2_manifest: dict[str, Any], screening: dict[str, Any], convergence: dict[str, Any], provenance: dict[str, Any], stage2_manifest_path: Path, screening_path: Path, convergence_path: Path) -> dict[str, Any]:
    if stage2_manifest.get("stageId") != "cross-geometry-stage-two-v1":
        raise ValueError("wrong stage-two manifest")
    if screening.get("stageId") != "cross-geometry-stage-two-v1" or screening.get("status") != "STAGE_TWO_SCREENING_ANALYZED":
        raise ValueError("wrong stage-two screening")
    if convergence.get("stageId") != "cross-geometry-convergence-v2" or convergence.get("status") != "REANALYZED_WITH_MEAN_UNCERTAINTY":
        raise ValueError("wrong convergence reanalysis")
    if provenance.get("stageId") != STAGE_ID or provenance.get("status") != "SOURCE_STAGE_TWO_FROZEN":
        raise ValueError("wrong source provenance")
    if provenance.get("frozenScreeningCopyRawSha256") != sha(screening_path):
        raise ValueError("frozen screening copy hash changed")
    if provenance.get("sourceConvergenceV2RawSha256") != sha(convergence_path):
        raise ValueError("convergence copy hash changed")
    needs = {result["groupId"] for result in convergence["geometryResults"] if result.get("classificationV2") == "NEEDS_MORE_PRECISION"}
    if needs != SELECTED:
        raise ValueError(f"unexpected final convergence set: {sorted(needs)}")
    geometries = [geometry for geometry in stage2_manifest["geometries"] if geometry["geometryId"] in SELECTED]
    if {geometry["geometryId"] for geometry in geometries} != SELECTED:
        raise ValueError("missing selected geometry")

    cases: list[dict[str, Any]] = []
    ordinal = 1
    for group, stem, base in (("g01-reference-bridge", "g01", 78700), ("g05-mid-opposite-low", "g05", 78740), ("g06-late-opposite-high-aerosol", "g06", 78750)):
        for block, offset in ((5, 1), (6, 2)):
            cases.append(case(f"cgf-{stem}-vroom-b{block}", group, "reference-vroom", ordinal, base + offset, block, "continuation"))
            ordinal += 1
    for block, offset in ((5, 1), (6, 2)):
        cases.append(case(f"cgf-g05-alis-b{block}", "g05-mid-opposite-low", "alis", ordinal, 78840 + offset, block, "continuation", 405.0))
        ordinal += 1
    seed_bases = {500.0: 78900, 550.0: 79000, 600.0: 79100}
    group_offsets = {"g01-reference-bridge": 0, "g06-late-opposite-high-aerosol": 50}
    stems = {"g01-reference-bridge": "g01", "g06-late-opposite-high-aerosol": "g06"}
    for group in sorted(DIAGNOSTIC_GROUPS):
        for reference_nm in REFERENCES_NM:
            for replicate in (1, 2, 3):
                cases.append(case(f"cgf-{stems[group]}-alis-is{int(reference_nm)}-r{replicate}", group, "alis", ordinal, seed_bases[reference_nm] + group_offsets[group] + replicate, replicate, "alis-reference-diagnostic", reference_nm))
                ordinal += 1
    seeds = [item["seed"] for item in cases]
    if len(cases) != 26 or len(set(seeds)) != 26:
        raise ValueError("final case accounting failure")
    if {item["seed"] for item in stage2_manifest["cases"]}.intersection(seeds):
        raise ValueError("final seeds reuse stage-two seeds")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "cross-geometry-final-convergence-screening-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
        "boundary": "adaptive final convergence: correct mean-uncertainty metric, finish g05, stabilize VROOM, and diagnose ALIS importance wavelength at g01/g06; no automatic production acceptance",
        "sourceStageTwoProposalRawSha256": sha(stage2_manifest_path),
        "sourceStageTwoScreeningRawSha256": provenance["sourceStageTwoScreeningRawSha256"],
        "sourceConvergenceV2RawSha256": sha(convergence_path),
        "sourceScientificRunId": provenance["sourceScientificRunId"],
        "selectedGeometryIds": sorted(SELECTED),
        "diagnosticGeometryIds": sorted(DIAGNOSTIC_GROUPS),
        "alisReferenceCandidatesNm": list(REFERENCES_NM),
        "geometries": geometries,
        "frozenInputs": json.loads(json.dumps(stage2_manifest["frozenInputs"])),
        "runtime": stage2_manifest["runtime"],
        "cases": cases,
        "limits": {"maximumCases": 26, "maximumConfiguredMcPhotonsSum": 520_000_000, "maximumParallel": 16, "perCaseTimeoutSeconds": 900},
        "analysisPlan": {"meanUncertaintyMetric": "relativeStandardErrorOfMean", "maximumRelativeStandardErrorOfMean": 0.10, "alisAllZeroNodeStdMeansUnavailable": True, "g04CarriedAsAgreementUnderMetricV2": True, "g05UsesSixBlocksPerMethod": True, "g01G06ChooseLowestVarianceCompatibleAlisReference": True, "noOpenEndedAdditionalBlocks": True},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-two-manifest", type=Path, required=True)
    parser.add_argument("--screening", type=Path, required=True)
    parser.add_argument("--convergence", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(load(args.stage_two_manifest), load(args.screening), load(args.convergence), load(args.provenance), args.stage_two_manifest, args.screening, args.convergence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump(result))
    print(dump(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
