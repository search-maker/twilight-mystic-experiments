#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / 'lunar-mystic-computational-precision-v1.json'
ROLO = HERE / 'rolo311g.py'
LUNAR_INPUT = HERE / 'lunar_mystic_input.py'


class LunarPrecisionError(RuntimeError):
    pass


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarPrecisionError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('contractId') != 'lunar-mystic-computational-precision-v1':
        raise LunarPrecisionError('contract identity drift')
    if data.get('status') != 'FROZEN_REVIEW_ONLY_NO_SOLVER_EXECUTION':
        raise LunarPrecisionError('contract status drift')
    opening = data.get('executionOpeningGate') or {}
    if opening.get('solverExecutionAuthorizedByThisFile') is not False:
        raise LunarPrecisionError('review contract may not authorize solver execution')
    if opening.get('resultOpeningAuthorizedByThisFile') is not False:
        raise LunarPrecisionError('review contract may not authorize result opening')
    protected = data.get('protectedBoundaries') or {}
    for key in (
        'taylorResidualUsed', 'jerusalemResidualUsed', 'xshooterResidualOpened',
        'airLusiResidualOpened', 'parameterFitOrTuningAllowed',
        'empiricalAtmosphericValidationClaimAllowed', 'toaValidationClaimAllowed',
        'totalSkyValidationClaimAllowed', 'productionAuthorized',
    ):
        if protected.get(key) is not False:
            raise LunarPrecisionError(f'protected boundary drift: {key}')
    return data


def _numeric_rows(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding='utf-8', errors='strict').splitlines():
        text = raw.strip()
        if not text or text.startswith('#'):
            continue
        parts = text.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[1])
        except ValueError:
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value):
            raise LunarPrecisionError(f'nonfinite spectral row in {path}')
        rows.append((wavelength, value))
    if len(rows) < 2:
        raise LunarPrecisionError(f'not enough numeric spectral rows in {path}')
    wavelengths = [row[0] for row in rows]
    if wavelengths != sorted(wavelengths) or len(set(wavelengths)) != len(wavelengths):
        raise LunarPrecisionError(f'wavelength grid not strictly increasing in {path}')
    return rows


def interpolate_spectrum(rows: list[tuple[float, float]], wavelengths_nm: Iterable[float]) -> list[float]:
    requested = [float(w) for w in wavelengths_nm]
    if not requested:
        raise LunarPrecisionError('requested wavelength grid empty')
    if requested != sorted(requested) or len(set(requested)) != len(requested):
        raise LunarPrecisionError('requested wavelength grid must be strictly increasing')
    if requested[0] < rows[0][0] or requested[-1] > rows[-1][0]:
        raise LunarPrecisionError('requested wavelengths not bracketed by source spectrum')
    out: list[float] = []
    j = 0
    for wavelength in requested:
        while j + 1 < len(rows) and rows[j + 1][0] < wavelength:
            j += 1
        if rows[j][0] == wavelength:
            value = rows[j][1]
        elif j + 1 < len(rows) and rows[j + 1][0] == wavelength:
            value = rows[j + 1][1]
        else:
            if j + 1 >= len(rows):
                raise LunarPrecisionError('interpolation bracket unavailable')
            w0, v0 = rows[j]
            w1, v1 = rows[j + 1]
            if not (w0 < wavelength < w1):
                raise LunarPrecisionError('interpolation interval drift')
            t = (wavelength - w0) / (w1 - w0)
            value = v0 * (1.0 - t) + v1 * t
        if not math.isfinite(value) or value < 0:
            raise LunarPrecisionError('invalid interpolated solar irradiance')
        out.append(value)
    return out


def wavelength_grid(contract: dict[str, Any]) -> list[float]:
    spec = contract['spectralConstruction']
    start = float(spec['wavelengthStartNm'])
    stop = float(spec['wavelengthStopNm'])
    step = float(spec['wavelengthStepNm'])
    count = int(round((stop - start) / step)) + 1
    grid = [start + i * step for i in range(count)]
    if grid[0] != 380.0 or grid[-1] != 780.0 or len(grid) != 401:
        raise LunarPrecisionError('frozen 380..780 nm 1-nm grid drift')
    return grid


