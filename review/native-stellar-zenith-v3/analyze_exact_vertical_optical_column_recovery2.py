#!/usr/bin/env python3
"""Analysis-only recovery2 for the exact-vertical optical-column diagnostic.

Consumes immutable stdout/stderr produced by run 33041069040. This module never
executes a radiative-transfer solver.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V1_PATH = HERE / "diagnose_exact_vertical_optical_column_v1.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v1 = _load(V1_PATH, "exact_vertical_optical_column_v1_for_analysis_recovery2")

STAGE_ID = "native-stellar-zenith-exact-vertical-optical-column-analysis-recovery2"
SOURCE_RUN_ID = 33041069040
SOURCE_DISPATCH_SHA = "ac4a1230fd3ceb500019f5188173fb8f7165f5ec"
SOURCE_ARTIFACT_ID = 9633879569
SOURCE_ARTIFACT_NAME = "native-stellar-zenith-exact-vertical-optical-column-recovery1-33041069040"
SOURCE_ARTIFACT_DIGEST = "sha256:eba59cc5d22e1600b0c38809cac29d615dddd0af02b491febae65164c3a1004e"
SOURCE_SOLVER_INVOCATION_COUNT = 4
SOURCE_FAILURE_CLASS = "POST_SOLVER_DENSE_OUTPUT_GRID_PARSER_FAILURE_NUMERIC_GATES_NOT_EVALUATED"
DENSE_START_NM = 380.0
DENSE_END_NM = 780.0
DENSE_STEP_NM = 0.05
DENSE_ROW_COUNT = 8001
DENSE_WAVELENGTH_TOLERANCE_NM = 1.0e-9
INTEGER_NODE_COUNT = 401
STDOUT_STDERR_FLUX_TOLERANCE = 1.0e-7
EXPECTED_CASE_UNIVERSE = v1.CASE_UNIVERSE
MAX_ABS_DELTA_TAU = v1.MAX_ABS_DELTA_TAU
MAX_ABS_DELTA_AV_MAG = v1.MAX_ABS_DELTA_AV_MAG

FLUX_DIR_RE = re.compile(
    r"^\s*iv\s*=\s*(\d+),\s*([0-9]+(?:\.[0-9]+)?)\s*nm,\s*iq\s*=\s*0,\s*"
    r"flux_dir\[lu=0\]\s*=\s*([0-9.eE+\-]+)",
    re.MULTILINE,
)


class Recovery2Refusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(label: str, value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise Recovery2Refusal(f"invalid {label}: {value!r}") from exc
    if not math.isfinite(number):
        raise Recovery2Refusal(f"non-finite {label}: {value!r}")
    return number


def parse_dense_direct_transmission(text: str) -> dict[str, Any]:
    rows: list[tuple[float, float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise Recovery2Refusal(f"unexpected dense stdout row: {raw!r}")
        wavelength = finite("dense wavelength", parts[0])
        transmission = finite("dense direct transmission", parts[1])
        if not (0.0 < transmission <= 1.000001):
            raise Recovery2Refusal(
                f"invalid dense direct transmission at {wavelength} nm: {transmission}"
            )
        rows.append((wavelength, min(1.0, transmission)))
    if len(rows) != DENSE_ROW_COUNT:
        raise Recovery2Refusal(f"dense stdout row count drift: {len(rows)} != {DENSE_ROW_COUNT}")
    for index, (wavelength, _transmission) in enumerate(rows):
        expected = DENSE_START_NM + DENSE_STEP_NM * index
        if abs(wavelength - expected) > DENSE_WAVELENGTH_TOLERANCE_NM:
            raise Recovery2Refusal(
                f"dense wavelength drift at row {index}: {wavelength} != {expected}"
            )
    if abs(rows[0][0] - DENSE_START_NM) > DENSE_WAVELENGTH_TOLERANCE_NM:
        raise Recovery2Refusal("dense stdout start wavelength drift")
    if abs(rows[-1][0] - DENSE_END_NM) > DENSE_WAVELENGTH_TOLERANCE_NM:
        raise Recovery2Refusal("dense stdout end wavelength drift")

    selected_wavelengths: list[int] = []
    selected_transmission: list[float] = []
    for integer_index in range(INTEGER_NODE_COUNT):
        dense_index = integer_index * 20
        wavelength, transmission = rows[dense_index]
        expected_wavelength = 380 + integer_index
        if abs(wavelength - expected_wavelength) > DENSE_WAVELENGTH_TOLERANCE_NM:
            raise Recovery2Refusal(
                f"integer-node wavelength drift at dense row {dense_index}: "
                f"{wavelength} != {expected_wavelength}"
            )
        selected_wavelengths.append(expected_wavelength)
        selected_transmission.append(transmission)
    if selected_wavelengths != list(v1.WAVELENGTH_NM):
        raise Recovery2Refusal("selected integer-nm grid differs from frozen 380..780 grid")
    return {
        "denseRowCount": len(rows),
        "denseStartNm": rows[0][0],
        "denseEndNm": rows[-1][0],
        "denseStepNm": DENSE_STEP_NM,
        "wavelengthNm": selected_wavelengths,
        "directTransmission": selected_transmission,
        "directOpticalDepth": [-math.log(value) for value in selected_transmission],
    }


def parse_stderr_direct_flux(text: str) -> dict[str, Any]:
    matches = list(FLUX_DIR_RE.finditer(text))
    if len(matches) != INTEGER_NODE_COUNT:
        raise Recovery2Refusal(
            f"stderr final iq=0 flux_dir count drift: {len(matches)} != {INTEGER_NODE_COUNT}"
        )
    wavelengths: list[int] = []
    transmission: list[float] = []
    for expected_iv, match in enumerate(matches):
        iv = int(match.group(1))
        wavelength = finite("stderr wavelength", match.group(2))
        flux_dir = finite("stderr flux_dir", match.group(3))
        expected_wavelength = 380 + expected_iv
        if iv != expected_iv:
            raise Recovery2Refusal(f"stderr iv drift: {iv} != {expected_iv}")
        if abs(wavelength - expected_wavelength) > DENSE_WAVELENGTH_TOLERANCE_NM:
            raise Recovery2Refusal(
                f"stderr wavelength drift at iv={iv}: {wavelength} != {expected_wavelength}"
            )
        if not (0.0 < flux_dir <= 1.000001):
            raise Recovery2Refusal(f"invalid stderr flux_dir at iv={iv}: {flux_dir}")
        wavelengths.append(expected_wavelength)
        transmission.append(min(1.0, flux_dir))
    return {"wavelengthNm": wavelengths, "directTransmission": transmission}


def crosscheck_selected_stdout_against_stderr(
    stdout_selected: dict[str, Any], stderr_direct: dict[str, Any]
) -> dict[str, Any]:
    if stdout_selected["wavelengthNm"] != stderr_direct["wavelengthNm"]:
        raise Recovery2Refusal("stdout/stderr selected wavelength grids differ")
    deltas = [
        abs(finite("stdout transmission", left) - finite("stderr transmission", right))
        for left, right in zip(
            stdout_selected["directTransmission"],
            stderr_direct["directTransmission"],
            strict=True,
        )
    ]
    max_delta = max(deltas)
    index = deltas.index(max_delta)
    passed = max_delta <= STDOUT_STDERR_FLUX_TOLERANCE
    return {
        "maxAbsDeltaTransmission": max_delta,
        "limit": STDOUT_STDERR_FLUX_TOLERANCE,
        "wavelengthNm": stdout_selected["wavelengthNm"][index],
        "passed": passed,
    }


def parse_case_input(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    required_exact = {
        "sza 0.00000000",
        "rte_solver disort",
        "number_of_streams 16",
        "output_quantity transmittance",
        "output_user lambda edir",
        "zout 0.000000",
    }
    missing = sorted(required_exact - set(lines))
    if missing:
        raise Recovery2Refusal(f"source case input missing frozen directives: {missing}")
    grid_lines = [line for line in lines if line.startswith("atm_z_grid ")]
    aod_lines = [line for line in lines if line.startswith("aerosol_set_tau_at_wvl 550 ")]
    if len(grid_lines) != 1 or len(aod_lines) != 1:
        raise Recovery2Refusal("source case input atmosphere/AOD directive ambiguity")
    grid = [finite("atm_z_grid", token) for token in grid_lines[0].split()[1:]]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise Recovery2Refusal("source case atm_z_grid is not strictly ascending")
    elevation_m = grid[0] * 1000.0
    aod = finite("AOD550", aod_lines[0].split()[-1])
    return {
        "observerElevationM": elevation_m,
        "aod550": aod,
        "expectedLayerCount": len(grid) - 1,
        "atmZGridLevelCount": len(grid),
    }


def expected_case_directories() -> tuple[str, ...]:
    return (
        "01-e500-a0p3",
        "02-e1250-a0p1",
        "03-e1250-a0p3",
        "04-e2000-a0p2",
    )


def validate_source_recovery_summary(source_root: Path) -> dict[str, Any]:
    path = source_root / "exact-vertical-optical-column-recovery1-summary.json"
    if not path.is_file():
        raise Recovery2Refusal("source recovery1 summary missing")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("stageId") != "native-stellar-zenith-exact-vertical-optical-column-recovery1":
        raise Recovery2Refusal("source recovery1 stage identity drift")
    if data.get("status") != "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_FAIL":
        raise Recovery2Refusal("source recovery1 status drift")
    if data.get("solverInvocationCount") != SOURCE_SOLVER_INVOCATION_COUNT:
        raise Recovery2Refusal("source solver invocation count drift")
    if data.get("successfulParsedCaseCount") != 0 or data.get("metrics") is not None:
        raise Recovery2Refusal("source parser-failure boundary drift")
    failures = data.get("failures")
    if not isinstance(failures, list) or len(failures) != 4:
        raise Recovery2Refusal("source failure list drift")
    if any(item.get("failure") != "non-integral wavelength in 1-nm output" for item in failures):
        raise Recovery2Refusal("source failure class is not the frozen dense-grid parser refusal")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "status": data["status"],
        "solverInvocationCount": data["solverInvocationCount"],
        "successfulParsedCaseCount": data["successfulParsedCaseCount"],
    }


def analyze_case(
    *, root: Path, case_dir: Path, expected_case: tuple[float, float],
    sed_bundle_path: Path, johnson_v_path: Path
) -> dict[str, Any]:
    input_path = case_dir / "case.inp"
    stdout_path = case_dir / "case.stdout.txt"
    stderr_path = case_dir / "case.stderr.txt"
    for path in (input_path, stdout_path, stderr_path):
        if not path.is_file():
            raise Recovery2Refusal(f"source case file missing: {path}")
    input_text = input_path.read_text(encoding="utf-8")
    stdout_text = stdout_path.read_text(encoding="utf-8")
    stderr_text = stderr_path.read_text(encoding="utf-8")
    identity = parse_case_input(input_text)
    expected_elevation, expected_aod = expected_case
    if abs(identity["observerElevationM"] - expected_elevation) > 1.0e-6:
        raise Recovery2Refusal(
            f"case elevation drift in {case_dir.name}: {identity['observerElevationM']} != {expected_elevation}"
        )
    if abs(identity["aod550"] - expected_aod) > 1.0e-12:
        raise Recovery2Refusal(
            f"case AOD drift in {case_dir.name}: {identity['aod550']} != {expected_aod}"
        )
    if "iv = 400, 780.000000 nm" not in stderr_text:
        raise Recovery2Refusal(f"case {case_dir.name} lacks final 780-nm solver evidence")

    dense = parse_dense_direct_transmission(stdout_text)
    stderr_direct = parse_stderr_direct_flux(stderr_text)
    crosscheck = crosscheck_selected_stdout_against_stderr(dense, stderr_direct)
    if not crosscheck["passed"]:
        raise Recovery2Refusal(
            f"case {case_dir.name} stdout/stderr direct-flux crosscheck failed: "
            f"{crosscheck['maxAbsDeltaTransmission']} > {STDOUT_STDERR_FLUX_TOLERANCE}"
        )
    try:
        verbose = v1.parse_verbose_optical_columns(
            stderr_text,
            expected_layer_count=identity["expectedLayerCount"],
        )
    except Exception as exc:
        raise Recovery2Refusal(f"case {case_dir.name} verbose optical parse failed: {exc}") from exc
    try:
        metrics = v1.evaluate_case(
            root=root,
            parsed_direct={
                "wavelengthNm": dense["wavelengthNm"],
                "directOpticalDepth": dense["directOpticalDepth"],
            },
            parsed_verbose=verbose,
            sed_bundle_path=sed_bundle_path,
            johnson_v_path=johnson_v_path,
        )
    except Exception as exc:
        raise Recovery2Refusal(f"case {case_dir.name} v1 scientific evaluator failed: {exc}") from exc

    universal_bound = (2.5 / math.log(10.0)) * metrics["maxAbsDeltaOpticalDepth"]
    return {
        "caseDirectory": case_dir.name,
        "observerElevationM": identity["observerElevationM"],
        "aod550": identity["aod550"],
        "expectedLayerCount": identity["expectedLayerCount"],
        "sourceFiles": {
            "inputSha256": sha256_file(input_path),
            "stdoutSha256": sha256_file(stdout_path),
            "stderrSha256": sha256_file(stderr_path),
        },
        "denseStdoutValidation": {
            "rowCount": dense["denseRowCount"],
            "startNm": dense["denseStartNm"],
            "endNm": dense["denseEndNm"],
            "stepNm": dense["denseStepNm"],
            "selectedIntegerNodeCount": len(dense["wavelengthNm"]),
        },
        "stdoutStderrDirectFluxCrosscheck": crosscheck,
        "verboseOpticalLayerCountMin": min(verbose["layerCountByWavelength"]),
        "verboseOpticalLayerCountMax": max(verbose["layerCountByWavelength"]),
        "metrics": metrics,
        "johnsonVUniversalBoundFromMaxDeltaTauMag": universal_bound,
    }


def analyze(
    *, root: Path, source_root: Path, sed_bundle_path: Path,
    johnson_v_path: Path, output_dir: Path
) -> dict[str, Any]:
    if not source_root.is_dir():
        raise Recovery2Refusal(f"source artifact directory missing: {source_root}")
    if not sed_bundle_path.is_file() or not johnson_v_path.is_file():
        raise Recovery2Refusal("frozen photometry asset missing")
    if v1.sha256_file(sed_bundle_path) != v1.SOURCE_SED_SHA256:
        raise Recovery2Refusal("Pickles SED asset SHA-256 drift")
    if v1.sha256_file(johnson_v_path) != v1.SOURCE_JOHNSON_V_SHA256:
        raise Recovery2Refusal("Johnson-V asset SHA-256 drift")
    source_summary = validate_source_recovery_summary(source_root)
    raw_root = source_root / "raw"
    actual_dirs = tuple(sorted(path.name for path in raw_root.iterdir() if path.is_dir()))
    if actual_dirs != expected_case_directories():
        raise Recovery2Refusal(f"source case directory universe drift: {actual_dirs!r}")

    cases: list[dict[str, Any]] = []
    for dirname, expected_case in zip(expected_case_directories(), EXPECTED_CASE_UNIVERSE, strict=True):
        cases.append(
            analyze_case(
                root=root,
                case_dir=raw_root / dirname,
                expected_case=expected_case,
                sed_bundle_path=sed_bundle_path,
                johnson_v_path=johnson_v_path,
            )
        )
    max_tau = max(case["metrics"]["maxAbsDeltaOpticalDepth"] for case in cases)
    max_av = max(case["metrics"]["maxAbsDeltaAvMag"] for case in cases)
    max_flux_crosscheck = max(
        case["stdoutStderrDirectFluxCrosscheck"]["maxAbsDeltaTransmission"] for case in cases
    )
    scientific_pass = max_tau <= MAX_ABS_DELTA_TAU and max_av <= MAX_ABS_DELTA_AV_MAG
    parser_evidence_pass = max_flux_crosscheck <= STDOUT_STDERR_FLUX_TOLERANCE
    passed = scientific_pass and parser_evidence_pass
    result = {
        "schemaVersion": 2,
        "stageId": STAGE_ID,
        "status": (
            "EXACT_VERTICAL_OPTICAL_COLUMN_ANALYSIS_RECOVERY2_PASS"
            if passed else "EXACT_VERTICAL_OPTICAL_COLUMN_ANALYSIS_RECOVERY2_FAIL"
        ),
        "source": {
            "runId": SOURCE_RUN_ID,
            "dispatchSha": SOURCE_DISPATCH_SHA,
            "artifactId": SOURCE_ARTIFACT_ID,
            "artifactName": SOURCE_ARTIFACT_NAME,
            "artifactDigest": SOURCE_ARTIFACT_DIGEST,
            "sourceSolverInvocationCount": SOURCE_SOLVER_INVOCATION_COUNT,
            "sourceFailureClass": SOURCE_FAILURE_CLASS,
            "sourceRecoverySummary": source_summary,
        },
        "analysisExecution": {
            "scientificSolverExecutionPerformedByThisAnalysis": False,
            "uvspecRequired": False,
            "sourceCaseCount": len(cases),
            "denseStdoutExpectedRowCountPerCase": DENSE_ROW_COUNT,
            "selectedIntegerNodeCountPerCase": INTEGER_NODE_COUNT,
        },
        "parserEvidenceGate": {
            "maxStdoutStderrDirectFluxAbsDelta": max_flux_crosscheck,
            "limit": STDOUT_STDERR_FLUX_TOLERANCE,
            "passed": parser_evidence_pass,
        },
        "scientificGates": {
            "maxAbsDeltaOpticalDepth": max_tau,
            "maxAbsDeltaOpticalDepthLimit": MAX_ABS_DELTA_TAU,
            "spectralOpticalColumnPassed": max_tau <= MAX_ABS_DELTA_TAU,
            "maxAbsDeltaAvMag": max_av,
            "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
            "johnsonVConsequencePassed": max_av <= MAX_ABS_DELTA_AV_MAG,
            "passed": scientific_pass,
        },
        "cases": cases,
        "claimBoundary": {
            "analysisOnlyRecovery": True,
            "protectedHoldoutOpened": False,
            "modelFitPerformed": False,
            "stellarLutAcceptanceGateEvaluated": False,
            "v32EndpointMethodAuthorizedForDraftOnlyIfPass": passed,
            "productionAuthorized": False,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    result_path = output_dir / "exact-vertical-optical-column-analysis-recovery2-summary.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.source_root is None:
        print(json.dumps({
            "stageId": STAGE_ID,
            "status": "REVIEW_ONLY_NO_ANALYSIS_EXECUTION",
            "sourceRunId": SOURCE_RUN_ID,
            "sourceArtifactId": SOURCE_ARTIFACT_ID,
            "sourceArtifactDigest": SOURCE_ARTIFACT_DIGEST,
            "scientificSolverExecutionAuthorized": False,
            "maxAbsDeltaOpticalDepthLimit": MAX_ABS_DELTA_TAU,
            "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
            "stdoutStderrFluxTolerance": STDOUT_STDERR_FLUX_TOLERANCE,
            "protectedHoldoutOpeningAuthorized": False,
            "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    if args.sed_bundle is None or args.johnson_v is None or args.output_dir is None:
        raise Recovery2Refusal("analysis execution requires source, photometry assets, and output dir")
    result = analyze(
        root=args.root,
        source_root=args.source_root,
        sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "status": result["status"],
        "parserEvidenceGate": result["parserEvidenceGate"],
        "scientificGates": result["scientificGates"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
