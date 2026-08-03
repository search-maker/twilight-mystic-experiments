#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
GENERIC_STAGE_ID = "mystic-batch-v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PACKAGE = Path("experiments/mystic-batch-v1")
SOURCE_PATHS = {
    "authorization": PACKAGE / "authorization.cross-geometry.json",
    "proposal": PACKAGE / "manifest.cross-geometry-pilot.proposal.json",
    "contract": PACKAGE / "cross-geometry-contract.json",
    "proposalAdapter": PACKAGE / "cross_geometry_adapter.py",
    "proposalValidator": PACKAGE / "cross_geometry_validate.py",
    "executionAdapter": PACKAGE / "cross_geometry_execution_adapter.py",
    "executionWorkflow": Path(".github/workflows/mystic-batch-v1-cross-geometry-execution.yml"),
    "runtimeLock": PACKAGE / "runtime-lock.micromamba.json",
    "plan": PACKAGE / "cross_geometry_execution_plan.py",
    "analysisDriver": PACKAGE / "cross_geometry_execution_analysis_driver.py",
    "executor": PACKAGE / "scientific_case_executor.py",
    "aggregate": PACKAGE / "scientific_aggregate.py",
    "audit": PACKAGE / "scientific_audit.py",
}
AUTH_HASH_FIELDS = {
    "proposal": "proposalRawSha256",
    "contract": "contractRawSha256",
    "proposalAdapter": "proposalAdapterRawSha256",
    "proposalValidator": "proposalValidatorRawSha256",
    "executionAdapter": "executionAdapterRawSha256",
    "executionWorkflow": "executionWorkflowRawSha256",
    "runtimeLock": "runtimeLockRawSha256",
    "plan": "planRawSha256",
    "analysisDriver": "analysisDriverRawSha256",
    "executor": "executorRawSha256",
    "aggregate": "aggregateRawSha256",
    "audit": "auditRawSha256",
}


class PostprocessRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise PostprocessRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PostprocessRefusal(f"cannot load source module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise PostprocessRefusal(f"invalid SHA-256 binding: {name}")
    return value


def verify_source_repository(root: Path, authorization_ref: str) -> tuple[dict[str, Any], dict[str, Path]]:
    source_root = root.resolve()
    paths = {name: source_root / rel for name, rel in SOURCE_PATHS.items()}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise PostprocessRefusal(f"source repository is missing bound files: {missing}")

    head = git(source_root, "rev-parse", "HEAD")
    parent = git(source_root, "rev-parse", "HEAD^")
    if head != authorization_ref:
        raise PostprocessRefusal(f"source checkout is not authorization ref: {head}")
    authorization = load_json(paths["authorization"])
    if authorization.get("exactAuthorizationParentCommit") != parent:
        raise PostprocessRefusal("source authorization parent mismatch")
    changed = git(source_root, "diff", "--name-only", parent, head).splitlines()
    if changed != [SOURCE_PATHS["authorization"].as_posix()]:
        raise PostprocessRefusal(f"authorization commit is not one-purpose: {changed}")

    for name, auth_field in AUTH_HASH_FIELDS.items():
        expected = require_sha(authorization.get(auth_field), auth_field)
        actual = raw_sha256(paths[name])
        if actual != expected:
            raise PostprocessRefusal(f"source file hash mismatch: {name}")
    return authorization, paths


def recover_plan(
    source_plan: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    guard: dict[str, Any],
    duplicate: dict[str, Any],
    authorization_ref: str,
    execution_key: str,
    authorization_ordinal: int,
) -> dict[str, Any]:
    required_auth = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "authorized": True,
        "scientificExecution": True,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "executionKey": execution_key,
        "authorizationOrdinal": authorization_ordinal,
        "batchId": proposal.get("batchId"),
    }
    stale_auth = {key: (authorization.get(key), value) for key, value in required_auth.items() if authorization.get(key) != value}
    if stale_auth:
        raise PostprocessRefusal(f"source authorization does not match requested recovery: {stale_auth}")

    required_guard = {
        "status": "AUTHORIZED",
        "stageId": STAGE_ID,
        "authorizationRef": authorization_ref,
        "executionKey": execution_key,
        "authorizationOrdinal": authorization_ordinal,
        "batchId": proposal.get("batchId"),
        "proposalRawSha256": authorization.get("proposalRawSha256"),
        "caseCount": 24,
        "configuredMcPhotonsSum": 480_000_000,
    }
    stale_guard = {key: (guard.get(key), value) for key, value in required_guard.items() if guard.get(key) != value}
    if stale_guard:
        raise PostprocessRefusal(f"source guard report mismatch: {stale_guard}")

    if duplicate.get("status") != "PASS" or duplicate.get("currentRunId") is None:
        raise PostprocessRefusal("source duplicate-run audit did not pass")
    marker = duplicate.get("displayTitle")
    expected_suffix = f"key={execution_key} | auth={authorization_ref} | ordinal={authorization_ordinal}"
    if not isinstance(marker, str) or not marker.endswith(expected_suffix):
        raise PostprocessRefusal("source duplicate-run marker mismatch")

    cases = proposal.get("cases")
    limits = proposal.get("limits")
    if not isinstance(cases, list) or not isinstance(limits, dict):
        raise PostprocessRefusal("source proposal cases or limits malformed")
    ordered = sorted(cases, key=lambda case: case["ordinal"])
    photon_sum = sum(case["photonHistories"] for case in ordered)
    if len(ordered) != 24 or photon_sum != 480_000_000:
        raise PostprocessRefusal("source proposal accounting changed")

    required_plan = {
        "schemaVersion": 1,
        "stageId": GENERIC_STAGE_ID,
        "scientificPurpose": STAGE_ID,
        "batchId": proposal.get("batchId"),
        "mode": "scientific",
        "scientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "manifestRawSha256": authorization.get("proposalRawSha256"),
        "authorizationRef": authorization_ref,
        "authorizationOrdinal": authorization_ordinal,
        "executionKey": execution_key,
        "caseCount": 24,
        "configuredMcPhotonsSum": 480_000_000,
        "cases": ordered,
    }
    stale_plan = {key: (source_plan.get(key), value) for key, value in required_plan.items() if source_plan.get(key) != value}
    if stale_plan:
        raise PostprocessRefusal(f"source plan mismatch: {stale_plan}")

    recovered = {
        **source_plan,
        "scientificAdapterRawSha256": require_sha(authorization.get("executionAdapterRawSha256"), "executionAdapterRawSha256"),
        "runtimeLockRawSha256": require_sha(authorization.get("runtimeLockRawSha256"), "runtimeLockRawSha256"),
        "executionWorkflowRawSha256": require_sha(authorization.get("executionWorkflowRawSha256"), "executionWorkflowRawSha256"),
        "recoveredFromRunId": duplicate["currentRunId"],
        "recoveryReason": "source execution plan predated generic aggregate compatibility bindings",
        "boundary": "artifact-only recovery; no syntax check, uvspec process, MYSTIC solver, or retry executed",
    }
    return recovered


