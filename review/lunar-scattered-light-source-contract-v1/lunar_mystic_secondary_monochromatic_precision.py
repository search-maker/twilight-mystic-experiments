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
CONTRACT = HERE / 'lunar-mystic-secondary-monochromatic-precision-v1.json'
PARENT_RUNTIME = HERE / 'lunar_mystic_computational_precision_runtime.py'
LUNAR_INPUT = HERE / 'lunar_mystic_input.py'


class LunarSecondaryPrecisionError(RuntimeError):
    pass


def _load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarSecondaryPrecisionError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('contractId') != 'lunar-mystic-secondary-monochromatic-precision-v1':
        raise LunarSecondaryPrecisionError('contract identity drift')
    if data.get('status') != 'FROZEN_REVIEW_ONLY_NO_SOLVER_EXECUTION':
        raise LunarSecondaryPrecisionError('contract status drift')
    trigger = data.get('triggerEvidence') or {}
    if trigger.get('executionRunId') != 33295634887 or trigger.get('executionRunAttempt') != 1:
        raise LunarSecondaryPrecisionError('parent execution identity drift')
    if trigger.get('resultArtifactId') != 9727358391:
        raise LunarSecondaryPrecisionError('parent artifact identity drift')
    if trigger.get('resultArtifactDigest') != 'sha256:9f284f23a40cd57027a5ede36eb2adaf5cca1d0d0d3fb4b2027bf3e3cab1cec8':
        raise LunarSecondaryPrecisionError('parent artifact digest drift')
    if trigger.get('parentStatus') != 'FAIL_COMPUTATIONAL_PRECISION' or trigger.get('failureCount') != 18:
        raise LunarSecondaryPrecisionError('parent failure classification drift')
    if trigger.get('parent550NmAllSixReplicateChecksPassed') is not True:
        raise LunarSecondaryPrecisionError('parent 550-nm precision prerequisite drift')
    numerical = data.get('numericalDesign') or {}
    if numerical.get('spectralMode') != 'MONOCHROMATIC_NO_MC_SPECTRAL_IS':
        raise LunarSecondaryPrecisionError('spectral mode drift')
    if numerical.get('photonHistoriesPerReplicate') != 5_000_000:
        raise LunarSecondaryPrecisionError('photon budget drift')
    seeds = numerical.get('freshIndependentSeeds')
    if not isinstance(seeds, list) or len(seeds) != 36 or len(set(seeds)) != 36:
        raise LunarSecondaryPrecisionError('fresh seed cardinality drift')
    parent_seeds = set(numerical.get('parentSeedsConsumedAndForbidden') or [])
    if parent_seeds.intersection(seeds):
        raise LunarSecondaryPrecisionError('parent seed reuse detected')
    protected = data.get('protectedBoundaries') or {}
    for key in (
        'taylorResidualUsed', 'jerusalemResidualUsed', 'xshooterResidualOpened',
        'airLusiResidualOpened', 'parameterFitOrTuningAllowed',
        'empiricalAtmosphericValidationClaimAllowed', 'toaValidationClaimAllowed',
        'finiteDiskValidationClaimAllowed', 'totalSkyValidationClaimAllowed',
        'productionAuthorized',
    ):
        if protected.get(key) is not False:
            raise LunarSecondaryPrecisionError(f'protected boundary drift: {key}')
    opening = data.get('executionOpeningGate') or {}
    if opening.get('solverExecutionAuthorizedByThisFile') is not False:
        raise LunarSecondaryPrecisionError('review file may not authorize solver')
    if opening.get('resultOpeningAuthorizedByThisFile') is not False:
        raise LunarSecondaryPrecisionError('review file may not authorize result opening')
    return data


def frozen_cases(contract: dict[str, Any] | None = None) -> tuple[dict[str, Any], ...]:
    contract = contract or load_contract()
    physical = contract['frozenPhysicalState']
    numerical = contract['numericalDesign']
    wavelengths = [float(x) for x in numerical['wavelengthNm']]
    elevations = [float(x) for x in physical['observerElevationM']]
    azimuths = [float(x) for x in physical['targetRelativeAzimuthToMoonDeg']]
    replicates = int(numerical['replicatesPerGeometryPerWavelength'])
    seeds = [int(x) for x in numerical['freshIndependentSeeds']]
    expected = len(wavelengths) * len(elevations) * len(azimuths) * replicates
    if wavelengths != [450.0, 650.0, 750.0] or expected != 36 or len(seeds) != expected:
        raise LunarSecondaryPrecisionError('frozen case grid drift')
    cases: list[dict[str, Any]] = []
    i = 0
    for wavelength in wavelengths:
        for elevation in elevations:
            for azimuth in azimuths:
                geometry_id = f'e{int(elevation):04d}-az{int(azimuth):03d}'
                for replicate in range(1, replicates + 1):
                    case_id = f'w{int(wavelength):03d}-{geometry_id}-r{replicate}'
                    cases.append({
                        'caseId': case_id,
                        'geometryId': geometry_id,
                        'wavelengthNm': wavelength,
                        'replicate': replicate,
                        'moonZenithDeg': float(physical['moonZenithDeg']),
                        'targetAltitudeDeg': float(physical['targetAltitudeDeg']),
                        'targetRelativeAzimuthToMoonDeg': azimuth,
                        'observerElevationM': elevation,
                        'aod550': float(physical['aod550']),
                        'albedo': float(physical['lambertianAlbedo']),
                        'photonHistories': int(numerical['photonHistoriesPerReplicate']),
                        'randomSeed': seeds[i],
                    })
                    i += 1
    return tuple(cases)


