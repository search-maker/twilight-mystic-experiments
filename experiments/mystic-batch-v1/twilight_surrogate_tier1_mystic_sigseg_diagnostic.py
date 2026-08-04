#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

STAGE_ID = "twilight-surrogate-tier-1-mystic-sigseg-diagnostic-v1"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_RUNTIME_LOCK_SHA256 = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"
EXPECTED_RESOLVED_INPUT_SHA256 = "89cbb012ef8ec6118285ab2664a6e2a32ad99851c313fcadab8244308bee04d4"
EXPECTED_SITE_ALTITUDE_KM = 0.357143
EXPECTED_MYSTIC_PHOTONS = 1
EXPECTED_MYSTIC_SEED = 990004
MAXIMUM_MYSTIC_SOLVER_EXECUTIONS = 1
SIGSEGV_MARKERS = (
    "Program received signal SIGSEGV",
    "Thread 1 received signal SIGSEGV",
    "received signal SIGSEGV",
)


class DiagnosticError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_probe_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise DiagnosticError(f"probe module missing: {path}")
    spec = importlib.util.spec_from_file_location("tier1_atm_z_grid_probe", path)
    if spec is None or spec.loader is None:
        raise DiagnosticError(f"cannot load probe module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finite_float(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise DiagnosticError(f"non-finite {label}")
    return number


def validate_probe_contract(probe: ModuleType) -> None:
    if finite_float(probe.PRIMARY_SITE_ALTITUDE_KM, "site altitude") != EXPECTED_SITE_ALTITUDE_KM:
        raise DiagnosticError("probe site altitude changed")
    if int(probe.MYSTIC_PHOTONS) != EXPECTED_MYSTIC_PHOTONS:
        raise DiagnosticError("probe photon count changed")
    if int(probe.MYSTIC_SEED) != EXPECTED_MYSTIC_SEED:
        raise DiagnosticError("probe seed changed")
    if str(probe.EXPECTED_ZOUT) != "zout 0.000000":
        raise DiagnosticError("probe local-surface zout changed")


def write_text(path: Path, value: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return raw_sha256(path)


def run_metadata_command(command: Sequence[str], output_path: Path) -> dict[str, Any]:
    start = time.monotonic()
    try:
        process = subprocess.run(
            list(command),
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        timed_out = False
        returncode = process.returncode
        text = process.stdout + process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        text = stdout + stderr
    elapsed = time.monotonic() - start
    digest = write_text(output_path, text)
    return {
        "command": list(command),
        "exitCode": returncode,
        "timedOut": timed_out,
        "elapsedSeconds": elapsed,
        "outputPath": output_path.name,
        "outputSha256": digest,
    }


def gdb_command_text(input_path: Path) -> str:
    return "\n".join(
        [
            "set pagination off",
            "set confirm off",
            "set print thread-events off",
            "set debuginfod enabled off",
            "set disable-randomization off",
            "handle SIGPIPE nostop noprint pass",
            "handle SIGSEGV stop print nopass",
            f"run < {input_path.resolve()}",
            "echo \\n=== TIER1_SIGNAL_CONTEXT ===\\n",
            "info program",
            "thread apply all bt full",
            "info registers",
            "x/32i $pc-64",
            "info sharedlibrary",
            "info proc mappings",
            "echo \\n=== END_TIER1_SIGNAL_CONTEXT ===\\n",
            "quit",
            "",
        ]
    )


def parse_gdb_evidence(text: str) -> dict[str, Any]:
    sigsegv = any(marker in text for marker in SIGSEGV_MARKERS)
    backtrace_frames = re.findall(r"(?m)^#(\d+)\s+(.+)$", text)
    instruction_pointer = None
    register_match = re.search(r"(?m)^(?:rip|pc)\s+([^\s]+)\s+(.+)$", text)
    if register_match:
        instruction_pointer = {
            "value": register_match.group(1),
            "description": register_match.group(2).strip(),
        }
    symbolic_frames = [
        {"index": int(index), "text": frame}
        for index, frame in backtrace_frames
        if "??" not in frame
    ]
    return {
        "sigsegvReproduced": sigsegv,
        "backtraceObserved": bool(backtrace_frames),
        "backtraceFrameCount": len(backtrace_frames),
        "symbolicFrameCount": len(symbolic_frames),
        "symbolicFrames": symbolic_frames[:20],
        "instructionPointerObserved": instruction_pointer is not None,
        "instructionPointer": instruction_pointer,
        "signalContextBoundaryObserved": (
            "=== TIER1_SIGNAL_CONTEXT ===" in text
            and "=== END_TIER1_SIGNAL_CONTEXT ===" in text
        ),
    }


def package_identity(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise DiagnosticError(f"package identity file missing: {path}")
    return {
        "path": path.name,
        "sizeBytes": path.stat().st_size,
        "rawSha256": raw_sha256(path),
    }


def build_exact_input(
    probe: ModuleType,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    run_dir: Path,
) -> tuple[str, str, list[float]]:
    grid = probe.forced_grid_ascending(atmosphere, EXPECTED_SITE_ALTITUDE_KM)
    raw = probe.render_mystic_input(
        data_dir,
        atmosphere,
        solar_flux,
        run_dir,
        grid,
        False,
    )
    resolved = probe.render_mystic_input(
        data_dir,
        atmosphere,
        solar_flux,
        run_dir,
        grid,
        True,
    )
    lines = resolved.splitlines()
    if "mc_photons 1" not in lines:
        raise DiagnosticError("exact one-photon boundary absent")
    if "mc_randomseed 990004" not in lines:
        raise DiagnosticError("exact diagnostic seed absent")
    if "zout 0.000000" not in lines:
        raise DiagnosticError("exact local-surface zout absent")
    if any(line.startswith("altitude ") for line in lines):
        raise DiagnosticError("forbidden altitude line present")
    if any(line.startswith("mc_elevation_file ") for line in lines):
        raise DiagnosticError("forbidden mc_elevation_file line present")
    return raw, resolved, list(grid)


def diagnostic(
    uvspec: Path,
    gdb: Path,
    probe_module: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    runtime_lock: Path,
    output_dir: Path,
    package_explicit: Path | None,
    package_json: Path | None,
    gdb_package_explicit: Path | None,
    gdb_package_json: Path | None,
) -> dict[str, Any]:
    uvspec = uvspec.resolve()
    gdb = gdb.resolve()
    for path, label in (
        (uvspec, "uvspec"),
        (gdb, "gdb"),
        (probe_module, "probe module"),
        (atmosphere, "atmosphere"),
        (solar_flux, "solar flux"),
        (runtime_lock, "runtime lock"),
    ):
        if not path.is_file():
            raise DiagnosticError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise DiagnosticError(f"data directory missing: {data_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = output_dir / f"h-{EXPECTED_SITE_ALTITUDE_KM:.6f}" / "mystic-B-one-photon"
    run_dir.mkdir(parents=True, exist_ok=True)

    probe = load_probe_module(probe_module)
    validate_probe_contract(probe)

    uvspec_hash = raw_sha256(uvspec)
    runtime_lock_hash = raw_sha256(runtime_lock)
    if uvspec_hash != EXPECTED_UVSPEC_SHA256:
        raise DiagnosticError(
            f"frozen uvspec hash mismatch: {uvspec_hash} != {EXPECTED_UVSPEC_SHA256}"
        )
    if runtime_lock_hash != EXPECTED_RUNTIME_LOCK_SHA256:
        raise DiagnosticError(
            "runtime lock hash mismatch: "
            f"{runtime_lock_hash} != {EXPECTED_RUNTIME_LOCK_SHA256}"
        )

    raw_input, resolved_input, grid = build_exact_input(
        probe,
        data_dir,
        atmosphere,
        solar_flux,
        run_dir,
    )
    raw_input_path = run_dir / "input-raw.txt"
    resolved_input_path = run_dir / "input-resolved.txt"
    raw_input_hash = write_text(raw_input_path, raw_input)
    resolved_input_hash = write_text(resolved_input_path, resolved_input)
    if resolved_input_hash != EXPECTED_RESOLVED_INPUT_SHA256:
        raise DiagnosticError(
            "resolved diagnostic input differs from preserved failed-probe input: "
            f"{resolved_input_hash} != {EXPECTED_RESOLVED_INPUT_SHA256}"
        )

    metadata = {
        "file": run_metadata_command(["file", str(uvspec)], output_dir / "uvspec-file.txt"),
        "ldd": run_metadata_command(["ldd", str(uvspec)], output_dir / "uvspec-ldd.txt"),
        "readelf": run_metadata_command(
            ["readelf", "-h", "-l", "-n", "-d", "-Ws", str(uvspec)],
            output_dir / "uvspec-readelf.txt",
        ),
    }

    command_path = run_dir / "gdb-command.txt"
    command_hash = write_text(command_path, gdb_command_text(resolved_input_path))
    start = time.monotonic()
    timed_out = False
    solver_execution_count = 0
    try:
        solver_execution_count = 1
        process = subprocess.run(
            [
                str(gdb),
                "-q",
                "-nx",
                "--batch",
                "-x",
                str(command_path.resolve()),
                "--args",
                str(uvspec),
            ],
            cwd=run_dir,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
            env=os.environ.copy(),
        )
        gdb_exit_code = process.returncode
        gdb_stdout = process.stdout
        gdb_stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        gdb_exit_code = 124
        gdb_stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        gdb_stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    elapsed = time.monotonic() - start

    gdb_stdout_hash = write_text(run_dir / "gdb-stdout.txt", gdb_stdout)
    gdb_stderr_hash = write_text(run_dir / "gdb-stderr.txt", gdb_stderr)
    combined = gdb_stdout + "\n" + gdb_stderr
    parsed = parse_gdb_evidence(combined)

    generated = sorted(
        path
        for path in run_dir.iterdir()
        if path.is_file() and path.name.startswith("mc")
    )
    generated_rows = [
        {
            "filename": path.name,
            "sizeBytes": path.stat().st_size,
            "rawSha256": raw_sha256(path),
        }
        for path in generated
    ]
    for path in generated:
        path.unlink()

    evidence_captured = (
        parsed["sigsegvReproduced"]
        and parsed["backtraceObserved"]
        and parsed["signalContextBoundaryObserved"]
        and not timed_out
        and solver_execution_count == 1
    )
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "FROZEN_MYSTIC_SIGSEGV_REPRODUCED_WITH_BACKTRACE"
            if evidence_captured
            else "FROZEN_MYSTIC_SIGSEGV_DIAGNOSTIC_INCONCLUSIVE"
        ),
        "diagnosticEvidenceCaptured": evidence_captured,
        "diagnosticOnly": True,
        "proofPassed": False,
        "mysticAcceptanceEstablished": False,
        "physicalEquivalenceEstablished": False,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "frozenTier1InvariantsChanged": False,
        "frozenTargetEnvironmentModified": False,
        "debuggerInstalledInSeparateEnvironment": True,
        "mysticSolverExecutionCount": solver_execution_count,
        "maximumPermittedMysticSolverExecutionCount": MAXIMUM_MYSTIC_SOLVER_EXECUTIONS,
        "siteAltitudeKm": EXPECTED_SITE_ALTITUDE_KM,
        "localSurfaceZoutKm": 0.0,
        "mcPhotons": EXPECTED_MYSTIC_PHOTONS,
        "mcRandomSeed": EXPECTED_MYSTIC_SEED,
        "forcedGridAscendingKm": grid,
        "resolvedInput": {
            "path": str(resolved_input_path.relative_to(output_dir)),
            "rawSha256": resolved_input_hash,
            "matchesPreservedFailedProbeInput": resolved_input_hash
            == EXPECTED_RESOLVED_INPUT_SHA256,
        },
        "rawInput": {
            "path": str(raw_input_path.relative_to(output_dir)),
            "rawSha256": raw_input_hash,
        },
        "gdb": {
            "path": str(gdb),
            "commandFile": str(command_path.relative_to(output_dir)),
            "commandFileRawSha256": command_hash,
            "exitCode": gdb_exit_code,
            "timedOut": timed_out,
            "elapsedSeconds": elapsed,
            "stdoutRawSha256": gdb_stdout_hash,
            "stderrRawSha256": gdb_stderr_hash,
            **parsed,
        },
        "generatedFiles": generated_rows,
        "generatedFilesPreserved": False,
        "runtime": {
            "uvspecPath": str(uvspec),
            "uvspecSha256": uvspec_hash,
            "runtimeLockRawSha256": runtime_lock_hash,
            "atmosphereSha256": raw_sha256(atmosphere),
            "solarFluxSha256": raw_sha256(solar_flux),
            "packageExplicit": package_identity(package_explicit),
            "packageJson": package_identity(package_json),
            "gdbPackageExplicit": package_identity(gdb_package_explicit),
            "gdbPackageJson": package_identity(gdb_package_json),
            "binaryMetadata": metadata,
        },
        "boundary": (
            "one exact-input, one-photon debugger reproduction only; debugger lives in a separate "
            "tool environment; no proof, dataset, authorization, dispatch, training, Tier-2, or "
            "production claim"
        ),
    }
    report_path = output_dir / "mystic-sigseg-diagnostic.json"
    report_path.write_text(dump(result), encoding="utf-8")
    result["reportRawSha256"] = raw_sha256(report_path)
    if not evidence_captured:
        raise DiagnosticError(
            "SIGSEGV diagnostic did not preserve a complete stopped-process backtrace"
        )
    return result


def failure_report(reason: str) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "REFUSED",
        "diagnosticEvidenceCaptured": False,
        "diagnosticOnly": True,
        "proofPassed": False,
        "reason": reason,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "mysticSolverExecutionCount": 0,
        "maximumPermittedMysticSolverExecutionCount": MAXIMUM_MYSTIC_SOLVER_EXECUTIONS,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--gdb", type=Path, required=True)
    parser.add_argument("--probe-module", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--solar-flux", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--package-explicit", type=Path)
    parser.add_argument("--package-json", type=Path)
    parser.add_argument("--gdb-package-explicit", type=Path)
    parser.add_argument("--gdb-package-json", type=Path)
    args = parser.parse_args()
    try:
        result = diagnostic(
            args.uvspec,
            args.gdb,
            args.probe_module,
            args.data_dir,
            args.atmosphere,
            args.solar_flux,
            args.runtime_lock,
            args.output_dir,
            args.package_explicit,
            args.package_json,
            args.gdb_package_explicit,
            args.gdb_package_json,
        )
        print(dump(result), end="")
        return 0
    except Exception as exc:
        failure = failure_report(str(exc))
        try:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = args.output_dir / "mystic-sigseg-diagnostic.json"
            if not report_path.exists():
                report_path.write_text(dump(failure), encoding="utf-8")
        except Exception:
            pass
        print(dump(failure), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
