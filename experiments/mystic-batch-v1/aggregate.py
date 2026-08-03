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


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AggregateRefusal(f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate_batch(plan_path: Path, cases_root: Path, output_dir: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    if plan.get("stageId") != STAGE_ID or plan.get("syntheticContractOnly") is not True:
        raise AggregateRefusal("wrong or non-synthetic plan")
    planned = {case["caseId"]: case for case in plan.get("cases", [])}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    if len(result_paths) != len(planned):
        raise AggregateRefusal(f"expected {len(planned)} case results, found {len(result_paths)}")

    records: dict[str, dict[str, Any]] = {}
    index: list[dict[str, Any]] = []
    for path in result_paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in records:
            raise AggregateRefusal(f"missing or duplicate caseId in {path}")
        expected = planned.get(case_id)
        if expected is None:
            raise AggregateRefusal(f"unplanned case result: {case_id}")
        required = {
            "stageId": STAGE_ID,
            "batchId": plan["batchId"],
            "ordinal": expected["ordinal"],
            "seed": expected["seed"],
            "photonHistories": expected["photonHistories"],
            "manifestRawSha256": plan["manifestRawSha256"],
            "status": "COMPLETED",
            "artifactType": "synthetic-contract-test-only",
            "scientificResult": False,
            "syntaxCheckCount": 0,
            "solverExecutionCount": 0,
            "syntheticExecutionCount": 1,
        }
        stale = {key: (record.get(key), expected_value) for key, expected_value in required.items() if record.get(key) != expected_value}
        if stale:
            raise AggregateRefusal(f"case result invariant failure for {case_id}: {stale}")
        value = record.get("syntheticPhotopicContribution")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise AggregateRefusal(f"invalid syntheticPhotopicContribution for {case_id}")
        records[case_id] = record
        index.append(
            {
                "caseId": case_id,
                "ordinal": expected["ordinal"],
                "path": str(path),
                "caseResultSha256": raw_sha256(path),
            }
        )

    if set(records) != set(planned):
        raise AggregateRefusal("case set mismatch")
    ordered = [records[case["caseId"]] for case in plan["cases"]]
    values = [float(record["syntheticPhotopicContribution"]) for record in ordered]
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values) if len(values) > 1 else 0.0
    cv = sample_std / mean if mean else 0.0
    aggregate = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "status": "COMPLETED",
        "classification": "SYNTHETIC_CONTRACT_PASS",
        "scientificResult": False,
        "manifestRawSha256": plan["manifestRawSha256"],
        "caseCount": len(ordered),
        "completeCaseCount": len(ordered),
        "syntaxCheckCount": sum(record["syntaxCheckCount"] for record in ordered),
        "solverExecutionCount": sum(record["solverExecutionCount"] for record in ordered),
        "syntheticExecutionCount": sum(record["syntheticExecutionCount"] for record in ordered),
        "configuredMcPhotonsSum": sum(record["photonHistories"] for record in ordered),
        "caseIds": [record["caseId"] for record in ordered],
        "seeds": [record["seed"] for record in ordered],
        "syntheticPhotopic": {
            "values": values,
            "mean": mean,
            "sampleStd": sample_std,
            "coefficientOfVariation": cv,
        },
        "boundary": "Synthetic contract pass only. No scientific inference or MYSTIC result.",
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    aggregate_path = output_dir / "aggregate.json"
    aggregate_path.write_text(dump_json(aggregate))
    index.sort(key=lambda item: item["ordinal"])
    (output_dir / "case-index.json").write_text(dump_json({"schemaVersion": 1, "cases": index}))
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        aggregate = aggregate_batch(args.plan, args.cases_root, args.output_dir)
        print(dump_json({"status": aggregate["status"], "caseCount": aggregate["caseCount"]}), end="")
        return 0
    except Exception as exc:
        print(dump_json({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
