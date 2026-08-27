#!/usr/bin/env python3
"""One-shot format probe for full-grid libRadtran optical properties.

This is infrastructure discovery only. It uses one existing stellar training-knot
atmosphere state and does not open the protected 64-case holdout, fit a model,
evaluate stellar acceptance gates, or authorize production.
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
    spec = importlib.util.spec_from_file_location("native_stellar_v3_for_optical_probe", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load native stellar zenith v3 base")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()
STAGE_ID = "native-stellar-zenith-optical-grid-format-probe-v1"
OBSERVER_ELEVATION_M = 500.0
AOD550 = 0.10
SZA_DEG = 0.0
WAVELENGTH_NM = base.WAVELENGTH_NM
UVSPEC_SHA256 = base.UVSPEC_SHA256
AFGLUS_SHA256 = base.AFGLUS_SHA256


class ProbeRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return base.sha256_file(path)


def render_input(*, data_dir: Path, atmosphere_file: Path, wavelength_grid_file: Path) -> str:
    grid = base.elevated_site_grid_ascending(atmosphere_file, OBSERVER_ELEVATION_M)
    lines = [
        f"data_files_path {Path(data_dir)}",
        f"atmosphere_file {Path(atmosphere_file)}",
        "source solar",
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
    if "rte_solver mystic" in text.lower() or "mc_" in text.lower():
        raise ProbeRefusal("scientific stochastic solver directive forbidden")
    return text


def _json_safe_scalar(value: Any) -> Any:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isfinite(number):
        return number
    return str(number)


def inspect_netcdf(path: Path) -> dict[str, Any]:
    try:
        from netCDF4 import Dataset  # type: ignore[import-not-found]
    except Exception as exc:
        raise ProbeRefusal(f"netCDF4 unavailable: {exc}") from exc
    if not path.is_file():
        raise ProbeRefusal("optical_properties.nc missing")
    variables: dict[str, Any] = {}
    dimensions: dict[str, int] = {}
    with Dataset(path, "r") as ds:
        dimensions = {name: len(dim) for name, dim in ds.dimensions.items()}
        for name, var in ds.variables.items():
            raw = var[:]
            if hasattr(raw, "filled"):
                raw = raw.filled(float("nan"))
            flat = raw.reshape(-1) if hasattr(raw, "reshape") else raw
            values = flat.tolist() if hasattr(flat, "tolist") else list(flat)
            sample = []
            if values:
                picks = sorted(set([0, min(1, len(values)-1), len(values)//2, len(values)-1]))
                sample = [_json_safe_scalar(values[i]) for i in picks]
            variables[name] = {
                "dimensions": list(var.dimensions),
                "shape": list(var.shape),
                "dtype": str(var.dtype),
                "valueCount": len(values),
                "sample": sample,
            }
    dtauc = variables.get("output_dtauc")
    if dtauc is None:
        raise ProbeRefusal("output_dtauc variable missing")
    wavelength_sized_dimensions = sorted(name for name, size in dimensions.items() if size == len(WAVELENGTH_NM))
    return {
        "dimensions": dimensions,
        "variables": variables,
        "outputDtauc": dtauc,
        "wavelengthSizedDimensions": wavelength_sized_dimensions,
        "hasUnique401Dimension": len(wavelength_sized_dimensions) == 1,
    }


def execute(*, uvspec: Path, data_dir: Path, atmosphere_file: Path,
            wavelength_grid_file: Path, output_dir: Path, allow_execution: bool = False) -> dict[str, Any]:
    if allow_execution is not True:
        raise ProbeRefusal("probe execution requires explicit allow_execution=True")
    if sha256_file(uvspec) != UVSPEC_SHA256:
        raise ProbeRefusal("uvspec SHA-256 drift")
    if sha256_file(atmosphere_file) != AFGLUS_SHA256:
        raise ProbeRefusal("AFGLUS SHA-256 drift")
    grid_values = [int(x) for x in Path(wavelength_grid_file).read_text().splitlines() if x.strip()]
    if grid_values != list(WAVELENGTH_NM):
        raise ProbeRefusal("wavelength-grid drift")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    text = render_input(data_dir=data_dir, atmosphere_file=atmosphere_file, wavelength_grid_file=wavelength_grid_file)
    (output_dir / "case.inp").write_text(text, encoding="utf-8")
    completed = subprocess.run(
        [str(uvspec)], input=text, text=True, capture_output=True, check=False,
        timeout=180, cwd=output_dir,
    )
    (output_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise ProbeRefusal(f"uvspec failed rc={completed.returncode}: {completed.stderr[-2000:]}")
    nc = output_dir / "optical_properties.nc"
    schema = inspect_netcdf(nc)
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FORMAT_PROBE_COMPLETED",
        "observerElevationM": OBSERVER_ELEVATION_M,
        "aod550": AOD550,
        "szaDeg": SZA_DEG,
        "requestedWavelengthNm": [WAVELENGTH_NM[0], WAVELENGTH_NM[-1]],
        "requestedWavelengthCount": len(WAVELENGTH_NM),
        "uvspecReturnCode": completed.returncode,
        "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
        "opticalPropertiesSha256": sha256_file(nc),
        "netcdf": schema,
        "claimBoundary": {
            "formatDiscoveryOnly": True,
            "protectedHoldoutOpened": False,
            "modelFitPerformed": False,
            "stellarAcceptanceGateEvaluated": False,
            "productionAuthorized": False,
        },
    }
    (output_dir / "format-probe-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--allow-execution", action="store_true")
    p.add_argument("--uvspec", type=Path)
    p.add_argument("--data-dir", type=Path)
    p.add_argument("--atmosphere-file", type=Path)
    p.add_argument("--wavelength-grid-file", type=Path)
    p.add_argument("--output-dir", type=Path)
    args = p.parse_args()
    if not args.execute:
        print(json.dumps({
            "stageId": STAGE_ID,
            "status": "REVIEW_ONLY_NO_EXECUTION",
            "observerElevationM": OBSERVER_ELEVATION_M,
            "aod550": AOD550,
            "requestedWavelengthCount": len(WAVELENGTH_NM),
            "protectedHoldoutOpened": False,
            "productionAuthorized": False,
        }, sort_keys=True))
        return 0
    required = [args.uvspec, args.data_dir, args.atmosphere_file, args.wavelength_grid_file, args.output_dir]
    if any(x is None for x in required):
        raise ProbeRefusal("execution requires all explicit paths")
    result = execute(
        uvspec=args.uvspec, data_dir=args.data_dir, atmosphere_file=args.atmosphere_file,
        wavelength_grid_file=args.wavelength_grid_file, output_dir=args.output_dir,
        allow_execution=args.allow_execution,
    )
    print(json.dumps({
        "status": result["status"],
        "outputDtauc": result["netcdf"]["outputDtauc"],
        "wavelengthSizedDimensions": result["netcdf"]["wavelengthSizedDimensions"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