def _render_monochromatic_input(*, lunar_input: Any, wavelength_nm: float, **kwargs: Any) -> tuple[str, dict[str, Any]]:
    # Start from the already-reviewed lunar source/geometry/elevated-site renderer
    # and alter only the spectral execution mode. Passing wavelength as the ALIS
    # importance wavelength makes the expected line deterministic before removal.
    text, metadata = lunar_input.render_lunar_mystic_input(
        **kwargs,
        alis_importance_nm=wavelength_nm,
    )
    spectral_line = 'wavelength 380 780'
    alis_line = f'mc_spectral_is {wavelength_nm:.1f}'
    if text.count(spectral_line) != 1 or text.count(alis_line) != 1:
        raise LunarSecondaryPrecisionError('reviewed lunar renderer spectral contract drift')
    lines = []
    for line in text.splitlines():
        if line == spectral_line:
            lines.append(f'wavelength {wavelength_nm:.1f} {wavelength_nm:.1f}')
        elif line == alis_line:
            continue
        else:
            lines.append(line)
    rendered = '\n'.join(lines) + '\n'
    if 'mc_spectral_is' in rendered:
        raise LunarSecondaryPrecisionError('ALIS spectral importance sampling remained in monochromatic input')
    if rendered.count(f'wavelength {wavelength_nm:.1f} {wavelength_nm:.1f}') != 1:
        raise LunarSecondaryPrecisionError('monochromatic wavelength directive drift')
    if rendered.count('mc_std') != 1:
        raise LunarSecondaryPrecisionError('mc_std must be emitted exactly once')
    if rendered.count('atm_z_grid ') != 1 or rendered.count('zout 0.000000') != 1:
        raise LunarSecondaryPrecisionError('elevated-site representation drift')
    if 'altitude ' in rendered:
        raise LunarSecondaryPrecisionError('legacy altitude directive emitted')
    meta = {
        **metadata,
        'spectralExecutionMode': 'MONOCHROMATIC_NO_MC_SPECTRAL_IS',
        'calculationWavelengthNm': wavelength_nm,
        'mcSpectralIsEnabled': False,
        'atmosphericScatteredMoonlightValidated': False,
        'finiteMoonDiskModeled': False,
        'productionAuthorized': False,
    }
    return rendered, meta


def _runtime_identity(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding='utf-8'))
    return {
        'uvspecSha256': data.get('uvspecSha256'),
        'libRadtranDataTreeSha256': data.get('libRadtranDataTreeSha256'),
    }


