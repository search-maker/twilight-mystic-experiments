#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave3-ordinal13-execution-v1"
RUN_TITLE = "Tier-1 precision continuation wave 3 ordinal 13"
AUTHORIZATION_ORDINAL = 13
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:13"
AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave3-v1/authorization.ordinal13.json"
PACKAGE_PATH = "experiments/tier1-precision-continuation-wave3-v1/package.py"
POSTPROCESS_PATH = "experiments/tier1-precision-continuation-wave3-v1/postprocess.py"
ADAPTER_PATH = "experiments/tier1-precision-continuation-wave3-v1/execution_adapter.py"
EXECUTOR_PATH = "experiments/tier1-precision-continuation-wave3-v1/case_executor.py"
PAGES_PATH = "experiments/tier1-precision-continuation-wave1-v3/duplicate_pages.py"
RUNTIME_LOCK_PATH = "experiments/mystic-batch-v1/runtime-lock.micromamba.json"
BLOCKS = [7, 8]
SOURCE_RUN_ID = 31_065_046_524
SOURCE_RUN_ATTEMPT = 1
SOURCE_MAIN_SHA = "0ef7e011e00a4c4badcafb2f6ca06256026b1746"
SOURCE_AUTHORIZATION_REF = "18a5746778441d57b722c740a17c94af9b56e9c9"
SOURCE_EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:12"


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
        "stageId": "tier1-precision-continuation-wave3-authorization-v1",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "runTitle": RUN_TITLE,
        "runAttempt": 1,
        "wave": 3,
        "blocks": BLOCKS,
        "geometryCount": preregistration["geometryCount"],
        "caseCount": preregistration["caseCount"],
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
        "sourceRunId": SOURCE_RUN_ID,
        "sourceRunAttempt": SOURCE_RUN_ATTEMPT,
        "sourceMainSha": SOURCE_MAIN_SHA,
        "sourceAuthorizationRef": SOURCE_AUTHORIZATION_REF,
        "sourceExecutionKey": SOURCE_EXECUTION_KEY,
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
    if authorization.get("sourceAnalysisRawSha256") != preregistration.get(
        "sourceAnalysisRawSha256"
    ):
        raise Refusal("source analysis raw binding changed")
    if authorization.get("sourceAnalysisSha256") != preregistration.get(
        "sourceAnalysisSha256"
    ):
        raise Refusal("source analysis self-hash binding changed")
    if authorization.get("executionSourceHeadSha") != context.get("headSha"):
        raise Refusal("authorization source head changed")


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
    source_analysis_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    validate_context(context)
    package = module(root / PACKAGE_PATH, "wave3_v1_execution_package")
    source_analysis = package.load_json(source_analysis_path)
    preregistration = package.build_preregistration(
        source_analysis, source_analysis_path, root
    )
    validate_authorization(authorization, preregistration, context)
    validate_authorization_metadata(metadata, context)
    pages = module(root / PAGES_PATH, "wave3_v1_execution_pages")
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
        preregistration["geometryCount"] <= 0
        or preregistration["caseCount"] != 2 * preregistration["geometryCount"]
        or preregistration["blocks"] != BLOCKS
        or len(preregistration["cases"]) != preregistration["caseCount"]
    ):
        raise Refusal("dynamic scientific scope changed")
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
        "wave": 3,
        "geometryIds": preregistration["geometryIds"],
        "geometryCount": preregistration["geometryCount"],
        "caseCount": preregistration["caseCount"],
        "maximumConfiguredPhotonHistories": preregistration[
            "maximumConfiguredPhotonHistories"
        ],
        "trainingGeometryIds": preregistration["trainingGeometryIds"],
        "internalHoldoutGeometryIds": preregistration[
            "internalHoldoutGeometryIds"
        ],
        "cases": preregistration["cases"],
        "seedProof": preregistration["seedProof"],
        "sourceOrdinal12": preregistration["sourceOrdinal12"],
        "sourceBindings": {
            "authorizationCanonicalSha256": canonical_sha256(authorization),
            "authorizationCommit": context["authorizationRef"],
            "preregistrationSha256": preregistration["preregistrationSha256"],
            "sourceAnalysisRawSha256": preregistration["sourceAnalysisRawSha256"],
            "sourceAnalysisSha256": preregistration["sourceAnalysisSha256"],
            "packageRawSha256": raw_sha256(root / PACKAGE_PATH),
            "postprocessRawSha256": raw_sha256(root / POSTPROCESS_PATH),
            "executionAdapterRawSha256": raw_sha256(root / ADAPTER_PATH),
            "caseExecutorRawSha256": raw_sha256(root / EXECUTOR_PATH),
            "runtimeLockRawSha256": raw_sha256(root / RUNTIME_LOCK_PATH),
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
        "wave": 3,
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
    if (
        not isinstance(manifest.get("geometryCount"), int)
        or manifest["geometryCount"] <= 0
        or manifest.get("caseCount") != 2 * manifest["geometryCount"]
        or not isinstance(manifest.get("cases"), list)
        or len(manifest["cases"]) != manifest["caseCount"]
    ):
        raise Refusal("dynamic manifest cardinality changed")


def load_results(root: Path, expected_count: int) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != expected_count:
        raise Refusal(f"expected {expected_count} case results, found {len(paths)}")
    return [load_json(path) for path in paths]


def validate_results(
    manifest: dict[str, Any], results: list[dict[str, Any]]
) -> None:
    validate_manifest(manifest)
    expected = {case["caseId"]: case for case in manifest["cases"]}
    if len(results) != manifest["caseCount"] or {
        row.get("caseId") for row in results
    } != set(expected):
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


def preregistration(root: Path, source_analysis_path: Path) -> dict[str, Any]:
    package = module(root / PACKAGE_PATH, "wave3_v1_runtime_package")
    return package.build_preregistration(
        package.load_json(source_analysis_path), source_analysis_path, root
    )


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
            raise Refusal("flattened runs must be an array")
        value = build_manifest(
            args.root,
            load_json(args.authorization),
            load_json(args.context),
            rows,
            load_json(args.runtime),
            load_json(args.authorization_metadata),
            args.source_analysis,
        )
    else:
        root = args.root.resolve()
        manifest = load_json(args.manifest)
        validate_manifest(manifest)
        prereg = preregistration(root, args.source_analysis)
        postprocess = module(root / POSTPROCESS_PATH, "wave3_v1_runtime_postprocess")
        if args.command == "aggregate":
            results = load_results(args.results_root, manifest["caseCount"])
            validate_results(manifest, results)
            value = postprocess.aggregate_wave3(prereg, results, root)
        elif args.command == "audit":
            results = load_results(args.results_root, manifest["caseCount"])
            validate_results(manifest, results)
            value = postprocess.audit_wave3(
                prereg, results, load_json(args.wave3_aggregate), root
            )
        else:
            value = postprocess.analyze_waves(
                prereg,
                load_json(args.wave1_aggregate),
                load_json(args.wave1_audit),
                load_json(args.wave2_aggregate),
                load_json(args.wave2_audit),
                load_json(args.wave3_aggregate),
                load_json(args.wave3_audit),
                root,
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump(value), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
