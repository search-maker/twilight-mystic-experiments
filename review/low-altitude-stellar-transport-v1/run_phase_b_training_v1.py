#!/usr/bin/env python3
"""Fresh deterministic Phase-B training controller for LOWALT-STELLAR-STATE-0001.

This executable is restricted to the 275 preregistered *training* spectra below
5 degrees. It cannot build or execute the protected 176-spectrum validation
matrix. Execution requires a separately reviewed one-shot workflow plus an
explicit --execute --allow-execution gate. No retry/resume path exists.
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
PHASE_B_PATH = HERE / "low_altitude_phase_b.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b_training_contract", PHASE_B_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load reviewed Phase-B contract")
phase_b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase_b)

EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec001"
SCIENTIFIC_STATE = phase_b.SCIENTIFIC_STATE
EXPECTED_INVOCATIONS = phase_b.EXPECTED_TRAINING_SPECTRA
EXACT_PACKAGE_SPEC = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
UVSPEC_HELP_SHA256 = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
MOL_ABS_PARAM = "crs"
SURFACE_ALBEDO = 0.15


class TrainingExecutionRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise TrainingExecutionRefusal(f"{name} must be finite")
    return number


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise TrainingExecutionRefusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", parts[0]))
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise TrainingExecutionRefusal("AFGLUS atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if elevation not in phase_b.ELEVATION_KNOTS_M:
        raise TrainingExecutionRefusal("observer elevation is not a frozen Phase-B training knot")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise TrainingExecutionRefusal("site elevation outside AFGLUS grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise TrainingExecutionRefusal("atm_z_grid must be strictly ascending")
    return grid


def render_training_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                          target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> str:
    altitude = finite("targetGeometricAltitudeDeg", target_altitude_deg)
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    if altitude not in phase_b.TRAINING_ALTITUDE_DEG:
        raise TrainingExecutionRefusal("renderer restricted to frozen Phase-B training altitudes")
    if elevation not in phase_b.ELEVATION_KNOTS_M:
        raise TrainingExecutionRefusal("renderer restricted to frozen elevation knots")
    if aod not in phase_b.AOD_KNOTS:
        raise TrainingExecutionRefusal("renderer restricted to frozen AOD knots")
    if not 0.0 < altitude < 5.0:
        raise TrainingExecutionRefusal("training target must be strictly inside (0,5) geometric degrees")
    grid = elevated_site_grid_ascending(atmosphere_file, elevation)
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
        f"mol_abs_param {MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {phase_b.WAVELENGTH_NM[0]} {phase_b.WAVELENGTH_NM[-1]}",
        f"sza {90.0 - altitude:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {SURFACE_ALBEDO:.8f}",
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
    for forbidden in (
        "rte_solver mystic", "mc_", "aerosol_species_file", "angstrom",
        "nrefrac", "refraction", "altitude ",
    ):
        if forbidden in lower:
            raise TrainingExecutionRefusal(f"forbidden directive emitted: {forbidden}")
    if text.count("rte_solver sdisort") != 1 or text.count("sdisort nscat 1") != 1:
        raise TrainingExecutionRefusal("pseudo-spherical deterministic solver surface drift")
    if text.count("aerosol_default") != 1 or text.count("aerosol_set_tau_at_wvl") != 1:
        raise TrainingExecutionRefusal("aerosol directive surface drift")
    return text


def parse_training_transmission(stdout_text: str, *, target_altitude_deg: float) -> dict[str, Any]:
    altitude = finite("targetGeometricAltitudeDeg", target_altitude_deg)
    if altitude not in phase_b.TRAINING_ALTITUDE_DEG or not 0.0 < altitude < 5.0:
        raise TrainingExecutionRefusal("parser altitude outside frozen Phase-B training universe")
    mu0 = math.sin(math.radians(altitude))
    if not math.isfinite(mu0) or not mu0 > 0.0:
        raise TrainingExecutionRefusal("mu0 must be finite and strictly positive")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise TrainingExecutionRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise TrainingExecutionRefusal("non-integral wavelength in exact 1-nm output")
        if not math.isfinite(ray_t) or not 0.0 < ray_t <= 1.000001:
            raise TrainingExecutionRefusal(f"NUMERICALLY_UNRESOLVED direct transmission at {wavelength} nm")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(phase_b.WAVELENGTH_NM):
        raise TrainingExecutionRefusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    if any(not math.isfinite(value) or not 0.0 < value <= 1.0 for value in transmission):
        raise TrainingExecutionRefusal("NUMERICALLY_UNRESOLVED direct transmission spectrum")
    tau = [-math.log(value) for value in transmission]
    for optical_depth in tau:
        reconstructed = math.exp(-optical_depth)
        if optical_depth < 0.0 or not math.isfinite(optical_depth) or not math.isfinite(reconstructed) or not 0.0 < reconstructed <= 1.0:
            raise TrainingExecutionRefusal("direct optical depth cannot be represented without underflow")
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": tau,
        "targetGeometricAltitudeDeg": altitude,
        "sourceZenithAngleDeg": 90.0 - altitude,
        "mu0": mu0,
        "positiveEpsilonSubstitutionUsed": False,
    }


def training_case_id(row: dict[str, Any]) -> str:
    return (
        f"h{float(row['targetGeometricAltitudeDeg']):.5f}"
        f"_e{float(row['observerElevationM']):.2f}"
        f"_a{float(row['aod550']):.5f}"
    ).replace(".", "p")


def review_ledger() -> dict[str, Any]:
    phase_b.validate_frozen_universe()
    cases = phase_b.build_training_cases()
    return {
        "schemaVersion": 1,
        "executionId": EXECUTION_ID,
        "scientificState": SCIENTIFIC_STATE,
        "phaseBFreezeIssue60CommentId": phase_b.PHASE_B_FREEZE_COMMENT_ID,
        "trainingSpectrumCount": len(cases),
        "protectedSpectrumCountExecuted": 0,
        "protectedResultsOpened": False,
        "solver": "sdisort",
        "solverGeometry": "pseudo-spherical",
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "sourceZenithAngleRule": "90deg-targetGeometricAltitudeDeg",
        "refractionAppliedInRadiativeTransfer": False,
        "randomNumbersUsed": False,
        "sameIdentityRetryAllowed": False,
        "solverResumeAllowed": False,
        "positiveEpsilonSubstitutionAllowed": False,
        "exactHorizonIncluded": False,
        "productionAuthorized": False,
        "trainingAltitudesDeg": list(phase_b.TRAINING_ALTITUDE_DEG),
        "observerElevationM": list(phase_b.ELEVATION_KNOTS_M),
        "aod550": list(phase_b.AOD_KNOTS),
        "wavelengthNm": [phase_b.WAVELENGTH_NM[0], phase_b.WAVELENGTH_NM[-1], 1],
        "exactPackageSpec": EXACT_PACKAGE_SPEC,
        "uvspecSha256": UVSPEC_SHA256,
        "uvspecHelpSha256": UVSPEC_HELP_SHA256,
        "afglusSha256": AFGLUS_SHA256,
        "scientificExecutionAuthorizedByModule": False,
    }


def execute_campaign(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, output_dir: Path,
                     allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise TrainingExecutionRefusal("scientific execution requires explicit allow_execution=True")
    if output_dir.exists():
        raise TrainingExecutionRefusal("output directory already exists; retry/resume is forbidden")
    if not Path(uvspec).is_file():
        raise TrainingExecutionRefusal("uvspec executable not found")
    phase_b.validate_frozen_universe()
    cases = phase_b.build_training_cases()
    if len(cases) != EXPECTED_INVOCATIONS:
        raise TrainingExecutionRefusal("frozen Phase-B training case count drift")
    output_dir.mkdir(parents=True)

    results: list[dict[str, Any]] = []
    invocation_count = 0
    for row in cases:
        cid = training_case_id(row)
        case_dir = output_dir / cid
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
        proc = subprocess.run(
            [str(uvspec)], input=input_text, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        stdout_path = case_dir / "uvspec.stdout"
        stderr_path = case_dir / "uvspec.stderr"
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        parsed = None
        refusal = None
        if proc.returncode == 0:
            try:
                parsed = parse_training_transmission(
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
        result: dict[str, Any] = {
            **row,
            "caseId": cid,
            "status": status,
            "solver": "sdisort",
            "solverGeometry": "pseudo-spherical",
            "solverExitCode": int(proc.returncode),
            "parserRefusal": refusal,
            "inputSha256": sha256_file(input_path),
            "stdoutSha256": sha256_file(stdout_path),
            "stderrSha256": sha256_file(stderr_path),
            "solverInvocationOrdinal": invocation_count,
            "sameIdentityRetryUsed": False,
            "positiveEpsilonSubstitutionUsed": False,
            "refractionAppliedInRadiativeTransfer": False,
        }
        if parsed is not None:
            result.update(parsed)
            result["minDirectTransmission"] = min(parsed["lineOfSightDirectTransmission"])
            result["maxDirectOpticalDepth"] = max(parsed["directOpticalDepth"])
        (case_dir / "case-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        results.append(result)

    if invocation_count != EXPECTED_INVOCATIONS:
        raise TrainingExecutionRefusal("solver invocation count drift")
    pass_count = sum(row["status"] == "PASS" for row in results)
    unresolved = [row["caseId"] for row in results if row["status"] != "PASS"]
    if pass_count == EXPECTED_INVOCATIONS:
        phase_b.validate_training_results(results)
    payload = {
        "schemaVersion": 1,
        "executionId": EXECUTION_ID,
        "scientificState": SCIENTIFIC_STATE,
        "phaseBFreezeIssue60CommentId": phase_b.PHASE_B_FREEZE_COMMENT_ID,
        "scientificSolverExecuted": True,
        "solver": "sdisort",
        "solverGeometry": "pseudo-spherical",
        "randomNumbersUsed": False,
        "solverInvocationCount": invocation_count,
        "expectedSolverInvocationCount": EXPECTED_INVOCATIONS,
        "executionComplete": len(results) == EXPECTED_INVOCATIONS,
        "trainingScientificallyEligible": pass_count == EXPECTED_INVOCATIONS,
        "passingTrainingSpectrumCount": pass_count,
        "numericallyUnresolvedTrainingSpectrumCount": len(unresolved),
        "numericallyUnresolvedCaseIds": unresolved,
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
    (output_dir / "execution-receipt.json").write_text(
        json.dumps({
            "executionId": EXECUTION_ID,
            "scientificState": SCIENTIFIC_STATE,
            "executionComplete": payload["executionComplete"],
            "trainingScientificallyEligible": payload["trainingScientificallyEligible"],
            "solverInvocationCount": invocation_count,
            "passingTrainingSpectrumCount": pass_count,
            "numericallyUnresolvedTrainingSpectrumCount": len(unresolved),
            "resultSha256": sha256_file(out),
            "trainingOnly": True,
            "protectedValidationOpened": False,
            "productionAuthorized": False,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-ledger", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.emit_ledger:
        if args.execute or args.allow_execution:
            parser.error("--emit-ledger cannot be combined with execution")
        print(json.dumps(review_ledger(), indent=2, sort_keys=True))
        return 0
    if not (args.execute and args.allow_execution):
        parser.error("one-shot Phase-B training controller requires --execute --allow-execution")
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
        "trainingScientificallyEligible": payload["trainingScientificallyEligible"],
        "solverInvocationCount": payload["solverInvocationCount"],
        "numericallyUnresolvedTrainingSpectrumCount": payload["numericallyUnresolvedTrainingSpectrumCount"],
        "protectedValidationOpened": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
