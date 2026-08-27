#!/usr/bin/env python3
"""Native MYSTIC-STATE-0081 stellar-transport zenith extension v3.1.

This module preserves the preregistered v3 training/validation universe and all
acceptance gates.  It changes exactly one numerical convention discovered by
an independently frozen one-case diagnostic: SDISORT 2.0.6 returns no spectrum
for exact ``umu0=1.0`` and writes ``Error,  Does not work for umu0=1.0``.

The physical target-altitude axis still ends at exactly 90 degrees.  Only the
solver representation of a physical 90-degree ray is regularized to
``sza=0.001 deg`` (solver altitude 89.999 deg).  The parser divides ``edir`` by
the matching solver ``mu0=cos(0.001 deg)``.  The relative plane-parallel
airmass excess versus exact vertical is <2e-10.

No training coordinate, protected holdout coordinate, threshold, atmosphere,
photometric asset, interpolation coordinate, or pre-80-degree runtime value is
changed.  This is computational direct-stellar-transport validation only; it
does not authorize production or claim real-sky / human first-seeing
validation.
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


def _load_base():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_base_for_v31", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen native stellar zenith v3 base")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()

STAGE_ID = "native-stellar-zenith-v3.1"
METHOD_VERSION = "stellar-transport-v3.1-zenith-limit"
MYSTIC_STATE = base.MYSTIC_STATE
ZENITH_LIMIT_SZA_DEG = 0.001
ZENITH_LIMIT_PHYSICAL_ALTITUDE_DEG = 90.0
ZENITH_LIMIT_RELATIVE_AIRMASS_EXCESS_MAX = 2.0e-10
FAILED_V3_RUN_ID = 33033742217
EXACT90_DIAGNOSTIC_RUN_ID = 33034345605
EXACT90_DIAGNOSTIC_STDERR = "Error,  Does not work for umu0=1.0"

# Re-export the frozen scientific universe so tests and workflow can assert
# that v3.1 changes no design coordinates or gates.
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


class ZenithV31Refusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def _finite(name: str, value: object) -> float:
    try:
        return base.finite(name, value)
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc


def build_training_cases() -> list[dict[str, float]]:
    return base.build_training_cases()


def build_validation_cases() -> list[dict[str, float]]:
    return base.build_validation_cases()


def validate_frozen_case_universe() -> None:
    try:
        base.validate_frozen_case_universe()
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc
    if NEW_TRAINING_ALTITUDE_DEG != (82.5, 85.0, 87.5, 90.0):
        raise ZenithV31Refusal("v3.1 training altitude universe drift")
    if VALIDATION_ALTITUDE_DEG != (80.9375, 83.4375, 85.9375, 88.4375):
        raise ZenithV31Refusal("v3.1 validation altitude universe drift")
    if MAX_ABS_ERROR_MAG_LIMIT != 0.025 or RMS_ERROR_MAG_LIMIT != 0.010:
        raise ZenithV31Refusal("v3.1 acceptance-gate drift")


def solver_source_zenith_angle_deg(target_altitude_deg: float) -> float:
    """Map physical altitude to the SDISORT source zenith angle.

    Every non-zenith coordinate is unchanged.  Exact physical zenith alone is
    represented by the fixed 0.001-degree limiting ray because the frozen
    SDISORT executable rejects exactly umu0=1.0.
    """
    altitude = _finite("targetAltitudeDeg", target_altitude_deg)
    if not 80.0 <= altitude <= 90.0:
        raise ZenithV31Refusal("zenith extension renderer is restricted to 80..90 deg")
    if math.isclose(altitude, ZENITH_LIMIT_PHYSICAL_ALTITUDE_DEG, rel_tol=0.0, abs_tol=1e-12):
        return ZENITH_LIMIT_SZA_DEG
    return 90.0 - altitude


def solver_target_altitude_deg(target_altitude_deg: float) -> float:
    return 90.0 - solver_source_zenith_angle_deg(target_altitude_deg)


def solver_mu0(target_altitude_deg: float) -> float:
    return math.cos(math.radians(solver_source_zenith_angle_deg(target_altitude_deg)))


def zenith_limit_relative_airmass_excess() -> float:
    value = 1.0 / math.cos(math.radians(ZENITH_LIMIT_SZA_DEG)) - 1.0
    if not 0.0 < value < ZENITH_LIMIT_RELATIVE_AIRMASS_EXCESS_MAX:
        raise ZenithV31Refusal("zenith-limit airmass bound drift")
    return value


def zenith_limit_applied(target_altitude_deg: float) -> bool:
    altitude = _finite("targetAltitudeDeg", target_altitude_deg)
    return math.isclose(altitude, ZENITH_LIMIT_PHYSICAL_ALTITUDE_DEG, rel_tol=0.0, abs_tol=1e-12)


def render_uvspec_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                        target_altitude_deg: float, observer_elevation_m: float, aod550: float) -> str:
    """Render the unchanged native v3 input, replacing only exact-zenith sza."""
    physical_altitude = _finite("targetAltitudeDeg", target_altitude_deg)
    solver_altitude = solver_target_altitude_deg(physical_altitude)
    try:
        text = base.render_uvspec_input(
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            target_altitude_deg=solver_altitude,
            observer_elevation_m=observer_elevation_m,
            aod550=aod550,
        )
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc
    expected_sza = solver_source_zenith_angle_deg(physical_altitude)
    if f"sza {expected_sza:.8f}" not in text:
        raise ZenithV31Refusal("solver zenith-angle rendering drift")
    if zenith_limit_applied(physical_altitude) and "sza 0.00000000" in text:
        raise ZenithV31Refusal("exact umu0=1.0 must never be sent to SDISORT")
    return text


def parse_direct_transmission(stdout_text: str, *, target_altitude_deg: float) -> dict[str, Any]:
    """Parse using the solver ray's mu0 while retaining exact physical altitude."""
    physical_altitude = _finite("targetAltitudeDeg", target_altitude_deg)
    solver_altitude = solver_target_altitude_deg(physical_altitude)
    try:
        parsed = base.parse_direct_transmission(stdout_text, target_altitude_deg=solver_altitude)
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc
    mu0 = solver_mu0(physical_altitude)
    if abs(float(parsed["mu0"]) - mu0) > 1e-15:
        raise ZenithV31Refusal("parser solver-mu0 mismatch")
    applied = zenith_limit_applied(physical_altitude)
    parsed.update({
        "targetAltitudeDeg": physical_altitude,
        "physicalTargetAltitudeDeg": physical_altitude,
        "physicalSourceZenithAngleDeg": 90.0 - physical_altitude,
        "solverTargetAltitudeDeg": solver_altitude,
        "solverSourceZenithAngleDeg": solver_source_zenith_angle_deg(physical_altitude),
        "solverMu0": mu0,
        "zenithLimitRegularizationApplied": applied,
        "relativePlaneParallelAirmassExcessVsExactVertical": zenith_limit_relative_airmass_excess() if applied else 0.0,
    })
    return parsed


