#!/usr/bin/env python3
"""One-shot deterministic Phase-B training controller for LOWALT-STELLAR-STATE-0001.

This controller executes only the frozen 275 fresh training spectra. It does
not generate the 5-degree seam, does not open protected validation, and does
not authorize application/production support. The exact 5-degree seam remains
owned by the authoritative v3.2 asset.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PHASE_A_PATH = HERE / "low_altitude_phase_a.py"
PHASE_B_PATH = HERE / "low_altitude_phase_b.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reviewed module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phase_a = _load(PHASE_A_PATH, "low_altitude_phase_a_for_phase_b_training")
phase_b = _load(PHASE_B_PATH, "low_altitude_phase_b_for_training")

EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec001"
SCIENTIFIC_STATE = phase_b.SCIENTIFIC_STATE
EXPECTED_INVOCATIONS = phase_b.EXPECTED_TRAINING_SPECTRA
EXACT_PACKAGE_SPEC = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
UVSPEC_HELP_SHA256 = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"


class TrainingExecutionRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def training_case_id(row: dict[str, Any]) -> str:
    return f"h{float(row['targetGeometricAltitudeDeg']):.5f}_e{int(round(float(row['observerElevationM']))):04d}_a{float(row['aod550']):.5f}"


def render_training_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                          target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> str:
    altitude = phase_b.finite("targetGeometricAltitudeDeg", target_altitude_deg)
    elevation = phase_b.finite("observerElevationM", observer_elevation_m)
    aod = phase_b.finite("aod550", aod550)
    if altitude not in phase_b.TRAINING_ALTITUDE_DEG:
        raise TrainingExecutionRefusal("renderer restricted to frozen Phase-B training altitudes")
    if elevation not in phase_b.ELEVATION_KNOTS_M:
        raise TrainingExecutionRefusal("renderer restricted to frozen elevation knots")
    if aod not in phase_b.AOD_KNOTS:
        raise TrainingExecutionRefusal("renderer restricted to frozen AOD knots")
    if not altitude > 0.0:
        raise TrainingExecutionRefusal("target must be above geometric horizon")
    try:
        grid = phase_a.elevated_site_grid_ascending(atmosphere_file, elevation)
    except Exception as exc:
        raise TrainingExecutionRefusal(str(exc)) from exc
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
        f"mol_abs_param {phase_a.MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {phase_b.WAVELENGTH_NM[0]} {phase_b.WAVELENGTH_NM[-1]}",
        f"sza {90.0 - altitude:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {phase_a.SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {aod:.8f}",
        "rte_solver sdisort",
        "sdisort nscat 1",
        "output_quantity transmittance",
        "output_user lambda edir",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    for forbidden in ("rte_solver mystic", "mc_", "aerosol_species_file", "angstrom", "nrefrac", "refraction", "altitude "):
        if forbidden in lower:
            raise TrainingExecutionRefusal(f"forbidden directive emitted: {forbidden}")
    return text


def parse_training_transmission(stdout_text: str, *, target_altitude_deg: float) -> dict[str, Any]:
    altitude = phase_b.finite("targetGeometricAltitudeDeg", target_altitude_deg)
    if altitude not in phase_b.TRAINING_ALTITUDE_DEG or not altitude > 0.0:
        raise TrainingExecutionRefusal("parser altitude outside frozen training universe")
    mu0 = math.sin(math.radians(altitude))
    if not math.isfinite(mu0) or not mu0 > 0.0:
        raise TrainingExecutionRefusal("mu0 must be finite and positive")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise TrainingExecutionRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = phase_b.finite("wavelength", parts[0])
        edir = phase_b.finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise TrainingExecutionRefusal("non-integral wavelength")
        if not math.isfinite(ray_t) or not 0.0 < ray_t <= 1.000001:
            raise TrainingExecutionRefusal(f"NUMERICALLY_UNRESOLVED direct transmission at {wavelength} nm")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(phase_b.WAVELENGTH_NM):
        raise TrainingExecutionRefusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    if any(not math.isfinite(v) or not 0.0 < v <= 1.0 for v in transmission):
        raise TrainingExecutionRefusal("NUMERICALLY_UNRESOLVED direct transmission spectrum")
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": [-math.log(v) for v in transmission],
        "targetGeometricAltitudeDeg": altitude,
        "sourceZenithAngleDeg": 90.0 - altitude,
        "mu0": mu0,
        "positiveEpsilonSubstitutionUsed": False,
    }


def execute_campaign(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, output_dir: Path,
                     allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise TrainingExecutionRefusal("scientific execution requires explicit allow_execution=True")
    if output_dir.exists():
        raise TrainingExecutionRefusal("output directory already exists; retry/resume forbidden")
    if not Path(uvspec).is_file():
        raise TrainingExecutionRefusal("uvspec executable not found")
    phase_b.validate_frozen_universe()
    cases = phase_b.build_training_cases()
    if len(cases) != EXPECTED_INVOCATIONS:
        raise TrainingExecutionRefusal("frozen training case count drift")
    output_dir.mkdir(parents=True)
    results: list[dict[str, Any]] = []
    invocation_count = 0
    for row in cases:
        case_id = training_case_id(row)
        case_dir = output_dir / case_id
        case_dir.mkdir()
        input_text = render_training_input(
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
        proc = subprocess.run([str(uvspec)], input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        stdout_path = case_dir / "uvspec.stdout"
        stderr_path = case_dir / "uvspec.stderr"
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            raise TrainingExecutionRefusal(f"terminal solver failure at {case_id}: exit {proc.returncode}")
        try:
            parsed = parse_training_transmission(proc.stdout, target_altitude_deg=row["targetGeometricAltitudeDeg"])
        except Exception as exc:
            raise TrainingExecutionRefusal(f"terminal parser/numerical refusal at {case_id}: {exc}") from exc
        result = {
            **row,
            "caseId": case_id,
            "status": "PASS",
            "solverExitCode": int(proc.returncode),
            "solverInvocationOrdinal": invocation_count,
            "inputSha256": sha256_file(input_path),
            "stdoutSha256": sha256_file(stdout_path),
            "stderrSha256": sha256_file(stderr_path),
            "wavelengthNm": parsed["wavelengthNm"],
            "directOpticalDepth": parsed["directOpticalDepth"],
            "minDirectTransmission": min(parsed["lineOfSightDirectTransmission"]),
            "maxDirectOpticalDepth": max(parsed["directOpticalDepth"]),
            "positiveEpsilonSubstitutionUsed": False,
            "sameIdentityRetryUsed": False,
        }
        (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results.append(result)
    if invocation_count != EXPECTED_INVOCATIONS or len(results) != EXPECTED_INVOCATIONS:
        raise TrainingExecutionRefusal("terminal training accounting drift")
    phase_b.validate_training_results(results)
    payload = {
        "schemaVersion": 1,
        "executionId": EXECUTION_ID,
        "scientificState": SCIENTIFIC_STATE,
        "phaseBFreezeIssue60CommentId": phase_b.PHASE_B_FREEZE_COMMENT_ID,
        "scientificSolverExecuted": True,
        "solver": "sdisort",
        "randomNumbersUsed": False,
        "solverInvocationCount": invocation_count,
        "expectedSolverInvocationCount": EXPECTED_INVOCATIONS,
        "executionComplete": True,
        "trainingOnly": True,
        "fiveDegreeSeamRegenerated": False,
        "protectedValidationOpened": False,
        "protectedSolverInvocationCount": 0,
        "githubRerunPermitted": False,
        "solverRetryPermitted": False,
        "solverResumePermitted": False,
        "positiveEpsilonSubstitutionUsed": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "cases": results,
    }
    out = output_dir / "phase-b-training-v1-result.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "executionId": EXECUTION_ID,
        "scientificState": SCIENTIFIC_STATE,
        "executionComplete": True,
        "solverInvocationCount": invocation_count,
        "resultSha256": sha256_file(out),
        "trainingOnly": True,
        "protectedValidationOpened": False,
        "productionAuthorized": False,
    }
    (output_dir / "execution-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
        parser.error("one-shot Phase-B training controller requires --execute --allow-execution")
    required = [args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file, args.output_dir]
    if any(v is None for v in required):
        parser.error("all execution paths required")
    payload = execute_campaign(
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        output_dir=args.output_dir,
        allow_execution=True,
    )
    print(json.dumps({"executionId": payload["executionId"], "solverInvocationCount": payload["solverInvocationCount"], "trainingOnly": True, "protectedValidationOpened": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
