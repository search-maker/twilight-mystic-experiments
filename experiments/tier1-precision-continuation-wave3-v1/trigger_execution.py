#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

BASE_EXECUTION = "experiments/tier1-precision-continuation-wave3-v1/execution.py"
TRIGGER_BRANCH = "dispatch/tier1-precision-continuation-wave3-ordinal13-v1"
EXECUTION_EVENT = "push"


def _base(root: Path | None = None):
    repository_root = (root or Path(__file__).resolve().parents[2]).resolve()
    path = repository_root / BASE_EXECUTION
    spec = importlib.util.spec_from_file_location("wave3_v1_base_execution_for_push", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("wave-three base execution module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_validate_authorization = module.validate_authorization

    def validate_context(context: dict[str, Any]) -> None:
        expected = {
            "eventName": EXECUTION_EVENT,
            "triggerBranch": TRIGGER_BRANCH,
            "runAttempt": 1,
            "displayTitle": module.RUN_TITLE,
            "authorizationOrdinal": module.AUTHORIZATION_ORDINAL,
            "executionKey": module.EXECUTION_KEY,
            "headBranch": "main",
        }
        stale = {
            key: (context.get(key), value)
            for key, value in expected.items()
            if context.get(key) != value
        }
        if stale:
            raise module.Refusal(f"push-trigger run context mismatch: {stale}")
        for key in ("headSha", "authorizationRef"):
            value = context.get(key)
            if (
                not isinstance(value, str)
                or len(value) != 40
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise module.Refusal(f"invalid {key}")
        if not isinstance(context.get("runId"), int) or context["runId"] <= 0:
            raise module.Refusal("invalid run id")

    def validate_authorization(authorization, preregistration, context):
        original_validate_authorization(authorization, preregistration, context)
        if authorization.get("triggerBranch") != TRIGGER_BRANCH:
            raise module.Refusal("authorization trigger branch changed")
        if authorization.get("triggerEvent") != EXECUTION_EVENT:
            raise module.Refusal("authorization trigger event changed")

    def validate_manifest(manifest: dict[str, Any]) -> None:
        seal = manifest.get("manifestSha256")
        payload = {
            key: value for key, value in manifest.items() if key != "manifestSha256"
        }
        if seal != module.canonical_sha256(payload):
            raise module.Refusal("manifest hash drift")
        expected = {
            "stageId": module.STAGE_ID,
            "wave": 3,
            "blocks": module.BLOCKS,
            "authorizationOrdinal": module.AUTHORIZATION_ORDINAL,
            "executionKey": module.EXECUTION_KEY,
            "runAttempt": 1,
            "eventName": EXECUTION_EVENT,
            "triggerBranch": TRIGGER_BRANCH,
            "headBranch": "main",
            "githubRerunAllowed": False,
            "retryAllowed": False,
            "resumeAllowed": False,
        }
        stale = {
            key: (manifest.get(key), value)
            for key, value in expected.items()
            if manifest.get(key) != value
        }
        if stale:
            raise module.Refusal(f"push-trigger manifest identity changed: {stale}")
        if (
            not isinstance(manifest.get("geometryCount"), int)
            or manifest["geometryCount"] <= 0
            or manifest.get("caseCount") != 2 * manifest["geometryCount"]
            or not isinstance(manifest.get("cases"), list)
            or len(manifest["cases"]) != manifest["caseCount"]
        ):
            raise module.Refusal("dynamic push-trigger manifest cardinality changed")

    module.validate_context = validate_context
    module.validate_authorization = validate_authorization
    module.validate_manifest = validate_manifest
    return module


def build_manifest(root, authorization, context, runs, runtime, metadata, source_analysis_path):
    base = _base(root)
    value = base.build_manifest(
        root,
        authorization,
        context,
        runs,
        runtime,
        metadata,
        source_analysis_path,
    )
    value["eventName"] = EXECUTION_EVENT
    value["triggerBranch"] = TRIGGER_BRANCH
    value["manifestSha256"] = base.canonical_sha256(
        {key: item for key, item in value.items() if key != "manifestSha256"}
    )
    base.validate_manifest(value)
    return value


def validate_manifest(manifest):
    return _base().validate_manifest(manifest)


def validate_results(manifest, results):
    return _base().validate_results(manifest, results)


def load_results(root, expected_count):
    return _base().load_results(root, expected_count)


def dump(value):
    return _base().dump(value)


def main() -> int:
    base = _base()
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
        base.validate_manifest(manifest)
        prereg = base.preregistration(root, args.source_analysis)
        postprocess = base.module(root / base.POSTPROCESS_PATH, "wave3_v1_trigger_postprocess")
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


if __name__ == "__main__":
    raise SystemExit(main())
