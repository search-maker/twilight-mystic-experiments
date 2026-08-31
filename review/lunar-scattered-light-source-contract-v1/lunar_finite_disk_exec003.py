#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
BASE_RUNTIME_PATH = HERE / 'lunar_finite_disk_exec002.py'
AUTH_PATH = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003-authorization.json'
EXECUTION_WORKFLOW_PATH = Path('.github/workflows/lunar-finite-disk-exec003-v1.yml')

EXECUTION_ID = 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003'
CONTROL_RUN = 33362571300
CONTROL_JOB = 99396670270
CONTROL_ARTIFACT = 9747665530
CONTROL_DIGEST = 'sha256:6dc617806f3b76fb675c19b295a9f9e1b6f85a5657d83d6811b69771c3d7683b'
CONTROL_PROOF_SHA = '684f4c343dee44e1ab65b8f50581482d1922d17175fb5ff7f9295e8db1f80acc'
SEED_CANONICAL = 'e27ba17758a6111da3b791535fff2a46d4e06a04fb163b546c871d455370ab44'
ROWS_CANONICAL = 'ad13f6645d6db0621af78c2434c3a0c9f82b09850def79d051175d4a6cb814d5'
V5_HEAD = 'f0131389c2195d61bd55b91cf03748dfd4c0da97'
V5_RUN = 33380238826
V5_JOB = 99450731881
V5_ARTIFACT = 9754092951
V5_DIGEST = 'sha256:9d30e770fe88453b5527d548e3571997fc624e7e5c7e6b2b8a4de6f99e43ea66'
V5_PROOF_SHA = '0c5d40e6fc2431cdce24419b87631da21048ce6ab9a2e0e3859a4e38c2c84bb9'
UVSPEC_SHA256 = '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
LIBRADTRAN_DATA_SHA256 = 'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7'


