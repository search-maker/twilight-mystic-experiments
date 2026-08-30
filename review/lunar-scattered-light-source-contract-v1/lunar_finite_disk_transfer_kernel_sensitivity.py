#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1.json'
LUNAR_INPUT_PATH = HERE / 'lunar_mystic_input.py'


class LunarFiniteDiskSensitivityError(ValueError):
    pass


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarFiniteDiskSensitivityError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract() -> dict:
    contract = json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))
    if contract.get('contractId') != 'lunar-finite-disk-transfer-kernel-sensitivity-v1':
        raise LunarFiniteDiskSensitivityError('finite-disk contract identity drift')
    if contract.get('status') != 'FROZEN_REVIEW_ONLY_NO_SOLVER_EXECUTION':
        raise LunarFiniteDiskSensitivityError('finite-disk contract status drift')
    if contract['reporting'].get('acceptanceThreshold') is not None:
        raise LunarFiniteDiskSensitivityError('result-dependent finite-disk acceptance threshold forbidden')
    return contract


def lunar_angular_radius_deg(*, moon_radius_km: float, observer_moon_distance_km: float) -> float:
    r = float(moon_radius_km)
    d = float(observer_moon_distance_km)
    if not math.isfinite(r) or not math.isfinite(d) or r <= 0.0 or d <= r:
        raise LunarFiniteDiskSensitivityError('invalid lunar radius/distance geometry')
    return math.degrees(math.asin(r / d))


def frozen_cases(contract: dict | None = None) -> tuple[dict, ...]:
    c = contract or load_contract()
    physical = c['physicalGeometry']
    design = c['numericalDesign']
    sampling = c['directionSampling']
    lunar_input = _load_module('lunar_finite_disk_input_dependency', LUNAR_INPUT_PATH)

    angular_radius = lunar_angular_radius_deg(
        moon_radius_km=physical['moonReferenceRadiusKm'],
        observer_moon_distance_km=physical['observerMoonDistanceKm'],
    )
    expected_radius = float(physical['expectedAngularRadiusDeg'])
    if abs(angular_radius - expected_radius) > 1e-12:
        raise LunarFiniteDiskSensitivityError('derived lunar angular radius drift')

    rows: list[dict] = []
    seed = int(design['candidateSeedStart'])
    for elevation_m in physical['observerElevationM']:
        for center_rel_az in physical['targetRelativeAzimuthToMoonCenterDeg']:
            samples = lunar_input.finite_disk_direction_samples(
                moon_zenith_deg=physical['moonCenterZenithDeg'],
                target_altitude_deg=physical['targetAltitudeDeg'],
                target_relative_azimuth_to_moon_deg=center_rel_az,
                lunar_angular_radius_deg=angular_radius,
            )
            geometry_key = f'e{int(round(elevation_m)):04d}-az{int(round(center_rel_az)):03d}'
            for sample in samples:
                rows.append({
                    'caseId': f'fd550-{geometry_key}-{sample["sampleId"]}',
                    'geometryKey': geometry_key,
                    'observerElevationM': float(elevation_m),
                    'moonCenterZenithDeg': float(physical['moonCenterZenithDeg']),
                    'targetAltitudeDeg': float(physical['targetAltitudeDeg']),
                    'targetRelativeAzimuthToMoonCenterDeg': float(center_rel_az),
                    'lunarAngularRadiusDeg': angular_radius,
                    'sampleId': sample['sampleId'],
                    'radiusFraction': float(sample['radiusFraction']),
                    'positionAngleDeg': float(sample['positionAngleDeg']),
                    'angularOffsetDeg': float(sample['angularOffsetDeg']),
                    'sourceZenithDeg': float(sample['sourceZenithDeg']),
                    'sourceAzimuthInCenterFrameDeg': float(sample['sourceAzimuthInCenterFrameDeg']),
                    'targetRelativeAzimuthToSampleSourceDeg': float(sample['targetRelativeAzimuthToSampleSourceDeg']),
                    'wavelengthNm': float(design['wavelengthNm']),
                    'photonHistories': int(design['photonHistoriesPerDirectionalCase']),
                    'randomSeed': seed,
                    'sameFullDiskIntegratedRoloIrradianceRequired': True,
                    'physicalResolvedDiskWeight': None,
                    'finiteMoonDiskModeled': False,
                })
                seed += 1

    expected_count = int(sampling['totalDirectionalCases'])
    if len(rows) != expected_count:
        raise LunarFiniteDiskSensitivityError(f'finite-disk case-count drift: {len(rows)} != {expected_count}')
    if rows[0]['randomSeed'] != design['candidateSeedStart'] or rows[-1]['randomSeed'] != design['candidateSeedStop']:
        raise LunarFiniteDiskSensitivityError('finite-disk candidate seed range drift')
    if len({row['caseId'] for row in rows}) != len(rows) or len({row['randomSeed'] for row in rows}) != len(rows):
        raise LunarFiniteDiskSensitivityError('finite-disk case/seed uniqueness drift')
    return tuple(rows)


