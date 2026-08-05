#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave1-ordinal11-execution-v5"
BASE_ADAPTER = "experiments/tier1-precision-continuation-wave1-v2/execution_adapter.py"


class AdapterRefusal(RuntimeError):
    pass


def _base(repository_root: Path):
    path = repository_root.resolve() / BASE_ADAPTER
    spec = importlib.util.spec_from_file_location("wave1_v5_reviewed_base_adapter", path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal("reviewed v2 execution adapter unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.STAGE_ID = STAGE_ID
    return module


def prepare_case(manifest_path: Path, runtime_report_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_root: Path) -> dict[str, Any]:
    return _base(repository_root).prepare_case(manifest_path, runtime_report_path, case_id, data_dir, repository_root, output_root)
