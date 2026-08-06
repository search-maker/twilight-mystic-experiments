#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

BASE_EXECUTION = "experiments/tier1-precision-continuation-wave2-v1/execution.py"
TRIGGER_BRANCH = "dispatch/tier1-precision-continuation-wave2-ordinal12-v1"
EXECUTION_EVENT = "push"


def _base(root: Path | None = None):
    repository_root = (root or Path(__file__).resolve().parents[2]).resolve()
    path = repository_root / BASE_EXECUTION
    spec = importlib.util.spec_from_file_location("wave2_v1_base_execution_for_push", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("wave-two base execution module unavailable")
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
            "caseCount": module.CASE_COUNT,
            "geometryCount": module.GEOMETRY_COUNT,
            "wave": 2,
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

    module.validate_context = validate_context
    module.validate_authorization = validate_authorization
    module.validate_manifest = validate_manifest
    return module


def build_manifest(root, authorization, context, runs, runtime, metadata):
    base = _base(root)
    value = base.build_manifest(root, authorization, context, runs, runtime, metadata)
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


def load_results(root):
    return _base().load_results(root)


def aggregate(root, manifest, results):
    return _base(root).aggregate(root, manifest, results)


def audit(root, manifest, results, aggregate_value):
    return _base(root).audit(root, manifest, results, aggregate_value)


def analyze(root, manifest, source_aggregate, source_audit, aggregate_value, audit_value):
    return _base(root).analyze(
        root,
        manifest,
        source_aggregate,
        source_audit,
        aggregate_value,
        audit_value,
    )


def load_bound_source(path, expected_sha256):
    return _base().load_bound_source(path, expected_sha256)


def dump(value):
    return _base().dump(value)


def load_json(path):
    return _base().load_json(path)


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
        "output",
    ):
        manifest_parser.add_argument(f"--{name}", type=Path, required=True)
    for command in ("aggregate", "audit", "analyze"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--root", type=Path, required=True)
        command_parser.add_argument("--manifest", type=Path, required=True)
        command_parser.add_argument("--results-root", type=Path)
        command_parser.add_argument("--source-aggregate", type=Path)
        command_parser.add_argument("--source-audit", type=Path)
        command_parser.add_argument("--aggregate", type=Path)
        command_parser.add_argument("--audit", type=Path)
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
        )
    else:
        root = args.root.resolve()
        manifest = base.load_json(args.manifest)
        results = base.load_results(args.results_root) if args.results_root else []
        if args.command == "aggregate":
            value = aggregate(root, manifest, results)
        elif args.command == "audit":
            value = audit(root, manifest, results, base.load_json(args.aggregate))
        else:
            source_aggregate = base.load_bound_source(
                args.source_aggregate, base.SOURCE_AGGREGATE_RAW_SHA256
            )
            source_audit = base.load_bound_source(
                args.source_audit, base.SOURCE_AUDIT_RAW_SHA256
            )
            value = analyze(
                root,
                manifest,
                source_aggregate,
                source_audit,
                base.load_json(args.aggregate),
                base.load_json(args.audit),
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(base.dump(value), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
