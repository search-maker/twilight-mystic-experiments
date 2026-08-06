#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("exploratory_terminal_public_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

core = _load("_exploratory_terminal_core")
analysis = _load("_exploratory_terminal_analysis")
inputs = _load("_exploratory_terminal_inputs")
builder = _load("_exploratory_terminal_build")

Refusal = core.Refusal
canonical_sha256 = core.canonical_sha256
raw_sha256 = core.raw_sha256
dump = core.dump
load = core.load
module = core.module
_photopic = core._photopic
_close = core._close
TRAINING_IDS = core.TRAINING_IDS
HOLDOUT_IDS = core.HOLDOUT_IDS
CONTINUATION_IDS = core.CONTINUATION_IDS
WAVE3_TRAINING_IDS = core.WAVE3_TRAINING_IDS
SOURCE_STAGE = core.SOURCE_STAGE
SOURCE_STATUS = core.SOURCE_STATUS
OUTPUT_STAGE = core.OUTPUT_STAGE
OUTPUT_STATUS = core.OUTPUT_STATUS
RESULT_STAGE = core.RESULT_STAGE
CIE = core.CIE
load_training_points = analysis.load_training_points
validate_source_dataset = inputs.validate_source_dataset
load_wave3_training_results = inputs.load_wave3_training_results
updated_record = builder.updated_record
build = builder.build

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--source-training-dataset", type=Path, required=True)
    parser.add_argument("--source-binding", type=Path, required=True)
    parser.add_argument("--terminal-analysis", type=Path, required=True)
    parser.add_argument("--wave3-training-results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = build(args.repository_root, args.source_training_dataset, args.source_binding, args.terminal_analysis, args.wave3_training_results_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(value), encoding="utf-8", newline="\n")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
