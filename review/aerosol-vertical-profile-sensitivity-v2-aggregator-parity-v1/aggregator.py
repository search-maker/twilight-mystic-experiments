from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v2"
EXPECTED_ORDINAL = 41
EXPECTED_EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2:numerical:41"
EXPECTED_AUTH_HEAD = "d5f5e4d9d19d7ede573fecae68565a92baabbec3"
EXPECTED_SEED_CANONICAL = "02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2"
EXPECTED_FOUR_ALIAS_TREE = "5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"
EXPECTED_CASE_COUNT = 360
EXPECTED_GROUP_COUNT = 72
EXPECTED_CELL_COUNT = 24
EXPECTED_STATES_PER_GROUP = 5
EXPECTED_CASE_ARTIFACT_PREFIX = "avps-v2-case-"

CONTRACT_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-execution-control-v1/execution-contract.review.json")
AUTH_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json")
ADAPTER_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py")
EXECUTOR_PATH = Path("review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py")
DERIVED_CHANNELS_PATH = Path("experiments/aerosol-family-challenge-v2-r8/derived_channels.py")

EXPECTED_BLOBS = {
    CONTRACT_PATH: "383db5619849cb499104826801ed82227e6a2ddf",
    AUTH_PATH: "dcfbd39081abe8e98604eedd48a1d934cea5483a",
    ADAPTER_PATH: "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
    EXECUTOR_PATH: "bb1e4276d6383127a6b7e820fc2568d87d5de4b0",
    DERIVED_CHANNELS_PATH: "ccfd04d4c21188966351f4257e92893d7ce340c7",
}

EXPECTED_PROFILE_SHA256 = {
    "opac-profile-continental-average": "ceed598f7681951cd0e6208b267beb5b41a52ab10311f37ce76f925700caff3d",
    "opac-profile-maritime-clean": "487b67bd7dbe89d12d032fdf2b33cab545e16a2e0697170648317f1a76362a67",
    "opac-profile-desert": "2b4d2e03c6ae3143d9bb05d2da49f57f75172dc1f24d34f7d4a4939bf9952fef",
    "opac-profile-arctic": "98f2fa5428c830764252fd0a2662b0f5c957fc027ffcb7bdc0a5e500dfd7d3d6",
    "opac-profile-antarctic": "ee063c6dca68cf9a31d8bb9d993f1fed5cb34c8bb056ac180c97171b5d6b4f19",
}

FIXED_RAW_MEMBERS = (
    "case.inp",
    "prepared.json",
    "runtime-report.json",
    "randomseed",
    "syntax-stdout.txt",
    "syntax-stderr.txt",
    "solver-stdout.txt",
    "solver-stderr.txt",
    "wavelength-grid-1nm.dat",
    "mc.flx.spc",
    "mc.flx.std.spc",
    "mc.rad.spc",
    "mc.rad.std.spc",
)


class AggregateRefusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AggregateRefusal(f"cannot import bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def find_one(root: Path, relative: str) -> Path:
    direct = root / relative
    if direct.is_file():
        return direct
    hits = [p for p in root.rglob(Path(relative).name) if p.is_file()]
    if len(hits) != 1:
        raise AggregateRefusal(f"{root}: expected exactly one {relative}, got {len(hits)}")
    return hits[0]


def load_and_validate_bound_state(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any], Any, Any]:
    for relative, expected in EXPECTED_BLOBS.items():
        path = repository_root / relative
        if not path.is_file() or git_blob_sha1(path) != expected:
            raise AggregateRefusal(f"bound source bytes changed: {relative}")
    contract = json.loads((repository_root / CONTRACT_PATH).read_text())
    if contract.get("status") != "REVIEW_ONLY_EXECUTION_CONTROL_FROZEN_DISPATCH_NOT_AUTHORIZED":
        raise AggregateRefusal("execution-control contract status drift")
    if contract.get("scientificOrdinal") != EXPECTED_ORDINAL or contract.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise AggregateRefusal("execution-control scientific identity drift")
    design = contract.get("caseDesign") or {}
    if (design.get("expectedCaseCount"), design.get("expectedGroupCount"), design.get("expectedAnalysisCellCount"), design.get("expectedStatesPerGroup")) != (EXPECTED_CASE_COUNT, EXPECTED_GROUP_COUNT, EXPECTED_CELL_COUNT, EXPECTED_STATES_PER_GROUP):
        raise AggregateRefusal("execution-control cardinality drift")
    if design.get("caseArtifactPrefix") != EXPECTED_CASE_ARTIFACT_PREFIX:
        raise AggregateRefusal("case artifact prefix drift")
    if (contract.get("transportRepresentation") or {}).get("speciesDirective") != "aerosol_species_file profiles/<state>.four-species.dat INSO WASO SOOT SUSO":
        raise AggregateRefusal("four-species transport contract drift")
    if (contract.get("runtimeIdentity") or {}).get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE:
        raise AggregateRefusal("four-alias runtime identity drift")
    auth = json.loads((repository_root / AUTH_PATH).read_text())
    if auth.get("scientificOrdinal") != EXPECTED_ORDINAL or auth.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise AggregateRefusal("authorization scientific identity drift")
    if auth.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise AggregateRefusal("authorization candidate-seed identity drift")
    if auth.get("exactFourSpeciesProfileSha256") != EXPECTED_PROFILE_SHA256:
        raise AggregateRefusal("authorization four-species profile identity drift")
    if auth.get("resultOpeningAuthorized") is not False or auth.get("productionAuthorized") is not False:
        raise AggregateRefusal("authorization result/production boundary drift")
    adapter = load_module("avps_v2_aggregate_adapter", repository_root / ADAPTER_PATH)
    derived = load_module("avps_v2_aggregate_derived", repository_root / DERIVED_CHANNELS_PATH)
    cases = adapter.authorized_case_universe(auth)
    if len(cases) != EXPECTED_CASE_COUNT or len({row["groupId"] for row in cases}) != EXPECTED_GROUP_COUNT:
        raise AggregateRefusal("authorized case/group universe drift")
    return contract, auth, adapter, derived