def prepare_inputs(
    *,
    data_dir: Path,
    atmosphere_file: Path,
    atlas_path: Path,
    runtime_report: Path,
    output_root: Path,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    parent_runtime = _load_registered('lunar_secondary_parent_runtime', PARENT_RUNTIME)
    lunar_input = _load_registered('lunar_secondary_input_renderer', LUNAR_INPUT)
    output_root.mkdir(parents=True, exist_ok=True)
    source_file = output_root / 'lunar-source-380-780nm.dat'
    source_meta = parent_runtime.build_lunar_source_from_runtime_atlas(atlas_path, source_file)
    identity = _runtime_identity(runtime_report)
    required_runtime = contract['sourceAndRuntime']
    if identity.get('uvspecSha256') != required_runtime['uvspecSha256']:
        raise LunarSecondaryPrecisionError('uvspec runtime hash drift')
    if identity.get('libRadtranDataTreeSha256') != required_runtime['libRadtranDataTreeSha256']:
        raise LunarSecondaryPrecisionError('libRadtran data tree hash drift')
    prepared = []
    for case in frozen_cases(contract):
        case_dir = output_root / case['caseId']
        case_dir.mkdir(parents=True, exist_ok=True)
        text, metadata = _render_monochromatic_input(
            lunar_input=lunar_input,
            wavelength_nm=case['wavelengthNm'],
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
            runtime_identity=identity,
        )
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
        'totalPhotonHistories': sum(x['photonHistories'] for x in prepared),
        'cases': prepared,
        'scientificSolverExecuted': False,
        'resultsOpened': False,
        'parentResultReclassified': False,
        'empiricalValidationClaim': False,
        'productionAuthorized': False,
    }
    (output_root / 'prepared-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def _read_single_wavelength(path: Path, target_nm: float) -> float:
    matches: list[tuple[float, float]] = []
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
            raise LunarSecondaryPrecisionError(f'nonfinite output row in {path}')
        if abs(wavelength - target_nm) <= 5e-4:
            matches.append((wavelength, value))
    if len(matches) != 1:
        raise LunarSecondaryPrecisionError(f'expected exactly one {target_nm} nm row in {path}, found {len(matches)}')
    return matches[0][1]


def evaluate_results(result_root: Path, contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    precision = contract['precisionEvaluation']
    max_rel = float(precision['perReplicateRelativeMcStdMax'])
    max_z = float(precision['replicateConsistencyZMax'])
    per_case: dict[str, Any] = {}
    failures: list[str] = []
    for case in frozen_cases(contract):
        case_dir = result_root / case['caseId']
        rad_path = case_dir / 'mc.rad.spc'
        std_path = case_dir / 'mc.rad.std.spc'
        if not rad_path.is_file() or not std_path.is_file():
            raise LunarSecondaryPrecisionError(f'missing MYSTIC output for {case["caseId"]}')
        radiance = _read_single_wavelength(rad_path, case['wavelengthNm'])
        sigma = _read_single_wavelength(std_path, case['wavelengthNm'])
        relative = sigma / radiance if radiance > 0 else None
        if not math.isfinite(radiance) or radiance <= 0:
            failures.append(f'NONPOSITIVE_OR_NONFINITE_RADIANCE:{case["caseId"]}')
        if not math.isfinite(sigma) or sigma <= 0:
            failures.append(f'NONPOSITIVE_OR_NONFINITE_MCSTD:{case["caseId"]}')
        if relative is None or not math.isfinite(relative) or relative > max_rel:
            failures.append(f'RELATIVE_MCSTD:{case["caseId"]}')
        per_case[case['caseId']] = {
            **case,
            'radiance': radiance,
            'mcStd': sigma,
            'relativeMcStd': relative,
        }

    replicate_checks: list[dict[str, Any]] = []
    grouped: dict[tuple[float, str], list[dict[str, Any]]] = {}
    for item in per_case.values():
        grouped.setdefault((item['wavelengthNm'], item['geometryId']), []).append(item)
    for (wavelength, geometry_id), items in sorted(grouped.items()):
        items.sort(key=lambda x: x['replicate'])
        if len(items) != 2:
            raise LunarSecondaryPrecisionError(f'expected two replicates for {wavelength}/{geometry_id}')
        a, b = items
        denom = math.hypot(a['mcStd'], b['mcStd'])
        z = math.inf if denom <= 0 else abs(a['radiance'] - b['radiance']) / denom
        passed = math.isfinite(z) and z <= max_z
        replicate_checks.append({
            'wavelengthNm': wavelength,
            'geometryId': geometry_id,
            'replicateConsistencyZ': z,
            'passed': passed,
        })
        if not passed:
            failures.append(f'REPLICATE_Z:{int(wavelength)}:{geometry_id}')

    passed = not failures
    report = {
        'schemaVersion': 1,
        'contractId': contract['contractId'],
        'status': 'PASS_SECONDARY_MONOCHROMATIC_PRECISION' if passed else 'FAIL_SECONDARY_MONOCHROMATIC_PRECISION',
        'computationallyEligibleForFrozenSecondaryGrid': passed,
        'combinedParentContinuationClassification': (
            'COMPUTATIONAL_PRECISION_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'
            if passed else 'COMPUTATIONAL_PRECISION_NOT_YET_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'
        ),
        'parentV1StatusRemains': 'FAIL_COMPUTATIONAL_PRECISION',
        'parentV1Reclassified': False,
        'failures': failures,
        'cases': per_case,
        'replicateChecks': replicate_checks,
        'toaSourceIndependentlyValidatedByThisResult': False,
        'atmosphericScatteredMoonlightEmpiricallyValidatedByThisResult': False,
        'finiteMoonDiskModeled': False,
        'totalSkyValidated': False,
        'taylorResidualUsed': False,
        'jerusalemResidualUsed': False,
        'productionAuthorized': False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description='Prepare or evaluate the frozen lunar secondary monochromatic precision continuation. This tool never executes uvspec.')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--evaluate-results', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--atmosphere-file', type=Path)
    parser.add_argument('--atlas-file', type=Path)
    parser.add_argument('--runtime-report', type=Path)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    if args.prepare == args.evaluate_results:
        raise LunarSecondaryPrecisionError('choose exactly one of --prepare or --evaluate-results')
    if args.prepare:
        required = (args.data_dir, args.atmosphere_file, args.atlas_file, args.runtime_report)
        if any(x is None for x in required):
            raise LunarSecondaryPrecisionError('--prepare requires data-dir, atmosphere-file, atlas-file, runtime-report')
        manifest = prepare_inputs(
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            atlas_path=args.atlas_file,
            runtime_report=args.runtime_report,
            output_root=args.output_root,
        )
        print(json.dumps({'status': manifest['status'], 'caseCount': manifest['caseCount']}, sort_keys=True))
        return 0
    report = evaluate_results(args.output_root)
    (args.output_root / 'secondary-monochromatic-precision-report.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    print(json.dumps({'status': report['status'], 'failureCount': len(report['failures'])}, sort_keys=True))
    return 0 if report['computationallyEligibleForFrozenSecondaryGrid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
