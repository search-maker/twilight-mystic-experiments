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
V1_VISIBLE_RENDERER = Path(__file__).with_name("reptran_visible_renderer_v1.py")
V1_VISIBLE_MOLECULAR_ABSORPTION = "reptran"


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


def load_module(path: Path, module_name: str = "cross_geometry_proposal_adapter"):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"cannot load reviewed module: {path}")
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


def render_current_v1_case(
    adapter: Any,
    inputs: dict[str, Any],
    data_dir: Path,
    repository_root: Path,
    case_dir: Path,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Render the authoritative V1 ALIS path with REPTRAN.

    The manifest/consumer contract is fail-closed: current V1 preparation must
    declare REPTRAN.  The historical reference-vroom branch is retained only as
    an explicit CRS diagnostic and cannot become the ALIS path implicitly.
    """

    if inputs.get("molecularAbsorption") != V1_VISIBLE_MOLECULAR_ABSORPTION:
        raise AdapterRefusal(
            "current V1 consumer requires molecularAbsorption='reptran'; "
            "historical CRS manifests are diagnostic evidence only"
        )

    method = inputs.get("method")
    if method == "alis":
        renderer = load_module(V1_VISIBLE_RENDERER, "reptran_visible_renderer_v1_consumer")
        try:
            text, renderer_proof = renderer.render_ground_site_input(
                inputs,
                data_dir.resolve(),
                repository_root.resolve(),
                case_dir.resolve(),
            )
        except Exception as exc:
            raise AdapterRefusal(f"reviewed REPTRAN renderer refused V1 ALIS input: {exc}") from exc
        lines = text.splitlines()
        if lines.count("mol_abs_param reptran") != 1 or "mol_abs_param crs" in lines:
            raise AdapterRefusal("authoritative V1 ALIS molecular-absorption wiring drift")
        proof = {
            "route": "authoritative-v1-visible-alis-reptran",
            "effectiveMolecularAbsorption": "reptran",
            "historicalCrsFallbackAllowed": False,
            "rendererProof": renderer_proof,
        }
        return text, dict(inputs), proof

    if method == "reference-vroom":
        diagnostic_inputs = dict(inputs)
        diagnostic_inputs["molecularAbsorption"] = "crs"
        text = adapter.render_input(
            diagnostic_inputs,
            data_dir.resolve(),
            repository_root.resolve(),
            case_dir.resolve(),
        )
        proof = {
            "route": "historical-reference-vroom-crs-diagnostic-only",
            "effectiveMolecularAbsorption": "crs",
            "historicalCrsFallbackAllowed": False,
        }
        return text, diagnostic_inputs, proof

    raise AdapterRefusal(f"unsupported execution method: {method}")


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
    text, effective_inputs, rendering_proof = render_current_v1_case(
        adapter,
        inputs,
        data_dir,
        repository_root,
        case_dir,
    )
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
        "visibleRendererRawSha256": raw_sha256(V1_VISIBLE_RENDERER),
        "inputResolvedSha256": text_sha256(text),
        "inputs": effective_inputs,
        "renderingProof": rendering_proof,
        "v1VisibleMolecularAbsorptionContract": V1_VISIBLE_MOLECULAR_ABSORPTION,
        "inputPath": str(input_path),
        "boundary": "input prepared after runtime identity verification; syntax and solver are executed only by the guarded case executor",
    }
    (case_dir / "cross-geometry-prepared.json").write_text(dump(prepared))
    return prepared
