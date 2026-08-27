#!/usr/bin/env python3
"""Native stellar zenith v3.2 exact-vertical endpoint training.

Reuses the immutable 75 successful v3.1 non-zenith training spectra and
executes only the 25 exact-90 training knots with the independently validated
exact-vertical DISORT optical-column method. Protected holdouts are not read or
executed here.
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


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load(HERE / "native_stellar_zenith_v3.py", "native_zenith_v3_base_for_v32")
v31 = _load(HERE / "native_stellar_zenith_v31.py", "native_zenith_v31_source_for_v32")
ev_v1 = _load(HERE / "diagnose_exact_vertical_optical_column_v1.py", "exact_vertical_v1_for_v32")
ev_r2 = _load(HERE / "analyze_exact_vertical_optical_column_recovery2.py", "exact_vertical_recovery2_for_v32")

STAGE_ID = "native-stellar-zenith-v3.2-endpoint-training-v1"
METHOD_VERSION = "stellar-transport-v3.2-exact-vertical-endpoint"
MYSTIC_STATE = base.MYSTIC_STATE

SOURCE_V31_RUN_ID = 33035467761
SOURCE_V31_DISPATCH_SHA = "2a6f6eadb003ea70c99e0c306f232a6233650a0e"
SOURCE_V31_ARTIFACT_ID = 9631872858
SOURCE_V31_ARTIFACT_DIGEST = "sha256:dd8cbf6c00fdcf34041fb61e43d0f97d43646a5d2bdaf5a2ef899ed1a40f078b"
SOURCE_V31_ARTIFACT_NAME = "native-stellar-zenith-v31-recovery2-33035467761"

EXACT_VERTICAL_VALIDATION_RUN_ID = 33041830554
EXACT_VERTICAL_VALIDATION_DISPATCH_SHA = "bdac3f0f03f1d2c63d274076365f1f3331a8b68e"
EXACT_VERTICAL_VALIDATION_ARTIFACT_ID = 9634148868
EXACT_VERTICAL_VALIDATION_ARTIFACT_DIGEST = "sha256:aa5b0b4a5b705bdcefd29c35113f331aa667b8dca9a2b228d44aa52ec864ca78"
EXACT_VERTICAL_VALIDATION_ARTIFACT_NAME = "native-stellar-zenith-exact-vertical-optical-column-analysis-recovery2-33041830554"

SOURCE_RUNTIME_SHA256 = base.SOURCE_RUNTIME_SHA256
SOURCE_SED_SHA256 = base.SOURCE_SED_SHA256
SOURCE_JOHNSON_V_SHA256 = base.SOURCE_JOHNSON_V_SHA256
UVSPEC_SHA256 = base.UVSPEC_SHA256
UVSPEC_HELP_SHA256 = base.UVSPEC_HELP_SHA256
AFGLUS_SHA256 = base.AFGLUS_SHA256
WAVELENGTH_NM = base.WAVELENGTH_NM
ELEVATION_KNOTS_M = base.ELEVATION_KNOTS_M
AOD_KNOTS = base.AOD_KNOTS
REUSED_ALTITUDE_DEG = (82.5, 85.0, 87.5)
EXACT_ENDPOINT_ALTITUDE_DEG = 90.0
EXPECTED_REUSED_SPECTRUM_COUNT = 75
EXPECTED_EXACT_ENDPOINT_SPECTRUM_COUNT = 25
EXPECTED_TOTAL_NEW_TRAINING_SPECTRUM_COUNT = 100

STDOUT_STDERR_FLUX_TOLERANCE = ev_r2.STDOUT_STDERR_FLUX_TOLERANCE
MAX_ABS_DELTA_TAU = ev_v1.MAX_ABS_DELTA_TAU
MAX_ABS_DELTA_AV_MAG = ev_v1.MAX_ABS_DELTA_AV_MAG
KNOT_REPRODUCTION_TOLERANCE = 1.0e-12
ENDPOINT_MONOTONIC_SLACK = 1.0e-10
SEAM_PROBE_COUNT = 101


class ZenithV32Refusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def finite(label: str, value: object) -> float:
    try:
        return base.finite(label, value)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc


def coord_key(h: float, e: float, a: float) -> tuple[float, float, float]:
    return base._coord_key(h, e, a)


def exact90_training_cases() -> list[dict[str, float]]:
    return [
        {"targetAltitudeDeg": 90.0, "observerElevationM": float(e), "aod550": float(a)}
        for e in ELEVATION_KNOTS_M for a in AOD_KNOTS
    ]


def reused_training_coordinates() -> set[tuple[float, float, float]]:
    return {
        coord_key(h, e, a)
        for h in REUSED_ALTITUDE_DEG for e in ELEVATION_KNOTS_M for a in AOD_KNOTS
    }


def validate_frozen_training_universe() -> None:
    base.validate_frozen_case_universe()
    if tuple(base.NEW_TRAINING_ALTITUDE_DEG) != (82.5, 85.0, 87.5, 90.0):
        raise ZenithV32Refusal("v3.2 training altitude universe drift")
    if len(reused_training_coordinates()) != EXPECTED_REUSED_SPECTRUM_COUNT:
        raise ZenithV32Refusal("reused non-zenith training universe drift")
    exact = {coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in exact90_training_cases()}
    if len(exact) != EXPECTED_EXACT_ENDPOINT_SPECTRUM_COUNT:
        raise ZenithV32Refusal("exact-90 training universe drift")
    if reused_training_coordinates() & exact:
        raise ZenithV32Refusal("reused and exact-endpoint universes overlap unexpectedly")
    if reused_training_coordinates() | exact != {
        coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"])
        for r in base.build_training_cases()
    }:
        raise ZenithV32Refusal("v3.2 does not exactly cover frozen 100-case training universe")


def validate_exact_vertical_validation_artifact(source_root: Path) -> dict[str, Any]:
    path = Path(source_root) / "exact-vertical-optical-column-analysis-recovery2-summary.json"
    if not path.is_file():
        raise ZenithV32Refusal("exact-vertical validation summary missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("stageId") != ev_r2.STAGE_ID:
        raise ZenithV32Refusal("exact-vertical validation stage drift")
    if data.get("status") != "EXACT_VERTICAL_OPTICAL_COLUMN_ANALYSIS_RECOVERY2_PASS":
        raise ZenithV32Refusal("exact-vertical endpoint method has not passed its validation")
    p = data.get("parserEvidenceGate") or {}
    g = data.get("scientificGates") or {}
    if p.get("passed") is not True or finite("validation flux delta", p.get("maxStdoutStderrDirectFluxAbsDelta")) > STDOUT_STDERR_FLUX_TOLERANCE:
        raise ZenithV32Refusal("exact-vertical parser-evidence gate drift")
    if g.get("spectralOpticalColumnPassed") is not True or finite("validation tau delta", g.get("maxAbsDeltaOpticalDepth")) > MAX_ABS_DELTA_TAU:
        raise ZenithV32Refusal("exact-vertical optical-depth validation gate drift")
    if g.get("johnsonVConsequencePassed") is not True or finite("validation Johnson-V delta", g.get("maxAbsDeltaAvMag")) > MAX_ABS_DELTA_AV_MAG:
        raise ZenithV32Refusal("exact-vertical Johnson-V validation gate drift")
    cb = data.get("claimBoundary") or {}
    if cb.get("protectedHoldoutOpened") is not False or cb.get("productionAuthorized") is not False:
        raise ZenithV32Refusal("exact-vertical validation claim boundary drift")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "status": data["status"],
        "maxAbsDeltaOpticalDepth": g["maxAbsDeltaOpticalDepth"],
        "maxAbsDeltaAvMag": g["maxAbsDeltaAvMag"],
        "maxStdoutStderrDirectFluxAbsDelta": p["maxStdoutStderrDirectFluxAbsDelta"],
    }


def _verify_case_file_hash(case: dict[str, Any], case_dir: Path, key: str, filename: str) -> None:
    expected = case.get(key)
    path = case_dir / filename
    if not isinstance(expected, str) or not path.is_file() or sha256_file(path) != expected:
        raise ZenithV32Refusal(f"v3.1 source case {case_dir.name} {filename} hash drift")


def _parse_reused_input(text: str, expected_h: float, expected_e: float, expected_a: float) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    required = {
        f"sza {90.0 - expected_h:.8f}",
        "rte_solver sdisort",
        "sdisort nscat 1",
        "output_quantity transmittance",
        "output_user lambda edir",
        "zout 0.000000",
        f"aerosol_set_tau_at_wvl 550 {expected_a:.8f}",
    }
    missing = sorted(required - set(lines))
    if missing:
        raise ZenithV32Refusal(f"v3.1 reused input drift: {missing}")
    grid_lines = [line for line in lines if line.startswith("atm_z_grid ")]
    if len(grid_lines) != 1:
        raise ZenithV32Refusal("v3.1 reused atm_z_grid ambiguity")
    grid = [finite("reused atm_z_grid", x) for x in grid_lines[0].split()[1:]]
    if abs(grid[0] * 1000.0 - expected_e) > 1e-6:
        raise ZenithV32Refusal("v3.1 reused observer elevation drift")


def load_reused_v31_training(source_root: Path) -> tuple[dict[tuple[float, float, float], dict[str, Any]], dict[str, Any]]:
    source_root = Path(source_root)
    campaign_path = source_root / "campaign.json"
    case_root = source_root / "cases"
    if not campaign_path.is_file() or not case_root.is_dir():
        raise ZenithV32Refusal("v3.1 source artifact structure missing")
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    if campaign.get("stageId") != "native-stellar-zenith-v3.1" or campaign.get("methodVersion") != "stellar-transport-v3.1-zenith-limit":
        raise ZenithV32Refusal("v3.1 source campaign identity drift")
    if campaign.get("trainingSpectrumCount") != 100 or campaign.get("freshValidationSpectrumCount") != 64:
        raise ZenithV32Refusal("v3.1 frozen design count drift")

    results: dict[tuple[float, float, float], dict[str, Any]] = {}
    failed_exact90: list[dict[str, Any]] = []
    all_dirs = sorted(p for p in case_root.iterdir() if p.is_dir())
    if len(all_dirs) != 76:
        raise ZenithV32Refusal(f"v3.1 source artifact must contain exactly 76 case directories, got {len(all_dirs)}")
    for case_dir in all_dirs:
        meta_path = case_dir / "case.json"
        if not meta_path.is_file():
            raise ZenithV32Refusal(f"v3.1 source metadata missing: {case_dir.name}")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("stageId") != "native-stellar-zenith-v3.1" or meta.get("phase") != "training":
            raise ZenithV32Refusal("v3.1 source case stage/phase drift")
        h = finite("source target altitude", meta.get("physicalTargetAltitudeDeg"))
        e = finite("source observer elevation", meta.get("observerElevationM"))
        a = finite("source AOD", meta.get("aod550"))
        if h == 90.0:
            failed_exact90.append({"dir": case_dir.name, "meta": meta})
            continue
        if h not in REUSED_ALTITUDE_DEG:
            raise ZenithV32Refusal(f"unexpected v3.1 source altitude {h}")
        key = coord_key(h, e, a)
        if key not in reused_training_coordinates() or key in results:
            raise ZenithV32Refusal("v3.1 reused coordinate missing, duplicated, or drifted")
        if meta.get("status") != "CASE_EXECUTED_AND_PARSED" or meta.get("wavelengthCount") != 401:
            raise ZenithV32Refusal(f"v3.1 source case not successfully parsed: {case_dir.name}")
        if meta.get("zenithLimitRegularizationApplied") is not False:
            raise ZenithV32Refusal("non-zenith reused case unexpectedly used zenith regularization")
        _verify_case_file_hash(meta, case_dir, "inputSha256", "case.inp")
        _verify_case_file_hash(meta, case_dir, "rawStdoutSha256", "case.stdout.txt")
        _verify_case_file_hash(meta, case_dir, "rawStderrSha256", "case.stderr.txt")
        input_text = (case_dir / "case.inp").read_text(encoding="utf-8")
        _parse_reused_input(input_text, h, e, a)
        try:
            parsed = v31.parse_direct_transmission(
                (case_dir / "case.stdout.txt").read_text(encoding="utf-8"),
                target_altitude_deg=h,
            )
        except Exception as exc:
            raise ZenithV32Refusal(f"v3.1 reused parser failed for {case_dir.name}: {exc}") from exc
        if parsed.get("zenithLimitRegularizationApplied") is not False:
            raise ZenithV32Refusal("v3.1 source parser provenance drift")
        results[key] = {
            "targetAltitudeDeg": h,
            "observerElevationM": e,
            "aod550": a,
            "wavelengthNm": parsed["wavelengthNm"],
            "lineOfSightDirectTransmission": parsed["lineOfSightDirectTransmission"],
            "directOpticalDepth": parsed["directOpticalDepth"],
            "sourceCaseDirectory": case_dir.name,
            "sourceCaseMetadataSha256": sha256_file(meta_path),
            "sourceStdoutSha256": meta["rawStdoutSha256"],
        }
    if set(results) != reused_training_coordinates():
        raise ZenithV32Refusal("v3.1 reusable 75-case universe incomplete")
    if len(failed_exact90) != 1:
        raise ZenithV32Refusal("v3.1 source must preserve exactly one failed 90-degree attempt")
    fail = failed_exact90[0]
    meta = fail["meta"]
    failed_dir = case_root / fail["dir"]
    _verify_case_file_hash(meta, failed_dir, "inputSha256", "case.inp")
    _verify_case_file_hash(meta, failed_dir, "rawStdoutSha256", "case.stdout.txt")
    _verify_case_file_hash(meta, failed_dir, "rawStderrSha256", "case.stderr.txt")
    if meta.get("status") != "PARSE_FAILED" or meta.get("solverSourceZenithAngleDeg") != 0.001:
        raise ZenithV32Refusal("v3.1 failed exact-90 source evidence drift")
    if (failed_dir / "case.stdout.txt").read_text(encoding="utf-8").strip():
        raise ZenithV32Refusal("v3.1 failed exact-90 source unexpectedly has a spectrum")
    if "Does not work for umu0=1.0" not in (failed_dir / "case.stderr.txt").read_text(encoding="utf-8"):
        raise ZenithV32Refusal("v3.1 exact-90 failure message drift")
    evidence = {
        "campaignSha256": sha256_file(campaign_path),
        "reusedSpectrumCount": len(results),
        "reusedAltitudeCounts": {
            str(h): sum(1 for key in results if key[0] == h) for h in REUSED_ALTITUDE_DEG
        },
        "preservedFailedExact90CaseDirectory": fail["dir"],
        "preservedFailedExact90MetadataSha256": sha256_file(failed_dir / "case.json"),
    }
    return results, evidence


def render_exact90_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                         observer_elevation_m: float, aod550: float) -> str:
    e = finite("observerElevationM", observer_elevation_m)
    a = finite("aod550", aod550)
    if e not in ELEVATION_KNOTS_M or a not in AOD_KNOTS:
        raise ZenithV32Refusal("exact-90 renderer restricted to frozen training knots")
    grid = base.elevated_site_grid_ascending(atmosphere_file, e)
    solar_source = Path(data_dir).resolve() / "solar_flux" / "atlas_plus_modtran"
    wavelength_grid = Path(wavelength_grid_file).resolve(strict=True)
    lines = [
        f"data_files_path {Path(data_dir).resolve()}",
        f"atmosphere_file {Path(atmosphere_file).resolve()}",
        f"source solar {solar_source}",
        f"mol_abs_param {base.MOL_ABS_PARAM}",
        f"wavelength_grid_file {wavelength_grid}",
        f"wavelength {WAVELENGTH_NM[0]} {WAVELENGTH_NM[-1]}",
        "sza 0.00000000",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {base.SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {a:.8f}",
        "rte_solver disort",
        "number_of_streams 16",
        "output_quantity transmittance",
        "output_user lambda edir",
        "verbose",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    for forbidden in (
        "rte_solver sdisort", "sdisort nscat", "rte_solver mystic", "mc_",
        "write_optical_properties", "altitude ", "mc_elevation_file", "angstrom",
    ):
        if forbidden in lower:
            raise ZenithV32Refusal(f"forbidden exact-90 directive emitted: {forbidden}")
    return text


def _safe(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".").replace("-", "m").replace(".", "p")


def execute_exact90_case(*, root: Path, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                         wavelength_grid_file: Path, sed_bundle_path: Path, johnson_v_path: Path,
                         row: dict[str, float], output_dir: Path, index: int) -> dict[str, Any]:
    e, a = row["observerElevationM"], row["aod550"]
    case_dir = Path(output_dir) / "exact90-cases" / f"exact90-{index:02d}-e{_safe(e)}-a{_safe(a)}"
    case_dir.mkdir(parents=True, exist_ok=False)
    input_text = render_exact90_input(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
        observer_elevation_m=e,
        aod550=a,
    )
    input_path = case_dir / "case.inp"
    input_path.write_text(input_text, encoding="utf-8")
    completed = subprocess.run(
        [str(uvspec)], input=input_text, text=True, capture_output=True, check=False,
        timeout=300, cwd=case_dir,
    )
    stdout_path = case_dir / "case.stdout.txt"
    stderr_path = case_dir / "case.stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    metadata: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "caseIndex": index,
        "targetAltitudeDeg": 90.0,
        "observerElevationM": e,
        "aod550": a,
        "solver": "disort",
        "solverSourceZenithAngleDeg": 0.0,
        "solverReturnCode": completed.returncode,
        "inputSha256": sha256_file(input_path),
        "rawStdoutSha256": sha256_file(stdout_path),
        "rawStderrSha256": sha256_file(stderr_path),
    }
    if completed.returncode != 0:
        metadata["status"] = "SOLVER_FAILED"
        (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise ZenithV32Refusal(f"exact-90 uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    try:
        dense = ev_r2.parse_dense_direct_transmission(completed.stdout)
        stderr_direct = ev_r2.parse_stderr_direct_flux(completed.stderr)
        crosscheck = ev_r2.crosscheck_selected_stdout_against_stderr(dense, stderr_direct)
        if crosscheck.get("passed") is not True:
            raise ZenithV32Refusal("exact-90 stdout/stderr direct-flux crosscheck failed")
        layer_count = len(base.elevated_site_grid_ascending(atmosphere_file, e)) - 1
        verbose = ev_v1.parse_verbose_optical_columns(completed.stderr, expected_layer_count=layer_count)
        metrics = ev_v1.evaluate_case(
            root=root,
            parsed_direct={
                "wavelengthNm": dense["wavelengthNm"],
                "directOpticalDepth": dense["directOpticalDepth"],
            },
            parsed_verbose=verbose,
            sed_bundle_path=sed_bundle_path,
            johnson_v_path=johnson_v_path,
        )
        if metrics.get("spectralOpticalColumnPassed") is not True or metrics["maxAbsDeltaOpticalDepth"] > MAX_ABS_DELTA_TAU:
            raise ZenithV32Refusal("exact-90 optical-column gate failed")
        if metrics.get("johnsonVConsequencePassed") is not True or metrics["maxAbsDeltaAvMag"] > MAX_ABS_DELTA_AV_MAG:
            raise ZenithV32Refusal("exact-90 Johnson-V internal-consistency gate failed")
    except Exception as exc:
        metadata["status"] = "POST_SOLVER_GATE_FAILED"
        metadata["failure"] = str(exc)
        (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    result = {
        "targetAltitudeDeg": 90.0,
        "observerElevationM": e,
        "aod550": a,
        "wavelengthNm": dense["wavelengthNm"],
        "lineOfSightDirectTransmission": dense["directTransmission"],
        "directOpticalDepth": dense["directOpticalDepth"],
        "stdoutStderrDirectFluxCrosscheck": crosscheck,
        "internalConsistencyMetrics": metrics,
        "expectedLayerCount": layer_count,
        "sourceCaseDirectory": case_dir.name,
    }
    result_path = case_dir / "parsed-result.json"
    result_path.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    metadata.update({
        "status": "CASE_EXECUTED_PARSED_AND_GATED",
        "wavelengthCount": 401,
        "parsedResultSha256": sha256_file(result_path),
        "stdoutStderrMaxAbsDeltaTransmission": crosscheck["maxAbsDeltaTransmission"],
        "maxAbsDeltaOpticalDepth": metrics["maxAbsDeltaOpticalDepth"],
        "maxAbsDeltaAvMag": metrics["maxAbsDeltaAvMag"],
    })
    (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def build_v32_training_runtime(source_runtime: dict[str, Any],
                               reused_results: dict[tuple[float, float, float], dict[str, Any]],
                               exact90_results: dict[tuple[float, float, float], dict[str, Any]]) -> dict[str, Any]:
    validate_frozen_training_universe()
    training = dict(reused_results)
    overlap = set(training) & set(exact90_results)
    if overlap:
        raise ZenithV32Refusal("v3.2 training source overlap")
    training.update(exact90_results)
    expected = {
        coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"])
        for r in base.build_training_cases()
    }
    if set(training) != expected:
        raise ZenithV32Refusal("v3.2 100-case training universe incomplete")
    try:
        runtime = base.build_extended_runtime(source_runtime, training)
    except Exception as exc:
        raise ZenithV32Refusal(str(exc)) from exc
    runtime["representation"] = {
        **(runtime.get("representation") or {}),
        "version": METHOD_VERSION,
        "exactZenithEndpointMethod": "DISORT_EXACT_VERTICAL_OPTICAL_COLUMN_VALIDATED",
        "nonZenithTrainingMethod": "IMMUTABLE_V31_SDISORT_NSCAT1_REUSE",
        "targetAltitudeCoordinate": "cosecant-altitude-1-over-sin-h",
    }
    runtime["provenance"] = {
        **(runtime.get("provenance") or {}),
        "zenithExtensionStageId": STAGE_ID,
        "methodVersion": METHOD_VERSION,
        "sourceV31RunId": SOURCE_V31_RUN_ID,
        "sourceV31DispatchSha": SOURCE_V31_DISPATCH_SHA,
        "sourceV31ArtifactId": SOURCE_V31_ARTIFACT_ID,
        "sourceV31ArtifactDigest": SOURCE_V31_ARTIFACT_DIGEST,
        "reusedNonZenithTrainingSpectrumCount": 75,
        "newExactZenithTrainingSpectrumCount": 25,
        "exactVerticalValidationRunId": EXACT_VERTICAL_VALIDATION_RUN_ID,
        "exactVerticalValidationArtifactId": EXACT_VERTICAL_VALIDATION_ARTIFACT_ID,
        "exactVerticalValidationArtifactDigest": EXACT_VERTICAL_VALIDATION_ARTIFACT_DIGEST,
        "tiltedSdisortDisortInterchangeabilityClaimed": False,
        "epsilonApproximationUsedAtExactZenith": False,
        "protectedHoldoutOpened": False,
        "productionAuthorized": False,
        "postResultRetuningPerformed": False,
    }
    if runtime["directOpticalDepth"][:675] != source_runtime["directOpticalDepth"]:
        raise ZenithV32Refusal("source v2 spectra changed in v3.2 training runtime")
    return runtime


def structural_seam_validation(runtime: dict[str, Any], source_runtime: dict[str, Any],
                               training_results: dict[tuple[float, float, float], dict[str, Any]]) -> dict[str, Any]:
    if runtime["directOpticalDepth"][:675] != source_runtime["directOpticalDepth"]:
        raise ZenithV32Refusal("v2 no-regression gate failed")
    max_knot_delta = 0.0
    endpoint_order_violations = 0
    overshoot_violations = 0
    nonfinite_or_negative = 0
    extrapolation_residuals: list[float] = []
    max_endpoint_span = 0.0
    probes = [87.5 + (90.0 - 87.5) * i / (SEAM_PROBE_COUNT - 1) for i in range(SEAM_PROBE_COUNT)]
    for e in ELEVATION_KNOTS_M:
        for a in AOD_KNOTS:
            tau85 = training_results[coord_key(85.0, e, a)]["directOpticalDepth"]
            tau875 = training_results[coord_key(87.5, e, a)]["directOpticalDepth"]
            tau90 = training_results[coord_key(90.0, e, a)]["directOpticalDepth"]
            pred875 = base.interpolate_optical_depth(runtime, target_altitude_deg=87.5, observer_elevation_m=e, aod550=a)
            pred90 = base.interpolate_optical_depth(runtime, target_altitude_deg=90.0, observer_elevation_m=e, aod550=a)
            max_knot_delta = max(
                max_knot_delta,
                max(abs(float(x) - float(y)) for x, y in zip(pred875, tau875, strict=True)),
                max(abs(float(x) - float(y)) for x, y in zip(pred90, tau90, strict=True)),
            )
            x85, x875, x90 = base.csc_altitude(85.0), base.csc_altitude(87.5), 1.0
            for t85, t875, t90 in zip(tau85, tau875, tau90, strict=True):
                t85, t875, t90 = float(t85), float(t875), float(t90)
                if not all(math.isfinite(x) and x >= 0.0 for x in (t85, t875, t90)):
                    nonfinite_or_negative += 1
                    continue
                if t90 > t875 + ENDPOINT_MONOTONIC_SLACK:
                    endpoint_order_violations += 1
                max_endpoint_span = max(max_endpoint_span, abs(t875 - t90))
                extrapolated = t875 + (t875 - t85) * (x90 - x875) / (x875 - x85)
                extrapolation_residuals.append(t90 - extrapolated)
            for h in probes:
                tau = base.interpolate_optical_depth(runtime, target_altitude_deg=h, observer_elevation_m=e, aod550=a)
                for value, lo, hi in zip(tau, tau90, tau875, strict=True):
                    value, lo, hi = float(value), float(lo), float(hi)
                    if not math.isfinite(value) or value < 0.0:
                        nonfinite_or_negative += 1
                    lower, upper = min(lo, hi) - KNOT_REPRODUCTION_TOLERANCE, max(lo, hi) + KNOT_REPRODUCTION_TOLERANCE
                    if value < lower or value > upper:
                        overshoot_violations += 1
    max_extrap = max(abs(x) for x in extrapolation_residuals)
    rms_extrap = math.sqrt(sum(x * x for x in extrapolation_residuals) / len(extrapolation_residuals))
    passed = (
        max_knot_delta <= KNOT_REPRODUCTION_TOLERANCE
        and endpoint_order_violations == 0
        and overshoot_violations == 0
        and nonfinite_or_negative == 0
    )
    return {
        "status": "V32_TRAINING_STRUCTURAL_SEAM_PASS" if passed else "V32_TRAINING_STRUCTURAL_SEAM_FAIL",
        "passed": passed,
        "probeCountPerAtmosphere": SEAM_PROBE_COUNT,
        "atmosphereCount": len(ELEVATION_KNOTS_M) * len(AOD_KNOTS),
        "maxKnotReproductionAbsDeltaOpticalDepth": max_knot_delta,
        "knotReproductionTolerance": KNOT_REPRODUCTION_TOLERANCE,
        "endpointMonotonicSlack": ENDPOINT_MONOTONIC_SLACK,
        "endpointOrderingViolationCount": endpoint_order_violations,
        "overshootViolationCount": overshoot_violations,
        "nonfiniteOrNegativeCount": nonfinite_or_negative,
        "maxEndpointTauSpan87p5To90": max_endpoint_span,
        "diagnosticOnlyExact90VsCscExtrapolationFrom85And87p5": {
            "acceptanceThresholdApplied": False,
            "maxAbsDeltaOpticalDepth": max_extrap,
            "rmsDeltaOpticalDepth": rms_extrap,
            "postResultThresholdMayBeInvented": False,
        },
        "protectedHoldoutOpened": False,
    }


def execute_campaign(*, root: Path, source_runtime_path: Path, source_v31_root: Path,
                     exact_vertical_validation_root: Path, uvspec: Path, data_dir: Path,
                     atmosphere_file: Path, wavelength_grid_file: Path, sed_bundle_path: Path,
                     johnson_v_path: Path, output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise ZenithV32Refusal("exact-90 training execution requires explicit allow_execution=True")
    validate_frozen_training_universe()
    if sha256_file(source_runtime_path) != SOURCE_RUNTIME_SHA256:
        raise ZenithV32Refusal("source v2 runtime SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ZenithV32Refusal("AFGLUS SHA-256 drift")
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise ZenithV32Refusal("uvspec SHA-256 drift")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256 or sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ZenithV32Refusal("frozen photometry asset SHA-256 drift")
    grid_values = [int(line) for line in Path(wavelength_grid_file).read_text().splitlines() if line.strip()]
    if grid_values != list(WAVELENGTH_NM):
        raise ZenithV32Refusal("wavelength-grid file drift")
    endpoint_validation = validate_exact_vertical_validation_artifact(exact_vertical_validation_root)
    reused, reused_evidence = load_reused_v31_training(source_v31_root)
    source_runtime = json.loads(Path(source_runtime_path).read_text(encoding="utf-8"))
    base.validate_source_runtime(source_runtime)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    exact_results: dict[tuple[float, float, float], dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for index, row in enumerate(exact90_training_cases(), start=1):
        try:
            result = execute_exact90_case(
                root=root,
                uvspec=uvspec,
                data_dir=data_dir,
                atmosphere_file=atmosphere_file,
                wavelength_grid_file=wavelength_grid_file,
                sed_bundle_path=sed_bundle_path,
                johnson_v_path=johnson_v_path,
                row=row,
                output_dir=output_dir,
                index=index,
            )
            exact_results[coord_key(90.0, row["observerElevationM"], row["aod550"])] = result
        except Exception as exc:
            failures.append({**row, "caseIndex": index, "failure": str(exc)})
    campaign: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "methodVersion": METHOD_VERSION,
        "sourceV31": {
            "runId": SOURCE_V31_RUN_ID,
            "dispatchSha": SOURCE_V31_DISPATCH_SHA,
            "artifactId": SOURCE_V31_ARTIFACT_ID,
            "artifactDigest": SOURCE_V31_ARTIFACT_DIGEST,
            **reused_evidence,
        },
        "exactVerticalMethodValidation": {
            "runId": EXACT_VERTICAL_VALIDATION_RUN_ID,
            "dispatchSha": EXACT_VERTICAL_VALIDATION_DISPATCH_SHA,
            "artifactId": EXACT_VERTICAL_VALIDATION_ARTIFACT_ID,
            "artifactDigest": EXACT_VERTICAL_VALIDATION_ARTIFACT_DIGEST,
            **endpoint_validation,
        },
        "reusedNonZenithTrainingSpectrumCount": len(reused),
        "newExactZenithSolverInvocationCount": 25,
        "successfulExactZenithTrainingSpectrumCount": len(exact_results),
        "failures": failures,
        "protectedHoldoutOpened": False,
        "productionAuthorized": False,
    }
    if failures or len(exact_results) != 25:
        campaign["status"] = "V32_ENDPOINT_TRAINING_FAIL"
        (output_dir / "native-stellar-zenith-v32-endpoint-training.json").write_text(
            json.dumps(campaign, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        raise ZenithV32Refusal(json.dumps({"endpointTrainingFailed": campaign}, sort_keys=True))

    training = dict(reused)
    training.update(exact_results)
    runtime = build_v32_training_runtime(source_runtime, reused, exact_results)
    seam = structural_seam_validation(runtime, source_runtime, training)
    if seam["passed"] is not True:
        campaign["status"] = "V32_ENDPOINT_TRAINING_SEAM_FAIL"
        campaign["structuralSeam"] = seam
        (output_dir / "native-stellar-zenith-v32-endpoint-training.json").write_text(
            json.dumps(campaign, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        raise ZenithV32Refusal(json.dumps({"structuralSeamFailed": seam}, sort_keys=True))

    runtime_path = output_dir / "stellar-transport-v32-training-lut.json"
    runtime_path.write_text(json.dumps(runtime, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    exact_metrics = [row["internalConsistencyMetrics"] for row in exact_results.values()]
    cross = [row["stdoutStderrDirectFluxCrosscheck"] for row in exact_results.values()]
    campaign.update({
        "status": "V32_ENDPOINT_TRAINING_AND_STRUCTURAL_SEAM_PASS",
        "trainingRuntimeSha256": sha256_file(runtime_path),
        "trainingRuntimeSpectrumCount": len(runtime["directOpticalDepth"]),
        "maxExact90StdoutStderrDirectFluxAbsDelta": max(x["maxAbsDeltaTransmission"] for x in cross),
        "maxExact90AbsDeltaOpticalDepth": max(x["maxAbsDeltaOpticalDepth"] for x in exact_metrics),
        "maxExact90AbsDeltaAvMag": max(x["maxAbsDeltaAvMag"] for x in exact_metrics),
        "exact90Gates": {
            "stdoutStderrFluxLimit": STDOUT_STDERR_FLUX_TOLERANCE,
            "maxAbsDeltaOpticalDepthLimit": MAX_ABS_DELTA_TAU,
            "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
            "all25Passed": True,
        },
        "structuralSeam": seam,
        "claimBoundary": {
            "trainingOnly": True,
            "protectedHoldoutOpened": False,
            "computationalReferenceValidationComplete": False,
            "holdoutAuthorizationPermittedAfterSeparateReview": True,
            "productionAuthorized": False,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
            "postResultRetuningPerformed": False,
        },
    })
    summary_path = output_dir / "native-stellar-zenith-v32-endpoint-training.json"
    summary_path.write_text(json.dumps(campaign, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return {"runtimePath": str(runtime_path), "summaryPath": str(summary_path), "summary": campaign}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-runtime", type=Path)
    parser.add_argument("--source-v31-root", type=Path)
    parser.add_argument("--exact-vertical-validation-root", type=Path)
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        validate_frozen_training_universe()
        print(json.dumps({
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "stageId": STAGE_ID,
            "reusedNonZenithTrainingSpectrumCount": 75,
            "newExactZenithTrainingSpectrumCount": 25,
            "newSolverInvocationCount": 25,
            "protectedHoldoutSpectrumCountOpened": 0,
            "protectedHoldoutOpeningAuthorized": False,
            "maxAbsDeltaOpticalDepthLimit": MAX_ABS_DELTA_TAU,
            "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
            "stdoutStderrFluxLimit": STDOUT_STDERR_FLUX_TOLERANCE,
        }, sort_keys=True))
        return 0
    required = [
        args.source_runtime, args.source_v31_root, args.exact_vertical_validation_root,
        args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file,
        args.sed_bundle, args.johnson_v, args.output_dir,
    ]
    if any(x is None for x in required):
        raise ZenithV32Refusal("execution requires all explicit bound inputs")
    result = execute_campaign(
        root=args.root,
        source_runtime_path=args.source_runtime,
        source_v31_root=args.source_v31_root,
        exact_vertical_validation_root=args.exact_vertical_validation_root,
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
        "status": result["summary"]["status"],
        "trainingRuntimeSha256": result["summary"]["trainingRuntimeSha256"],
        "maxExact90AbsDeltaOpticalDepth": result["summary"]["maxExact90AbsDeltaOpticalDepth"],
        "maxExact90AbsDeltaAvMag": result["summary"]["maxExact90AbsDeltaAvMag"],
        "structuralSeam": result["summary"]["structuralSeam"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
