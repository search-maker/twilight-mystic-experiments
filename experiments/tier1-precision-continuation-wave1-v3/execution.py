#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE_ID = "tier1-precision-continuation-wave1-ordinal9-execution-v3"
RUN_TITLE = "Tier-1 precision continuation wave 1 ordinal 9"
AUTHORIZATION_ORDINAL = 9
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:9"
AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave1-v3/authorization.ordinal9.json"
PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v3/package.py"
PAGES_PATH = "experiments/tier1-precision-continuation-wave1-v3/duplicate_pages.py"
RUNTIME_LOCK_PATH = "experiments/mystic-batch-v1/runtime-lock.micromamba.json"
EXPECTED_PREREGISTRATION_SHA256 = "9517d15623ef7b9e08f5b3d3a2e0ec5702f634755eb9851a2afe761810d4cd67"
CASE_COUNT = 40
GEOMETRY_COUNT = 20
MAX_CONFIGURED_PHOTON_HISTORIES = 5_100_000_000
BLOCKS = [3, 4]


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


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
    stale = {key: (context.get(key), value) for key, value in expected.items() if context.get(key) != value}
    if stale:
        raise Refusal(f"run context mismatch: {stale}")
    for key in ("headSha", "authorizationRef"):
        value = context.get(key)
        if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            raise Refusal(f"invalid {key}")
    if not isinstance(context.get("runId"), int) or context["runId"] <= 0:
        raise Refusal("invalid run id")


