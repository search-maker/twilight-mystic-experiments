#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

STAGE_ID = "tier1-precision-continuation-wave1-ordinal10-execution-v4"
BASE_PATH = Path(__file__).resolve().parents[1] / "tier1-precision-continuation-wave1-v3" / "case_executor.py"


def _base():
    spec = importlib.util.spec_from_file_location("wave1_v4_base_executor", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"base executor unavailable: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    return module


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
    base = _base()
    try:
        value = base.execute_case(args.manifest, args.runtime_report, args.adapter, args.case_id, args.data_dir, args.repository_root, args.uvspec, args.output_root, args.timeout_seconds, args.allow_execution)
        print(base.dump(value), end="")
        return 0
    except Exception as exc:
        print(base.dump({"stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
