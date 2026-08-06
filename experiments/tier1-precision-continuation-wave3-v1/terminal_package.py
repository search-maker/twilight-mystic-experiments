#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

BASE_PACKAGE_PATH = "experiments/tier1-precision-continuation-wave3-v1/package.py"
BINDING_PATH = "experiments/tier1-precision-continuation-wave3-v1/terminal_binding.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _modules(root: Path | None = None):
    repository_root = (root or Path(__file__).resolve().parents[2]).resolve()
    base = _load(repository_root / BASE_PACKAGE_PATH, "wave3_terminal_base_package")
    binding = _load(repository_root / BINDING_PATH, "wave3_terminal_binding")
    return repository_root, base, binding


def build_preregistration(
    source_analysis: dict[str, Any], source_analysis_path: Path, root: Path | None = None
) -> dict[str, Any]:
    repository_root, base, binding = _modules(root)
    binding.validate_path(source_analysis_path)
    value = base.build_preregistration(source_analysis, source_analysis_path, repository_root)
    if value.get("geometryIds") != list(binding.ACTIVE_GEOMETRY_IDS):
        raise binding.Refusal("generated wave-three geometry set drifted from terminal binding")
    if value.get("geometryCount") != 15 or value.get("caseCount") != 30:
        raise binding.Refusal("generated wave-three cardinality drifted from terminal binding")
    value["terminalSourceArtifactId"] = binding.SOURCE_ARTIFACT_ID
    value["terminalSourceArtifactDigest"] = binding.SOURCE_ARTIFACT_DIGEST
    value["terminalBindingStatus"] = "ORDINAL12_TERMINAL_SOURCE_EXACTLY_BOUND"
    value["preregistrationSha256"] = base.canonical_sha256(
        {key: item for key, item in value.items() if key != "preregistrationSha256"}
    )
    return value


def write_generated(source_analysis_path: Path, output_dir: Path, root: Path | None = None):
    repository_root, base, binding = _modules(root)
    source = base.load_json(source_analysis_path)
    preregistration = build_preregistration(source, source_analysis_path, repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    prereg_path = output_dir / "preregistration.json"
    prereg_path.write_text(base.dump(preregistration), encoding="utf-8", newline="\n")
    source_report = binding.validate_path(source_analysis_path)
    source_report_path = output_dir / "terminal-source-binding.json"
    source_report_path.write_text(base.dump(source_report), encoding="utf-8", newline="\n")
    report = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave3-terminal-generation-v1",
        "status": "EXACT_TERMINAL_WAVE3_PREPARATION_GENERATED_NOT_AUTHORIZED",
        "sourceAnalysisRawSha256": preregistration["sourceAnalysisRawSha256"],
        "sourceAnalysisSha256": preregistration["sourceAnalysisSha256"],
        "preregistrationRawSha256": base.raw_sha256(prereg_path),
        "preregistrationSha256": preregistration["preregistrationSha256"],
        "geometryIds": preregistration["geometryIds"],
        "geometryCount": preregistration["geometryCount"],
        "caseCount": preregistration["caseCount"],
        "authorizationAllocated": False,
        "dispatchEnabled": False,
        "scientificExecution": False,
    }
    report["reportSha256"] = base.canonical_sha256(report)
    (output_dir / "generation-report.json").write_text(
        base.dump(report), encoding="utf-8", newline="\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-analysis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = write_generated(args.source_analysis, args.output_dir)
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
