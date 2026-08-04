#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

SOURCE_RUN_ID = 30878704003
SOURCE_HEAD_SHA = "bb0d6fab6edfe4e66faf3d2d9dedd2a40a195d09"
AUTHORIZATION_REF = "a59b885d28636f6b83aceef30b1029c785b2433d"
EXECUTION_KEY = "g01-fixed-precision-diagnosis-execution-v1:screening:7"
SOURCE_STAGE_ID = "g01-fixed-precision-diagnosis-execution-v1"
BATCH_ID = "g01-fixed-precision-diagnosis-v1"
MANIFEST_SHA = "26abe87fca24e16e04366a2fd35eb9161c0d0da022ed834e33faf575a41a401d"
ADAPTER_SHA = "1c149470d86bd440c0e04ef99e155024540a86672047c17a1f8acb8d5909db4c"
EXPECTED_CASES = [
    {"caseId": "g01pd-alis-b5", "ordinal": 1, "block": 5, "seed": 84601, "photonHistories": 50_000_000},
    {"caseId": "g01pd-alis-b6", "ordinal": 2, "block": 6, "seed": 84602, "photonHistories": 50_000_000},
    {"caseId": "g01pd-alis-b7", "ordinal": 3, "block": 7, "seed": 84603, "photonHistories": 50_000_000},
    {"caseId": "g01pd-alis-b8", "ordinal": 4, "block": 8, "seed": 84604, "photonHistories": 50_000_000},
]
EXPECTED_ARTIFACTS = {
    "cross-geometry-g01-precision-continuation-v1-preflight": (8880452058, "sha256:801bddf35fd526f0bf181d5e7137a744fe87a77948b49ff5e9152a1e4c05383f"),
    "cross-geometry-g01-precision-continuation-v1-case-g01pd-alis-b5": (8880552334, "sha256:dc7b371755d8516ad0039b31529f4eec88fc79c03522e98fc31e599bfdc01a16"),
    "cross-geometry-g01-precision-continuation-v1-case-g01pd-alis-b6": (8880568680, "sha256:5ed4f0f9af72b99ac1c37e2b115041b38143f465c7f2d48b5662e37b7df54321"),
    "cross-geometry-g01-precision-continuation-v1-case-g01pd-alis-b7": (8880568315, "sha256:1e35d6711dcd061b0e889688134e622c4da18630b18e038e2db7af053e60771e"),
    "cross-geometry-g01-precision-continuation-v1-case-g01pd-alis-b8": (8880568006, "sha256:4c6783072ae07179647b64e3818257816b9a3d60f8a9e2ca63422f45742a7f9b"),
}


class RecoveryError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise RecoveryError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def validate_source_run(run: dict[str, Any]) -> None:
    expected = {
        "id": SOURCE_RUN_ID,
        "status": "completed",
        "conclusion": "failure",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "head_branch": "main",
        "head_sha": SOURCE_HEAD_SHA,
    }
    stale = {key: (run.get(key), value) for key, value in expected.items() if run.get(key) != value}
    if stale:
        raise RecoveryError(f"source run mismatch: {stale}")
    marker = f"| key={EXECUTION_KEY} | auth={AUTHORIZATION_REF} | ordinal=7"
    if marker not in str(run.get("name", "")):
        raise RecoveryError("source run one-shot marker changed")


def validate_jobs(value: dict[str, Any]) -> None:
    jobs = value.get("jobs")
    if not isinstance(jobs, list):
        raise RecoveryError("source jobs missing")
    by_name = {str(job.get("name")): job for job in jobs if isinstance(job, dict)}
    preflight = by_name.get("preflight")
    if not isinstance(preflight, dict) or preflight.get("conclusion") != "success":
        raise RecoveryError("source preflight did not succeed")
    for case in EXPECTED_CASES:
        prefix = f"cases ({case['caseId']},"
        matches = [job for name, job in by_name.items() if name.startswith(prefix)]
        if len(matches) != 1 or matches[0].get("conclusion") != "success":
            raise RecoveryError(f"source case job not successful: {case['caseId']}")
    aggregate = by_name.get("aggregate")
    if not isinstance(aggregate, dict) or aggregate.get("conclusion") != "failure":
        raise RecoveryError("source aggregate boundary changed")


