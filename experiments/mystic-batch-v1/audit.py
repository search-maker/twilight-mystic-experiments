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


def close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(a, b, rel_tol=tolerance, abs_tol=tolerance)


def audit_batch(plan_path: Path, cases_root: Path, aggregate_dir: Path, output_path: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    aggregate_path = aggregate_dir / "aggregate.json"
    index_path = aggregate_dir / "case-index.json"
    aggregate = load_json(aggregate_path)
    index = load_json(index_path)
    if plan.get("stageId") != STAGE_ID or plan.get("syntheticContractOnly") is not True:
        raise AuditFailure("plan is not an approved synthetic contract plan")
    if aggregate.get("stageId") != STAGE_ID or aggregate.get("batchId") != plan.get("batchId"):
        raise AuditFailure("aggregate header mismatch")
    if aggregate.get("scientificResult") is not False or aggregate.get("classification") != "SYNTHETIC_CONTRACT_PASS":
        raise AuditFailure("aggregate crossed the synthetic-only boundary")

    planned_cases = plan.get("cases")
    if not isinstance(planned_cases, list):
        raise AuditFailure("plan cases missing")
    planned_by_id = {case["caseId"]: case for case in planned_cases}
    result_paths = sorted(cases_root.rglob("case-result.json"))
    if len(result_paths) != len(planned_cases):
        raise AuditFailure("wrong number of case-result.json files")

    audited: dict[str, dict[str, Any]] = {}
    case_hashes: dict[str, str] = {}
    for path in result_paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in audited:
            raise AuditFailure(f"duplicate or invalid caseId: {case_id}")
        expected = planned_by_id.get(case_id)
        if expected is None:
            raise AuditFailure(f"unplanned case: {case_id}")
        if record.get("seed") != expected["seed"] or record.get("ordinal") != expected["ordinal"]:
            raise AuditFailure(f"identity mismatch for {case_id}")
        if record.get("photonHistories") != expected["photonHistories"]:
            raise AuditFailure(f"photon mismatch for {case_id}")
        if record.get("manifestRawSha256") != plan.get("manifestRawSha256"):
            raise AuditFailure(f"manifest hash mismatch for {case_id}")
        if record.get("status") != "COMPLETED" or record.get("scientificResult") is not False:
            raise AuditFailure(f"invalid completion boundary for {case_id}")
        if record.get("syntaxCheckCount") != 0 or record.get("solverExecutionCount") != 0:
            raise AuditFailure(f"synthetic case claimed syntax or solver execution: {case_id}")
        if record.get("syntheticExecutionCount") != 1:
            raise AuditFailure(f"wrong synthetic execution count for {case_id}")
        input_path = path.parent / "input-resolved.json"
        runtime_path = path.parent / "runtime-report.json"
        if not input_path.is_file() or not runtime_path.is_file():
            raise AuditFailure(f"missing companion files for {case_id}")
        if record.get("inputResolvedSha256") != raw_sha256(input_path):
            raise AuditFailure(f"input hash mismatch for {case_id}")
        value = record.get("syntheticPhotopicContribution")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise AuditFailure(f"invalid photopic value for {case_id}")
        audited[case_id] = record
        case_hashes[case_id] = raw_sha256(path)

    if set(audited) != set(planned_by_id):
        raise AuditFailure("planned and audited case sets differ")
    ordered = [audited[case["caseId"]] for case in planned_cases]
    values = [float(record["syntheticPhotopicContribution"]) for record in ordered]
    recomputed_mean = statistics.fmean(values)
    recomputed_std = statistics.stdev(values) if len(values) > 1 else 0.0
    recomputed_cv = recomputed_std / recomputed_mean if recomputed_mean else 0.0
    reported = aggregate.get("syntheticPhotopic")
    if not isinstance(reported, dict):
        raise AuditFailure("aggregate syntheticPhotopic missing")
    comparisons = {
        "mean": (float(reported.get("mean")), recomputed_mean),
        "sampleStd": (float(reported.get("sampleStd")), recomputed_std),
        "coefficientOfVariation": (float(reported.get("coefficientOfVariation")), recomputed_cv),
    }
    bad = {key: pair for key, pair in comparisons.items() if not close(*pair)}
    if bad:
        raise AuditFailure(f"aggregate statistics mismatch: {bad}")

    expected_accounting = {
        "caseCount": len(ordered),
        "completeCaseCount": len(ordered),
        "syntaxCheckCount": 0,
        "solverExecutionCount": 0,
        "syntheticExecutionCount": len(ordered),
        "configuredMcPhotonsSum": sum(case["photonHistories"] for case in planned_cases),
        "caseIds": [case["caseId"] for case in planned_cases],
        "seeds": [case["seed"] for case in planned_cases],
        "manifestRawSha256": plan["manifestRawSha256"],
    }
    stale = {key: (aggregate.get(key), expected) for key, expected in expected_accounting.items() if aggregate.get(key) != expected}
    if stale:
        raise AuditFailure(f"aggregate accounting mismatch: {stale}")

    indexed = index.get("cases")
    if not isinstance(indexed, list) or len(indexed) != len(ordered):
        raise AuditFailure("invalid case index")
    indexed_hashes = {item.get("caseId"): item.get("caseResultSha256") for item in indexed if isinstance(item, dict)}
    if indexed_hashes != case_hashes:
        raise AuditFailure("case index hashes do not match exact artifacts")

    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "status": "PASSED",
        "independentAudit": True,
        "scientificResult": False,
        "caseCount": len(ordered),
        "caseResultSha256": case_hashes,
        "aggregateSha256": raw_sha256(aggregate_path),
        "caseIndexSha256": raw_sha256(index_path),
        "recomputedSyntheticPhotopic": {
            "mean": recomputed_mean,
            "sampleStd": recomputed_std,
            "coefficientOfVariation": recomputed_cv,
        },
        "boundary": "Synthetic infrastructure audit only. No MYSTIC execution or scientific validation.",
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
        report = audit_batch(args.plan, args.cases_root, args.aggregate_dir, args.output)
        print(dump_json({"status": report["status"], "caseCount": report["caseCount"]}), end="")
        return 0
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "FAILED",
            "independentAudit": True,
            "scientificResult": False,
            "reason": str(exc),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(failure))
        print(dump_json(failure), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
