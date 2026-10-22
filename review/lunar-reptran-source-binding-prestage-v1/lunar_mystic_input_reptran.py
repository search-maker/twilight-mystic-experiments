#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from typing import Iterable

BASE_MAIN = "16292e6246d0c15f72bc5e09bee9f0a0ba330e3e"
HISTORICAL_EXEC003_RENDERER_BLOB = "ce81d2c3cd7fa3570b064c327cd834138535bdc8"
HELPER = Path(__file__).resolve().parents[2] / "experiments" / "mystic-batch-v1" / "twilight_surrogate_tier1_execution_adapter.py"


class LunarReptranPrestageError(ValueError):
    pass


def _finite(name: str, value: object, lo: float, hi: float) -> float:
    if isinstance(value, bool):
        raise LunarReptranPrestageError(f"{name} must be numeric")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise LunarReptranPrestageError(f"{name} must be numeric") from exc
    if not math.isfinite(x) or not lo <= x <= hi:
        raise LunarReptranPrestageError(f"{name} outside [{lo}, {hi}]")
    return x


def _elevation_helper():
    spec = importlib.util.spec_from_file_location("lunar_reptran_elevation_helper", HELPER)
    if spec is None or spec.loader is None:
        raise LunarReptranPrestageError("reviewed Level-B elevation helper unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_lunar_source_file(
    path: Path,
    wavelengths_nm: Iterable[float],
    lunar_toa_w_m2_nm: Iterable[float],
) -> dict:
    """Write the frozen custom-source representation without day-of-year scaling."""
    wl = [float(x) for x in wavelengths_nm]
    ir = [float(x) for x in lunar_toa_w_m2_nm]
    if len(wl) < 2 or len(wl) != len(ir):
        raise LunarReptranPrestageError("lunar source arrays must have equal length >= 2")
    if wl != sorted(wl) or len(set(wl)) != len(wl):
        raise LunarReptranPrestageError("lunar source wavelength grid must be strictly increasing")
    if wl[0] != 380.0 or wl[-1] != 780.0:
        raise LunarReptranPrestageError("lunar source must explicitly cover exact 380 and 780 nm endpoints")
    if any(not math.isfinite(x) or x < 0.0 for x in ir):
        raise LunarReptranPrestageError("lunar source irradiance must be finite and nonnegative")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{w:.6f} {1000.0 * e:.12e}\n" for w, e in zip(wl, ir)),
        encoding="utf-8",
    )
    return {
        "schemaVersion": 1,
        "inputUnit": "W m-2 nm-1",
        "unit": "mW m-2 nm-1",
        "nodeCount": len(wl),
        "startNm": wl[0],
        "stopNm": wl[-1],
        "dayOfYearDistanceScalingApplied": False,
    }