def validate_case_result(result: dict[str, Any], expected: dict[str, Any], *, workflow_run_id: int, derived: Any, artifact_root: Path) -> dict[str, Any]:
    static_keys = (
        "caseId", "groupId", "sunDepressionDeg", "geometryId", "geometryTag", "targetAltitudeDeg",
        "relativeAzimuthDeg", "observerElevationM", "aod550", "replicate", "stateId", "seed",
        "photonHistories", "numericalMethod",
    )
    for key in static_keys:
        if result.get(key) != expected.get(key):
            raise AggregateRefusal(f"{expected['caseId']}: result/authorization drift for {key}")
    if result.get("stageId") != STAGE or result.get("status") != "COMPLETED":
        raise AggregateRefusal(f"{expected['caseId']}: stage/status drift")
    if result.get("scientificOrdinal") != EXPECTED_ORDINAL or result.get("executionKey") != EXPECTED_EXECUTION_KEY:
        raise AggregateRefusal(f"{expected['caseId']}: scientific identity drift")
    if result.get("workflowRunId") != workflow_run_id or result.get("workflowRunAttempt") != 1:
        raise AggregateRefusal(f"{expected['caseId']}: workflow identity/attempt drift")
    if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
        raise AggregateRefusal(f"{expected['caseId']}: syntax/solver count drift")
    if any(result.get(k) is not False for k in ("retryPerformed", "resumePerformed", "githubRerun")):
        raise AggregateRefusal(f"{expected['caseId']}: retry/resume/rerun drift")
    if result.get("processGroupIsolation") is not True:
        raise AggregateRefusal(f"{expected['caseId']}: process-group isolation missing")
    if result.get("authorizationHead") != EXPECTED_AUTH_HEAD or result.get("candidateSeedCanonicalSha256") != EXPECTED_SEED_CANONICAL:
        raise AggregateRefusal(f"{expected['caseId']}: authorization/seed binding drift")
    if result.get("fourAliasDataTreeSha256") != EXPECTED_FOUR_ALIAS_TREE:
        raise AggregateRefusal(f"{expected['caseId']}: four-alias runtime identity drift")
    if result.get("resultOpeningAuthorized") is not False or result.get("productionAuthorized") is not False:
        raise AggregateRefusal(f"{expected['caseId']}: result/production boundary crossed")

    state = str(expected["stateId"])
    profile_rel = f"profiles/{state}.four-species.dat"
    expected_profile = EXPECTED_PROFILE_SHA256[state]
    if result.get("fourSpeciesProfileRelativePath") != profile_rel or result.get("fourSpeciesProfileSha256") != expected_profile:
        raise AggregateRefusal(f"{expected['caseId']}: explicit four-species profile identity drift")
    raw_hashes = result.get("rawMemberSha256ByRelativePath")
    required = set(FIXED_RAW_MEMBERS) | {profile_rel}
    if not isinstance(raw_hashes, dict) or set(raw_hashes) != required:
        raise AggregateRefusal(f"{expected['caseId']}: raw-member hash map drift")
    for rel in sorted(required):
        path = find_one(artifact_root, rel)
        if sha256_file(path) != raw_hashes[rel]:
            raise AggregateRefusal(f"{expected['caseId']}: raw-member hash mismatch: {rel}")
    if raw_hashes[profile_rel] != expected_profile:
        raise AggregateRefusal(f"{expected['caseId']}: persisted four-species profile hash mismatch")
    inp = find_one(artifact_root, "case.inp").read_text()
    directive = f"aerosol_species_file profiles/{state}.four-species.dat INSO WASO SOOT SUSO"
    if directive not in inp:
        raise AggregateRefusal(f"{expected['caseId']}: explicit four-species transport directive missing")
    if any(line.startswith("aerosol_file ") for line in inp.splitlines()):
        raise AggregateRefusal(f"{expected['caseId']}: legacy aerosol_file transport present")

    stored = result.get("contentSha256")
    check = dict(result)
    check.pop("contentSha256", None)
    if stored != canonical_sha256(check):
        raise AggregateRefusal(f"{expected['caseId']}: case-result canonical hash mismatch")
    wavelengths, radiance = parse_spectrum(find_one(artifact_root, "mc.rad.spc"))
    std_wavelengths, std_radiance = parse_spectrum(find_one(artifact_root, "mc.rad.std.spc"))
    derived.validate_raw_grid(wavelengths, radiance)
    derived.validate_raw_grid(std_wavelengths, std_radiance)
    if len(wavelengths) != 8001 or len(std_wavelengths) != 8001:
        raise AggregateRefusal(f"{expected['caseId']}: raw spectrum node-count drift")
    if any(abs(a - b) > derived.RAW_POINT_TOLERANCE_NM for a, b in zip(wavelengths, std_wavelengths)):
        raise AggregateRefusal(f"{expected['caseId']}: radiance/std wavelength grids differ")
    channels = derived.derive_channels(wavelengths, radiance)
    if result.get("channels") != channels:
        raise AggregateRefusal(f"{expected['caseId']}: derived-channel recomputation mismatch")
    return channels


