#!/usr/bin/env python3
"""Fresh protected-v2 validator for LOWALT-STELLAR-STATE-0001.

The protected matrix is the reviewed result-blind cell-center protocol frozen in
Issue #60 comment 5468889581. Import/review never executes a solver. Execution
requires an explicit one-shot dispatch and the exact admissible exec003
candidate runtime SHA. No protected-v1 numerical result, post-result retuning,
retry/resume, epsilon substitution, support-floor back-selection, or refraction
inside radiative transfer exists in this controller.
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


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reviewed module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phase_b = _load_module("low_altitude_phase_b_protected_v2_contract", HERE / "low_altitude_phase_b.py")
fresh_v2 = _load_module("low_altitude_protected_v2_fresh_matrix_contract", HERE / "protected_v2_fresh_matrix.py")

STAGE_ID = "low-altitude-stellar-phase-b-protected-validation-v2"
EXECUTION_ID = "low-altitude-stellar-phase-b-protected-validation-v2-exec001"
PROTOCOL_ID = fresh_v2.PROTOCOL_ID
SCIENTIFIC_STATE = phase_b.SCIENTIFIC_STATE
PROTOCOL_FREEZE_ISSUE60_COMMENT_ID = 5468889581

CANDIDATE_RUNTIME_SHA256 = "4730c4404ef4ee93c07930f5fe8eb391f117cdc84f2c9eff49c5e7ee9f73b72e"
CANDIDATE_ASSEMBLY_ID = "low-altitude-stellar-phase-b-training-candidate-v1-exec003"
CANDIDATE_ARTIFACT_ID = 9732635873
CANDIDATE_ARTIFACT_DIGEST = "sha256:f5049c22d5c4c793e4ee789b3e0e050969b132aeac714c8ccf17d7de264dbeec"
CANDIDATE_ASSEMBLY_RUN_ID = 33313239384
CANDIDATE_ASSEMBLY_JOB_ID = 99261929321
CANDIDATE_ASSEMBLY_DISPATCH_SHA = "c723e3c4cf780d68148b8b9297e486596e33d6a5"
TRAINING_EXECUTION_ID = "low-altitude-stellar-phase-b-training-v1-exec003"
TRAINING_RUN_ID = 33312698195
TRAINING_ARTIFACT_ID = 9732576191
TRAINING_ARTIFACT_DIGEST = "sha256:29d5c7ae2518735989364e7d235a87ff4bf4c48295b70761d7816835d2cc238a"
TRAINING_DISPATCH_SHA = "b72a8a9bf625e49e78fd5631b22957bf6025cd78"
SOURCE_V32_RUNTIME_SHA256 = phase_b.SOURCE_V32_RUNTIME_SHA256

SOURCE_SED_SHA256 = "85cbf41c86309b9d54d4765516167165f2d8736bcda8994337ef25d775ea11cb"
SOURCE_JOHNSON_V_SHA256 = "51c357eb4cb3609361759f9750ad13ae13a901970913e3a5d87bb5c45ee2db9a"
EXACT_PACKAGE_SPEC = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
UVSPEC_HELP_SHA256 = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
AFGLUS_SHA256 = "dab26290ed81c762ed0c607e5dc2d53393c1462a0c3a528bc5e3f5935191cfb5"
SURFACE_ALBEDO = 0.15
EXPECTED_PROTECTED_SPECTRA = fresh_v2.EXPECTED_PROTECTED_SPECTRA
EXPECTED_PROTECTED_COMPARISONS = fresh_v2.EXPECTED_PROTECTED_COMPARISONS


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
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise ProtectedV2Refusal("atm_z_grid must be strictly ascending")
    return grid


def protected_cases() -> list[dict[str, float]]:
    fresh_v2.validate_protocol()
    return fresh_v2.build_protected_cases()


def protected_keys() -> set[tuple[float, float, float]]:
    return {
        phase_b.coord(row["targetGeometricAltitudeDeg"], row["observerElevationM"], row["aod550"])
        for row in protected_cases()
    }


def render_protected_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                           target_geometric_altitude_deg: float, observer_elevation_m: float,
                           aod550: float) -> str:
    h = finite("targetGeometricAltitudeDeg", target_geometric_altitude_deg)
    e = finite("observerElevationM", observer_elevation_m)
    a = finite("aod550", aod550)
    if phase_b.coord(h, e, a) not in protected_keys():
        raise ProtectedV2Refusal("renderer restricted to frozen protected-v2 coordinate universe")
    if not 0.0 < h < 5.0:
        raise ProtectedV2Refusal("protected target must be strictly above the geometric horizon and below 5deg")
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
    if h not in fresh_v2.PROTECTED_ALTITUDE_DEG:
        raise ProtectedV2Refusal("parser altitude is not a frozen protected-v2 altitude")
    mu0 = math.sin(math.radians(h))
    if not math.isfinite(mu0) or not mu0 > 0.0:
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
        if value < 0.0 or not math.isfinite(value) or not math.isfinite(reconstructed) or not 0.0 < reconstructed <= 1.0:
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
    exact = {
        "assemblyId": CANDIDATE_ASSEMBLY_ID,
        "trainingExecutionId": TRAINING_EXECUTION_ID,
        "trainingSourceRunId": TRAINING_RUN_ID,
        "trainingSourceArtifactId": TRAINING_ARTIFACT_ID,
        "trainingSourceArtifactDigest": TRAINING_ARTIFACT_DIGEST,
        "trainingSourceDispatchSha": TRAINING_DISPATCH_SHA,
        "sourceV32RuntimeSha256": SOURCE_V32_RUNTIME_SHA256,
        "trainingSolver": "sdisort",
        "trainingSolverGeometry": "pseudo-spherical",
        "trainingTargetAltitudeBasis": "topocentric-vacuum-geometric",
    }
    for key, expected in exact.items():
        if provenance.get(key) != expected:
            raise ProtectedV2Refusal(f"candidate provenance mismatch: {key}")
    for key in ("protectedValidationOpened", "protectedResultsOpened", "scientificallyValidatedBelow5Deg",
                "productionAuthorized", "applicationSupportChanged", "refractionAppliedInRadiativeTransfer"):
        if provenance.get(key) is not False:
            raise ProtectedV2Refusal(f"candidate claim boundary drift: {key}")
    if provenance.get("protectedSolverInvocationCount") != 0:
        raise ProtectedV2Refusal("candidate protected invocation count drift")
    routing = runtime.get("routing") or {}
    if routing.get("lowerProviderMinInclusiveDeg") != 0.25 or routing.get("lowerProviderMaxExclusiveDeg") != 5.0:
        raise ProtectedV2Refusal("candidate routing boundary drift")
    if routing.get("exactFiveAndAboveProvider") != "authoritative-v3.2" or routing.get("exactHorizonSupported") is not False:
        raise ProtectedV2Refusal("candidate seam/horizon claim drift")
    representation = runtime.get("representation") or {}
    expected_representation = {
        "interpolatedQuantity": "direct-optical-depth",
        "targetAltitudeCoordinate": "identity-geometric-altitude-deg",
        "targetAltitudeInterpolation": "linear",
        "observerElevationInterpolation": "linear",
        "aod550Interpolation": "linear",
        "cscExtrapolationBelow5Deg": False,
    }
    for key, expected in expected_representation.items():
        if representation.get(key) != expected:
            raise ProtectedV2Refusal(f"candidate representation drift: {key}")


def _load_photometry(root: Path):
    path = root / "review/asiv-matched-stellar-transport-v1/assemble_validate_matched_stellar_v1.py"
    return _load_module("low_altitude_protected_v2_photometry", path)


def evaluate_complete_protected_results(*, root: Path, candidate_runtime: dict[str, Any],
                                        protected_results: dict[tuple[float, float, float], dict[str, Any]],
                                        sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    validate_candidate(candidate_runtime)
    expected = protected_keys()
    if set(protected_results) != expected:
        raise ProtectedV2Refusal("protected-v2 result universe incomplete or drifted")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise ProtectedV2Refusal("frozen Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ProtectedV2Refusal("frozen Johnson-V asset SHA-256 drift")
    phot = _load_photometry(root)
    _, wavelength_nm, band_response, representatives = phot.load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path
    )
    reps = [row for row in representatives if int(row["libraryNumber"]) in fresh_v2.REPRESENTATIVE_LIBRARY_NUMBERS]
    if [int(row["libraryNumber"]) for row in reps] != list(fresh_v2.REPRESENTATIVE_LIBRARY_NUMBERS):
        raise ProtectedV2Refusal("representative Pickles template identity drift")
    delta_rows: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for row in protected_cases():
        h = row["targetGeometricAltitudeDeg"]
        e = row["observerElevationM"]
        a = row["aod550"]
        key = phase_b.coord(h, e, a)
        ref = protected_results[key]
        if ref.get("status") != "PASS":
            raise ProtectedV2Refusal("non-PASS protected spectrum in complete evaluator")
        predicted_tau = phase_b.interpolate_lower_tau(candidate_runtime, h, e, a)
        predicted_t = [math.exp(-tau) for tau in predicted_tau]
        if any((not math.isfinite(x) or not 0.0 < x <= 1.0) for x in predicted_t):
            raise ProtectedV2Refusal("candidate interpolation produced unrepresentable direct transmission")
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
            comparison = {
                "targetGeometricAltitudeDeg": h,
                "observerElevationM": e,
                "aod550": a,
                "libraryNumber": int(sed["libraryNumber"]),
                "runtimeAvMag": runtime_av,
                "referenceAvMag": reference_av,
                "deltaAvMag": runtime_av - reference_av,
            }
            delta_rows.append(comparison)
            comparisons.append(comparison)
        cases.append({**row, "sedComparisons": comparisons})
    metrics = fresh_v2.evaluate_deltas(delta_rows)
    return {
        "status": metrics["status"],
        "freshProtectedAtmosphericSpectrumCount": EXPECTED_PROTECTED_SPECTRA,
        "freshProtectedJohnsonVComparisonCount": EXPECTED_PROTECTED_COMPARISONS,
        "overall": metrics["overall"],
        "byProtectedAltitudeDeg": metrics["byProtectedAltitudeDeg"],
        "minimumSupportedGeometricAltitudeIfPassDeg": metrics["minimumSupportedGeometricAltitudeIfPassDeg"],
        "cases": cases,
    }


def execute_campaign(*, root: Path, candidate_runtime_path: Path, expected_candidate_sha256: str,
                     uvspec: Path, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                     sed_bundle_path: Path, johnson_v_path: Path, output_dir: Path) -> dict[str, Any]:
    fresh_v2.validate_protocol()
    if expected_candidate_sha256 != CANDIDATE_RUNTIME_SHA256:
        raise ProtectedV2Refusal("expected candidate SHA is not the frozen protected-v2 candidate")
    actual_candidate_sha = sha256_file(candidate_runtime_path)
    if actual_candidate_sha != CANDIDATE_RUNTIME_SHA256:
        raise ProtectedV2Refusal("candidate runtime SHA-256 mismatch")
    candidate = json.loads(Path(candidate_runtime_path).read_text(encoding="utf-8"))
    validate_candidate(candidate)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ProtectedV2Refusal("protected-v2 output directory already exists; retry/resume is forbidden")
    output_dir.mkdir(parents=True)
    results: dict[tuple[float, float, float], dict[str, Any]] = {}
    raw_cases: list[dict[str, Any]] = []
    numerically_unresolved = 0
    solver_invocations = 0
    for index, row in enumerate(protected_cases(), start=1):
        h = row["targetGeometricAltitudeDeg"]
        e = row["observerElevationM"]
        a = row["aod550"]
        rendered = render_protected_input(
            data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            target_geometric_altitude_deg=h, observer_elevation_m=e, aod550=a,
        )
        case_id = f"protected-v2-{index:03d}"
        case_dir = output_dir / "cases" / case_id
        case_dir.mkdir(parents=True)
        (case_dir / "input.inp").write_text(rendered, encoding="utf-8")
        proc = subprocess.run([str(uvspec)], input=rendered, text=True, capture_output=True)
        solver_invocations += 1
        (case_dir / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (case_dir / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            raise ProtectedV2Refusal(f"uvspec failed for {case_id}: exit {proc.returncode}")
        try:
            parsed = parse_protected_transmission(proc.stdout, target_geometric_altitude_deg=h)
            status = "PASS"
        except ProtectedV2Refusal as exc:
            parsed = None
            status = "NUMERICALLY_UNRESOLVED"
            numerically_unresolved += 1
            (case_dir / "numeric-refusal.txt").write_text(str(exc) + "\n", encoding="utf-8")
        result = {
            **row,
            "caseId": case_id,
            "status": status,
            "sourceZenithAngleDeg": 90.0 - h,
            "positiveEpsilonSubstitutionUsed": False,
        }
        if parsed is not None:
            result.update(parsed)
        key = phase_b.coord(h, e, a)
        results[key] = result
        raw_cases.append(result)
    if solver_invocations != EXPECTED_PROTECTED_SPECTRA or len(results) != EXPECTED_PROTECTED_SPECTRA:
        raise ProtectedV2Refusal("protected-v2 solver accounting drift")
    if numerically_unresolved:
        decision: dict[str, Any] = {
            "status": "PROTECTED_VALIDATION_FAIL_NUMERICALLY_UNRESOLVED",
            "freshProtectedAtmosphericSpectrumCount": EXPECTED_PROTECTED_SPECTRA,
            "freshProtectedJohnsonVComparisonCount": 0,
            "overall": None,
            "byProtectedAltitudeDeg": None,
            "minimumSupportedGeometricAltitudeIfPassDeg": None,
            "cases": raw_cases,
        }
    else:
        decision = evaluate_complete_protected_results(
            root=root, candidate_runtime=candidate, protected_results=results,
            sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path,
        )
    decision.update({
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "executionId": EXECUTION_ID,
        "protocolId": PROTOCOL_ID,
        "scientificState": SCIENTIFIC_STATE,
        "protocolFreezeIssue60CommentId": PROTOCOL_FREEZE_ISSUE60_COMMENT_ID,
        "candidateRuntimeSha256": actual_candidate_sha,
        "candidateAssemblyId": CANDIDATE_ASSEMBLY_ID,
        "candidateArtifactId": CANDIDATE_ARTIFACT_ID,
        "candidateArtifactDigest": CANDIDATE_ARTIFACT_DIGEST,
        "candidateAssemblyRunId": CANDIDATE_ASSEMBLY_RUN_ID,
        "candidateAssemblyJobId": CANDIDATE_ASSEMBLY_JOB_ID,
        "candidateAssemblyDispatchSha": CANDIDATE_ASSEMBLY_DISPATCH_SHA,
        "scientificSolverExecuted": True,
        "solver": "sdisort",
        "solverGeometry": "pseudo-spherical",
        "solverInvocationCount": solver_invocations,
        "randomNumbersUsed": False,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "numericallyUnresolvedSpectrumCount": numerically_unresolved,
        "positiveEpsilonSubstitutionUsed": False,
        "sameIdentityRetryUsed": False,
        "githubRerunUsed": False,
        "exactHorizonSupported": False,
        "exactFiveDegreeProvider": "authoritative-v3.2",
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
    })
    result_path = output_dir / "low-altitude-stellar-phase-b-protected-validation-v2.json"
    result_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "schemaVersion": 1,
        "executionId": EXECUTION_ID,
        "stageId": STAGE_ID,
        "scientificState": SCIENTIFIC_STATE,
        "protocolId": PROTOCOL_ID,
        "candidateRuntimeSha256": actual_candidate_sha,
        "solverInvocationCount": solver_invocations,
        "protectedResultsOpened": True,
        "status": decision["status"],
        "minimumSupportedGeometricAltitudeIfPassDeg": decision.get("minimumSupportedGeometricAltitudeIfPassDeg"),
        "exactHorizonSupported": False,
        "positiveEpsilonSubstitutionUsed": False,
        "retryResumePermitted": False,
        "githubRerunPermitted": False,
        "productionAuthorized": False,
        "applicationSupportChanged": False,
    }
    (output_dir / "execution-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return decision


def review_ledger() -> dict[str, Any]:
    fresh_v2.validate_protocol()
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "executionId": EXECUTION_ID,
        "protocolId": PROTOCOL_ID,
        "scientificState": SCIENTIFIC_STATE,
        "protocolFreezeIssue60CommentId": PROTOCOL_FREEZE_ISSUE60_COMMENT_ID,
        "candidateRuntimeSha256": CANDIDATE_RUNTIME_SHA256,
        "candidateAssemblyId": CANDIDATE_ASSEMBLY_ID,
        "candidateArtifactId": CANDIDATE_ARTIFACT_ID,
        "candidateArtifactDigest": CANDIDATE_ARTIFACT_DIGEST,
        "candidateAssemblyRunId": CANDIDATE_ASSEMBLY_RUN_ID,
        "candidateAssemblyJobId": CANDIDATE_ASSEMBLY_JOB_ID,
        "candidateAssemblyDispatchSha": CANDIDATE_ASSEMBLY_DISPATCH_SHA,
        "trainingExecutionId": TRAINING_EXECUTION_ID,
        "trainingRunId": TRAINING_RUN_ID,
        "trainingArtifactId": TRAINING_ARTIFACT_ID,
        "trainingArtifactDigest": TRAINING_ARTIFACT_DIGEST,
        "trainingDispatchSha": TRAINING_DISPATCH_SHA,
        "protectedAtmosphericSpectrumCount": EXPECTED_PROTECTED_SPECTRA,
        "protectedJohnsonVComparisonCount": EXPECTED_PROTECTED_COMPARISONS,
        "protectedAltitudeDeg": list(fresh_v2.PROTECTED_ALTITUDE_DEG),
        "protectedElevationM": list(fresh_v2.PROTECTED_ELEVATION_M),
        "protectedAod550": list(fresh_v2.PROTECTED_AOD550),
        "representativeLibraryNumbers": list(fresh_v2.REPRESENTATIVE_LIBRARY_NUMBERS),
        "maxAbsDeltaAvMagLimit": fresh_v2.MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": fresh_v2.RMS_ERROR_MAG_LIMIT,
        "globalAndEveryAltitudeIntervalMustPass": True,
        "matrixSelectionBasis": "exact-geometric-center-of-every-frozen-trilinear-interpolation-cell",
        "protectedV1NumericalResultsUsed": False,
        "mysticState0077ResidualsUsed": False,
        "taylorOrJerusalemUsed": False,
        "candidateShaMustBeBoundBeforeExecution": True,
        "targetAltitudeBasis": "topocentric-vacuum-geometric",
        "refractionAppliedInRadiativeTransfer": False,
        "zeroOrUnderflowDirectTransmission": "TERMINAL_REFUSAL",
        "postResultFloorBackSelectionAuthorized": False,
        "postResultRetuningAuthorized": False,
        "positiveEpsilonSubstitutionAllowed": False,
        "sameIdentityRetryAllowed": False,
        "githubRerunAllowed": False,
        "scientificExecutionAuthorizedByModule": False,
        "minimumSupportedGeometricAltitudeIfPassDeg": 0.25,
        "exactHorizonSupported": False,
        "exactFiveDegreeProvider": "authoritative-v3.2",
        "productionAuthorized": False,
        "applicationSupportChanged": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-ledger", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path)
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
            parser.error("ledger emission cannot execute protected science")
        print(json.dumps(review_ledger(), indent=2, sort_keys=True))
        return 0
    if not args.execute or not args.allow_execution:
        parser.error("protected-v2 execution requires both --execute and --allow-execution")
    required = {
        "root": args.root,
        "candidate-runtime": args.candidate_runtime,
        "expected-candidate-sha256": args.expected_candidate_sha256,
        "uvspec": args.uvspec,
        "data-dir": args.data_dir,
        "atmosphere-file": args.atmosphere_file,
        "wavelength-grid-file": args.wavelength_grid_file,
        "sed-bundle": args.sed_bundle,
        "johnson-v": args.johnson_v,
        "output-dir": args.output_dir,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error("missing protected-v2 execution arguments: " + ", ".join(missing))
    execute_campaign(
        root=args.root,
        candidate_runtime_path=args.candidate_runtime,
        expected_candidate_sha256=args.expected_candidate_sha256,
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
