#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"


class AuditFailure(RuntimeError):
    pass


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AuditFailure(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close_number(left: Any, right: Any, tolerance: float = 1e-12) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def audit_batch(plan_path: Path, cases_root: Path, aggregate_dir: Path, output_path: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    aggregate_path = aggregate_dir / "aggregate-result.json"
    aggregate_manifest_path = aggregate_dir / "aggregate-manifest.json"
    aggregate = load_json(aggregate_path)
    aggregate_manifest = load_json(aggregate_manifest_path)
    if plan.get("stageId") != STAGE_ID or plan.get("status") != "AUTHORIZED_PLAN":
        raise AuditFailure("wrong plan header")
    if aggregate.get("stageId") != STAGE_ID or aggregate.get("batchId") != plan.get("batchId"):
        raise AuditFailure("aggregate header mismatch")
    if aggregate_manifest.get("resultSha256") != raw_sha256(aggregate_path):
        raise AuditFailure("aggregate result hash mismatch")

    planned = {case["caseId"]: case for case in plan.get("cases", [])}
    paths = sorted(cases_root.rglob("case-result.json"))
    if len(paths) != len(planned):
        raise AuditFailure(f"expected {len(planned)} case results, found {len(paths)}")

    records: dict[str, dict[str, Any]] = {}
    case_hashes: dict[str, str] = {}
    for path in paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in records or case_id not in planned:
            raise AuditFailure(f"unexpected or duplicate case result: {case_id}")
        expected = planned[case_id]
        invariants = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "batchId": plan["batchId"],
            "ordinal": expected["ordinal"],
            "seed": expected["seed"],
            "photonHistories": expected["photonHistories"],
            "manifestRawSha256": plan["manifestRawSha256"],
        }
        stale = {key: (record.get(key), value) for key, value in invariants.items() if record.get(key) != value}
        if stale:
            raise AuditFailure(f"case invariant mismatch for {case_id}: {stale}")
        status = record.get("status")
        if status == "COMPLETED":
            if record.get("syntaxCheckCount") != 1 or record.get("solverExecutionCount") != 1:
                raise AuditFailure(f"completed case has wrong execution counts: {case_id}")
            value = record.get("selectedPhotopicContributionCdM2")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0:
                raise AuditFailure(f"completed case has invalid metric: {case_id}")
            if record.get("structuralFailure") is not None:
                raise AuditFailure(f"completed case carries structural failure: {case_id}")
        elif status == "FAILED":
            if record.get("classification") != "STRUCTURAL_OR_EXECUTION_FAILURE":
                raise AuditFailure(f"failed case has wrong classification: {case_id}")
            if not isinstance(record.get("structuralFailure"), dict):
                raise AuditFailure(f"failed case lacks structural failure: {case_id}")
        else:
            raise AuditFailure(f"invalid case status: {case_id}")
        records[case_id] = record
        case_hashes[case_id] = raw_sha256(path)

    ordered = [records[case["caseId"]] for case in plan["cases"]]
    completed = [record for record in ordered if record["status"] == "COMPLETED"]
    failed = [record for record in ordered if record["status"] == "FAILED"]
    syntax_count = sum(int(record["syntaxCheckCount"]) for record in ordered)
    solver_count = sum(int(record["solverExecutionCount"]) for record in ordered)
    attempted_photons = sum(
        int(record["photonHistories"]) for record in ordered if int(record["solverExecutionCount"]) == 1
    )
    completed_photons = sum(int(record["photonHistories"]) for record in completed)

    expected_status = "COMPLETED" if not failed and len(completed) == len(ordered) else "FAILED"
    expected_classification = (
        "BATCH_COMPLETE_UNCLASSIFIED" if expected_status == "COMPLETED" else "STRUCTURAL_OR_EXECUTION_FAILURE"
    )
    exact = {
        "status": expected_status,
        "classification": expected_classification,
        "caseCount": len(ordered),
        "completeCaseCount": len(completed),
        "failedCaseCount": len(failed),
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": solver_count,
        "attemptedConfiguredMcPhotonsSum": attempted_photons,
        "completedConfiguredMcPhotonsSum": completed_photons,
        "manifestRawSha256": plan["manifestRawSha256"],
        "planRawSha256": raw_sha256(plan_path),
        "scientificInterpretationAssigned": False,
    }
    stale_aggregate = {key: (aggregate.get(key), value) for key, value in exact.items() if aggregate.get(key) != value}
    if stale_aggregate:
        raise AuditFailure(f"aggregate accounting mismatch: {stale_aggregate}")
    if aggregate_manifest.get("caseResultSha256") != case_hashes:
        raise AuditFailure("aggregate manifest case hashes mismatch")

    recomputed_statistics: dict[str, Any] | None = None
    if expected_status == "COMPLETED":
        values = [float(record["selectedPhotopicContributionCdM2"]) for record in completed]
        mean = statistics.fmean(values)
        sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
        cv = sample_std / mean if mean else None
        recomputed_statistics = {
            "values": values,
            "mean": mean,
            "sampleStd": sample_std,
            "coefficientOfVariation": cv,
        }
        reported = aggregate.get("statistics")
        if not isinstance(reported, dict) or reported.get("values") != values:
            raise AuditFailure("aggregate values mismatch")
        for key in ("mean", "sampleStd", "coefficientOfVariation"):
            if not close_number(reported.get(key), recomputed_statistics[key]):
                raise AuditFailure(f"aggregate statistic mismatch: {key}")
    elif aggregate.get("statistics") is not None:
        raise AuditFailure("failed aggregate must not claim complete-batch statistics")

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "status": "PASSED",
        "auditedBatchStatus": expected_status,
        "auditedClassification": expected_classification,
        "scientificInterpretationAssigned": False,
        "caseCount": len(ordered),
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": solver_count,
        "seeds": [record["seed"] for record in ordered],
        "caseResultSha256": case_hashes,
        "aggregateResultSha256": raw_sha256(aggregate_path),
        "aggregateManifestSha256": raw_sha256(aggregate_manifest_path),
        "statistics": recomputed_statistics,
        "boundary": "independent structural and numerical audit only; no physical, observational, or method-agreement validity",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump_json(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--aggregate-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit_batch(args.plan, args.cases_root, args.aggregate_dir, args.output)
        print(dump_json(result), end="")
        return 0
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "FAILED",
            "classification": "STRUCTURAL_OR_EXECUTION_FAILURE",
            "reason": str(exc),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(refusal))
        print(dump_json(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