def postprocess(
    source_repository_root: Path,
    source_run_id: int,
    source_authorization_ref: str,
    expected_execution_key: str,
    expected_authorization_ordinal: int,
    source_plan_path: Path,
    guard_report_path: Path,
    duplicate_report_path: Path,
    cases_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    authorization, paths = verify_source_repository(source_repository_root, source_authorization_ref)
    proposal = load_json(paths["proposal"])
    source_plan = load_json(source_plan_path)
    guard = load_json(guard_report_path)
    duplicate = load_json(duplicate_report_path)
    if duplicate.get("currentRunId") != source_run_id:
        raise PostprocessRefusal("source run ID does not match duplicate-run audit")

    recovered_plan = recover_plan(
        source_plan,
        proposal,
        authorization,
        guard,
        duplicate,
        source_authorization_ref,
        expected_execution_key,
        expected_authorization_ordinal,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    recovered_plan_path = output_dir / "recovered-plan.json"
    recovered_plan_path.write_text(dump(recovered_plan))

    aggregate_module = load_module("source_scientific_aggregate", paths["aggregate"])
    audit_module = load_module("source_scientific_audit", paths["audit"])
    analysis_module = load_module("source_cross_geometry_analysis_driver", paths["analysisDriver"])

    aggregate_dir = output_dir / "aggregate"
    summary, aggregate_complete = aggregate_module.aggregate(recovered_plan_path, cases_root, aggregate_dir)
    if not aggregate_complete or summary.get("classification") != "BATCH_NUMERICALLY_COMPLETE":
        raise PostprocessRefusal(f"source aggregate did not complete: {summary.get('structuralFailures')}")

    audit_path = output_dir / "audit" / "audit-report.json"
    audit, audit_passed = audit_module.audit(recovered_plan_path, cases_root, aggregate_dir, audit_path)
    if not audit_passed or audit.get("status") != "PASSED":
        raise PostprocessRefusal(f"source independent audit failed: {audit.get('failures')}")

    screening_dir = output_dir / "screening"
    screening, screening_passed = analysis_module.analyze_artifacts(
        paths["proposal"],
        paths["contract"],
        cases_root,
        aggregate_dir / "batch-summary.json",
        audit_path,
        screening_dir,
    )
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "POSTPROCESS_COMPLETED" if screening_passed else "POSTPROCESS_SCREENING_REQUIRES_FOLLOWUP",
        "sourceRunId": source_run_id,
        "sourceAuthorizationRef": source_authorization_ref,
        "executionKey": expected_execution_key,
        "authorizationOrdinal": expected_authorization_ordinal,
        "caseCount": summary.get("caseCountCompleted"),
        "configuredMcPhotonsSum": summary.get("configuredMcPhotonsSum"),
        "aggregateClassification": summary.get("classification"),
        "auditStatus": audit.get("status"),
        "screeningStatus": screening.get("status"),
        "screeningClassificationCounts": screening.get("classificationCounts"),
        "recoveredPlanRawSha256": raw_sha256(recovered_plan_path),
        "aggregateRawSha256": raw_sha256(aggregate_dir / "batch-summary.json"),
        "auditRawSha256": raw_sha256(audit_path),
        "screeningRawSha256": raw_sha256(screening_dir / "screening-analysis.json"),
        "boundary": "post-processing of preserved artifacts only; no syntax check, uvspec, MYSTIC solver, or retry executed",
    }
    (output_dir / "postprocess-report.json").write_text(dump(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repository-root", type=Path, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--source-authorization-ref", required=True)
    parser.add_argument("--expected-execution-key", required=True)
    parser.add_argument("--expected-authorization-ordinal", type=int, required=True)
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--guard-report", type=Path, required=True)
    parser.add_argument("--duplicate-report", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = postprocess(
            args.source_repository_root,
            args.source_run_id,
            args.source_authorization_ref,
            args.expected_execution_key,
            args.expected_authorization_ordinal,
            args.source_plan,
            args.guard_report,
            args.duplicate_report,
            args.cases_root,
            args.output_dir,
        )
        print(dump(report), end="")
        return 0
    except Exception as exc:
        refusal = {"schemaVersion": 1, "stageId": STAGE_ID, "status": "REFUSED", "reason": str(exc)}
        print(dump(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
