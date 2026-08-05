#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "tier1-precision-continuation-wave1-v4" / "matrix_output.py"


def _base():
    spec = importlib.util.spec_from_file_location("wave1_v5_matrix_output", BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("reviewed matrix output module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matrix_value(manifest):
    return _base().matrix_value(manifest)


def append_github_output(manifest_path, output_path):
    return _base().append_github_output(manifest_path, output_path)


def main() -> int:
    return _base().main()


if __name__ == "__main__":
    raise SystemExit(main())
