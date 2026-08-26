#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

BATCH_ID = "jerusalem-tishrei-three-star-direct-mystic-v1"
EXPECTED_AOD550 = 0.22
AOD550_DIRECTIVE_PREFIX = "aerosol_set_tau_at_wvl 550 "
GENERIC_ADAPTER = Path(__file__).parents[1] / "mystic-batch-v1" / "cross_geometry_execution_adapter.py"


class TishreiAdapterRefusal(RuntimeError):
    pass


def load_generic_adapter():
    spec = importlib.util.spec_from_file_location("tishrei_generic_cross_geometry_execution_adapter", GENERIC_ADAPTER)
    if spec is None or spec.loader is None:
        raise TishreiAdapterRefusal(f"cannot load generic execution adapter: {GENERIC_ADAPTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_rendered_aod550_binding(text: str, expected_aod550: Any) -> None:
    try:
        aod = float(expected_aod550)
    except (TypeError, ValueError) as exc:
        raise TishreiAdapterRefusal(f"invalid normalized AOD550: {expected_aod550}") from exc
    if abs(aod - EXPECTED_AOD550) > 1e-12:
        raise TishreiAdapterRefusal(f"Tishrei AOD550 changed: expected {EXPECTED_AOD550}, got {aod}")
    expected = f"{AOD550_DIRECTIVE_PREFIX}{aod:.6f}"
    directives = [line.strip() for line in text.splitlines() if line.strip().startswith("aerosol_set_tau_at_wvl")]
    if directives != [expected]:
        raise TishreiAdapterRefusal(f"rendered AOD550 binding mismatch: expected exactly {expected!r}, got {directives!r}")


def prepare_case(
    proposal_path: Path,
    runtime_report_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    generic = load_generic_adapter()
    prepared = generic.prepare_case(
        proposal_path,
        runtime_report_path,
        case_id,
        data_dir,
        repository_root,
        output_dir,
    )
    if prepared.get("batchId") != BATCH_ID:
        raise TishreiAdapterRefusal(f"wrong batchId: {prepared.get('batchId')}")
    inputs = prepared.get("inputs")
    if not isinstance(inputs, dict):
        raise TishreiAdapterRefusal("normalized inputs missing from generic prepared record")
    input_path = Path(prepared.get("inputPath", ""))
    if not input_path.is_file():
        raise TishreiAdapterRefusal(f"resolved input missing: {input_path}")
    validate_rendered_aod550_binding(input_path.read_text(), inputs.get("aod550"))
    return prepared
