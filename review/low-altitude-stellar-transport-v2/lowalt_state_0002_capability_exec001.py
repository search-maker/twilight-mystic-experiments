#!/usr/bin/env python3
"""One-shot deterministic capability/timing executor for LOWALT-STELLAR-STATE-0002.

This implementation is scientifically result-blind. It is bound to the
published STATE-0002 controller and can only execute that frozen fresh
20-coordinate / 60-invocation capability/timing matrix. Results are capability
and runtime evidence only: they cannot lower the production support floor,
select a compact representation, or open protected validation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

SCIENTIFIC_STATE = "LOWALT-STELLAR-STATE-0002"
EXECUTION_ID = "lowalt-state-0002-capability-runtime-exec001"
CONTROLLER_RELATIVE_PATH = "review/low-altitude-stellar-transport-v2/lowalt_state_0002_capability_controller.py"
CONTROLLER_GIT_BLOB = "2b7951b1ed260d21e3d1cbc6dbd48b68fdf44607"
EXPECTED_PROTOCOL_ID = "lowalt-state-0002-capability-runtime-v1"
EXPECTED_CASE_COUNT = 20
EXPECTED_INVOCATION_COUNT = 60
EXPECTED_WAVELENGTHS = tuple(range(380, 781))
EXPECTED_UVSPEC_SHA256 = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"
EXPECTED_LIBRADTRAN_PACKAGE = "rubin-libradtran=2.0.6=py312pl5321he9373c2_1"
SURFACE_ALBEDO = 0.15
MOL_ABS_PARAM = "crs"


class ExecutionRefusal(RuntimeError):
    pass


def finite(name: str, value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ExecutionRefusal(f"{name} must be finite")
    return number


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_controller(repo_root: Path):
    path = repo_root / CONTROLLER_RELATIVE_PATH
    if not path.is_file():
        raise ExecutionRefusal(f"published controller missing: {path}")
    spec = importlib.util.spec_from_file_location("lowalt_state_0002_controller", path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal("cannot load published controller")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.self_test()
    manifest = module.manifest()
    if manifest.get("scientificState") != SCIENTIFIC_STATE:
        raise ExecutionRefusal("controller scientific-state drift")
    if manifest.get("protocolId") != EXPECTED_PROTOCOL_ID:
        raise ExecutionRefusal("controller protocol drift")
    if manifest.get("freshCaseCount") != EXPECTED_CASE_COUNT:
        raise ExecutionRefusal("controller case-count drift")
    if manifest.get("timedInvocationCount") != EXPECTED_INVOCATION_COUNT:
        raise ExecutionRefusal("controller invocation-count drift")
    if manifest.get("protectedResultsAuthorized") is not False:
        raise ExecutionRefusal("controller protected-result boundary drift")
    if manifest.get("applicationSupportChangeAuthorized") is not False:
        raise ExecutionRefusal("controller support boundary drift")
    if manifest.get("runtimeIdentity", {}).get("uvspecSha256") != EXPECTED_UVSPEC_SHA256:
        raise ExecutionRefusal("controller uvspec identity drift")
    if manifest.get("runtimeIdentity", {}).get("libRadtranPackage") != EXPECTED_LIBRADTRAN_PACKAGE:
        raise ExecutionRefusal("controller package identity drift")
    return module, manifest


def atmosphere_levels_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ExecutionRefusal(f"malformed atmosphere row: {raw!r}")
        levels.append(finite("atmosphere altitude", parts[0]))
    if len(levels) < 2 or any(levels[i] <= levels[i + 1] for i in range(len(levels) - 1)):
        raise ExecutionRefusal("atmosphere levels must be strictly descending")
    return levels


def elevated_site_grid_ascending(atmosphere_file: Path, observer_elevation_m: float) -> list[float]:
    elevation = finite("observerElevationM", observer_elevation_m)
    if elevation not in {0.0, 2500.0}:
        raise ExecutionRefusal("observer elevation outside frozen STATE-0002 capability endpoints")
    site_km = elevation / 1000.0
    levels = atmosphere_levels_descending(atmosphere_file)
    if not levels[-1] <= site_km < levels[0]:
        raise ExecutionRefusal("site elevation outside atmosphere grid")
    grid = [site_km, *sorted(z for z in levels if z > site_km)]
    if len(grid) < 2 or any(grid[i] >= grid[i + 1] for i in range(len(grid) - 1)):
        raise ExecutionRefusal("atm_z_grid must be strictly ascending")
    return grid


def _controller_axes(manifest: dict[str, Any]) -> tuple[set[float], set[float], set[float]]:
    axes = manifest["freshAxes"]
    return (
        {float(x) for x in axes["targetGeometricAltitudeDeg"]},
        {float(x) for x in axes["observerElevationM"]},
        {float(x) for x in axes["aod550"]},
    )


def render_uvspec_input(*, manifest: dict[str, Any], data_dir: Path, atmosphere_file: Path,
                        wavelength_grid_file: Path, target_altitude_deg: float,
                        observer_elevation_m: float, aod550: float) -> str:
    altitude = finite("targetGeometricAltitudeDeg", target_altitude_deg)
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    altitudes, elevations, aods = _controller_axes(manifest)
    if altitude not in altitudes or elevation not in elevations or aod not in aods:
        raise ExecutionRefusal("renderer coordinate outside published STATE-0002 capability universe")
    if not 0.0 < altitude < 5.0:
        raise ExecutionRefusal("STATE-0002 capability target must be strictly between 0 and 5 deg geometric")
    grid = elevated_site_grid_ascending(atmosphere_file, elevation)
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
        f"mol_abs_param {MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {EXPECTED_WAVELENGTHS[0]} {EXPECTED_WAVELENGTHS[-1]}",
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
    for forbidden in ("rte_solver mystic", "mc_", "aerosol_species_file", "angstrom", "nrefrac", "refraction", "altitude "):
        if forbidden in lower:
            raise ExecutionRefusal(f"forbidden directive emitted: {forbidden}")
    if text.count("aerosol_default") != 1 or text.count("aerosol_set_tau_at_wvl") != 1:
        raise ExecutionRefusal("aerosol directive surface drift")
    if text.count("rte_solver sdisort") != 1 or text.count("sdisort nscat 1") != 1:
        raise ExecutionRefusal("pseudo-spherical deterministic solver surface drift")
    return text


def parse_direct_transmission(stdout_text: str, *, manifest: dict[str, Any], target_altitude_deg: float) -> dict[str, Any]:
    altitude = finite("targetGeometricAltitudeDeg", target_altitude_deg)
    if altitude not in _controller_axes(manifest)[0] or not 0.0 < altitude < 5.0:
        raise ExecutionRefusal("parser altitude outside frozen STATE-0002 capability universe")
    mu0 = math.sin(math.radians(altitude))
    if not math.isfinite(mu0) or not mu0 > 0.0:
        raise ExecutionRefusal("mu0 must be finite and strictly positive")
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ExecutionRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        ray_t = edir / mu0
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise ExecutionRefusal("non-integral wavelength in exact 1-nm output")
        if not math.isfinite(ray_t) or not 0.0 < ray_t <= 1.000001:
            raise ExecutionRefusal(f"NUMERICALLY_UNRESOLVED direct transmission at {wavelength} nm")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(EXPECTED_WAVELENGTHS):
        raise ExecutionRefusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    if any(not math.isfinite(value) or not 0.0 < value <= 1.0 for value in transmission):
        raise ExecutionRefusal("NUMERICALLY_UNRESOLVED direct transmission spectrum")
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "directOpticalDepth": [-math.log(value) for value in transmission],
        "targetGeometricAltitudeDeg": altitude,
        "sourceZenithAngleDeg": 90.0 - altitude,
        "mu0": mu0,
        "positiveEpsilonSubstitutionUsed": False,
    }


def nearest_rank_percentile(values: list[float], percentile: float) -> float:
    if not values or not 0.0 < percentile <= 1.0:
        raise ExecutionRefusal("invalid percentile input")
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def timing_summary(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    seconds = [float(row["elapsedSeconds"]) for row in rows]
    if len(seconds) != EXPECTED_INVOCATION_COUNT or any(not math.isfinite(x) or x < 0.0 for x in seconds):
        raise ExecutionRefusal("timing universe incomplete or nonfinite")
    median = statistics.median(seconds)
    p95 = nearest_rank_percentile(seconds, 0.95)
    per_altitude: dict[str, dict[str, float]] = {}
    for altitude in manifest["freshAxes"]["targetGeometricAltitudeDeg"]:
        subset = [float(row["elapsedSeconds"]) for row in rows if row["targetGeometricAltitudeDeg"] == altitude]
        per_altitude[altitude] = {
            "count": len(subset),
            "medianSeconds": statistics.median(subset),
            "p95NearestRankSeconds": nearest_rank_percentile(subset, 0.95),
            "maxSeconds": max(subset),
            "totalSeconds": sum(subset),
        }
    budgets = manifest["practicalRouteFreeze"]
    return {
        "count": len(seconds),
        "medianSeconds": median,
        "p95NearestRankSeconds": p95,
        "maxSeconds": max(seconds),
        "totalSeconds": sum(seconds),
        "perAltitude": per_altitude,
        "projectedSerialSecondsAtMedian": {
            "ordinaryTimelineBase2049": median * int(budgets["ordinaryTimelineBaseEvaluations"]),
            "sevenDayAnnualSingleTarget108597": median * int(budgets["sevenDayAnnualSingleTargetBaseEvaluations"]),
        },
        "projectedSerialSecondsAtP95": {
            "ordinaryTimelineBase2049": p95 * int(budgets["ordinaryTimelineBaseEvaluations"]),
            "sevenDayAnnualSingleTarget108597": p95 * int(budgets["sevenDayAnnualSingleTargetBaseEvaluations"]),
        },
        "routingBoundary": "PER_SAMPLE_REMOTE_SDISORT_REMAINS_ARCHITECTURALLY_INELIGIBLE_INDEPENDENT_OF_TIMING",
    }


def _case_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {row["caseId"]: row for row in manifest["cases"]}
    if len(rows) != EXPECTED_CASE_COUNT:
        raise ExecutionRefusal("case map drift")
    return rows


def execute(*, repo_root: Path, uvspec: Path, data_dir: Path, atmosphere_file: Path,
            wavelength_grid_file: Path, output_dir: Path) -> dict[str, Any]:
    _, manifest = load_controller(repo_root)
    if output_dir.exists():
        raise ExecutionRefusal("output directory must not already exist")
    output_dir.mkdir(parents=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir()
    cases = _case_map(manifest)
    invocations = manifest["timedInvocations"]
    if len(invocations) != EXPECTED_INVOCATION_COUNT:
        raise ExecutionRefusal("invocation universe drift")

    records: list[dict[str, Any]] = []
    capability: dict[str, dict[str, Any]] = {}
    attempted = 0
    for invocation in invocations:
        attempted += 1
        case = cases[invocation["caseId"]]
        h = float(case["targetGeometricAltitudeDeg"])
        e = float(case["observerElevationM"])
        a = float(case["aod550"])
        input_text = render_uvspec_input(
            manifest=manifest, data_dir=data_dir, atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file, target_altitude_deg=h,
            observer_elevation_m=e, aod550=a,
        )
        ordinal = int(invocation["invocationOrdinal"])
        input_path = raw_dir / f"invocation-{ordinal:03d}.inp"
        stdout_path = raw_dir / f"invocation-{ordinal:03d}.out"
        stderr_path = raw_dir / f"invocation-{ordinal:03d}.err"
        input_path.write_text(input_text, encoding="utf-8")
        started = time.perf_counter()
        proc = subprocess.run([str(uvspec)], input=input_text, text=True, capture_output=True, check=False)
        elapsed = time.perf_counter() - started
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        status = "PASS"
        parsed: dict[str, Any] | None = None
        error: str | None = None
        if proc.returncode != 0:
            status = "SOLVER_ERROR"
            error = f"uvspec return code {proc.returncode}"
        else:
            try:
                parsed = parse_direct_transmission(proc.stdout, manifest=manifest, target_altitude_deg=h)
            except Exception as exc:
                status = "NUMERICALLY_UNRESOLVED"
                error = f"{type(exc).__name__}: {exc}"
        record = {
            "invocationOrdinal": ordinal,
            "caseId": case["caseId"],
            "repetition": int(invocation["repetition"]),
            "capabilitySpectrum": bool(invocation["capabilitySpectrum"]),
            "timingOnly": bool(invocation["timingOnly"]),
            "targetGeometricAltitudeDeg": case["targetGeometricAltitudeDeg"],
            "observerElevationM": case["observerElevationM"],
            "aod550": case["aod550"],
            "elapsedSeconds": elapsed,
            "status": status,
            "returnCode": int(proc.returncode),
            "inputSha256": sha256_file(input_path),
            "stdoutSha256": sha256_file(stdout_path),
            "stderrSha256": sha256_file(stderr_path),
            "retryUsed": False,
            "epsilonSubstitutionUsed": False,
            "error": error,
        }
        records.append(record)
        if invocation["capabilitySpectrum"]:
            capability[case["caseId"]] = {"status": status, "spectrum": parsed if status == "PASS" else None}

    if attempted != EXPECTED_INVOCATION_COUNT or len(records) != EXPECTED_INVOCATION_COUNT:
        raise ExecutionRefusal("did not attempt exactly 60 frozen invocations")
    capability_statuses = [capability[case_id]["status"] for case_id in cases]
    all_capability_resolved = all(status == "PASS" for status in capability_statuses)
    all_invocations_resolved = all(row["status"] == "PASS" for row in records)
    result = {
        "schemaVersion": 1,
        "scientificState": SCIENTIFIC_STATE,
        "executionId": EXECUTION_ID,
        "protocolId": EXPECTED_PROTOCOL_ID,
        "postV1Nonblocking": True,
        "protectedEvidence": False,
        "supportDecisionEvidence": False,
        "compactRepresentationSelectionEvidence": False,
        "applicationSupportChangeAuthorized": False,
        "controllerGitBlob": CONTROLLER_GIT_BLOB,
        "controllerManifestSha256": manifest["manifestSha256"],
        "attemptedInvocationCount": attempted,
        "solverInvocationCount": attempted,
        "capabilitySpectrumCount": len(capability),
        "allCapabilitySpectraNumericallyResolved": all_capability_resolved,
        "allTimedInvocationsNumericallyResolved": all_invocations_resolved,
        "capability": capability,
        "invocations": records,
        "timing": timing_summary(records, manifest),
        "randomNumbersUsed": False,
        "positiveEpsilonSubstitutionUsed": False,
        "sameIdentityRetryUsed": False,
        "githubRerunPermitted": False,
        "productionAuthorized": False,
        "minimumSupportedGeometricAltitudeDeg": None,
        "exactHorizonSupported": False,
    }
    result_path = output_dir / "capability-runtime-result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    receipt = {
        "scientificState": SCIENTIFIC_STATE,
        "executionId": EXECUTION_ID,
        "attemptedInvocationCount": attempted,
        "solverInvocationCount": attempted,
        "resultSha256": sha256_file(result_path),
        "allCapabilitySpectraNumericallyResolved": all_capability_resolved,
        "allTimedInvocationsNumericallyResolved": all_invocations_resolved,
        "protectedEvidence": False,
        "supportDecisionEvidence": False,
        "productionAuthorized": False,
        "sameIdentityRetryUsed": False,
        "positiveEpsilonSubstitutionUsed": False,
    }
    (output_dir / "execution-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return result


def self_test(repo_root: Path) -> None:
    _, manifest = load_controller(repo_root)
    assert manifest["scientificState"] == SCIENTIFIC_STATE
    assert manifest["freshCaseCount"] == EXPECTED_CASE_COUNT
    assert manifest["timedInvocationCount"] == EXPECTED_INVOCATION_COUNT
    assert manifest["exactHorizonSupported"] is False
    assert manifest["applicationSupportChangeAuthorized"] is False
    assert manifest["protectedResultsAuthorized"] is False
    assert manifest["practicalRouteFreeze"]["perSampleRemoteSdisortEligible"] is False
    assert _controller_axes(manifest)[0] == {0.30, 0.70, 1.40, 2.90, 4.60}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test(args.repo_root)
        print("PASS LOWALT-STELLAR-STATE-0002 capability exec001 self-test")
        return 0
    if not args.execute:
        parser.error("choose --self-test or --execute")
    if not args.allow_execution:
        raise ExecutionRefusal("execution requires explicit --allow-execution")
    required = (args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file, args.output_dir)
    if any(value is None for value in required):
        parser.error("execution requires --uvspec --data-dir --atmosphere-file --wavelength-grid-file --output-dir")
    result = execute(
        repo_root=args.repo_root, uvspec=args.uvspec, data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file, wavelength_grid_file=args.wavelength_grid_file,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "executionId": result["executionId"],
        "solverInvocationCount": result["solverInvocationCount"],
        "allCapabilitySpectraNumericallyResolved": result["allCapabilitySpectraNumericallyResolved"],
        "allTimedInvocationsNumericallyResolved": result["allTimedInvocationsNumericallyResolved"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
