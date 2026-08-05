#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave1-ordinal10-execution-v4"
BASE_PATH = "experiments/tier1-precision-continuation-wave1-v3/execution_adapter.py"


def _base(root: Path):
    path = root / BASE_PATH
    spec = importlib.util.spec_from_file_location("wave1_v4_base_adapter", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"base adapter unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    return module


def prepare_case(manifest_path: Path, runtime_report_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_root: Path) -> dict[str, Any]:
    return _base(repository_root.resolve()).prepare_case(manifest_path, runtime_report_path, case_id, data_dir, repository_root, output_root)
