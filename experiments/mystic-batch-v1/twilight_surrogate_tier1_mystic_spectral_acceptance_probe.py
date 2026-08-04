#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

STAGE_ID = "twilight-surrogate-tier-1-mystic-spectral-acceptance-probe-v1"
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_RUNTIME_LOCK_SHA256 = "3b5fbec964642b04c73a6423b3355dbcc4ba5e84f9614f6d74420491bacc20c5"
SITE_ALTITUDE_KM = 0.357143
WAVELENGTH_START_NM = 380.0
WAVELENGTH_END_NM = 780.0
IMPORTANCE_WAVELENGTH_NM = 550.0
CONTROL_SZA_DEG = 30.0
CONTROL_PHI0_DEG = 0.0
CONTROL_UMU = -0.5
CONTROL_PHI_DEG = 36.0
CONTROL_ALBEDO = 0.15
CONTROL_AOD550 = 0.081818
MYSTIC_PHOTONS = 1
MYSTIC_SEED = 990005
MAXIMUM_MYSTIC_SOLVER_EXECUTIONS = 1
EXPECTED_ZOUT = "zout 0.000000"
ALTITUDE_REJECTION_FRAGMENT = "option altitude does not work with"
SURFACE_MARKER = f"forced new altitude = {SITE_ALTITUDE_KM:.6f}"
ALIS_MARKER_FRAGMENT = "ALIS calculation wavelength: 550"

PRIOR_CRASH_RUN_ID = 30930545636
PRIOR_CRASH_ARTIFACT_ID = 8900947961
PRIOR_CRASH_ARTIFACT_DIGEST = "f68b33242657c11ed4be3f1c7c14e98e5e5e80aee9e7edd86c3d613adfa406f0"
PRIOR_CRASH_INPUT_SHA256 = "89cbb012ef8ec6118285ab2664a6e2a32ad99851c313fcadab8244308bee04d4"
PRIOR_CRASH_GDB_STDOUT_SHA256 = "eb14aab4f2d3ab517a117100bec26b8e03e21da087793d24a23780f4fce2a2dc"
PRIOR_CRASH_GDB_STDERR_SHA256 = "89c087695852e69d09357c55c0c0c354a3203d5d6187703b99323b239b24c163"


