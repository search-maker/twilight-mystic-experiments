#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"


class AggregateRefusal(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AggregateRefusal(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def aggregate(plan_path: Path, cases_root: Path, output_dir: Path) -> tuple[dict[str, Any], bool]:
    plan = load_json(plan_path)
    if plan.get("stageId") != STAGE_ID or plan.get("scientificExecution") is not True:
        raise AggregateRefusal("wrong scientific plan")
    planned = {case["caseId"]: case for case in plan.get("cases", [])}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    records: dict[str, dict[str, Any]] = {}
    index: list[dict[str, Any]] = []
    structural_failures: list[dict[str, Any]] = []

    for path in result_paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in records:
            structural_failures.append({"code": "duplicate-or-missing-case-id", "path": str(path)})
            continue
        expected = planned.get(case_id)
        if expected is None:
            structural_failures.append({"code": "unplanned-case", "caseId": case_id, "path": str(path)})
            continue
        required = {
            "stageId": STAGE_ID,
            "batchId": plan["batchId"],
            "ordinal": expected["ordinal"],
            "seed": expected["seed"],
            "photonHistories": expected["photonHistories"],
            "manifestRawSha256": plan["manifestRawSha256"],
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
        }
        stale = {key: (record.get(key), value) for key, value in required.items() if record.get(key) != value}
        if stale:
            structural_failures.append({"code": "case-invariant", "caseId": case_id, "detail": stale})
        records[case_id] = record
        index.append({"caseId": case_id, "path": str(path), "caseResultSha256": raw_sha256(path)})

    missing = sorted(set(planned) - set(records))
    if missing:
        structural_failures.append({"code": "missing-cases", "caseIds": missing})
    extra_count = len(result_paths) - len(records)
    if extra_count:
        structural_failures.append({"code": "unusable-results", "count": extra_count})

    ordered = [records[case["caseId"]] for case in plan["cases"] if case["caseId"] in records]
    completed = [record for record in ordered if record.get("status") == "COMPLETED"]
    failed = [record for record in ordered if record.get("status") != "COMPLETED"]
    syntax_count = sum(int(record.get("syntaxCheckCount", 0)) for record in ordered)
    solver_count = sum(int(record.get("solverExecutionCount", 0)) for record in ordered)
    values = [float(record["selectedPhotopicContributionCdM2"]) for record in completed if isinstance(record.get("selectedPhotopicContributionCdM2"), (int, float))]

    complete = not structural_failures and not failed and len(completed) == len(planned)
    if complete:
        mean = statistics.fmean(values)
        sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
        cv = sample_std / mean if mean else 0.0
        statistics_block: dict[str, Any] | None = {
            "values": values,
            "mean": mean,
            "sampleStd": sample_std,
            "coefficientOfVariation": cv,
        }
        classification = "BATCH_NUMERICALLY_COMPLETE"
        status = "COMPLETED"
    else:
        statistics_block = None
        classification = "STRUCTURAL_OR_EXECUTION_FAILURE"
        status = "FAILED"

    summary = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": status,
        "classification": classification,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "batchId": plan["batchId"],
        "manifestRawSha256": plan["manifestRawSha256"],
        "authorizationRef": plan["authorizationRef"],
        "caseCountPlanned": len(planned),
        "caseCountCompleted": len(completed),
        "caseCountFailed": len(failed),
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": solver_count,
        "configuredMcPhotonsSum": plan["configuredMcPhotonsSum"],
        "statistics": statistics_block,
        "structuralFailures": structural_failures,
        "failedCases": [{"caseId": record.get("caseId"), "failure": record.get("failure")} for record in failed],
        "caseIndex": sorted(index, key=lambda item: item["caseId"]),
        "boundary": "numerical completion only; no physical, observational, surrogate, LUT, or production validity claim",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "batch-summary.json").write_text(dump(summary))
    return summary, complete


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary, complete = aggregate(args.plan, args.cases_root, args.output_dir)
        print(dump(summary), end="")
        return 0 if complete else 2
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
