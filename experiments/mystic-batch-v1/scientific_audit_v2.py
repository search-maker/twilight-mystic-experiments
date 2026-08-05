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
NODES = [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660]
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


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


def estimator_close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-30)


def luminance(values: list[float]) -> float:
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(values, CIE))


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def numeric_vector(value: Any, length: int) -> list[float] | None:
    if not isinstance(value, list) or len(value) != length or not all(finite_number(item) for item in value):
        return None
    return [float(item) for item in value]


def parse_spectrum(path: Path) -> dict[str, Any]:
    line_count = 0
    value_count = 0
    nonzero_count = 0
    selected: dict[int, float] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        columns = line.split()
        if len(columns) < 2:
            raise AuditFailure(f"malformed spectrum {path}:{line_number}")
        try:
            numbers = [float(item) for item in columns]
        except ValueError as exc:
            raise AuditFailure(f"nonnumeric spectrum {path}:{line_number}") from exc
        if not all(math.isfinite(item) for item in numbers):
            raise AuditFailure(f"nonfinite spectrum {path}:{line_number}")
        line_count += 1
        value_count += len(numbers) - 1
        nonzero_count += sum(item != 0.0 for item in numbers[1:])
        for node in NODES:
            if abs(numbers[0] - node) <= 1e-7:
                selected[node] = numbers[-1]
    if line_count == 0:
        raise AuditFailure(f"empty spectrum {path}")
    if sorted(selected) != NODES:
        raise AuditFailure(f"missing diagnostic nodes in {path}: {sorted(selected)}")
    return {
        "lineCount": line_count,
        "valueCount": value_count,
        "nonzeroValueCount": nonzero_count,
        "allEstimatorValuesZero": nonzero_count == 0,
        "selectedNodeValues": [selected[node] for node in NODES],
        "rawSha256": raw_sha256(path),
    }


def runtime_report_path(cases_root: Path, result_path: Path, case_id: str) -> Path | None:
    candidates = [
        cases_root / "runtime-reports" / case_id / "runtime-report.json",
        result_path.parent / "runtime-report.json",
    ]
    return next((path for path in candidates if path.is_file()), None)


def expected_group_statistics(values: list[float], zero_count: int) -> dict[str, Any]:
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
    cv = None if zero_count or mean == 0.0 else sample_std / mean
    return {
        "values": values,
        "mean": mean,
        "sampleStd": sample_std,
        "coefficientOfVariation": cv,
        "coefficientOfVariationStatus": (
            "NOT_COMPUTED_ZERO_HIT_PRESENT"
            if zero_count
            else "NOT_COMPUTED_ZERO_MEAN"
            if mean == 0.0
            else "COMPUTED"
        ),
        "zeroHitCount": zero_count,
        "zeroHitFraction": zero_count / len(values),
    }


