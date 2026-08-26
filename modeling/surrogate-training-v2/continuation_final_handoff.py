#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE_PATH = "modeling/surrogate-training-v2/continuation_handoff.py"
WAVE3_RESULT_STAGE = "tier1-precision-continuation-wave3-ordinal13-execution-v1"


class FinalHandoffRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_base(repository_root: Path):
    path = repository_root.resolve() / BASE_PATH
    spec = importlib.util.spec_from_file_location(
        "surrogate_training_v2_final_continuation_handoff_base", path
    )
    if spec is None or spec.loader is None:
        raise FinalHandoffRefusal("continuation handoff base unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ALLOWED_RESULT_STAGES = set(module.ALLOWED_RESULT_STAGES) | {
        WAVE3_RESULT_STAGE
    }
    return module


def build(
    *,
    repository_root: Path,
    source_dataset_path: Path,
    source_audit_path: Path,
    continuation_results_root: Path,
    final_analysis_path: Path,
    reference_anchors_path: Path,
    final_manifest_path: Path,
    final_aggregate_path: Path,
    final_audit_path: Path,
    exact_main_sha: str,
    output_dir: Path,
) -> dict[str, Path]:
    base = load_base(repository_root)
    with tempfile.TemporaryDirectory() as raw:
        empty = Path(raw) / "empty-results"
        empty.mkdir()
        return base.build(
            source_dataset_path=source_dataset_path,
            source_audit_path=source_audit_path,
            wave1_results_root=continuation_results_root,
            wave2_results_root=empty,
            final_analysis_path=final_analysis_path,
            reference_anchors_path=reference_anchors_path,
            final_manifest_path=final_manifest_path,
            final_aggregate_path=final_aggregate_path,
            final_audit_path=final_audit_path,
            exact_main_sha=exact_main_sha,
            output_dir=output_dir,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--source-dataset", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--continuation-results-root", type=Path, required=True)
    parser.add_argument("--final-analysis", type=Path, required=True)
    parser.add_argument("--reference-anchors", type=Path, required=True)
    parser.add_argument("--final-manifest", type=Path, required=True)
    parser.add_argument("--final-aggregate", type=Path, required=True)
    parser.add_argument("--final-audit", type=Path, required=True)
    parser.add_argument("--exact-main-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(
            repository_root=args.repository_root,
            source_dataset_path=args.source_dataset,
            source_audit_path=args.source_audit,
            continuation_results_root=args.continuation_results_root,
            final_analysis_path=args.final_analysis,
            reference_anchors_path=args.reference_anchors,
            final_manifest_path=args.final_manifest,
            final_aggregate_path=args.final_aggregate,
            final_audit_path=args.final_audit,
            exact_main_sha=args.exact_main_sha,
            output_dir=args.output_dir,
        )
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