def validate_plan(cases: tuple[dict, ...] | None = None, contract: dict | None = None) -> dict:
    c = contract or load_contract()
    rows = cases or frozen_cases(c)
    by_geometry: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_geometry[row['geometryKey']].append(row)
    expected_geometries = int(c['directionSampling']['atmosphereTargetConfigurations'])
    expected_per_geometry = int(c['directionSampling']['directionsPerAtmosphereTargetConfiguration'])
    if len(by_geometry) != expected_geometries:
        raise LunarFiniteDiskSensitivityError('finite-disk geometry-count drift')
    for geometry_key, group in by_geometry.items():
        if len(group) != expected_per_geometry:
            raise LunarFiniteDiskSensitivityError(f'{geometry_key} direction-count drift')
        radii = [row['radiusFraction'] for row in group]
        if radii.count(0.0) != 1 or radii.count(0.5) != 16 or radii.count(1.0) != 16:
            raise LunarFiniteDiskSensitivityError(f'{geometry_key} ring cardinality drift')
        radius = group[0]['lunarAngularRadiusDeg']
        for row in group:
            expected_offset = radius * row['radiusFraction']
            if abs(row['angularOffsetDeg'] - expected_offset) > 2e-9:
                raise LunarFiniteDiskSensitivityError(f'{row["caseId"]} angular offset drift')
            if row['physicalResolvedDiskWeight'] is not None:
                raise LunarFiniteDiskSensitivityError('physical resolved-disk weighting is not admitted')
            if row['sameFullDiskIntegratedRoloIrradianceRequired'] is not True:
                raise LunarFiniteDiskSensitivityError('directional probe source normalization drift')
    return {
        'contractId': c['contractId'],
        'caseCount': len(rows),
        'geometryCount': len(by_geometry),
        'directionsPerGeometry': expected_per_geometry,
        'candidateSeedCount': len({row['randomSeed'] for row in rows}),
        'lunarAngularRadiusDeg': rows[0]['lunarAngularRadiusDeg'],
        'solverExecutionAuthorized': False,
        'resultOpeningAuthorized': False,
    }