def finite_disk_direction_samples(
    *,
    moon_zenith_deg: float,
    target_altitude_deg: float,
    target_relative_azimuth_to_moon_deg: float,
    lunar_angular_radius_deg: float,
) -> tuple[dict, ...]:
    """Return the frozen 33-direction transfer-kernel sampling plan."""
    moon_zenith = _finite("moon_zenith_deg", moon_zenith_deg, 0.0, 120.0)
    target_alt = _finite("target_altitude_deg", target_altitude_deg, 0.0, 90.0)
    target_rel_az = _finite(
        "target_relative_azimuth_to_moon_deg",
        target_relative_azimuth_to_moon_deg,
        0.0,
        360.0,
    )
    angular_radius = _finite("lunar_angular_radius_deg", lunar_angular_radius_deg, 0.0, 1.0)
    if angular_radius <= 0.0:
        raise LunarReptranPrestageError("lunar_angular_radius_deg must be > 0")

    theta = math.radians(moon_zenith)
    center = (math.sin(theta), 0.0, math.cos(theta))
    zenithward = (-math.cos(theta), 0.0, math.sin(theta))
    azimuthward = (0.0, 1.0, 0.0)

    def sample(radius_fraction: float, position_angle_deg: float, sample_id: str) -> dict:
        delta = math.radians(angular_radius * radius_fraction)
        alpha = math.radians(position_angle_deg)
        tangent = tuple(
            math.cos(alpha) * zenithward[i] + math.sin(alpha) * azimuthward[i]
            for i in range(3)
        )
        direction = tuple(
            math.cos(delta) * center[i] + math.sin(delta) * tangent[i]
            for i in range(3)
        )
        norm = math.sqrt(sum(v * v for v in direction))
        x, y, z = (v / norm for v in direction)
        source_zenith = math.degrees(math.acos(max(-1.0, min(1.0, z))))
        source_azimuth = math.degrees(math.atan2(y, x)) % 360.0
        target_relative = (target_rel_az - source_azimuth) % 360.0
        dot = max(-1.0, min(1.0, sum(center[i] * direction[i] / norm for i in range(3))))
        return {
            "sampleId": sample_id,
            "radiusFraction": radius_fraction,
            "positionAngleDeg": position_angle_deg,
            "angularOffsetDeg": math.degrees(math.acos(dot)),
            "sourceZenithDeg": source_zenith,
            "sourceAzimuthInCenterFrameDeg": source_azimuth,
            "targetAltitudeDeg": target_alt,
            "targetRelativeAzimuthToSampleSourceDeg": target_relative,
            "sameFullDiskIntegratedRoloIrradianceRequired": True,
            "physicalResolvedDiskWeight": None,
        }

    samples = [sample(0.0, 0.0, "center")]
    for radius_fraction, label in ((0.5, "r050"), (1.0, "r100")):
        for index in range(16):
            samples.append(sample(radius_fraction, 22.5 * index, f"{label}-pa{index:02d}"))
    if len(samples) != 33:
        raise LunarReptranPrestageError("finite-disk plan must contain exactly 33 directions")
    return tuple(samples)


def validate_rendered_reptran_input(text: str, lunar_source_file: Path) -> None:
    """Fail closed on any CRS fallback or protected-input structural drift."""
    lines = text.splitlines()
    source_line = f"source solar {lunar_source_file.resolve()}"
    exact_counts = {
        source_line: 1,
        "mol_abs_param reptran": 1,
        "mc_spherical 1D": 1,
        "mc_vroom off": 1,
        "mc_spectral_is 550.0": 1,
        "zout 0.000000": 1,
    }
    for line, expected in exact_counts.items():
        if lines.count(line) != expected:
            raise LunarReptranPrestageError(
                f"required directive count drift: {line!r} expected {expected}, found {lines.count(line)}"
            )
    if any(line.startswith("mol_abs_param crs") for line in lines):
        raise LunarReptranPrestageError("historical CRS fallback is forbidden")
    if sum(line.startswith("mol_abs_param ") for line in lines) != 1:
        raise LunarReptranPrestageError("exactly one molecular-absorption directive is required")
    if sum(line.startswith("source solar ") for line in lines) != 1:
        raise LunarReptranPrestageError("exactly one custom source solar directive is required")
    if sum(line.startswith("atm_z_grid ") for line in lines) != 1:
        raise LunarReptranPrestageError("exactly one atm_z_grid directive is required")
    forbidden_prefixes = (
        "day_of_year ",
        "altitude ",
        "mc_elevation_file ",
        "source solar atlas_plus_modtran",
    )
    if any(line.startswith(forbidden_prefixes) for line in lines):
        raise LunarReptranPrestageError("forbidden distance/elevation/default-source directive emitted")


