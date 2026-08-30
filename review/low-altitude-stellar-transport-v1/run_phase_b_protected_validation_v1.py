#!/usr/bin/env python3
"""Frozen protected validator for LOWALT-STELLAR-STATE-0001.

The protected 176-spectrum / 528 Johnson-V matrix is inherited verbatim from
Issue #60 comment 5467228174. Import/review does not execute a solver. A future
one-shot dispatch must bind the exact reviewed training-candidate SHA before
--execute --allow-execution can be used. No retry/resume or floor back-selection
exists in this controller.
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
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b_protected_contract", PHASE_B_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load reviewed Phase-B contract")
phase_b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase_b)

STAGE_ID = "low-altitude-stellar-phase-b-protected-validation-v1"
SCIENTIFIC_STATE = phase_b.SCIENTIFIC_STATE
SOURCE_SED_SHA256 = "85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb"
SOURCE_JOHNSON_V_SHA256 = "51c357eb4cb3609361759f9750ad13ae13a901970913e3a5d87bb5c45ee2db9a"
EXACT_PACKAGE_SPEC = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
SURFACE_ALBEDO = 0.15


class ProtectedValidationRefusal(RuntimeError):
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
        raise ProtectedValidationRefusal(f"{name} must be finite")
    return number


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ProtectedValidationRefusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", parts[0]))
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise ProtectedValidationRefusal("AFGLUS atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if not phase_b.ELEVATION_KNOTS_M[0] <= elevation <= phase_b.ELEVATION_KNOTS_M[-1]:
        raise ProtectedValidationRefusal("observer elevation outside frozen domain")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise ProtectedValidationRefusal("site elevation outside AFGLUS grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise ProtectedValidationRefusal("atm_z_grid must be strictly ascending")
    return grid


def protected_keys() -> set[tuple[float, float, float]]:
    return {
        phase_b.coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"])
        for row in phase_b.build_protected_cases()
    }


def render_protected_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                           target_geometric_altitude_deg: float, observer_elevation_m: float,
                           aod550: float) -> str:
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    e = finite("observerElevationM", observer_elevation_m)
    a = finite("aod550", aod550)
    if phase_b.coord(h, e, a) not in protected_keys():
        raise ProtectedValidationRefusal("renderer restricted to frozen protected coordinate universe")
    if not 0.0 < h < 5.0:
        raise ProtectedValidationRefusal("protected target must be strictly above the geometric horizon and below 5deg")
    grid = elevated_site_grid_ascending(atmosphere_file, e)
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
        "mol_abs_param crs",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {phase_b.WAVELENGTH_NM[0]} {phase_b.WAVELENGTH_NM[-1]}",
        f"sza {90.0 - h:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {a:.8f}",
        "rte_solver sdisort",
        "sdisort nscat 1",
        "output_quantity transmittance",
        "output_user lambda edir",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    for forbidden in ("rte_solver mystic", "mc_", "nrefrac", "refraction", "aerosol_species_file", "angstrom"):
        if forbidden in lower:
            raise ProtectedValidationRefusal(f"forbidden directive emitted: {forbidden}")
    return text


def parse_protected_transmission(stdout_text: str, *, target_geometric_altitude_deg: float) -> dict[str, Any]:
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    if h not in phase_b.PROTECTED_ALTITUDE_DEG:
        raise ProtectedValidationRefusal("parser altitude is not a frozen protected altitude")
    mu0 = math.sin(math.radians(h))
    if not math.isfinite(mu0) or not mu0 > 0.0:
        raise ProtectedValidationRefusal("protected mu0 must be finite and positive")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ProtectedValidationRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise ProtectedValidationRefusal("non-integral wavelength in exact 1-nm output")
        if not math.isfinite(ray_t) or not 0.0 < ray_t <= 1.000001:
            raise ProtectedValidationRefusal(f"NUMERICALLY_UNRESOLVED direct transmission at {wavelength} nm")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(phase_b.WAVELENGTH_NM):
        raise ProtectedValidationRefusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    tau = [-math.log(value) for value in transmission]
    for value in tau:
        reconstructed = math.exp(-value)
        if value < 0.0 or not math.isfinite(value) or not math.isfinite(reconstructed) or not 0.0 < reconstructed <= 1.0:
            raise ProtectedValidationRefusal("protected optical depth cannot be represented without underflow")
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": tau,
        "targetGeometricAltitudeDeg": h,
        "sourceZenithAngleDeg": 90.0 - h,
        "mu0": mu0,
        "positiveEpsilonSubstitutionUsed": False,
    }


def validate_candidate(runtime: dict[str, Any]) -> None:
    phase_b.validate_lower_runtime(runtime)
    if runtime.get("scientificState") != SCIENTIFIC_STATE:
        raise ProtectedValidationRefusal("candidate scientific-state mismatch")
    provenance = runtime.get("provenance") or {}
    if provenance.get("trainingExecutionId") != "low-altitude-stellar-phase-b-training-v1-exec001":
        raise ProtectedValidationRefusal("candidate training identity mismatch")
    if provenance.get("protectedValidationOpened") is not False:
        raise ProtectedValidationRefusal("candidate already claims protected validation opening")
    if provenance.get("scientificallyValidatedBelow5Deg") is not False:
        raise ProtectedValidationRefusal("candidate already claims scientific validation below 5deg")
    routing = runtime.get("routing") or {}
    if routing.get("lowerProviderMinInclusiveDeg") != 0.25 or routing.get("lowerProviderMaxExclusiveDeg") != 5.0:
        raise ProtectedValidationRefusal("candidate routing boundary drift")
    if routing.get("exactFiveAndAboveProvider") != "authoritative-v3.2" or routing.get("exactHorizonSupported") is not False:
        raise ProtectedValidationRefusal("candidate seam/horizon claim drift")


def _load_photometry(root: Path):
    path = root / "review/asiv-matched-stellar-transport-v1/assemble_validate_matched_stellar_v1.py"
    spec = importlib.util.spec_from_file_location("low_altitude_protected_photometry", path)
    if spec is None or spec.loader is None:
        raise ProtectedValidationRefusal("cannot load frozen stellar photometry helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_complete_protected_results(*, root: Path, candidate_runtime: dict[str, Any],
                                        protected_results: dict[tuple[float, float, float], dict[str, Any]],
                                        sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    validate_candidate(candidate_runtime)
    expected = protected_keys()
    if set(protected_results) != expected:
        raise ProtectedValidationRefusal("protected result universe incomplete or drifted")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise ProtectedValidationRefusal("frozen Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ProtectedValidationRefusal("frozen Johnson-V asset SHA-256 drift")
    phot = _load_photometry(root)
    _, wavelength_nm, band_response, representatives = phot.load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path
    )
    reps = [row for row in representatives if int(row["libraryNumber"]) in phase_b.REPRESENTATIVE_LIBRARY_NUMBERS]
    if [int(row["libraryNumber"]) for row in reps] != list(phase_b.REPRESENTATIVE_LIBRARY_NUMBERS):
        raise ProtectedValidationRefusal("representative Pickles template identity drift")
    delta_rows: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for row in phase_b.build_protected_cases():
        h = row["targetGeometricAltitudeDeg"]
        e = row["observerElevationM"]
        a = row["aod550"]
        key = phase_b.coord(h, e, a)
        ref = protected_results[key]
        if ref.get("status") != "PASS":
            raise ProtectedValidationRefusal("non-PASS protected spectrum in complete evaluator")
        predicted_tau = phase_b.interpolate_lower_tau(candidate_runtime, h, e, a)
        predicted_t = [math.exp(-tau) for tau in predicted_tau]
        reference_t = [finite("reference transmission", x) for x in ref["lineOfSightDirectTransmission"]]
        comparisons = []
        for sed in reps:
            flux = [float(x) for x in sed["fluxRelative"]]
            runtime_av = phot.band_extinction_mag(
                wavelength_nm=wavelength_nm, flux_relative=flux,
                band_response=band_response, transmission=predicted_t,
            )
            reference_av = phot.band_extinction_mag(
                wavelength_nm=wavelength_nm, flux_relative=flux,
                band_response=band_response, transmission=reference_t,
            )
            delta = runtime_av - reference_av
            comparison = {
                "targetGeometricAltitudeDeg": h,
                "observerElevationM": e,
                "aod550": a,
                "libraryNumber": int(sed["libraryNumber"]),
                "runtimeAvMag": runtime_av,
                "referenceAvMag": reference_av,
                "deltaAvMag": delta,
            }
            delta_rows.append(comparison)
            comparisons.append(comparison)
        cases.append({**row, "sedComparisons": comparisons})
    metrics = phase_b.evaluate_protected_deltas(delta_rows)
    passed = metrics["status"] == "PROTECTED_VALIDATION_PASS"
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "scientificState": SCIENTIFIC_STATE,
        "status": metrics["status"],
        "freshProtectedAtmosphericSpectrumCount": phase_b.EXPECTED_PROTECTED_SPECTRA,
        "freshProtectedJohnsonVComparisonCount": phase_b.EXPECTED_PROTECTED_COMPARISONS,
        "representativeLibraryNumbers": list(phase_b.REPRESENTATIVE_LIBRARY_NUMBERS),
        "overall": metrics["overall"],
        "byProtectedAltitudeDeg": metrics["byProtectedAltitudeDeg"],
        "minimumSupportedGeometricAltitudeIfPassDeg": 0.25 if passed else None,
        "exactHorizonSupported": False,
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "cases": cases,
    }


def execute_campaign(*, root: Path, candidate_runtime_path: Path, expected_candidate_sha256: str,
                     uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, sed_bundle_path: Path, johnson_v_path: Path,
                     output_dir: Path, allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise ProtectedValidationRefusal("protected solver execution requires explicit allow_execution=True")
    if output_dir.exists():
        raise ProtectedValidationRefusal("output directory already exists; retry/resume is forbidden")
    phase_b.validate_frozen_universe()
    if sha256_file(candidate_runtime_path) != str(expected_candidate_sha256):
        raise ProtectedValidationRefusal("candidate runtime SHA-256 mismatch")
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise ProtectedValidationRefusal("uvspec SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ProtectedValidationRefusal("AFGLUS SHA-256 drift")
    grid_values = [int(line) for line in wavelength_grid_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if grid_values != list(phase_b.WAVELENGTH_NM):
        raise ProtectedValidationRefusal("wavelength-grid file drift")
    candidate = json.loads(candidate_runtime_path.read_text(encoding="utf-8"))
    validate_candidate(candidate)
    output_dir.mkdir(parents=True)
    results: dict[tuple[float, float, float], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    invocation_count = 0
    for row in phase_b.build_protected_cases():
        key = phase_b.coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"])
        cid = f"h{key[0]:.5f}_e{key[1]:.5f}_a{key[2]:.6f}".replace(".", "p")
        case_dir = output_dir / cid
        case_dir.mkdir()
        input_text = render_protected_input(
            data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            target_geometric_altitude_deg=row["targetGeometricAltitudeDeg"],
            observer_elevation_m=row["observerElevationM"], aod550=row["aod550"],
        )
        (case_dir / "uvspec.inp").write_text(input_text, encoding="utf-8")
        invocation_count += 1
        proc = subprocess.run([str(uvspec)], input=input_text, text=True, capture_output=True, check=False)
        (case_dir / "uvspec.stdout").write_text(proc.stdout, encoding="utf-8")
        (case_dir / "uvspec.stderr").write_text(proc.stderr, encoding="utf-8")
        parsed = None
        refusal = None
        if proc.returncode == 0:
            try:
                parsed = parse_protected_transmission(proc.stdout, target_geometric_altitude_deg=row["targetGeometricAltitudeDeg"])
                status = "PASS"
            except Exception as exc:
                status = "NUMERICALLY_UNRESOLVED"
                refusal = f"{type(exc).__name__}: {exc}"
        else:
            status = "NUMERICALLY_UNRESOLVED"
            refusal = f"uvspec_exit_{proc.returncode}"
        result = {
            **row,
            "caseId": cid,
            "status": status,
            "solverExitCode": int(proc.returncode),
            "parserRefusal": refusal,
            "solverInvocationOrdinal": invocation_count,
            "sameIdentityRetryUsed": False,
            "positiveEpsilonSubstitutionUsed": False,
            "refractionAppliedInRadiativeTransfer": False,
        }
        if parsed is not None:
            result.update(parsed)
        (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results[key] = result
        rows.append(result)
    if invocation_count != phase_b.EXPECTED_PROTECTED_SPECTRA:
        raise ProtectedValidationRefusal("protected solver invocation count drift")
    unresolved = [row["caseId"] for row in rows if row["status"] != "PASS"]
    if unresolved:
        validation = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "scientificState": SCIENTIFIC_STATE,
            "status": "PROTECTED_VALIDATION_FAIL_NUMERICALLY_UNRESOLVED",
            "freshProtectedAtmosphericSpectrumCount": phase_b.EXPECTED_PROTECTED_SPECTRA,
            "freshProtectedJohnsonVComparisonCount": 0,
            "numericallyUnresolvedSpectrumCount": len(unresolved),
            "numericallyUnresolvedCaseIds": unresolved,
            "minimumSupportedGeometricAltitudeIfPassDeg": None,
            "exactHorizonSupported": False,
            "postResultFloorBackSelectionAuthorized": False,
            "postResultRetuningAuthorized": False,
            "productionAuthorized": False,
            "applicationSupportChanged": False,
        }
    else:
        validation = evaluate_complete_protected_results(
            root=root, candidate_runtime=candidate, protected_results=results,
            sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path,
        )
    validation.update({
        "candidateRuntimeSha256": str(expected_candidate_sha256),
        "scientificSolverExecuted": True,
        "solver": "sdisort",
        "solverGeometry": "pseudo-spherical",
        "solverInvocationCount": invocation_count,
        "randomNumbersUsed": False,
        "positiveEpsilonSubstitutionUsed": False,
        "sameIdentityRetryUsed": False,
    })
    out = output_dir / "low-altitude-stellar-phase-b-protected-validation-v1.json"
    out.write_text(json.dumps(validation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return validation


def review_ledger() -> dict[str, Any]:
    phase_b.validate_frozen_universe()
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "scientificState": SCIENTIFIC_STATE,
        "phaseBFreezeIssue60CommentId": phase_b.PHASE_B_FREEZE_COMMENT_ID,
        "protectedAltitudeDeg": list(phase_b.PROTECTED_ALTITUDE_DEG),
        "protectedElevationM": list(phase_b.PROTECTED_ELEVATION_M),
        "protectedAod550": list(phase_b.PROTECTED_AOD550),
        "protectedAtmosphericSpectrumCount": phase_b.EXPECTED_PROTECTED_SPECTRA,
        "protectedJohnsonVComparisonCount": phase_b.EXPECTED_PROTECTED_COMPARISONS,
        "representativeLibraryNumbers": list(phase_b.REPRESENTATIVE_LIBRARY_NUMBERS),
        "maxAbsDeltaAvMagLimit": phase_b.MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": phase_b.RMS_ERROR_MAG_LIMIT,
        "globalAndEveryAltitudeIntervalMustPass": True,
        "candidateShaMustBeBoundBeforeExecution": True,
        "exactHorizonIncluded": False,
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "githubRerunPermitted": False,
        "solverRetryPermitted": False,
        "solverResumePermitted": False,
        "positiveEpsilonSubstitutionAllowed": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "scientificExecutionAuthorizedByModule": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-ledger", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--candidate-runtime", type=Path)
    parser.add_argument("--expected-candidate-sha256")
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.emit_ledger:
        if args.execute or args.allow_execution:
            parser.error("--emit-ledger cannot be combined with execution")
        print(json.dumps(review_ledger(), indent=2, sort_keys=True))
        return 0
    if not (args.execute and args.allow_execution):
        parser.error("protected validation requires --execute --allow-execution")
    required = [args.candidate_runtime, args.expected_candidate_sha256, args.uvspec, args.data_dir,
                args.atmosphere_file, args.wavelength_grid_file, args.sed_bundle, args.johnson_v, args.output_dir]
    if any(value is None for value in required):
        parser.error("all protected execution bindings are required")
    result = execute_campaign(
        root=args.root, candidate_runtime_path=args.candidate_runtime,
        expected_candidate_sha256=args.expected_candidate_sha256,
        uvspec=args.uvspec, data_dir=args.data_dir, atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file, sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v, output_dir=args.output_dir,
        allow_execution=True,
    )
    print(json.dumps({
        "status": result["status"],
        "solverInvocationCount": result["solverInvocationCount"],
        "minimumSupportedGeometricAltitudeIfPassDeg": result.get("minimumSupportedGeometricAltitudeIfPassDeg"),
        "exactHorizonSupported": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
