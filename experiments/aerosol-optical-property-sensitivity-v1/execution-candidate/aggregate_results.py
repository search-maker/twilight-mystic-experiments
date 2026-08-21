from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any


class AggregateRefusal(RuntimeError):
    pass


STAGE = "aerosol-optical-property-sensitivity-v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AggregateRefusal(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_one(root: Path, basename: str) -> Path:
    rows = [p for p in root.rglob(basename) if p.is_file()]
    if len(rows) != 1:
        raise AggregateRefusal(f"{root}: expected exactly one {basename}, got {len(rows)}")
    return rows[0]


def parse_spectrum(path: Path) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for raw in path.read_text().splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelengths.append(float(parts[0]))
            values.append(float(parts[-1]))
        except ValueError:
            continue
    return wavelengths, values


def load_contract(stage_dir: Path) -> dict[str, Any]:
    contract = json.loads((stage_dir / "execution-contract.review.json").read_text())
    if contract.get("stageId") != f"{STAGE}-execution-contract":
        raise AggregateRefusal("execution contract stage drift")
    if contract.get("status") != "FROZEN_REVIEW_ONLY_EXECUTION_CONTRACT_NOT_AUTHORIZED":
        raise AggregateRefusal("execution contract status drift")
    if contract.get("expectedCaseCount") != 360 or contract.get("expectedGroupCount") != 72:
        raise AggregateRefusal("execution contract cardinality drift")
    return contract


def _finite_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)) and float(value) > 0.0