def cell_id(case: dict[str, Any]) -> str:
    return f"dep{float(case['sunDepressionDeg']):.1f}|aod{float(case['aod550']):.2f}|{case['geometryId']}"


def aggregate(repository_root: Path, artifact_root: Path, artifact_metadata_path: Path, *, workflow_run_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    if workflow_run_id <= 0:
        raise AggregateRefusal("positive workflow run ID required")
    contract, auth, adapter, derived = load_and_validate_bound_state(repository_root)
    expected_cases = {row["caseId"]: row for row in adapter.authorized_case_universe(auth)}
    metadata = json.loads(artifact_metadata_path.read_text())
    rows = metadata.get("artifacts", []) if isinstance(metadata, dict) else metadata
    if not isinstance(rows, list):
        raise AggregateRefusal("artifact metadata must contain a list")
    case_meta = [row for row in rows if str(row.get("name") or "").startswith(EXPECTED_CASE_ARTIFACT_PREFIX)]
    if len(case_meta) != EXPECTED_CASE_COUNT or len({str(row.get("name") or "") for row in case_meta}) != EXPECTED_CASE_COUNT:
        raise AggregateRefusal("exact unique 360-case artifact universe required")

    records: dict[str, dict[str, Any]] = {}
    acquisition_rows: list[dict[str, Any]] = []
    for meta in sorted(case_meta, key=lambda row: str(row.get("name") or "")):
        name = str(meta.get("name") or "")
        case_id = name[len(EXPECTED_CASE_ARTIFACT_PREFIX):]
        expected = expected_cases.get(case_id)
        if expected is None:
            raise AggregateRefusal(f"unexpected case artifact: {name}")
        root = artifact_root / name
        result_path = find_one(root, "case-result.json")
        result = json.loads(result_path.read_text())
        channels = validate_case_result(result, expected, workflow_run_id=workflow_run_id, derived=derived, artifact_root=root)
        records[case_id] = {"case": expected, "channels": channels}
        acquisition_rows.append({
            "caseId": case_id,
            "artifactId": meta.get("id"),
            "artifactName": name,
            "artifactDigest": meta.get("digest"),
            "artifactSizeBytes": meta.get("size_in_bytes"),
            "caseResultRawSha256": sha256_file(result_path),
            "caseResultContentSha256": result.get("contentSha256"),
            "fourSpeciesProfileSha256": result.get("fourSpeciesProfileSha256"),
            "rawMemberSha256ByRelativePath": result.get("rawMemberSha256ByRelativePath"),
        })
    if set(records) != set(expected_cases):
        raise AggregateRefusal("artifact universe does not equal exact authorized case universe")

    cells: dict[str, dict[str, Any]] = {}
    for row in records.values():
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
            raise AggregateRefusal(f"{cid}: duplicate state within replicate {rep}")
        rep_row["recordsByState"][case["stateId"]] = row["channels"]
    if len(cells) != EXPECTED_CELL_COUNT:
        raise AggregateRefusal(f"expected 24 analysis cells, got {len(cells)}")
    expected_states = set(EXPECTED_PROFILE_SHA256)
    normalized: list[dict[str, Any]] = []
    for cid in sorted(cells):
        cell = cells[cid]
        if set(cell["replicates"]) != {"1", "2", "3"}:
            raise AggregateRefusal(f"{cid}: exact replicates 1,2,3 required")
        reps = [cell["replicates"][str(i)] for i in (1, 2, 3)]
        if any(set(rep["recordsByState"]) != expected_states for rep in reps):
            raise AggregateRefusal(f"{cid}: exact five-state replicate universe required")
        normalized.append({**{k: v for k, v in cell.items() if k != "replicates"}, "replicates": reps})

    acquisition = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-aggregate-verification",
        "status": "COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE_RESULTS_STILL_CLOSED",
        "workflowRunId": workflow_run_id,
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "caseCount": EXPECTED_CASE_COUNT,
        "groupCount": EXPECTED_GROUP_COUNT,
        "analysisCellCount": EXPECTED_CELL_COUNT,
        "statesPerGroup": EXPECTED_STATES_PER_GROUP,
        "sourceArtifactCount": EXPECTED_CASE_COUNT,
        "authorizationHead": EXPECTED_AUTH_HEAD,
        "candidateSeedCanonicalSha256": EXPECTED_SEED_CANONICAL,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE,
        "resultOpeningAuthorized": False,
        "partialResultInterpretationPermitted": False,
        "taylorOrJerusalemScoringPermitted": False,
        "artifacts": acquisition_rows,
    }
    acquisition["contentSha256"] = canonical_sha256(acquisition)
    analysis_input = {
        "schemaVersion": 1,
        "stageId": f"{STAGE}-verified-analysis-input",
        "status": "COMPLETE_EXACT_360_ANALYSIS_INPUT_RESULTS_STILL_CLOSED",
        "workflowRunId": workflow_run_id,
        "scientificOrdinal": EXPECTED_ORDINAL,
        "caseCount": EXPECTED_CASE_COUNT,
        "groupCount": EXPECTED_GROUP_COUNT,
        "analysisCellCount": EXPECTED_CELL_COUNT,
        "statesPerGroup": EXPECTED_STATES_PER_GROUP,
        "primaryContrastCountPerCell": 4,
        "sourceAcquisitionContentSha256": acquisition["contentSha256"],
        "resultOpeningAuthorized": False,
        "epsilonSubstitutionPermitted": False,
        "pValuesPermitted": False,
        "confidenceIntervalsPermitted": False,
        "taylorOrJerusalemScoringPermitted": False,
        "cells": normalized,
    }
    analysis_input["contentSha256"] = canonical_sha256(analysis_input)
    return acquisition, analysis_input