def _coord_key(h: float, e: float, a: float) -> tuple[float, float, float]:
    return base._coord_key(h, e, a)


def build_extended_runtime(source_runtime: dict[str, Any], training_results: dict[tuple[float, float, float], dict[str, Any]]) -> dict[str, Any]:
    try:
        runtime = base.build_extended_runtime(source_runtime, training_results)
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc
    runtime["representation"] = {
        **(runtime.get("representation") or {}),
        "version": METHOD_VERSION,
        "physicalTargetAltitudeMaxDeg": 90.0,
        "zenithSolverLimitConvention": "physical-90deg-is-evaluated-at-sdisort-sza-0.001deg",
        "zenithSolverLimitSzaDeg": ZENITH_LIMIT_SZA_DEG,
        "targetAltitudeCoordinate": "cosecant-altitude-1-over-sin-h",
    }
    runtime["provenance"] = {
        **(runtime.get("provenance") or {}),
        "zenithExtensionStageId": STAGE_ID,
        "methodVersion": METHOD_VERSION,
        "failedV3RunId": FAILED_V3_RUN_ID,
        "exact90DiagnosticRunId": EXACT90_DIAGNOSTIC_RUN_ID,
        "exact90DiagnosticFinding": EXACT90_DIAGNOSTIC_STDERR,
        "physicalTargetAltitudeMaxDeg": 90.0,
        "solverZenithLimitSzaDeg": ZENITH_LIMIT_SZA_DEG,
        "solverZenithLimitRelativePlaneParallelAirmassExcessVsExactVertical": zenith_limit_relative_airmass_excess(),
        "solverZenithLimitRelativeAirmassExcessBound": ZENITH_LIMIT_RELATIVE_AIRMASS_EXCESS_MAX,
        "trainingCoordinatesChangedFromV3": False,
        "holdoutCoordinatesChangedFromV3": False,
        "acceptanceGatesChangedFromV3": False,
        "oldDomainValuesUnchanged": True,
        "postResultRetuningPerformed": False,
        "empiricalRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
        "productionAuthorized": False,
    }
    if runtime["directOpticalDepth"][:675] != source_runtime["directOpticalDepth"]:
        raise ZenithV31Refusal("v2 spectra changed while building v3.1 extension")
    return runtime


def _safe_component(value: float) -> str:
    return (f"{float(value):.6f}".rstrip("0").rstrip(".").replace("-", "m").replace(".", "p"))


