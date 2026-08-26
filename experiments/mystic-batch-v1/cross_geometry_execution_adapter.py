#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
ADAPTER_ID = "mystic-cross-geometry-execution-v1"
PROPOSAL_ADAPTER = Path(__file__).with_name("cross_geometry_adapter.py")
AOD550_DIRECTIVE_PREFIX = "aerosol_set_tau_at_wvl 550 "


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


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_proposal_adapter", path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"cannot load proposal adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def validate_rendered_aod550_binding(text: str, expected_aod550: Any) -> None:
    try:
        aod = float(expected_aod550)
    except (TypeError, ValueError) as exc:
        raise AdapterRefusal(f"invalid normalized AOD550: {expected_aod550}") from exc
    expected = f"{AOD550_DIRECTIVE_PREFIX}{aod:.6f}"
    directives = [line.strip() for line in text.splitlines() if line.strip().startswith("aerosol_set_tau_at_wvl")]
    if directives != [expected]:
        raise AdapterRefusal(f"rendered AOD550 binding mismatch: expected exactly {expected!r}, got {directives!r}")


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
    validate_runtime(proposal, report)
    adapter = load_module(PROPOSAL_ADAPTER)
    adapter.validate_manifest(proposal)
    case, geometry = adapter.resolve_case(proposal, case_id)
    inputs = adapter.normalized_inputs(proposal, case, geometry)
    case_dir = output_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    text = adapter.render_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())
    validate_rendered_aod550_binding(text, inputs.get("aod550"))
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(text)
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_FOR_ONE_AUTHORIZED_CASE",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "batchId": proposal["batchId"],
        "caseId": case_id,
        "groupId": case["groupId"],
        "method": case["method"],
        "block": case["block"],
        "proposalRawSha256": raw_sha256(proposal_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "proposalAdapterRawSha256": raw_sha256(PROPOSAL_ADAPTER),
        "inputResolvedSha256": text_sha256(text),
        "inputs": inputs,
        "inputPath": str(input_path),
        "boundary": "input prepared after runtime identity verification and exact AOD550 directive binding; syntax and solver are executed only by the guarded case executor",
    }
    (case_dir / "cross-geometry-prepared.json").write_text(dump(prepared))
    return prepared
