#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import math
from pathlib import Path
from typing import Iterable

HELPER = Path(__file__).resolve().parents[2] / 'experiments' / 'mystic-batch-v1' / 'twilight_surrogate_tier1_execution_adapter.py'
CRS_SOURCE_BINDING_RESULT = Path(__file__).with_name('libradtran-custom-source-crs-admission-result-v1.json')

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

def _require_verified_crs_source_binding(runtime_identity: dict | None) -> dict:
    """Bind the renderer to the exact runtime tuple that passed source-file admission.

    This gate proves only that the custom extraterrestrial source amplitude is
    consumed with ``mol_abs_param crs`` on the exact frozen libRadtran runtime.
    It is not an empirical moonlit-sky validation or production authorization.
    """
    if not isinstance(runtime_identity, dict):
        raise LunarMysticInputError('exact libRadtran runtime identity required for lunar CRS custom source')
    if not CRS_SOURCE_BINDING_RESULT.is_file():
        raise LunarMysticInputError('lunar CRS custom-source admission result unavailable')
    try:
        result = json.loads(CRS_SOURCE_BINDING_RESULT.read_text(encoding='utf-8'))
    except Exception as exc:
        raise LunarMysticInputError('cannot read lunar CRS custom-source admission result') from exc
    if result.get('contractId') != 'libradtran-custom-source-crs-admission-gate-v1':
        raise LunarMysticInputError('lunar CRS source-binding contract identity drift')
    if result.get('status') != 'PASS_CUSTOM_SOURCE_WITH_CRS_CONSUMED_EXACT_RUNTIME':
        raise LunarMysticInputError('lunar CRS custom-source admission has not passed')
    interpretation = result.get('interpretation') or {}
    if interpretation.get('customSourceAmplitudeConsumedWithMolAbsParamCrsForExactRuntimeTuple') is not True:
        raise LunarMysticInputError('lunar CRS source consumption capability not proven')
    if interpretation.get('atmosphericScatteredMoonlightValidatedByThisResult') is not False:
        raise LunarMysticInputError('source-binding result scientific boundary drift')
    if interpretation.get('productionAuthorized') is not False:
        raise LunarMysticInputError('source-binding result production boundary drift')
    observed = result.get('observed') or {}
    ratios = observed.get('armBToArmARatio')
    tolerance = observed.get('maximumAbsoluteRatioDeviationAllowed')
    if ratios != [7.0, 7.0, 7.0] or tolerance != 0.01 or observed.get('maximumAbsoluteRatioDeviationObserved') != 0.0:
        raise LunarMysticInputError('source-binding frozen decision evidence drift')
    runtime = result.get('runtime') or {}
    for key in ('uvspecSha256', 'libRadtranDataTreeSha256'):
        if runtime_identity.get(key) != runtime.get(key):
            raise LunarMysticInputError(f'lunar CRS source-binding runtime mismatch: {key}')
    evidence = result.get('evidence') or {}
    if evidence.get('workflowRunAttempt') != 1 or evidence.get('artifactDigest') != 'sha256:5f9c2a642a61a5a82fd62e2ccd3f5e5f1ad287b9580f1097a8dbacbbfb23a42b':
        raise LunarMysticInputError('source-binding immutable evidence identity drift')
    return {
        'contractId': result['contractId'],
        'status': result['status'],
        'workflowRunId': evidence.get('workflowRunId'),
        'workflowRunAttempt': evidence.get('workflowRunAttempt'),
        'artifactId': evidence.get('artifactId'),
        'artifactDigest': evidence.get('artifactDigest'),
        'probeReportSha256': evidence.get('probeReportSha256'),
        'uvspecSha256': runtime.get('uvspecSha256'),
        'libRadtranDataTreeSha256': runtime.get('libRadtranDataTreeSha256'),
        'capabilityOnly': True,
        'atmosphericScatteredMoonlightValidated': False,
        'productionAuthorized': False,
    }

