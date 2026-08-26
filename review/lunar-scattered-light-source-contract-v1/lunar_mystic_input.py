#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import math
from pathlib import Path
from typing import Iterable

HELPER = Path(__file__).resolve().parents[2] / 'experiments' / 'mystic-batch-v1' / 'twilight_surrogate_tier1_execution_adapter.py'

class LunarMysticInputError(ValueError):
    pass

def _finite(name, value, lo, hi):
    if isinstance(value, bool):
        raise LunarMysticInputError(f'{name} must be numeric')
    x = float(value)
    if not math.isfinite(x) or not lo <= x <= hi:
        raise LunarMysticInputError(f'{name} outside [{lo}, {hi}]')
    return x

def _elevation_helper():
    spec = importlib.util.spec_from_file_location('lunar_level_b_elevation_helper', HELPER)
    if spec is None or spec.loader is None:
        raise LunarMysticInputError('reviewed Level-B elevation helper unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def write_lunar_source_file(path: Path, wavelengths_nm: Iterable[float], lunar_toa_w_m2_nm: Iterable[float]) -> dict:
    wl = [float(x) for x in wavelengths_nm]
    ir = [float(x) for x in lunar_toa_w_m2_nm]
    if not wl or len(wl) != len(ir):
        raise LunarMysticInputError('lunar source arrays must have same nonzero length')
    if wl != sorted(wl) or len(set(wl)) != len(wl):
        raise LunarMysticInputError('lunar source wavelength grid must be strictly increasing')
    if wl[0] < 380.0 or wl[-1] > 780.0:
        raise LunarMysticInputError('lunar MYSTIC source must stay inside 380..780 nm')
    if any(not math.isfinite(x) or x < 0 for x in ir):
        raise LunarMysticInputError('lunar source irradiance must be finite and nonnegative')
    path.parent.mkdir(parents=True, exist_ok=True)
    # libRadtran solar source-file default spectral flux unit is mW/(m2 nm).
    path.write_text(''.join(f'{w:.6f} {1000.0 * e:.12e}\n' for w, e in zip(wl, ir)), encoding='utf-8')
    return {
        'schemaVersion': 1,
        'unit': 'mW m-2 nm-1',
        'inputUnit': 'W m-2 nm-1',
        'nodeCount': len(wl),
        'startNm': wl[0],
        'stopNm': wl[-1],
        'dayOfYearDistanceScalingApplied': False,
    }

def render_lunar_mystic_input(*,
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
    random_seed: int,
    case_dir: Path,
    alis_importance_nm: float = 550.0,
) -> tuple[str, dict]:
    moon_zenith = _finite('moon_zenith_deg', moon_zenith_deg, 0.0, 120.0)
    target_alt = _finite('target_altitude_deg', target_altitude_deg, 0.0, 90.0)
    relative_az = _finite('target_relative_azimuth_to_moon_deg', target_relative_azimuth_to_moon_deg, 0.0, 360.0)
    elevation = _finite('observer_elevation_m', observer_elevation_m, 0.0, 10000.0)
    aod = _finite('aod550', aod550, 0.0, 5.0)
    alb = _finite('albedo', albedo, 0.0, 1.0)
    alis = _finite('alis_importance_nm', alis_importance_nm, 380.0, 780.0)
    if not isinstance(photon_histories, int) or isinstance(photon_histories, bool) or photon_histories < 1:
        raise LunarMysticInputError('photon_histories must be positive integer')
    if not isinstance(random_seed, int) or isinstance(random_seed, bool) or random_seed < 1:
        raise LunarMysticInputError('random_seed must be positive integer')
    data_dir = data_dir.resolve()
    atmosphere_file = atmosphere_file.resolve()
    lunar_source_file = lunar_source_file.resolve()
    case_dir = case_dir.resolve()
    if not atmosphere_file.is_file() or not lunar_source_file.is_file():
        raise LunarMysticInputError('atmosphere/source file missing')
    if lunar_source_file == atmosphere_file:
        raise LunarMysticInputError('source and atmosphere files may not alias')
    umu = -math.sin(math.radians(target_alt))
    lines = [
        f'data_files_path {data_dir}',
        f'atmosphere_file {atmosphere_file}',
        f'source solar {lunar_source_file}',
        'mol_abs_param crs',
        'wavelength 380 780',
        f'sza {moon_zenith:.6f}',
        'phi0 0.000000',
        'rte_solver mystic',
        'mc_spherical 1D',
        f'mc_photons {photon_histories}',
        'mc_vroom off',
        'mc_std',
        f'mc_randomseed {random_seed}',
        f'mc_basename {(case_dir / "mc").resolve()}',
        f'mc_spectral_is {alis:.1f}',
        f'albedo {alb:.6f}',
        'aerosol_default',
        f'aerosol_set_tau_at_wvl 550 {aod:.6f}',
        f'zout {elevation / 1000.0:.6f}',
        f'umu {umu:.8f}',
        f'phi {relative_az:.6f}',
        'quiet',
    ]
    base = '\n'.join(lines) + '\n'
    helper = _elevation_helper()
    corrected, site_altitude_km, atmosphere_grid_km = helper.apply_ground_site_atm_z_grid(base, elevation)
    forbidden = ('day_of_year ', 'altitude ', 'mc_elevation_file ', 'source solar atlas_plus_modtran')
    if any(token in corrected for token in forbidden):
        raise LunarMysticInputError('forbidden source/elevation/distance-scaling directive emitted')
    if corrected.count(f'source solar {lunar_source_file}') != 1:
        raise LunarMysticInputError('exact custom lunar source not emitted once')
    if corrected.count('zout 0.000000') != 1 or corrected.count('atm_z_grid ') != 1:
        raise LunarMysticInputError('ground-site representation drift')
    return corrected, {
        'schemaVersion': 1,
        'sourceKind': 'LUNAR_TOA_COLLIMATED_RESEARCH_SOURCE',
        'sourceFileUnit': 'mW m-2 nm-1',
        'moonZenithDeg': moon_zenith,
        'targetAltitudeDeg': target_alt,
        'targetRelativeAzimuthToMoonDeg': relative_az,
        'observerElevationM': elevation,
        'siteAltitudeKm': site_altitude_km,
        'atmosphereGridKm': atmosphere_grid_km,
        'dayOfYearDistanceScalingApplied': False,
        'finiteMoonDiskModeled': False,
        'sameAtmosphereStateRequiredForComposition': True,
        'validatedForAtmosphericScatteredMoonlight': False,
        'productionAuthorized': False,
    }
