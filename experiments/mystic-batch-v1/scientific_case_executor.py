#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"
NODES = [470, 480, 490, 500, 510, 520, 530, 540, 560, 580, 590, 600, 610, 640, 660]
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


class ExecutionRefusal(RuntimeError):
    def __init__(self, code: str, reason: str, detail: Any | None = None) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.detail = detail


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ExecutionRefusal("invalid-json", f"expected JSON object: {path}")
    return value


def load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("mystic_batch_scientific_adapter", path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal("adapter-load", f"cannot load adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_spectrum(path: Path) -> list[float]:
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
        for node in NODES:
            if abs(wavelength - node) <= 1e-7:
                found[node] = value
    if sorted(found) != NODES:
        raise ExecutionRefusal("spectrum", f"missing diagnostic nodes in {path}", sorted(found))
    values = [found[node] for node in NODES]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ExecutionRefusal("spectrum", f"invalid spectral values in {path}")
    return values


def luminance(values: list[float]) -> float:
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(values, CIE))


def run_process(command: list[str], text: str, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "exitCode": result.returncode,
            "timedOut": False,
            "elapsedSeconds": time.monotonic() - start,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exitCode": None,
            "timedOut": True,
            "elapsedSeconds": time.monotonic() - start,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def verify_context(allow_execution: bool) -> None:
    if not allow_execution:
        raise ExecutionRefusal("execution-flag", "--allow-execution is required")
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    stale = {key: (os.getenv(key), value) for key, value in expected.items() if os.getenv(key) != value}
    if stale:
        raise ExecutionRefusal("github-context", "not exact first-attempt workflow_dispatch context", stale)


def execute_case(
    manifest_path: Path,
    runtime_report_path: Path,
    adapter_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    uvspec: Path,
    output_root: Path,
    timeout_seconds: int,
    allow_execution: bool,
) -> tuple[dict[str, Any], bool]:
    verify_context(allow_execution)
    if timeout_seconds < 1:
        raise ExecutionRefusal("timeout", "timeout must be positive")
    if not uvspec.is_file() or not os.access(uvspec, os.X_OK):
        raise ExecutionRefusal("uvspec", "uvspec is missing or not executable", str(uvspec))

    manifest = load_json(manifest_path)
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ExecutionRefusal("manifest", "manifest cases must be an array")
    matches = [case for case in cases if isinstance(case, dict) and case.get("caseId") == case_id]
    if len(matches) != 1:
        raise ExecutionRefusal("case-selection", "case must occur exactly once", case_id)
    expected_case = matches[0]

    adapter = load_adapter(adapter_path)
    output_root.mkdir(parents=True, exist_ok=True)
    proposal = adapter.prepare_case(
        manifest_path,
        runtime_report_path,
        case_id,
        data_dir,
        repository_root,
        output_root,
    )
    case_dir = output_root / case_id
    input_path = case_dir / "input-resolved.txt"
    text = input_path.read_text()
    syntax = run_process([str(uvspec), "-c"], text, case_dir, 60)
    (case_dir / "syntax-stdout.txt").write_text(str(syntax["stdout"]))
    (case_dir / "syntax-stderr.txt").write_text(str(syntax["stderr"]))

    failure: dict[str, Any] | None = None
    solver: dict[str, Any] | None = None
    syntax_count = 1
    solver_count = 0
    if syntax["timedOut"] or syntax["exitCode"] != 0:
        failure = {"code": "syntax-failure", "detail": syntax}
    else:
        solver_count = 1
        solver = run_process([str(uvspec)], text, case_dir, timeout_seconds)
        (case_dir / "solver-stdout.txt").write_text(str(solver["stdout"]))
        (case_dir / "solver-stderr.txt").write_text(str(solver["stderr"]))
        if solver["timedOut"] or solver["exitCode"] != 0:
            failure = {"code": "solver-failure", "detail": solver}

    if failure is None:
        radiance_path = case_dir / "mc.rad.spc"
        std_path = case_dir / "mc.rad.std.spc"
        if not radiance_path.is_file() or not std_path.is_file():
            failure = {"code": "missing-output", "detail": [str(radiance_path), str(std_path)]}

    if failure is None:
        values = parse_spectrum(radiance_path)
        std_values = parse_spectrum(std_path)
        photopic = luminance(values)
        status = "COMPLETED"
        ok = True
    else:
        values = []
        std_values = []
        photopic = None
        status = "FAILED"
        ok = False

    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": status,
        "scientificDiagnostic": True,
        "successDoesNotAuthorizeProduction": True,
        "batchId": manifest.get("batchId"),
        "caseId": case_id,
        "ordinal": expected_case.get("ordinal"),
        "seed": expected_case.get("seed"),
        "photonHistories": expected_case.get("photonHistories"),
        "manifestRawSha256": raw_sha256(manifest_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "adapterRawSha256": raw_sha256(adapter_path),
        "inputResolvedSha256": proposal["inputResolvedSha256"],
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": solver_count,
        "syntax": {key: syntax[key] for key in ("exitCode", "timedOut", "elapsedSeconds")},
        "solver": None if solver is None else {key: solver[key] for key in ("exitCode", "timedOut", "elapsedSeconds")},
        "diagnosticNodesNm": NODES,
        "selectedNodeRadiance": values,
        "selectedNodeStdRadiance": std_values,
        "selectedPhotopicContributionCdM2": photopic,
        "radianceOutputSha256": raw_sha256(radiance_path) if failure is None else None,
        "stdOutputSha256": raw_sha256(std_path) if failure is None else None,
        "failure": failure,
        "boundary": "one syntax check and at most one solver execution; no retry; result does not authorize production",
    }
    (case_dir / "case-result.json").write_text(dump(result))
    return result, ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--runtime-report", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--allow-execution", action="store_true")
    args = parser.parse_args()
    try:
        result, ok = execute_case(
            args.manifest,
            args.runtime_report,
            args.adapter,
            args.case_id,
            args.data_dir,
            args.repository_root,
            args.uvspec,
            args.output_root,
            args.timeout_seconds,
            args.allow_execution,
        )
        print(dump(result), end="")
        return 0 if ok else 2
    except Exception as exc:
        refusal = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED_BEFORE_OR_DURING_EXECUTION",
            "reason": str(exc),
        }
        print(dump(refusal), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