def render_lunar_mystic_reptran_prestage(
    *,
    data_dir: Path,
    atmosphere_file: Path,
    lunar_source_file: Path,
    moon_zenith_deg: float,
    target_altitude_deg: float,
    target_relative_azimuth_to_moon_deg: float,
    observer_elevation_m: float,
    aod550: float,
    albedo: float,
    photon_histories: int,
    synthetic_review_seed: int,
    case_dir: Path,
    alis_importance_nm: float = 550.0,
) -> tuple[str, dict]:
    """Render only; this module has no solver invocation or execution authorization."""
    moon_zenith = _finite("moon_zenith_deg", moon_zenith_deg, 0.0, 120.0)
    target_alt = _finite("target_altitude_deg", target_altitude_deg, 0.0, 90.0)
    relative_az = _finite(
        "target_relative_azimuth_to_moon_deg",
        target_relative_azimuth_to_moon_deg,
        0.0,
        360.0,
    )
    elevation = _finite("observer_elevation_m", observer_elevation_m, 0.0, 10000.0)
    aod = _finite("aod550", aod550, 0.0, 5.0)
    alb = _finite("albedo", albedo, 0.0, 1.0)
    alis = _finite("alis_importance_nm", alis_importance_nm, 550.0, 550.0)
    if not isinstance(photon_histories, int) or isinstance(photon_histories, bool) or photon_histories != 5_000_000:
        raise LunarReptranPrestageError("frozen photon_histories must equal 5000000")
    if not isinstance(synthetic_review_seed, int) or isinstance(synthetic_review_seed, bool) or synthetic_review_seed < 1:
        raise LunarReptranPrestageError("synthetic_review_seed must be a positive non-scientific fixture integer")

    data_dir = data_dir.resolve()
    atmosphere_file = atmosphere_file.resolve()
    lunar_source_file = lunar_source_file.resolve()
    case_dir = case_dir.resolve()
    if not atmosphere_file.is_file() or not lunar_source_file.is_file():
        raise LunarReptranPrestageError("atmosphere/source file missing")
    if atmosphere_file == lunar_source_file:
        raise LunarReptranPrestageError("source and atmosphere files may not alias")

    umu = -math.sin(math.radians(target_alt))
    lines = [
        f"data_files_path {data_dir}",
        f"atmosphere_file {atmosphere_file}",
        f"source solar {lunar_source_file}",
        "mol_abs_param reptran",
        "wavelength 380 780",
        f"sza {moon_zenith:.6f}",
        "phi0 0.000000",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {photon_histories}",
        "mc_vroom off",
        "mc_std",
        f"mc_randomseed {synthetic_review_seed}",
        f"mc_basename {(case_dir / 'mc').resolve()}",
        f"mc_spectral_is {alis:.1f}",
        f"albedo {alb:.6f}",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {aod:.6f}",
        f"zout {elevation / 1000.0:.6f}",
        f"umu {umu:.8f}",
        f"phi {relative_az:.6f}",
        "quiet",
    ]
    helper = _elevation_helper()
    corrected, site_altitude_km, atmosphere_grid_km = helper.apply_ground_site_atm_z_grid(
        "\n".join(lines) + "\n", elevation
    )
    validate_rendered_reptran_input(corrected, lunar_source_file)
    return corrected, {
        "schemaVersion": 1,
        "status": "SOLVER_FREE_REPTRAN_SOURCE_BINDING_PRESTAGE_ONLY",
        "baseMain": BASE_MAIN,
        "historicalExec003RendererBlob": HISTORICAL_EXEC003_RENDERER_BLOB,
        "sourceKind": "LUNAR_TOA_COLLIMATED_RESEARCH_SOURCE",
        "sourceFileUnit": "mW m-2 nm-1",
        "dayOfYearDistanceScalingApplied": False,
        "molecularAbsorption": "reptran",
        "crsFallbackAllowed": False,
        "observerElevationM": elevation,
        "siteAltitudeKm": site_altitude_km,
        "atmosphereGridKm": atmosphere_grid_km,
        "alisSpectralImportanceSamplingNm": alis,
        "mcSpherical": "1D",
        "mcVroom": False,
        "runtimeCapabilityVerified": False,
        "scientificSeedAllocated": False,
        "solverExecutionAuthorized": False,
        "protectedResultOpeningAuthorized": False,
        "productionAuthorized": False,
    }
