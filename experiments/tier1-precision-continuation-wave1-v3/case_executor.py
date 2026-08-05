#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

STAGE_ID = "tier1-precision-continuation-wave1-ordinal9-execution-v3"
BASE_EXECUTOR = "experiments/tier1-precision-continuation-wave1-v2/case_executor.py"


def _base():
    root = Path(__file__).resolve().parents[2]
    path = root / BASE_EXECUTOR
    spec = importlib.util.spec_from_file_location("wave1_v3_reviewed_case_executor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("reviewed case executor unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    return module


def main() -> int:
    return _base().main()


if __name__ == "__main__":
    raise SystemExit(main())
