#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / 'lunar-mystic-secondary-aod550-anchor-precision-recovery-v1.json'
PARENT_RUNTIME = HERE / 'lunar_mystic_computational_precision_runtime.py'
LUNAR_INPUT = HERE / 'lunar_mystic_input.py'
COMPATIBILITY = HERE / 'lunar_mystic_secondary_aod550_anchor_compatibility.py'


class LunarAnchorPrecisionRecoveryError(RuntimeError):
    pass


def _load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarAnchorPrecisionRecoveryError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('contractId') != 'lunar-mystic-secondary-aod550-anchor-precision-recovery-v1':
        raise LunarAnchorPrecisionRecoveryError('contract identity drift')
    if data.get('status') != 'FROZEN_REVIEW_ONLY_NO_SOLVER_EXECUTION':
        raise LunarAnchorPrecisionRecoveryError('contract status drift')
    prereq = data.get('prerequisiteEvidence') or {}
    if prereq.get('compatibilityRunId') != 33296667726 or prereq.get('compatibilityRunAttempt') != 1:
        raise LunarAnchorPrecisionRecoveryError('compatibility run identity drift')
    if prereq.get('compatibilityArtifactId') != 9727625601:
        raise LunarAnchorPrecisionRecoveryError('compatibility artifact identity drift')
    if prereq.get('compatibilityArtifactDigest') != 'sha256:64862bc2235c8f98acc4f25c0171f100fb516c376de4e1bcfe0ed8ae33bde851':
        raise LunarAnchorPrecisionRecoveryError('compatibility artifact digest drift')
    if prereq.get('compatibilityStatus') != 'PASS_TRANSPORT_COMPATIBILITY_ONLY':
        raise LunarAnchorPrecisionRecoveryError('compatibility prerequisite not passed')
    if prereq.get('immutableParentStatus') != 'FAIL_COMPUTATIONAL_PRECISION':
        raise LunarAnchorPrecisionRecoveryError('parent immutable classification drift')
    if prereq.get('failedMonochromaticExec001Status') != 'EXECUTION_INCOMPLETE':
        raise LunarAnchorPrecisionRecoveryError('exec001 immutable classification drift')
    numerical = data.get('numericalDesign') or {}
    if numerical.get('targetWavelengthNm') != [450.0, 650.0, 750.0]:
        raise LunarAnchorPrecisionRecoveryError('target wavelength drift')
    if numerical.get('technicalAnchorWavelengthNm') != 550.0:
        raise LunarAnchorPrecisionRecoveryError('technical anchor drift')
    if numerical.get('spectralMode') != 'TARGET_PLUS_550_SPARSE_GRID_NO_MC_SPECTRAL_IS':
        raise LunarAnchorPrecisionRecoveryError('spectral mode drift')
    if numerical.get('mcPhotonsDirectivePerInput') != 5_000_000:
        raise LunarAnchorPrecisionRecoveryError('photon directive drift')
    seeds = numerical.get('freshIndependentSeeds')
    if not isinstance(seeds, list) or seeds != list(range(28764001, 28764037)):
        raise LunarAnchorPrecisionRecoveryError('fresh seed list drift')
    protected = data.get('protectedBoundaries') or {}
    for key, value in protected.items():
        if value is not False:
            raise LunarAnchorPrecisionRecoveryError(f'protected boundary drift: {key}')
    opening = data.get('executionOpeningGate') or {}
    if opening.get('solverExecutionAuthorizedByThisFile') is not False or opening.get('resultOpeningAuthorizedByThisFile') is not False:
        raise LunarAnchorPrecisionRecoveryError('review contract may not authorize solver/result opening')
    return data


