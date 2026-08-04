#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

STAGE_ID = "twilight-surrogate-tier-1-atm-z-grid-equivalence-proof-v1"
PRIMARY_SITE_ALTITUDE_KM = 0.357143
STRUCTURAL_SITE_ALTITUDES_KM = (0.0, 2.0)
CONTROL_WAVELENGTH_NM = 550.0
CONTROL_SZA_DEG = 30.0
CONTROL_PHI0_DEG = 0.0
CONTROL_UMU = -0.5
CONTROL_PHI_DEG = 36.0
CONTROL_ALBEDO = 0.15
CONTROL_AOD550 = 0.081818
CONTROL_STREAMS = 16
MYSTIC_SEED = 990004
MYSTIC_PHOTONS = 1
EXPECTED_ZOUT = "zout 0.000000"
FORBIDDEN_PREFIXES = ("altitude ", "mc_elevation_file ")
ALTITUDE_REJECTION_FRAGMENT = "option altitude does not work with"
SOURCE_ARCHIVE_EXPECTED_SHA256 = "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85"
SOURCE_ARCHIVE_CURRENT_DOWNLOAD_SHA256 = "64930cc40b6e4a37aa220520974d330fc1563796f466a649b2238131f2d69840"

# Preregistered before inspecting any A/B proof result. These values must not be
# changed in response to observed differences from the proof run.
PREREGISTERED_TOLERANCES: dict[str, dict[str, float]] = {
    "layerBoundaryKm": {"rtol": 0.0, "atol": 1.0e-6},
    "surfaceAndOutputAltitudeKm": {"rtol": 0.0, "atol": 1.0e-6},
    "pressureTemperatureAndNumberDensity": {"rtol": 5.0e-6, "atol": 1.0e-8},
    "gasColumn": {"rtol": 1.0e-5, "atol": 1.0e-6},
    "layerOpticalProperty": {"rtol": 1.0e-5, "atol": 1.0e-10},
    "columnOpticalProperty": {"rtol": 1.0e-5, "atol": 1.0e-10},
    "deterministicRadianceOrIrradiance": {"rtol": 1.0e-5, "atol": 1.0e-10},
}

PROFILE_COLUMNS = (
    "lambda",
    "zout_sur",
    "zout_sea",
    "z_sur",
    "p",
    "T",
    "n_AIR",
    "n_O3",
    "n_O2",
    "n_H2O",
    "n_CO2",
    "n_NO2",
    "edir",
    "edn",
    "eup",
    "uu",
)
PROFILE_STATE_COLUMNS = (
    "p",
    "T",
    "n_AIR",
    "n_O3",
    "n_O2",
    "n_H2O",
    "n_CO2",
    "n_NO2",
)
GAS_DENSITY_COLUMNS = (
    "n_AIR",
    "n_O3",
    "n_O2",
    "n_H2O",
    "n_CO2",
    "n_NO2",
)
RADIOMETRIC_COLUMNS = ("edir", "edn", "eup", "uu")
OPTICAL_REQUIRED_VARIABLES = (
    "output_dtauc",
    "output_dtauc_md",
    "output_ssalb",
    "output_pmom",
)


