#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

STAGE_ID = "tier1-precision-continuation-wave1-ordinal8-execution-v2"
RUN_TITLE = "Tier-1 precision continuation wave 1 ordinal 8"
AUTHORIZATION_REF = "5168be57c28bca5f316d70a785a782ea9b3b1036"
AUTHORIZATION_ORDINAL = 8
EXECUTION_KEY = "twilight-surrogate-tier-1-v1:numerical:8"
AUTHORIZATION_PATH = "experiments/tier1-precision-continuation-wave1-v2/authorization.ordinal8.json"
PREREGISTRATION_PATH = "evidence/tier1-precision-continuation-wave1-v2/preregistration.json"
PACKAGE_PATH = "experiments/tier1-precision-continuation-wave1-v2/package.py"
RUNTIME_LOCK_PATH = "experiments/mystic-batch-v1/runtime-lock.micromamba.json"
EXPECTED_PREREGISTRATION_SHA256 = "03ac61690981232edd30cbd5a674f8b246d9abc31ac2f1c8cf9bb4e57eeb3c96"
CASE_COUNT = 40
GEOMETRY_COUNT = 20
MAX_CONFIGURED_PHOTON_HISTORIES = 5_100_000_000
BLOCKS = [3, 4]


class Refusal(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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


def load_package(root: Path):
    path = root / PACKAGE_PATH
    spec = importlib.util.spec_from_file_location("wave1_package", path)
    if spec is None or spec.loader is None:
        raise Refusal("wave-1 package unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_authorization(auth: dict[str, Any], prereg: dict[str, Any]) -> None:
    expected = {
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "enabled": True,
        "solverExecutionAuthorized": True,
        "runAttempt": 1,
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "caseCount": CASE_COUNT,
        "blocks": BLOCKS,
        "automaticDispatch": False,
        "githubRerunAllowed": False,
    }
    stale = {key: (auth.get(key), value) for key, value in expected.items() if auth.get(key) != value}
    if stale:
        raise Refusal(f"authorization mismatch: {stale}")
    if auth.get("preregistrationSha256") != EXPECTED_PREREGISTRATION_SHA256:
        raise Refusal("authorization preregistration binding changed")
    if prereg.get("preregistrationSha256") != EXPECTED_PREREGISTRATION_SHA256:
        raise Refusal("preregistration self-binding changed")
    forbidden_true = ("dispatch", "workflowDispatchEnabled", "automaticDispatch", "githubRerunAllowed")
    if any(auth.get(key) is True for key in forbidden_true):
        raise Refusal("authorization attempted to dispatch or rerun")


def validate_context(context: dict[str, Any]) -> None:
    expected = {
        "eventName": "workflow_dispatch",
        "runAttempt": 1,
        "displayTitle": RUN_TITLE,
        "authorizationRef": AUTHORIZATION_REF,
        "authorizationOrdinal": AUTHORIZATION_ORDINAL,
        "executionKey": EXECUTION_KEY,
        "headBranch": "main",
    }
    stale = {key: (context.get(key), value) for key, value in expected.items() if context.get(key) != value}
    if stale:
        raise Refusal(f"run context mismatch: {stale}")
    sha = context.get("headSha")
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise Refusal("invalid execution source head")


def duplicate_run_audit(existing_runs: Iterable[dict[str, Any]], current_run_id: int) -> dict[str, Any]:
    matches = []
    for run in existing_runs:
        if not isinstance(run, dict):
            raise Refusal("malformed duplicate-search evidence")
        run_id = run.get("id")
        if run.get("display_title") == RUN_TITLE and run_id != current_run_id:
            matches.append({"id": run_id, "status": run.get("status"), "conclusion": run.get("conclusion")})
    if matches:
        raise Refusal(f"duplicate execution identity already exists: {matches}")
    return {
        "schemaVersion": 1,
        "status": "NO_PRIOR_MATCHING_RUN",
        "displayTitle": RUN_TITLE,
        "currentRunId": current_run_id,
        "inspectedRunCount": len(list(existing_runs)) if isinstance(existing_runs, list) else None,
        "matchingRuns": [],
    }


def _validate_cases(prereg: dict[str, Any]) -> list[dict[str, Any]]:
    cases = prereg.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise Refusal("wave-1 case count changed")
    ids = [case.get("caseId") for case in cases]
    seeds = [case.get("seed") for case in cases]
    geometries = [case.get("groupId") for case in cases]
    if len(set(ids)) != CASE_COUNT or len(set(seeds)) != CASE_COUNT:
        raise Refusal("case IDs or seeds are not unique")
    if len(set(geometries)) != GEOMETRY_COUNT:
        raise Refusal("geometry count changed")
    if {case.get("block") for case in cases} != set(BLOCKS):
        raise Refusal("blocks changed")
    if sum(case.get("photonHistories", 0) for case in cases) != MAX_CONFIGURED_PHOTON_HISTORIES:
        raise Refusal("configured photon budget changed")
    role_geometries: dict[str, set[str]] = {"surrogate-training": set(), "internal-holdout": set()}
    for case in cases:
        role = case.get("role")
        if role not in role_geometries:
            raise Refusal("unknown role")
        role_geometries[role].add(case["groupId"])
        if case.get("proposalOnly") is not True or case.get("wave") != 1:
            raise Refusal("case escaped proposal-only wave 1")
    if {key: len(value) for key, value in role_geometries.items()} != {"surrogate-training": 17, "internal-holdout": 3}:
        raise Refusal("17/3 role isolation changed")
    proof = prereg.get("seedProof", {})
    if proof.get("wave1SeedCount") != CASE_COUNT or proof.get("allWave1SeedsUnique") is not True:
        raise Refusal("seed uniqueness proof changed")
    if proof.get("historicalOverlap") != []:
        raise Refusal("wave seeds overlap historical seeds")
    return cases


def build_manifest(root: Path, auth: dict[str, Any], context: dict[str, Any], runs: list[dict[str, Any]], runtime: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    prereg_path = root / PREREGISTRATION_PATH
    prereg = load_json(prereg_path)
    package = load_package(root)
    package.validate_preregistration(prereg, root)
    validate_authorization(auth, prereg)
    validate_context(context)
    duplicate = duplicate_run_audit(runs, int(context["runId"]))
    cases = _validate_cases(prereg)
    required_runtime = ("uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "runtimeLockRawSha256")
    if any(not isinstance(runtime.get(key), str) or len(runtime[key]) != 64 for key in required_runtime):
        raise Refusal("runtime binding incomplete")
    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "AUTHORIZED_FOR_ONE_ATTEMPT1_EXECUTION",
        "displayTitle": RUN_TITLE,
        "authorizationRef": AUTHORIZATION_REF,
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
        "cases": cases,
        "seedProof": prereg["seedProof"],
        "sourceBindings": {
            "authorizationRawSha256": canonical_sha256(auth),
            "preregistrationRawSha256": source_sha256(prereg_path),
            "preregistrationSha256": prereg["preregistrationSha256"],
            "packageRawSha256": source_sha256(root / PACKAGE_PATH),
            "runtimeLockRawSha256": source_sha256(root / RUNTIME_LOCK_PATH),
            "ordinal2Evidence": prereg["sourceBindings"],
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


def validate_result_set(manifest: dict[str, Any], results: list[dict[str, Any]]) -> None:
    expected = {case["caseId"]: case for case in manifest["cases"]}
    if len(results) != CASE_COUNT or {r.get("caseId") for r in results} != set(expected):
        raise Refusal("partial, duplicate, or unplanned result set")
    for result in results:
        case = expected[result["caseId"]]
        if result.get("status") != "COMPLETED" or result.get("role") != case["role"] or result.get("seed") != case["seed"]:
            raise Refusal("case result provenance changed")
        values = result.get("selectedNodeRadiance")
        if not isinstance(values, list) or len(values) != 15 or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)) or v < 0 for v in values):
            raise Refusal("malformed or nonfinite radiance evidence")
        if result.get("syntaxCheckCount") != 1 or result.get("solverExecutionCount") != 1:
            raise Refusal("case did not execute exactly once")
        seal = result.get("contentSha256")
        payload = {k: v for k, v in result.items() if k != "contentSha256"}
        if seal != canonical_sha256(payload):
            raise Refusal("case result hash drift")


def aggregate(root: Path, manifest: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    validate_result_set(manifest, results)
    prereg = load_json(root / PREREGISTRATION_PATH)
    package = load_package(root)
    wrapper = package.aggregate_wave1(prereg, results, root)
    return {"schemaVersion": 1, "stageId": STAGE_ID, "manifestSha256": manifest["manifestSha256"], "resultHashes": {r["caseId"]: r["contentSha256"] for r in sorted(results, key=lambda x: x["caseId"])}, "aggregate": wrapper}


def audit(root: Path, manifest: dict[str, Any], results: list[dict[str, Any]], aggregate_value: dict[str, Any]) -> dict[str, Any]:
    validate_result_set(manifest, results)
    prereg = load_json(root / PREREGISTRATION_PATH)
    package = load_package(root)
    wrapper = package.audit_wave1(prereg, results, aggregate_value["aggregate"], root)
    return {"schemaVersion": 1, "stageId": STAGE_ID, "status": "PASSED", "manifestSha256": manifest["manifestSha256"], "audit": wrapper}


def analyze(root: Path, manifest: dict[str, Any], aggregate_value: dict[str, Any], audit_value: dict[str, Any]) -> dict[str, Any]:
    prereg = load_json(root / PREREGISTRATION_PATH)
    package = load_package(root)
    wrapper = package.analyze_wave1(prereg, aggregate_value["aggregate"], audit_value["audit"], root)
    return {"schemaVersion": 1, "stageId": STAGE_ID, "status": "ANALYSIS_COMPLETE_NO_AUTOMATIC_ACTION", "manifestSha256": manifest["manifestSha256"], "analysis": wrapper, "automaticNextWave": False, "surrogateTrainingAuthorized": False, "internalHoldoutOpeningAuthorized": False, "tier2Authorized": False, "productionPromotionAuthorized": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("manifest")
    for name in ("root", "authorization", "context", "runs", "runtime", "output"):
        pre.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "manifest":
        value = build_manifest(args.root, load_json(args.authorization), load_json(args.context), json.loads(args.runs.read_text()), load_json(args.runtime))
        args.output.write_text(dump(value), encoding="utf-8", newline="\n")
        print(dump(value), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())