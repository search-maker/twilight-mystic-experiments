#!/usr/bin/env python3
"""Training-only exact-vertical optical-column diagnostic v1.

Frozen protocol: EXACT_VERTICAL_OPTICAL_COLUMN_PROTOCOL_V1.md.
No protected holdout is opened and no model is fit by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_PATH = HERE / "native_stellar_zenith_v3.py"
BRIDGE_PATH = HERE / "diagnose_exact_vertical_disort_bridge_v1.py"
TIER1_PARSER_PATH = ROOT / "experiments/mystic-batch-v1/twilight_surrogate_tier1_atm_z_grid_equivalence_proof.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load(BASE_PATH, "native_stellar_zenith_v3_for_optical_column")
bridge = _load(BRIDGE_PATH, "native_stellar_vertical_bridge_for_optical_column")
tier1 = _load(TIER1_PARSER_PATH, "tier1_verbose_optical_parser_for_stellar_vertical")

STAGE_ID = "native-stellar-zenith-exact-vertical-optical-column-v1"
MYSTIC_STATE = base.MYSTIC_STATE
WAVELENGTH_NM = base.WAVELENGTH_NM
AFGLUS_SHA256 = base.AFGLUS_SHA256
UVSPEC_SHA256 = base.UVSPEC_SHA256
SOURCE_SED_SHA256 = base.SOURCE_SED_SHA256
SOURCE_JOHNSON_V_SHA256 = base.SOURCE_JOHNSON_V_SHA256
REPRESENTATIVE_LIBRARY_NUMBERS = base.REPRESENTATIVE_LIBRARY_NUMBERS
SURFACE_ALBEDO = base.SURFACE_ALBEDO
MOL_ABS_PARAM = base.MOL_ABS_PARAM

CASE_UNIVERSE = (
    (500.0, 0.30),
    (1250.0, 0.10),
    (1250.0, 0.30),
    (2000.0, 0.20),
)
EXPECTED_SOLVER_CALLS = 4
NUMBER_OF_STREAMS = 16
MAX_ABS_DELTA_TAU = 1.0e-5
MAX_ABS_DELTA_AV_MAG = 1.0e-4
FINAL_WAVELENGTH_RE = re.compile(
    r"^\*\*\* wavelength: iv = (\d+), ([0-9]+(?:\.[0-9]+)?) nm, albedo = ([0-9]+(?:\.[0-9]+)?)\s*$",
    re.MULTILINE,
)


class OpticalColumnRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def finite(name: str, value: object) -> float:
    try:
        return base.finite(name, value)
    except Exception as exc:
        raise OpticalColumnRefusal(str(exc)) from exc


def validate_case_universe() -> None:
    if len(CASE_UNIVERSE) != EXPECTED_SOLVER_CALLS:
        raise OpticalColumnRefusal("frozen case count drift")
    if len(set(CASE_UNIVERSE)) != EXPECTED_SOLVER_CALLS:
        raise OpticalColumnRefusal("frozen cases are not unique")
    for elevation, aod in CASE_UNIVERSE:
        if elevation not in base.ELEVATION_KNOTS_M or aod not in base.AOD_KNOTS:
            raise OpticalColumnRefusal("diagnostic point left frozen stellar training axes")
        if elevation in (0.0, 2500.0):
            raise OpticalColumnRefusal("diagnostic reused old DISORT bridge corner")


def render_uvspec_input(*, observer_elevation_m: float, aod550: float, data_dir: Path,
                        atmosphere_file: Path, wavelength_grid_file: Path) -> str:
    elevation = finite("observerElevationM", observer_elevation_m)
    aod = finite("aod550", aod550)
    if (elevation, aod) not in CASE_UNIVERSE:
        raise OpticalColumnRefusal("atmosphere state outside frozen diagnostic universe")
    try:
        grid = base.elevated_site_grid_ascending(atmosphere_file, elevation)
    except Exception as exc:
        raise OpticalColumnRefusal(str(exc)) from exc
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
        f"number_of_streams {NUMBER_OF_STREAMS}",
        "output_quantity transmittance",
        "output_user lambda edir",
        "verbose",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    for forbidden in (
        "write_optical_properties", "rte_solver mystic", "rte_solver sdisort",
        "sdisort nscat", "mc_", "aerosol_species_file", "angstrom", "altitude ",
        "mc_elevation_file",
    ):
        if forbidden in lower:
            raise OpticalColumnRefusal(f"forbidden directive emitted: {forbidden}")
    if text.count("source solar ") != 1 or "atlas_plus_modtran" not in text:
        raise OpticalColumnRefusal("explicit packaged solar source missing")
    return text


def parse_direct_transmission(stdout_text: str, expected_grid: Sequence[int] = WAVELENGTH_NM) -> dict[str, Any]:
    wavelengths: list[int] = []
    transmission: list[float] = []
    for raw in stdout_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise OpticalColumnRefusal(f"unexpected uvspec output: {raw!r}")
        wavelength = finite("wavelength", parts[0])
        edir = finite("edir", parts[1])
        if abs(wavelength - round(wavelength)) > 1.0e-9:
            raise OpticalColumnRefusal("non-integral wavelength in 1-nm output")
        if not 0.0 < edir <= 1.000001:
            raise OpticalColumnRefusal(f"invalid exact-vertical direct transmission at {wavelength} nm: {edir}")
        wavelengths.append(int(round(wavelength)))
        transmission.append(min(1.0, edir))
    if wavelengths != list(expected_grid):
        raise OpticalColumnRefusal("uvspec direct-transmission grid mismatch")
    return {
        "wavelengthNm": wavelengths,
        "directTransmission": transmission,
        "directOpticalDepth": [-math.log(value) for value in transmission],
    }


def parse_verbose_optical_columns(stderr_text: str, *, expected_grid: Sequence[int] = WAVELENGTH_NM,
                                  expected_layer_count: int) -> dict[str, Any]:
    matches = list(FINAL_WAVELENGTH_RE.finditer(stderr_text))
    if len(matches) != len(expected_grid):
        raise OpticalColumnRefusal(
            f"expected {len(expected_grid)} final solve-stage wavelength blocks, got {len(matches)}"
        )
    wavelengths: list[int] = []
    column_tau: list[float] = []
    layer_counts: list[int] = []
    for position, match in enumerate(matches):
        iv = int(match.group(1))
        wavelength = finite("verbose wavelength", match.group(2))
        albedo = finite("verbose albedo", match.group(3))
        expected_wavelength = int(expected_grid[position])
        if iv != position:
            raise OpticalColumnRefusal(f"verbose wavelength index drift: {iv} != {position}")
        if abs(wavelength - expected_wavelength) > 1.0e-9:
            raise OpticalColumnRefusal(
                f"verbose wavelength drift at iv={iv}: {wavelength} != {expected_wavelength}"
            )
        if abs(albedo - SURFACE_ALBEDO) > 1.0e-9:
            raise OpticalColumnRefusal("verbose solve-stage albedo drift")
        end = matches[position + 1].start() if position + 1 < len(matches) else len(stderr_text)
        block = stderr_text[match.start():end]
        if block.count("*** optical_properties()") != 1:
            raise OpticalColumnRefusal(f"iv={iv} does not contain exactly one optical_properties table")
        try:
            table = tier1.parse_resolved_optical_table(block)
        except Exception as exc:
            raise OpticalColumnRefusal(f"iv={iv} optical table parse failed: {exc}") from exc
        layer_count = len(table["totalLayerOpticalDepth"])
        if layer_count != expected_layer_count:
            raise OpticalColumnRefusal(
                f"iv={iv} layer count drift: {layer_count} != {expected_layer_count}"
            )
        for cloud_key in (
            "waterCloudScatteringLayerOpticalDepth", "waterCloudAbsorptionLayerOpticalDepth",
            "iceCloudScatteringLayerOpticalDepth", "iceCloudAbsorptionLayerOpticalDepth",
        ):
            if any(abs(finite(cloud_key, value)) > 0.0 for value in table[cloud_key]):
                raise OpticalColumnRefusal(f"configured cloud optical depth is nonzero at iv={iv}")
        tau = sum(finite("totalLayerOpticalDepth", value) for value in table["totalLayerOpticalDepth"])
        if tau < 0.0:
            raise OpticalColumnRefusal(f"negative resolved optical column at iv={iv}")
        wavelengths.append(expected_wavelength)
        column_tau.append(tau)
        layer_counts.append(layer_count)
    return {
        "wavelengthNm": wavelengths,
        "verboseColumnOpticalDepth": column_tau,
        "layerCountByWavelength": layer_counts,
    }


def max_abs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        raise OpticalColumnRefusal("comparison vector shape mismatch")
    return max(abs(finite("left", x) - finite("right", y)) for x, y in zip(a, b, strict=True))


def _photometry(root: Path, sed_bundle_path: Path, johnson_v_path: Path):
    try:
        return bridge._photometry(root, sed_bundle_path, johnson_v_path)
    except Exception as exc:
        raise OpticalColumnRefusal(str(exc)) from exc


def evaluate_case(*, root: Path, parsed_direct: dict[str, Any], parsed_verbose: dict[str, Any],
                  sed_bundle_path: Path, johnson_v_path: Path) -> dict[str, Any]:
    if parsed_direct["wavelengthNm"] != parsed_verbose["wavelengthNm"]:
        raise OpticalColumnRefusal("direct and verbose wavelength grids differ")
    tau_direct = [finite("tauDirect", x) for x in parsed_direct["directOpticalDepth"]]
    tau_verbose = [finite("tauVerbose", x) for x in parsed_verbose["verboseColumnOpticalDepth"]]
    spectral_delta = [abs(a - b) for a, b in zip(tau_direct, tau_verbose, strict=True)]
    max_tau_delta = max(spectral_delta)
    max_index = spectral_delta.index(max_tau_delta)
    phot, wavelength_nm, band_response, reps = _photometry(root, sed_bundle_path, johnson_v_path)
    direct_t = [math.exp(-x) for x in tau_direct]
    verbose_t = [math.exp(-x) for x in tau_verbose]
    max_av_delta, sed_rows = bridge.photometric_max_abs_delta(
        transmission_a=direct_t,
        transmission_b=verbose_t,
        phot=phot,
        wavelength_nm=wavelength_nm,
        band_response=band_response,
        reps=reps,
    )
    return {
        "maxAbsDeltaOpticalDepth": max_tau_delta,
        "maxAbsDeltaOpticalDepthWavelengthNm": parsed_direct["wavelengthNm"][max_index],
        "maxAbsDeltaAvMag": max_av_delta,
        "sedComparisons": sed_rows,
        "spectralOpticalColumnPassed": max_tau_delta <= MAX_ABS_DELTA_TAU,
        "johnsonVConsequencePassed": max_av_delta <= MAX_ABS_DELTA_AV_MAG,
    }


def _safe(value: float) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".").replace(".", "p")


def execute_case(*, root: Path, observer_elevation_m: float, aod550: float, uvspec: Path,
                 data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path,
                 sed_bundle_path: Path, johnson_v_path: Path, output_dir: Path,
                 index: int) -> dict[str, Any]:
    text = render_uvspec_input(
        observer_elevation_m=observer_elevation_m,
        aod550=aod550,
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        wavelength_grid_file=wavelength_grid_file,
    )
    grid = base.elevated_site_grid_ascending(atmosphere_file, observer_elevation_m)
    expected_layer_count = len(grid) - 1
    case_dir = output_dir / "raw" / f"{index:02d}-e{_safe(observer_elevation_m)}-a{_safe(aod550)}"
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "case.inp").write_text(text, encoding="utf-8")
    completed = subprocess.run(
        [str(uvspec)], input=text, text=True, capture_output=True, check=False,
        timeout=300, cwd=case_dir,
    )
    (case_dir / "case.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (case_dir / "case.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "caseIndex": index,
        "observerElevationM": observer_elevation_m,
        "aod550": aod550,
        "szaDeg": 0.0,
        "solver": "disort",
        "solverReturnCode": completed.returncode,
        "expectedLayerCount": expected_layer_count,
        "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
        "stdoutSha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderrSha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
    }
    if completed.returncode != 0:
        meta["status"] = "SOLVER_FAILED"
        (case_dir / "case.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise OpticalColumnRefusal(f"uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    direct = parse_direct_transmission(completed.stdout)
    verbose = parse_verbose_optical_columns(
        completed.stderr, expected_layer_count=expected_layer_count
    )
    metrics = evaluate_case(
        root=root,
        parsed_direct=direct,
        parsed_verbose=verbose,
        sed_bundle_path=sed_bundle_path,
        johnson_v_path=johnson_v_path,
    )
    parsed = {
        "wavelengthNm": direct["wavelengthNm"],
        "directTransmission": direct["directTransmission"],
        "directOpticalDepth": direct["directOpticalDepth"],
        "verboseColumnOpticalDepth": verbose["verboseColumnOpticalDepth"],
        "layerCountByWavelength": verbose["layerCountByWavelength"],
        "metrics": metrics,
    }
    parsed_path = case_dir / "parsed-optical-column.json"
    parsed_path.write_text(json.dumps(parsed, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    meta.update({
        "status": "CASE_EXECUTED_AND_PARSED",
        "wavelengthCount": len(direct["wavelengthNm"]),
        "parsedSha256": sha256_file(parsed_path),
        "metrics": metrics,
    })
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return meta


def execute_campaign(*, root: Path, uvspec: Path, data_dir: Path, atmosphere_file: Path,
                     wavelength_grid_file: Path, sed_bundle_path: Path, johnson_v_path: Path,
                     output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise OpticalColumnRefusal("scientific solver execution requires explicit allow_execution=True")
    validate_case_universe()
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise OpticalColumnRefusal("uvspec SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise OpticalColumnRefusal("AFGLUS SHA-256 drift")
    solar_source = Path(data_dir) / "solar_flux" / "atlas_plus_modtran"
    if not solar_source.is_file():
        raise OpticalColumnRefusal("explicit packaged solar source missing")
    grid = [int(x) for x in Path(wavelength_grid_file).read_text().splitlines() if x.strip()]
    if grid != list(WAVELENGTH_NM):
        raise OpticalColumnRefusal("wavelength-grid drift")
    if sha256_file(sed_bundle_path) != SOURCE_SED_SHA256:
        raise OpticalColumnRefusal("Pickles SED bundle SHA-256 drift")
    if sha256_file(johnson_v_path) != SOURCE_JOHNSON_V_SHA256:
        raise OpticalColumnRefusal("Johnson-V SHA-256 drift")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    cases: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, (elevation, aod) in enumerate(CASE_UNIVERSE, start=1):
        try:
            cases.append(execute_case(
                root=root,
                observer_elevation_m=elevation,
                aod550=aod,
                uvspec=uvspec,
                data_dir=data_dir,
                atmosphere_file=atmosphere_file,
                wavelength_grid_file=wavelength_grid_file,
                sed_bundle_path=sed_bundle_path,
                johnson_v_path=johnson_v_path,
                output_dir=output_dir,
                index=index,
            ))
        except Exception as exc:
            failures.append({
                "caseIndex": index,
                "observerElevationM": elevation,
                "aod550": aod,
                "failure": str(exc),
            })
    if failures:
        summary = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_FAIL",
            "solverInvocationCount": EXPECTED_SOLVER_CALLS,
            "successfulParsedCaseCount": len(cases),
            "failures": failures,
        }
    else:
        max_tau = max(case["metrics"]["maxAbsDeltaOpticalDepth"] for case in cases)
        max_av = max(case["metrics"]["maxAbsDeltaAvMag"] for case in cases)
        passed = max_tau <= MAX_ABS_DELTA_TAU and max_av <= MAX_ABS_DELTA_AV_MAG
        summary = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": (
                "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_PASS"
                if passed else "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_FAIL"
            ),
            "mysticState": MYSTIC_STATE,
            "solverInvocationCount": EXPECTED_SOLVER_CALLS,
            "caseCount": len(cases),
            "metrics": {
                "maxAbsDeltaOpticalDepth": max_tau,
                "maxAbsDeltaOpticalDepthLimit": MAX_ABS_DELTA_TAU,
                "maxAbsDeltaAvMag": max_av,
                "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
                "spectralOpticalColumnPassed": max_tau <= MAX_ABS_DELTA_TAU,
                "johnsonVConsequencePassed": max_av <= MAX_ABS_DELTA_AV_MAG,
            },
            "cases": cases,
        }
    summary["claimBoundary"] = {
        "trainingOnlyDiagnostic": True,
        "protectedHoldoutOpened": False,
        "modelFitPerformed": False,
        "stellarLutAcceptanceGateEvaluated": False,
        "v32EndpointMethodAuthorizedForDraftOnlyIfPass": summary["status"] == "EXACT_VERTICAL_OPTICAL_COLUMN_DIAGNOSTIC_PASS",
        "productionAuthorized": False,
        "empiricalRealSkyValidated": False,
        "humanFirstSeeingValidated": False,
    }
    summary_path = output_dir / "exact-vertical-optical-column-summary.json"
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
            "status": "REVIEW_ONLY_NO_SOLVER_EXECUTION",
            "stageId": STAGE_ID,
            "solverInvocationCount": EXPECTED_SOLVER_CALLS,
            "caseUniverse": [
                {"observerElevationM": e, "aod550": a, "szaDeg": 0.0, "solver": "disort"}
                for e, a in CASE_UNIVERSE
            ],
            "maxAbsDeltaOpticalDepthLimit": MAX_ABS_DELTA_TAU,
            "maxAbsDeltaAvMagLimit": MAX_ABS_DELTA_AV_MAG,
            "protectedHoldoutOpened": False,
            "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    required = [
        args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file,
        args.sed_bundle, args.johnson_v, args.output_dir,
    ]
    if any(value is None for value in required):
        raise OpticalColumnRefusal("execution requires all explicit bound paths")
    summary = execute_campaign(
        root=args.root,
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        sed_bundle_path=args.sed_bundle,
        johnson_v_path=args.johnson_v,
        output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({"status": summary["status"], "metrics": summary.get("metrics")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
