#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-two-v1"
ADAPTER_ID = "mystic-cross-geometry-stage-two-execution-v1"
BASE_ADAPTER = Path(__file__).with_name("cross_geometry_adapter.py")
EXPECTED_GROUPS = {
    "g01-reference-bridge",
    "g04-mid-perpendicular",
    "g05-mid-opposite-low",
    "g06-late-opposite-high-aerosol",
}


class AdapterRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AdapterRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_base_adapter():
    spec = importlib.util.spec_from_file_location("cross_geometry_base_adapter", BASE_ADAPTER)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"cannot load base adapter: {BASE_ADAPTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_manifest(proposal: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": "cross-geometry-stage-two-screening-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
    }
    stale = {key: (proposal.get(key), expected) for key, expected in required.items() if proposal.get(key) != expected}
    if stale:
        raise AdapterRefusal(f"stage-two proposal header mismatch: {stale}")
    cases = proposal.get("cases")
    selected = proposal.get("selectedGeometryIds")
    if not isinstance(cases, list) or len(cases) != 16:
        raise AdapterRefusal("stage-two proposal must contain exactly 16 cases")
    if not isinstance(selected, list) or set(selected) != EXPECTED_GROUPS or len(selected) != 4:
        raise AdapterRefusal("stage-two selected geometry set changed")
    if {case.get("groupId") for case in cases if isinstance(case, dict)} != EXPECTED_GROUPS:
        raise AdapterRefusal("stage-two case geometry set changed")
    if {case.get("block") for case in cases if isinstance(case, dict)} != {3, 4}:
        raise AdapterRefusal("stage-two cases must be blocks 3 and 4")
    if {case.get("method") for case in cases if isinstance(case, dict)} != {"reference-vroom", "alis"}:
        raise AdapterRefusal("stage-two method set changed")
    seeds = [case.get("seed") for case in cases if isinstance(case, dict)]
    if len(seeds) != 16 or len(set(seeds)) != 16 or any(not isinstance(seed, int) or seed < 1 for seed in seeds):
        raise AdapterRefusal("stage-two seeds must be 16 unique positive integers")
    photons = [case.get("photonHistories") for case in cases if isinstance(case, dict)]
    if photons != [20_000_000] * 16:
        raise AdapterRefusal("stage-two photons changed")


def validate_runtime(proposal: dict[str, Any], report: dict[str, Any]) -> None:
    runtime = proposal.get("runtime")
    if not isinstance(runtime, dict):
        raise AdapterRefusal("proposal runtime missing")
    if report.get("schemaVersion") != 1 or report.get("stageId") != "mystic-batch-v1":
        raise AdapterRefusal("runtime report header mismatch")
    if report.get("scientificSolverExecuted") is not False or report.get("syntaxCheckExecuted") is not False:
        raise AdapterRefusal("runtime report must precede syntax and solver execution")
    fields = (
        "uvspecSha256",
        "uvspecHelpSha256",
        "libRadtranDataTreeSha256",
        "atmosphereSha256",
        "runtimeLockRawSha256",
    )
    stale = {field: (report.get(field), runtime.get(field)) for field in fields if report.get(field) != runtime.get(field)}
    if stale:
        raise AdapterRefusal(f"runtime identity mismatch: {stale}")


def prepare_case(
    proposal_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    proposal = load_json(proposal_path)
    report = load_json(runtime_report_path)
    validate_manifest(proposal)
    validate_runtime(proposal, report)
    base = load_base_adapter()
    case, geometry = base.resolve_case(proposal, case_id)
    inputs = base.normalized_inputs(proposal, case, geometry)
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = base.render_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(text)
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_FOR_ONE_AUTHORIZED_STAGE_TWO_CASE",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "batchId": proposal["batchId"],
        "caseId": case_id,
        "groupId": case["groupId"],
        "method": case["method"],
        "block": case["block"],
        "proposalRawSha256": raw_sha256(proposal_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "baseAdapterRawSha256": raw_sha256(BASE_ADAPTER),
        "inputResolvedSha256": text_sha256(text),
        "inputs": inputs,
        "inputPath": str(input_path),
        "boundary": "stage-two input prepared after runtime identity verification; syntax and solver are executed only by the guarded case executor",
    }
    (case_dir / "cross-geometry-stage-two-prepared.json").write_text(dump(prepared))
    return prepared