def validate_artifacts(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = value.get("artifacts")
    if not isinstance(items, list):
        raise RecoveryError("source artifacts missing")
    by_name = {item.get("name"): item for item in items if isinstance(item, dict)}
    bound: dict[str, dict[str, Any]] = {}
    for name, (artifact_id, digest) in EXPECTED_ARTIFACTS.items():
        item = by_name.get(name)
        if not isinstance(item, dict):
            raise RecoveryError(f"missing source artifact: {name}")
        expected = {"id": artifact_id, "digest": digest, "expired": False}
        stale = {key: (item.get(key), wanted) for key, wanted in expected.items() if item.get(key) != wanted}
        if stale:
            raise RecoveryError(f"source artifact mismatch: {name}: {stale}")
        workflow_run = item.get("workflow_run")
        if isinstance(workflow_run, dict) and workflow_run.get("id") not in {None, SOURCE_RUN_ID}:
            raise RecoveryError(f"artifact belongs to another run: {name}")
        bound[name] = {"id": artifact_id, "digest": digest}
    return bound


def validate_preflight(preflight: Path) -> None:
    plan = load(preflight / "plan.json")
    guard = load(preflight / "authorization-guard.json")
    duplicate = load(preflight / "duplicate-run-audit.json")
    expected_plan = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE_ID,
        "status": "PLAN_FROZEN",
        "caseCount": 4,
        "configuredMcPhotonsSum": 200_000_000,
        "maxParallel": 4,
        "timeoutSeconds": 900,
    }
    stale = {key: (plan.get(key), value) for key, value in expected_plan.items() if plan.get(key) != value}
    if stale:
        raise RecoveryError(f"source plan mismatch: {stale}")
    include = plan.get("matrix", {}).get("include")
    if not isinstance(include, list) or len(include) != 4:
        raise RecoveryError("source plan matrix invalid")
    normalized = [
        {
            "caseId": row.get("case_id"),
            "ordinal": row.get("ordinal"),
            "block": row.get("block"),
            "seed": row.get("seed"),
            "photonHistories": row.get("photon_histories"),
        }
        for row in include
    ]
    if normalized != EXPECTED_CASES:
        raise RecoveryError("source plan cases changed")
    expected_guard = {
        "status": "AUTHORIZED",
        "stageId": SOURCE_STAGE_ID,
        "authorizationOrdinal": 7,
        "authorizationParentCommit": SOURCE_HEAD_SHA,
        "authorizationRef": AUTHORIZATION_REF,
        "executionKey": EXECUTION_KEY,
        "sourceDiagnosisRunId": 30876899126,
        "sourceRunId": 30875148389,
        "caseCount": 4,
        "configuredMcPhotonsSum": 200_000_000,
        "manifestRawSha256": MANIFEST_SHA,
    }
    stale = {key: (guard.get(key), value) for key, value in expected_guard.items() if guard.get(key) != value}
    if stale:
        raise RecoveryError(f"authorization guard mismatch: {stale}")
    expected_duplicate = {"status": "PASS", "currentRunId": SOURCE_RUN_ID, "matchingPriorRunCount": 0}
    stale = {key: (duplicate.get(key), value) for key, value in expected_duplicate.items() if duplicate.get(key) != value}
    if stale:
        raise RecoveryError(f"duplicate audit mismatch: {stale}")


def validate_authorization(auth: dict[str, Any]) -> None:
    expected = {
        "schemaVersion": 1,
        "stageId": SOURCE_STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "authorizationOrdinal": 7,
        "exactAuthorizationParentCommit": SOURCE_HEAD_SHA,
        "executionKey": EXECUTION_KEY,
        "sourceDiagnosisRunId": 30876899126,
        "sourceRunId": 30875148389,
        "proposalRawSha256": MANIFEST_SHA,
        "executionAdapterRawSha256": ADAPTER_SHA,
    }
    stale = {key: (auth.get(key), value) for key, value in expected.items() if auth.get(key) != value}
    if stale:
        raise RecoveryError(f"authorization mismatch: {stale}")
    for key in ("runtimeLockRawSha256", "executionWorkflowRawSha256", "aggregateRawSha256", "auditRawSha256", "analysisDriverRawSha256"):
        if not valid_sha(auth.get(key)):
            raise RecoveryError(f"authorization hash invalid: {key}")


