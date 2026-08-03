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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AuditFailure(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


def audit(plan_path: Path, cases_root: Path, aggregate_dir: Path, output_path: Path) -> tuple[dict[str, Any], bool]:
    plan = load_json(plan_path)
    summary_path = aggregate_dir / "batch-summary.json"
    summary = load_json(summary_path)
    planned = {case["caseId"]: case for case in plan.get("cases", [])}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    records: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for path in result_paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in records:
            failures.append({"code": "duplicate-or-invalid-case", "path": str(path)})
            continue
        records[case_id] = record
        expected = planned.get(case_id)
        if expected is None:
            failures.append({"code": "unplanned-case", "caseId": case_id})
            continue
        for key, expected_value in {
            "ordinal": expected["ordinal"],
            "seed": expected["seed"],
            "photonHistories": expected["photonHistories"],
            "manifestRawSha256": plan["manifestRawSha256"],
            "adapterRawSha256": plan["scientificAdapterRawSha256"],
        }.items():
            if record.get(key) != expected_value:
                failures.append({"code": "case-invariant", "caseId": case_id, "field": key, "actual": record.get(key), "expected": expected_value})
        if record.get("syntaxCheckCount") != 1:
            failures.append({"code": "syntax-count", "caseId": case_id, "actual": record.get("syntaxCheckCount")})
        if record.get("solverExecutionCount") != 1:
            failures.append({"code": "solver-count", "caseId": case_id, "actual": record.get("solverExecutionCount")})
        if record.get("status") == "COMPLETED":
            syntax = record.get("syntax")
            solver = record.get("solver")
            if not isinstance(syntax, dict) or syntax.get("timedOut") is not False or syntax.get("exitCode") != 0:
                failures.append({"code": "syntax-status", "caseId": case_id, "detail": syntax})
            if not isinstance(solver, dict) or solver.get("timedOut") is not False or solver.get("exitCode") != 0:
                failures.append({"code": "solver-status", "caseId": case_id, "detail": solver})
            hashes = (record.get("inputResolvedSha256"), record.get("radianceOutputSha256"), record.get("stdOutputSha256"), record.get("runtimeReportRawSha256"))
            if any(not isinstance(item, str) or len(item) != 64 for item in hashes):
                failures.append({"code": "output-hash", "caseId": case_id})

    missing = sorted(set(planned) - set(records))
    if missing:
        failures.append({"code": "missing-cases", "caseIds": missing})
    completed = [records[case_id] for case_id in planned if case_id in records and records[case_id].get("status") == "COMPLETED"]
    values = [float(record["selectedPhotopicContributionCdM2"]) for record in completed]
    complete = not failures and len(completed) == len(planned)

    expected_classification = "BATCH_NUMERICALLY_COMPLETE" if complete else "STRUCTURAL_OR_EXECUTION_FAILURE"
    if summary.get("classification") != expected_classification:
        failures.append({"code": "summary-classification", "actual": summary.get("classification"), "expected": expected_classification})
    if summary.get("caseCountPlanned") != len(planned):
        failures.append({"code": "summary-case-count"})
    if summary.get("manifestRawSha256") != plan.get("manifestRawSha256"):
        failures.append({"code": "summary-manifest-hash"})
    if summary.get("syntaxCheckCount") != len(planned) or summary.get("solverExecutionCount") != len(planned):
        failures.append({"code": "summary-execution-counts", "syntax": summary.get("syntaxCheckCount"), "solver": summary.get("solverExecutionCount")})
    if summary.get("completedConfiguredMcPhotonsSum") != plan.get("configuredMcPhotonsSum"):
        failures.append({"code": "summary-photon-accounting"})

    if complete:
        mean = statistics.fmean(values)
        sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
        cv = sample_std / mean if mean else 0.0
        stats = summary.get("statistics")
        if not isinstance(stats, dict):
            failures.append({"code": "summary-statistics-missing"})
        else:
            for key, expected in {"mean": mean, "sampleStd": sample_std, "coefficientOfVariation": cv}.items():
                actual = stats.get(key)
                if not isinstance(actual, (int, float)) or not close(float(actual), expected):
                    failures.append({"code": "summary-statistic", "field": key, "actual": actual, "expected": expected})

    audit_passed = not failures
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PASSED" if audit_passed else "FAILED",
        "batchClassification": expected_classification,
        "successDoesNotAuthorizeProduction": True,
        "planRawSha256": raw_sha256(plan_path),
        "aggregateRawSha256": raw_sha256(summary_path),
        "caseResultCount": len(result_paths),
        "caseResultHashes": {path.parent.name: raw_sha256(path) for path in result_paths},
        "failures": failures,
        "boundary": "independent artifact audit only; no physical or observational validity claim",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump(report))
    return report, audit_passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--aggregate-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report, passed = audit(args.plan, args.cases_root, args.aggregate_dir, args.output)
        print(dump(report), end="")
        return 0 if passed else 2
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
