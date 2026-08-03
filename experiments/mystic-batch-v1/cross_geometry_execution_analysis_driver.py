#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-pilot-v1"
ANALYSIS_MODULE = Path(__file__).with_name("cross_geometry_analysis.py")


class DriverFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise DriverFailure(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_analysis_module(path: Path):
    spec = importlib.util.spec_from_file_location("cross_geometry_screening_analysis", path)
    if spec is None or spec.loader is None:
        raise DriverFailure(f"cannot load analysis module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze_artifacts(
    proposal_path: Path,
    contract_path: Path,
    cases_root: Path,
    generic_summary_path: Path,
    generic_audit_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], bool]:
    proposal = load_json(proposal_path)
    summary = load_json(generic_summary_path)
    audit = load_json(generic_audit_path)
    if proposal.get("stageId") != STAGE_ID or proposal.get("proposalOnly") is not True:
        raise DriverFailure("wrong proposal header")
    if summary.get("classification") != "BATCH_NUMERICALLY_COMPLETE" or summary.get("status") != "COMPLETED":
        raise DriverFailure("generic aggregate is not numerically complete")
    if audit.get("status") != "PASSED":
        raise DriverFailure("generic independent audit did not pass")

    planned = {case["caseId"]: case for case in proposal.get("cases", [])}
    paths = sorted(cases_root.rglob("case-result.json"))
    records: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    proposal_hash = raw_sha256(proposal_path)
    for path in paths:
        record = load_json(path)
        case_id = record.get("caseId")
        if not isinstance(case_id, str) or case_id in records:
            failures.append({"code": "duplicate-or-invalid-case", "path": str(path)})
            continue
        case = planned.get(case_id)
        if case is None:
            failures.append({"code": "unplanned-case", "caseId": case_id})
            continue
        required = {
            "status": "COMPLETED",
            "batchId": proposal["batchId"],
            "ordinal": case["ordinal"],
            "seed": case["seed"],
            "photonHistories": case["photonHistories"],
            "manifestRawSha256": proposal_hash,
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
        }
        stale = {key: (record.get(key), expected) for key, expected in required.items() if record.get(key) != expected}
        if stale:
            failures.append({"code": "case-invariant", "caseId": case_id, "detail": stale})
        syntax = record.get("syntax") or {}
        solver = record.get("solver") or {}
        if syntax.get("timedOut") is not False or syntax.get("exitCode") != 0 or solver.get("timedOut") is not False or solver.get("exitCode") != 0:
            failures.append({"code": "process-result", "caseId": case_id})
        records[case_id] = record

    missing = sorted(set(planned) - set(records))
    if missing:
        failures.append({"code": "missing-cases", "caseIds": missing})
    if len(paths) != len(planned):
        failures.append({"code": "case-file-count", "actual": len(paths), "expected": len(planned)})
    if failures:
        raise DriverFailure(f"artifact invariants failed: {failures}")

    ordered_records = [records[case["caseId"]] for case in proposal["cases"]]
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "records.json"
    records_path.write_text(dump({"records": ordered_records}))
    analysis_module = load_analysis_module(ANALYSIS_MODULE)
    screening = analysis_module.analyze(proposal_path, contract_path, records_path)
    structural_count = int(screening.get("classificationCounts", {}).get("STRUCTURAL_OR_EXECUTION_FAILURE", 0))
    result = {
        **screening,
        "proposalRawSha256": proposal_hash,
        "contractRawSha256": raw_sha256(contract_path),
        "genericSummaryRawSha256": raw_sha256(generic_summary_path),
        "genericAuditRawSha256": raw_sha256(generic_audit_path),
        "recordsRawSha256": raw_sha256(records_path),
        "caseResultCount": len(paths),
        "executionArtifactAuditPassed": True,
    }
    (output_dir / "screening-analysis.json").write_text(dump(result))
    return result, structural_count == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--generic-summary", type=Path, required=True)
    parser.add_argument("--generic-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result, passed = analyze_artifacts(
            args.proposal, args.contract, args.cases_root, args.generic_summary, args.generic_audit, args.output_dir
        )
        print(dump(result), end="")
        return 0 if passed else 2
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
