#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"
ADAPTER_ID = "mystic-spectral-radiance-v1"


class CaseFailure(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "reason": self.reason, "detail": self.detail}


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CaseFailure("invalid-json", f"cannot read JSON object: {path}", str(exc)) from exc
    if not isinstance(value, dict):
        raise CaseFailure("invalid-json-object", f"expected JSON object: {path}")
    return value


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_case(plan: dict[str, Any], case_id: str) -> dict[str, Any]:
    if plan.get("stageId") != STAGE_ID or plan.get("status") != "AUTHORIZED_PLAN":
        raise CaseFailure("plan", "plan is not an authorized scientific plan")
    matches = [case for case in plan.get("cases", []) if isinstance(case, dict) and case.get("caseId") == case_id]
    if len(matches) != 1:
        raise CaseFailure("case-selection", "case ID must occur exactly once in plan")
    return matches[0]


def validate_proposal(plan: dict[str, Any], case: dict[str, Any], proposal: dict[str, Any], proposal_path: Path) -> Path:
    expected = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "adapterId": ADAPTER_ID,
        "status": "PREPARED_NO_SOLVER",
        "scientificSolverExecuted": False,
        "batchId": plan["batchId"],
        "caseId": case["caseId"],
        "manifestRawSha256": plan["manifestRawSha256"],
    }
    stale = {key: (proposal.get(key), value) for key, value in expected.items() if proposal.get(key) != value}
    if stale:
        raise CaseFailure("proposal", "case proposal does not match authorized plan", stale)
    inputs = proposal.get("inputs")
    if not isinstance(inputs, dict):
        raise CaseFailure("proposal", "proposal inputs are missing")
    case_expected = {
        "ordinal": case["ordinal"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
    }
    stale_case = {key: (inputs.get(key), value) for key, value in case_expected.items() if inputs.get(key) != value}
    if stale_case:
        raise CaseFailure("proposal", "proposal case identity is stale", stale_case)
    input_path_value = proposal.get("inputPath")
    if not isinstance(input_path_value, str):
        raise CaseFailure("proposal", "proposal inputPath is missing")
    input_path = Path(input_path_value)
    if not input_path.is_file():
        fallback = proposal_path.parent / "input-resolved.txt"
        if fallback.is_file():
            input_path = fallback
        else:
            raise CaseFailure("input", "prepared input file is missing", input_path_value)
    rendered = input_path.read_text()
    if text_sha256(rendered) != proposal.get("inputResolvedSha256"):
        raise CaseFailure("input-hash", "prepared input hash does not match proposal")
    return input_path


def run_process(command: list[str], text: str, cwd: Path, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout,
            check=False,
        )
        return {
            "exitCode": process.returncode,
            "timedOut": False,
            "elapsedSeconds": time.monotonic() - started,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "exitCode": None,
            "timedOut": True,
            "elapsedSeconds": time.monotonic() - started,
            "stdout": stdout,
            "stderr": stderr,
        }


def parse_spectrum(path: Path, nodes: list[int]) -> list[float]:
    if not path.is_file():
        raise CaseFailure("spectrum", "expected spectrum file is missing", str(path))
    found: dict[int, float] = {}
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[-1])
        except ValueError:
            continue
        for node in nodes:
            if abs(wavelength - node) <= 1e-7:
                found[node] = value
    if sorted(found) != nodes:
        raise CaseFailure("spectrum", "spectrum does not contain every diagnostic node", sorted(found))
    values = [found[node] for node in nodes]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise CaseFailure("spectrum", "spectrum contains invalid radiance")
    return values


def calculate_metric(values: list[float], analysis: dict[str, Any]) -> float:
    weights = [float(value) for value in analysis["photopicWeights"]]
    if len(values) != len(weights):
        raise CaseFailure("analysis", "radiance and photopic weight lengths differ")
    return (
        float(analysis["luminousEfficacyLmPerW"])
        * float(analysis["wavelengthBinWidthNm"])
        * sum(
            value * float(analysis["radianceUnitScale"]) * weight
            for value, weight in zip(values, weights, strict=True)
        )
    )


