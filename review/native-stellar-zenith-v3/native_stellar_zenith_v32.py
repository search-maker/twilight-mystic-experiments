#!/usr/bin/env python3
"""Native stellar zenith v3.2 exact-vertical endpoint.

Frozen protocol: NATIVE_STELLAR_ZENITH_V32_ENDPOINT_METHOD_PROTOCOL.md.

The v3 scientific design is preserved exactly.  Every physical target altitude
below 90 degrees delegates byte-for-byte to native_stellar_zenith_v3.  Exact
physical zenith alone uses the preregistered and validated deterministic DISORT
vertical optical-column endpoint: sum the resolved per-layer optical depth from
libRadtran's verbose optical_properties table and set T=exp(-tau).

Importing this module or running it without --execute never invokes a solver.
Protected holdouts remain closed until a separately gated one-shot dispatch is
created after this method is reviewed and merged to main.
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
BASE_PATH = HERE / "native_stellar_zenith_v3.py"
VERTICAL_PATH = HERE / "diagnose_exact_vertical_optical_column_v1.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load(BASE_PATH, "native_stellar_zenith_v3_base_for_v32")
vertical = _load(VERTICAL_PATH, "exact_vertical_optical_column_for_v32")

STAGE_ID = "native-stellar-zenith-v3.2"
METHOD_VERSION = "stellar-transport-v3.2-exact-vertical-endpoint"
MYSTIC_STATE = base.MYSTIC_STATE

# Immutable proof that authorized drafting this endpoint method.
EXACT_VERTICAL_ANALYSIS_RUN_ID = 33041830554
EXACT_VERTICAL_ANALYSIS_DISPATCH_SHA = "bdac3f0f03f1d2c63d274076365f1f3331a8b68e"
EXACT_VERTICAL_ANALYSIS_ARTIFACT_ID = 9634148868
EXACT_VERTICAL_ANALYSIS_ARTIFACT_DIGEST = "sha256:aa5b0b4a5b705bdcefd29c35113f331aa667b8dca9a2b228d44aa52ec864ca78"
EXACT_VERTICAL_SOURCE_RUN_ID = 33041069040
EXACT_VERTICAL_SOURCE_ARTIFACT_ID = 9633879569
EXACT_VERTICAL_SOURCE_ARTIFACT_DIGEST = "sha256:eba59cc5d22e1600b0c38809cac29d615dddd0af02b491febae65164c3a1004e"
EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_TAU = 8.630205807602653e-06
EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_AV_MAG = 2.0522918572907223e-06
EXACT_VERTICAL_PROOF_MAX_DIRECT_FLUX_CROSSCHECK = 5.000000002919336e-08
EXACT_VERTICAL_PROOF_TAU_LIMIT = 1.0e-05
EXACT_VERTICAL_PROOF_AV_LIMIT = 1.0e-04
EXACT_VERTICAL_PROOF_CROSSCHECK_LIMIT = 1.0e-07

# Re-export the complete frozen v3 universe and identities.
SOURCE_ASSET_COMMIT = base.SOURCE_ASSET_COMMIT
SOURCE_RUNTIME_SHA256 = base.SOURCE_RUNTIME_SHA256
SOURCE_SED_SHA256 = base.SOURCE_SED_SHA256
SOURCE_JOHNSON_V_SHA256 = base.SOURCE_JOHNSON_V_SHA256
SOURCE_PROTOCOL_SHA256 = base.SOURCE_PROTOCOL_SHA256
EXACT_PACKAGE_SPEC = base.EXACT_PACKAGE_SPEC
UVSPEC_SHA256 = base.UVSPEC_SHA256
UVSPEC_HELP_SHA256 = base.UVSPEC_HELP_SHA256
AFGLUS_SHA256 = base.AFGLUS_SHA256
WAVELENGTH_NM = base.WAVELENGTH_NM
OLD_ALTITUDE_KNOTS = base.OLD_ALTITUDE_KNOTS
NEW_TRAINING_ALTITUDE_DEG = base.NEW_TRAINING_ALTITUDE_DEG
EXTENDED_ALTITUDE_KNOTS = base.EXTENDED_ALTITUDE_KNOTS
ELEVATION_KNOTS_M = base.ELEVATION_KNOTS_M
AOD_KNOTS = base.AOD_KNOTS
VALIDATION_ALTITUDE_DEG = base.VALIDATION_ALTITUDE_DEG
VALIDATION_ELEVATION_M = base.VALIDATION_ELEVATION_M
VALIDATION_AOD550 = base.VALIDATION_AOD550
REPRESENTATIVE_LIBRARY_NUMBERS = base.REPRESENTATIVE_LIBRARY_NUMBERS
MAX_ABS_ERROR_MAG_LIMIT = base.MAX_ABS_ERROR_MAG_LIMIT
RMS_ERROR_MAG_LIMIT = base.RMS_ERROR_MAG_LIMIT
SURFACE_ALBEDO = base.SURFACE_ALBEDO
MOL_ABS_PARAM = base.MOL_ABS_PARAM

EXACT_VERTICAL_ALTITUDE_DEG = 90.0
EXACT_VERTICAL_NUMBER_OF_STREAMS = 16
EXPECTED_TRAINING_SPECTRA = 100
EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA = 25
EXPECTED_SDISORT_TRAINING_SPECTRA = 75
EXPECTED_PROTECTED_HOLDOUT_SPECTRA = 64
EXPECTED_TOTAL_SOLVER_CALLS = 164
EXPECTED_JOHNSON_V_COMPARISONS = 192


class ZenithV32Refusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def finite(name: str, value: object) -> float:
    try:
        return base.finite(name, value)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc


def is_exact_zenith(target_altitude_deg: float) -> bool:
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    return math.isclose(altitude, EXACT_VERTICAL_ALTITUDE_DEG, rel_tol=0.0, abs_tol=1.0e-12)


def validate_proof_binding() -> None:
    if not EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_TAU <= EXACT_VERTICAL_PROOF_TAU_LIMIT:
        raise ZenithV32Refusal("bound exact-vertical optical-depth proof no longer passes")
    if not EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_AV_MAG <= EXACT_VERTICAL_PROOF_AV_LIMIT:
        raise ZenithV32Refusal("bound exact-vertical Johnson-V proof no longer passes")
    if not EXACT_VERTICAL_PROOF_MAX_DIRECT_FLUX_CROSSCHECK <= EXACT_VERTICAL_PROOF_CROSSCHECK_LIMIT:
        raise ZenithV32Refusal("bound exact-vertical parser cross-check no longer passes")


def build_training_cases() -> list[dict[str, float]]:
    return base.build_training_cases()


def build_validation_cases() -> list[dict[str, float]]:
    return base.build_validation_cases()


def validate_frozen_case_universe() -> None:
    validate_proof_binding()
    try:
        base.validate_frozen_case_universe()
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    training = build_training_cases()
    holdout = build_validation_cases()
    exact = [row for row in training if is_exact_zenith(row["targetAltitudeDeg"])]
    below = [row for row in training if not is_exact_zenith(row["targetAltitudeDeg"])]
    if len(training) != EXPECTED_TRAINING_SPECTRA:
        raise ZenithV32Refusal("v3.2 training count drift")
    if len(exact) != EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA:
        raise ZenithV32Refusal("v3.2 exact-vertical training count drift")
    if len(below) != EXPECTED_SDISORT_TRAINING_SPECTRA:
        raise ZenithV32Refusal("v3.2 below-zenith training count drift")
    if len(holdout) != EXPECTED_PROTECTED_HOLDOUT_SPECTRA:
        raise ZenithV32Refusal("v3.2 protected holdout count drift")
    if any(float(row["targetAltitudeDeg"]) >= EXACT_VERTICAL_ALTITUDE_DEG for row in holdout):
        raise ZenithV32Refusal("protected holdout must remain strictly below exact zenith")
    if NEW_TRAINING_ALTITUDE_DEG != (82.5, 85.0, 87.5, 90.0):
        raise ZenithV32Refusal("v3.2 training altitude universe drift")
    if VALIDATION_ALTITUDE_DEG != (80.9375, 83.4375, 85.9375, 88.4375):
        raise ZenithV32Refusal("v3.2 protected holdout altitude universe drift")
    if MAX_ABS_ERROR_MAG_LIMIT != 0.025 or RMS_ERROR_MAG_LIMIT != 0.010:
        raise ZenithV32Refusal("v3.2 acceptance-gate drift")


def expected_layer_count(atmosphere_file: Path, observer_elevation_m: float) -> int:
    try:
        grid = base.elevated_site_grid_ascending(atmosphere_file, observer_elevation_m)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    count = len(grid) - 1
    if count <= 0:
        raise ZenithV32Refusal("exact-vertical atmosphere has no layers")
    return count


def render_exact_vertical_input(*, data_dir: Path, atmosphere_file: Path,
                                wavelength_grid_file: Path, observer_elevation_m: float,
                                aod550: float) -> str:
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    if elevation not in ELEVATION_KNOTS_M:
        raise ZenithV32Refusal("exact-vertical endpoint is restricted to frozen training elevation knots")
    if aod not in AOD_KNOTS:
        raise ZenithV32Refusal("exact-vertical endpoint is restricted to frozen training AOD knots")
    try:
        grid = base.elevated_site_grid_ascending(atmosphere_file, elevation)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    solar_source = Path(data_dir) / "solar_flux" / "atlas_plus_modtran"
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        f"source solar {solar_source}",
        f"mol_abs_param {MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {WAVELENGTH_NM[0]} {WAVELENGTH_NM[-1]}",
        "sza 0.00000000",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {aod:.8f}",
        "rte_solver disort",
        f"number_of_streams {EXACT_VERTICAL_NUMBER_OF_STREAMS}",
        "output_quantity transmittance",
        "output_user lambda edir",
        "verbose",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    for forbidden in (
        "rte_solver sdisort", "sdisort nscat", "rte_solver mystic", "mc_",
        "write_optical_properties", "aerosol_species_file", "angstrom", "altitude ",
        "mc_elevation_file",
    ):
        if forbidden in lower:
            raise ZenithV32Refusal(f"forbidden exact-vertical directive emitted: {forbidden}")
    if text.count("source solar ") != 1 or "atlas_plus_modtran" not in text:
        raise ZenithV32Refusal("exact-vertical packaged solar source missing")
    if text.count("aerosol_default") != 1 or text.count("aerosol_set_tau_at_wvl") != 1:
        raise ZenithV32Refusal("exact-vertical aerosol directive surface drift")
    return text


def render_uvspec_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                        target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> str:
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    if not 80.0 <= altitude <= EXACT_VERTICAL_ALTITUDE_DEG:
        raise ZenithV32Refusal("zenith extension renderer is restricted to 80..90 deg")
    if not is_exact_zenith(altitude):
        try:
            return base.render_uvspec_input(
                data_dir=data_dir,
                atmosphere_file=atmosphere_file,
                wavelength_grid_file=wavelength_grid_file,
                target_altitude_deg=altitude,
                observer_elevation_m=observer_elevation_m,
                aod550=aod550,
            )
        except Exception as exc:
            raise ZenithV32Refusal(str(exc)) from exc
    return render_exact_vertical_input(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
        observer_elevation_m=observer_elevation_m,
        aod550=aod550,
    )


def parse_case_outputs(*, stdout_text: str, stderr_text: str, target_altitude_deg: float,
                       expected_layer_count_value: int | None = None) -> dict[str, Any]:
    altitude = finite("targetAltitudeDeg", target_altitude_deg)
    if not is_exact_zenith(altitude):
        try:
            parsed = base.parse_direct_transmission(stdout_text, target_altitude_deg=altitude)
        except Exception as exc:
            raise ZenithV32Refusal(str(exc)) from exc
        return {
            **parsed,
            "endpointMethod": "SDISORT_V3_UNCHANGED",
            "exactVerticalOpticalColumnEndpointApplied": False,
        }
    if expected_layer_count_value is None or int(expected_layer_count_value) <= 0:
        raise ZenithV32Refusal("exact-vertical parser requires the positive expected layer count")
    try:
        parsed_verbose = vertical.parse_verbose_optical_columns(
            stderr_text,
            expected_grid=WAVELENGTH_NM,
            expected_layer_count=int(expected_layer_count_value),
        )
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    tau = [finite("exactVerticalLayerSumOpticalDepth", value)
           for value in parsed_verbose["verboseColumnOpticalDepth"]]
    if len(tau) != len(WAVELENGTH_NM) or any(value < 0.0 for value in tau):
        raise ZenithV32Refusal("exact-vertical optical-column spectrum invalid")
    transmission = [math.exp(-value) for value in tau]
    if any(not (0.0 < value <= 1.0) for value in transmission):
        raise ZenithV32Refusal("exact-vertical reconstructed transmission invalid")
    return {
        "wavelengthNm": list(WAVELENGTH_NM),
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": tau,
        "targetAltitudeDeg": EXACT_VERTICAL_ALTITUDE_DEG,
        "sourceZenithAngleDeg": 0.0,
        "mu0": 1.0,
        "endpointMethod": "EXACT_VERTICAL_DISORT_RESOLVED_OPTICAL_COLUMN_V1",
        "exactVerticalOpticalColumnEndpointApplied": True,
        "layerCountByWavelength": list(parsed_verbose["layerCountByWavelength"]),
        "stdoutDirectSpectrumUsedAsEstimator": False,
    }


def _coord_key(h: float, e: float, a: float) -> tuple[float, float, float]:
    return base._coord_key(h, e, a)


def build_extended_runtime(source_runtime: dict[str, Any],
                           training_results: dict[tuple[float, float, float], dict[str, Any]]) -> dict[str, Any]:
    validate_frozen_case_universe()
    for row in build_training_cases():
        key = _coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
        if key not in training_results:
            raise ZenithV32Refusal("v3.2 training result universe incomplete")
        result = training_results[key]
        expected_method = (
            "EXACT_VERTICAL_DISORT_RESOLVED_OPTICAL_COLUMN_V1"
            if is_exact_zenith(row["targetAltitudeDeg"])
            else "SDISORT_V3_UNCHANGED"
        )
        if result.get("endpointMethod") != expected_method:
            raise ZenithV32Refusal("v3.2 training endpoint-method provenance drift")
    try:
        runtime = base.build_extended_runtime(source_runtime, training_results)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    runtime["representation"] = {
        **(runtime.get("representation") or {}),
        "version": METHOD_VERSION,
        "physicalTargetAltitudeMaxDeg": EXACT_VERTICAL_ALTITUDE_DEG,
        "zenithEndpointRule": "h<90:unchanged-sdisort-v3;h=90:exact-vertical-disort-resolved-optical-column",
        "positiveEpsilonSubstitutionUsed": False,
        "targetAltitudeCoordinate": "cosecant-altitude-1-over-sin-h",
    }
    runtime["provenance"] = {
        **(runtime.get("provenance") or {}),
        "zenithExtensionStageId": STAGE_ID,
        "methodVersion": METHOD_VERSION,
        "sourceV2RuntimeSha256": SOURCE_RUNTIME_SHA256,
        "oldDomainValuesUnchanged": True,
        "newTrainingSolverSpectrumCount": EXPECTED_TRAINING_SPECTRA,
        "belowZenithSdisortTrainingSpectrumCount": EXPECTED_SDISORT_TRAINING_SPECTRA,
        "exactVerticalOpticalColumnTrainingSpectrumCount": EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA,
        "exactVerticalAnalysisRunId": EXACT_VERTICAL_ANALYSIS_RUN_ID,
        "exactVerticalAnalysisArtifactId": EXACT_VERTICAL_ANALYSIS_ARTIFACT_ID,
        "exactVerticalAnalysisArtifactDigest": EXACT_VERTICAL_ANALYSIS_ARTIFACT_DIGEST,
        "exactVerticalSourceRunId": EXACT_VERTICAL_SOURCE_RUN_ID,
        "exactVerticalSourceArtifactId": EXACT_VERTICAL_SOURCE_ARTIFACT_ID,
        "exactVerticalSourceArtifactDigest": EXACT_VERTICAL_SOURCE_ARTIFACT_DIGEST,
        "epsilonSubstitutionUsed": False,
        "trainingCoordinatesChangedFromV3": False,
        "holdoutCoordinatesChangedFromV3": False,
        "acceptanceGatesChangedFromV3": False,
        "postResultRetuningPerformed": False,
        "empiricalRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
        "productionAuthorized": False,
    }
    if runtime["directOpticalDepth"][:675] != source_runtime["directOpticalDepth"]:
        raise ZenithV32Refusal("v2 spectra changed while building v3.2 extension")
    if len(runtime["directOpticalDepth"]) != 775:
        raise ZenithV32Refusal("v3.2 runtime must contain exactly 775 spectra")
    return runtime


def validate_against_fresh_holdout(*, root: Path, extended_runtime: dict[str, Any],
                                   validation_results: dict[tuple[float, float, float], dict[str, Any]],
                                   sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    if any(is_exact_zenith(row["targetAltitudeDeg"]) for row in build_validation_cases()):
        raise ZenithV32Refusal("v3.2 protected holdouts must not use exact-vertical endpoint")
    for row in build_validation_cases():
        key = _coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
        if key not in validation_results:
            raise ZenithV32Refusal("v3.2 protected holdout result universe incomplete")
        if validation_results[key].get("endpointMethod") != "SDISORT_V3_UNCHANGED":
            raise ZenithV32Refusal("v3.2 protected holdout reference method drift")
    try:
        result = base.validate_against_fresh_holdout(
            root=root,
            extended_runtime=extended_runtime,
            validation_results=validation_results,
            sed_bundle_path=sed_bundle_path,
            johnson_v_path=johnson_v_path,
        )
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    result["stageId"] = STAGE_ID
    result["methodVersion"] = METHOD_VERSION
    result["interpolation"] = "v3-csc-altitude-trilinear-direct-optical-depth-with-exact-vertical-90deg-endpoint"
    result["exactVerticalTrainingSpectrumCount"] = EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA
    result["belowZenithSdisortTrainingSpectrumCount"] = EXPECTED_SDISORT_TRAINING_SPECTRA
    result["protectedHoldoutSdisortSpectrumCount"] = EXPECTED_PROTECTED_HOLDOUT_SPECTRA
    result["exactVerticalEndpointProof"] = {
        "analysisRunId": EXACT_VERTICAL_ANALYSIS_RUN_ID,
        "analysisArtifactId": EXACT_VERTICAL_ANALYSIS_ARTIFACT_ID,
        "analysisArtifactDigest": EXACT_VERTICAL_ANALYSIS_ARTIFACT_DIGEST,
        "maxAbsDeltaOpticalDepth": EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_TAU,
        "maxAbsDeltaOpticalDepthLimit": EXACT_VERTICAL_PROOF_TAU_LIMIT,
        "maxAbsDeltaAvMag": EXACT_VERTICAL_PROOF_MAX_ABS_DELTA_AV_MAG,
        "maxAbsDeltaAvMagLimit": EXACT_VERTICAL_PROOF_AV_LIMIT,
        "passed": True,
    }
    result["claimBoundary"] = {
        **(result.get("claimBoundary") or {}),
        "computationalReferenceValidationOnly": True,
        "exactVerticalEndpointComputationallyValidated": True,
        "positiveEpsilonSubstitutionUsed": False,
        "oldV2DomainChanged": False,
        "empiricalRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
        "productionAuthorized": False,
    }
    return result


def _safe_component(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".").replace("-", "m").replace(".", "p")


def _case_dir(output_dir: Path, *, phase: str, index: int, row: dict[str, float]) -> Path:
    return output_dir / "cases" / (
        f"{phase}-{index:03d}-h{_safe_component(row['targetAltitudeDeg'])}"
        f"-e{_safe_component(row['observerElevationM'])}-a{_safe_component(row['aod550'])}"
    )


def execute_case(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                 wavelength_grid_file: Path, row: dict[str, float], output_dir: Path,
                 phase: str, index: int) -> dict[str, Any]:
    input_text = render_uvspec_input(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
        target_altitude_deg=row["targetAltitudeDeg"],
        observer_elevation_m=row["observerElevationM"],
        aod550=row["aod550"],
    )
    case_dir = _case_dir(Path(output_dir), phase=phase, index=index, row=row)
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "case.inp").write_text(input_text, encoding="utf-8")
    completed = subprocess.run(
        [str(uvspec)], input=input_text, text=True, capture_output=True,
        check=False, timeout=180,
    )
    (case_dir / "case.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (case_dir / "case.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    metadata: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "phase": phase,
        "caseIndex": index,
        **row,
        "solverReturnCode": completed.returncode,
        "inputSha256": hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
        "rawStdoutSha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        "rawStderrSha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
        "exactVerticalEndpointRequested": is_exact_zenith(row["targetAltitudeDeg"]),
    }
    if completed.returncode != 0:
        metadata["status"] = "SOLVER_FAILED"
        (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise ZenithV32Refusal(f"uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    layers = None
    if is_exact_zenith(row["targetAltitudeDeg"]):
        layers = expected_layer_count(atmosphere_file, row["observerElevationM"])
    try:
        parsed = parse_case_outputs(
            stdout_text=completed.stdout,
            stderr_text=completed.stderr,
            target_altitude_deg=row["targetAltitudeDeg"],
            expected_layer_count_value=layers,
        )
    except Exception as exc:
        metadata["status"] = "PARSE_FAILED"
        metadata["failure"] = str(exc)
        (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    metadata.update({
        "status": "CASE_EXECUTED_AND_PARSED",
        "endpointMethod": parsed["endpointMethod"],
        "wavelengthCount": len(parsed["wavelengthNm"]),
        "expectedLayerCount": layers,
        "stdoutDirectSpectrumUsedAsEstimator": parsed.get("stdoutDirectSpectrumUsedAsEstimator", True),
    })
    (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**row, **parsed, "inputSha256": metadata["inputSha256"]}


def execute_campaign(*, root: Path, source_runtime_path: Path, uvspec: Path, data_dir: Path,
                     atmosphere_file: Path, wavelength_grid_file: Path, sed_bundle_path: Path,
                     johnson_v_path: Path, output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise ZenithV32Refusal("scientific solver execution requires explicit allow_execution=True")
    validate_frozen_case_universe()
    if sha256_file(source_runtime_path) != SOURCE_RUNTIME_SHA256:
        raise ZenithV32Refusal("source native stellar v2 runtime SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ZenithV32Refusal("AFGLUS atmosphere SHA-256 drift")
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise ZenithV32Refusal("uvspec SHA-256 drift")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise ZenithV32Refusal("frozen Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ZenithV32Refusal("frozen Johnson-V asset SHA-256 drift")
    try:
        grid_values = [int(line) for line in Path(wavelength_grid_file).read_text().splitlines() if line.strip()]
    except Exception as exc:
        raise ZenithV32Refusal("cannot read frozen wavelength grid") from exc
    if grid_values != list(WAVELENGTH_NM):
        raise ZenithV32Refusal("wavelength-grid file drift")

    source_runtime = json.loads(Path(source_runtime_path).read_text(encoding="utf-8"))
    try:
        base.validate_source_runtime(source_runtime)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)

    training_results: dict[tuple[float, float, float], dict[str, Any]] = {}
    for index, row in enumerate(build_training_cases(), start=1):
        result = execute_case(
            uvspec=uvspec,
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            row=row,
            output_dir=output_dir,
            phase="training",
            index=index,
        )
        training_results[_coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = result

    extended_runtime = build_extended_runtime(source_runtime, training_results)

    validation_results: dict[tuple[float, float, float], dict[str, Any]] = {}
    for index, row in enumerate(build_validation_cases(), start=1):
        result = execute_case(
            uvspec=uvspec,
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            row=row,
            output_dir=output_dir,
            phase="protected-holdout",
            index=index,
        )
        validation_results[_coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = result

    validation = validate_against_fresh_holdout(
        root=root,
        extended_runtime=extended_runtime,
        validation_results=validation_results,
        sed_bundle_path=sed_bundle_path,
        johnson_v_path=johnson_v_path,
    )
    extended_runtime["validation"] = {
        "status": validation["status"],
        "freshBandComparisonCount": validation["johnsonVComparisonCount"],
        "freshAtmosphericCaseCount": validation["freshValidationAtmosphericSpectrumCount"],
        "maxAbsDeltaAvMag": validation["overall"]["maxAbsDeltaAvMag"],
        "rmsDeltaAvMag": validation["overall"]["rmsDeltaAvMag"],
        "maxAbsDeltaAvMagLimit": MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": RMS_ERROR_MAG_LIMIT,
        "everyNewAltitudeIntervalPassed": all(x["passed"] for x in validation["byValidationAltitudeDeg"].values()),
        "validationStageId": STAGE_ID,
    }
    runtime_path = output_dir / "stellar-transport-v32-zenith-lut.json"
    runtime_path.write_text(json.dumps(extended_runtime, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    validation.update({
        "extendedRuntimeSha256": sha256_file(runtime_path),
        "scientificSolverExecuted": True,
        "solverInvocationCount": EXPECTED_TOTAL_SOLVER_CALLS,
        "trainingSolverInvocationCount": EXPECTED_TRAINING_SPECTRA,
        "exactVerticalTrainingSolverInvocationCount": EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA,
        "belowZenithSdisortTrainingSolverInvocationCount": EXPECTED_SDISORT_TRAINING_SPECTRA,
        "protectedHoldoutSolverInvocationCount": EXPECTED_PROTECTED_HOLDOUT_SPECTRA,
        "randomNumbersUsed": False,
    })
    validation_path = output_dir / "native-stellar-zenith-v32-validation.json"
    validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return validation


def review_summary() -> dict[str, Any]:
    validate_frozen_case_universe()
    return {
        "stageId": STAGE_ID,
        "methodVersion": METHOD_VERSION,
        "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
        "trainingSpectrumCount": EXPECTED_TRAINING_SPECTRA,
        "exactVerticalTrainingSpectrumCount": EXPECTED_EXACT_VERTICAL_TRAINING_SPECTRA,
        "belowZenithSdisortTrainingSpectrumCount": EXPECTED_SDISORT_TRAINING_SPECTRA,
        "protectedHoldoutSpectrumCount": EXPECTED_PROTECTED_HOLDOUT_SPECTRA,
        "johnsonVComparisonCount": EXPECTED_JOHNSON_V_COMPARISONS,
        "maxAbsDeltaAvMagLimit": MAX_ABS_ERROR_MAG_LIMIT,
        "rmsDeltaAvMagLimit": RMS_ERROR_MAG_LIMIT,
        "exactVerticalAnalysisRunId": EXACT_VERTICAL_ANALYSIS_RUN_ID,
        "exactVerticalAnalysisArtifactId": EXACT_VERTICAL_ANALYSIS_ARTIFACT_ID,
        "positiveEpsilonSubstitutionUsed": False,
        "productionAuthorized": False,
        "protectedHoldoutOpeningAuthorizedByReviewModule": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-runtime", type=Path)
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(review_summary(), sort_keys=True))
        return 0
    required = {
        "source_runtime": args.source_runtime,
        "uvspec": args.uvspec,
        "data_dir": args.data_dir,
        "atmosphere_file": args.atmosphere_file,
        "wavelength_grid_file": args.wavelength_grid_file,
        "sed_bundle": args.sed_bundle,
        "johnson_v": args.johnson_v,
        "output_dir": args.output_dir,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ZenithV32Refusal(f"missing execution arguments: {missing}")
    result = execute_campaign(
        root=args.root,
        source_runtime_path=args.source_runtime,
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v,
        output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({
        "stageId": result["stageId"],
        "status": result["status"],
        "solverInvocationCount": result["solverInvocationCount"],
        "overall": result["overall"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
