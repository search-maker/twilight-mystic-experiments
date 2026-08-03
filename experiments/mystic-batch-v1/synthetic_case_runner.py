#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"


class CaseRefusal(RuntimeError):
    pass


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise CaseRefusal(f"expected JSON object: {path}")
    return value


def deterministic_spectrum(seed: int, nodes: list[int]) -> tuple[list[float], list[float]]:
    rng = random.Random(seed)
    values: list[float] = []
    std_values: list[float] = []
    for node in nodes:
        base = 0.55 * math.exp(-((node - 555.0) / 125.0) ** 2) + 0.02
        perturbation = 1.0 + rng.uniform(-0.025, 0.025)
        value = base * perturbation
        relative_std = 0.018 + rng.uniform(0.0, 0.006)
        values.append(value)
        std_values.append(value * relative_std)
    return values, std_values


def run_case(plan_path: Path, case_id: str, output_root: Path) -> dict[str, Any]:
    plan = load_json(plan_path)
    if plan.get("stageId") != STAGE_ID or plan.get("syntheticContractOnly") is not True:
        raise CaseRefusal("plan is not a mystic-batch-v1 synthetic contract plan")
    matches = [case for case in plan.get("cases", []) if case.get("caseId") == case_id]
    if len(matches) != 1:
        raise CaseRefusal(f"planned case not found exactly once: {case_id}")
    case = matches[0]
    nodes = plan.get("frozenInputs", {}).get("diagnosticNodesNm")
    if not isinstance(nodes, list) or not nodes or not all(isinstance(node, int) for node in nodes):
        raise CaseRefusal("diagnosticNodesNm must be a non-empty integer array")

    case_dir = output_root / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    resolved_input = {
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "manifestRawSha256": plan["manifestRawSha256"],
        "case": case,
        "frozenInputs": plan["frozenInputs"],
        "runtime": plan["runtime"],
        "boundary": "synthetic contract test only; no MYSTIC or uvspec execution",
    }
    resolved_path = case_dir / "input-resolved.json"
    resolved_path.write_text(dump_json(resolved_input))

    spectrum, spectrum_std = deterministic_spectrum(case["seed"], nodes)
    photopic = sum(value * math.exp(-((node - 555.0) / 90.0) ** 2) for node, value in zip(nodes, spectrum))
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "caseId": case["caseId"],
        "ordinal": case["ordinal"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "manifestRawSha256": plan["manifestRawSha256"],
        "status": "COMPLETED",
        "artifactType": "synthetic-contract-test-only",
        "scientificResult": False,
        "syntaxCheckCount": 0,
        "solverExecutionCount": 0,
        "syntheticExecutionCount": 1,
        "diagnosticNodesNm": nodes,
        "syntheticNodeRadiance": spectrum,
        "syntheticNodeStdRadiance": spectrum_std,
        "syntheticPhotopicContribution": photopic,
        "inputResolvedSha256": raw_sha256(resolved_path),
    }
    result_path = case_dir / "case-result.json"
    result_path.write_text(dump_json(result))

    runtime_report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "caseId": case_id,
        "python": platform.python_version(),
        "pythonImplementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "runnerScriptSha256": raw_sha256(Path(__file__)),
        "planSha256": raw_sha256(plan_path),
        "caseResultSha256": raw_sha256(result_path),
        "boundary": "runtime identity for synthetic contract test only",
    }
    (case_dir / "runtime-report.json").write_text(dump_json(runtime_report))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_case(args.plan, args.case_id, args.output_root)
        print(dump_json({"status": result["status"], "caseId": result["caseId"]}), end="")
        return 0
    except Exception as exc:
        print(dump_json({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