def aggregate(
    repository_root: Path,
    artifact_root: Path,
    artifact_metadata_path: Path,
    *,
    expected_workflow_run_id: int,
    expected_scientific_ordinal: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if expected_workflow_run_id <= 0 or expected_scientific_ordinal <= 0:
        raise AggregateRefusal("positive workflow run ID and scientific ordinal required")

    stage_dir = repository_root / "experiments" / STAGE
    contract_path = stage_dir / "execution-contract.review.json"
    contract = load_contract(stage_dir)
    design_mod = load_module("aops_v1_execution_design_for_aggregate", stage_dir / "execution_design.py")
    analysis = load_module("aops_v1_frozen_analysis_for_aggregate", stage_dir / "analysis.py")

    derived_path = repository_root / contract["sourceBindings"]["r8DerivedChannelsPath"]
    if git_blob_sha1(derived_path) != contract["sourceBindings"]["r8DerivedChannelsGitBlobSha1"]:
        raise AggregateRefusal("bound R8 derived-channel bytes changed")
    derived = load_module("aops_v1_bound_r8_derived_for_aggregate", derived_path)

    design = design_mod.build_review_execution_design()
    if design.get("status") != "REVIEW_ONLY_SEEDED_DESIGN_NON_RENDERABLE_NOT_AUTHORIZED":
        raise AggregateRefusal("frozen execution design status drift")
    if design.get("caseCount") != 360 or design.get("groupCount") != 72 or design.get("analysisCellCount") != 24:
        raise AggregateRefusal("frozen execution design cardinality drift")
    expected_cases = {str(row["caseId"]): row for row in design["cases"]}
    if len(expected_cases) != 360:
        raise AggregateRefusal("expected case ID uniqueness failure")

    metadata = json.loads(artifact_metadata_path.read_text())
    rows = metadata.get("artifacts", metadata if isinstance(metadata, list) else [])
    if not isinstance(rows, list):
        raise AggregateRefusal("artifact metadata missing list")
    prefix = str(contract["caseArtifactPrefix"])
    case_meta = [row for row in rows if str(row.get("name") or "").startswith(prefix)]
    if len(case_meta) != 360:
        raise AggregateRefusal(f"expected exactly 360 case artifacts, got {len(case_meta)}")
    names = [str(row.get("name") or "") for row in case_meta]
    if len(set(names)) != 360:
        raise AggregateRefusal("duplicate case artifact name")

    records: dict[str, dict[str, Any]] = {}
    acquisition_rows: list[dict[str, Any]] = []
    expected_contract_blob = git_blob_sha1(contract_path)
    raw_names = tuple(contract["rawMembersRequired"])

    static_keys = (
        "caseId", "groupId", "analysisCellId", "sunDepressionDeg", "geometryId", "geometryTag",
        "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550", "replicate",
        "stateId", "aerosolKind", "ssaSet", "ggSet", "seed", "photonHistories", "numericalMethod",
    )

    for meta in sorted(case_meta, key=lambda row: str(row.get("name") or "")):
        name = str(meta.get("name") or "")
        case_id = name[len(prefix):]
        expected = expected_cases.get(case_id)
        if expected is None:
            raise AggregateRefusal(f"unexpected case artifact: {name}")
        root = artifact_root / name
        if not root.is_dir():
            raise AggregateRefusal(f"downloaded artifact directory missing: {name}")
        result_path = find_one(root, "case-result.json")
        result = json.loads(result_path.read_text())

        for key in static_keys:
            if result.get(key) != expected.get(key):
                raise AggregateRefusal(f"{case_id}: result/design drift for {key}")
        if result.get("stageId") != STAGE or result.get("status") != "COMPLETED":
            raise AggregateRefusal(f"{case_id}: stage/status drift")
        if result.get("workflowRunId") != expected_workflow_run_id:
            raise AggregateRefusal(f"{case_id}: workflow run identity drift")
        if result.get("scientificOrdinal") != expected_scientific_ordinal:
            raise AggregateRefusal(f"{case_id}: scientific ordinal drift")
        if result.get("workflowRunAttempt") != 1:
            raise AggregateRefusal(f"{case_id}: workflow attempt drift")
        if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
            raise AggregateRefusal(f"{case_id}: syntax/solver execution count drift")
        if any(result.get(key) is not False for key in ("retryPerformed", "resumePerformed", "githubRerun")):
            raise AggregateRefusal(f"{case_id}: retry/resume/rerun drift")
        if result.get("processGroupIsolation") is not True:
            raise AggregateRefusal(f"{case_id}: process-group isolation missing")
        if result.get("designCanonicalSha256") != design["canonicalDesignSha256"]:
            raise AggregateRefusal(f"{case_id}: frozen design hash drift")
        if result.get("executionContractGitBlobSha1") != expected_contract_blob:
            raise AggregateRefusal(f"{case_id}: execution-contract binding drift")
        if result.get("rawOutputNodeCount") != int(contract["rawSpectrumNodeCount"]):
            raise AggregateRefusal(f"{case_id}: raw node-count drift")

        stored = result.get("contentSha256")
        check = dict(result)
        check.pop("contentSha256", None)
        if stored != canonical_sha256(check):
            raise AggregateRefusal(f"{case_id}: case-result content hash mismatch")

        raw_hashes = result.get("rawMemberSha256ByBasename")
        if not isinstance(raw_hashes, dict) or set(raw_hashes) != set(raw_names):
            raise AggregateRefusal(f"{case_id}: raw member hash-map drift")
        for basename in raw_names:
            path = find_one(root, basename)
            if raw_hashes.get(basename) != sha256_file(path):
                raise AggregateRefusal(f"{case_id}: raw member hash mismatch: {basename}")

        rad_path = find_one(root, "mc.rad.spc")
        std_path = find_one(root, "mc.rad.std.spc")
        wl, rad = parse_spectrum(rad_path)
        std_wl, std_rad = parse_spectrum(std_path)
        derived.validate_raw_grid(wl, rad)
        derived.validate_raw_grid(std_wl, std_rad)
        if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wl, std_wl)):
            raise AggregateRefusal(f"{case_id}: radiance/std wavelength grids differ")
        channels = derived.derive_channels(wl, rad)
        if result.get("channels") != channels:
            raise AggregateRefusal(f"{case_id}: derived-channel recomputation mismatch")
        if not all(_finite_positive(channels.get(key)) for key in analysis.PRIMARY_CHANNELS):
            # Frozen analysis will mark paired log contrasts unresolved when needed;
            # this gate only records the raw record and does not substitute epsilon.
            pass

        record = dict(channels)
        record["radianceSpectrum"] = rad
        records[case_id] = record
        acquisition_rows.append({
            "caseId": case_id,
            "artifactId": meta.get("id"),
            "artifactName": name,
            "artifactDigest": meta.get("digest"),
            "artifactSizeBytes": meta.get("size_in_bytes"),
            "caseResultRawSha256": sha256_file(result_path),
            "caseResultContentSha256": stored,
            "rawMemberSha256ByBasename": raw_hashes,
        })

    if set(records) != set(expected_cases):
        raise AggregateRefusal("case artifact universe does not equal frozen 360-case design")

    by_cell: dict[str, list[dict[str, Any]]] = {}
    for row in design["cases"]:
        by_cell.setdefault(str(row["analysisCellId"]), []).append(row)
    if len(by_cell) != 24:
        raise AggregateRefusal("expected exactly 24 analysis cells")

    scalar_cells: list[dict[str, Any]] = []
    spectral_cells: dict[str, Any] = {}
    expected_states = set(analysis.EXPECTED_STATES)

    for cell_id in sorted(by_cell):
        rows_for_cell = by_cell[cell_id]
        replicate_scalar: list[dict[str, dict[str, float | None]]] = []
        replicate_spectral: list[dict[str, list[float | None]]] = []
        for rep in (1, 2, 3):
            rep_rows = [row for row in rows_for_cell if int(row["replicate"]) == rep]
            if len(rep_rows) != 5 or {str(row["stateId"]) for row in rep_rows} != expected_states:
                raise AggregateRefusal(f"{cell_id}: incomplete five-state replicate {rep}")
            seeds = {int(row["seed"]) for row in rep_rows}
            if len(seeds) != 1:
                raise AggregateRefusal(f"{cell_id}: CRN seed sharing drift in replicate {rep}")
            records_by_state = {str(row["stateId"]): records[str(row["caseId"])] for row in rep_rows}
            scalar_for_rep = {
                channel: analysis.scalar_replicate_contrasts(records_by_state, channel)
                for channel in analysis.PRIMARY_CHANNELS
            }
            spectra_by_state = {
                state: list(records_by_state[state]["radianceSpectrum"])
                for state in expected_states
            }
            replicate_scalar.append(scalar_for_rep)
            replicate_spectral.append(analysis.spectral_replicate_contrasts(spectra_by_state))

        sample = rows_for_cell[0]
        scalar_cells.append({
            "analysisCellId": cell_id,
            "sunDepressionDeg": sample["sunDepressionDeg"],
            "geometryId": sample["geometryId"],
            "geometryTag": sample["geometryTag"],
            "targetAltitudeDeg": sample["targetAltitudeDeg"],
            "relativeAzimuthDeg": sample["relativeAzimuthDeg"],
            "aod550": sample["aod550"],
            "primary": analysis.aggregate_three_replicates(replicate_scalar),
        })
        spectral_cells[cell_id] = analysis.summarize_spectral_three(replicate_spectral)

    acquisition = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-acquisition",
        "status": "COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE",
        "workflowRunId": expected_workflow_run_id,
        "scientificOrdinal": expected_scientific_ordinal,
        "caseArtifactCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "designCanonicalSha256": design["canonicalDesignSha256"],
        "executionContractGitBlobSha1": expected_contract_blob,
        "cases": acquisition_rows,
    }
    analysis_out = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-preregistered-analysis",
        "status": "COMPLETED_PREREGISTERED_AOPS_V1_ANALYSIS",
        "workflowRunId": expected_workflow_run_id,
        "scientificOrdinal": expected_scientific_ordinal,
        "caseCount": 360,
        "comparisonGroupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "contrastCountPerPrimaryChannelPerCell": 9,
        "primaryChannels": list(analysis.PRIMARY_CHANNELS),
        "nonpositiveHandling": "NUMERICALLY_UNRESOLVED_NO_EPSILON",
        "pairedContrastUncertaintyUsePermitted": False,
        "inferentialPValueOrConfidenceIntervalPermitted": False,
        "postResultRuleChangePermitted": False,
        "cells": scalar_cells,
    }
    spectral_out = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-preregistered-spectral-analysis",
        "status": "COMPLETED_PREREGISTERED_AOPS_V1_SPECTRAL_ANALYSIS",
        "analysisCellCount": 24,
        "contrastCountPerCell": 9,
        "wavelengthGrid": {"startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "nodeCount": 8001},
        "cells": spectral_cells,
        "inferentialPValueOrConfidenceIntervalPermitted": False,
    }
    return acquisition, analysis_out, spectral_out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--artifact-metadata", type=Path, required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--scientific-ordinal", type=int, required=True)
    parser.add_argument("--output-acquisition", type=Path, required=True)
    parser.add_argument("--output-analysis", type=Path, required=True)
    parser.add_argument("--output-spectral", type=Path, required=True)
    args = parser.parse_args()
    acquisition, analysis_out, spectral_out = aggregate(
        args.repository_root,
        args.artifact_root,
        args.artifact_metadata,
        expected_workflow_run_id=args.workflow_run_id,
        expected_scientific_ordinal=args.scientific_ordinal,
    )
    args.output_acquisition.write_text(json.dumps(acquisition, indent=2, sort_keys=True) + "\n")
    args.output_analysis.write_text(json.dumps(analysis_out, indent=2, sort_keys=True) + "\n")
    args.output_spectral.write_text(json.dumps(spectral_out, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
