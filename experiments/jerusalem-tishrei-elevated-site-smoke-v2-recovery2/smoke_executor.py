#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2-recovery2"
BASE_EXECUTOR = Path(__file__).parents[1] / "jerusalem-tishrei-elevated-site-smoke-v2" / "smoke_executor.py"
TRANSPORT_GRID_NM = [380.0, 470.0, 480.0, 490.0, 500.0, 510.0, 520.0, 530.0, 540.0, 560.0, 580.0, 590.0, 600.0, 610.0, 640.0, 660.0, 780.0]
COMPARISON_NODES_NM = [470.0, 480.0, 490.0, 500.0, 510.0, 520.0, 530.0, 540.0, 560.0, 580.0, 590.0, 600.0, 610.0, 640.0, 660.0]


class Recovery2Error(RuntimeError):
    pass


def load_base_executor():
    spec = importlib.util.spec_from_file_location("tishrei_smoke_v2_base_executor", BASE_EXECUTOR)
    if spec is None or spec.loader is None:
        raise Recovery2Error(f"cannot load base smoke executor: {BASE_EXECUTOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_full_8001_grid(wavelengths: list[float], path: Path) -> None:
    if len(wavelengths) != 8001:
        raise Recovery2Error(f"full smoke output row count changed in {path}: {len(wavelengths)}")
    if abs(wavelengths[0] - 380.0) > 1e-7 or abs(wavelengths[-1] - 780.0) > 1e-7:
        raise Recovery2Error(f"full smoke output endpoints changed in {path}")
    for index, actual in enumerate(wavelengths):
        if not math.isfinite(actual):
            raise Recovery2Error(f"non-finite wavelength at index {index} in {path}")
        expected = 380.0 + 0.05 * index
        if abs(actual - expected) > 5e-5:
            raise Recovery2Error(f"full smoke output grid mismatch at {index}: {actual} vs {expected}")


def _require_nodes(wavelengths: list[float], required: list[float], label: str, path: Path) -> None:
    present = set(round(value, 7) for value in wavelengths)
    missing = [node for node in required if round(node, 7) not in present]
    if missing:
        raise Recovery2Error(f"{label} nodes missing from full VROOM output {path}: {missing}")


def validate_grid(method: str, wavelengths: list[float], path: Path) -> dict[str, Any]:
    """Structural-only correction: VROOM writes a full 8001-row spectrum.

    The 17-node wavelength_grid_file controls VROOM transport/reference sampling; it
    does not imply a 17-row mc.rad.spc.  This matches the existing
    experiments/reference-vroom-v1/runner.py parser, which scans the full spectrum
    and selects the frozen diagnostic wavelengths.
    """
    _require_full_8001_grid(wavelengths, path)
    common = {
        "nodeCount": 8001,
        "startNm": 380.0,
        "stopNm": 780.0,
        "stepNm": 0.05,
    }
    if method == "alis":
        return {**common, "gridMode": "full-alis-8001-node"}
    if method == "reference-vroom":
        _require_nodes(wavelengths, TRANSPORT_GRID_NM, "transport-grid", path)
        _require_nodes(wavelengths, COMPARISON_NODES_NM, "comparison", path)
        return {
            **common,
            "gridMode": "full-vroom-output-8001-node",
            "transportGridNodeCount": len(TRANSPORT_GRID_NM),
            "comparisonNodeCount": len(COMPARISON_NODES_NM),
            "transportGridNodesPresent": True,
            "comparisonNodesPresent": True,
            "scientificRole": "sparse diagnostic-node cross-check only; full-channel derivation remains prohibited",
        }
    raise Recovery2Error(f"unknown smoke method: {method}")


def execute(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    base = load_base_executor()
    base.validate_grid = validate_grid
    result, ok = base.execute(
        args.smoke_manifest,
        args.runtime_report,
        args.adapter,
        args.case_id,
        args.data_dir,
        args.repository_root,
        args.uvspec,
        args.output_root,
        args.timeout_seconds,
        args.allow_infrastructure_smoke,
    )
    result["recoveryStageId"] = STAGE_ID
    result["vroomStructuralCorrectionOnly"] = True
    result["scientificUseProhibited"] = True
    case_dir = args.output_root / args.case_id
    (case_dir / "smoke-case-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result, ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--smoke-manifest", type=Path, required=True)
    p.add_argument("--runtime-report", type=Path, required=True)
    p.add_argument("--adapter", type=Path, required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--repository-root", type=Path, required=True)
    p.add_argument("--uvspec", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--timeout-seconds", type=int, required=True)
    p.add_argument("--allow-infrastructure-smoke", action="store_true")
    args = p.parse_args()
    try:
        result, ok = execute(args)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if ok else 2
    except Exception as exc:
        report = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "INFRASTRUCTURE_RECOVERY2_SMOKE_REFUSED_OR_FAILED",
            "infrastructureOnly": True,
            "scientificUseProhibited": True,
            "reason": str(exc),
        }
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
