#!/usr/bin/env python3
"""Recovery1 for the full-grid optical-property format probe.

Run 33037957904 reached libRadtran optical-property setup but exited before
NetCDF materialization because `write_optical_properties` requires an explicit
extraterrestrial solar spectrum.  This recovery changes exactly that
infrastructure detail by binding the already-used libRadtran
`solar_flux/atlas_plus_modtran` file.  The training-knot atmosphere state,
401-point wavelength request, and all closed claim boundaries are unchanged.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BASE_PROBE_PATH = HERE / "probe_vertical_optical_grid_format_v1.py"


def _load_base_probe():
    spec = importlib.util.spec_from_file_location("stellar_optical_grid_format_probe_v1_for_recovery1", BASE_PROBE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen format-probe v1 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = _load_base_probe()
base = probe.base

STAGE_ID = "native-stellar-zenith-optical-grid-format-probe-recovery1"
FAILED_RUN_ID = 33037957904
FAILURE_REASON = "WRITE_OPTICAL_PROPERTIES_REQUIRES_EXPLICIT_SOLAR_SOURCE_FILENAME"
RECOVERY_CHANGE_SCOPE = "solar-source-filename-only"
SOLAR_FLUX_RELATIVE_PATH = Path("solar_flux/atlas_plus_modtran")

OBSERVER_ELEVATION_M = probe.OBSERVER_ELEVATION_M
AOD550 = probe.AOD550
SZA_DEG = probe.SZA_DEG
WAVELENGTH_NM = probe.WAVELENGTH_NM
UVSPEC_SHA256 = probe.UVSPEC_SHA256
AFGLUS_SHA256 = probe.AFGLUS_SHA256
ProbeRefusal = probe.ProbeRefusal


def render_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path) -> str:
    grid = base.elevated_site_grid_ascending(atmosphere_file, OBSERVER_ELEVATION_M)
    solar_flux = Path(data_dir) / SOLAR_FLUX_RELATIVE_PATH
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        f"source solar {solar_flux}",
        f"mol_abs_param {base.MOL_ABS_PARAM}",
        f"wavelength_grid_file {Path(wavelength_grid_file)}",
        f"wavelength {WAVELENGTH_NM[0]} {WAVELENGTH_NM[-1]}",
        f"sza {SZA_DEG:.8f}",
        f"atm_z_grid {' '.join(f'{z:.6f}' for z in grid)}",
        "zout 0.000000",
        f"albedo {base.SURFACE_ALBEDO:.8f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {AOD550:.8f}",
        "rte_solver disort",
        "write_optical_properties",
        "verbose",
    ]
    text = "\n".join(lines) + "\n"
    lower = text.lower()
    if "rte_solver mystic" in lower or "mc_" in lower:
        raise ProbeRefusal("scientific stochastic solver directive forbidden")
    if text.count("source solar ") != 1 or str(SOLAR_FLUX_RELATIVE_PATH) not in text:
        raise ProbeRefusal("recovery must bind exactly one explicit solar source filename")
    return text


def execute(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
            wavelength_grid_file: Path, output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise ProbeRefusal("probe execution requires explicit allow_execution=True")
    solar_flux = Path(data_dir) / SOLAR_FLUX_RELATIVE_PATH
    if not solar_flux.is_file():
        raise ProbeRefusal(f"required recovery solar source missing: {solar_flux}")

    # Preserve the reviewed v1 implementation and replace only its renderer.
    original_renderer = probe.render_input
    try:
        probe.render_input = render_input
        result = probe.execute(
            uvspec=uvspec,
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            wavelength_grid_file=wavelength_grid_file,
            output_dir=output_dir,
            allow_execution=True,
        )
    finally:
        probe.render_input = original_renderer

    result = dict(result)
    result.update({
        "stageId": STAGE_ID,
        "recoveryOfRunId": FAILED_RUN_ID,
        "priorFailureReason": FAILURE_REASON,
        "recoveryChangeScope": RECOVERY_CHANGE_SCOPE,
        "scientificMethodChanged": False,
        "scientificInputsChanged": False,
        "trainingCoordinateChanged": False,
        "protectedHoldoutOpened": False,
        "solarSourceFile": str(solar_flux),
    })
    result["claimBoundary"] = {
        **(result.get("claimBoundary") or {}),
        "formatDiscoveryOnly": True,
        "protectedHoldoutOpened": False,
        "modelFitPerformed": False,
        "stellarAcceptanceGateEvaluated": False,
        "productionAuthorized": False,
    }
    Path(output_dir, "format-probe-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-execution", action="store_true")
    parser.add_argument("--uvspec", type=Path)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--atmosphere-file", type=Path)
    parser.add_argument("--wavelength-grid-file", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({
            "stageId": STAGE_ID,
            "status": "REVIEW_ONLY_NO_EXECUTION",
            "recoveryOfRunId": FAILED_RUN_ID,
            "priorFailureReason": FAILURE_REASON,
            "recoveryChangeScope": RECOVERY_CHANGE_SCOPE,
            "observerElevationM": OBSERVER_ELEVATION_M,
            "aod550": AOD550,
            "requestedWavelengthCount": len(WAVELENGTH_NM),
            "protectedHoldoutOpened": False,
            "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    required = [args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file, args.output_dir]
    if any(value is None for value in required):
        raise ProbeRefusal("execution requires all explicit paths")
    result = execute(
        uvspec=args.uvspec,
        data_dir=args.data_dir,
        atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file,
        output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({
        "status": result["status"],
        "stageId": result["stageId"],
        "recoveryOfRunId": result["recoveryOfRunId"],
        "outputDtauc": result["netcdf"]["outputDtauc"],
        "wavelengthSizedDimensions": result["netcdf"]["wavelengthSizedDimensions"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