def execute_case(
    plan_path: Path, proposal_path: Path, runtime_report_path: Path, case_id: str, uvspec: Path
) -> tuple[dict[str, Any], bool]:
    plan = load_json(plan_path)
    case = resolve_case(plan, case_id)
    proposal = load_json(proposal_path)
    input_path = validate_proposal(plan, case, proposal, proposal_path)
    if not runtime_report_path.is_file():
        raise CaseFailure("runtime-report", "runtime report is missing", str(runtime_report_path))
    if raw_sha256(runtime_report_path) != proposal.get("runtimeReportRawSha256"):
        raise CaseFailure("runtime-report", "runtime report hash does not match proposal")
    case_dir = input_path.parent
    result_path = case_dir / "case-result.json"
    syntax_count = 0
    solver_count = 0
    failure: dict[str, Any] | None = None
    syntax: dict[str, Any] | None = None
    solver: dict[str, Any] | None = None
    record: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "batchId": plan["batchId"],
        "caseId": case_id,
        "ordinal": case["ordinal"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "manifestRawSha256": plan["manifestRawSha256"],
        "planRawSha256": raw_sha256(plan_path),
        "proposalRawSha256": raw_sha256(proposal_path),
        "inputResolvedSha256": raw_sha256(input_path),
        "runtimeReportRawSha256": proposal.get("runtimeReportRawSha256"),
        "successDoesNotAuthorizeProduction": True,
    }
    try:
        if not uvspec.is_file():
            raise CaseFailure("uvspec", "uvspec executable is missing", str(uvspec))
        rendered = input_path.read_text()
        syntax_count = 1
        syntax = run_process([str(uvspec.resolve()), "-c"], rendered, case_dir, 60)
        (case_dir / "syntax-stdout.txt").write_text(str(syntax["stdout"]))
        (case_dir / "syntax-stderr.txt").write_text(str(syntax["stderr"]))
        if syntax["timedOut"] or syntax["exitCode"] != 0:
            raise CaseFailure("syntax-failure", "uvspec syntax check failed", syntax)

        solver_count = 1
        solver = run_process(
            [str(uvspec.resolve())],
            rendered,
            case_dir,
            int(plan["perCaseTimeoutSeconds"]),
        )
        (case_dir / "solver-stdout.txt").write_text(str(solver["stdout"]))
        (case_dir / "solver-stderr.txt").write_text(str(solver["stderr"]))
        if solver["timedOut"] or solver["exitCode"] != 0:
            raise CaseFailure("solver-failure", "uvspec solver execution failed", solver)

        nodes = [int(node) for node in plan["frozenInputs"]["diagnosticNodesNm"]]
        radiance_path = case_dir / "mc.rad.spc"
        std_path = case_dir / "mc.rad.std.spc"
        radiance = parse_spectrum(radiance_path, nodes)
        std_radiance = parse_spectrum(std_path, nodes)
        metric = calculate_metric(radiance, plan["analysis"])
        if not math.isfinite(metric) or metric <= 0:
            raise CaseFailure("analysis", "selected photopic contribution is invalid", metric)
        record.update(
            {
                "status": "COMPLETED",
                "classification": "CASE_COMPLETE_UNCLASSIFIED",
                "syntaxCheckCount": syntax_count,
                "solverExecutionCount": solver_count,
                "syntaxElapsedSeconds": syntax["elapsedSeconds"],
                "solverElapsedSeconds": solver["elapsedSeconds"],
                "diagnosticNodesNm": nodes,
                "selectedNodeRadiance": radiance,
                "selectedNodeStdRadiance": std_radiance,
                "selectedPhotopicContributionCdM2": metric,
                "outputSha256": raw_sha256(radiance_path),
                "stdOutputSha256": raw_sha256(std_path),
                "structuralFailure": None,
            }
        )
        ok = True
    except CaseFailure as exc:
        failure = exc.as_dict()
        record.update(
            {
                "status": "FAILED",
                "classification": "STRUCTURAL_OR_EXECUTION_FAILURE",
                "syntaxCheckCount": syntax_count,
                "solverExecutionCount": solver_count,
                "syntaxElapsedSeconds": syntax.get("elapsedSeconds") if syntax else None,
                "solverElapsedSeconds": solver.get("elapsedSeconds") if solver else None,
                "structuralFailure": failure,
            }
        )
        ok = False
    except Exception as exc:
        failure = CaseFailure("unexpected-error", str(exc)).as_dict()
        record.update(
            {
                "status": "FAILED",
                "classification": "STRUCTURAL_OR_EXECUTION_FAILURE",
                "syntaxCheckCount": syntax_count,
                "solverExecutionCount": solver_count,
                "structuralFailure": failure,
            }
        )
        ok = False
    result_path.write_text(dump_json(record))
    return record, ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--uvspec", type=Path, required=True)
    args = parser.parse_args()
    result, ok = execute_case(args.plan, args.proposal, args.runtime_report, args.case_id, args.uvspec)
    print(dump_json(result), end="")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
