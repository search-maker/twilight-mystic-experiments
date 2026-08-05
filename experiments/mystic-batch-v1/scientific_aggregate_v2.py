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
SCHEMA_VERSION = 2
NODE_COUNT = 15


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


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def numeric_vector(value: Any, length: int) -> list[float] | None:
    if not isinstance(value, list) or len(value) != length or not all(finite_number(item) for item in value):
        return None
    return [float(item) for item in value]


def group_statistics(values: list[float], zero_hit_count: int) -> dict[str, Any]:
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
    if zero_hit_count:
        cv = None
        cv_status = "NOT_COMPUTED_ZERO_HIT_PRESENT"
    elif mean == 0.0:
        cv = None
        cv_status = "NOT_COMPUTED_ZERO_MEAN"
    else:
        cv = sample_std / mean
        cv_status = "COMPUTED"
    return {
        "values": values,
        "mean": mean,
        "sampleStd": sample_std,
        "coefficientOfVariation": cv,
        "coefficientOfVariationStatus": cv_status,
        "zeroHitCount": zero_hit_count,
        "zeroHitFraction": zero_hit_count / len(values),
    }


def aggregate(plan_path: Path, cases_root: Path, output_dir: Path) -> tuple[dict[str, Any], bool]:
    plan = load_json(plan_path)
    if plan.get("stageId") != STAGE_ID or plan.get("scientificExecution") is not True:
        raise AggregateRefusal("wrong scientific plan")
    planned = {case["caseId"]: case for case in plan.get("cases", [])}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    records: dict[str, dict[str, Any]] = {}
    case_validity: dict[str, bool] = {}
    index: list[dict[str, Any]] = []
    structural_failures: list[dict[str, Any]] = []
    zero_hit_diagnostics: list[dict[str, Any]] = []
    cases_by_seed: dict[Any, list[str]] = {}
    for case_id, case in planned.items():
        cases_by_seed.setdefault(case.get("seed"), []).append(case_id)
    duplicate_seed_case_ids = {
        case_id for case_ids in cases_by_seed.values() if len(case_ids) > 1 for case_id in case_ids
    }
    if duplicate_seed_case_ids:
        structural_failures.append(
            {"code": "duplicate-planned-seeds", "caseIds": sorted(duplicate_seed_case_ids)}
        )

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
        failure_count_before = len(structural_failures)
        required = {
            "stageId": STAGE_ID,
            "batchId": plan["batchId"],
            "ordinal": expected["ordinal"],
            "seed": expected["seed"],
            "photonHistories": expected["photonHistories"],
            "manifestRawSha256": plan["manifestRawSha256"],
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "adapterRawSha256": plan["scientificAdapterRawSha256"],
        }
        stale = {key: (record.get(key), value) for key, value in required.items() if record.get(key) != value}
        if stale:
            structural_failures.append({"code": "case-invariant", "caseId": case_id, "detail": stale})
        if record.get("syntaxCheckCount") != 1 or record.get("solverExecutionCount") != 1:
            structural_failures.append(
                {
                    "code": "execution-count",
                    "caseId": case_id,
                    "syntax": record.get("syntaxCheckCount"),
                    "solver": record.get("solverExecutionCount"),
                }
            )
        syntax = record.get("syntax")
        solver = record.get("solver")
        if record.get("status") == "COMPLETED":
            if not isinstance(syntax, dict) or syntax.get("timedOut") is not False or syntax.get("exitCode") != 0:
                structural_failures.append({"code": "syntax-status", "caseId": case_id, "detail": syntax})
            if not isinstance(solver, dict) or solver.get("timedOut") is not False or solver.get("exitCode") != 0:
                structural_failures.append({"code": "solver-status", "caseId": case_id, "detail": solver})
            value = record.get("selectedPhotopicContributionCdM2")
            selected = numeric_vector(record.get("selectedNodeRadiance"), NODE_COUNT)
            selected_std = numeric_vector(record.get("selectedNodeStdRadiance"), NODE_COUNT)
            hashes = (
                record.get("inputResolvedSha256"),
                record.get("radianceOutputSha256"),
                record.get("stdOutputSha256"),
                record.get("runtimeReportRawSha256"),
            )
            if not finite_number(value) or float(value) < 0.0:
                structural_failures.append({"code": "photopic-value", "caseId": case_id, "detail": value})
            if selected is None or any(item < 0.0 for item in selected):
                structural_failures.append({"code": "selected-radiance", "caseId": case_id})
            if selected_std is None or any(item < 0.0 for item in selected_std):
                structural_failures.append({"code": "selected-standard-radiance", "caseId": case_id})
            if any(not valid_sha256(item) for item in hashes):
                structural_failures.append({"code": "output-hash", "caseId": case_id})
            if finite_number(value) and selected is not None:
                zero_value = float(value) == 0.0
                zero_nodes = all(item == 0.0 for item in selected)
                if zero_value != zero_nodes:
                    structural_failures.append(
                        {
                            "code": "zero-estimator-inconsistent",
                            "caseId": case_id,
                            "photopicZero": zero_value,
                            "selectedNodesAllZero": zero_nodes,
                        }
                    )
                elif zero_value:
                    zero_hit_diagnostics.append(
                        {
                            "caseId": case_id,
                            "geometryId": expected.get("groupId", case_id),
                            "block": expected.get("block"),
                            "seed": expected["seed"],
                            "photonHistories": expected["photonHistories"],
                            "selectedPhotopicContributionCdM2": 0.0,
                            "selectedNodeNonzeroCount": 0,
                            "classification": "NUMERICAL_ZERO_HIT_UNDERCONVERGED",
                            "executionComplete": True,
                            "scientificallyEligible": False,
                        }
                    )
        records[case_id] = record
        case_validity[case_id] = (
            record.get("status") == "COMPLETED"
            and case_id not in duplicate_seed_case_ids
            and len(structural_failures) == failure_count_before
        )
        index.append(
            {
                "caseId": case_id,
                "path": path.relative_to(cases_root).as_posix(),
                "caseResultSha256": raw_sha256(path),
            }
        )

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
    values = [
        float(record["selectedPhotopicContributionCdM2"])
        for record in completed
        if finite_number(record.get("selectedPhotopicContributionCdM2"))
    ]

    group_cases: dict[str, list[dict[str, Any]]] = {}
    for expected in plan["cases"]:
        group_cases.setdefault(expected.get("groupId", expected["caseId"]), []).append(expected)
    zero_by_case = {item["caseId"] for item in zero_hit_diagnostics}
    geometry_results: list[dict[str, Any]] = []
    for group_id in sorted(group_cases):
        expected_cases = group_cases[group_id]
        group_records = [records[item["caseId"]] for item in expected_cases if item["caseId"] in records]
        group_completed = [item for item in group_records if item.get("status") == "COMPLETED"]
        group_values = [
            float(item["selectedPhotopicContributionCdM2"])
            for item in group_completed
            if finite_number(item.get("selectedPhotopicContributionCdM2"))
        ]
        zero_case_ids = sorted(item["caseId"] for item in expected_cases if item["caseId"] in zero_by_case)
        execution_complete = (
            len(group_completed) == len(expected_cases)
            and all(case_validity.get(item["caseId"], False) for item in expected_cases)
        )
        if not execution_complete or len(group_values) != len(expected_cases):
            classification = "STRUCTURAL_OR_EXECUTION_FAILURE"
            numerical_status = "INCOMPLETE"
            stats = None
        elif zero_case_ids:
            classification = "ADAPTIVE_CONTINUATION_REQUIRED"
            numerical_status = "NUMERICAL_ZERO_HIT_UNDERCONVERGED"
            stats = group_statistics(group_values, len(zero_case_ids))
        else:
            classification = "BATCH_NUMERICALLY_COMPLETE"
            numerical_status = "NUMERIC_ESTIMATES_AVAILABLE"
            stats = group_statistics(group_values, 0)
        roles = sorted({item.get("role") for item in expected_cases if isinstance(item.get("role"), str)})
        geometry_results.append(
            {
                "geometryId": group_id,
                "caseIds": sorted(item["caseId"] for item in expected_cases),
                "roles": roles,
                "caseCountPlanned": len(expected_cases),
                "caseCountCompleted": len(group_completed),
                "zeroHitCaseIds": zero_case_ids,
                "executionComplete": execution_complete,
                "scientificallyEligible": False,
                "scientificEligibilityPendingPrecisionAnalysis": execution_complete and not zero_case_ids,
                "classification": classification,
                "numericalStatus": numerical_status,
                "statistics": stats,
            }
        )

    execution_complete = not structural_failures and not failed and len(completed) == len(planned)
    if not execution_complete:
        statistics_block: dict[str, Any] | None = None
        classification = "STRUCTURAL_OR_EXECUTION_FAILURE"
        status = "FAILED"
    elif zero_hit_diagnostics:
        statistics_block = group_statistics(values, len(zero_hit_diagnostics))
        classification = "SCIENTIFICALLY_INELIGIBLE"
        status = "COMPLETED"
    else:
        statistics_block = group_statistics(values, 0)
        classification = "BATCH_NUMERICALLY_COMPLETE"
        status = "COMPLETED"

    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "stageId": STAGE_ID,
        "status": status,
        "classification": classification,
        "executionComplete": execution_complete,
        "scientificallyEligible": False,
        "scientificEligibilityPendingPrecisionAnalysis": execution_complete and not zero_hit_diagnostics,
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
        "completedConfiguredMcPhotonsSum": sum(int(record.get("photonHistories", 0)) for record in completed),
        "scientificAdapterRawSha256": plan["scientificAdapterRawSha256"],
        "runtimeLockRawSha256": plan["runtimeLockRawSha256"],
        "executionWorkflowRawSha256": plan["executionWorkflowRawSha256"],
        "statistics": statistics_block,
        "zeroHitCaseCount": len(zero_hit_diagnostics),
        "zeroHitDiagnostics": zero_hit_diagnostics,
        "continuationRequiredGeometryIds": [
            item["geometryId"]
            for item in geometry_results
            if item["classification"] == "ADAPTIVE_CONTINUATION_REQUIRED"
        ],
        "geometryResults": geometry_results,
        "structuralFailures": structural_failures,
        "failedCases": [{"caseId": record.get("caseId"), "failure": record.get("failure")} for record in failed],
        "caseIndex": sorted(index, key=lambda item: item["caseId"]),
        "boundary": "execution accounting and numerical-estimator classification only; no physical, observational, surrogate, LUT, or production validity claim",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "batch-summary.json").write_text(dump(summary))
    return summary, execution_complete


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary, execution_complete = aggregate(args.plan, args.cases_root, args.output_dir)
        print(dump(summary), end="")
        return 0 if execution_complete else 2
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