class ProofError(RuntimeError):
    pass


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def dump(value: Any) -> str:
    return json.dumps(json_safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_float(value: str, label: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ProofError(f"invalid {label}: {value}") from exc
    if not math.isfinite(number):
        raise ProofError(f"non-finite {label}: {value}")
    return number


def atmosphere_altitudes_descending(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        columns = stripped.split()
        if len(columns) < 2:
            raise ProofError(f"malformed atmosphere row: {raw}")
        levels.append(finite_float(columns[0], "atmosphere altitude"))
    if len(levels) < 2:
        raise ProofError("atmosphere has fewer than two levels")
    if any(levels[index] <= levels[index + 1] for index in range(len(levels) - 1)):
        raise ProofError("atmosphere_file levels must be strictly descending")
    return levels


def forced_grid_ascending(atmosphere: Path, site_altitude_km: float) -> list[float]:
    if not math.isfinite(site_altitude_km) or site_altitude_km < 0:
        raise ProofError("invalid site altitude")
    original = atmosphere_altitudes_descending(atmosphere)
    if not (original[-1] <= site_altitude_km < original[0]):
        raise ProofError("site altitude outside atmosphere grid")
    above = sorted(value for value in original if value > site_altitude_km)
    grid = [site_altitude_km, *above]
    if len(grid) < 2 or any(grid[index] >= grid[index + 1] for index in range(len(grid) - 1)):
        raise ProofError("forced atm_z_grid must be strictly ascending")
    expected_above = sorted(value for value in original if value > site_altitude_km)
    if grid[1:] != expected_above:
        raise ProofError("original levels above site altitude were not preserved exactly")
    return grid


def format_level(value: float) -> str:
    return f"{value:.6f}"


def local_levels(grid_ascending: Sequence[float], site_altitude_km: float) -> list[float]:
    values = [value - site_altitude_km for value in grid_ascending]
    values[0] = 0.0
    return values


def path_value(path: Path, token: str, resolved: bool) -> str:
    return str(path.resolve()) if resolved else token


def common_lines(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    resolved: bool,
) -> list[str]:
    return [
        f"data_files_path {path_value(data_dir, '${LIBRADTRAN_DATA}', resolved)}",
        f"atmosphere_file {path_value(atmosphere, '${ATMOSPHERE_FILE}', resolved)}",
        f"source solar {path_value(solar_flux, '${SOLAR_FLUX_FILE}', resolved)}",
        "mol_abs_param crs",
        f"wavelength {CONTROL_WAVELENGTH_NM:.1f} {CONTROL_WAVELENGTH_NM:.1f}",
        f"sza {CONTROL_SZA_DEG:.6f}",
        f"phi0 {CONTROL_PHI0_DEG:.6f}",
        f"albedo {CONTROL_ALBEDO:.6f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {CONTROL_AOD550:.6f}",
    ]


def representation_lines(
    representation: str,
    site_altitude_km: float,
    grid_ascending: Sequence[float],
) -> list[str]:
    if representation == "A-explicit-altitude-control":
        return [f"altitude {site_altitude_km:.6f}"]
    if representation == "B-atm-z-grid-candidate":
        return ["atm_z_grid " + " ".join(format_level(value) for value in grid_ascending)]
    raise ProofError(f"unknown representation: {representation}")


def render_profile_input(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    representation: str,
    site_altitude_km: float,
    grid_ascending: Sequence[float],
    resolved: bool,
) -> str:
    zouts = local_levels(grid_ascending, site_altitude_km)
    lines = [
        *common_lines(data_dir, atmosphere, solar_flux, resolved),
        *representation_lines(representation, site_altitude_km, grid_ascending),
        "rte_solver disort",
        f"number_of_streams {CONTROL_STREAMS}",
        "zout " + " ".join(format_level(value) for value in zouts),
        f"umu {CONTROL_UMU:.8f}",
        f"phi {CONTROL_PHI_DEG:.6f}",
        "output_user " + " ".join(PROFILE_COLUMNS),
        "quiet",
        "",
    ]
    return "\n".join(lines)


def render_optical_input(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    representation: str,
    site_altitude_km: float,
    grid_ascending: Sequence[float],
    resolved: bool,
) -> str:
    lines = [
        *common_lines(data_dir, atmosphere, solar_flux, resolved),
        *representation_lines(representation, site_altitude_km, grid_ascending),
        "rte_solver disort",
        f"number_of_streams {CONTROL_STREAMS}",
        EXPECTED_ZOUT,
        "write_optical_properties",
        "verbose",
        "",
    ]
    return "\n".join(lines)


def render_mystic_input(
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_dir: Path,
    grid_ascending: Sequence[float],
    resolved: bool,
) -> str:
    basename = path_value(output_dir / "mc", "${OUTPUT_DIR}/mc", resolved)
    lines = [
        *common_lines(data_dir, atmosphere, solar_flux, resolved),
        *representation_lines(
            "B-atm-z-grid-candidate",
            PRIMARY_SITE_ALTITUDE_KM,
            grid_ascending,
        ),
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {MYSTIC_PHOTONS}",
        "mc_vroom off",
        "mc_std",
        f"mc_randomseed {MYSTIC_SEED}",
        f"mc_basename {basename}",
        f"mc_spectral_is {CONTROL_WAVELENGTH_NM:.1f}",
        EXPECTED_ZOUT,
        f"umu {CONTROL_UMU:.8f}",
        f"phi {CONTROL_PHI_DEG:.6f}",
        "verbose",
        "",
    ]
    text = "\n".join(lines)
    actual = text.splitlines()
    if any(line.startswith(prefix) for line in actual for prefix in FORBIDDEN_PREFIXES):
        raise ProofError("candidate MYSTIC input contains forbidden altitude mechanism")
    if actual.count(EXPECTED_ZOUT) != 1:
        raise ProofError("candidate MYSTIC input lacks exact local-surface zout")
    if sum(line.startswith("atm_z_grid ") for line in actual) != 1:
        raise ProofError("candidate MYSTIC input lacks exact atm_z_grid")
    return text


def preserve_input(run_dir: Path, raw_text: str, resolved_text: str) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "input-raw.txt"
    resolved_path = run_dir / "input-resolved.txt"
    raw_path.write_text(raw_text, encoding="utf-8")
    resolved_path.write_text(resolved_text, encoding="utf-8")
    return {
        "rawInputSha256": raw_sha256(raw_path),
        "resolvedInputSha256": raw_sha256(resolved_path),
    }


def run_uvspec(
    uvspec: Path,
    run_dir: Path,
    raw_text: str,
    resolved_text: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    hashes = preserve_input(run_dir, raw_text, resolved_text)
    start = time.monotonic()
    timed_out = False
    try:
        process = subprocess.run(
            [str(uvspec.resolve())],
            input=resolved_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
            cwd=run_dir,
        )
        returncode = process.returncode
        stdout = process.stdout
        stderr = process.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    elapsed = time.monotonic() - start
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    return {
        **hashes,
        "exitCode": returncode,
        "timedOut": timed_out,
        "elapsedSeconds": elapsed,
        "stdoutSha256": raw_sha256(stdout_path),
        "stderrSha256": raw_sha256(stderr_path),
        "stdout": stdout,
        "stderr": stderr,
    }


def parse_profile_output(text: str) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) != len(PROFILE_COLUMNS):
            continue
        try:
            values = [float(field) for field in fields]
        except ValueError:
            continue
        if not all(math.isfinite(value) for value in values):
            raise ProofError("non-finite deterministic profile output")
        rows.append(dict(zip(PROFILE_COLUMNS, values, strict=True)))
    if not rows:
        raise ProofError("no deterministic profile rows parsed")
    rows.sort(key=lambda row: row["zout_sur"])
    return rows


def tolerance(name: str) -> tuple[float, float]:
    value = PREREGISTERED_TOLERANCES[name]
    return value["rtol"], value["atol"]


def close_enough(left: float, right: float, rtol: float, atol: float) -> bool:
    return abs(left - right) <= atol + rtol * max(abs(left), abs(right))


def compare_vectors(
    label: str,
    left: Sequence[float],
    right: Sequence[float],
    tolerance_name: str,
) -> dict[str, Any]:
    rtol, atol = tolerance(tolerance_name)
    if len(left) != len(right):
        return {
            "label": label,
            "passed": False,
            "reason": "length-mismatch",
            "leftLength": len(left),
            "rightLength": len(right),
            "rtol": rtol,
            "atol": atol,
        }
    failures: list[dict[str, Any]] = []
    max_abs = 0.0
    max_rel = 0.0
    for index, (a, b) in enumerate(zip(left, right, strict=True)):
        if math.isnan(a) and math.isnan(b):
            continue
        if not (math.isfinite(a) and math.isfinite(b)):
            failures.append({"index": index, "left": a, "right": b, "reason": "non-finite"})
            continue
        absolute = abs(a - b)
        scale = max(abs(a), abs(b))
        relative = absolute / scale if scale > 0 else 0.0
        max_abs = max(max_abs, absolute)
        max_rel = max(max_rel, relative)
        if not close_enough(a, b, rtol, atol):
            failures.append(
                {
                    "index": index,
                    "left": a,
                    "right": b,
                    "absoluteDifference": absolute,
                    "relativeDifference": relative,
                }
            )
    return {
        "label": label,
        "passed": not failures,
        "rtol": rtol,
        "atol": atol,
        "maxAbsoluteDifference": max_abs,
        "maxRelativeDifference": max_rel,
        "failureCount": len(failures),
        "failures": failures[:20],
    }


def profile_vectors(rows: Sequence[dict[str, float]], field: str) -> list[float]:
    return [row[field] for row in rows]


def gas_columns(rows: Sequence[dict[str, float]]) -> dict[str, float]:
    if len(rows) < 2:
        raise ProofError("profile has fewer than two rows")
    columns: dict[str, float] = {}
    for field in GAS_DENSITY_COLUMNS:
        total = 0.0
        for lower, upper in zip(rows, rows[1:]):
            dz_cm = (upper["zout_sea"] - lower["zout_sea"]) * 1.0e5
            if dz_cm <= 0:
                raise ProofError("profile physical altitudes are not increasing")
            total += 0.5 * dz_cm * (lower[field] + upper[field])
        columns[field] = total
    return columns


def expected_geometry_checks(
    rows: Sequence[dict[str, float]],
    grid: Sequence[float],
    site_altitude_km: float,
    label: str,
) -> list[dict[str, Any]]:
    local = local_levels(grid, site_altitude_km)
    return [
        compare_vectors(
            f"{label}.zout_sur",
            profile_vectors(rows, "zout_sur"),
            local,
            "surfaceAndOutputAltitudeKm",
        ),
        compare_vectors(
            f"{label}.zout_sea",
            profile_vectors(rows, "zout_sea"),
            list(grid),
            "surfaceAndOutputAltitudeKm",
        ),
        compare_vectors(
            f"{label}.z_sur",
            profile_vectors(rows, "z_sur"),
            [site_altitude_km] * len(rows),
            "surfaceAndOutputAltitudeKm",
        ),
    ]


def validate_profile_pair(
    rows_a: Sequence[dict[str, float]],
    rows_b: Sequence[dict[str, float]],
    grid: Sequence[float],
    site_altitude_km: float,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.extend(expected_geometry_checks(rows_a, grid, site_altitude_km, "A"))
    checks.extend(expected_geometry_checks(rows_b, grid, site_altitude_km, "B"))
    checks.append(
        compare_vectors(
            "A-vs-B.layer-boundaries",
            profile_vectors(rows_a, "zout_sea"),
            profile_vectors(rows_b, "zout_sea"),
            "layerBoundaryKm",
        )
    )
    for field in PROFILE_STATE_COLUMNS:
        checks.append(
            compare_vectors(
                f"A-vs-B.{field}",
                profile_vectors(rows_a, field),
                profile_vectors(rows_b, field),
                "pressureTemperatureAndNumberDensity",
            )
        )
    columns_a = gas_columns(rows_a)
    columns_b = gas_columns(rows_b)
    for field in GAS_DENSITY_COLUMNS:
        checks.append(
            compare_vectors(
                f"A-vs-B.column.{field}",
                [columns_a[field]],
                [columns_b[field]],
                "gasColumn",
            )
        )
    radiometric_checks: list[dict[str, Any]] = []
    for field in RADIOMETRIC_COLUMNS:
        radiometric_checks.append(
            compare_vectors(
                f"A-vs-B.{field}",
                profile_vectors(rows_a, field),
                profile_vectors(rows_b, field),
                "deterministicRadianceOrIrradiance",
            )
        )
    atmospheric_passed = all(check["passed"] for check in checks)
    radiometric_passed = all(check["passed"] for check in radiometric_checks)
    return {
        "atmosphericProfileAndColumnPassed": atmospheric_passed,
        "deterministicControlPassed": radiometric_passed,
        "atmosphericChecks": checks,
        "radiometricChecks": radiometric_checks,
        "gasColumnsA": columns_a,
        "gasColumnsB": columns_b,
    }


def flatten_numeric(value: Any) -> tuple[list[int], list[float]]:
    shape: list[int] = []

    def infer_shape(node: Any, depth: int) -> None:
        if isinstance(node, list):
            if depth == len(shape):
                shape.append(len(node))
            elif shape[depth] != len(node):
                raise ProofError("ragged netCDF variable")
            for child in node:
                infer_shape(child, depth + 1)

    infer_shape(value, 0)
    flat: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
        else:
            number = float(node)
            flat.append(number)

    walk(value)
    return shape, flat


def read_optical_netcdf(path: Path) -> dict[str, Any]:
    try:
        from netCDF4 import Dataset  # type: ignore[import-not-found]
    except Exception as exc:
        raise ProofError(f"netCDF4 Python reader unavailable: {exc}") from exc
    if not path.is_file():
        raise ProofError(f"optical properties file missing: {path}")
    result: dict[str, Any] = {}
    with Dataset(path, "r") as dataset:
        for name, variable in dataset.variables.items():
            raw = variable[:]
            if hasattr(raw, "filled"):
                raw = raw.filled(float("nan"))
            if hasattr(raw, "tolist"):
                raw = raw.tolist()
            shape, flat = flatten_numeric(raw)
            result[name] = {
                "shape": shape,
                "values": flat,
                "dimensions": list(variable.dimensions),
                "dtype": str(variable.dtype),
            }
    missing = [name for name in OPTICAL_REQUIRED_VARIABLES if name not in result]
    if missing:
        raise ProofError(f"required optical variables missing: {missing}")
    return result


def parse_gas_optical_table(stderr: str) -> dict[str, list[float]]:
    marker = "*** setup_gases(), layer properties"
    position = stderr.find(marker)
    if position < 0:
        raise ProofError("setup_gases optical table not found")
    rows: list[tuple[float, float, float]] = []
    for raw in stderr[position:].splitlines():
        pieces = [piece.strip() for piece in raw.split("|")]
        if len(pieces) < 4:
            continue
        try:
            layer_index = int(pieces[0])
            lower_boundary = float(pieces[1])
            rayleigh = float(pieces[2])
            molecular_absorption = float(pieces[3])
        except ValueError:
            if rows and pieces[0] == "sum":
                break
            continue
        if layer_index != len(rows):
            if rows:
                break
            continue
        rows.append((lower_boundary, rayleigh, molecular_absorption))
    if not rows:
        raise ProofError("no setup_gases optical rows parsed")
    return {
        "lowerBoundaryKm": [row[0] for row in rows],
        "rayleighLayerOpticalDepth": [row[1] for row in rows],
        "molecularAbsorptionLayerOpticalDepth": [row[2] for row in rows],
    }


def optical_components(
    netcdf: dict[str, Any],
    gas_table: dict[str, list[float]],
) -> dict[str, list[float]]:
    total = list(netcdf["output_dtauc"]["values"])
    single_scattering_albedo = list(netcdf["output_ssalb"]["values"])
    rayleigh = gas_table["rayleighLayerOpticalDepth"]
    molecular_absorption = gas_table["molecularAbsorptionLayerOpticalDepth"]
    lengths = {len(total), len(single_scattering_albedo), len(rayleigh), len(molecular_absorption)}
    if len(lengths) != 1:
        raise ProofError(f"optical layer length mismatch: {sorted(lengths)}")
    total_scattering = [tau * ssa for tau, ssa in zip(total, single_scattering_albedo, strict=True)]
    total_absorption = [tau - scattering for tau, scattering in zip(total, total_scattering, strict=True)]
    # No cloud options occur in either preregistered proof input. Therefore the
    # remaining extinction after molecular/Rayleigh contributions is aerosol.
    aerosol_extinction = [
        tau - ray - mol
        for tau, ray, mol in zip(total, rayleigh, molecular_absorption, strict=True)
    ]
    return {
        "totalLayerOpticalDepth": total,
        "singleScatteringAlbedo": single_scattering_albedo,
        "totalScatteringLayerOpticalDepth": total_scattering,
        "totalAbsorptionLayerOpticalDepth": total_absorption,
        "rayleighLayerOpticalDepth": rayleigh,
        "molecularAbsorptionLayerOpticalDepth": molecular_absorption,
        "aerosolLayerOpticalDepth": aerosol_extinction,
        "waterCloudLayerOpticalDepth": [0.0] * len(total),
        "iceCloudLayerOpticalDepth": [0.0] * len(total),
    }


def validate_optical_pair(
    netcdf_a: dict[str, Any],
    netcdf_b: dict[str, Any],
    gas_a: dict[str, list[float]],
    gas_b: dict[str, list[float]],
    expected_grid: Sequence[float],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    all_variables = sorted(set(netcdf_a) | set(netcdf_b))
    for name in all_variables:
        if name not in netcdf_a or name not in netcdf_b:
            checks.append({"label": f"netcdf.{name}", "passed": False, "reason": "variable-missing"})
            continue
        left = netcdf_a[name]
        right = netcdf_b[name]
        if left["shape"] != right["shape"] or left["dimensions"] != right["dimensions"]:
            checks.append(
                {
                    "label": f"netcdf.{name}",
                    "passed": False,
                    "reason": "shape-or-dimension-mismatch",
                    "leftShape": left["shape"],
                    "rightShape": right["shape"],
                    "leftDimensions": left["dimensions"],
                    "rightDimensions": right["dimensions"],
                }
            )
            continue
        checks.append(
            compare_vectors(
                f"netcdf.{name}",
                left["values"],
                right["values"],
                "layerOpticalProperty",
            )
        )
    expected_lower_boundaries_desc = list(reversed(expected_grid[:-1]))
    # setup_gases emits layers from top to bottom and prints each lower boundary.
    checks.append(
        compare_vectors(
            "A.optical-layer-boundaries",
            gas_a["lowerBoundaryKm"],
            expected_lower_boundaries_desc,
            "layerBoundaryKm",
        )
    )
    checks.append(
        compare_vectors(
            "B.optical-layer-boundaries",
            gas_b["lowerBoundaryKm"],
            expected_lower_boundaries_desc,
            "layerBoundaryKm",
        )
    )
    components_a = optical_components(netcdf_a, gas_a)
    components_b = optical_components(netcdf_b, gas_b)
    for name in components_a:
        checks.append(
            compare_vectors(
                f"A-vs-B.{name}",
                components_a[name],
                components_b[name],
                "layerOpticalProperty",
            )
        )
        checks.append(
            compare_vectors(
                f"A-vs-B.column.{name}",
                [sum(components_a[name])],
                [sum(components_b[name])],
                "columnOpticalProperty",
            )
        )
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "componentsA": components_a,
        "componentsB": components_b,
        "cloudsConfigured": False,
        "allResolvedNetcdfVariablesCompared": all_variables,
    }


def run_profile_pair(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_root: Path,
    site_altitude_km: float,
) -> dict[str, Any]:
    grid = forced_grid_ascending(atmosphere, site_altitude_km)
    runs: dict[str, Any] = {}
    parsed: dict[str, list[dict[str, float]]] = {}
    for short, representation in (
        ("A", "A-explicit-altitude-control"),
        ("B", "B-atm-z-grid-candidate"),
    ):
        run_dir = output_root / f"h-{site_altitude_km:.6f}" / f"profile-{short}"
        raw = render_profile_input(
            data_dir,
            atmosphere,
            solar_flux,
            representation,
            site_altitude_km,
            grid,
            False,
        )
        resolved = render_profile_input(
            data_dir,
            atmosphere,
            solar_flux,
            representation,
            site_altitude_km,
            grid,
            True,
        )
        execution = run_uvspec(uvspec, run_dir, raw, resolved, 180)
        if execution["exitCode"] != 0 or execution["timedOut"]:
            raise ProofError(
                f"deterministic profile {short} failed at h={site_altitude_km:.6f}: "
                f"exit={execution['exitCode']} timeout={execution['timedOut']}"
            )
        rows = parse_profile_output(execution.pop("stdout"))
        execution.pop("stderr")
        if len(rows) != len(grid):
            raise ProofError(
                f"profile row count mismatch at h={site_altitude_km:.6f}, {short}: "
                f"{len(rows)} != {len(grid)}"
            )
        (run_dir / "profile-parsed.json").write_text(dump(rows), encoding="utf-8")
        execution["profileParsedSha256"] = raw_sha256(run_dir / "profile-parsed.json")
        runs[short] = execution
        parsed[short] = rows
    decision = validate_profile_pair(parsed["A"], parsed["B"], grid, site_altitude_km)
    result = {
        "siteAltitudeKm": site_altitude_km,
        "forcedGridAscendingKm": grid,
        "forcedGridBottomKm": grid[0],
        "allOriginalLevelsAboveSitePreservedExactly": True,
        "runs": runs,
        "decision": decision,
    }
    result_path = output_root / f"h-{site_altitude_km:.6f}" / "profile-equivalence.json"
    result_path.write_text(dump(result), encoding="utf-8")
    result["resultRawSha256"] = raw_sha256(result_path)
    return result


def run_optical_pair(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_root: Path,
) -> dict[str, Any]:
    site_altitude_km = PRIMARY_SITE_ALTITUDE_KM
    grid = forced_grid_ascending(atmosphere, site_altitude_km)
    executions: dict[str, Any] = {}
    netcdfs: dict[str, dict[str, Any]] = {}
    gas_tables: dict[str, dict[str, list[float]]] = {}
    for short, representation in (
        ("A", "A-explicit-altitude-control"),
        ("B", "B-atm-z-grid-candidate"),
    ):
        run_dir = output_root / f"h-{site_altitude_km:.6f}" / f"optical-{short}"
        raw = render_optical_input(
            data_dir,
            atmosphere,
            solar_flux,
            representation,
            site_altitude_km,
            grid,
            False,
        )
        resolved = render_optical_input(
            data_dir,
            atmosphere,
            solar_flux,
            representation,
            site_altitude_km,
            grid,
            True,
        )
        execution = run_uvspec(uvspec, run_dir, raw, resolved, 180)
        stderr = execution.pop("stderr")
        execution.pop("stdout")
        if execution["exitCode"] != 0 or execution["timedOut"]:
            raise ProofError(
                f"optical setup {short} failed: exit={execution['exitCode']} timeout={execution['timedOut']}"
            )
        nc_path = run_dir / "optical_properties.nc"
        execution["opticalPropertiesRawSha256"] = raw_sha256(nc_path)
        netcdf = read_optical_netcdf(nc_path)
        gas_table = parse_gas_optical_table(stderr)
        (run_dir / "optical-properties-parsed.json").write_text(dump(netcdf), encoding="utf-8")
        (run_dir / "gas-optical-table.json").write_text(dump(gas_table), encoding="utf-8")
        execution["opticalPropertiesParsedSha256"] = raw_sha256(run_dir / "optical-properties-parsed.json")
        execution["gasOpticalTableSha256"] = raw_sha256(run_dir / "gas-optical-table.json")
        executions[short] = execution
        netcdfs[short] = netcdf
        gas_tables[short] = gas_table
    decision = validate_optical_pair(netcdfs["A"], netcdfs["B"], gas_tables["A"], gas_tables["B"], grid)
    result = {
        "siteAltitudeKm": site_altitude_km,
        "runs": executions,
        "decision": decision,
        "writeOpticalPropertiesSolverExecutionCount": 0,
        "boundary": "atmosphere setup and optical-property materialization only; write_optical_properties switches to null solver",
    }
    result_path = output_root / f"h-{site_altitude_km:.6f}" / "optical-equivalence.json"
    result_path.write_text(dump(result), encoding="utf-8")
    result["resultRawSha256"] = raw_sha256(result_path)
    return result


def should_run_mystic(
    primary_profile: dict[str, Any],
    optical: dict[str, Any],
    structural_profiles: Sequence[dict[str, Any]],
) -> bool:
    return (
        primary_profile["decision"]["atmosphericProfileAndColumnPassed"]
        and primary_profile["decision"]["deterministicControlPassed"]
        and optical["decision"]["passed"]
        and all(
            item["decision"]["atmosphericProfileAndColumnPassed"]
            and item["decision"]["deterministicControlPassed"]
            for item in structural_profiles
        )
    )


def run_mystic_probe(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    output_root: Path,
) -> dict[str, Any]:
    grid = forced_grid_ascending(atmosphere, PRIMARY_SITE_ALTITUDE_KM)
    run_dir = output_root / f"h-{PRIMARY_SITE_ALTITUDE_KM:.6f}" / "mystic-B-one-photon"
    raw = render_mystic_input(data_dir, atmosphere, solar_flux, run_dir, grid, False)
    resolved = render_mystic_input(data_dir, atmosphere, solar_flux, run_dir, grid, True)
    execution = run_uvspec(uvspec, run_dir, raw, resolved, 180)
    stdout = execution.pop("stdout")
    stderr = execution.pop("stderr")
    generated = sorted(
        path
        for path in run_dir.iterdir()
        if path.is_file() and path.name.startswith("mc")
    )
    generated_rows = [
        {
            "filename": path.name,
            "sizeBytes": path.stat().st_size,
            "rawSha256": raw_sha256(path),
        }
        for path in generated
    ]
    for path in generated:
        path.unlink()
    surface_marker = f"forced new altitude = {PRIMARY_SITE_ALTITUDE_KM:.6f}"
    passed = (
        execution["exitCode"] == 0
        and not execution["timedOut"]
        and ALTITUDE_REJECTION_FRAGMENT not in stderr
        and surface_marker in stderr
        and bool(generated_rows)
    )
    result = {
        "status": (
            "MYSTIC_ACCEPTS_EQUIVALENCE_VALIDATED_ATM_Z_GRID_SITE_REPRESENTATION"
            if passed
            else "MYSTIC_ATM_Z_GRID_ACCEPTANCE_PROBE_FAILED"
        ),
        "passed": passed,
        "siteAltitudeKm": PRIMARY_SITE_ALTITUDE_KM,
        "localSurfaceZoutKm": 0.0,
        "outputLevelInterpretation": {
            "localSurfaceHeightKm": 0.0,
            "aboveSeaLevelKm": PRIMARY_SITE_ALTITUDE_KM,
            "binding": "validated deterministic B profile at identical atm_z_grid and zout semantics",
        },
        "atmosphereStartsAtSiteAltitude": grid[0] == PRIMARY_SITE_ALTITUDE_KM,
        "layersBelowSiteAltitudePresent": False,
        "explicitAltitudePresent": False,
        "mcElevationFilePresent": False,
        "surfaceMarkerObserved": surface_marker in stderr,
        "altitudeRejectionObserved": ALTITUDE_REJECTION_FRAGMENT in stderr,
        "generatedFiles": generated_rows,
        "generatedFilesPreserved": False,
        "scientificDatasetProduced": False,
        "solverExecutionCount": 1,
        "mcPhotons": MYSTIC_PHOTONS,
        "execution": execution,
        "stdoutSha256": sha_bytes(stdout.encode("utf-8")),
        "stderrSha256": sha_bytes(stderr.encode("utf-8")),
    }
    result_path = run_dir / "mystic-probe.json"
    result_path.write_text(dump(result), encoding="utf-8")
    result["resultRawSha256"] = raw_sha256(result_path)
    return result


def package_identity(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise ProofError(f"package identity file missing: {path}")
    return {"path": path.name, "rawSha256": raw_sha256(path), "sizeBytes": path.stat().st_size}


def proof(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    solar_flux: Path,
    runtime_lock: Path,
    output_dir: Path,
    package_explicit: Path | None,
    package_json: Path | None,
) -> dict[str, Any]:
    for path, label in (
        (uvspec, "uvspec"),
        (atmosphere, "atmosphere"),
        (solar_flux, "solar flux"),
        (runtime_lock, "runtime lock"),
    ):
        if not path.is_file():
            raise ProofError(f"{label} missing: {path}")
    if not data_dir.is_dir():
        raise ProofError(f"data directory missing: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "preregistered-tolerances.json").write_text(
        dump(PREREGISTERED_TOLERANCES), encoding="utf-8"
    )

    primary_profile = run_profile_pair(
        uvspec,
        data_dir,
        atmosphere,
        solar_flux,
        output_dir,
        PRIMARY_SITE_ALTITUDE_KM,
    )
    optical = run_optical_pair(uvspec, data_dir, atmosphere, solar_flux, output_dir)
    structural_profiles = [
        run_profile_pair(
            uvspec,
            data_dir,
            atmosphere,
            solar_flux,
            output_dir,
            height,
        )
        for height in STRUCTURAL_SITE_ALTITUDES_KM
    ]

    deterministic_gate = should_run_mystic(primary_profile, optical, structural_profiles)
    if deterministic_gate:
        mystic = run_mystic_probe(uvspec, data_dir, atmosphere, solar_flux, output_dir)
    else:
        mystic = {
            "status": "NOT_RUN_DETERMINISTIC_EQUIVALENCE_GATE_FAILED",
            "passed": False,
            "solverExecutionCount": 0,
            "mcPhotons": 0,
            "scientificDatasetProduced": False,
        }

    profile_decision = primary_profile["decision"]["atmosphericProfileAndColumnPassed"]
    deterministic_decision = primary_profile["decision"]["deterministicControlPassed"]
    optical_decision = optical["decision"]["passed"]
    three_heights_decision = all(
        item["decision"]["atmosphericProfileAndColumnPassed"]
        and item["decision"]["deterministicControlPassed"]
        for item in structural_profiles
    )
    proof_passed = (
        profile_decision
        and deterministic_decision
        and optical_decision
        and three_heights_decision
        and mystic["passed"]
    )
    result = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": (
            "ATM_Z_GRID_ELEVATED_SITE_EQUIVALENCE_AND_MYSTIC_ACCEPTANCE_PROOF_PASSED"
            if proof_passed
            else "ATM_Z_GRID_ELEVATED_SITE_PROOF_FAILED"
        ),
        "proofPassed": proof_passed,
        "candidateRepresentation": {
            "atmosphereFileRemainsProfileSource": True,
            "atmZGridBottomIsSiteAltitude": True,
            "originalAtmosphereLevelsAboveSitePreservedExactly": True,
            "explicitAltitudeForbidden": True,
            "mcElevationFileForbidden": True,
            "localSurfaceZoutKm": 0.0,
        },
        "controlGeometry": {
            "purpose": "low-SZA deterministic mechanism control only",
            "szaDeg": CONTROL_SZA_DEG,
            "wavelengthNm": CONTROL_WAVELENGTH_NM,
            "umu": CONTROL_UMU,
            "phiDeg": CONTROL_PHI_DEG,
            "notFrozenTier1TwilightGeometry": True,
        },
        "preregisteredTolerances": PREREGISTERED_TOLERANCES,
        "preregisteredTolerancesRawSha256": raw_sha256(output_dir / "preregistered-tolerances.json"),
        "profileEquivalenceDecision": profile_decision,
        "opticalPropertyEquivalenceDecision": optical_decision,
        "deterministicControlDecision": deterministic_decision,
        "threeHeightStructuralProfileDecision": three_heights_decision,
        "mysticProbeDecision": mystic["passed"],
        "primaryProfile": primary_profile,
        "primaryOptical": optical,
        "structuralProfiles": structural_profiles,
        "mysticProbe": mystic,
        "runtime": {
            "uvspecSha256": raw_sha256(uvspec),
            "runtimeLockRawSha256": raw_sha256(runtime_lock),
            "atmosphereSha256": raw_sha256(atmosphere),
            "solarFluxSha256": raw_sha256(solar_flux),
            "packageExplicit": package_identity(package_explicit),
            "packageJson": package_identity(package_json),
        },
        "sourceProvenance": {
            "status": "SEPARATE_UNRESOLVED_OFFICIAL_ARCHIVE_HASH_MISMATCH",
            "historicCondaForgeExpectedSha256": SOURCE_ARCHIVE_EXPECTED_SHA256,
            "currentOfficialDownloadObservedSha256": SOURCE_ARCHIVE_CURRENT_DOWNLOAD_SHA256,
            "expectedHashChangedToMakeCiGreen": False,
            "sourceEvidenceAccepted": False,
            "behaviorEvidenceIndependentOfSourceArchiveAcceptance": True,
        },
        "scientificExecution": False,
        "scientificDatasetProduced": False,
        "surrogateTrainingUsePermitted": False,
        "authorizationPermitted": False,
        "ordinal2ScientificDispatchPermitted": False,
        "githubRerunPermitted": False,
        "mysticSolverExecutionCount": mystic["solverExecutionCount"],
        "maximumPermittedMysticSolverExecutionCount": 1,
        "frozenTier1InvariantsChanged": False,
        "boundary": (
            "mechanism equivalence and one-photon MYSTIC acceptance proof only; "
            "no Tier-1 dataset, authorization, dispatch, training, Tier-2, or production claim"
        ),
    }
    report_path = output_dir / "atm-z-grid-equivalence-proof.json"
    report_path.write_text(dump(result), encoding="utf-8")
    result["reportRawSha256"] = raw_sha256(report_path)
    if not proof_passed:
        raise ProofError(
            "proof decision failed; preserved report and evidence with authorizationPermitted=false"
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--solar-flux", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--package-explicit", type=Path)
    parser.add_argument("--package-json", type=Path)
    args = parser.parse_args()
    try:
        result = proof(
            args.uvspec,
            args.data_dir,
            args.atmosphere,
            args.solar_flux,
            args.runtime_lock,
            args.output_dir,
            args.package_explicit,
            args.package_json,
        )
        print(dump(result), end="")
        return 0
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "REFUSED",
            "proofPassed": False,
            "reason": str(exc),
            "scientificExecution": False,
            "scientificDatasetProduced": False,
            "surrogateTrainingUsePermitted": False,
            "authorizationPermitted": False,
            "ordinal2ScientificDispatchPermitted": False,
            "githubRerunPermitted": False,
            "mysticSolverExecutionCount": 0,
            "maximumPermittedMysticSolverExecutionCount": 1,
            "sourceProvenance": {
                "status": "SEPARATE_UNRESOLVED_OFFICIAL_ARCHIVE_HASH_MISMATCH",
                "historicCondaForgeExpectedSha256": SOURCE_ARCHIVE_EXPECTED_SHA256,
                "currentOfficialDownloadObservedSha256": SOURCE_ARCHIVE_CURRENT_DOWNLOAD_SHA256,
                "expectedHashChangedToMakeCiGreen": False,
                "sourceEvidenceAccepted": False,
            },
        }
        try:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = args.output_dir / "atm-z-grid-equivalence-proof.json"
            if not report_path.exists():
                report_path.write_text(dump(failure), encoding="utf-8")
        except Exception:
            pass
        print(dump(failure), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