def render_case_input(
    case: dict,
    *,
    data_dir: Path,
    atmosphere_file: Path,
    lunar_source_file: Path,
    case_dir: Path,
    runtime_identity: dict,
    contract: dict | None = None,
) -> tuple[str, dict]:
    c = contract or load_contract()
    expected = {row['caseId']: row for row in frozen_cases(c)}
    if case.get('caseId') not in expected or case != expected[case['caseId']]:
        raise LunarFiniteDiskSensitivityError('case is not byte-semantically equal to frozen planner row')
    lunar_input = _load_module('lunar_finite_disk_render_dependency', LUNAR_INPUT_PATH)
    text, meta = lunar_input.render_lunar_mystic_input(
        data_dir=data_dir,
        atmosphere_file=atmosphere_file,
        lunar_source_file=lunar_source_file,
        moon_zenith_deg=case['sourceZenithDeg'],
        target_altitude_deg=case['targetAltitudeDeg'],
        target_relative_azimuth_to_moon_deg=case['targetRelativeAzimuthToSampleSourceDeg'],
        observer_elevation_m=case['observerElevationM'],
        aod550=c['runtimeAndAtmosphere']['aod550'],
        albedo=c['runtimeAndAtmosphere']['lambertianAlbedo'],
        photon_histories=case['photonHistories'],
        random_seed=case['randomSeed'],
        case_dir=case_dir,
        runtime_identity=runtime_identity,
        alis_importance_nm=c['numericalDesign']['wavelengthNm'],
    )
    if meta.get('finiteMoonDiskModeled') is not False:
        raise LunarFiniteDiskSensitivityError('directional probe was mislabeled as finite-disk model')
    return text, {
        **meta,
        'finiteDiskSensitivityCaseId': case['caseId'],
        'geometryKey': case['geometryKey'],
        'sampleId': case['sampleId'],
        'radiusFraction': case['radiusFraction'],
        'positionAngleDeg': case['positionAngleDeg'],
        'lunarAngularRadiusDeg': case['lunarAngularRadiusDeg'],
        'sameFullDiskIntegratedRoloIrradianceRequired': True,
        'physicalResolvedDiskWeight': None,
        'finiteDiskSensitivityDiagnosticOnly': True,
        'finiteMoonDiskValidated': False,
        'productionAuthorized': False,
    }


def _incomplete(reason: str, expected_count: int, observed_count: int) -> dict:
    return {
        'schemaVersion': 1,
        'contractId': 'lunar-finite-disk-transfer-kernel-sensitivity-v1',
        'classification': 'EXECUTION_INCOMPLETE',
        'executionComplete': False,
        'caseCountExpected': expected_count,
        'caseCountObserved': observed_count,
        'reasons': [reason],
        'finiteMoonDiskValidated': False,
        'continuousDiskBoundProven': False,
        'physicalResolvedDiskIntegrationImplemented': False,
        'empiricalAtmosphericMoonlightValidated': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
    }


