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


class AggregateFailure(RuntimeError):
    pass


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AggregateFailure(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate_batch(plan_path: Path, cases_root: Path, output_dir: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    if plan.get("stageId") != STAGE_ID or plan.get("status") != "AUTHORIZED_PLAN":
        raise AggregateFailure("wrong or unauthorized plan")
    planned_cases = {case["caseId"]: case for case in plan.get("cases", [])}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    if len(result_paths) != len(planned_cases):
        raise AggregateFailure(f"expected {len(planned_cases)} case results, found {len(result_paths)}")

    records: dict[str, dict[str, Any]] = {}
    index: list[dict[str, Any]] = []
    for path in result_paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in records:
            raise AggregateFailure(f"missing or duplicate caseId in {path}")
        expected = planned_cases.get(case_id)
        if expected is None:
            raise AggregateFailure(f"unplanned case result: {case_id}")
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
            raise AggregateFailure(f"case result invariant failure for {case_id}: {stale}")
        if record.get("status") not in {"COMPLETED", "FAILED"}:
            raise AggregateFailure(f"invalid case status for {case_id}")
        if record.get("syntaxCheckCount") not in {0, 1} or record.get("solverExecutionCount") not in {0, 1}:
            raise AggregateFailure(f"invalid execution accounting for {case_id}")
        records[case_id] = record
        index.append(
            {
                "caseId": case_id,
                "ordinal": expected["ordinal"],
                "path": str(path),
                "caseResultSha256": raw_sha256(path),
            }
        )

    ordered = [records[case["caseId"]] for case in plan["cases"]]
    complete = [record for record in ordered if record["status"] == "COMPLETED"]
    failed = [record for record in ordered if record["status"] == "FAILED"]
    syntax_count = sum(int(record["syntaxCheckCount"]) for record in ordered)
    solver_count = sum(int(record["solverExecutionCount"]) for record in ordered)
    attempted_photons = sum(
        int(record["photonHistories"]) for record in ordered if int(record["solverExecutionCount"]) == 1
    )
    completed_photons = sum(int(record["photonHistories"]) for record in complete)

    statistics_block: dict[str, Any] | None = None
    if not failed and len(complete) == len(ordered):
        values = [float(record["selectedPhotopicContributionCdM2"]) for record in complete]
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise AggregateFailure("completed case contains invalid photopic contribution")
        mean = statistics.fmean(values)
        sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
        statistics_block = {
            "values": values,
            "mean": mean,
            "sampleStd": sample_std,
            "coefficientOfVariation": sample_std / mean if mean else None,
        }
        status = "COMPLETED"
        classification = "BATCH_COMPLETE_UNCLASSIFIED"
    else:
        status = "FAILED"
        classification = "STRUCTURAL_OR_EXECUTION_FAILURE"

    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "status": status,
        "classification": classification,
        "scientificInterpretationAssigned": False,
        "successDoesNotAuthorizeProduction": True,
        "manifestRawSha256": plan["manifestRawSha256"],
        "planRawSha256": raw_sha256(plan_path),
        "caseCount": len(ordered),
        "completeCaseCount": len(complete),
        "failedCaseCount": len(failed),
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": solver_count,
        "attemptedConfiguredMcPhotonsSum": attempted_photons,
        "completedConfiguredMcPhotonsSum": completed_photons,
        "statistics": statistics_block,
        "failedCases": [
            {"caseId": record["caseId"], "structuralFailure": record.get("structuralFailure")}
            for record in failed
        ],
        "cases": ordered,
        "caseIndex": sorted(index, key=lambda item: item["ordinal"]),
        "boundary": "generic batch accounting only; no method-agreement or physical-validity classification",
    }
    result_path = output_dir / "aggregate-result.json"
    result_path.write_text(dump_json(aggregate))
    manifest = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "status": status,
        "classification": classification,
        "resultSha256": raw_sha256(result_path),
        "caseResultSha256": {
            item["caseId"]: item["caseResultSha256"] for item in aggregate["caseIndex"]
        },
    }
    (output_dir / "aggregate-manifest.json").write_text(dump_json(manifest))
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = aggregate_batch(args.plan, args.cases_root, args.output_dir)
        print(dump_json(result), end="")
        return 0 if result["status"] == "COMPLETED" else 2
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "FAILED",
            "classification": "STRUCTURAL_OR_EXECUTION_FAILURE",
            "reason": str(exc),
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "aggregate-failure.json").write_text(dump_json(refusal))
        print(dump_json(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
