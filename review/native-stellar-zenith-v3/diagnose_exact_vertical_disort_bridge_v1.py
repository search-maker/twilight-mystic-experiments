#!/usr/bin/env python3
"""Training-only exact-vertical DISORT bridge diagnostic v1.

Frozen before execution. This script does not open the protected stellar holdout,
fit a model, modify any acceptance gate, or authorize production.
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
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_for_vertical_bridge", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load native stellar zenith v3 base")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()

STAGE_ID = "native-stellar-zenith-exact-vertical-disort-bridge-v1"
MYSTIC_STATE = base.MYSTIC_STATE
WAVELENGTH_NM = base.WAVELENGTH_NM
AFGLUS_SHA256 = base.AFGLUS_SHA256
UVSPEC_SHA256 = base.UVSPEC_SHA256
SOURCE_SED_SHA256 = base.SOURCE_SED_SHA256
SOURCE_JOHNSON_V_SHA256 = base.SOURCE_JOHNSON_V_SHA256
REPRESENTATIVE_LIBRARY_NUMBERS = base.REPRESENTATIVE_LIBRARY_NUMBERS
SURFACE_ALBEDO = base.SURFACE_ALBEDO
MOL_ABS_PARAM = base.MOL_ABS_PARAM

ELEVATION_M = (0.0, 2500.0)
AOD550 = (0.05, 0.40)
DISORT_SZA_DEG = (0.0, 0.5, 1.0)
SDISORT_SZA_DEG = (0.5, 1.0)
EXPECTED_SOLVER_CALLS = 20
MAX_ABS_DELTA_VERTICAL_TAU = 5e-6
MAX_ABS_DELTA_SOLVER_BRIDGE_TAU = 5e-6
MAX_ABS_DELTA_AV_MAG = 1e-4


class BridgeRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def finite(name: str, value: object) -> float:
    try:
        return base.finite(name, value)
    except Exception as exc:
        raise BridgeRefusal(str(exc)) from exc


def mu_from_sza(sza_deg: float) -> float:
    sza = finite("szaDeg", sza_deg)
    if not 0.0 <= sza < 90.0:
        raise BridgeRefusal("SZA must be in [0,90)")
    mu = math.cos(math.radians(sza))
    if not mu > 0:
        raise BridgeRefusal("source-direction cosine must be positive")
    return mu


def build_case_universe() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for elevation in ELEVATION_M:
        for aod in AOD550:
            for sza in DISORT_SZA_DEG:
                rows.append({"solver": "disort", "szaDeg": sza, "observerElevationM": elevation, "aod550": aod})
            for sza in SDISORT_SZA_DEG:
                rows.append({"solver": "sdisort", "szaDeg": sza, "observerElevationM": elevation, "aod550": aod})
    return rows


def validate_case_universe() -> None:
    rows = build_case_universe()
    if len(rows) != EXPECTED_SOLVER_CALLS:
        raise BridgeRefusal(f"expected {EXPECTED_SOLVER_CALLS} cases, got {len(rows)}")
    keys = {(r["solver"], r["szaDeg"], r["observerElevationM"], r["aod550"]) for r in rows}
    if len(keys) != EXPECTED_SOLVER_CALLS:
        raise BridgeRefusal("diagnostic case universe is not unique")
    if any(r["solver"] == "sdisort" and r["szaDeg"] == 0 for r in rows):
        raise BridgeRefusal("proven SDISORT umu0=1 endpoint must not be executed")


def render_uvspec_input(*, solver: str, sza_deg: float, observer_elevation_m: float, aod550: float,
                        data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path) -> str:
    solver = str(solver).strip().lower()
    sza = finite("szaDeg", sza_deg)
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    if solver not in {"disort", "sdisort"}:
        raise BridgeRefusal("solver must be disort or sdisort")
    if solver == "disort" and sza not in DISORT_SZA_DEG:
        raise BridgeRefusal("DISORT SZA outside frozen diagnostic universe")
    if solver == "sdisort" and sza not in SDISORT_SZA_DEG:
        raise BridgeRefusal("SDISORT SZA outside frozen diagnostic universe")
    if elevation not in ELEVATION_M or aod not in AOD550:
        raise BridgeRefusal("atmosphere corner outside frozen diagnostic universe")
    try:
        grid = base.elevated_site_grid_ascending(atmosphere_file, elevation)
    except Exception as exc:
        raise BridgeRefusal(str(exc)) from exc
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
        f"mol_abs_param {MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {WAVELENGTH_NM[0]} {WAVELENGTH_NM[-1]}",
        f"sza {sza:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {aod:.8f}",
        f"rte_solver {solver}",
    ]
    if solver == "sdisort":
        lines.append("sdisort nscat 1")
    lines.extend([
        "output_quantity transmittance",
        "output_user lambda edir",
        "quiet",
    ])
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    if "rte_solver mystic" in lower or "mc_" in lower or "aerosol_species_file" in lower or "angstrom" in lower:
        raise BridgeRefusal("forbidden directive emitted")
    if solver == "disort" and "sdisort nscat" in lower:
        raise BridgeRefusal("SDISORT option leaked into DISORT case")
    return text


def parse_direct_transmission(stdout_text: str, *, sza_deg: float) -> dict[str, Any]:
    mu = mu_from_sza(sza_deg)
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise BridgeRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        if abs(wavelength - round(wavelength)) > 1e-9:
            raise BridgeRefusal("non-integral wavelength in exact 1-nm output")
        ray_t = edir / mu
        if ray_t <= 0 or ray_t > 1.000001:
            raise BridgeRefusal(f"invalid direct transmission at {wavelength} nm: {ray_t}")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, ray_t))
    if wavelengths != list(WAVELENGTH_NM):
        raise BridgeRefusal("uvspec output grid is not exact 380..780 nm / 1 nm")
    tau_los = [-math.log(value) for value in transmission]
    return {
        "wavelengthNm": wavelengths,
        "lineOfSightDirectTransmission": transmission,
        "lineOfSightDirectOpticalDepth": tau_los,
        "szaDeg": float(sza_deg),
        "mu": mu,
    }


def reconstructed_vertical_optical_depth(parsed: dict[str, Any]) -> list[float]:
    mu = finite("mu", parsed["mu"])
    return [mu * finite("tauLos", value) for value in parsed["lineOfSightDirectOpticalDepth"]]


def exact_vertical_optical_depth(parsed_disort_sza0: dict[str, Any]) -> list[float]:
    if abs(float(parsed_disort_sza0.get("szaDeg")) - 0.0) > 1e-15:
        raise BridgeRefusal("exact vertical reference must be DISORT SZA 0")
    if abs(float(parsed_disort_sza0.get("mu")) - 1.0) > 1e-15:
        raise BridgeRefusal("exact vertical reference must have mu=1")
    return [finite("tauVertical", value) for value in parsed_disort_sza0["lineOfSightDirectOpticalDepth"]]


def max_abs_delta(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        raise BridgeRefusal("comparison vector shape mismatch")
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


def _photometry(root: Path, sed_bundle_path: Path, johnson_v_path: Path):
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise BridgeRefusal("Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise BridgeRefusal("Johnson-V SHA-256 drift")
    phot = base._load_v1_photometry(root)
    _, wavelength_nm, band_response, representatives = phot.load_bound_photometric_assets(
        sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path
    )
    reps = [r for r in representatives if int(r["libraryNumber"]) in REPRESENTATIVE_LIBRARY_NUMBERS]
    if [int(r["libraryNumber"]) for r in reps] != list(REPRESENTATIVE_LIBRARY_NUMBERS):
        raise BridgeRefusal("Pickles representative identity drift")
    return phot, wavelength_nm, band_response, reps


def photometric_max_abs_delta(*, transmission_a: list[float], transmission_b: list[float],
                              phot: Any, wavelength_nm: list[float], band_response: list[float], reps: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    for sed in reps:
        flux = [float(x) for x in sed["fluxRelative"]]
        av_a = phot.band_extinction_mag(
            wavelength_nm=wavelength_nm, flux_relative=flux, band_response=band_response, transmission=transmission_a
        )
        av_b = phot.band_extinction_mag(
            wavelength_nm=wavelength_nm, flux_relative=flux, band_response=band_response, transmission=transmission_b
        )
        rows.append({"libraryNumber": int(sed["libraryNumber"]), "aMag": av_a, "bMag": av_b, "deltaAvMag": av_a - av_b})
    return max(abs(row["deltaAvMag"]) for row in rows), rows


def evaluate_results(*, root: Path, results: dict[tuple[str, float, float, float], dict[str, Any]],
                     sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    expected = {(r["solver"], float(r["szaDeg"]), float(r["observerElevationM"]), float(r["aod550"])) for r in build_case_universe()}
    if set(results) != expected:
        raise BridgeRefusal("result universe incomplete or drifted")
    phot, wavelength_nm, band_response, reps = _photometry(root, sed_bundle_path, johnson_v_path)
    corners = []
    all_vertical_tau_delta: list[float] = []
    all_bridge_tau_delta: list[float] = []
    all_phot_delta: list[float] = []
    for elevation in ELEVATION_M:
        for aod in AOD550:
            d0 = results[("disort", 0.0, elevation, aod)]
            tau0 = exact_vertical_optical_depth(d0)
            t0 = [math.exp(-tau) for tau in tau0]
            comparisons = []
            for sza in (0.5, 1.0):
                dp = results[("disort", sza, elevation, aod)]
                sp = results[("sdisort", sza, elevation, aod)]
                tau_v = reconstructed_vertical_optical_depth(dp)
                vertical_tau_delta = max_abs_delta(tau_v, tau0)
                t_v = [math.exp(-tau) for tau in tau_v]
                vertical_av_delta, vertical_av_rows = photometric_max_abs_delta(
                    transmission_a=t_v, transmission_b=t0,
                    phot=phot, wavelength_nm=wavelength_nm, band_response=band_response, reps=reps,
                )
                bridge_tau_delta = max_abs_delta(
                    dp["lineOfSightDirectOpticalDepth"], sp["lineOfSightDirectOpticalDepth"]
                )
                bridge_av_delta, bridge_av_rows = photometric_max_abs_delta(
                    transmission_a=dp["lineOfSightDirectTransmission"],
                    transmission_b=sp["lineOfSightDirectTransmission"],
                    phot=phot, wavelength_nm=wavelength_nm, band_response=band_response, reps=reps,
                )
                all_vertical_tau_delta.append(vertical_tau_delta)
                all_bridge_tau_delta.append(bridge_tau_delta)
                all_phot_delta.extend([vertical_av_delta, bridge_av_delta])
                comparisons.append({
                    "szaDeg": sza,
                    "planeParallelVerticalReconstruction": {
                        "maxAbsDeltaVerticalOpticalDepth": vertical_tau_delta,
                        "maxAbsDeltaAvMag": vertical_av_delta,
                        "sedComparisons": vertical_av_rows,
                    },
                    "nearZenithSolverBridge": {
                        "maxAbsDeltaLineOfSightOpticalDepth": bridge_tau_delta,
                        "maxAbsDeltaAvMag": bridge_av_delta,
                        "sedComparisons": bridge_av_rows,
                    },
                })
            corners.append({"observerElevationM": elevation, "aod550": aod, "comparisons": comparisons})
    metrics = {
        "maxAbsDeltaVerticalOpticalDepth": max(all_vertical_tau_delta),
        "maxAbsDeltaSolverBridgeOpticalDepth": max(all_bridge_tau_delta),
        "maxAbsDeltaAvMag": max(all_phot_delta),
        "maxAbsDeltaVerticalOpticalDepthLimit": MAX_ABS_DELTA_VERTICAL_TAU,
        "maxAbsDeltaSolverBridgeOpticalDepthLimit": MAX_ABS_DELTA_SOLVER_BRIDGE_TAU,
        "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
    }
    metrics["verticalOpticalDepthPassed"] = metrics["maxAbsDeltaVerticalOpticalDepth"] <= MAX_ABS_DELTA_VERTICAL_TAU
    metrics["solverBridgeOpticalDepthPassed"] = metrics["maxAbsDeltaSolverBridgeOpticalDepth"] <= MAX_ABS_DELTA_SOLVER_BRIDGE_TAU
    metrics["photometryPassed"] = metrics["maxAbsDeltaAvMag"] <= MAX_ABS_DELTA_AV_MAG
    passed = metrics["verticalOpticalDepthPassed"] and metrics["solverBridgeOpticalDepthPassed"] and metrics["photometryPassed"]
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "EXACT_VERTICAL_DISORT_BRIDGE_DIAGNOSTIC_PASS" if passed else "EXACT_VERTICAL_DISORT_BRIDGE_DIAGNOSTIC_FAIL",
        "mysticState": MYSTIC_STATE,
        "solverInvocationCount": EXPECTED_SOLVER_CALLS,
        "atmosphereCornerCount": 4,
        "disortSzaDeg": list(DISORT_SZA_DEG),
        "sdisortSzaDeg": list(SDISORT_SZA_DEG),
        "metrics": metrics,
        "corners": corners,
        "claimBoundary": {
            "trainingOnlyDiagnostic": True,
            "protectedHoldoutOpened": False,
            "modelFitPerformed": False,
            "stellarLutAcceptanceGateEvaluated": False,
            "v32MethodAuthorizedForDraftOnlyIfPass": passed,
            "productionAuthorized": False,
            "empiricalRealSkyValidated": False,
            "humanFirstSeeingValidated": False,
        },
    }


def _safe(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".").replace(".", "p")


def execute_case(*, row: dict[str, Any], uvspec: Path, data_dir: Path, atmosphere_file: Path,
                 wavelength_grid_file: Path, output_dir: Path, index: int) -> dict[str, Any]:
    text = render_uvspec_input(
        solver=row["solver"], sza_deg=row["szaDeg"], observer_elevation_m=row["observerElevationM"],
        aod550=row["aod550"], data_dir=data_dir, atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
    )
    case_dir = output_dir / "raw" / (
        f"{index:02d}-{row['solver']}-sza{_safe(row['szaDeg'])}-e{_safe(row['observerElevationM'])}-a{_safe(row['aod550'])}"
    )
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "case.inp").write_text(text, encoding="utf-8")
    completed = subprocess.run([str(uvspec)], input=text, text=True, capture_output=True, check=False, timeout=180)
    (case_dir / "case.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (case_dir / "case.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    meta = {
        "schemaVersion": 1, "stageId": STAGE_ID, "caseIndex": index, **row,
        "solverReturnCode": completed.returncode,
        "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
        "stdoutSha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderrSha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
    }
    if completed.returncode != 0:
        meta["status"] = "SOLVER_FAILED"
        (case_dir / "case.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise BridgeRefusal(f"uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    try:
        parsed = parse_direct_transmission(completed.stdout, sza_deg=row["szaDeg"])
    except Exception as exc:
        meta["status"] = "PARSE_FAILED"
        meta["failure"] = str(exc)
        (case_dir / "case.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    meta["status"] = "CASE_EXECUTED_AND_PARSED"
    meta["wavelengthCount"] = len(parsed["wavelengthNm"])
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**row, **parsed, "inputSha256": meta["inputSha256"]}


def execute_campaign(*, root: Path, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, sed_bundle_path: Path, johnson_v_path: Path,
                     output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise BridgeRefusal("scientific solver execution requires explicit allow_execution=True")
    validate_case_universe()
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise BridgeRefusal("uvspec SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise BridgeRefusal("AFGLUS SHA-256 drift")
    grid = [int(x) for x in Path(wavelength_grid_file).read_text().splitlines() if x.strip()]
    if grid != list(WAVELENGTH_NM):
        raise BridgeRefusal("wavelength-grid drift")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256 or sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise BridgeRefusal("frozen photometric asset identity drift")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    results: dict[tuple[str, float, float, float], dict[str, Any]] = {}
    failures = []
    for index, row in enumerate(build_case_universe(), start=1):
        try:
            result = execute_case(
                row=row, uvspec=uvspec, data_dir=data_dir, atmosphere_file=atmosphere_file,
                wavelength_grid_file=wavelength_grid_file, output_dir=output_dir, index=index,
            )
            key = (row["solver"], float(row["szaDeg"]), float(row["observerElevationM"]), float(row["aod550"]))
            results[key] = result
        except Exception as exc:
            failures.append({"caseIndex": index, **row, "failure": str(exc)})
    if failures:
        summary = {
            "schemaVersion": 1, "stageId": STAGE_ID,
            "status": "EXACT_VERTICAL_DISORT_BRIDGE_DIAGNOSTIC_FAIL",
            "solverInvocationCount": EXPECTED_SOLVER_CALLS,
            "successfulParsedCaseCount": len(results), "failures": failures,
            "claimBoundary": {"protectedHoldoutOpened": False, "modelFitPerformed": False, "productionAuthorized": False},
        }
    else:
        summary = evaluate_results(
            root=root, results=results, sed_bundle_path=sed_bundle_path, johnson_v_path=johnson_v_path
        )
    summary_path = output_dir / "exact-vertical-disort-bridge-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--sed-bundle", type=Path)
    parser.add_argument("--johnson-v", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        validate_case_universe()
        print(json.dumps({
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION", "stageId": STAGE_ID,
            "solverInvocationCount": EXPECTED_SOLVER_CALLS,
            "maxAbsDeltaVerticalOpticalDepthLimit": MAX_ABS_DELTA_VERTICAL_TAU,
            "maxAbsDeltaSolverBridgeOpticalDepthLimit": MAX_ABS_DELTA_SOLVER_BRIDGE_TAU,
            "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
            "protectedHoldoutOpened": False, "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    required = [args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file,
                args.sed_bundle, args.johnson_v, args.output_dir]
    if any(x is None for x in required):
        raise BridgeRefusal("execution requires all explicit bound paths")
    summary = execute_campaign(
        root=args.root, uvspec=args.uvspec, data_dir=args.data_dir, atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file, sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v, output_dir=args.output_dir, allow_execution=args.allow_execution,
    )
    print(json.dumps({"status": summary["status"], "metrics": summary.get("metrics")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
