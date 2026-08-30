#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
AUTH_PATH = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002-authorization.json'
PLANNER_PATH = HERE / 'lunar_finite_disk_transfer_kernel_sensitivity.py'
LUNAR_INPUT_PATH = HERE / 'lunar_mystic_input.py'
SOURCE_RUNTIME_PATH = HERE / 'lunar_mystic_computational_precision_runtime.py'

EXPECTED_EXECUTION_ID = 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002'
EXPECTED_SEED_CANONICAL = '30350e6986b554d09bcd77e9095cb871dd634a80a4f219cca29d0fc0b8249e84'
EXPECTED_ROWS_CANONICAL = '7dbb4cbe6c34ffad668eb63ad051bd7319d68e56ea1b3c4e540d70eda23b1c95'
EXPECTED_RECHECK_ARTIFACT_ID = 9740536985
EXPECTED_AUTH_REVIEW_ARTIFACT_ID = 9741235986


class LunarFiniteDiskExec002Error(RuntimeError):
    pass


def _load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LunarFiniteDiskExec002Error(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def load_authorization() -> dict[str, Any]:
    a = json.loads(AUTH_PATH.read_text(encoding='utf-8'))
    if a.get('authorizationId') != 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec002-authorization':
        raise LunarFiniteDiskExec002Error('authorization identity drift')
    if a.get('executionId') != EXPECTED_EXECUTION_ID:
        raise LunarFiniteDiskExec002Error('execution identity drift')
    if a.get('status') != 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_NOT_DISPATCHED_PENDING_SOLVER_FREE_REVIEW':
        raise LunarFiniteDiskExec002Error('authorization status drift')

    source = a.get('sourceReview') or {}
    if source.get('finiteDiskContractGitBlobSha1') != 'e235dcac8f3c307764d207b9111e9ab2011acb82':
        raise LunarFiniteDiskExec002Error('finite-disk contract binding drift')
    if source.get('authorizationRecheckHead') != '7698d3f58756650be5ffcfd41d277dadbbba1874':
        raise LunarFiniteDiskExec002Error('authorization-time recheck head drift')
    if source.get('authorizationRecheckRunId') != 33340294645 or source.get('authorizationRecheckRunAttempt') != 1:
        raise LunarFiniteDiskExec002Error('authorization-time recheck run identity drift')
    if source.get('authorizationRecheckArtifactId') != EXPECTED_RECHECK_ARTIFACT_ID:
        raise LunarFiniteDiskExec002Error('authorization-time recheck artifact drift')
    if source.get('authorizationRecheckArtifactDigest') != 'sha256:3949d8b0b9d7ef7b9a689613b4088a96a82a79c2a04f284ec44eeb64df1bc713':
        raise LunarFiniteDiskExec002Error('authorization-time recheck digest drift')
    if source.get('authorizationRecheckStatus') != 'PASS_LUNAR_FINITE_DISK_EXEC002_AUTHORIZATION_TIME_RECHECK_ZERO_RUNTIME':
        raise LunarFiniteDiskExec002Error('authorization-time recheck did not pass')

    prior = a.get('priorFreshnessEvidence') or {}
    if prior.get('artifactId') != 9739969664:
        raise LunarFiniteDiskExec002Error('fresh-seed control artifact drift')
    if prior.get('artifactDigest') != 'sha256:fa1ed884e21b59dee7a3013cfb2fd84ab3c3cd8f2befaca1f1ed26fb5b44e858':
        raise LunarFiniteDiskExec002Error('fresh-seed control digest drift')
    if prior.get('candidateSeedCount') != 198:
        raise LunarFiniteDiskExec002Error('candidate seed count drift')
    if prior.get('candidateSeedCanonicalSha256') != EXPECTED_SEED_CANONICAL:
        raise LunarFiniteDiskExec002Error('candidate seed canonical drift')
    if prior.get('candidateRowsCanonicalSha256') != EXPECTED_ROWS_CANONICAL:
        raise LunarFiniteDiskExec002Error('candidate rows canonical drift')

    predecessor = a.get('consumedPredecessor') or {}
    if predecessor.get('executionId') != 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec001':
        raise LunarFiniteDiskExec002Error('consumed predecessor identity drift')
    if predecessor.get('runId') != 33303099872 or predecessor.get('consumed') is not True:
        raise LunarFiniteDiskExec002Error('consumed predecessor binding drift')
    if predecessor.get('rerunRetryResumeForbidden') is not True or predecessor.get('resultsExist') is not False:
        raise LunarFiniteDiskExec002Error('consumed predecessor boundary drift')

    frozen = a.get('frozenExecution') or {}
    if frozen.get('wavelengthNm') != 550.0 or frozen.get('totalDirectionalCases') != 198:
        raise LunarFiniteDiskExec002Error('frozen finite-disk grid drift')
    if frozen.get('photonHistoriesPerDirectionalCase') != 5_000_000 or frozen.get('totalPhotonHistories') != 990_000_000:
        raise LunarFiniteDiskExec002Error('frozen photon budget drift')
    if frozen.get('candidateSeedCount') != 198:
        raise LunarFiniteDiskExec002Error('frozen candidate cardinality drift')
    if frozen.get('candidateSeedCanonicalSha256') != EXPECTED_SEED_CANONICAL:
        raise LunarFiniteDiskExec002Error('frozen candidate hash drift')
    if frozen.get('candidateSeedRowsCanonicalSha256') != EXPECTED_ROWS_CANONICAL:
        raise LunarFiniteDiskExec002Error('frozen candidate row hash drift')
    if frozen.get('scientificDesignChangedFromExec001') is not False:
        raise LunarFiniteDiskExec002Error('scientific design changed from consumed exec001')

    result = a.get('resultContract') or {}
    if result.get('acceptanceThreshold') is not None or result.get('resultDependentPointSourceAcceptanceForbidden') is not True:
        raise LunarFiniteDiskExec002Error('result-dependent finite-disk threshold forbidden')
    if result.get('mandatorySpectralFollowOnWavelengthsNm') != [450.0, 650.0, 750.0]:
        raise LunarFiniteDiskExec002Error('mandatory spectral follow-on drift')
    if result.get('finiteMoonDiskValidatedByThisExecution') is not False:
        raise LunarFiniteDiskExec002Error('550 nm execution may not validate finite Moon disk')

    rules = a.get('oneShotRules') or {}
    if rules.get('githubRunAttemptMustEqual') != 1:
        raise LunarFiniteDiskExec002Error('attempt-1-only rule drift')
    for key in ('githubRerunForbidden', 'retryForbidden', 'resumeForbidden', 'seedReuseForbiddenAfterAnyExecutionAttempt', 'resultOpeningOnlyThroughFrozenEvaluator', 'fullPaginatedIssue60ReleaseBarrierRequired'):
        if rules.get(key) is not True:
            raise LunarFiniteDiskExec002Error(f'one-shot rule drift: {key}')

    auth = a.get('authorization') or {}
    if auth.get('scientificSolverExecutionAuthorizedAfterSolverFreeReviewPass') is not True:
        raise LunarFiniteDiskExec002Error('post-review solver authorization rule drift')
    if auth.get('dispatchCreated') is not False:
        raise LunarFiniteDiskExec002Error('authorization file must precede dispatch')
    if auth.get('controlProofItselfAuthorizesNoDispatch') is not True:
        raise LunarFiniteDiskExec002Error('control-proof boundary drift')
    if any(value is not False for value in (a.get('protectedBoundaries') or {}).values()):
        raise LunarFiniteDiskExec002Error('protected boundary drift')
    return a


def load_candidate_ledger(path: Path) -> dict[str, Any]:
    ledger = json.loads(path.read_text(encoding='utf-8'))
    if ledger.get('freshExecutionIdentity') != EXPECTED_EXECUTION_ID:
        raise LunarFiniteDiskExec002Error('candidate ledger execution identity drift')
    if ledger.get('candidateSeedCount') != 198:
        raise LunarFiniteDiskExec002Error('candidate ledger cardinality drift')
    seeds = ledger.get('candidateSeeds')
    rows = ledger.get('candidateRows')
    if not isinstance(seeds, list) or not isinstance(rows, list) or len(seeds) != 198 or len(rows) != 198:
        raise LunarFiniteDiskExec002Error('candidate ledger shape drift')
    normalized_seeds = [int(seed) for seed in seeds]
    if len(set(normalized_seeds)) != 198:
        raise LunarFiniteDiskExec002Error('candidate ledger seeds not unique')
    if ledger.get('candidateSeedCanonicalSha256') != EXPECTED_SEED_CANONICAL:
        raise LunarFiniteDiskExec002Error('candidate ledger declared seed hash drift')
    if ledger.get('candidateRowsCanonicalSha256') != EXPECTED_ROWS_CANONICAL:
        raise LunarFiniteDiskExec002Error('candidate ledger declared row hash drift')
    if _canonical_sha256(seeds) != EXPECTED_SEED_CANONICAL:
        raise LunarFiniteDiskExec002Error('candidate ledger seed content hash drift')
    if _canonical_sha256(rows) != EXPECTED_ROWS_CANONICAL:
        raise LunarFiniteDiskExec002Error('candidate ledger row content hash drift')
    if ledger.get('candidateSeedsAppliedToCases') is not False:
        raise LunarFiniteDiskExec002Error('control ledger must remain unapplied evidence')
    if ledger.get('scientificExecutionAuthorized') is not False or ledger.get('solverExecutionAuthorized') is not False:
        raise LunarFiniteDiskExec002Error('control ledger must not self-authorize science')
    return ledger


def authorized_cases(candidate_ledger_path: Path) -> tuple[dict[str, Any], ...]:
    load_authorization()
    planner = _load_registered('lunar_fd_exec002_planner', PLANNER_PATH)
    planned = list(planner.frozen_cases())
    ledger = load_candidate_ledger(candidate_ledger_path)
    rows = ledger['candidateRows']
    if len(planned) != 198:
        raise LunarFiniteDiskExec002Error('frozen case universe drift')
    seed_by_case: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('caseId'), str):
            raise LunarFiniteDiskExec002Error('malformed candidate row')
        case_id = row['caseId']
        seed = int(row.get('seed'))
        if case_id in seed_by_case:
            raise LunarFiniteDiskExec002Error('duplicate candidate case mapping')
        seed_by_case[case_id] = seed
    if set(seed_by_case) != {str(case['caseId']) for case in planned}:
        raise LunarFiniteDiskExec002Error('candidate case universe mismatch')
    out: list[dict[str, Any]] = []
    for case in planned:
        case_id = str(case['caseId'])
        out.append({**case, 'randomSeed': seed_by_case[case_id]})
    if len({row['randomSeed'] for row in out}) != 198:
        raise LunarFiniteDiskExec002Error('authorized execution seeds not unique')
    return tuple(out)