def build_lunar_source_from_runtime_atlas(
    atlas_path: Path,
    destination: Path,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    rolo = _load_module('lunar_precision_rolo311g', ROLO)
    lunar_input = _load_module('lunar_precision_input', LUNAR_INPUT)
    grid = wavelength_grid(contract)
    atlas_rows = _numeric_rows(atlas_path)
    # atlas_plus_modtran is mW m-2 nm-1 in the pinned libRadtran data tree.
    solar_mw = interpolate_spectrum(atlas_rows, grid)
    solar_w = [value / 1000.0 for value in solar_mw]
    g = contract['frozenRoloGeometry']
    geometry = rolo.RoloGeometry(
        phase_deg=g['phaseDeg'],
        subobserver_latitude_deg=g['subobserverLatitudeDeg'],
        subobserver_longitude_deg=g['subobserverLongitudeDeg'],
        subsolar_longitude_deg=g['subsolarLongitudeDeg'],
        sun_moon_distance_au=g['sunMoonDistanceAu'],
        observer_moon_distance_km=g['observerMoonDistanceKm'],
    )
    reconstructed = rolo.reconstruct_spectrum(grid, solar_w, geometry)
    source_meta = lunar_input.write_lunar_source_file(
        destination,
        reconstructed['wavelengthNm'],
        reconstructed['lunarToaIrradianceWm2Nm'],
    )
    return {
        'schemaVersion': 1,
        'atlasPath': str(atlas_path),
        'atlasUnit': 'mW m-2 nm-1',
        'sourceMetadata': source_meta,
        'roloReconstructionId': reconstructed['reconstructionId'],
        'roloGeometry': reconstructed['geometry'],
        'independentToaValidationClaim': False,
        'atmosphericScatteredMoonlightValidationClaim': False,
        'productionAuthorized': False,
    }


def frozen_cases(contract: dict[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    contract = contract or load_contract()
    grid = contract['geometryGrid']
    numerical = contract['numericalDesign']
    azimuths = [float(x) for x in grid['targetRelativeAzimuthToMoonDeg']]
    elevations = [float(x) for x in grid['observerElevationM']]
    seeds = list(numerical['freshIndependentSeeds'])
    expected = len(azimuths) * len(elevations) * int(numerical['replicatesPerGeometry'])
    if expected != 12 or len(seeds) != expected or len(set(seeds)) != len(seeds):
        raise LunarPrecisionError('frozen case/seed cardinality drift')
    cases: list[dict[str, Any]] = []
    index = 0
    for elevation in elevations:
        for azimuth in azimuths:
            geometry_id = f'e{int(elevation):04d}-az{int(azimuth):03d}'
            for replicate in range(1, int(numerical['replicatesPerGeometry']) + 1):
                cases.append({
                    'caseId': f'{geometry_id}-r{replicate}',
                    'geometryId': geometry_id,
                    'replicate': replicate,
                    'moonZenithDeg': float(grid['moonZenithDeg']),
                    'targetAltitudeDeg': float(grid['targetAltitudeDeg']),
                    'targetRelativeAzimuthToMoonDeg': azimuth,
                    'observerElevationM': elevation,
                    'aod550': float(contract['atmosphereAndSurface']['aod550']),
                    'albedo': float(contract['atmosphereAndSurface']['lambertianAlbedo']),
                    'photonHistories': int(numerical['photonHistoriesPerReplicate']),
                    'randomSeed': int(seeds[index]),
                    'alisImportanceNm': float(numerical['alisImportanceWavelengthNm']),
                })
                index += 1
    return tuple(cases)


def prepare_inputs(
    *,
    data_dir: Path,
    atmosphere_file: Path,
    atlas_path: Path,
    output_root: Path,
    runtime_identity: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    lunar_input = _load_module('lunar_precision_input_prepare', LUNAR_INPUT)
    output_root.mkdir(parents=True, exist_ok=True)
    source_file = output_root / 'lunar-source-380-780nm.dat'
    source_meta = build_lunar_source_from_runtime_atlas(atlas_path, source_file, contract)
    prepared: list[dict[str, Any]] = []
    for case in frozen_cases(contract):
        case_dir = output_root / case['caseId']
        case_dir.mkdir(parents=True, exist_ok=True)
        text, metadata = lunar_input.render_lunar_mystic_input(
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            lunar_source_file=source_file,
            moon_zenith_deg=case['moonZenithDeg'],
            target_altitude_deg=case['targetAltitudeDeg'],
            target_relative_azimuth_to_moon_deg=case['targetRelativeAzimuthToMoonDeg'],
            observer_elevation_m=case['observerElevationM'],
            aod550=case['aod550'],
            albedo=case['albedo'],
            photon_histories=case['photonHistories'],
            random_seed=case['randomSeed'],
            case_dir=case_dir,
            runtime_identity=runtime_identity,
            alis_importance_nm=case['alisImportanceNm'],
        )
        if text.count('atm_z_grid ') != 1 or text.count('zout 0.000000') != 1:
            raise LunarPrecisionError(f'elevated-site representation drift for {case["caseId"]}')
        if 'altitude ' in text:
            raise LunarPrecisionError(f'legacy altitude directive emitted for {case["caseId"]}')
        input_path = case_dir / 'case.inp'
        input_path.write_text(text, encoding='utf-8')
        item = {**case, 'inputPath': str(input_path), 'renderMetadata': metadata}
        (case_dir / 'prepared.json').write_text(json.dumps(item, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        prepared.append(item)
    manifest = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': 'PREPARED_NO_SOLVER_EXECUTION',
        'source': source_meta,
        'caseCount': len(prepared),
        'cases': prepared,
        'scientificSolverExecuted': False,
        'resultsOpened': False,
        'empiricalValidationClaim': False,
        'productionAuthorized': False,
    }
    (output_root / 'prepared-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def _read_spectral_last_column(path: Path) -> tuple[list[float], list[float]]:
    wavelengths: list[float] = []
    values: list[float] = []
    for raw in path.read_text(encoding='utf-8', errors='strict').splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        try:
            wavelength = float(parts[0])
            value = float(parts[-1])
        except ValueError:
            continue
        if not math.isfinite(wavelength) or not math.isfinite(value):
            raise LunarPrecisionError(f'nonfinite output row in {path}')
        wavelengths.append(wavelength)
        values.append(value)
    if not wavelengths:
        raise LunarPrecisionError(f'no numeric spectral output in {path}')
    if wavelengths != sorted(wavelengths):
        raise LunarPrecisionError(f'output wavelengths not sorted in {path}')
    return wavelengths, values


def _value_at(wavelengths: list[float], values: list[float], target_nm: float, tolerance_nm: float = 5e-4) -> float:
    candidates = [(abs(w - target_nm), value) for w, value in zip(wavelengths, values)]
    distance, value = min(candidates, key=lambda pair: pair[0])
    if distance > tolerance_nm:
        raise LunarPrecisionError(f'output grid missing {target_nm} nm within tolerance')
    return value


def evaluate_results(result_root: Path, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    precision = contract['precisionEvaluation']
    wavelengths_to_check = [float(precision['primaryWavelengthNm'])] + [float(x) for x in precision['secondaryWavelengthNm']]
    per_case: dict[str, Any] = {}
    for case in frozen_cases(contract):
        case_dir = result_root / case['caseId']
        rad_path = case_dir / 'mc.rad.spc'
        std_path = case_dir / 'mc.rad.std.spc'
        if not rad_path.is_file() or not std_path.is_file():
            raise LunarPrecisionError(f'missing MYSTIC output for {case["caseId"]}')
        rw, rv = _read_spectral_last_column(rad_path)
        sw, sv = _read_spectral_last_column(std_path)
        values: dict[str, Any] = {}
        for wavelength in wavelengths_to_check:
            radiance = _value_at(rw, rv, wavelength)
            sigma = _value_at(sw, sv, wavelength)
            if radiance < 0 or sigma < 0:
                raise LunarPrecisionError(f'negative radiance/std for {case["caseId"]} at {wavelength}')
            relative_std = None if radiance <= 0 else sigma / radiance
            values[f'{int(wavelength)}nm'] = {
                'radiance': radiance,
                'mcStd': sigma,
                'relativeMcStd': relative_std,
            }
        per_case[case['caseId']] = {**case, 'wavelengths': values}

    failures: list[str] = []
    primary = int(float(precision['primaryWavelengthNm']))
    secondary = [int(float(x)) for x in precision['secondaryWavelengthNm']]
    for case_id, item in per_case.items():
        p = item['wavelengths'][f'{primary}nm']
        if p['radiance'] <= 0:
            failures.append(f'PRIMARY_NONPOSITIVE:{case_id}')
        elif p['relativeMcStd'] is None or p['relativeMcStd'] > float(precision['primaryPerReplicateRelativeMcStdMax']):
            failures.append(f'PRIMARY_RELATIVE_STD:{case_id}')
        for wavelength in secondary:
            row = item['wavelengths'][f'{wavelength}nm']
            if row['radiance'] <= 0:
                failures.append(f'SECONDARY_NONPOSITIVE:{case_id}:{wavelength}')
            elif row['relativeMcStd'] is None or row['relativeMcStd'] > float(precision['secondaryPerReplicateRelativeMcStdMax']):
                failures.append(f'SECONDARY_RELATIVE_STD:{case_id}:{wavelength}')

    replicate_checks: list[dict[str, Any]] = []
    by_geometry: dict[str, list[dict[str, Any]]] = {}
    for item in per_case.values():
        by_geometry.setdefault(item['geometryId'], []).append(item)
    for geometry_id, items in sorted(by_geometry.items()):
        items.sort(key=lambda row: row['replicate'])
        if len(items) != 2:
            raise LunarPrecisionError(f'expected two replicates for {geometry_id}')
        for wavelength in [primary, *secondary]:
            a = items[0]['wavelengths'][f'{wavelength}nm']
            b = items[1]['wavelengths'][f'{wavelength}nm']
            denom = math.hypot(a['mcStd'], b['mcStd'])
            if denom == 0:
                z = 0.0 if a['radiance'] == b['radiance'] else math.inf
            else:
                z = abs(a['radiance'] - b['radiance']) / denom
            passed = math.isfinite(z) and z <= float(precision['replicateConsistencyZMax'])
            replicate_checks.append({
                'geometryId': geometry_id,
                'wavelengthNm': wavelength,
                'replicateConsistencyZ': z,
                'passed': passed,
            })
            if not passed:
                failures.append(f'REPLICATE_Z:{geometry_id}:{wavelength}')

    report = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': 'PASS_COMPUTATIONAL_PRECISION' if not failures else 'FAIL_COMPUTATIONAL_PRECISION',
        'computationallyEligibleForFrozenSyntheticGrid': not failures,
        'failures': failures,
        'cases': per_case,
        'replicateChecks': replicate_checks,
        'toaSourceIndependentlyValidatedByThisResult': False,
        'atmosphericScatteredMoonlightEmpiricallyValidatedByThisResult': False,
        'finiteMoonDiskModeled': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
    }
    return report


def _parse_runtime_identity(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    return {
        'uvspecSha256': data.get('uvspecSha256'),
        'libRadtranDataTreeSha256': data.get('libRadtranDataTreeSha256'),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Prepare or evaluate the frozen lunar MYSTIC computational precision stage. This tool does not execute uvspec.')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--evaluate-results', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--atmosphere-file', type=Path)
    parser.add_argument('--atlas-file', type=Path)
    parser.add_argument('--runtime-report', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    if args.prepare == args.evaluate_results:
        raise LunarPrecisionError('choose exactly one of --prepare or --evaluate-results')
    if args.prepare:
        required = (args.data_dir, args.atmosphere_file, args.atlas_file, args.runtime_report)
        if any(value is None for value in required):
            raise LunarPrecisionError('--prepare requires data-dir, atmosphere-file, atlas-file, and runtime-report')
        manifest = prepare_inputs(
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            atlas_path=args.atlas_file,
            output_root=args.output_root,
            runtime_identity=_parse_runtime_identity(args.runtime_report),
        )
        print(json.dumps({'status': manifest['status'], 'caseCount': manifest['caseCount']}, sort_keys=True))
        return 0
    report = evaluate_results(args.output_root)
    report_path = args.output_root / 'computational-precision-report.json'
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'failureCount': len(report['failures'])}, sort_keys=True))
    return 0 if report['computationallyEligibleForFrozenSyntheticGrid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
