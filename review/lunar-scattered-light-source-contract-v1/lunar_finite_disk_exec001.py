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
AUTH_PATH = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001-authorization.json'
PLANNER_PATH = HERE / 'lunar_finite_disk_transfer_kernel_sensitivity.py'
SEED_LEDGER_PATH = HERE / 'lunar_finite_disk_seed_ledger.py'
LUNAR_INPUT_PATH = HERE / 'lunar_mystic_input.py'
SOURCE_RUNTIME_PATH = HERE / 'lunar_mystic_computational_precision_runtime.py'


class LunarFiniteDiskExec001Error(RuntimeError):
    pass


def _load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarFiniteDiskExec001Error(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_authorization() -> dict[str, Any]:
    a = json.loads(AUTH_PATH.read_text(encoding='utf-8'))
    if a.get('authorizationId') != 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001-authorization':
        raise LunarFiniteDiskExec001Error('authorization identity drift')
    if a.get('executionId') != 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001':
        raise LunarFiniteDiskExec001Error('execution identity drift')
    if a.get('status') != 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_NOT_DISPATCHED':
        raise LunarFiniteDiskExec001Error('execution authorization status drift')
    source = a.get('sourceReview') or {}
    if source.get('finiteDiskContractGitBlobSha1') != 'e235dcac8f3c307764d207b9111e9ab2011acb82':
        raise LunarFiniteDiskExec001Error('finite-disk contract binding drift')
    if source.get('authorizationRecheckHead') != '885c978b4349a0967056856724f5f8ea87bf5141':
        raise LunarFiniteDiskExec001Error('authorization recheck head drift')
    if source.get('authorizationRecheckRunId') != 33301829750 or source.get('authorizationRecheckRunAttempt') != 1:
        raise LunarFiniteDiskExec001Error('authorization recheck run identity drift')
    if source.get('authorizationRecheckArtifactId') != 9729425504:
        raise LunarFiniteDiskExec001Error('authorization recheck artifact identity drift')
    if source.get('authorizationRecheckArtifactDigest') != 'sha256:52691f5eaa6b7337d02a845f76cc5601a3ac8f0274ff02329391fd965141200a':
        raise LunarFiniteDiskExec001Error('authorization recheck artifact digest drift')
    if source.get('authorizationRecheckStatus') != 'PASS_AUTHORIZATION_TIME_REPOSITORY_GLOBAL_SEED_RECHECK_ZERO_RUNTIME':
        raise LunarFiniteDiskExec001Error('authorization recheck did not pass')
    frozen = a.get('frozenExecution') or {}
    if frozen.get('wavelengthNm') != 550.0 or frozen.get('totalDirectionalCases') != 198:
        raise LunarFiniteDiskExec001Error('frozen finite-disk grid drift')
    if frozen.get('photonHistoriesPerDirectionalCase') != 5_000_000 or frozen.get('totalPhotonHistories') != 990_000_000:
        raise LunarFiniteDiskExec001Error('frozen photon budget drift')
    if frozen.get('replacementSeedCanonicalSha256') != 'ccfb4a645fdb35f35e759338cde7e5d20992391b4d25b3d272d1b8e80c93ad7a':
        raise LunarFiniteDiskExec001Error('replacement seed canonical hash drift')
    if frozen.get('replacementSeedRowsCanonicalSha256') != 'b2c69985b098ca46c5447f025c4a774ab384135b2a641a2a439121cb45f90ce8':
        raise LunarFiniteDiskExec001Error('replacement seed rows hash drift')
    if frozen.get('retiredDisclosedSeedRangeMayExecute') is not False:
        raise LunarFiniteDiskExec001Error('retired disclosed seeds may not execute')
    result = a.get('resultContract') or {}
    if result.get('acceptanceThreshold') is not None or result.get('resultDependentPointSourceAcceptanceForbidden') is not True:
        raise LunarFiniteDiskExec001Error('result-dependent finite-disk threshold forbidden')
    if result.get('mandatorySpectralFollowOnWavelengthsNm') != [450.0, 650.0, 750.0]:
        raise LunarFiniteDiskExec001Error('mandatory spectral follow-on drift')
    auth = a.get('authorization') or {}
    if auth.get('scientificSolverExecutionAuthorized') is not True:
        raise LunarFiniteDiskExec001Error('solver execution not authorized')
    if auth.get('dispatchCreated') is not False:
        raise LunarFiniteDiskExec001Error('authorization file must precede dispatch')
    if auth.get('resultOpeningAuthorizedOnlyByFrozenEvaluator') is not True:
        raise LunarFiniteDiskExec001Error('result opening must be frozen-evaluator-only')
    if any(value is not False for value in (a.get('protectedBoundaries') or {}).values()):
        raise LunarFiniteDiskExec001Error('protected boundary drift')
    return a


def _runtime_identity(path: Path) -> dict[str, str | None]:
    r = json.loads(path.read_text(encoding='utf-8'))
    return {
        'uvspecSha256': r.get('uvspecSha256'),
        'libRadtranDataTreeSha256': r.get('libRadtranDataTreeSha256'),
    }


def authorized_cases() -> tuple[dict[str, Any], ...]:
    a = load_authorization()
    planner = _load_registered('lunar_fd_exec001_planner', PLANNER_PATH)
    seed_ledger = _load_registered('lunar_fd_exec001_seed_ledger', SEED_LEDGER_PATH)
    planned = list(planner.frozen_cases())
    ledger = seed_ledger.validate_ledger()
    rows = ledger['candidateRows']
    if ledger['candidateSeedCanonicalSha256'] != a['frozenExecution']['replacementSeedCanonicalSha256']:
        raise LunarFiniteDiskExec001Error('runtime seed universe hash mismatch')
    if ledger['candidateRowsCanonicalSha256'] != a['frozenExecution']['replacementSeedRowsCanonicalSha256']:
        raise LunarFiniteDiskExec001Error('runtime seed row hash mismatch')
    if len(planned) != 198 or len(rows) != 198:
        raise LunarFiniteDiskExec001Error('case/seed cardinality drift')
    seed_by_case = {str(row['caseId']): int(row['seed']) for row in rows}
    if len(seed_by_case) != 198:
        raise LunarFiniteDiskExec001Error('replacement seed mapping uniqueness drift')
    out: list[dict[str, Any]] = []
    for case in planned:
        case_id = str(case['caseId'])
        if case_id not in seed_by_case:
            raise LunarFiniteDiskExec001Error(f'missing replacement seed for {case_id}')
        replacement = seed_by_case[case_id]
        if 32_910_001 <= replacement <= 32_910_198:
            raise LunarFiniteDiskExec001Error('retired disclosed seed reached execution case')
        out.append({**case, 'randomSeed': replacement})
    if len({row['randomSeed'] for row in out}) != 198:
        raise LunarFiniteDiskExec001Error('authorized execution seeds not unique')
    return tuple(out)


def prepare_shard(
    *,
    data_dir: Path,
    atmosphere_file: Path,
    atlas_file: Path,
    runtime_report: Path,
    output_root: Path,
    shard_index: int,
    shard_count: int,
) -> dict[str, Any]:
    a = load_authorization()
    if shard_count <= 0 or shard_index < 0 or shard_index >= shard_count:
        raise LunarFiniteDiskExec001Error('invalid shard index/count')
    if 198 % shard_count != 0:
        raise LunarFiniteDiskExec001Error('shard count must divide the 198-case universe exactly')
    identity = _runtime_identity(runtime_report)
    frozen = a['frozenExecution']
    if identity['uvspecSha256'] != frozen['uvspecSha256']:
        raise LunarFiniteDiskExec001Error('uvspec runtime identity drift')
    if identity['libRadtranDataTreeSha256'] != frozen['libRadtranDataTreeSha256']:
        raise LunarFiniteDiskExec001Error('libRadtran data-tree identity drift')

    source_runtime = _load_registered('lunar_fd_exec001_source_runtime', SOURCE_RUNTIME_PATH)
    lunar_input = _load_registered('lunar_fd_exec001_lunar_input', LUNAR_INPUT_PATH)
    output_root.mkdir(parents=True, exist_ok=True)
    source_file = output_root / 'frozen-lunar-source-380-780nm.dat'
    source_meta = source_runtime.build_lunar_source_from_runtime_atlas(atlas_file, source_file)

    all_cases = authorized_cases()
    selected = [case for index, case in enumerate(all_cases) if index % shard_count == shard_index]
    expected_per_shard = 198 // shard_count
    if len(selected) != expected_per_shard:
        raise LunarFiniteDiskExec001Error('unexpected shard cardinality')

    manifest_rows = []
    for case in selected:
        case_dir = output_root / case['caseId']
        case_dir.mkdir(parents=True, exist_ok=True)
        rendered, meta = lunar_input.render_lunar_mystic_input(
            data_dir=data_dir,
            atmosphere_file=atmosphere_file,
            lunar_source_file=source_file,
            moon_zenith_deg=case['sourceZenithDeg'],
            target_altitude_deg=case['targetAltitudeDeg'],
            target_relative_azimuth_to_moon_deg=case['targetRelativeAzimuthToSampleSourceDeg'],
            observer_elevation_m=case['observerElevationM'],
            aod550=frozen['aod550'],
            albedo=frozen['lambertianAlbedo'],
            photon_histories=case['photonHistories'],
            random_seed=case['randomSeed'],
            case_dir=case_dir,
            runtime_identity=identity,
            alis_importance_nm=frozen['wavelengthNm'],
        )
        if meta.get('finiteMoonDiskModeled') is not False:
            raise LunarFiniteDiskExec001Error('directional sensitivity input mislabeled as finite-disk solution')
        if meta.get('atmosphericScatteredMoonlightValidated') is not False:
            raise LunarFiniteDiskExec001Error('input renderer empirical-validation boundary drift')
        if meta.get('productionAuthorized') is not False:
            raise LunarFiniteDiskExec001Error('input renderer production boundary drift')
        input_path = case_dir / 'case.inp'
        input_path.write_text(rendered, encoding='utf-8')
        # Do not serialize seed literals into the manifest or upload them as
        # review evidence. They exist only in the local execution input.
        manifest_rows.append({
            'caseId': case['caseId'],
            'inputPath': str(input_path),
            'geometryKey': case['geometryKey'],
            'sampleId': case['sampleId'],
            'shardIndex': shard_index,
        })

    manifest = {
        'schemaVersion': 1,
        'executionId': a['executionId'],
        'status': 'PREPARED_AUTHORIZED_SHARD_NO_RESULT_OPENED',
        'shardIndex': shard_index,
        'shardCount': shard_count,
        'caseCount': len(manifest_rows),
        'caseIds': [row['caseId'] for row in manifest_rows],
        'cases': manifest_rows,
        'sourceMetadata': source_meta,
        'replacementSeedCanonicalSha256': frozen['replacementSeedCanonicalSha256'],
        'replacementSeedRowsCanonicalSha256': frozen['replacementSeedRowsCanonicalSha256'],
        'seedLiteralsSerializedInManifest': False,
        'solverExecuted': False,
        'resultOpened': False,
        'finiteDiskAdequacyClaimed': False,
        'productionAuthorized': False,
    }
    (output_root / 'prepared-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


def _read_wavelength_value(path: Path, wavelength_nm: float) -> float:
    matches: list[float] = []
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
            raise LunarFiniteDiskExec001Error(f'nonfinite output row in {path}')
        if abs(wavelength - wavelength_nm) <= 5e-4:
            matches.append(value)
    if len(matches) != 1:
        raise LunarFiniteDiskExec001Error(f'expected exactly one {wavelength_nm} nm row in {path}, found {len(matches)}')
    return matches[0]


def evaluate_result_root(*, result_root: Path, output_path: Path) -> dict[str, Any]:
    a = load_authorization()
    planner = _load_registered('lunar_fd_exec001_frozen_evaluator', PLANNER_PATH)
    cases = authorized_cases()
    records: list[dict[str, Any]] = []
    parser_failures: list[str] = []
    for case in cases:
        case_dir = result_root / case['caseId']
        exit_path = case_dir / 'uvspec.exitcode'
        if not exit_path.is_file():
            parser_failures.append(f'MISSING_EXITCODE:{case["caseId"]}')
            continue
        try:
            exit_code = int(exit_path.read_text(encoding='utf-8').strip())
        except Exception:
            parser_failures.append(f'INVALID_EXITCODE:{case["caseId"]}')
            continue
        if exit_code != 0:
            records.append({'caseId': case['caseId'], 'solverExitCode': exit_code, 'radiance': None, 'stdRadiance': None})
            continue
        rad_path = case_dir / 'mc.rad.spc'
        std_path = case_dir / 'mc.rad.std.spc'
        if not rad_path.is_file() or not std_path.is_file():
            parser_failures.append(f'MISSING_MYSTIC_OUTPUT:{case["caseId"]}')
            continue
        try:
            radiance = _read_wavelength_value(rad_path, a['frozenExecution']['wavelengthNm'])
            std = _read_wavelength_value(std_path, a['frozenExecution']['wavelengthNm'])
        except LunarFiniteDiskExec001Error as exc:
            parser_failures.append(f'OUTPUT_PARSE:{case["caseId"]}:{exc}')
            continue
        records.append({
            'caseId': case['caseId'],
            'solverExitCode': exit_code,
            'radiance': radiance,
            'stdRadiance': std,
        })

    if parser_failures:
        report = {
            'schemaVersion': 1,
            'contractId': 'lunar-finite-disk-transfer-kernel-sensitivity-v1',
            'classification': 'EXECUTION_INCOMPLETE',
            'executionComplete': False,
            'caseCountExpected': 198,
            'caseCountObserved': len(records),
            'reasons': parser_failures,
            'acceptanceThresholdApplied': False,
            'finiteMoonDiskValidated': False,
            'continuousDiskBoundProven': False,
            'physicalResolvedDiskIntegrationImplemented': False,
            'empiricalAtmosphericMoonlightValidated': False,
            'toaSourceValidated': False,
            'totalSkyValidated': False,
            'productionAuthorized': False,
        }
    else:
        report = planner.evaluate_records(records)

    report['executionId'] = a['executionId']
    report['authorizationHead'] = '72916c8c98cba2454c73e09b30915be3af609a07'
    report['authorizationReviewRunId'] = 33302850769
    report['authorizationReviewArtifactId'] = 9729497306
    report['authorizationReviewArtifactDigest'] = 'sha256:cf34132a74873e56bef0f66e47a6d6d662e7579d47a11e12ffdc81545d75f3ee'
    report['replacementSeedCanonicalSha256'] = a['frozenExecution']['replacementSeedCanonicalSha256']
    report['replacementSeedRowsCanonicalSha256'] = a['frozenExecution']['replacementSeedRowsCanonicalSha256']
    report['seedLiteralsIncludedInReport'] = False
    report['resultDependentThresholdApplied'] = False
    report['mandatorySpectralFollowOnRequiredBeforeBroadbandFiniteDiskClaim'] = True
    report['mandatorySpectralFollowOnWavelengthsNm'] = [450.0, 650.0, 750.0]
    report['taylorOrJerusalemUsed'] = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)

    validate = sub.add_parser('validate')
    validate.add_argument('--json', action='store_true')

    prepare = sub.add_parser('prepare-shard')
    prepare.add_argument('--data-dir', type=Path, required=True)
    prepare.add_argument('--atmosphere-file', type=Path, required=True)
    prepare.add_argument('--atlas-file', type=Path, required=True)
    prepare.add_argument('--runtime-report', type=Path, required=True)
    prepare.add_argument('--output-root', type=Path, required=True)
    prepare.add_argument('--shard-index', type=int, required=True)
    prepare.add_argument('--shard-count', type=int, required=True)

    evaluate = sub.add_parser('evaluate')
    evaluate.add_argument('--result-root', type=Path, required=True)
    evaluate.add_argument('--output', type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == 'validate':
        a = load_authorization()
        cases = authorized_cases()
        summary = {
            'status': 'PASS_EXEC001_AUTHORIZED_CASE_MAP_NO_SOLVER_NO_RESULT',
            'executionId': a['executionId'],
            'caseCount': len(cases),
            'replacementSeedCanonicalSha256': a['frozenExecution']['replacementSeedCanonicalSha256'],
            'replacementSeedRowsCanonicalSha256': a['frozenExecution']['replacementSeedRowsCanonicalSha256'],
            'seedLiteralsPrinted': False,
            'solverExecuted': False,
            'resultOpened': False,
        }
        print(json.dumps(summary, sort_keys=True) if args.json else summary['status'])
        return 0
    if args.command == 'prepare-shard':
        manifest = prepare_shard(
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            atlas_file=args.atlas_file,
            runtime_report=args.runtime_report,
            output_root=args.output_root,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
        print(json.dumps({
            'status': manifest['status'],
            'shardIndex': manifest['shardIndex'],
            'caseCount': manifest['caseCount'],
            'seedLiteralsSerializedInManifest': False,
        }, sort_keys=True))
        return 0
    if args.command == 'evaluate':
        report = evaluate_result_root(result_root=args.result_root, output_path=args.output)
        print(json.dumps({
            'classification': report.get('classification'),
            'executionComplete': report.get('executionComplete'),
            'caseCountObserved': report.get('caseCountObserved'),
            'finiteMoonDiskValidated': report.get('finiteMoonDiskValidated'),
            'productionAuthorized': report.get('productionAuthorized'),
        }, sort_keys=True))
        return 0 if report.get('executionComplete') is True else 2
    raise AssertionError('unreachable')


if __name__ == '__main__':
    raise SystemExit(main())
