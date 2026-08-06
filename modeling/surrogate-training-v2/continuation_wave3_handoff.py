#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

FINAL_HANDOFF_PATH = "modeling/surrogate-training-v2/continuation_final_handoff.py"
WAVE3_ANALYSIS_STAGE = "tier1-precision-continuation-wave3-analysis-v1"


class Wave3HandoffRefusal(RuntimeError):
    pass


def _final(repository_root: Path):
    path = repository_root.resolve() / FINAL_HANDOFF_PATH
    spec = importlib.util.spec_from_file_location(
        "surrogate_training_v2_wave3_final_handoff", path
    )
    if spec is None or spec.loader is None:
        raise Wave3HandoffRefusal("authoritative final continuation handoff unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_load_base = module.load_base

    def load_base(root: Path):
        base = original_load_base(root)
        base.FINAL_ANALYSIS_STAGE = WAVE3_ANALYSIS_STAGE
        return base

    module.load_base = load_base
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
    final = _final(repository_root)
    return final.build(
        repository_root=repository_root,
        source_dataset_path=source_dataset_path,
        source_audit_path=source_audit_path,
        continuation_results_root=continuation_results_root,
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
        final = _final(args.repository_root)
        print(final.dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
