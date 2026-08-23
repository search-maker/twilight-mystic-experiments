from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STAGE = "aerosol-full-phase-function-sensitivity-v1"
EXPECTED_STATES = {
    "native-rural-ss",
    "opac-continental-average",
    "opac-maritime-clean",
    "opac-desert",
    "opac-desert-spheroids",
}


class LevelBInputRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def find_one(root: Path, basename: str) -> Path:
    rows = [path for path in root.rglob(basename) if path.is_file()]
    if len(rows) != 1:
        raise LevelBInputRefusal(f"{root}: expected exactly one {basename}, got {len(rows)}")
    return rows[0]


def build(
    design: dict[str, Any],
    acquisition: dict[str, Any],
    artifact_root: Path,
    *,
    expected_workflow_run_id: int,
    expected_scientific_ordinal: int,
) -> dict[str, Any]:
    if acquisition.get("status") != "COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE":
        raise LevelBInputRefusal("Level-B input may only be built after exact-360 aggregate acquisition success")
    if acquisition.get("workflowRunId") != expected_workflow_run_id:
        raise LevelBInputRefusal("acquisition workflow run drift")
    if acquisition.get("scientificOrdinal") != expected_scientific_ordinal:
        raise LevelBInputRefusal("acquisition scientific ordinal drift")
    if acquisition.get("caseArtifactCount") != 360 or acquisition.get("groupCount") != 72:
        raise LevelBInputRefusal("acquisition cardinality drift")
    if acquisition.get("analysisCellCount") != 24 or acquisition.get("statesPerGroup") != 5:
        raise LevelBInputRefusal("acquisition analysis/state cardinality drift")
    if design.get("status") != "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY":
        raise LevelBInputRefusal("frozen seeded design status drift")
    if design.get("caseCount") != 360 or design.get("groupCount") != 72 or design.get("analysisCellCount") != 24:
        raise LevelBInputRefusal("frozen seeded design cardinality drift")
    if acquisition.get("designCanonicalSha256") != design.get("canonicalDesignSha256"):
        raise LevelBInputRefusal("acquisition/design canonical hash drift")

    design_cases = {str(row["caseId"]): row for row in design.get("cases", [])}
    if len(design_cases) != 360:
        raise LevelBInputRefusal("design case universe must be exactly 360 unique IDs")
    acquisition_cases = {str(row["caseId"]): row for row in acquisition.get("cases", [])}
    if len(acquisition_cases) != 360 or set(acquisition_cases) != set(design_cases):
        raise LevelBInputRefusal("acquisition case universe does not equal frozen design")

    photopic_by_case: dict[str, float] = {}
    for case_id in sorted(design_cases):
        meta = acquisition_cases[case_id]
        artifact_name = str(meta.get("artifactName") or "")
        root = artifact_root / artifact_name
        if not artifact_name.startswith("afpf-v1-case-") or not root.is_dir():
            raise LevelBInputRefusal(f"{case_id}: exact case artifact directory missing")
        result_path = find_one(root, "case-result.json")
        if sha256_file(result_path) != meta.get("caseResultRawSha256"):
            raise LevelBInputRefusal(f"{case_id}: case-result raw hash differs from aggregate acquisition")
        result = json.loads(result_path.read_text())
        stored = result.get("contentSha256")
        check = dict(result)
        check.pop("contentSha256", None)
        if stored != canonical_sha256(check) or stored != meta.get("caseResultContentSha256"):
            raise LevelBInputRefusal(f"{case_id}: case-result content hash differs from aggregate acquisition")
        expected = design_cases[case_id]
        for key in (
            "caseId", "groupId", "analysisCellId", "sunDepressionDeg", "geometryId", "geometryTag",
            "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550", "replicate",
            "stateId", "aerosolKind", "opacMixture", "augmentedDataTreeSha256", "seed",
            "photonHistories", "numericalMethod",
        ):
            if result.get(key) != expected.get(key):
                raise LevelBInputRefusal(f"{case_id}: case-result/design drift for {key}")
        if result.get("stageId") != STAGE or result.get("status") != "COMPLETED":
            raise LevelBInputRefusal(f"{case_id}: case-result stage/status drift")
        if result.get("workflowRunId") != expected_workflow_run_id or result.get("scientificOrdinal") != expected_scientific_ordinal:
            raise LevelBInputRefusal(f"{case_id}: case-result run/ordinal drift")
        if result.get("workflowRunAttempt") != 1:
            raise LevelBInputRefusal(f"{case_id}: case-result attempt drift")
        channels = result.get("channels") or {}
        value = channels.get("photopicLuminanceCdM2")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LevelBInputRefusal(f"{case_id}: photopic channel missing/non-numeric")
        photopic_by_case[case_id] = float(value)

    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in design["cases"]:
        by_cell.setdefault(str(row["analysisCellId"]), []).append(row)
    if len(by_cell) != 24:
        raise LevelBInputRefusal("expected exactly 24 Level-B cells")

    cells: list[dict[str, Any]] = []
    for cell_id in sorted(by_cell):
        rows = by_cell[cell_id]
        sample = rows[0]
        replicates = []
        for replicate in (1, 2, 3):
            rep_rows = [row for row in rows if int(row["replicate"]) == replicate]
            if len(rep_rows) != 5 or {str(row["stateId"]) for row in rep_rows} != EXPECTED_STATES:
                raise LevelBInputRefusal(f"{cell_id}: incomplete five-state replicate {replicate}")
            if len({int(row["seed"]) for row in rep_rows}) != 1:
                raise LevelBInputRefusal(f"{cell_id}: CRN seed sharing drift in replicate {replicate}")
            records = {
                str(row["stateId"]): {"photopicLuminanceCdM2": photopic_by_case[str(row["caseId"])]}
                for row in rep_rows
            }
            replicates.append({"replicate": replicate, "recordsByState": records})
        cells.append({
            "analysisCellId": cell_id,
            "sunDepressionDeg": sample["sunDepressionDeg"],
            "geometryId": sample["geometryId"],
            "geometryTag": sample["geometryTag"],
            "targetAltitudeDeg": sample["targetAltitudeDeg"],
            "relativeAzimuthDeg": sample["relativeAzimuthDeg"],
            "aod550": sample["aod550"],
            "replicates": replicates,
        })

    return {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-level-b-input",
        "status": "COMPLETE_EXACT_360_LEVEL_B_INPUT_AFTER_AGGREGATE_VERIFICATION",
        "workflowRunId": expected_workflow_run_id,
        "scientificOrdinal": expected_scientific_ordinal,
        "caseCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "contrastCountPerCell": 7,
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "sourceAcquisitionStatus": acquisition["status"],
        "sourceCaseArtifactCount": acquisition["caseArtifactCount"],
        "cells": cells,
        "resultOpeningBeforeAggregatePermitted": False,
        "epsilonSubstitutionPermitted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-design", type=Path, required=True)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--scientific-ordinal", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = build(
        json.loads(args.execution_design.read_text()),
        json.loads(args.acquisition.read_text()),
        args.artifact_root,
        expected_workflow_run_id=args.workflow_run_id,
        expected_scientific_ordinal=args.scientific_ordinal,
    )
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
