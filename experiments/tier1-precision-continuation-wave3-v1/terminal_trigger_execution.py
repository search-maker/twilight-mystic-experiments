#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

TRIGGER_PATH = "experiments/tier1-precision-continuation-wave3-v1/trigger_execution.py"
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
    trigger = _load(repository_root / TRIGGER_PATH, "wave3_terminal_trigger_base")
    binding = _load(repository_root / BINDING_PATH, "wave3_terminal_trigger_binding")
    return repository_root, trigger, binding


def terminal_binding_value(report: dict[str, Any], binding) -> dict[str, Any]:
    return {
        "status": report["status"],
        "sourceRunId": binding.SOURCE_RUN_ID,
        "sourceRunAttempt": binding.SOURCE_RUN_ATTEMPT,
        "sourceHeadSha": binding.SOURCE_HEAD_SHA,
        "sourceArtifactId": binding.SOURCE_ARTIFACT_ID,
        "sourceArtifactName": binding.SOURCE_ARTIFACT_NAME,
        "sourceArtifactDigest": binding.SOURCE_ARTIFACT_DIGEST,
        "sourceAnalysisRawSha256": binding.SOURCE_ANALYSIS_RAW_SHA256,
        "sourceAnalysisSha256": binding.SOURCE_ANALYSIS_SHA256,
        "geometryIds": list(binding.ACTIVE_GEOMETRY_IDS),
        "geometryCount": len(binding.ACTIVE_GEOMETRY_IDS),
        "caseCount": 2 * len(binding.ACTIVE_GEOMETRY_IDS),
        "blocks": [7, 8],
        "bindingReportSha256": report["reportSha256"],
    }


def validate_terminal_manifest(
    manifest: dict[str, Any], report: dict[str, Any] | None = None, root: Path | None = None
) -> None:
    _, trigger, binding = _modules(root)
    trigger.validate_manifest(manifest)
    expected_scope = {
        "geometryIds": list(binding.ACTIVE_GEOMETRY_IDS),
        "geometryCount": len(binding.ACTIVE_GEOMETRY_IDS),
        "caseCount": 2 * len(binding.ACTIVE_GEOMETRY_IDS),
        "blocks": [7, 8],
        "wave": 3,
        "eventName": "push",
        "triggerBranch": trigger.TRIGGER_BRANCH,
        "runAttempt": 1,
        "authorizationOrdinal": 13,
        "executionKey": "twilight-surrogate-tier-1-v1:numerical:13",
        "githubRerunAllowed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    stale = {
        key: (manifest.get(key), expected)
        for key, expected in expected_scope.items()
        if manifest.get(key) != expected
    }
    if stale:
        raise binding.Refusal(f"terminal-bound ordinal-13 manifest scope changed: {stale}")
    cases = manifest.get("cases")
    if (
        not isinstance(cases, list)
        or len(cases) != 30
        or {case.get("groupId") for case in cases} != set(binding.ACTIVE_GEOMETRY_IDS)
        or {case.get("block") for case in cases} != {7, 8}
        or len({case.get("caseId") for case in cases}) != 30
        or len({case.get("seed") for case in cases}) != 30
    ):
        raise binding.Refusal("terminal-bound ordinal-13 case universe changed")
    bindings = manifest.get("sourceBindings")
    if not isinstance(bindings, dict):
        raise binding.Refusal("terminal-bound ordinal-13 source bindings missing")
    expected_hashes = {
        "sourceAnalysisRawSha256": binding.SOURCE_ANALYSIS_RAW_SHA256,
        "sourceAnalysisSha256": binding.SOURCE_ANALYSIS_SHA256,
    }
    stale = {
        key: (bindings.get(key), expected)
        for key, expected in expected_hashes.items()
        if bindings.get(key) != expected
    }
    if stale:
        raise binding.Refusal(f"terminal-bound ordinal-13 source hash changed: {stale}")
    terminal = manifest.get("terminalSourceBinding")
    if not isinstance(terminal, dict):
        raise binding.Refusal("terminal source binding missing from manifest")
    expected_terminal = {
        "sourceRunId": binding.SOURCE_RUN_ID,
        "sourceRunAttempt": binding.SOURCE_RUN_ATTEMPT,
        "sourceHeadSha": binding.SOURCE_HEAD_SHA,
        "sourceArtifactId": binding.SOURCE_ARTIFACT_ID,
        "sourceArtifactName": binding.SOURCE_ARTIFACT_NAME,
        "sourceArtifactDigest": binding.SOURCE_ARTIFACT_DIGEST,
        "sourceAnalysisRawSha256": binding.SOURCE_ANALYSIS_RAW_SHA256,
        "sourceAnalysisSha256": binding.SOURCE_ANALYSIS_SHA256,
        "geometryIds": list(binding.ACTIVE_GEOMETRY_IDS),
        "geometryCount": 15,
        "caseCount": 30,
        "blocks": [7, 8],
    }
    stale = {
        key: (terminal.get(key), expected)
        for key, expected in expected_terminal.items()
        if terminal.get(key) != expected
    }
    if stale:
        raise binding.Refusal(f"terminal source binding manifest record changed: {stale}")
    if report is not None and terminal.get("bindingReportSha256") != report.get("reportSha256"):
        raise binding.Refusal("terminal binding report hash changed")


