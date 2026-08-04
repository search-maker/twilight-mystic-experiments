#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-stage-three-v1"
ADAPTER_ID = "mystic-cross-geometry-stage-three-execution-v1"
BASE_ADAPTER = Path(__file__).with_name("cross_geometry_adapter.py")
EXPECTED_GROUPS = {"g01-reference-bridge", "g05-mid-opposite-low", "g06-late-opposite-high-aerosol"}
ALIS_CANDIDATES = {405.0, 500.0, 550.0, 600.0}


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
        "batchId": "cross-geometry-stage-three-diagnostics-v1",
        "mode": "scientific-proposal",
        "proposalOnly": True,
        "scientificExecution": False,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "adapterId": "mystic-cross-geometry-v1",
    }
    stale = {key: (proposal.get(key), expected) for key, expected in required.items() if proposal.get(key) != expected}
    if stale:
        raise AdapterRefusal(f"Stage-3 proposal header mismatch: {stale}")
    cases = proposal.get("cases")
    if not isinstance(cases, list) or len(cases) != 24:
        raise AdapterRefusal("Stage-3 proposal must contain exactly 24 cases")
    if {case.get("groupId") for case in cases if isinstance(case, dict)} != EXPECTED_GROUPS:
        raise AdapterRefusal("Stage-3 geometry set changed")
    seeds = [case.get("seed") for case in cases if isinstance(case, dict)]
    if len(seeds) != 24 or len(set(seeds)) != 24:
        raise AdapterRefusal("Stage-3 seeds must be unique")
    for case in cases:
        if not isinstance(case, dict) or case.get("photonHistories") != 20_000_000:
            raise AdapterRefusal("Stage-3 photon accounting changed")
        if case.get("method") == "alis":
            value = case.get("alisSpectralImportanceSamplingNm")
            if not isinstance(value, (int, float)) or float(value) not in ALIS_CANDIDATES:
                raise AdapterRefusal("ALIS case has an unauthorized importance wavelength")
        elif case.get("method") == "reference-vroom":
            if "alisSpectralImportanceSamplingNm" in case:
                raise AdapterRefusal("VROOM case must not specify an ALIS importance wavelength")
        else:
            raise AdapterRefusal("unsupported Stage-3 method")


def validate_runtime(proposal: dict[str, Any], report: dict[str, Any]) -> None:
    runtime = proposal.get("runtime")
    if not isinstance(runtime, dict):
        raise AdapterRefusal("proposal runtime missing")
    required = {
        "schemaVersion": 1,
        "stageId": "mystic-batch-v1",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
    }
    stale = {key: (report.get(key), expected) for key, expected in required.items() if report.get(key) != expected}
    if stale:
        raise AdapterRefusal(f"runtime report header mismatch: {stale}")
    for field in ("uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "runtimeLockRawSha256"):
        if report.get(field) != runtime.get(field):
            raise AdapterRefusal(f"runtime identity mismatch: {field}")


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

    rendered_manifest = json.loads(json.dumps(proposal))
    if case["method"] == "alis":
        rendered_manifest["frozenInputs"]["alisSpectralImportanceSamplingNm"] = float(case["alisSpectralImportanceSamplingNm"])
    else:
        rendered_manifest["frozenInputs"]["alisSpectralImportanceSamplingNm"] = float(
            proposal["frozenInputs"]["defaultAlisSpectralImportanceSamplingNm"]
        )
    inputs = base.normalized_inputs(rendered_manifest, case, geometry)
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = base.render_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(text)
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_FOR_ONE_AUTHORIZED_STAGE_THREE_CASE",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "batchId": proposal["batchId"],
        "caseId": case_id,
        "groupId": case["groupId"],
        "method": case["method"],
        "block": case["block"],
        "alisSpectralImportanceSamplingNm": case.get("alisSpectralImportanceSamplingNm"),
        "proposalRawSha256": raw_sha256(proposal_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "baseAdapterRawSha256": raw_sha256(BASE_ADAPTER),
        "inputResolvedSha256": text_sha256(text),
        "inputs": inputs,
        "inputPath": str(input_path),
        "boundary": "Stage-3 input prepared after exact runtime verification; syntax and solver may run only through the guarded case executor.",
    }
    (case_dir / "cross-geometry-stage-three-prepared.json").write_text(dump(prepared))
    return prepared