def audit(plan_path: Path, cases_root: Path, aggregate_dir: Path, output_path: Path) -> tuple[dict[str, Any], bool]:
    plan = load_json(plan_path)
    summary_path = aggregate_dir / "batch-summary.json"
    summary = load_json(summary_path)
    planned = {case["caseId"]: case for case in plan.get("cases", [])}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    records: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    zero_hit_diagnostics: list[dict[str, Any]] = []
    raw_case_evidence: dict[str, dict[str, Any]] = {}

    planned_seeds = [case.get("seed") for case in planned.values()]
    if len(set(planned_seeds)) != len(planned_seeds):
        failures.append({"code": "duplicate-planned-seeds"})
    groups: dict[str, list[dict[str, Any]]] = {}
    for expected in planned.values():
        groups.setdefault(expected.get("groupId", expected["caseId"]), []).append(expected)
    for group_id, group in groups.items():
        blocks = [item.get("block") for item in group if item.get("block") is not None]
        roles = {item.get("role") for item in group if item.get("role") is not None}
        if blocks and len(set(blocks)) != len(blocks):
            failures.append({"code": "duplicate-block", "geometryId": group_id})
        if len(roles) > 1:
            failures.append({"code": "mixed-geometry-role", "geometryId": group_id})

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
                failures.append(
                    {
                        "code": "case-invariant",
                        "caseId": case_id,
                        "field": key,
                        "actual": record.get(key),
                        "expected": expected_value,
                    }
                )
        if record.get("syntaxCheckCount") != 1:
            failures.append({"code": "syntax-count", "caseId": case_id, "actual": record.get("syntaxCheckCount")})
        if record.get("solverExecutionCount") != 1:
            failures.append({"code": "solver-count", "caseId": case_id, "actual": record.get("solverExecutionCount")})
        if record.get("status") != "COMPLETED":
            failures.append({"code": "case-execution-status", "caseId": case_id, "status": record.get("status")})
            continue
        syntax = record.get("syntax")
        solver = record.get("solver")
        if not isinstance(syntax, dict) or syntax.get("timedOut") is not False or syntax.get("exitCode") != 0:
            failures.append({"code": "syntax-status", "caseId": case_id, "detail": syntax})
        if not isinstance(solver, dict) or solver.get("timedOut") is not False or solver.get("exitCode") != 0:
            failures.append({"code": "solver-status", "caseId": case_id, "detail": solver})
        value = record.get("selectedPhotopicContributionCdM2")
        selected = numeric_vector(record.get("selectedNodeRadiance"), NODE_COUNT)
        selected_std = numeric_vector(record.get("selectedNodeStdRadiance"), NODE_COUNT)
        if not finite_number(value) or float(value) < 0.0:
            failures.append({"code": "photopic-value", "caseId": case_id, "detail": value})
            continue
        if selected is None or any(item < 0.0 for item in selected):
            failures.append({"code": "selected-radiance", "caseId": case_id})
            continue
        if selected_std is None or any(item < 0.0 for item in selected_std):
            failures.append({"code": "selected-standard-radiance", "caseId": case_id})
            continue

        input_path = path.parent / "input-resolved.txt"
        radiance_path = path.parent / "mc.rad.spc"
        std_path = path.parent / "mc.rad.std.spc"
        runtime_path = runtime_report_path(cases_root, path, case_id)
        required_paths = {
            "input": input_path,
            "radiance": radiance_path,
            "standardRadiance": std_path,
            "runtimeReport": runtime_path,
        }
        missing_raw = [name for name, candidate in required_paths.items() if candidate is None or not candidate.is_file()]
        if missing_raw:
            failures.append({"code": "missing-raw-output", "caseId": case_id, "files": missing_raw})
            continue
        assert runtime_path is not None
        expected_hashes = {
            "inputResolvedSha256": raw_sha256(input_path),
            "radianceOutputSha256": raw_sha256(radiance_path),
            "stdOutputSha256": raw_sha256(std_path),
            "runtimeReportRawSha256": raw_sha256(runtime_path),
        }
        for field, expected_hash in expected_hashes.items():
            if record.get(field) != expected_hash:
                failures.append(
                    {
                        "code": "raw-output-hash",
                        "caseId": case_id,
                        "field": field,
                        "actual": record.get(field),
                        "expected": expected_hash,
                    }
                )
        try:
            radiance = parse_spectrum(radiance_path)
            standard_radiance = parse_spectrum(std_path)
        except AuditFailure as exc:
            failures.append({"code": "malformed-raw-spectrum", "caseId": case_id, "detail": str(exc)})
            continue
        raw_case_evidence[case_id] = {
            "caseResultRawSha256": raw_sha256(path),
            "inputResolvedRawSha256": expected_hashes["inputResolvedSha256"],
            "runtimeReportRawSha256": expected_hashes["runtimeReportRawSha256"],
            "radiance": radiance,
            "standardRadiance": standard_radiance,
        }
        zero_value = float(value) == 0.0
        zero_nodes = all(item == 0.0 for item in selected)
        raw_zero = radiance["allEstimatorValuesZero"]
        raw_std_zero = standard_radiance["allEstimatorValuesZero"]
        raw_selected = radiance["selectedNodeValues"]
        raw_selected_std = standard_radiance["selectedNodeValues"]
        raw_photopic = luminance(raw_selected)
        if any(not estimator_close(actual, expected) for actual, expected in zip(selected, raw_selected)):
            failures.append({"code": "selected-radiance-raw-mismatch", "caseId": case_id})
        if any(not estimator_close(actual, expected) for actual, expected in zip(selected_std, raw_selected_std)):
            failures.append({"code": "selected-standard-radiance-raw-mismatch", "caseId": case_id})
        if not estimator_close(float(value), raw_photopic):
            failures.append(
                {
                    "code": "photopic-raw-mismatch",
                    "caseId": case_id,
                    "actual": float(value),
                    "expected": raw_photopic,
                }
            )
        if zero_value:
            if not zero_nodes or not raw_zero or not raw_std_zero:
                failures.append(
                    {
                        "code": "zero-hit-raw-evidence-inconsistent",
                        "caseId": case_id,
                        "selectedNodesAllZero": zero_nodes,
                        "rawRadianceAllZero": raw_zero,
                        "rawStandardRadianceAllZero": raw_std_zero,
                    }
                )
            else:
                zero_hit_diagnostics.append(
                    {
                        "caseId": case_id,
                        "geometryId": expected.get("groupId", case_id),
                        "block": expected.get("block"),
                        "seed": expected["seed"],
                        "photonHistories": expected["photonHistories"],
                        "classification": "NUMERICAL_ZERO_HIT_UNDERCONVERGED",
                        "derivedFromRawOutputs": True,
                    }
                )
        elif zero_nodes or raw_zero:
            failures.append(
                {
                    "code": "positive-estimator-raw-evidence-inconsistent",
                    "caseId": case_id,
                    "selectedNodesAllZero": zero_nodes,
                    "rawRadianceAllZero": raw_zero,
                }
            )

    missing = sorted(set(planned) - set(records))
    if missing:
        failures.append({"code": "missing-cases", "caseIds": missing})
    completed = [records[case_id] for case_id in planned if case_id in records and records[case_id].get("status") == "COMPLETED"]
    execution_complete = not failures and len(completed) == len(planned)
    expected_classification = (
        "STRUCTURAL_OR_EXECUTION_FAILURE"
        if not execution_complete
        else "SCIENTIFICALLY_INELIGIBLE"
        if zero_hit_diagnostics
        else "BATCH_NUMERICALLY_COMPLETE"
    )

    if summary.get("schemaVersion") != SCHEMA_VERSION:
        failures.append({"code": "summary-schema", "actual": summary.get("schemaVersion")})
    if summary.get("classification") != expected_classification:
        failures.append(
            {"code": "summary-classification", "actual": summary.get("classification"), "expected": expected_classification}
        )
    if summary.get("executionComplete") is not execution_complete:
        failures.append({"code": "summary-execution-complete"})
    if summary.get("scientificallyEligible") is not False:
        failures.append({"code": "summary-scientific-eligibility"})
    if summary.get("caseCountPlanned") != len(planned):
        failures.append({"code": "summary-case-count"})
    if summary.get("manifestRawSha256") != plan.get("manifestRawSha256"):
        failures.append({"code": "summary-manifest-hash"})
    if summary.get("syntaxCheckCount") != len(planned) or summary.get("solverExecutionCount") != len(planned):
        failures.append(
            {
                "code": "summary-execution-counts",
                "syntax": summary.get("syntaxCheckCount"),
                "solver": summary.get("solverExecutionCount"),
            }
        )
    if summary.get("completedConfiguredMcPhotonsSum") != plan.get("configuredMcPhotonsSum"):
        failures.append({"code": "summary-photon-accounting"})
    summary_zero_ids = sorted(item.get("caseId") for item in summary.get("zeroHitDiagnostics", []))
    audited_zero_ids = sorted(item["caseId"] for item in zero_hit_diagnostics)
    if summary_zero_ids != audited_zero_ids:
        failures.append(
            {"code": "summary-zero-hit-diagnostics", "actual": summary_zero_ids, "expected": audited_zero_ids}
        )

    geometry_results = summary.get("geometryResults")
    geometry_map = {
        item.get("geometryId"): item
        for item in geometry_results
        if isinstance(item, dict) and isinstance(item.get("geometryId"), str)
    } if isinstance(geometry_results, list) else {}
    if len(geometry_map) != len(groups):
        failures.append({"code": "summary-geometry-count", "actual": len(geometry_map), "expected": len(groups)})
    zero_case_ids = set(audited_zero_ids)
    for group_id, expected_cases in groups.items():
        actual = geometry_map.get(group_id)
        if actual is None:
            failures.append({"code": "summary-geometry-missing", "geometryId": group_id})
            continue
        expected_case_ids = sorted(item["caseId"] for item in expected_cases)
        expected_zero_ids = sorted(set(expected_case_ids) & zero_case_ids)
        group_complete = all(
            case_id in records
            and records[case_id].get("status") == "COMPLETED"
            and finite_number(records[case_id].get("selectedPhotopicContributionCdM2"))
            for case_id in expected_case_ids
        )
        values = (
            [float(records[case_id]["selectedPhotopicContributionCdM2"]) for case_id in expected_case_ids]
            if group_complete
            else []
        )
        expected_geometry_classification = (
            "STRUCTURAL_OR_EXECUTION_FAILURE"
            if not group_complete
            else "ADAPTIVE_CONTINUATION_REQUIRED"
            if expected_zero_ids
            else "BATCH_NUMERICALLY_COMPLETE"
        )
        if actual.get("caseIds") != expected_case_ids or actual.get("zeroHitCaseIds") != expected_zero_ids:
            failures.append({"code": "summary-geometry-cases", "geometryId": group_id})
        if actual.get("classification") != expected_geometry_classification:
            failures.append({"code": "summary-geometry-classification", "geometryId": group_id})
        if actual.get("scientificallyEligible") is not False:
            failures.append({"code": "summary-incomplete-geometry-eligible", "geometryId": group_id})
        stats = actual.get("statistics")
        if not group_complete:
            if stats is not None:
                failures.append({"code": "summary-failed-geometry-statistics-present", "geometryId": group_id})
        else:
            expected_stats = expected_group_statistics(values, len(expected_zero_ids))
            if not isinstance(stats, dict):
                failures.append({"code": "summary-geometry-statistics-missing", "geometryId": group_id})
            else:
                for key in ("mean", "sampleStd", "zeroHitFraction"):
                    if not finite_number(stats.get(key)) or not close(float(stats[key]), float(expected_stats[key])):
                        failures.append({"code": "summary-geometry-statistic", "geometryId": group_id, "field": key})
                for key in ("values", "coefficientOfVariation", "coefficientOfVariationStatus", "zeroHitCount"):
                    if stats.get(key) != expected_stats[key]:
                        failures.append({"code": "summary-geometry-statistic", "geometryId": group_id, "field": key})

    audit_passed = not failures
    report = {
        "schemaVersion": SCHEMA_VERSION,
        "stageId": STAGE_ID,
        "status": "PASSED" if audit_passed else "FAILED",
        "batchClassification": expected_classification,
        "executionComplete": execution_complete,
        "scientificallyEligible": False,
        "successDoesNotAuthorizeProduction": True,
        "planRawSha256": raw_sha256(plan_path),
        "manifestRawSha256": plan.get("manifestRawSha256"),
        "aggregateRawSha256": raw_sha256(summary_path),
        "caseResultCount": len(result_paths),
        "caseResultHashes": {
            case_id: raw_sha256(path)
            for path in result_paths
            if isinstance((case_id := load_json(path).get("caseId")), str)
        },
        "rawCaseEvidence": raw_case_evidence,
        "zeroHitDiagnostics": zero_hit_diagnostics,
        "unaffectedGeometryStatisticsVerified": audit_passed and len(geometry_map) == len(groups),
        "incompleteGeometryEnteredTrainingEligibility": False,
        "failures": failures,
        "boundary": "independent raw artifact and numerical-classification audit only; no physical or observational validity claim",
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
