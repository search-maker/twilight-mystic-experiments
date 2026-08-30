#!/usr/bin/env python3
"""Frozen fresh protected-v2 validator for LOWALT-STELLAR-STATE-0001.

This controller consumes only the admissible exec003 candidate and the wholly
fresh cell-center protected-v2 protocol. Import/review executes no solver.
Execution is fail-closed, one-shot by external workflow identity, uses exact
pseudo-spherical sdisort direct transport, never substitutes epsilon, and never
back-selects a support floor from protected results.
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
ROOT = HERE.parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phase_b = _load("low_altitude_phase_b_for_protected_v2", HERE / "low_altitude_phase_b.py")
fresh = _load("low_altitude_fresh_protected_v2", HERE / "protected_v2_fresh_matrix.py")

STAGE_ID = "low-altitude-stellar-protected-v2-validation-v1"
SCIENTIFIC_STATE = phase_b.SCIENTIFIC_STATE
PROTOCOL_ID = fresh.PROTOCOL_ID
EXPECTED_TRAINING_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec003"
EXPECTED_CANDIDATE_ASSEMBLY_ID = "low-altitude-stellar-phase-b-training-candidate-v1-exec003"
EXPECTED_CANDIDATE_RUNTIME_SHA256 = "4730c4404ef4ee93c07930f5fe8eb391f117cdc84f2c9eff49c5e7ee9f73b72e"
EXPECTED_CANDIDATE_SOURCE_RUN_ID = 33313239384
EXPECTED_CANDIDATE_SOURCE_JOB_ID = 99261929321
EXPECTED_CANDIDATE_ARTIFACT_ID = 9732635873
EXPECTED_CANDIDATE_ARTIFACT_DIGEST = "sha256:f5049c22d5c4c793e4ee789b3e0e050969b132aeac714c8ccf17d7de264dbeec"
EXPECTED_CANDIDATE_SOURCE_DISPATCH_SHA = "c723e3c4cf780d68148b8b9297e486596e33d6a5"
SOURCE_SED_SHA256 = "85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb"
SOURCE_JOHNSON_V_SHA256 = "51c357eb4cb3609361759f9750ad13ae13a901970913e3a5d87bb5c45ee2db9a"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5d3e5d2d53393c1462a0c3a528bc5e3f5935191cfb5"
# Correct frozen AFGLUS hash below; the deliberately separate constant makes
# accidental edits easy to catch in review.
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
SURFACE_ALBEDO = 0.15


class ProtectedV2Refusal(RuntimeError):
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
        raise ProtectedV2Refusal(f"{name} must be finite")
    return number


def protected_keys() -> set[tuple[float, float, float]]:
    fresh.validate_protocol()
    return {
        phase_b.coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
        for r in fresh.build_protected_cases()
    }


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ProtectedV2Refusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", parts[0]))
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise ProtectedV2Refusal("AFGLUS atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if not phase_b.ELEVATION_KNOTS_M[0] <= elevation <= phase_b.ELEVATION_KNOTS_M[-1]:
        raise ProtectedV2Refusal("observer elevation outside frozen domain")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise ProtectedV2Refusal("site elevation outside AFGLUS grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise ProtectedV2Refusal("atm_z_grid must be strictly ascending")
    return grid


def render_protected_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                           target_geometric_altitude_deg: float, observer_elevation_m: float,
                           aod550: float) -> str:
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    e = finite("observerElevationM", observer_elevation_m)
    a = finite("aod550", aod550)
    if phase_b.coord(h, e, a) not in protected_keys():
        raise ProtectedV2Refusal("renderer restricted to fresh protected-v2 universe")
    if not 0.0 < h < 5.0:
        raise ProtectedV2Refusal("protected target must be strictly above geometric horizon and below 5deg")
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
            raise ProtectedV2Refusal(f"forbidden directive emitted: {forbidden}")
    return text


def parse_protected_transmission(stdout_text: str, *, target_geometric_altitude_deg: float) -> dict[str, Any]:
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    if h not in fresh.PROTECTED_ALTITUDE_DEG:
        raise ProtectedV2Refusal("parser altitude is not a fresh protected-v2 altitude")
    mu0 = math.sin(math.radians(h))
    if not math.isfinite(mu0) or mu0 <= 0.0:
        raise ProtectedV2Refusal("protected mu0 must be finite and positive")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ProtectedV2Refusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise ProtectedV2Refusal("non-integral wavelength in exact 1-nm output")
        if not math.isfinite(ray_t) or not 0.0 < ray_t <= 1.000001:
            raise ProtectedV2Refusal(f"NUMERICALLY_UNRESOLVED direct transmission at {wavelength} nm")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(phase_b.WAVELENGTH_NM):
        raise ProtectedV2Refusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    tau = [-math.log(value) for value in transmission]
    for value in tau:
        reconstructed = math.exp(-value)
        if value < 0.0 or not math.isfinite(value) or not 0.0 < reconstructed <= 1.0:
            raise ProtectedV2Refusal("protected optical depth cannot be represented without underflow")
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
        raise ProtectedV2Refusal("candidate scientific-state mismatch")
    provenance = runtime.get("provenance") or {}
    if provenance.get("trainingExecutionId") != EXPECTED_TRAINING_EXECUTION_ID:
        raise ProtectedV2Refusal("candidate training identity mismatch")
    if provenance.get("assemblyId") not in (None, EXPECTED_CANDIDATE_ASSEMBLY_ID):
        raise ProtectedV2Refusal("candidate assembly identity mismatch")
    if provenance.get("protectedValidationOpened") is not False:
        raise ProtectedV2Refusal("candidate already claims protected validation opening")
    if provenance.get("scientificallyValidatedBelow5Deg") is not False:
        raise ProtectedV2Refusal("candidate already claims validation below 5deg")
    routing = runtime.get("routing") or {}
    if routing.get("lowerProviderMinInclusiveDeg") != 0.25 or routing.get("lowerProviderMaxExclusiveDeg") != 5.0:
        raise ProtectedV2Refusal("candidate routing boundary drift")
    if routing.get("exactFiveAndAboveProvider") != "authoritative-v3.2":
        raise ProtectedV2Refusal("5deg seam provider drift")
    if routing.get("exactHorizonSupported") is not False:
        raise ProtectedV2Refusal("exact horizon must remain unsupported")


def _load_photometry(root: Path):
    return _load("low_altitude_protected_v2_photometry", root / "review/asiv-matched-stellar-transport-v1/assemble_validate_matched_stellar_v1.py")


def evaluate_complete_results(*, root: Path, candidate_runtime: dict[str, Any],
                              protected_results: dict[tuple[float, float, float], dict[str, Any]],
                              sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    validate_candidate(candidate_runtime)
    if set(protected_results) != protected_keys():
        raise ProtectedV2Refusal("protected-v2 result universe incomplete or drifted")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise ProtectedV2Refusal("frozen Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ProtectedV2Refusal("frozen Johnson-V asset SHA-256 drift")
    phot = _load_photometry(root)
    _, wavelength_nm, band_response, representatives = phot.load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path
    )
    reps = [r for r in representatives if int(r["libraryNumber"]) in fresh.REPRESENTATIVE_LIBRARY_NUMBERS]
    if [int(r["libraryNumber"]) for r in reps] != list(fresh.REPRESENTATIVE_LIBRARY_NUMBERS):
        raise ProtectedV2Refusal("representative Pickles identity drift")
    deltas: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for row in fresh.build_protected_cases():
        h, e, a = row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"]
        ref = protected_results[phase_b.coord(h, e, a)]
        if ref.get("status") != "PASS":
            raise ProtectedV2Refusal("non-PASS spectrum reached evaluator")
        predicted_t = [math.exp(-tau) for tau in phase_b.interpolate_lower_tau(candidate_runtime, h, e, a)]
        reference_t = [finite("reference transmission", x) for x in ref["lineOfSightDirectTransmission"]]
        comparisons = []
        for sed in reps:
            flux = [float(x) for x in sed["fluxRelative"]]
            runtime_av = phot.band_extinction_mag(wavelength_nm=wavelength_nm, flux_relative=flux, band_response=band_response, transmission=predicted_t)
            reference_av = phot.band_extinction_mag(wavelength_nm=wavelength_nm, flux_relative=flux, band_response=band_response, transmission=reference_t)
            item = {**row, "libraryNumber": int(sed["libraryNumber"]), "runtimeAvMag": runtime_av,
                    "referenceAvMag": reference_av, "deltaAvMag": runtime_av - reference_av}
            deltas.append(item)
            comparisons.append(item)
        cases.append({**row, "sedComparisons": comparisons})
    metrics = fresh.evaluate_deltas(deltas)
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "protocolId": PROTOCOL_ID,
        "scientificState": SCIENTIFIC_STATE,
        "status": metrics["status"],
        "freshProtectedAtmosphericSpectrumCount": fresh.EXPECTED_PROTECTED_SPECTRA,
        "freshProtectedJohnsonVComparisonCount": fresh.EXPECTED_PROTECTED_COMPARISONS,
        "representativeLibraryNumbers": list(fresh.REPRESENTATIVE_LIBRARY_NUMBERS),
        "overall": metrics["overall"],
        "byProtectedAltitudeDeg": metrics["byProtectedAltitudeDeg"],
        "minimumSupportedGeometricAltitudeIfPassDeg": metrics["minimumSupportedGeometricAltitudeIfPassDeg"],
        "exactHorizonSupported": False,
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "cases": cases,
    }


def execute_campaign(*, root: Path, candidate_runtime_path: Path, expected_candidate_sha256: str,
                     uvspec: Path, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                     sed_bundle_path: Path, johnson_v_path: Path, output_dir: Path,
                     allow_execution: bool) -> dict[str, Any]:
    if allow_execution is not True:
        raise ProtectedV2Refusal("protected solver execution requires explicit allow_execution=True")
    if output_dir.exists():
        raise ProtectedV2Refusal("output directory already exists; retry/resume forbidden")
    fresh.validate_protocol()
    if expected_candidate_sha256 != EXPECTED_CANDIDATE_RUNTIME_SHA256:
        raise ProtectedV2Refusal("controller is bound to the exact admissible exec003 candidate SHA")
    if sha256_file(candidate_runtime_path) != EXPECTED_CANDIDATE_RUNTIME_SHA256:
        raise ProtectedV2Refusal("candidate runtime SHA-256 mismatch")
    if sha256_file(uvspec) != UVSPEC_SHA256 or sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ProtectedV2Refusal("pinned solver or AFGLUS input drift")
    grid_values = [int(x) for x in wavelength_grid_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    if grid_values != list(phase_b.WAVELENGTH_NM):
        raise ProtectedV2Refusal("wavelength grid drift")
    candidate = json.loads(candidate_runtime_path.read_text(encoding="utf-8"))
    validate_candidate(candidate)
    output_dir.mkdir(parents=True)
    results: dict[tuple[float, float, float], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for ordinal, row in enumerate(fresh.build_protected_cases(), start=1):
        h, e, a = row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"]
        key = phase_b.coord(h, e, a)
        cid = f"h{key[0]:.5f}_e{key[1]:.5f}_a{key[2]:.6f}".replace(".", "p")
        case_dir = output_dir / cid
        case_dir.mkdir()
        inp = render_protected_input(data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file, target_geometric_altitude_deg=h,
            observer_elevation_m=e, aod550=a)
        (case_dir / "uvspec.inp").write_text(inp, encoding="utf-8")
        proc = subprocess.run([str(uvspec)], input=inp, text=True, capture_output=True, check=False)
        (case_dir / "uvspec.stdout").write_text(proc.stdout, encoding="utf-8")
        (case_dir / "uvspec.stderr").write_text(proc.stderr, encoding="utf-8")
        parsed = None
        refusal = None
        if proc.returncode == 0:
            try:
                parsed = parse_protected_transmission(proc.stdout, target_geometric_altitude_deg=h)
                status = "PASS"
            except Exception as exc:
                status = "NUMERICALLY_UNRESOLVED"
                refusal = f"{type(exc).__name__}: {exc}"
        else:
            status = "NUMERICALLY_UNRESOLVED"
            refusal = f"uvspec_exit_{proc.returncode}"
        result = {**row, "caseId": cid, "status": status, "solverExitCode": int(proc.returncode),
                  "parserRefusal": refusal, "solverInvocationOrdinal": ordinal,
                  "sameIdentityRetryUsed": False, "positiveEpsilonSubstitutionUsed": False,
                  "refractionAppliedInRadiativeTransfer": False}
        if parsed is not None:
            result.update(parsed)
        (case_dir / "case-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results[key] = result
        rows.append(result)
    if len(rows) != fresh.EXPECTED_PROTECTED_SPECTRA:
        raise ProtectedV2Refusal("protected-v2 solver invocation count drift")
    unresolved = [r["caseId"] for r in rows if r["status"] != "PASS"]
    if unresolved:
        validation = {
            "schemaVersion": 1, "stageId": STAGE_ID, "protocolId": PROTOCOL_ID,
            "scientificState": SCIENTIFIC_STATE, "status": "PROTECTED_VALIDATION_FAIL_NUMERICALLY_UNRESOLVED",
            "freshProtectedAtmosphericSpectrumCount": fresh.EXPECTED_PROTECTED_SPECTRA,
            "freshProtectedJohnsonVComparisonCount": 0,
            "numericallyUnresolvedSpectrumCount": len(unresolved),
            "numericallyUnresolvedCaseIds": unresolved,
            "minimumSupportedGeometricAltitudeIfPassDeg": None,
            "exactHorizonSupported": False, "postResultFloorBackSelectionAuthorized": False,
            "postResultRetuningAuthorized": False, "productionAuthorized": False,
            "applicationSupportChanged": False,
        }
    else:
        validation = evaluate_complete_results(root=root, candidate_runtime=candidate,
            protected_results=results, sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path)
    validation.update({"candidateRuntimeSha256": EXPECTED_CANDIDATE_RUNTIME_SHA256,
        "scientificSolverExecuted": True, "solver": "sdisort", "solverGeometry": "pseudo-spherical",
        "solverInvocationCount": len(rows), "randomNumbersUsed": False,
        "positiveEpsilonSubstitutionUsed": False, "sameIdentityRetryUsed": False,
        "refractionAppliedInRadiativeTransfer": False})
    (output_dir / "low-altitude-stellar-protected-v2-validation-v1.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return validation


def review_ledger() -> dict[str, Any]:
    fresh.validate_protocol()
    return {
        "schemaVersion": 1, "stageId": STAGE_ID, "protocolId": PROTOCOL_ID,
        "scientificState": SCIENTIFIC_STATE,
        "coordinatorCorrectionIssue60CommentId": fresh.COORDINATOR_CORRECTION_ISSUE60_COMMENT_ID,
        "candidateTrainingExecutionId": EXPECTED_TRAINING_EXECUTION_ID,
        "candidateAssemblyId": EXPECTED_CANDIDATE_ASSEMBLY_ID,
        "candidateRuntimeSha256": EXPECTED_CANDIDATE_RUNTIME_SHA256,
        "candidateSourceRunId": EXPECTED_CANDIDATE_SOURCE_RUN_ID,
        "candidateSourceJobId": EXPECTED_CANDIDATE_SOURCE_JOB_ID,
        "candidateArtifactId": EXPECTED_CANDIDATE_ARTIFACT_ID,
        "candidateArtifactDigest": EXPECTED_CANDIDATE_ARTIFACT_DIGEST,
        "candidateSourceDispatchSha": EXPECTED_CANDIDATE_SOURCE_DISPATCH_SHA,
        "protectedAltitudeDeg": list(fresh.PROTECTED_ALTITUDE_DEG),
        "protectedElevationM": list(fresh.PROTECTED_ELEVATION_M),
        "protectedAod550": list(fresh.PROTECTED_AOD550),
        "protectedAtmosphericSpectrumCount": fresh.EXPECTED_PROTECTED_SPECTRA,
        "protectedJohnsonVComparisonCount": fresh.EXPECTED_PROTECTED_COMPARISONS,
        "representativeLibraryNumbers": list(fresh.REPRESENTATIVE_LIBRARY_NUMBERS),
        "maxAbsDeltaAvMagLimit": fresh.MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": fresh.RMS_ERROR_MAG_LIMIT,
        "globalAndEveryAltitudeCellCenterMustPass": True,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "sourceZenithAngleRelation": "sza=90deg-targetGeometricAltitudeDeg",
        "refractionAppliedInRadiativeTransfer": False,
        "exactFiveDegreeSeamContentIdentityRequired": True,
        "minimumSupportedGeometricAltitudeIfPassDeg": 0.25,
        "exactHorizonSupported": False,
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "githubRerunPermitted": False,
        "solverRetryPermitted": False,
        "solverResumePermitted": False,
        "positiveEpsilonSubstitutionAllowed": False,
        "scientificExecutionAuthorizedByModule": False,
        "protectedResultsOpenedByReview": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
        "inadmissibleExec001NumericalResultsUsed": False,
        "mysticState0077ResidualsUsed": False,
        "taylorOrJerusalemUsed": False,
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
        parser.error("protected-v2 validation requires --execute --allow-execution")
    required = [args.candidate_runtime, args.expected_candidate_sha256, args.uvspec, args.data_dir,
                args.atmosphere_file, args.wavelength_grid_file, args.sed_bundle, args.johnson_v, args.output_dir]
    if any(value is None for value in required):
        parser.error("all protected-v2 execution bindings are required")
    result = execute_campaign(root=args.root, candidate_runtime_path=args.candidate_runtime,
        expected_candidate_sha256=args.expected_candidate_sha256, uvspec=args.uvspec,
        data_dir=args.data_dir, atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file, sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v, output_dir=args.output_dir, allow_execution=True)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2, sort_keys=True))
    return 0 if result["status"] == "PROTECTED_VALIDATION_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
