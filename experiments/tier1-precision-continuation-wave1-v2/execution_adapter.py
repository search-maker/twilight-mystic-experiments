#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave1-ordinal8-execution-v2"
BASE_ADAPTER = "experiments/mystic-batch-v1/cross_geometry_adapter.py"
PILOT_MANIFEST = "experiments/mystic-batch-v1/manifest.cross-geometry-pilot.proposal.json"


class AdapterRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module(path: Path):
    spec = importlib.util.spec_from_file_location("wave1_base_adapter", path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal("base adapter unavailable")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def prepare_case(manifest_path: Path, runtime_report_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_root: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runtime = json.loads(runtime_report_path.read_text(encoding="utf-8"))
    if manifest.get("stageId") != STAGE_ID or manifest.get("caseCount") != 40:
        raise AdapterRefusal("execution manifest changed")
    required_runtime = tuple(manifest.get("runtime", {}))
    if any(runtime.get(key) != manifest["runtime"].get(key) for key in required_runtime):
        raise AdapterRefusal("runtime hash drift")
    matches = [case for case in manifest["cases"] if case.get("caseId") == case_id]
    if len(matches) != 1:
        raise AdapterRefusal("case must occur exactly once")
    case = matches[0]
    if case.get("block") not in (3, 4) or case.get("role") not in ("surrogate-training", "internal-holdout"):
        raise AdapterRefusal("case contract changed")
    pilot_path = repository_root / PILOT_MANIFEST
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    frozen = pilot.get("frozenInputs")
    if not isinstance(frozen, dict):
        raise AdapterRefusal("frozen solver inputs unavailable")
    synthetic_case = dict(case)
    synthetic_case["method"] = "alis"
    synthetic_case["ordinal"] = case["caseOrdinal"]
    geometry = dict(case["geometry"])
    proposal = {"frozenInputs": frozen, "cases": [synthetic_case], "geometries": [geometry]}
    base = _module(repository_root / BASE_ADAPTER)
    inputs = base.normalized_inputs(proposal, synthetic_case, geometry)
    inputs["alisSpectralImportanceSamplingNm"] = float(case["alisSpectralImportanceSamplingNm"])
    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    rendered = base.render_input(inputs, data_dir.resolve(), repository_root.resolve(), case_dir.resolve())
    if rendered.count("mc_randomseed ") != 1 or rendered.count("mc_photons ") != 1:
        raise AdapterRefusal("rendered execution identity is ambiguous")
    if f"mc_randomseed {case['seed']}" not in rendered or f"mc_photons {case['photonHistories']}" not in rendered:
        raise AdapterRefusal("rendered seed or photon budget changed")
    input_path = case_dir / "input-resolved.txt"
    input_path.write_text(rendered, encoding="utf-8", newline="\n")
    prepared = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARED_FOR_EXACTLY_ONE_AUTHORIZED_CASE",
        "caseId": case_id,
        "groupId": case["groupId"],
        "block": case["block"],
        "role": case["role"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "manifestRawSha256": raw_sha256(manifest_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "pilotManifestRawSha256": raw_sha256(pilot_path),
        "baseAdapterRawSha256": raw_sha256(repository_root / BASE_ADAPTER),
        "inputResolvedSha256": hashlib.sha256(rendered.encode()).hexdigest(),
        "inputPath": str(input_path),
        "fittingSurfaceExposed": False,
        "boundary": "input rendering only; no syntax check or solver execution",
    }
    (case_dir / "prepared.json").write_text(dump(prepared), encoding="utf-8", newline="\n")
    return prepared