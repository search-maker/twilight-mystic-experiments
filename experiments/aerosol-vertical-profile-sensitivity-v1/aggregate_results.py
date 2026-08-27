from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"


class AggregateRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def find_one(root: Path, relative_or_basename: str) -> Path:
    direct = root / relative_or_basename
    if direct.is_file():
        return direct
    rows = [path for path in root.rglob(Path(relative_or_basename).name) if path.is_file()]
    if len(rows) != 1:
        raise AggregateRefusal(f"{root}: expected exactly one {relative_or_basename}, got {len(rows)}")
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
    if contract.get("status") != "FROZEN_REVIEW_ONLY_EXECUTION_TRANSPORT_NOT_AUTHORIZED":
        raise AggregateRefusal("execution contract status drift")
    if contract.get("expectedCaseCount") != 360 or contract.get("expectedGroupCount") != 72:
        raise AggregateRefusal("execution contract cardinality drift")
    if contract.get("expectedAnalysisCellCount") != 24 or contract.get("expectedStatesPerGroup") != 5:
        raise AggregateRefusal("execution contract analysis/state cardinality drift")
    if contract.get("expectedPrimaryContrastCount") != 4:
        raise AggregateRefusal("execution contract contrast cardinality drift")
    return contract


def validate_bound_sources(repository_root: Path, contract: dict[str, Any]) -> dict[str, Path]:
    bindings = contract["sourceBindings"]
    pairs = (
        ("protocolPath", "protocolGitBlobSha1"),
        ("executionCandidatePath", "executionCandidateGitBlobSha1"),
        ("executionPackagePath", "executionPackageGitBlobSha1"),
        ("adapterPath", "adapterGitBlobSha1"),
        ("analysisPath", "analysisGitBlobSha1"),
        ("levelBAnalysisPath", "levelBAnalysisGitBlobSha1"),
        ("executorPath", "executorGitBlobSha1"),
        ("aggregatorPath", "aggregatorGitBlobSha1"),
        ("processGroupRunnerPath", "processGroupRunnerGitBlobSha1"),
        ("runtimeOverlayPath", "runtimeOverlayGitBlobSha1"),
        ("r8DerivedChannelsPath", "r8DerivedChannelsGitBlobSha1"),
        ("r8AnalysisPath", "r8AnalysisGitBlobSha1"),
        ("wavelengthGridPath", "wavelengthGridGitBlobSha1"),
    )
    resolved: dict[str, Path] = {}
    for path_key, blob_key in pairs:
        path = repository_root / bindings[path_key]
        if git_blob_sha1(path) != bindings[blob_key]:
            raise AggregateRefusal(f"bound source bytes changed: {path}")
        resolved[path_key] = path
    runtime_lock = repository_root / contract["runtimeIdentity"]["runtimeLockPath"]
    if git_blob_sha1(runtime_lock) != contract["runtimeIdentity"]["runtimeLockGitBlobSha1"]:
        raise AggregateRefusal("runtime lock Git blob drift")
    if sha256_file(runtime_lock) != contract["runtimeIdentity"]["runtimeLockRawSha256"]:
        raise AggregateRefusal("runtime lock raw SHA drift")
    return resolved


def validate_runtime_report(runtime: dict[str, Any], contract: dict[str, Any], case_id: str) -> None:
    if runtime.get("scientificSolverExecuted") is not False:
        raise AggregateRefusal(f"{case_id}: runtime identity report is not pre-solver")
    expected = contract["runtimeIdentity"]
    mapping = {
        "runtimeLockRawSha256": "runtimeLockRawSha256",
        "uvspecSha256": "uvspecSha256",
        "uvspecHelpSha256": "uvspecHelpSha256",
        "libRadtranDataTreeSha256": "augmentedDataTreeSha256",
        "atmosphereSha256": "atmosphereSha256",
    }
    for runtime_key, contract_key in mapping.items():
        if runtime.get(runtime_key) != expected.get(contract_key):
            raise AggregateRefusal(f"{case_id}: runtime identity drift: {runtime_key}")
    if runtime.get("exactPackageSpec") not in (None, expected.get("exactPackageSpec")):
        raise AggregateRefusal(f"{case_id}: runtime package spec drift")