def _runtime_identity(path: Path) -> dict[str, str | None]:
    row = json.loads(path.read_text(encoding='utf-8'))
    return {
        'uvspecSha256': row.get('uvspecSha256'),
        'libRadtranDataTreeSha256': row.get('libRadtranDataTreeSha256'),
    }


def prepare_shard(*, data_dir: Path, atmosphere_file: Path, atlas_file: Path, runtime_report: Path, candidate_ledger_path: Path, output_root: Path, shard_index: int, shard_count: int) -> dict[str, Any]:
    a = load_authorization()
    if shard_count <= 0 or shard_index < 0 or shard_index >= shard_count or 198 % shard_count != 0:
        raise LunarFiniteDiskExec002Error('invalid shard index/count')
    identity = _runtime_identity(runtime_report)
    frozen = a['frozenExecution']
    if identity['uvspecSha256'] != frozen['uvspecSha256']:
        raise LunarFiniteDiskExec002Error('uvspec runtime identity drift')
    if identity['libRadtranDataTreeSha256'] != frozen['libRadtranDataTreeSha256']:
        raise LunarFiniteDiskExec002Error('libRadtran data-tree identity drift')

    source_runtime = _load_registered('lunar_fd_exec002_source_runtime', SOURCE_RUNTIME_PATH)
    lunar_input = _load_registered('lunar_fd_exec002_lunar_input', LUNAR_INPUT_PATH)
    output_root.mkdir(parents=True, exist_ok=True)
    source_file = output_root / 'frozen-lunar-source-380-780nm.dat'
    source_meta = source_runtime.build_lunar_source_from_runtime_atlas(atlas_file, source_file)

    all_cases = authorized_cases(candidate_ledger_path)
    selected = [case for index, case in enumerate(all_cases) if index % shard_count == shard_index]
    if len(selected) != 198 // shard_count:
        raise LunarFiniteDiskExec002Error('unexpected shard cardinality')

    manifest_rows: list[dict[str, Any]] = []
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
            raise LunarFiniteDiskExec002Error('directional sensitivity input mislabeled as finite-disk solution')
        if meta.get('atmosphericScatteredMoonlightValidated') is not False:
            raise LunarFiniteDiskExec002Error('input renderer empirical-validation boundary drift')
        if meta.get('productionAuthorized') is not False:
            raise LunarFiniteDiskExec002Error('input renderer production boundary drift')
        input_path = case_dir / 'case.inp'
        input_path.write_text(rendered, encoding='utf-8')
        manifest_rows.append({
            'caseId': case['caseId'],
            'inputPath': str(input_path),
            'geometryKey': case['geometryKey'],
            'sampleId': case['sampleId'],
            'shardIndex': shard_index,
        })

    manifest = {
        'schemaVersion': 1,
        'executionId': EXPECTED_EXECUTION_ID,
        'status': 'PREPARED_AUTHORIZED_SHARD_NO_RESULT_OPENED',
        'shardIndex': shard_index,
        'shardCount': shard_count,
        'caseCount': len(manifest_rows),
        'caseIds': [row['caseId'] for row in manifest_rows],
        'cases': manifest_rows,
        'sourceMetadata': source_meta,
        'candidateSeedCanonicalSha256': EXPECTED_SEED_CANONICAL,
        'candidateRowsCanonicalSha256': EXPECTED_ROWS_CANONICAL,
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
            raise LunarFiniteDiskExec002Error(f'nonfinite output row in {path}')
        if abs(wavelength - wavelength_nm) <= 5e-4:
            matches.append(value)
    if len(matches) != 1:
        raise LunarFiniteDiskExec002Error(f'expected exactly one {wavelength_nm} nm row in {path}, found {len(matches)}')
    return matches[0]


def evaluate_result_root(*, candidate_ledger_path: Path, result_root: Path, output_path: Path) -> dict[str, Any]:
    a = load_authorization()
    planner = _load_registered('lunar_fd_exec002_frozen_evaluator', PLANNER_PATH)
    cases = authorized_cases(candidate_ledger_path)
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
        except LunarFiniteDiskExec002Error as exc:
            parser_failures.append(f'OUTPUT_PARSE:{case["caseId"]}:{exc}')
            continue
        records.append({'caseId': case['caseId'], 'solverExitCode': exit_code, 'radiance': radiance, 'stdRadiance': std})

    if parser_failures:
        report: dict[str, Any] = {
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

    report.update({
        'executionId': EXPECTED_EXECUTION_ID,
        'authorizationReviewArtifactId': EXPECTED_AUTH_REVIEW_ARTIFACT_ID,
        'authorizationTimeRecheckArtifactId': EXPECTED_RECHECK_ARTIFACT_ID,
        'candidateSeedCanonicalSha256': EXPECTED_SEED_CANONICAL,
        'candidateRowsCanonicalSha256': EXPECTED_ROWS_CANONICAL,
        'seedLiteralsIncludedInResult': False,
        'mandatorySpectralFollowOnRequired': True,
        'mandatorySpectralFollowOnWavelengthsNm': [450.0, 650.0, 750.0],
        'finiteMoonDiskValidated': False,
        'empiricalAtmosphericMoonlightValidated': False,
        'totalSkyValidated': False,
        'productionAuthorized': False,
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def validate_runtime_contract() -> dict[str, Any]:
    a = load_authorization()
    planner = _load_registered('lunar_fd_exec002_validate_planner', PLANNER_PATH)
    plan = planner.validate_plan()
    if plan['caseCount'] != 198 or plan['geometryCount'] != 6 or plan['directionsPerGeometry'] != 33:
        raise LunarFiniteDiskExec002Error('planner design drift')
    return {
        'executionId': a['executionId'],
        'caseCount': plan['caseCount'],
        'geometryCount': plan['geometryCount'],
        'directionsPerGeometry': plan['directionsPerGeometry'],
        'candidateSeedCount': 198,
        'candidateSeedCanonicalSha256': EXPECTED_SEED_CANONICAL,
        'candidateRowsCanonicalSha256': EXPECTED_ROWS_CANONICAL,
        'acceptanceThreshold': None,
        'mandatorySpectralFollowOnNm': [450.0, 650.0, 750.0],
        'solverExecutionPerformed': False,
        'resultOpened': False,
        'finiteMoonDiskValidated': False,
        'productionAuthorized': False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)

    validate = sub.add_parser('validate')
    validate.add_argument('--json', action='store_true')

    ledger = sub.add_parser('validate-candidate-ledger')
    ledger.add_argument('--candidate-ledger', type=Path, required=True)

    prepare = sub.add_parser('prepare-shard')
    prepare.add_argument('--data-dir', type=Path, required=True)
    prepare.add_argument('--atmosphere-file', type=Path, required=True)
    prepare.add_argument('--atlas-file', type=Path, required=True)
    prepare.add_argument('--runtime-report', type=Path, required=True)
    prepare.add_argument('--candidate-ledger', type=Path, required=True)
    prepare.add_argument('--output-root', type=Path, required=True)
    prepare.add_argument('--shard-index', type=int, required=True)
    prepare.add_argument('--shard-count', type=int, required=True)

    evaluate = sub.add_parser('evaluate')
    evaluate.add_argument('--candidate-ledger', type=Path, required=True)
    evaluate.add_argument('--result-root', type=Path, required=True)
    evaluate.add_argument('--output', type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == 'validate':
        report = validate_runtime_contract()
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print('PASS_LUNAR_FINITE_DISK_EXEC002_RUNTIME_CONTRACT')
        return 0
    if args.command == 'validate-candidate-ledger':
        candidate = load_candidate_ledger(args.candidate_ledger)
        print(json.dumps({
            'status': 'PASS_EXEC002_CANDIDATE_LEDGER_BINDING',
            'candidateSeedCount': candidate['candidateSeedCount'],
            'candidateSeedCanonicalSha256': candidate['candidateSeedCanonicalSha256'],
            'candidateRowsCanonicalSha256': candidate['candidateRowsCanonicalSha256'],
            'seedLiteralsLogged': False,
        }, indent=2, sort_keys=True))
        return 0
    if args.command == 'prepare-shard':
        report = prepare_shard(
            data_dir=args.data_dir,
            atmosphere_file=args.atmosphere_file,
            atlas_file=args.atlas_file,
            runtime_report=args.runtime_report,
            candidate_ledger_path=args.candidate_ledger,
            output_root=args.output_root,
            shard_index=args.shard_index,
            shard_count=args.shard_count,
        )
        print(json.dumps({
            'status': report['status'],
            'executionId': report['executionId'],
            'shardIndex': report['shardIndex'],
            'caseCount': report['caseCount'],
            'seedLiteralsSerializedInManifest': report['seedLiteralsSerializedInManifest'],
        }, sort_keys=True))
        return 0
    report = evaluate_result_root(candidate_ledger_path=args.candidate_ledger, result_root=args.result_root, output_path=args.output)
    print(json.dumps({
        'classification': report.get('classification'),
        'executionComplete': report.get('executionComplete'),
        'finiteMoonDiskValidated': report.get('finiteMoonDiskValidated'),
        'mandatorySpectralFollowOnRequired': report.get('mandatorySpectralFollowOnRequired'),
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