def write_lunar_source_file(path: Path, wavelengths_nm: Iterable[float], lunar_toa_w_m2_nm: Iterable[float]) -> dict:
    wl = [float(x) for x in wavelengths_nm]
    ir = [float(x) for x in lunar_toa_w_m2_nm]
    if len(wl) < 2 or len(wl) != len(ir):
        raise LunarMysticInputError('lunar source arrays must have same length with at least two nodes')
    if wl != sorted(wl) or len(set(wl)) != len(wl):
        raise LunarMysticInputError('lunar source wavelength grid must be strictly increasing')
    if wl[0] != 380.0 or wl[-1] != 780.0:
        raise LunarMysticInputError('lunar MYSTIC source must explicitly cover exact 380 and 780 nm endpoints')
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
        'exactRequestedWavelengthCoverage': True,
        'dayOfYearDistanceScalingApplied': False,
    }

def finite_disk_direction_samples(*,
    moon_zenith_deg: float,
    target_altitude_deg: float,
    target_relative_azimuth_to_moon_deg: float,
    lunar_angular_radius_deg: float,
) -> tuple[dict, ...]:
    """Return the frozen 33-direction finite-disk sensitivity geometry.

    This is a directional transfer-kernel sampling plan, not a physical lunar
    brightness model. Every returned direction is intended to be run with the
    same full disk-integrated ROLO irradiance. The original Moon-center azimuth
    is defined as 0 deg. Ring position angle 0 deg points along the tangent
    toward local zenith; 90 deg points toward increasing astronomical azimuth.
    The target direction remains fixed in that original local frame, so the
    target relative azimuth is recomputed for every offset source direction.
    """
    moon_zenith = _finite('moon_zenith_deg', moon_zenith_deg, 0.0, 120.0)
    target_alt = _finite('target_altitude_deg', target_altitude_deg, 0.0, 90.0)
    target_rel_az = _finite('target_relative_azimuth_to_moon_deg', target_relative_azimuth_to_moon_deg, 0.0, 360.0)
    angular_radius = _finite('lunar_angular_radius_deg', lunar_angular_radius_deg, 0.0, 1.0)
    if angular_radius <= 0.0:
        raise LunarMysticInputError('lunar_angular_radius_deg must be > 0')

    theta = math.radians(moon_zenith)
    center = (math.sin(theta), 0.0, math.cos(theta))
    # Unit tangent vectors at center azimuth=0. Position angle 0 is zenithward;
    # +90 degrees is toward increasing azimuth.
    zenithward = (-math.cos(theta), 0.0, math.sin(theta))
    azimuthward = (0.0, 1.0, 0.0)

    def sample_at(radius_fraction: float, position_angle_deg: float, sample_id: str) -> dict:
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
        sample_zenith = math.degrees(math.acos(max(-1.0, min(1.0, z))))
        sample_azimuth = math.degrees(math.atan2(y, x)) % 360.0
        target_relative = (target_rel_az - sample_azimuth) % 360.0
        dot = max(-1.0, min(1.0, sum(center[i] * direction[i] / norm for i in range(3))))
        actual_offset = math.degrees(math.acos(dot))
        return {
            'sampleId': sample_id,
            'radiusFraction': radius_fraction,
            'positionAngleDeg': position_angle_deg,
            'angularOffsetDeg': actual_offset,
            'sourceZenithDeg': sample_zenith,
            'sourceAzimuthInCenterFrameDeg': sample_azimuth,
            'targetAltitudeDeg': target_alt,
            'targetRelativeAzimuthToSampleSourceDeg': target_relative,
            'sameFullDiskIntegratedRoloIrradianceRequired': True,
            'physicalResolvedDiskWeight': None,
        }

    samples = [sample_at(0.0, 0.0, 'center')]
    for radius_fraction, ring_label in ((0.5, 'r050'), (1.0, 'r100')):
        for index in range(16):
            position_angle = 22.5 * index
            samples.append(sample_at(radius_fraction, position_angle, f'{ring_label}-pa{index:02d}'))
    if len(samples) != 33:
        raise LunarMysticInputError('finite-disk sampling plan must contain exactly 33 directions')
    return tuple(samples)

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
    runtime_identity: dict | None = None,
    alis_importance_nm: float = 550.0,
) -> tuple[str, dict]:
    source_binding = _require_verified_crs_source_binding(runtime_identity)
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
        'customSourceCrsConsumptionCapabilityVerified': True,
        'customSourceCrsBinding': source_binding,
        'sameAtmosphereStateRequiredForComposition': True,
        'validatedForAtmosphericScatteredMoonlight': False,
        'productionAuthorized': False,
    }
