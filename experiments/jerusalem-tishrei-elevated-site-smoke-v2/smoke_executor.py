#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

STAGE_ID = "jerusalem-tishrei-elevated-site-smoke-v2"
EXPECTED_VROOM_GRID = [380.0, 470.0, 480.0, 490.0, 500.0, 510.0, 520.0, 530.0, 540.0, 560.0, 580.0, 590.0, 600.0, 610.0, 640.0, 660.0, 780.0]


class SmokeExecutionError(RuntimeError):
    pass


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SmokeExecutionError(f"expected JSON object: {path}")
    return value


def load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("tishrei_infrastructure_smoke_adapter", path)
    if spec is None or spec.loader is None:
        raise SmokeExecutionError(f"cannot load smoke adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_process(command: list[str], text: str, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    start = time.monotonic()
    try:
        result = subprocess.run(command, input=text, text=True, capture_output=True, cwd=cwd, timeout=timeout_seconds, check=False)
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


def verify_context(allow_infrastructure_smoke: bool) -> None:
    if not allow_infrastructure_smoke:
        raise SmokeExecutionError("--allow-infrastructure-smoke is required")
    expected = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1"}
    stale = {key: (os.getenv(key), value) for key, value in expected.items() if os.getenv(key) != value}
    if stale:
        raise SmokeExecutionError(f"not exact first-attempt workflow_dispatch context: {stale}")


def parse_wavelength_grid(path: Path) -> list[float]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise SmokeExecutionError(f"missing/empty smoke output: {path}")
    wavelengths: list[float] = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            values = [float(x) for x in parts[1:]]
        except ValueError:
            continue
        if not math.isfinite(wavelength) or any(not math.isfinite(value) for value in values):
            raise SmokeExecutionError(f"non-finite numeric smoke output in {path}")
        wavelengths.append(wavelength)
    if not wavelengths:
        raise SmokeExecutionError(f"no numeric wavelength rows in {path}")
    return wavelengths


def validate_grid(method: str, wavelengths: list[float], path: Path) -> dict[str, Any]:
    if method == "reference-vroom":
        if len(wavelengths) != len(EXPECTED_VROOM_GRID):
            raise SmokeExecutionError(f"VROOM smoke grid row count changed in {path}: {len(wavelengths)}")
        for actual, expected in zip(wavelengths, EXPECTED_VROOM_GRID):
            if abs(actual - expected) > 1e-7:
                raise SmokeExecutionError(f"VROOM smoke grid mismatch in {path}: {actual} vs {expected}")
        return {"nodeCount": len(wavelengths), "startNm": wavelengths[0], "stopNm": wavelengths[-1], "gridMode": "frozen-17-node-vroom"}
    if method == "alis":
        if len(wavelengths) != 8001:
            raise SmokeExecutionError(f"ALIS smoke grid row count changed in {path}: {len(wavelengths)}")
        if abs(wavelengths[0] - 380.0) > 1e-7 or abs(wavelengths[-1] - 780.0) > 1e-7:
            raise SmokeExecutionError(f"ALIS smoke endpoints changed in {path}")
        for index, actual in enumerate(wavelengths):
            expected = 380.0 + 0.05 * index
            if abs(actual - expected) > 5e-5:
                raise SmokeExecutionError(f"ALIS smoke grid mismatch at {index}: {actual} vs {expected}")
        return {"nodeCount": 8001, "startNm": 380.0, "stopNm": 780.0, "stepNm": 0.05, "gridMode": "full-alis-8001-node"}
    raise SmokeExecutionError(f"unknown smoke method: {method}")


def execute(
    smoke_manifest_path: Path,
    runtime_report_path: Path,
    adapter_path: Path,
    case_id: str,
    data_dir: Path,
    repository_root: Path,
    uvspec: Path,
    output_root: Path,
    timeout_seconds: int,
    allow_infrastructure_smoke: bool,
) -> tuple[dict[str, Any], bool]:
    verify_context(allow_infrastructure_smoke)
    if timeout_seconds < 1 or timeout_seconds > 300:
        raise SmokeExecutionError("smoke timeout must be 1..300 seconds")
    if not uvspec.is_file() or not os.access(uvspec, os.X_OK):
        raise SmokeExecutionError(f"uvspec missing/not executable: {uvspec}")
    smoke = load_json(smoke_manifest_path)
    if smoke.get("stageId") != STAGE_ID or smoke.get("infrastructureOnly") is not True or smoke.get("scientificUseProhibited") is not True:
        raise SmokeExecutionError("wrong smoke execution boundary")
    cases = smoke.get("cases") or []
    matches = [case for case in cases if isinstance(case, dict) and case.get("caseId") == case_id]
    if len(matches) != 1:
        raise SmokeExecutionError(f"case not unique in smoke manifest: {case_id}")
    case = matches[0]
    if case.get("photonHistories") != 10000:
        raise SmokeExecutionError("smoke photon count changed")
    adapter = load_adapter(adapter_path)
    output_root.mkdir(parents=True, exist_ok=True)
    prepared = adapter.prepare_case(smoke_manifest_path, runtime_report_path, case_id, data_dir, repository_root, output_root)
    if prepared.get("scientificUseProhibited") is not True or prepared.get("photonHistories") != 10000:
        raise SmokeExecutionError("prepared smoke boundary changed")
    case_dir = output_root / case_id
    input_path = case_dir / "input-resolved.txt"
    text = input_path.read_text(encoding="utf-8")

    syntax = run_process([str(uvspec), "-c"], text, case_dir, min(60, timeout_seconds))
    (case_dir / "syntax-stdout.txt").write_text(str(syntax["stdout"]), encoding="utf-8")
    (case_dir / "syntax-stderr.txt").write_text(str(syntax["stderr"]), encoding="utf-8")
    solver: dict[str, Any] | None = None
    failure: dict[str, Any] | None = None
    syntax_count = 1
    solver_count = 0
    if syntax["timedOut"] or syntax["exitCode"] != 0:
        failure = {"code": "syntax-failure", "detail": {k: syntax[k] for k in ("exitCode", "timedOut", "elapsedSeconds")}}
    else:
        solver_count = 1
        solver = run_process([str(uvspec)], text, case_dir, timeout_seconds)
        (case_dir / "solver-stdout.txt").write_text(str(solver["stdout"]), encoding="utf-8")
        (case_dir / "solver-stderr.txt").write_text(str(solver["stderr"]), encoding="utf-8")
        if solver["timedOut"] or solver["exitCode"] != 0:
            failure = {"code": "solver-failure", "detail": {k: solver[k] for k in ("exitCode", "timedOut", "elapsedSeconds")}}

    structure: dict[str, Any] | None = None
    radiance_path = case_dir / "mc.rad.spc"
    std_path = case_dir / "mc.rad.std.spc"
    if failure is None:
        try:
            radiance_grid = parse_wavelength_grid(radiance_path)
            std_grid = parse_wavelength_grid(std_path)
            if radiance_grid != std_grid:
                raise SmokeExecutionError("radiance/std wavelength grids differ")
            structure = validate_grid(case["method"], radiance_grid, radiance_path)
        except Exception as exc:
            failure = {"code": "structural-output-failure", "detail": str(exc)}

    ok = failure is None
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "INFRASTRUCTURE_SMOKE_COMPLETED" if ok else "INFRASTRUCTURE_SMOKE_FAILED",
        "infrastructureOnly": True,
        "scientificDiagnostic": False,
        "scientificUseProhibited": True,
        "successDoesNotAuthorizeScientificExecution": True,
        "successDoesNotAuthorizeProduction": True,
        "caseId": case_id,
        "method": case["method"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "smokeManifestRawSha256": raw_sha256(smoke_manifest_path),
        "runtimeReportRawSha256": raw_sha256(runtime_report_path),
        "adapterRawSha256": raw_sha256(adapter_path),
        "inputResolvedSha256": prepared["inputResolvedSha256"],
        "syntaxCheckCount": syntax_count,
        "solverExecutionCount": solver_count,
        "syntax": {k: syntax[k] for k in ("exitCode", "timedOut", "elapsedSeconds")},
        "solver": None if solver is None else {k: solver[k] for k in ("exitCode", "timedOut", "elapsedSeconds")},
        "structuralOutput": structure,
        "radianceOutputSha256": raw_sha256(radiance_path) if ok else None,
        "stdOutputSha256": raw_sha256(std_path) if ok else None,
        "failure": failure,
        "boundary": "low-photon infrastructure smoke only; output values are prohibited from scientific interpretation, fitting, validation, or visibility analysis",
    }
    (case_dir / "smoke-case-result.json").write_text(dump(result), encoding="utf-8")
    return result, ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--smoke-manifest", type=Path, required=True)
    p.add_argument("--runtime-report", type=Path, required=True)
    p.add_argument("--adapter", type=Path, required=True)
    p.add_argument("--case-id", required=True)
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--repository-root", type=Path, required=True)
    p.add_argument("--uvspec", type=Path, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--timeout-seconds", type=int, required=True)
    p.add_argument("--allow-infrastructure-smoke", action="store_true")
    args = p.parse_args()
    try:
        result, ok = execute(args.smoke_manifest, args.runtime_report, args.adapter, args.case_id, args.data_dir, args.repository_root, args.uvspec, args.output_root, args.timeout_seconds, args.allow_infrastructure_smoke)
        print(dump(result), end="")
        return 0 if ok else 2
    except Exception as exc:
        report = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "INFRASTRUCTURE_SMOKE_REFUSED_OR_FAILED",
            "infrastructureOnly": True,
            "scientificUseProhibited": True,
            "reason": str(exc),
        }
        print(dump(report), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