def build_manifest(
    root: Path,
    authorization: dict[str, Any],
    context: dict[str, Any],
    runs: list[dict[str, Any]],
    runtime: dict[str, Any],
    metadata: dict[str, Any],
    source_analysis_path: Path,
) -> dict[str, Any]:
    repository_root, trigger, binding = _modules(root)
    report = binding.validate_path(source_analysis_path)
    manifest = trigger.build_manifest(
        repository_root,
        authorization,
        context,
        runs,
        runtime,
        metadata,
        source_analysis_path,
    )
    manifest["terminalSourceBinding"] = terminal_binding_value(report, binding)
    base = trigger._base(repository_root)
    manifest["manifestSha256"] = base.canonical_sha256(
        {key: item for key, item in manifest.items() if key != "manifestSha256"}
    )
    validate_terminal_manifest(manifest, report, repository_root)
    return manifest


def validate_results(manifest, results, root: Path | None = None):
    _, trigger, _ = _modules(root)
    validate_terminal_manifest(manifest, root=root)
    return trigger.validate_results(manifest, results)


def load_results(root, expected_count, repository_root: Path | None = None):
    _, trigger, _ = _modules(repository_root)
    return trigger.load_results(root, expected_count)


def dump(value, root: Path | None = None):
    _, trigger, _ = _modules(root)
    return trigger.dump(value)


def main() -> int:
    repository_root, trigger, _ = _modules()
    base = trigger._base(repository_root)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    manifest_parser = sub.add_parser("manifest")
    for name in (
        "root",
        "authorization",
        "context",
        "runs",
        "runtime",
        "authorization-metadata",
        "source-analysis",
        "output",
    ):
        manifest_parser.add_argument(f"--{name}", type=Path, required=True)
    for command in ("aggregate", "audit", "analyze"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--root", type=Path, required=True)
        command_parser.add_argument("--manifest", type=Path, required=True)
        command_parser.add_argument("--source-analysis", type=Path, required=True)
        command_parser.add_argument("--results-root", type=Path)
        command_parser.add_argument("--wave1-aggregate", type=Path)
        command_parser.add_argument("--wave1-audit", type=Path)
        command_parser.add_argument("--wave2-aggregate", type=Path)
        command_parser.add_argument("--wave2-audit", type=Path)
        command_parser.add_argument("--wave3-aggregate", type=Path)
        command_parser.add_argument("--wave3-audit", type=Path)
        command_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "manifest":
            rows = json.loads(args.runs.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise base.Refusal("flattened runs must be an array")
            value = build_manifest(
                args.root,
                base.load_json(args.authorization),
                base.load_json(args.context),
                rows,
                base.load_json(args.runtime),
                base.load_json(args.authorization_metadata),
                args.source_analysis,
            )
        else:
            root = args.root.resolve()
            manifest = base.load_json(args.manifest)
            validate_terminal_manifest(manifest, root=root)
            prereg = base.preregistration(root, args.source_analysis)
            postprocess = base.module(root / base.POSTPROCESS_PATH, "wave3_v1_terminal_trigger_postprocess")
            if args.command == "aggregate":
                results = base.load_results(args.results_root, manifest["caseCount"])
                base.validate_results(manifest, results)
                value = postprocess.aggregate_wave3(prereg, results, root)
            elif args.command == "audit":
                results = base.load_results(args.results_root, manifest["caseCount"])
                base.validate_results(manifest, results)
                value = postprocess.audit_wave3(
                    prereg, results, base.load_json(args.wave3_aggregate), root
                )
            else:
                value = postprocess.analyze_waves(
                    prereg,
                    base.load_json(args.wave1_aggregate),
                    base.load_json(args.wave1_audit),
                    base.load_json(args.wave2_aggregate),
                    base.load_json(args.wave2_audit),
                    base.load_json(args.wave3_aggregate),
                    base.load_json(args.wave3_audit),
                    root,
                )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(base.dump(value), encoding="utf-8", newline="\n")
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
