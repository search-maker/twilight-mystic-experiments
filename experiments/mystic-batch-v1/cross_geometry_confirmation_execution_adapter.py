#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-selected-reference-confirmation-v1"
ADAPTER_ID = "mystic-cross-geometry-confirmation-execution-v1"
BASE_ADAPTER = Path(__file__).with_name("cross_geometry_adapter.py")
ALIS_REFERENCES = {405.0, 500.0, 550.0, 600.0}


class AdapterRefusal(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
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


def base_module():
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
        "batchId": STAGE_ID,
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
    }
    stale = {key: (proposal.get(key), expected) for key, expected in required.items() if proposal.get(key) != expected}
    if stale:
        raise AdapterRefusal(f"confirmation manifest header mismatch: {stale}")
    cases = proposal.get("cases")
    selected = proposal.get("selectedGeometryIds")
    geometries = proposal.get("geometries")
    if not isinstance(cases, list) or not 1 <= len(cases) <= 24:
        raise AdapterRefusal("confirmation manifest must contain 1..24 cases")
    if [case.get("ordinal") for case in cases] != list(range(1, len(cases) + 1)):
        raise AdapterRefusal("confirmation case ordinals changed")
    groups = {case.get("groupId") for case in cases}
    if not isinstance(selected, list) or set(selected) != groups:
        raise AdapterRefusal("selected geometry set changed")
    if not isinstance(geometries, list) or {item.get("geometryId") for item in geometries if isinstance(item, dict)} != groups:
        raise AdapterRefusal("geometry definitions changed")
    seeds = [case.get("seed") for case in cases]
    if len(set(seeds)) != len(seeds) or any(not isinstance(seed, int) or seed < 1 for seed in seeds):
        raise AdapterRefusal("confirmation seeds invalid")
    if any(case.get("method") not in {"reference-vroom", "alis"} for case in cases):
        raise AdapterRefusal("confirmation method changed")
    for case in cases:
        if case.get("method") == "alis" and float(case.get("alisSpectralImportanceSamplingNm", -1)) not in ALIS_REFERENCES:
            raise AdapterRefusal(f"unsupported ALIS reference: {case.get('caseId')}")
        if case.get("method") == "reference-vroom" and case.get("alisSpectralImportanceSamplingNm") is not None:
            raise AdapterRefusal(f"VROOM case contains ALIS reference: {case.get('caseId')}")


def validate_runtime(proposal: dict[str, Any], report: dict[str, Any]) -> None:
    runtime = proposal.get("runtime")
    if not isinstance(runtime, dict):
        raise AdapterRefusal("runtime missing")
    fields = ("uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "runtimeLockRawSha256")
    if report.get("schemaVersion") != 1 or report.get("stageId") != "mystic-batch-v1":
        raise AdapterRefusal("runtime report header mismatch")
    if report.get("scientificSolverExecuted") is not False or report.get("syntaxCheckExecuted") is not False:
        raise AdapterRefusal("runtime report must precede execution")
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
    proposal = load(proposal_path)
    report = load(runtime_report_path)
    validate_manifest(proposal)
    validate_runtime(proposal, report)
    base = base_module()
    case, geometry = base.resolve_case(proposal, case_id)
    inputs = base.normalized_inputs(proposal, case, geometry)
    if case.get("method") == "alis":
        reference = float(case["alisSpectralImportanceSamplingNm"])
        if reference not in ALIS_REFERENCES:
            raise AdapterRefusal("unsupported ALIS importance wavelength")
        inputs["alisSpectralImportanceSamplingNm"] = reference
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = base.render_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(text)
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_FOR_ONE_AUTHORIZED_HELD_OUT_CONFIRMATION_CASE",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "batchId": proposal["batchId"],
        "caseId": case_id,
        "groupId": case["groupId"],
        "method": case["method"],
        "block": case["block"],
        "purpose": case["purpose"],
        "alisSpectralImportanceSamplingNm": inputs.get("alisSpectralImportanceSamplingNm"),
        "proposalRawSha256": raw_sha256(proposal_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "baseAdapterRawSha256": raw_sha256(BASE_ADAPTER),
        "inputResolvedSha256": text_sha256(text),
        "inputs": inputs,
        "inputPath": str(input_path),
        "boundary": "held-out confirmation input prepared after runtime verification; one syntax check and at most one solver execution are delegated to the guarded executor",
    }
    (case_dir / "cross-geometry-confirmation-prepared.json").write_text(dump(prepared))
    return prepared