def frozen_cases(contract: dict[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    contract = contract or load_contract()
    p = contract['frozenPhysicalState']
    n = contract['numericalDesign']
    seeds = [int(x) for x in n['freshIndependentSeeds']]
    cases = []
    index = 0
    for wavelength in [float(x) for x in n['targetWavelengthNm']]:
        for elevation in [float(x) for x in p['observerElevationM']]:
            for azimuth in [float(x) for x in p['targetRelativeAzimuthToMoonDeg']]:
                geometry_id = f'e{int(elevation):04d}-az{int(azimuth):03d}'
                for replicate in range(1, int(n['replicatesPerGeometryPerTarget']) + 1):
                    cases.append({
                        'caseId': f'w{int(wavelength):03d}-{geometry_id}-r{replicate}',
                        'geometryId': geometry_id,
                        'targetWavelengthNm': wavelength,
                        'anchorWavelengthNm': float(n['technicalAnchorWavelengthNm']),
                        'replicate': replicate,
                        'moonZenithDeg': float(p['moonZenithDeg']),
                        'targetAltitudeDeg': float(p['targetAltitudeDeg']),
                        'targetRelativeAzimuthToMoonDeg': azimuth,
                        'observerElevationM': elevation,
                        'aod550': float(p['aod550']),
                        'albedo': float(p['lambertianAlbedo']),
                        'photonHistories': int(n['mcPhotonsDirectivePerInput']),
                        'randomSeed': seeds[index],
                    })
                    index += 1
    if len(cases) != 36 or index != 36:
        raise LunarAnchorPrecisionRecoveryError('frozen case grid drift')
    return tuple(cases)


def _runtime_identity(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    return {
        'uvspecSha256': data.get('uvspecSha256'),
        'libRadtranDataTreeSha256': data.get('libRadtranDataTreeSha256'),
    }


def prepare_inputs(*, data_dir: Path, atmosphere_file: Path, atlas_path: Path, runtime_report: Path, output_root: Path) -> dict[str, Any]:
    contract = load_contract()
    parent_runtime = _load_registered('lunar_anchor_recovery_parent_runtime', PARENT_RUNTIME)
    lunar_input = _load_registered('lunar_anchor_recovery_input', LUNAR_INPUT)
    compatibility = _load_registered('lunar_anchor_recovery_compatibility', COMPATIBILITY)
    output_root.mkdir(parents=True, exist_ok=True)
    full_source = output_root / 'frozen-lunar-source-380-780nm.dat'
    source_meta = parent_runtime.build_lunar_source_from_runtime_atlas(atlas_path, full_source)
    identity = _runtime_identity(runtime_report)
    required = contract['sourceAndRuntime']
    if identity['uvspecSha256'] != required['uvspecSha256']:
        raise LunarAnchorPrecisionRecoveryError('uvspec runtime hash drift')
    if identity['libRadtranDataTreeSha256'] != required['libRadtranDataTreeSha256']:
        raise LunarAnchorPrecisionRecoveryError('libRadtran data tree hash drift')
    prepared = []
    for case in frozen_cases(contract):
        case_dir = output_root / case['caseId']
        case_dir.mkdir(parents=True, exist_ok=True)
        sparse_source = case_dir / 'lunar-source-target-plus-550.dat'
        sparse_meta = compatibility.write_sparse_anchor_source(
            full_source,
            case['targetWavelengthNm'],
            sparse_source,
            case['anchorWavelengthNm'],
        )
        base, base_meta = lunar_input.render_lunar_mystic_input(
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            lunar_source_file=sparse_source,
            moon_zenith_deg=case['moonZenithDeg'],
            target_altitude_deg=case['targetAltitudeDeg'],
            target_relative_azimuth_to_moon_deg=case['targetRelativeAzimuthToMoonDeg'],
            observer_elevation_m=case['observerElevationM'],
            aod550=case['aod550'],
            albedo=case['albedo'],
            photon_histories=case['photonHistories'],
            random_seed=case['randomSeed'],
            case_dir=case_dir,
            runtime_identity=identity,
            alis_importance_nm=case['anchorWavelengthNm'],
        )
        rendered = compatibility.convert_reviewed_input_to_anchor_grid(
            base,
            case['targetWavelengthNm'],
            case['anchorWavelengthNm'],
        )
        input_path = case_dir / 'case.inp'
        input_path.write_text(rendered, encoding='utf-8')
        item = {
            **case,
            'inputPath': str(input_path),
            'sparseSourcePath': str(sparse_source),
            'sparseSourceMetadata': sparse_meta,
            'baseRenderMetadata': base_meta,
        }
        (case_dir / 'prepared.json').write_text(json.dumps(item, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        prepared.append(item)
    manifest = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': 'PREPARED_NO_SOLVER_EXECUTION',
        'fullFrozenSource': source_meta,
        'caseCount': len(prepared),
        'cases': prepared,
        'scientificSolverExecuted': False,
        'resultsOpened': False,
        'parentResultReclassified': False,
        'failedExec001Reclassified': False,
        'compatibilityProbeUsedAsPrecisionEvidence': False,
        'empiricalValidationClaim': False,
        'productionAuthorized': False,
    }
    (output_root / 'prepared-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def _read_wavelength_value(path: Path, wavelength_nm: float) -> float:
    matches = []
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
            raise LunarAnchorPrecisionRecoveryError(f'nonfinite output row in {path}')
        if abs(wavelength - wavelength_nm) <= 5e-4:
            matches.append(value)
    if len(matches) != 1:
        raise LunarAnchorPrecisionRecoveryError(f'expected exactly one {wavelength_nm} nm row in {path}, found {len(matches)}')
    return matches[0]


def evaluate_results(result_root: Path) -> dict[str, Any]:
    contract = load_contract()
    precision = contract['precisionEvaluation']
    max_rel = float(precision['perReplicateTargetRelativeMcStdMax'])
    max_z = float(precision['replicateConsistencyZMax'])
    case_rows: dict[str, dict[str, Any]] = {}
    execution_failures = []
    precision_failures = []

    for case in frozen_cases(contract):
        case_dir = result_root / case['caseId']
        exit_path = case_dir / 'uvspec.exitcode'
        if not exit_path.is_file():
            execution_failures.append(f'MISSING_EXITCODE:{case["caseId"]}')
            continue
        exit_code = int(exit_path.read_text(encoding='utf-8').strip())
        if exit_code != 0:
            execution_failures.append(f'NONZERO_UVSPEC_EXIT:{case["caseId"]}:{exit_code}')
            continue
        rad_path = case_dir / 'mc.rad.spc'
        std_path = case_dir / 'mc.rad.std.spc'
        if not rad_path.is_file() or not std_path.is_file():
            execution_failures.append(f'MISSING_MYSTIC_OUTPUT:{case["caseId"]}')
            continue
        try:
            target_rad = _read_wavelength_value(rad_path, case['targetWavelengthNm'])
            target_std = _read_wavelength_value(std_path, case['targetWavelengthNm'])
            anchor_rad = _read_wavelength_value(rad_path, case['anchorWavelengthNm'])
            anchor_std = _read_wavelength_value(std_path, case['anchorWavelengthNm'])
        except LunarAnchorPrecisionRecoveryError as exc:
            execution_failures.append(f'OUTPUT_PARSE:{case["caseId"]}:{exc}')
            continue
        relative = target_std / target_rad if target_rad > 0 else None
        row = {
            **case,
            'exitCode': exit_code,
            'targetRadiance': target_rad,
            'targetMcStd': target_std,
            'targetRelativeMcStd': relative,
            'anchor550RadianceDiagnosticOnly': anchor_rad,
            'anchor550McStdDiagnosticOnly': anchor_std,
        }
        case_rows[case['caseId']] = row
        if target_rad <= 0 or not math.isfinite(target_rad):
            precision_failures.append(f'NONPOSITIVE_TARGET_RADIANCE:{case["caseId"]}')
        if target_std <= 0 or not math.isfinite(target_std):
            precision_failures.append(f'NONPOSITIVE_TARGET_MCSTD:{case["caseId"]}')
        if relative is None or not math.isfinite(relative) or relative > max_rel:
            precision_failures.append(f'TARGET_RELATIVE_MCSTD:{case["caseId"]}')

    replicate_checks = []
    if not execution_failures:
        grouped: dict[tuple[float, str], list[dict[str, Any]]] = {}
        for row in case_rows.values():
            grouped.setdefault((row['targetWavelengthNm'], row['geometryId']), []).append(row)
        for (wavelength, geometry_id), items in sorted(grouped.items()):
            items.sort(key=lambda x: x['replicate'])
            if len(items) != 2:
                execution_failures.append(f'REPLICATE_CARDINALITY:{int(wavelength)}:{geometry_id}')
                continue
            a, b = items
            denom = math.hypot(a['targetMcStd'], b['targetMcStd'])
            z = math.inf if denom <= 0 else abs(a['targetRadiance'] - b['targetRadiance']) / denom
            passed = math.isfinite(z) and z <= max_z
            replicate_checks.append({
                'targetWavelengthNm': wavelength,
                'geometryId': geometry_id,
                'replicateConsistencyZ': z,
                'passed': passed,
            })
            if not passed:
                precision_failures.append(f'TARGET_REPLICATE_Z:{int(wavelength)}:{geometry_id}')

    execution_complete = not execution_failures and len(case_rows) == 36 and len(replicate_checks) == 18
    precision_supported = execution_complete and not precision_failures
    if not execution_complete:
        status = 'EXECUTION_INCOMPLETE'
        combined = 'COMPUTATIONAL_PRECISION_NOT_YET_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'
    elif precision_supported:
        status = 'PASS_SECONDARY_PRECISION_RECOVERY'
        combined = 'COMPUTATIONAL_PRECISION_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'
    else:
        status = 'FAIL_SECONDARY_PRECISION'
        combined = 'COMPUTATIONAL_PRECISION_NOT_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'

    report = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': status,
        'executionComplete': execution_complete,
        'secondaryPrecisionSupported': precision_supported,
        'combinedParentRecoveryClassification': combined,
        'parentV1StatusRemains': 'FAIL_COMPUTATIONAL_PRECISION',
        'failedExec001StatusRemains': 'EXECUTION_INCOMPLETE',
        'executionFailures': execution_failures,
        'precisionFailures': precision_failures if execution_complete else [],
        'caseCountParsed': len(case_rows),
        'cases': list(case_rows.values()),
        'replicateChecks': replicate_checks,
        'technicalAnchorExcludedFromPrecisionAcceptance': True,
        'compatibilityProbeUsedAsPrecisionEvidence': False,
        'toaSourceValidated': False,
        'atmosphericScatteredMoonlightEmpiricallyValidated': False,
        'finiteMoonDiskValidated': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
    }
    (result_root / 'precision-recovery-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--evaluate', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--atmosphere-file', type=Path)
    parser.add_argument('--atlas-file', type=Path)
    parser.add_argument('--runtime-report', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    if args.prepare == args.evaluate:
        parser.error('choose exactly one of --prepare or --evaluate')
    if args.prepare:
        for name in ('data_dir', 'atmosphere_file', 'atlas_file', 'runtime_report'):
            if getattr(args, name) is None:
                parser.error(f'--{name.replace("_", "-")} required with --prepare')
        prepare_inputs(
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            atlas_path=args.atlas_file,
            runtime_report=args.runtime_report,
            output_root=args.output_root,
        )
        return 0
    report = evaluate_results(args.output_root)
    if report['status'] == 'PASS_SECONDARY_PRECISION_RECOVERY':
        return 0
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