def evaluate_records(records: list[dict], contract: dict | None = None) -> dict:
    c = contract or load_contract()
    cases = frozen_cases(c)
    expected = {row['caseId']: row for row in cases}
    if not isinstance(records, list):
        return _incomplete('records must be a list', len(cases), 0)
    observed: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('caseId'), str):
            return _incomplete('malformed result record', len(cases), len(records))
        case_id = record['caseId']
        if case_id not in expected:
            return _incomplete(f'unexpected caseId: {case_id}', len(cases), len(records))
        if case_id in observed:
            return _incomplete(f'duplicate caseId: {case_id}', len(cases), len(records))
        observed[case_id] = record
    if set(observed) != set(expected):
        missing = sorted(set(expected) - set(observed))
        return _incomplete(f'missing cases: {missing[:5]}', len(cases), len(records))

    for case_id, record in observed.items():
        if record.get('solverExitCode') != 0:
            return _incomplete(f'nonzero solver exit: {case_id}', len(cases), len(records))
        radiance = record.get('radiance')
        std = record.get('stdRadiance')
        if isinstance(radiance, bool) or not isinstance(radiance, (int, float)) or not math.isfinite(float(radiance)) or float(radiance) <= 0.0:
            return _incomplete(f'nonpositive/nonfinite radiance: {case_id}', len(cases), len(records))
        if isinstance(std, bool) or not isinstance(std, (int, float)) or not math.isfinite(float(std)) or float(std) < 0.0:
            return _incomplete(f'negative/nonfinite std radiance: {case_id}', len(cases), len(records))

    sigma_mult = float(c['reporting']['mcUncertaintyExpansionSigmaMultiplier'])
    by_geometry: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        by_geometry[case['geometryKey']].append({**case, **observed[case['caseId']]})

    geometry_reports: list[dict] = []
    unresolved_uncertainty = False
    for geometry_key in sorted(by_geometry):
        group = by_geometry[geometry_key]
        center = next(row for row in group if row['radiusFraction'] == 0.0)
        lc = float(center['radiance'])
        sc = float(center['stdRadiance'])
        center_low = max(0.0, lc - sigma_mult * sc)
        center_high = lc + sigma_mult * sc
        ratios = [float(row['radiance']) / lc for row in group]
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        expanded_lower: list[float] = []
        expanded_upper: list[float] = []
        if center_low <= 0.0:
            unresolved_uncertainty = True
        else:
            for row in group:
                l = float(row['radiance'])
                s = float(row['stdRadiance'])
                expanded_lower.append(max(0.0, l - sigma_mult * s) / center_high)
                expanded_upper.append((l + sigma_mult * s) / center_low)

        ringwise = {}
        for radius_fraction in (0.0, 0.5, 1.0):
            ring = [float(row['radiance']) for row in group if row['radiusFraction'] == radius_fraction]
            ringwise[str(radius_fraction)] = {
                'count': len(ring),
                'minimumRadiance': min(ring),
                'maximumRadiance': max(ring),
                'meanRadiance': sum(ring) / len(ring),
            }

        report = {
            'geometryKey': geometry_key,
            'observerElevationM': center['observerElevationM'],
            'targetRelativeAzimuthToMoonCenterDeg': center['targetRelativeAzimuthToMoonCenterDeg'],
            'centralDirectionRadiance': lc,
            'centralDirectionStdRadiance': sc,
            'minimumSampledDirectionRadiance': min(float(row['radiance']) for row in group),
            'maximumSampledDirectionRadiance': max(float(row['radiance']) for row in group),
            'sampledRangeFractionOfCentral': (max(float(row['radiance']) for row in group) - min(float(row['radiance']) for row in group)) / lc,
            'maximumAbsoluteSampledDeviationFractionOfCentral': max(abs(ratio - 1.0) for ratio in ratios),
            'sampledRatioToCentralMinimum': min_ratio,
            'sampledRatioToCentralMaximum': max_ratio,
            'ringwise': ringwise,
            'uncertaintyExpandedRatioDiagnosticAvailable': center_low > 0.0,
            'uncertaintyExpansionSigmaMultiplier': sigma_mult,
            'simultaneousCoverageCalibrated': False,
        }
        if center_low > 0.0:
            lower = min(expanded_lower)
            upper = max(expanded_upper)
            report.update({
                'uncertaintyExpandedRatioToCentralMinimumDiagnostic': lower,
                'uncertaintyExpandedRatioToCentralMaximumDiagnostic': upper,
                'maximumAbsoluteUncertaintyExpandedDeviationFractionOfCentralDiagnostic': max(1.0 - lower, upper - 1.0),
            })
        geometry_reports.append(report)

    classification = (
        'COMPLETE_550NM_SAMPLED_DIRECTIONAL_SENSITIVITY_MC_UNRESOLVED'
        if unresolved_uncertainty
        else c['reporting']['classificationOnCompleteExecution']
    )
    return {
        'schemaVersion': 1,
        'contractId': c['contractId'],
        'classification': classification,
        'executionComplete': True,
        'caseCountExpected': len(cases),
        'caseCountObserved': len(records),
        'wavelengthNm': c['numericalDesign']['wavelengthNm'],
        'lunarAngularRadiusDeg': cases[0]['lunarAngularRadiusDeg'],
        'geometryReports': geometry_reports,
        'acceptanceThresholdApplied': False,
        'sampledDirectionalSensitivityDiagnosticComputed': True,
        'sampledEnvelopeIsExactContinuousDiskBound': False,
        'resolvedLunarBrightnessModelAssumed': False,
        'mandatorySpectralFollowOnRequiredBeforeBroadbandFiniteDiskClaim': True,
        'finiteMoonDiskValidated': False,
        'continuousDiskBoundProven': False,
        'physicalResolvedDiskIntegrationImplemented': False,
        'empiricalAtmosphericMoonlightValidated': False,
        'toaSourceValidated': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
    }


if __name__ == '__main__':
    print(json.dumps(validate_plan(), indent=2, sort_keys=True))