def review_summary(repository_root: Path) -> dict[str, Any]:
    contract, auth, adapter, _ = load_and_validate_bound_state(repository_root)
    cases = adapter.authorized_case_universe(auth)
    return {
        "status": "REVIEW_ONLY_V2_AGGREGATOR_PARITY_PASS_NO_SOLVER_RESULTS_CLOSED",
        "scientificOrdinal": EXPECTED_ORDINAL,
        "executionKey": EXPECTED_EXECUTION_KEY,
        "authorizationHead": EXPECTED_AUTH_HEAD,
        "caseCount": len(cases),
        "groupCount": len({row["groupId"] for row in cases}),
        "analysisCellCount": contract["caseDesign"]["expectedAnalysisCellCount"],
        "statesPerGroup": EXPECTED_STATES_PER_GROUP,
        "caseArtifactPrefix": EXPECTED_CASE_ARTIFACT_PREFIX,
        "explicitFourSpeciesProfileRequiredPerCase": True,
        "fourAliasDataTreeSha256": EXPECTED_FOUR_ALIAS_TREE,
        "derivedChannelsMustRecomputeFromRawSpectrum": True,
        "partialResultsMayBeInterpreted": False,
        "resultOpeningAuthorized": False,
        "solverExecutionPerformed": False,
        "dispatchCreated": False,
        "productionAuthorized": False,
        "nextRequiredStage": "implement and solver-free review the attempt-1 AVPS v2 science workflow and zero-runtime dispatch publisher bound to the reviewed executor and aggregator bytes",
    }


if __name__ == "__main__":
    print(json.dumps(review_summary(Path.cwd()), indent=2, sort_keys=True))
