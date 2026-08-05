#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

STAGE_ID = "tier1-precision-continuation-wave1-ordinal11-execution-v5"
BASE_EXECUTOR = "experiments/tier1-precision-continuation-wave1-v2/case_executor.py"


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _base(repository_root: Path | None = None):
    root = (repository_root or Path(__file__).resolve().parents[2]).resolve()
    path = root / BASE_EXECUTOR
    spec = importlib.util.spec_from_file_location("wave1_v5_reviewed_case_executor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("reviewed v2 case executor unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    required = ("execute_case", "dump", "parse_spectrum", "verify_context")
    missing = [name for name in required if not callable(getattr(module, name, None))]
    if missing:
        raise RuntimeError(f"reviewed v2 executor API missing: {missing}")
    return module


def execute_case(manifest_path: Path, runtime_path: Path, adapter_path: Path, case_id: str, data_dir: Path, repository_root: Path, uvspec: Path, output_root: Path, timeout_seconds: int, allow_execution: bool, runner: Callable[..., dict[str, Any]] | None = None) -> dict[str, Any]:
    base = _base(repository_root)
    args = (manifest_path, runtime_path, adapter_path, case_id, data_dir, repository_root, uvspec, output_root, timeout_seconds, allow_execution)
    if runner is None:
        return base.execute_case(*args)
    return base.execute_case(*args, runner=runner)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--allow-execution", action="store_true")
    args = parser.parse_args()
    try:
        value = execute_case(args.manifest, args.runtime_report, args.adapter, args.case_id, args.data_dir, args.repository_root, args.uvspec, args.output_root, args.timeout_seconds, args.allow_execution)
        print(dump(value), end="")
        return 0
    except Exception as exc:
        print(dump({"stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