class ProbeError(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_base_probe(path: Path) -> ModuleType:
    if not path.is_file():
        raise ProbeError(f"base probe module missing: {path}")
    spec = importlib.util.spec_from_file_location("tier1_atm_z_grid_probe", path)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load base probe module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_control_contract() -> None:
    values = (
        SITE_ALTITUDE_KM,
        WAVELENGTH_START_NM,
        WAVELENGTH_END_NM,
        IMPORTANCE_WAVELENGTH_NM,
        CONTROL_SZA_DEG,
        CONTROL_PHI0_DEG,
        CONTROL_UMU,
        CONTROL_PHI_DEG,
        CONTROL_ALBEDO,
        CONTROL_AOD550,
    )
    if not all(math.isfinite(value) for value in values):
        raise ProbeError("non-finite control value")
    if not WAVELENGTH_START_NM < IMPORTANCE_WAVELENGTH_NM < WAVELENGTH_END_NM:
        raise ProbeError("ALIS importance wavelength must be strictly inside the spectral interval")
    if MYSTIC_PHOTONS != 1 or MAXIMUM_MYSTIC_SOLVER_EXECUTIONS != 1:
        raise ProbeError("probe must remain exactly one photon and one solver execution")
    if MYSTIC_SEED <= 0:
        raise ProbeError("invalid diagnostic seed")


def path_value(path: Path, token: str, resolved: bool) -> str:
    return str(path.resolve()) if resolved else token


def render_input(
    base: ModuleType,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    run_dir: Path,
    resolved: bool,
) -> tuple[str, list[float]]:
    validate_control_contract()
    grid = list(base.forced_grid_ascending(atmosphere, SITE_ALTITUDE_KM))
    if not grid or grid[0] != SITE_ALTITUDE_KM:
        raise ProbeError("candidate grid does not begin at the site altitude")
    if any(grid[index] >= grid[index + 1] for index in range(len(grid) - 1)):
        raise ProbeError("candidate grid is not strictly ascending")
    basename = path_value(run_dir / "mc", "${OUTPUT_DIR}/mc", resolved)
    lines = [
        f"data_files_path {path_value(data_dir, '${LIBRADTRAN_DATA}', resolved)}",
        f"atmosphere_file {path_value(atmosphere, '${ATMOSPHERE_FILE}', resolved)}",
        f"source solar {path_value(solar_flux, '${SOLAR_FLUX_FILE}', resolved)}",
        "mol_abs_param crs",
        f"wavelength {WAVELENGTH_START_NM:.1f} {WAVELENGTH_END_NM:.1f}",
        f"sza {CONTROL_SZA_DEG:.6f}",
        f"phi0 {CONTROL_PHI0_DEG:.6f}",
        f"albedo {CONTROL_ALBEDO:.6f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {CONTROL_AOD550:.6f}",
        "atm_z_grid " + " ".join(f"{value:.6f}" for value in grid),
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {MYSTIC_PHOTONS}",
        "mc_vroom off",
        "mc_std",
        f"mc_randomseed {MYSTIC_SEED}",
        f"mc_basename {basename}",
        f"mc_spectral_is {IMPORTANCE_WAVELENGTH_NM:.1f}",
        EXPECTED_ZOUT,
        f"umu {CONTROL_UMU:.8f}",
        f"phi {CONTROL_PHI_DEG:.6f}",
        "verbose",
        "",
    ]
    text = "\n".join(lines)
    actual = text.splitlines()
    if any(line.startswith("altitude ") for line in actual):
        raise ProbeError("candidate input contains forbidden explicit altitude")
    if any(line.startswith("mc_elevation_file ") for line in actual):
        raise ProbeError("candidate input contains forbidden mc_elevation_file")
    if actual.count(EXPECTED_ZOUT) != 1:
        raise ProbeError("candidate input lacks exact local-surface zout")
    if actual.count(f"mc_photons {MYSTIC_PHOTONS}") != 1:
        raise ProbeError("candidate input lacks exact one-photon line")
    if actual.count(f"mc_spectral_is {IMPORTANCE_WAVELENGTH_NM:.1f}") != 1:
        raise ProbeError("candidate input lacks exact interior ALIS reference")
    return text, grid


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return raw_sha256(path)


def inventory_files(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.name):
        if not path.is_file():
            continue
        rows.append(
            {
                "filename": path.name,
                "sizeBytes": path.stat().st_size,
                "rawSha256": raw_sha256(path),
                "numericalOutput": path.name.startswith("mc"),
                "randomSeedState": path.name == "randomseed",
            }
        )
    return rows


def prior_crash_interpretation() -> dict[str, Any]:
    return {
        "classification": "SINGLE_WAVELENGTH_ENDPOINT_ALIS_REFERENCE_NULL_DEREFERENCE",
        "confidence": "binary-evidence-strong-source-provenance-separately-unresolved",
        "runId": PRIOR_CRASH_RUN_ID,
        "artifactId": PRIOR_CRASH_ARTIFACT_ID,
        "artifactZipSha256": PRIOR_CRASH_ARTIFACT_DIGEST,
        "resolvedInputSha256": PRIOR_CRASH_INPUT_SHA256,
        "gdbStdoutSha256": PRIOR_CRASH_GDB_STDOUT_SHA256,
        "gdbStderrSha256": PRIOR_CRASH_GDB_STDERR_SHA256,
        "observed": {
            "signal": "SIGSEGV",
            "function": "generate_photon.isra",
            "instructionOffset": 1013,
            "instruction": "mov (%rax),%eax",
            "rax": 0,
            "callStack": [
                "generate_photon.isra",
                "mystic",
                "call_solver",
                "setup_and_call_solver",
                "solve_rte",
                "uvspec",
                "main",
            ],
        },
        "binaryConsistentFieldMapping": {
            "atmosphereNlambdaAbsOffsetHex": "0x108",
            "atmosphereIlambdaRefOffsetHex": "0x128",
            "photonIvAlisOffsetHex": "0x100",
            "photonNlambdaOffsetHex": "0x22c",
            "interpretation": (
                "the crash dereferenced a null atmosphere ilambda_ref pointer while initializing "
                "the ALIS photon reference index"
            ),
        },
        "triggeringProbeConfiguration": {
            "spectralIntervalNm": [550.0, 550.0],
            "explicitAlisReferenceNm": 550.0,
            "referenceAtUpperEndpoint": True,
        },
        "correctedProbeConfiguration": {
            "spectralIntervalNm": [WAVELENGTH_START_NM, WAVELENGTH_END_NM],
            "explicitAlisReferenceNm": IMPORTANCE_WAVELENGTH_NM,
            "referenceStrictlyInsideInterval": True,
            "matchesTier1SpectralDomain": True,
            "lowSzaNonScientificControl": True,
        },
        "sourceBoundary": (
            "the exact package source archive remains unaccepted; this classification is bound "
            "to exact binary disassembly plus a matching public 2.0.6 source-code structure"
        ),
    }


def package_identity(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise ProbeError(f"package identity file missing: {path}")
    return {"path": path.name, "rawSha256": raw_sha256(path), "sizeBytes": path.stat().st_size}


def run_probe(
    uvspec: Path,
    base_probe_module: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    runtime_lock: Path,
    output_dir: Path,
    package_explicit: Path | None,
    package_json: Path | None,
) -> dict[str, Any]:
    uvspec = uvspec.resolve()
    for path, label in (
        (uvspec, "uvspec"),
        (base_probe_module, "base probe module"),
        (atmosphere, "atmosphere"),
        (solar_flux, "solar flux"),
        (runtime_lock, "runtime lock"),
    ):
        if not path.is_file():
            raise ProbeError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise ProbeError(f"data directory missing: {data_dir}")

    uvspec_hash = raw_sha256(uvspec)
    runtime_lock_hash = raw_sha256(runtime_lock)
    if uvspec_hash != EXPECTED_UVSPEC_SHA256:
        raise ProbeError(f"frozen uvspec hash mismatch: {uvspec_hash}")
    if runtime_lock_hash != EXPECTED_RUNTIME_LOCK_SHA256:
        raise ProbeError(f"runtime lock hash mismatch: {runtime_lock_hash}")

    base = load_base_probe(base_probe_module)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = output_dir / f"h-{SITE_ALTITUDE_KM:.6f}" / "mystic-B-tier1-spectrum-one-photon"
    run_dir.mkdir(parents=True, exist_ok=False)
    raw_input, grid = render_input(base, data_dir, atmosphere, solar_flux, run_dir, False)
    resolved_input, resolved_grid = render_input(base, data_dir, atmosphere, solar_flux, run_dir, True)
    if grid != resolved_grid:
        raise ProbeError("raw and resolved input grids differ")
    raw_input_path = run_dir / "input-raw.txt"
    resolved_input_path = run_dir / "input-resolved.txt"
    raw_input_hash = write_text(raw_input_path, raw_input)
    resolved_input_hash = write_text(resolved_input_path, resolved_input)

    preexisting = {path.resolve() for path in run_dir.iterdir() if path.is_file()}
    start = time.monotonic()
    timed_out = False
    solver_execution_count = 1
    try:
        process = subprocess.run(
            [str(uvspec)],
            cwd=run_dir,
            input=resolved_input,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        exit_code = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    elapsed = time.monotonic() - start

    solver_generated_paths = [
        path
        for path in run_dir.iterdir()
        if path.is_file() and path.resolve() not in preexisting
    ]
    generated_rows = inventory_files(solver_generated_paths)
    numerical_rows = [row for row in generated_rows if row["numericalOutput"]]
    seed_state_rows = [row for row in generated_rows if row["randomSeedState"]]
    for path in solver_generated_paths:
        path.unlink()
    remaining_solver_generated = [
        path.name
        for path in run_dir.iterdir()
        if path.is_file() and path.resolve() not in preexisting
    ]
    if remaining_solver_generated:
        raise ProbeError(f"solver-generated files remain after deletion: {remaining_solver_generated}")

    stdout_hash = write_text(run_dir / "stdout.txt", stdout)
    stderr_hash = write_text(run_dir / "stderr.txt", stderr)
    surface_marker_observed = SURFACE_MARKER in stderr
    alis_marker_observed = ALIS_MARKER_FRAGMENT in stderr
    acceptance_passed = (
        exit_code == 0
        and not timed_out
        and surface_marker_observed
        and alis_marker_observed
        and ALTITUDE_REJECTION_FRAGMENT not in stderr
        and bool(numerical_rows)
        and solver_execution_count == 1
    )
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "MYSTIC_ACCEPTS_ATM_Z_GRID_WITH_TIER1_SPECTRAL_DOMAIN"
            if acceptance_passed
            else "MYSTIC_TIER1_SPECTRAL_ACCEPTANCE_PROBE_FAILED"
        ),
        "acceptanceProbePassed": acceptance_passed,
        "diagnosticOnly": True,
        "combinedEquivalenceProofPassed": False,
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "frozenTier1InvariantsChanged": False,
        "mysticSolverExecutionCount": solver_execution_count,
        "maximumPermittedMysticSolverExecutionCount": MAXIMUM_MYSTIC_SOLVER_EXECUTIONS,
        "candidateRepresentation": {
            "siteAltitudeKm": SITE_ALTITUDE_KM,
            "atmZGridBottomIsSiteAltitude": grid[0] == SITE_ALTITUDE_KM,
            "forcedGridAscendingKm": grid,
            "explicitAltitudePresent": False,
            "mcElevationFilePresent": False,
            "localSurfaceZoutKm": 0.0,
            "surfaceMarkerObserved": surface_marker_observed,
        },
        "controlGeometry": {
            "purpose": "low-SZA exact-runtime acceptance control only",
            "szaDeg": CONTROL_SZA_DEG,
            "notFrozenTier1TwilightGeometry": True,
        },
        "spectralConfiguration": {
            "wavelengthDomainNm": [WAVELENGTH_START_NM, WAVELENGTH_END_NM],
            "alisImportanceWavelengthNm": IMPORTANCE_WAVELENGTH_NM,
            "alisReferenceStrictlyInsideDomain": (
                WAVELENGTH_START_NM < IMPORTANCE_WAVELENGTH_NM < WAVELENGTH_END_NM
            ),
            "matchesFrozenTier1Domain": True,
            "alisMarkerObserved": alis_marker_observed,
        },
        "mcPhotons": MYSTIC_PHOTONS,
        "mcRandomSeed": MYSTIC_SEED,
        "execution": {
            "exitCode": exit_code,
            "timedOut": timed_out,
            "elapsedSeconds": elapsed,
            "stdoutSha256": stdout_hash,
            "stderrSha256": stderr_hash,
        },
        "input": {
            "rawInputSha256": raw_input_hash,
            "resolvedInputSha256": resolved_input_hash,
        },
        "solverGeneratedFilesBeforeDeletion": generated_rows,
        "solverGeneratedNumericalFileCount": len(numerical_rows),
        "solverGeneratedRandomSeedStateFileCount": len(seed_state_rows),
        "solverGeneratedFilesPreserved": False,
        "priorCrashInterpretation": prior_crash_interpretation(),
        "runtime": {
            "uvspecSha256": uvspec_hash,
            "runtimeLockRawSha256": runtime_lock_hash,
            "atmosphereSha256": raw_sha256(atmosphere),
            "solarFluxSha256": raw_sha256(solar_flux),
            "packageExplicit": package_identity(package_explicit),
            "packageJson": package_identity(package_json),
        },
        "sourceProvenance": {
            "status": "SEPARATE_UNRESOLVED_OFFICIAL_ARCHIVE_HASH_MISMATCH",
            "sourceEvidenceAccepted": False,
            "behaviorEvidenceIndependentOfSourceArchiveAcceptance": True,
        },
        "boundary": (
            "one low-SZA, one-photon MYSTIC acceptance probe using the frozen Tier-1 spectral "
            "domain; generated solver files are hashed then deleted; no dataset, combined proof, "
            "authorization, dispatch, training, Tier-2, or production claim"
        ),
    }
    report_path = output_dir / "mystic-spectral-acceptance-probe.json"
    report_path.write_text(dump(result), encoding="utf-8")
    if not acceptance_passed:
        raise ProbeError("corrected spectral acceptance probe failed; evidence preserved")
    return result


def failure_report(reason: str) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "REFUSED",
        "acceptanceProbePassed": False,
        "diagnosticOnly": True,
        "combinedEquivalenceProofPassed": False,
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
    parser.add_argument("--base-probe-module", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--solar-flux", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--package-explicit", type=Path)
    parser.add_argument("--package-json", type=Path)
    args = parser.parse_args()
    try:
        result = run_probe(
            args.uvspec,
            args.base_probe_module,
            args.data_dir,
            args.atmosphere,
            args.solar_flux,
            args.runtime_lock,
            args.output_dir,
            args.package_explicit,
            args.package_json,
        )
        print(dump(result), end="")
        return 0
    except Exception as exc:
        failure = failure_report(str(exc))
        try:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = args.output_dir / "mystic-spectral-acceptance-probe.json"
            if not report_path.exists():
                report_path.write_text(dump(failure), encoding="utf-8")
        except Exception:
            pass
        print(dump(failure), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