def validate_cases(root: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != 4:
        raise RecoveryError(f"expected four case results, found {len(paths)}")
    by_id: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in paths:
        row = load(path)
        case_id = row.get("caseId")
        if not isinstance(case_id, str) or case_id in by_id:
            raise RecoveryError("duplicate or missing case ID")
        by_id[case_id] = (row, path)
    ordered: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    for expected in EXPECTED_CASES:
        pair = by_id.get(expected["caseId"])
        if pair is None:
            raise RecoveryError(f"missing case result: {expected['caseId']}")
        row, path = pair
        invariants = {
            "stageId": "mystic-batch-v1",
            "batchId": BATCH_ID,
            "ordinal": expected["ordinal"],
            "seed": expected["seed"],
            "photonHistories": expected["photonHistories"],
            "manifestRawSha256": MANIFEST_SHA,
            "adapterRawSha256": ADAPTER_SHA,
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "status": "COMPLETED",
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
        }
        stale = {key: (row.get(key), value) for key, value in invariants.items() if row.get(key) != value}
        if stale:
            raise RecoveryError(f"case invariant mismatch: {expected['caseId']}: {stale}")
        for phase in ("syntax", "solver"):
            detail = row.get(phase)
            if not isinstance(detail, dict) or detail.get("exitCode") != 0 or detail.get("timedOut") is not False:
                raise RecoveryError(f"case {phase} failed: {expected['caseId']}")
        value = row.get("selectedPhotopicContributionCdM2")
        nodes = row.get("selectedNodeRadiance")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
            raise RecoveryError(f"invalid photopic value: {expected['caseId']}")
        if not isinstance(nodes, list) or len(nodes) != 15 or any(not isinstance(item, (int, float)) or not math.isfinite(float(item)) or item < 0 for item in nodes):
            raise RecoveryError(f"invalid node vector: {expected['caseId']}")
        for key in ("inputResolvedSha256", "radianceOutputSha256", "stdOutputSha256", "runtimeReportRawSha256"):
            if not valid_sha(row.get(key)):
                raise RecoveryError(f"invalid case hash {key}: {expected['caseId']}")
        ordered.append(row)
        hashes[expected["caseId"]] = raw_sha256(path)
    return ordered, hashes


def build(preflight: Path, cases_root: Path, source_run_path: Path, source_jobs_path: Path, source_artifacts_path: Path, authorization_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source_run = load(source_run_path)
    source_jobs = load(source_jobs_path)
    source_artifacts = load(source_artifacts_path)
    authorization = load(authorization_path)
    validate_source_run(source_run)
    validate_jobs(source_jobs)
    bound_artifacts = validate_artifacts(source_artifacts)
    validate_preflight(preflight)
    validate_authorization(authorization)
    rows, case_hashes = validate_cases(cases_root)
    canonical_cases = [
        {"caseId": item["caseId"], "ordinal": item["ordinal"], "seed": item["seed"], "photonHistories": item["photonHistories"]}
        for item in EXPECTED_CASES
    ]
    plan = {
        "schemaVersion": 1,
        "stageId": "mystic-batch-v1",
        "status": "ARTIFACT_ONLY_RECOVERY_PLAN_FROZEN",
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "batchId": BATCH_ID,
        "authorizationRef": AUTHORIZATION_REF,
        "authorizationOrdinal": 7,
        "executionKey": EXECUTION_KEY,
        "manifestRawSha256": MANIFEST_SHA,
        "scientificAdapterRawSha256": ADAPTER_SHA,
        "runtimeLockRawSha256": authorization["runtimeLockRawSha256"],
        "executionWorkflowRawSha256": authorization["executionWorkflowRawSha256"],
        "configuredMcPhotonsSum": 200_000_000,
        "cases": canonical_cases,
        "recoverySourceRunId": SOURCE_RUN_ID,
        "boundary": "artifact-only recovery plan for four already-completed cases; no syntax check, solver, retry, or new scientific execution",
    }
    audit = {
        "schemaVersion": 1,
        "stageId": "g01-fixed-precision-artifact-recovery-v1",
        "status": "SOURCE_ARTIFACTS_VERIFIED_FOR_POSTPROCESS_ONLY",
        "sourceRunId": SOURCE_RUN_ID,
        "sourceRunHeadSha": SOURCE_HEAD_SHA,
        "sourceRunConclusion": source_run["conclusion"],
        "authorizationRef": AUTHORIZATION_REF,
        "authorizationOrdinal": 7,
        "executionKey": EXECUTION_KEY,
        "caseCount": len(rows),
        "configuredMcPhotonsSum": sum(int(row["photonHistories"]) for row in rows),
        "caseResultRawSha256": case_hashes,
        "sourceArtifacts": bound_artifacts,
        "sourcePreflightPlanRawSha256": raw_sha256(preflight / "plan.json"),
        "sourceAuthorizationGuardRawSha256": raw_sha256(preflight / "authorization-guard.json"),
        "canonicalPlanRawSha256": None,
        "scientificExecution": False,
        "postprocessOnly": True,
        "successDoesNotAuthorizeProduction": True,
        "boundary": "recovery validates immutable outputs from run 30878704003 and performs postprocessing only",
    }
    return plan, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-jobs", type=Path, required=True)
    parser.add_argument("--source-artifacts", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-plan", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan, audit = build(args.preflight, args.cases_root, args.source_run, args.source_jobs, args.source_artifacts, args.authorization)
        args.output_plan.parent.mkdir(parents=True, exist_ok=True)
        args.output_plan.write_text(dump(plan))
        audit["canonicalPlanRawSha256"] = raw_sha256(args.output_plan)
        args.output_audit.parent.mkdir(parents=True, exist_ok=True)
        args.output_audit.write_text(dump(audit))
        print(dump(audit), end="")
        return 0
    except Exception as exc:
        print(dump({"schemaVersion": 1, "stageId": "g01-fixed-precision-artifact-recovery-v1", "status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