def validate_authorization(auth: dict[str, Any], prereg: dict[str, Any], context: dict[str, Any]) -> None:
    expected = {
        "schemaVersion": 1,
        "stageId": "tier1-precision-continuation-wave1-authorization-v3",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "runTitle": RUN_TITLE,
        "runAttempt": 1,
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
    stale = {key: (auth.get(key), value) for key, value in expected.items() if auth.get(key) != value}
    if stale:
        raise Refusal(f"authorization mismatch: {stale}")
    if auth.get("preregistrationSha256") != EXPECTED_PREREGISTRATION_SHA256 or prereg.get("preregistrationSha256") != EXPECTED_PREREGISTRATION_SHA256:
        raise Refusal("preregistration binding changed")
    if auth.get("executionSourceHeadSha") != context.get("headSha"):
        raise Refusal("authorization source head changed")


def validate_authorization_metadata(metadata: dict[str, Any], context: dict[str, Any]) -> None:
    expected = {
        "authorizationCommit": context["authorizationRef"],
        "authorizationParent": context["headSha"],
        "changedFiles": [AUTHORIZATION_PATH],
        "parentCount": 1,
    }
    stale = {key: (metadata.get(key), value) for key, value in expected.items() if metadata.get(key) != value}
    if stale:
        raise Refusal(f"authorization commit metadata mismatch: {stale}")


def build_manifest(root: Path, auth: dict[str, Any], context: dict[str, Any], runs: list[dict[str, Any]], runtime: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_context(context)
    package = module(root / PACKAGE_PATH, "wave1_v3_execution_package")
    prereg = package.build_preregistration(root)
    package.validate_preregistration(prereg, root)
    validate_authorization(auth, prereg, context)
    validate_authorization_metadata(metadata, context)
    pages = module(root / PAGES_PATH, "wave1_v3_execution_pages")
    duplicate = pages.duplicate_audit(runs, current_run_id=context["runId"], candidate_title=RUN_TITLE)
    required_runtime = ("uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "runtimeLockRawSha256")
    if any(not isinstance(runtime.get(key), str) or len(runtime[key]) != 64 for key in required_runtime):
        raise Refusal("runtime binding incomplete")
    if prereg["caseCount"] != CASE_COUNT or prereg["geometryCount"] != GEOMETRY_COUNT or prereg["maximumConfiguredPhotonHistories"] != MAX_CONFIGURED_PHOTON_HISTORIES:
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
        "wave": 1,
        "geometryCount": GEOMETRY_COUNT,
        "caseCount": CASE_COUNT,
        "maximumConfiguredPhotonHistories": MAX_CONFIGURED_PHOTON_HISTORIES,
        "roleCounts": prereg["roleCounts"],
        "cases": prereg["cases"],
        "seedProof": prereg["seedProof"],
        "sourceBindings": {
            "authorizationRawSha256": canonical_sha256(auth),
            "authorizationCommit": context["authorizationRef"],
            "preregistrationSha256": prereg["preregistrationSha256"],
            "packageRawSha256": raw_sha256(root / PACKAGE_PATH),
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
    if manifest.get("stageId") != STAGE_ID or manifest.get("caseCount") != CASE_COUNT:
        raise Refusal("manifest identity changed")


def load_results(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != CASE_COUNT:
        raise Refusal(f"expected {CASE_COUNT} case results, found {len(paths)}")
    return [load_json(path) for path in paths]


def validate_results(manifest: dict[str, Any], results: list[dict[str, Any]]) -> None:
    validate_manifest(manifest)
    expected = {case["caseId"]: case for case in manifest["cases"]}
    if len(results) != CASE_COUNT or {row.get("caseId") for row in results} != set(expected):
        raise Refusal("partial, duplicate, or unplanned result set")
    for result in results:
        case = expected[result["caseId"]]
        if result.get("status") != "COMPLETED" or result.get("role") != case["role"] or result.get("seed") != case["seed"] or result.get("block") != case["block"]:
            raise Refusal("case result provenance changed")
        values = result.get("selectedNodeRadiance")
        if not isinstance(values, list) or len(values) != 15 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)) or v < 0 for v in values):
            raise Refusal("malformed selected-node radiance")
        if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
            raise Refusal("case did not execute exactly once")
        seal = result.get("contentSha256")
        payload = {key: value for key, value in result.items() if key != "contentSha256"}
        if seal != canonical_sha256(payload):
            raise Refusal("case result hash drift")


def package_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # The execution seal binds the v3 case identity. The reviewed scientific
    # package translates that identity to its v2 base case ID, so the seal is
    # verified above and intentionally removed before translation.
    return [{key: value for key, value in row.items() if key != "contentSha256"} for row in results]


def aggregate(root: Path, manifest: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    validate_results(manifest, results)
    package = module(root / PACKAGE_PATH, "wave1_v3_aggregate_package")
    prereg = package.build_preregistration(root)
    return package.aggregate_wave1(prereg, package_results(results), root)


def audit(root: Path, manifest: dict[str, Any], results: list[dict[str, Any]], aggregate_value: dict[str, Any]) -> dict[str, Any]:
    validate_results(manifest, results)
    package = module(root / PACKAGE_PATH, "wave1_v3_audit_package")
    prereg = package.build_preregistration(root)
    return package.audit_wave1(prereg, package_results(results), aggregate_value, root)


def analyze(root: Path, manifest: dict[str, Any], aggregate_value: dict[str, Any], audit_value: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(manifest)
    package = module(root / PACKAGE_PATH, "wave1_v3_analysis_package")
    prereg = package.build_preregistration(root)
    return package.analyze_wave1(prereg, aggregate_value, audit_value, root)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("manifest")
    for name in ("root", "authorization", "context", "runs", "runtime", "authorization-metadata", "output"):
        m.add_argument(f"--{name}", type=Path, required=True)
    for command in ("aggregate", "audit", "analyze"):
        p = sub.add_parser(command)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--results-root", type=Path)
        p.add_argument("--aggregate", type=Path)
        p.add_argument("--audit", type=Path)
        p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "manifest":
        rows = json.loads(args.runs.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise Refusal("flattened runs must be an array")
        value = build_manifest(args.root, load_json(args.authorization), load_json(args.context), rows, load_json(args.runtime), load_json(args.authorization_metadata))
    else:
        root = args.root.resolve()
        manifest = load_json(args.manifest)
        results = load_results(args.results_root) if args.results_root else []
        if args.command == "aggregate":
            value = aggregate(root, manifest, results)
        elif args.command == "audit":
            value = audit(root, manifest, results, load_json(args.aggregate))
        else:
            value = analyze(root, manifest, load_json(args.aggregate), load_json(args.audit))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump(value), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
