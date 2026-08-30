#!/usr/bin/env python3
"""Fresh exec002 mechanical recovery controller for frozen Phase-A science.

Scientific case generation, rendering, parsing, refusal semantics and numerical
floor classification are imported unchanged from low_altitude_phase_a.py.
Exec001 is immutable and is never resumed or retried.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "low_altitude_phase_a.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_a_exec002", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load reviewed Phase-A module")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

EXECUTION_ID = "low-altitude-stellar-phase-a-v1-exec002"
EXPECTED_INVOCATIONS = 28
PARENT_FAILED_EXECUTION_ID = "low-altitude-stellar-phase-a-v1-exec001"
PARENT_FAILED_RUN = 33297281047
PARENT_FAILED_JOB = 99219023542


class ExecutionRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def execute_campaign(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, output_dir: Path,
                     allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise ExecutionRefusal("scientific execution requires explicit allow_execution=True")
    if output_dir.exists():
        raise ExecutionRefusal("output directory already exists; retry/resume is forbidden")
    if not Path(uvspec).is_file():
        raise ExecutionRefusal("uvspec executable not found")
    output_dir.mkdir(parents=True)

    cases = m.build_phase_a_cases()
    if len(cases) != EXPECTED_INVOCATIONS:
        raise ExecutionRefusal("frozen Phase-A case count drift")

    results: list[dict[str, Any]] = []
    status_map: dict[str, str] = {}
    invocation_count = 0
    for row in cases:
        case_id = row["caseId"]
        case_dir = output_dir / case_id
        case_dir.mkdir()
        input_text = m.render_uvspec_input(
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            target_altitude_deg=row["targetGeometricAltitudeDeg"],
            observer_elevation_m=row["observerElevationM"],
            aod550=row["aod550"],
        )
        input_path = case_dir / "uvspec.inp"
        input_path.write_text(input_text, encoding="utf-8")
        invocation_count += 1
        proc = subprocess.run(
            [str(uvspec)], input=input_text, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        (case_dir / "uvspec.stdout").write_text(proc.stdout, encoding="utf-8")
        (case_dir / "uvspec.stderr").write_text(proc.stderr, encoding="utf-8")
        parsed = None
        refusal = None
        if proc.returncode == 0:
            try:
                parsed = m.parse_direct_transmission(
                    proc.stdout,
                    target_altitude_deg=row["targetGeometricAltitudeDeg"],
                )
                status = "PASS"
            except Exception as exc:
                status = "NUMERICALLY_UNRESOLVED"
                refusal = f"{type(exc).__name__}: {exc}"
        else:
            status = "NUMERICALLY_UNRESOLVED"
            refusal = f"uvspec_exit_{proc.returncode}"
        status_map[case_id] = status
        result = {
            **row,
            "status": status,
            "solverExitCode": int(proc.returncode),
            "parserRefusal": refusal,
            "inputSha256": sha256_file(input_path),
            "stdoutSha256": sha256_file(case_dir / "uvspec.stdout"),
            "stderrSha256": sha256_file(case_dir / "uvspec.stderr"),
            "solverInvocationOrdinal": invocation_count,
            "sameIdentityRetryUsed": False,
            "positiveEpsilonSubstitutionUsed": False,
        }
        if parsed is not None:
            result["minDirectTransmission"] = min(parsed["lineOfSightDirectTransmission"])
            result["maxDirectOpticalDepth"] = max(parsed["directOpticalDepth"])
            result["mu0"] = parsed["mu0"]
            result["sourceZenithAngleDeg"] = parsed["sourceZenithAngleDeg"]
        (case_dir / "case-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        results.append(result)

    if invocation_count != EXPECTED_INVOCATIONS:
        raise ExecutionRefusal("solver invocation count drift")
    floor = m.classify_numerical_floor(status_map)
    payload = {
        "schemaVersion": 1,
        "executionId": EXECUTION_ID,
        "parentFailedExecutionId": PARENT_FAILED_EXECUTION_ID,
        "parentFailedRun": PARENT_FAILED_RUN,
        "parentFailedJob": PARENT_FAILED_JOB,
        "parentFailureClass": "PRE_SOLVER_PROVENANCE_INSPECTION_FAILURE",
        "stageId": m.STAGE_ID,
        "caseLedgerSha256": m.case_ledger()["caseLedgerSha256"],
        "scientificSolverExecuted": True,
        "solver": "sdisort",
        "randomNumbersUsed": False,
        "solverInvocationCount": invocation_count,
        "expectedSolverInvocationCount": EXPECTED_INVOCATIONS,
        "executionComplete": len(results) == EXPECTED_INVOCATIONS,
        "githubRerunPermitted": False,
        "solverRetryPermitted": False,
        "solverResumePermitted": False,
        "positiveEpsilonSubstitutionUsed": False,
        "protectedRepresentationValidationOpened": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "phaseANumericalCapability": floor,
        "cases": results,
    }
    out = output_dir / "phase-a-exec002-result.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result_sha = sha256_file(out)
    (output_dir / "execution-receipt.json").write_text(
        json.dumps({
            "executionId": EXECUTION_ID,
            "executionComplete": payload["executionComplete"],
            "solverInvocationCount": invocation_count,
            "resultSha256": result_sha,
            "phaseAStatus": floor["status"],
            "minimumNumericallyRepresentableAltitudeDeg": floor["minimumNumericallyRepresentableAltitudeDeg"],
            "protectedRepresentationValidationOpened": False,
            "productionAuthorized": False,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not (args.execute and args.allow_execution):
        parser.error("one-shot exec002 controller requires --execute --allow-execution")
    required = [args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file, args.output_dir]
    if any(value is None for value in required):
        parser.error("all execution paths are required")
    payload = execute_campaign(
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        output_dir=args.output_dir,
        allow_execution=True,
    )
    print(json.dumps({
        "executionId": payload["executionId"],
        "executionComplete": payload["executionComplete"],
        "solverInvocationCount": payload["solverInvocationCount"],
        "phaseANumericalCapability": payload["phaseANumericalCapability"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