def _case_dir(output_dir: Path, *, phase: str, index: int, row: dict[str, float]) -> Path:
    name = (
        f"{phase}-{index:03d}-h{_safe_component(row['targetAltitudeDeg'])}"
        f"-e{_safe_component(row['observerElevationM'])}-a{_safe_component(row['aod550'])}"
    )
    return output_dir / "cases" / name


def execute_case(*, uvspec: Path, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                 row: dict[str, float], output_dir: Path, phase: str, index: int) -> dict[str, Any]:
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
        [str(uvspec)], input=input_text, text=True, capture_output=True, check=False, timeout=180,
    )
    (case_dir / "case.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (case_dir / "case.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    metadata = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "phase": phase,
        "caseIndex": index,
        **row,
        "physicalTargetAltitudeDeg": float(row["targetAltitudeDeg"]),
        "solverSourceZenithAngleDeg": solver_source_zenith_angle_deg(row["targetAltitudeDeg"]),
        "solverMu0": solver_mu0(row["targetAltitudeDeg"]),
        "zenithLimitRegularizationApplied": zenith_limit_applied(row["targetAltitudeDeg"]),
        "solverReturnCode": completed.returncode,
        "inputSha256": hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
        "rawStdoutSha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        "rawStderrSha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
    }
    if completed.returncode != 0:
        metadata["status"] = "SOLVER_FAILED"
        (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise ZenithV31Refusal(f"uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    try:
        parsed = parse_direct_transmission(completed.stdout, target_altitude_deg=row["targetAltitudeDeg"])
    except Exception as exc:
        metadata["status"] = "PARSE_FAILED"
        metadata["failure"] = str(exc)
        (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    metadata["status"] = "CASE_EXECUTED_AND_PARSED"
    metadata["wavelengthCount"] = len(parsed["wavelengthNm"])
    metadata["relativePlaneParallelAirmassExcessVsExactVertical"] = parsed["relativePlaneParallelAirmassExcessVsExactVertical"]
    (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**row, **parsed, "inputSha256": metadata["inputSha256"]}


def validate_against_fresh_holdout(*, root: Path, extended_runtime: dict[str, Any],
                                   validation_results: dict[tuple[float, float, float], dict[str, Any]],
                                   sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    try:
        validation = base.validate_against_fresh_holdout(
            root=root,
            extended_runtime=extended_runtime,
            validation_results=validation_results,
            sed_bundle_path=sed_bundle_path,
            johnson_v_path=johnson_v_path,
        )
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc
    validation["stageId"] = STAGE_ID
    validation["methodVersion"] = METHOD_VERSION
    validation["interpolation"] = "v2-csc-altitude-trilinear-direct-optical-depth-with-new-2.5deg-zenith-knots-and-explicit-sdisort-zenith-limit"
    validation["zenithLimit"] = {
        "physicalTargetAltitudeDeg": 90.0,
        "solverSourceZenithAngleDeg": ZENITH_LIMIT_SZA_DEG,
        "solverMu0": solver_mu0(90.0),
        "relativePlaneParallelAirmassExcessVsExactVertical": zenith_limit_relative_airmass_excess(),
        "relativeAirmassExcessBound": ZENITH_LIMIT_RELATIVE_AIRMASS_EXCESS_MAX,
        "diagnosticRunId": EXACT90_DIAGNOSTIC_RUN_ID,
        "diagnosticFinding": EXACT90_DIAGNOSTIC_STDERR,
    }
    validation["claimBoundary"] = {
        **(validation.get("claimBoundary") or {}),
        "physicalTargetAltitudeMaxDeg": 90.0,
        "exact90EvaluatedDirectlyBySDISORT": False,
        "exact90RepresentedByDocumentedZenithLimit": True,
        "productionAuthorized": False,
    }
    return validation


def execute_campaign(*, root: Path, source_runtime_path: Path, uvspec: Path, data_dir: Path,
                     atmosphere_file: Path, wavelength_grid_file: Path, sed_bundle_path: Path,
                     johnson_v_path: Path, output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise ZenithV31Refusal("scientific solver execution requires explicit allow_execution=True")
    validate_frozen_case_universe()
    if sha256_file(source_runtime_path) != SOURCE_RUNTIME_SHA256:
        raise ZenithV31Refusal("source native stellar v2 runtime SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ZenithV31Refusal("AFGLUS atmosphere SHA-256 drift")
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise ZenithV31Refusal("uvspec SHA-256 drift")
    grid_values = [int(line) for line in Path(wavelength_grid_file).read_text().splitlines() if line.strip()]
    if grid_values != list(WAVELENGTH_NM):
        raise ZenithV31Refusal("wavelength-grid file drift")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise ZenithV31Refusal("frozen Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise ZenithV31Refusal("frozen Johnson-V asset SHA-256 drift")

    source_runtime = json.loads(Path(source_runtime_path).read_text(encoding="utf-8"))
    try:
        base.validate_source_runtime(source_runtime)
    except Exception as exc:
        raise ZenithV31Refusal(str(exc)) from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    campaign_meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "methodVersion": METHOD_VERSION,
        "status": "EXECUTION_STARTED",
        "failedV3RunId": FAILED_V3_RUN_ID,
        "exact90DiagnosticRunId": EXACT90_DIAGNOSTIC_RUN_ID,
        "trainingSpectrumCount": 100,
        "freshValidationSpectrumCount": 64,
        "johnsonVComparisonCount": 192,
        "solverZenithLimitSzaDeg": ZENITH_LIMIT_SZA_DEG,
        "relativeAirmassExcessBound": ZENITH_LIMIT_RELATIVE_AIRMASS_EXCESS_MAX,
        "productionAuthorized": False,
    }
    (output_dir / "campaign.json").write_text(json.dumps(campaign_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    training_results: dict[tuple[float, float, float], dict[str, Any]] = {}
    invocation_count = 0
    for index, row in enumerate(build_training_cases(), start=1):
        invocation_count += 1
        result = execute_case(
            uvspec=uvspec, data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file, row=row, output_dir=output_dir,
            phase="training", index=index,
        )
        training_results[_coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = result
    extended_runtime = build_extended_runtime(source_runtime, training_results)

    validation_results: dict[tuple[float, float, float], dict[str, Any]] = {}
    for index, row in enumerate(build_validation_cases(), start=1):
        invocation_count += 1
        result = execute_case(
            uvspec=uvspec, data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file, row=row, output_dir=output_dir,
            phase="validation", index=index,
        )
        validation_results[_coord_key(row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])] = result

    try:
        validation = validate_against_fresh_holdout(
            root=root,
            extended_runtime=extended_runtime,
            validation_results=validation_results,
            sed_bundle_path=sed_bundle_path,
            johnson_v_path=johnson_v_path,
        )
    except Exception as exc:
        (output_dir / "validation-failure.txt").write_text(str(exc) + "\n", encoding="utf-8")
        raise

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
        "methodVersion": METHOD_VERSION,
        "solverZenithLimitSzaDeg": ZENITH_LIMIT_SZA_DEG,
    }
    runtime_path = output_dir / "stellar-transport-v31-zenith-lut.json"
    runtime_path.write_text(json.dumps(extended_runtime, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    validation["extendedRuntimeSha256"] = sha256_file(runtime_path)
    validation["scientificSolverExecuted"] = True
    validation["solverInvocationCount"] = invocation_count
    validation["randomNumbersUsed"] = False
    validation_path = output_dir / "native-stellar-zenith-v31-validation.json"
    validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    campaign_meta.update({
        "status": validation["status"],
        "solverInvocationCount": invocation_count,
        "extendedRuntimeSha256": validation["extendedRuntimeSha256"],
    })
    (output_dir / "campaign.json").write_text(json.dumps(campaign_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"runtimePath": str(runtime_path), "validationPath": str(validation_path), "validation": validation}


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
        validate_frozen_case_universe()
        print(json.dumps({
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "stageId": STAGE_ID,
            "methodVersion": METHOD_VERSION,
            "newTrainingSpectrumCount": 100,
            "freshValidationSpectrumCount": 64,
            "johnsonVComparisonCount": 192,
            "physicalTargetAltitudeMaxDeg": 90.0,
            "solverZenithLimitSzaDeg": ZENITH_LIMIT_SZA_DEG,
            "solverZenithLimitRelativeAirmassExcess": zenith_limit_relative_airmass_excess(),
            "failedV3RunId": FAILED_V3_RUN_ID,
            "exact90DiagnosticRunId": EXACT90_DIAGNOSTIC_RUN_ID,
            "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    required = [args.source_runtime, args.uvspec, args.data_dir, args.atmosphere_file,
                args.wavelength_grid_file, args.sed_bundle, args.johnson_v, args.output_dir]
    if any(value is None for value in required):
        raise ZenithV31Refusal("execution requires all explicit bound paths")
    result = execute_campaign(
        root=args.root, source_runtime_path=args.source_runtime, uvspec=args.uvspec,
        data_dir=args.data_dir, atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file, sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v, output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({
        "status": result["validation"]["status"],
        "methodVersion": METHOD_VERSION,
        "extendedRuntimeSha256": result["validation"]["extendedRuntimeSha256"],
        "maxAbsDeltaAvMag": result["validation"]["overall"]["maxAbsDeltaAvMag"],
        "rmsDeltaAvMag": result["validation"]["overall"]["rmsDeltaAvMag"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