class Exec003Error(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Exec003Error(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review_contract() -> dict[str, Any]:
    return {
        'schemaVersion': 1,
        'status': 'FROZEN_EXEC003_SCIENCE_RUNTIME_REVIEW_ONLY_NOT_AUTHORIZED',
        'executionId': EXECUTION_ID,
        'control': {
            'run': CONTROL_RUN, 'job': CONTROL_JOB, 'artifact': CONTROL_ARTIFACT,
            'digest': CONTROL_DIGEST, 'proofSha256': CONTROL_PROOF_SHA,
            'candidateSeedCount': 198, 'seedCanonicalSha256': SEED_CANONICAL,
            'rowsCanonicalSha256': ROWS_CANONICAL,
        },
        'authorizationTimeRecheck': {
            'head': V5_HEAD, 'run': V5_RUN, 'job': V5_JOB, 'artifact': V5_ARTIFACT,
            'digest': V5_DIGEST, 'proofSha256': V5_PROOF_SHA,
            'status': 'PASS_LUNAR_FINITE_DISK_EXEC003_AUTHORIZATION_TIME_RECHECK_ZERO_RUNTIME_NOT_AUTHORIZED',
        },
        'frozenScience': {
            'wavelengthNm': 550.0, 'geometryCount': 6, 'directionsPerGeometry': 33,
            'totalDirectionalCases': 198, 'photonHistoriesPerDirectionalCase': 5_000_000,
            'totalPhotonHistories': 990_000_000, 'acceptanceThreshold': None,
            'mandatorySpectralFollowOnNm': [450.0, 650.0, 750.0],
            'descriptiveEvaluatorUnchanged': True,
        },
        'runtime': {
            'package': 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1',
            'uvspecSha256': UVSPEC_SHA256,
            'libRadtranDataTreeSha256': LIBRADTRAN_DATA_SHA256,
        },
        'protectedBoundaries': {
            'candidateSeedsApplied': False, 'scientificExecutionAuthorized': False,
            'solverExecuted': False, 'resultOpened': False, 'finiteDiskAdequacyValidated': False,
            'empiricalAtmosphericMoonlightValidated': False, 'taylorOrJerusalemUsed': False,
            'totalSkyValidated': False, 'productionAuthorized': False,
        },
    }


def _require_hex(value: Any, n: int, label: str) -> str:
    value = str(value or '')
    if not re.fullmatch(rf'[0-9a-f]{{{n}}}', value):
        raise Exec003Error(f'{label} must be {n}-hex')
    return value


def load_authorization() -> dict[str, Any]:
    if not AUTH_PATH.is_file():
        raise Exec003Error('exec003 authorization file absent; review package cannot self-authorize')
    a = json.loads(AUTH_PATH.read_text(encoding='utf-8'))
    if a.get('authorizationId') != 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec003-authorization':
        raise Exec003Error('authorization identity drift')
    if a.get('executionId') != EXECUTION_ID:
        raise Exec003Error('execution identity drift')
    if a.get('status') != 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_AFTER_V6_SOLVER_FREE_REVIEW':
        raise Exec003Error('authorization status drift')
    v5 = a.get('authorizationTimeRecheck') or {}
    expected_v5 = (V5_HEAD, V5_RUN, V5_JOB, V5_ARTIFACT, V5_DIGEST, V5_PROOF_SHA)
    observed_v5 = (v5.get('head'), v5.get('run'), v5.get('job'), v5.get('artifact'), v5.get('digest'), v5.get('proofSha256'))
    if observed_v5 != expected_v5:
        raise Exec003Error('V5 authorization-time proof binding drift')
    review = a.get('scienceWorkflowReview') or {}
    if review.get('status') != 'PASS_LUNAR_FINITE_DISK_EXEC003_SCIENCE_WORKFLOW_V6_SOLVER_FREE':
        raise Exec003Error('V6 science-workflow review not bound')
    _require_hex(review.get('head'), 40, 'scienceWorkflowReview.head')
    if int(review.get('run') or 0) <= 0 or int(review.get('artifact') or 0) <= 0:
        raise Exec003Error('scienceWorkflowReview run/artifact missing')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', str(review.get('artifactDigest') or '')):
        raise Exec003Error('scienceWorkflowReview artifact digest malformed')
    _require_hex(review.get('workflowSha256'), 64, 'scienceWorkflowReview.workflowSha256')
    _require_hex(review.get('runtimeSha256'), 64, 'scienceWorkflowReview.runtimeSha256')
    if EXECUTION_WORKFLOW_PATH.is_file() and _sha256(EXECUTION_WORKFLOW_PATH) != review['workflowSha256']:
        raise Exec003Error('execution workflow bytes differ from V6-reviewed bytes')
    if _sha256(Path(__file__)) != review['runtimeSha256']:
        raise Exec003Error('exec003 runtime bytes differ from V6-reviewed bytes')
    control = a.get('control') or {}
    expected_control = (CONTROL_RUN, CONTROL_JOB, CONTROL_ARTIFACT, CONTROL_DIGEST, CONTROL_PROOF_SHA, SEED_CANONICAL, ROWS_CANONICAL)
    observed_control = (control.get('run'), control.get('job'), control.get('artifact'), control.get('digest'), control.get('proofSha256'), control.get('seedCanonicalSha256'), control.get('rowsCanonicalSha256'))
    if observed_control != expected_control:
        raise Exec003Error('control binding drift')
    frozen = a.get('frozenExecution') or {}
    required = {
        'wavelengthNm': 550.0, 'totalDirectionalCases': 198,
        'photonHistoriesPerDirectionalCase': 5_000_000, 'totalPhotonHistories': 990_000_000,
        'candidateSeedCount': 198, 'candidateSeedCanonicalSha256': SEED_CANONICAL,
        'candidateSeedRowsCanonicalSha256': ROWS_CANONICAL,
        'uvspecSha256': UVSPEC_SHA256, 'libRadtranDataTreeSha256': LIBRADTRAN_DATA_SHA256,
        'aod550': 0.1, 'lambertianAlbedo': 0.15,
    }
    for key, expected in required.items():
        if frozen.get(key) != expected:
            raise Exec003Error(f'frozenExecution drift: {key}')
    if (a.get('resultContract') or {}).get('acceptanceThreshold') is not None:
        raise Exec003Error('result-dependent acceptance threshold forbidden')
    if (a.get('resultContract') or {}).get('mandatorySpectralFollowOnWavelengthsNm') != [450.0, 650.0, 750.0]:
        raise Exec003Error('spectral follow-on drift')
    one = a.get('oneShotRules') or {}
    for key in ('githubRerunForbidden', 'retryForbidden', 'resumeForbidden', 'seedReuseForbiddenAfterAnyExecutionAttempt', 'fullPaginatedIssue60ReleaseBarrierRequired'):
        if one.get(key) is not True:
            raise Exec003Error(f'one-shot rule drift: {key}')
    if one.get('githubRunAttemptMustEqual') != 1:
        raise Exec003Error('attempt-1 rule drift')
    if any((a.get('protectedBoundaries') or {}).values()):
        raise Exec003Error('protected boundary opened')
    return a


def _base(*, require_authorization: bool):
    base = _load('lunar_fd_exec003_base_runtime', BASE_RUNTIME_PATH)
    base.EXPECTED_EXECUTION_ID = EXECUTION_ID
    base.EXPECTED_SEED_CANONICAL = SEED_CANONICAL
    base.EXPECTED_ROWS_CANONICAL = ROWS_CANONICAL
    base.EXPECTED_RECHECK_ARTIFACT_ID = V5_ARTIFACT
    base.EXPECTED_AUTH_REVIEW_ARTIFACT_ID = 0
    if require_authorization:
        base.load_authorization = load_authorization
    return base


def validate_candidate_ledger(path: Path) -> dict[str, Any]:
    base = _base(require_authorization=False)
    row = base.load_candidate_ledger(path)
    return {
        'status': 'PASS_EXEC003_CANDIDATE_LEDGER_BINDING',
        'candidateSeedCount': row['candidateSeedCount'],
        'candidateSeedCanonicalSha256': row['candidateSeedCanonicalSha256'],
        'candidateRowsCanonicalSha256': row['candidateRowsCanonicalSha256'],
        'seedLiteralsLogged': False,
    }


def prepare_shard(**kwargs):
    return _base(require_authorization=True).prepare_shard(**kwargs)


def evaluate_result_root(*, candidate_ledger_path: Path, result_root: Path, output_path: Path) -> dict[str, Any]:
    base = _base(require_authorization=True)
    report = base.evaluate_result_root(candidate_ledger_path=candidate_ledger_path, result_root=result_root, output_path=output_path)
    auth = load_authorization()
    report.pop('authorizationReviewArtifactId', None)
    report['authorizationTimeRecheckArtifactId'] = V5_ARTIFACT
    report['scienceWorkflowReviewArtifactId'] = int(auth['scienceWorkflowReview']['artifact'])
    report['executionId'] = EXECUTION_ID
    report['finiteMoonDiskValidated'] = False
    report['empiricalAtmosphericMoonlightValidated'] = False
    report['totalSkyValidated'] = False
    report['productionAuthorized'] = False
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest='command', required=True)
    s.add_parser('validate-review')
    s.add_parser('validate-authorization')
    c = s.add_parser('validate-candidate-ledger'); c.add_argument('--candidate-ledger', type=Path, required=True)
    prep = s.add_parser('prepare-shard')
    for flag in ('data-dir','atmosphere-file','atlas-file','runtime-report','candidate-ledger','output-root'):
        prep.add_argument('--'+flag, type=Path, required=True)
    prep.add_argument('--shard-index', type=int, required=True); prep.add_argument('--shard-count', type=int, required=True)
    ev = s.add_parser('evaluate'); ev.add_argument('--candidate-ledger', type=Path, required=True); ev.add_argument('--result-root', type=Path, required=True); ev.add_argument('--output', type=Path, required=True)
    a = p.parse_args(argv)
    if a.command == 'validate-review':
        print(json.dumps(review_contract(), indent=2, sort_keys=True)); return 0
    if a.command == 'validate-authorization':
        auth = load_authorization(); print(json.dumps({'status':'PASS_EXEC003_AUTHORIZATION_BINDING','executionId':auth['executionId']}, sort_keys=True)); return 0
    if a.command == 'validate-candidate-ledger':
        print(json.dumps(validate_candidate_ledger(a.candidate_ledger), indent=2, sort_keys=True)); return 0
    if a.command == 'prepare-shard':
        r = prepare_shard(data_dir=a.data_dir, atmosphere_file=a.atmosphere_file, atlas_file=a.atlas_file, runtime_report=a.runtime_report, candidate_ledger_path=a.candidate_ledger, output_root=a.output_root, shard_index=a.shard_index, shard_count=a.shard_count)
        print(json.dumps({'status':r['status'],'executionId':r['executionId'],'shardIndex':r['shardIndex'],'caseCount':r['caseCount'],'seedLiteralsSerializedInManifest':r['seedLiteralsSerializedInManifest']}, sort_keys=True)); return 0
    r = evaluate_result_root(candidate_ledger_path=a.candidate_ledger, result_root=a.result_root, output_path=a.output)
    print(json.dumps({'classification':r.get('classification'),'executionComplete':r.get('executionComplete'),'finiteMoonDiskValidated':r.get('finiteMoonDiskValidated'),'mandatorySpectralFollowOnRequired':r.get('mandatorySpectralFollowOnRequired')}, sort_keys=True)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