def cell_id(case: dict[str, Any]) -> str:
    return f"dep{float(case['sunDepressionDeg']):.1f}|aod{float(case['aod550']):.2f}|{case['geometryId']}"


def aggregate(
    repository_root: Path,
    authorization_path: Path,
    artifact_root: Path,
    artifact_metadata_path: Path,
    *,
    expected_workflow_run_id: int,
    expected_scientific_ordinal: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if expected_workflow_run_id <= 0 or expected_scientific_ordinal <= 0:
        raise AggregateRefusal("positive workflow run ID and scientific ordinal required")

    stage_dir = repository_root / "experiments" / STAGE
    contract_path = stage_dir / "execution-contract.review.json"
    contract = load_contract(stage_dir)
    sources = validate_bound_sources(repository_root, contract)
    adapter = load_module("avps_adapter_for_aggregate", sources["adapterPath"])
    derived = load_module("avps_bound_r8_derived_for_aggregate", sources["r8DerivedChannelsPath"])
    auth = json.loads(authorization_path.read_text())
    adapter.validate_authorization_bindings(auth)
    if auth.get("scientificOrdinal") != expected_scientific_ordinal:
        raise AggregateRefusal("authorization/expected scientific ordinal drift")
    expected_cases = {row["caseId"]: row for row in adapter.authorized_case_universe(auth)}
    if len(expected_cases) != 360:
        raise AggregateRefusal("expected authorized case universe drift")

    metadata = json.loads(artifact_metadata_path.read_text())
    rows = metadata.get("artifacts", []) if isinstance(metadata, dict) else metadata
    if not isinstance(rows, list):
        raise AggregateRefusal("artifact metadata must contain a list")
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
    fixed_raw = tuple(contract["rawMembersRequired"])

    static_keys = (
        "caseId", "groupId", "sunDepressionDeg", "geometryId", "geometryTag",
        "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550",
        "replicate", "stateId", "seed", "photonHistories", "numericalMethod",
    )

    for meta in sorted(case_meta, key=lambda row: str(row.get("name") or "")):
        name = str(meta.get("name") or "")
        case_id_value = name[len(prefix):]
        expected = expected_cases.get(case_id_value)
        if expected is None:
            raise AggregateRefusal(f"unexpected case artifact: {name}")
        root = artifact_root / name
        if not root.is_dir():
            raise AggregateRefusal(f"downloaded artifact directory missing: {name}")
        result_path = find_one(root, "case-result.json")
        result = json.loads(result_path.read_text())

        for key in static_keys:
            if result.get(key) != expected.get(key):
                raise AggregateRefusal(f"{case_id_value}: result/authorized-case drift for {key}")
        if result.get("stageId") != STAGE or result.get("status") != "COMPLETED":
            raise AggregateRefusal(f"{case_id_value}: stage/status drift")
        if result.get("workflowRunId") != expected_workflow_run_id or result.get("scientificOrdinal") != expected_scientific_ordinal:
            raise AggregateRefusal(f"{case_id_value}: workflow/ordinal identity drift")
        if result.get("workflowRunAttempt") != 1:
            raise AggregateRefusal(f"{case_id_value}: workflow attempt drift")
        if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
            raise AggregateRefusal(f"{case_id_value}: syntax/solver count drift")
        if any(result.get(key) is not False for key in ("retryPerformed", "resumePerformed", "githubRerun")):
            raise AggregateRefusal(f"{case_id_value}: retry/resume/rerun drift")
        if result.get("processGroupIsolation") is not True:
            raise AggregateRefusal(f"{case_id_value}: process-group isolation missing")
        if result.get("executionDesignCanonicalSha256") != auth.get("executionDesignCanonicalSha256"):
            raise AggregateRefusal(f"{case_id_value}: execution design binding drift")
        if result.get("executionContractGitBlobSha1") != expected_contract_blob:
            raise AggregateRefusal(f"{case_id_value}: execution-contract binding drift")
        if result.get("disabledExecutionPackageCanonicalSha256") != contract["disabledExecutionPackageCanonicalSha256"]:
            raise AggregateRefusal(f"{case_id_value}: disabled-package binding drift")
        if result.get("caseSurfaceSha256") != expected.get("caseSurfaceSha256"):
            raise AggregateRefusal(f"{case_id_value}: case-surface hash drift")
        if result.get("exactAfglProfileTauSha256") != contract["exactAfglProfileTauSha256"][expected["stateId"]]:
            raise AggregateRefusal(f"{case_id_value}: exact-AFGL tau hash drift")
        if result.get("rawOutputNodeCount") != contract["rawSpectrumNodeCount"]:
            raise AggregateRefusal(f"{case_id_value}: raw node count drift")
        if result.get("resultOpeningAuthorized") is not False:
            raise AggregateRefusal(f"{case_id_value}: per-case result crossed result-opening boundary")

        stored = result.get("contentSha256")
        check = dict(result)
        check.pop("contentSha256", None)
        if stored != canonical_sha256(check):
            raise AggregateRefusal(f"{case_id_value}: case-result content hash mismatch")

        profile_rel = f"profiles/{expected['stateId']}.tau"
        expected_raw_keys = set(fixed_raw) | {profile_rel}
        raw_hashes = result.get("rawMemberSha256ByRelativePath")
        if not isinstance(raw_hashes, dict) or set(raw_hashes) != expected_raw_keys:
            raise AggregateRefusal(f"{case_id_value}: raw member hash-map drift")
        for rel in sorted(expected_raw_keys):
            path = find_one(root, rel)
            if raw_hashes.get(rel) != sha256_file(path):
                raise AggregateRefusal(f"{case_id_value}: raw member hash mismatch: {rel}")
        if result.get("caseInpSha256") != raw_hashes["case.inp"]:
            raise AggregateRefusal(f"{case_id_value}: case input hash mismatch")
        if result.get("runtimeReportRawSha256") != raw_hashes["runtime-report.json"]:
            raise AggregateRefusal(f"{case_id_value}: runtime-report hash mismatch")
        if result.get("radianceOutputSha256") != raw_hashes["mc.rad.spc"]:
            raise AggregateRefusal(f"{case_id_value}: radiance hash mismatch")
        if result.get("stdRadianceOutputSha256") != raw_hashes["mc.rad.std.spc"]:
            raise AggregateRefusal(f"{case_id_value}: std-radiance hash mismatch")
        if raw_hashes[profile_rel] != contract["exactAfglProfileTauSha256"][expected["stateId"]]:
            raise AggregateRefusal(f"{case_id_value}: profile artifact hash mismatch")

        runtime_report = json.loads(find_one(root, "runtime-report.json").read_text())
        validate_runtime_report(runtime_report, contract, case_id_value)
        wavelengths, radiance = parse_spectrum(find_one(root, "mc.rad.spc"))
        std_wavelengths, std_radiance = parse_spectrum(find_one(root, "mc.rad.std.spc"))
        derived.validate_raw_grid(wavelengths, radiance)
        derived.validate_raw_grid(std_wavelengths, std_radiance)
        if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wavelengths, std_wavelengths)):
            raise AggregateRefusal(f"{case_id_value}: radiance/std wavelength grids differ")
        channels = derived.derive_channels(wavelengths, radiance)
        if result.get("channels") != channels:
            raise AggregateRefusal(f"{case_id_value}: derived channel recomputation mismatch")

        records[case_id_value] = {
            "case": expected,
            "channels": channels,
            "radianceSpectrumSha256": raw_hashes["mc.rad.spc"],
            "stdRadianceSpectrumSha256": raw_hashes["mc.rad.std.spc"],
        }
        acquisition_rows.append({
            "caseId": case_id_value,
            "artifactId": meta.get("id"),
            "artifactName": name,
            "artifactDigest": meta.get("digest"),
            "artifactSizeBytes": meta.get("size_in_bytes"),
            "caseResultRawSha256": sha256_file(result_path),
            "caseResultContentSha256": stored,
            "rawMemberSha256ByRelativePath": raw_hashes,
        })

    if set(records) != set(expected_cases):
        raise AggregateRefusal("case artifact universe does not equal exact authorized 360-case universe")

    cells: dict[str, dict[str, Any]] = {}
    for case_id_value, row in records.items():
        case = row["case"]
        cid = cell_id(case)
        cell = cells.setdefault(cid, {
            "analysisCellId": cid,
            "sunDepressionDeg": case["sunDepressionDeg"],
            "aod550": case["aod550"],
            "geometryId": case["geometryId"],
            "geometryTag": case["geometryTag"],
            "targetAltitudeDeg": case["targetAltitudeDeg"],
            "relativeAzimuthDeg": case["relativeAzimuthDeg"],
            "replicates": {},
        })
        rep = str(case["replicate"])
        rep_row = cell["replicates"].setdefault(rep, {"replicate": case["replicate"], "recordsByState": {}})
        if case["stateId"] in rep_row["recordsByState"]:
            raise AggregateRefusal(f"{cid}: duplicate state in replicate {rep}")
        rep_row["recordsByState"][case["stateId"]] = row["channels"]

    if len(cells) != 24:
        raise AggregateRefusal(f"expected 24 analysis cells, got {len(cells)}")
    expected_states = set(contract["stateIds"])
    normalized_cells: list[dict[str, Any]] = []
    for cid in sorted(cells):
        cell = cells[cid]
        if set(cell["replicates"]) != {"1", "2", "3"}:
            raise AggregateRefusal(f"{cid}: exact three replicate identities required")
        reps = [cell["replicates"][str(i)] for i in (1, 2, 3)]
        if any(set(rep["recordsByState"]) != expected_states for rep in reps):
            raise AggregateRefusal(f"{cid}: exact five-state replicate universe required")
        normalized_cells.append({**{k: v for k, v in cell.items() if k != "replicates"}, "replicates": reps})

    acquisition = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-aggregate-verification",
        "status": "COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE_RESULTS_STILL_CLOSED",
        "workflowRunId": expected_workflow_run_id,
        "scientificOrdinal": expected_scientific_ordinal,
        "caseCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "sourceArtifactCount": 360,
        "executionContractGitBlobSha1": expected_contract_blob,
        "authorizationDocumentSha256": canonical_sha256(auth),
        "disabledExecutionPackageCanonicalSha256": contract["disabledExecutionPackageCanonicalSha256"],
        "resultOpeningAuthorized": False,
        "partialResultInterpretationPermitted": False,
        "artifacts": acquisition_rows,
    }
    acquisition["contentSha256"] = canonical_sha256(acquisition)

    analysis_input = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-verified-analysis-input",
        "status": "COMPLETE_EXACT_360_ANALYSIS_INPUT_AFTER_AGGREGATE_VERIFICATION",
        "workflowRunId": expected_workflow_run_id,
        "scientificOrdinal": expected_scientific_ordinal,
        "caseCount": 360,
        "groupCount": 72,
        "analysisCellCount": 24,
        "statesPerGroup": 5,
        "primaryContrastCountPerCell": 4,
        "sourceAcquisitionStatus": acquisition["status"],
        "sourceAcquisitionContentSha256": acquisition["contentSha256"],
        "executionDesignCanonicalSha256": auth["executionDesignCanonicalSha256"],
        "resultOpeningBeforeAggregatePermitted": False,
        "epsilonSubstitutionPermitted": False,
        "cells": normalized_cells,
    }
    analysis_input["contentSha256"] = canonical_sha256(analysis_input)
    return acquisition, analysis_input
