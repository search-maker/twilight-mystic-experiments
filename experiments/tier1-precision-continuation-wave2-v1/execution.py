#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave2-ordinal12-execution-v1"
RUN_TITLE = "Tier-1 precision continuation wave 2 ordinal 12"
AUTHORIZATION_ORDINAL = 12
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:12"
AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave2-v1/authorization.ordinal12.json"
PACKAGE_PATH = "experiments/tier1-precision-continuation-wave2-v1/package.py"
POSTPROCESS_PATH = "experiments/tier1-precision-continuation-wave2-v1/postprocess.py"
ADAPTER_PATH = "experiments/tier1-precision-continuation-wave2-v1/execution_adapter.py"
EXECUTOR_PATH = "experiments/tier1-precision-continuation-wave2-v1/case_executor.py"
PAGES_PATH = "experiments/tier1-precision-continuation-wave1-v3/duplicate_pages.py"
RUNTIME_LOCK_PATH = "experiments/mystic-batch-v1/runtime-lock.micromamba.json"
CASE_COUNT = 32
GEOMETRY_COUNT = 16
MAX_CONFIGURED_PHOTON_HISTORIES = 4_600_000_000
BLOCKS = [5, 6]
SOURCE_AGGREGATE_RAW_SHA256 = "b57477cf68555ec9752d43e817cadaf5e1f2bf33490b09767cad73b341a2ca8e"
SOURCE_AUDIT_RAW_SHA256 = "4e37595c348f4f9d8593db20cff5c69ed41068f4f2810934e5e8f93d1df62be5"


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise Refusal(f"expected object: {path}")
    return value


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Refusal(f"module unavailable: {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def validate_context(context: dict[str, Any]) -> None:
    expected = {
        "eventName": "workflow_dispatch",
        "runAttempt": 1,
        "displayTitle": RUN_TITLE,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "headBranch": "main",
    }
    stale = {
        key: (context.get(key), value)
        for key, value in expected.items()
        if context.get(key) != value
    }
    if stale:
        raise Refusal(f"run context mismatch: {stale}")
    for key in ("headSha", "authorizationRef"):
        value = context.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise Refusal(f"invalid {key}")
    if not isinstance(context.get("runId"), int) or context["runId"] <= 0:
        raise Refusal("invalid run id")


def validate_authorization(
    authorization: dict[str, Any],
    preregistration: dict[str, Any],
    context: dict[str, Any],
) -> None:
    expected = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave2-authorization-v1",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "runTitle": RUN_TITLE,
        "runAttempt": 1,
        "wave": 2,
        "caseCount": CASE_COUNT,
        "blocks": BLOCKS,
        "enabled": True,
        "solverExecutionAuthorized": True,
        "automaticDispatch": False,
        "dispatch": False,
        "workflowDispatchEnabled": False,
        "githubRerunAllowed": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    stale = {
        key: (authorization.get(key), value)
        for key, value in expected.items()
        if authorization.get(key) != value
    }
    if stale:
        raise Refusal(f"authorization mismatch: {stale}")
    if authorization.get("preregistrationSha256") != preregistration.get(
        "preregistrationSha256"
    ):
        raise Refusal("preregistration binding changed")
    if authorization.get("executionSourceHeadSha") != context.get("headSha"):
        raise Refusal("authorization source head changed")
    if authorization.get("sourceSalvageDescriptorSha256") != preregistration[
        "sourceBindings"
    ]["sourceSalvageDescriptorSha256"]:
        raise Refusal("source salvage authorization binding changed")


def validate_authorization_metadata(
    metadata: dict[str, Any], context: dict[str, Any]
) -> None:
    expected = {
        "authorizationCommit": context["authorizationRef"],
        "authorizationParent": context["headSha"],
        "changedFiles": [AUTHORIZATION_PATH],
        "parentCount": 1,
    }
    stale = {
        key: (metadata.get(key), value)
        for key, value in expected.items()
        if metadata.get(key) != value
    }
    if stale:
        raise Refusal(f"authorization commit metadata mismatch: {stale}")


def build_manifest(
    root: Path,
    authorization: dict[str, Any],
    context: dict[str, Any],
    runs: list[dict[str, Any]],
    runtime: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    validate_context(context)
    package = module(root / PACKAGE_PATH, "wave2_v1_execution_package")
    preregistration = package.build_preregistration(root)
    package.validate_preregistration(preregistration, root)
    validate_authorization(authorization, preregistration, context)
    validate_authorization_metadata(metadata, context)
    pages = module(root / PAGES_PATH, "wave2_v1_execution_pages")
    duplicate = pages.duplicate_audit(
        runs, current_run_id=context["runId"], candidate_title=RUN_TITLE
    )
    required_runtime = (
        "uvspecSha256",
        "uvspecHelpSha256",
        "libRadtranDataTreeSha256",
        "atmosphereSha256",
        "runtimeLockRawSha256",
    )
    if any(
        not isinstance(runtime.get(key), str) or len(runtime[key]) != 64
        for key in required_runtime
    ):
        raise Refusal("runtime binding incomplete")
    if (
        preregistration["caseCount"] != CASE_COUNT
        or preregistration["geometryCount"] != GEOMETRY_COUNT
        or preregistration["maximumConfiguredPhotonHistories"]
        != MAX_CONFIGURED_PHOTON_HISTORIES
        or preregistration["blocks"] != BLOCKS
    ):
        raise Refusal("scientific scope changed")
    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED_FOR_ONE_ATTEMPT1_EXECUTION",
        "displayTitle": RUN_TITLE,
        "authorizationRef": context["authorizationRef"],
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "runId": context["runId"],
        "runAttempt": 1,
        "eventName": "workflow_dispatch",
        "headBranch": "main",
        "headSha": context["headSha"],
        "blocks": BLOCKS,
        "wave": 2,
        "geometryCount": GEOMETRY_COUNT,
        "caseCount": CASE_COUNT,
        "maximumConfiguredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
        "roleCounts": preregistration["roleCounts"],
        "cases": preregistration["cases"],
        "seedProof": preregistration["seedProof"],
        "sourceBindings": {
            "authorizationRawSha256": canonical_sha256(authorization),
            "authorizationCommit": context["authorizationRef"],
            "preregistrationSha256": preregistration["preregistrationSha256"],
            "packageRawSha256": raw_sha256(root / PACKAGE_PATH),
            "postprocessRawSha256": raw_sha256(root / POSTPROCESS_PATH),
            "executionAdapterRawSha256": raw_sha256(root / ADAPTER_PATH),
            "caseExecutorRawSha256": raw_sha256(root / EXECUTOR_PATH),
            "runtimeLockRawSha256": raw_sha256(root / RUNTIME_LOCK_PATH),
            "sourceSalvageRunId": preregistration["sourceBindings"][
                "sourceSalvageRunId"
            ],
            "sourceSalvageArtifactId": preregistration["sourceBindings"][
                "sourceSalvageArtifactId"
            ],
            "sourceSalvageArtifactDigest": preregistration["sourceBindings"][
                "sourceSalvageArtifactDigest"
            ],
            "sourceAggregateRawSha256": SOURCE_AGGREGATE_RAW_SHA256,
            "sourceAuditRawSha256": SOURCE_AUDIT_RAW_SHA256,
        },
        "runtime": {key: runtime[key] for key in required_runtime},
        "duplicateRunAudit": duplicate,
        "solverExecutionAuthorized": True,
        "syntaxChecksPerCase": 1,
        "solverExecutionsPerCaseMaximum": 1,
        "retryAllowed": False,
        "resumeAllowed": False,
        "githubRerunAllowed": False,
        "automaticNextWave": False,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    seal = manifest.get("manifestSha256")
    payload = {key: value for key, value in manifest.items() if key != "manifestSha256"}
    if seal != canonical_sha256(payload):
        raise Refusal("manifest hash drift")
    expected = {
        "stageId": STAGE_ID,
        "caseCount": CASE_COUNT,
        "geometryCount": GEOMETRY_COUNT,
        "wave": 2,
        "blocks": BLOCKS,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "runAttempt": 1,
        "eventName": "workflow_dispatch",
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
        raise Refusal(f"manifest identity changed: {stale}")


def load_results(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != CASE_COUNT:
        raise Refusal(f"expected {CASE_COUNT} case results, found {len(paths)}")
    return [load_json(path) for path in paths]


def validate_results(
    manifest: dict[str, Any], results: list[dict[str, Any]]
) -> None:
    validate_manifest(manifest)
    expected = {case["caseId"]: case for case in manifest["cases"]}
    if len(results) != CASE_COUNT or {row.get("caseId") for row in results} != set(
        expected
    ):
        raise Refusal("partial, duplicate, or unplanned result set")
    for result in results:
        case = expected[result["caseId"]]
        if (
            result.get("stageId") != STAGE_ID
            or result.get("status") != "COMPLETED"
            or result.get("role") != case["role"]
            or result.get("seed") != case["seed"]
            or result.get("block") != case["block"]
            or result.get("photonHistories") != case["photonHistories"]
        ):
            raise Refusal("case result provenance changed")
        values = result.get("selectedNodeRadiance")
        if (
            not isinstance(values, list)
            or len(values) != 15
            or any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or value < 0
                for value in values
            )
        ):
            raise Refusal("malformed selected-node radiance")
        if (
            result.get("syntaxCheckCount") != 1
            or result.get("solverExecutionCount") != 1
            or result.get("retryAllowed") is not False
            or result.get("resumeAllowed") is not False
            or result.get("fittingSurfaceExposed") is not False
        ):
            raise Refusal("case did not execute exactly once")
        seal = result.get("contentSha256")
        payload = {key: value for key, value in result.items() if key != "contentSha256"}
        if seal != canonical_sha256(payload):
            raise Refusal("case result hash drift")


def aggregate(
    root: Path, manifest: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    validate_results(manifest, results)
    postprocess = module(root / POSTPROCESS_PATH, "wave2_v1_aggregate_postprocess")
    package = module(root / PACKAGE_PATH, "wave2_v1_aggregate_package")
    preregistration = package.build_preregistration(root)
    return postprocess.aggregate_wave2(preregistration, results, root)


def audit(
    root: Path,
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
    aggregate_value: dict[str, Any],
) -> dict[str, Any]:
    validate_results(manifest, results)
    postprocess = module(root / POSTPROCESS_PATH, "wave2_v1_audit_postprocess")
    package = module(root / PACKAGE_PATH, "wave2_v1_audit_package")
    preregistration = package.build_preregistration(root)
    return postprocess.audit_wave2(
        preregistration, results, aggregate_value, root
    )


def analyze(
    root: Path,
    manifest: dict[str, Any],
    source_aggregate: dict[str, Any],
    source_audit: dict[str, Any],
    aggregate_value: dict[str, Any],
    audit_value: dict[str, Any],
) -> dict[str, Any]:
    validate_manifest(manifest)
    postprocess = module(root / POSTPROCESS_PATH, "wave2_v1_analysis_postprocess")
    package = module(root / PACKAGE_PATH, "wave2_v1_analysis_package")
    preregistration = package.build_preregistration(root)
    return postprocess.analyze_waves(
        preregistration,
        source_aggregate,
        source_audit,
        aggregate_value,
        audit_value,
        root,
    )


def load_bound_source(path: Path, expected_sha256: str) -> dict[str, Any]:
    if raw_sha256(path) != expected_sha256:
        raise Refusal(f"source salvage payload hash changed: {path}")
    return load_json(path)


def main() -> int:
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
            raise Refusal("flattened runs must be an array")
        value = build_manifest(
            args.root,
            load_json(args.authorization),
            load_json(args.context),
            rows,
            load_json(args.runtime),
            load_json(args.authorization_metadata),
        )
    else:
        root = args.root.resolve()
        manifest = load_json(args.manifest)
        results = load_results(args.results_root) if args.results_root else []
        if args.command == "aggregate":
            value = aggregate(root, manifest, results)
        elif args.command == "audit":
            value = audit(
                root, manifest, results, load_json(args.aggregate)
            )
        else:
            source_aggregate = load_bound_source(
                args.source_aggregate, SOURCE_AGGREGATE_RAW_SHA256
            )
            source_audit = load_bound_source(
                args.source_audit, SOURCE_AUDIT_RAW_SHA256
            )
            value = analyze(
                root,
                manifest,
                source_aggregate,
                source_audit,
                load_json(args.aggregate),
                load_json(args.audit),
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump(value), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
