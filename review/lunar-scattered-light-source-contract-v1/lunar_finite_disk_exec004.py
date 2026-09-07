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
FROZEN_BASE_ROOT = HERE / '.exec004-frozen-base'
BASE_RUNTIME_PATH = FROZEN_BASE_ROOT / 'lunar_finite_disk_exec002.py'
REPTRAN_ADAPTER_PATH = HERE / 'lunar_mystic_input_exec004_reptran_adapter.py'
AUTH_PATH = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec004-authorization.json'
EXECUTION_WORKFLOW_PATH = Path('.github/workflows/lunar-finite-disk-exec004-v1.yml')

EXECUTION_ID = 'lunar-finite-disk-transfer-kernel-sensitivity-v1-exec004'
CONTROL_RUN = 34059309664
CONTROL_JOB = 101556849327
CONTROL_ARTIFACT = 9997398593
CONTROL_DIGEST = 'sha256:2314be605f0c8ed5f1592b36e8cd9801037434d3c9668ec2e1d2b7d287037d70'
CONTROL_PROOF_SHA = '16113b29ee13cb9545e14733b1eefda3fbb641905003d1ab28b713dbd46133ff'
SEED_CANONICAL = '9a29092f1708b3c8c46542967b29471689b9de3b293adadbc16c25410091e585'
ROWS_CANONICAL = '9f6aa730fa7720fd985cfbda55ac49023f90be7de8d5f5bc931ab52aca77aa56'
RECHECK_HEAD = '74f70d2d5db29926c5d1833326d3469993cbbdb2'
RECHECK_RUN = 34065544069
RECHECK_JOB = 101573540184
RECHECK_ARTIFACT = 9999276308
RECHECK_DIGEST = 'sha256:c97196f901fd3dd4004b6cf543b0c6ece2b2dcc1b60b99fc2894a7a05e247ff9'
RECHECK_PROOF_SHA = '0310413267de648fda91c1f0f683651d54ef55786a2e5244de67664260f5750b'
REPTRAN_PRESTAGE_HEAD = 'b85a9ea9175bc6c98cbdf3f607ad2b81bb7da823'
REPTRAN_PRESTAGE_RUN = 34052817182
REPTRAN_PRESTAGE_ARTIFACT = 9995060899
REPTRAN_PRESTAGE_DIGEST = 'sha256:60e01e40e899e28f65e58c2acb90eac4c893010fab0e7f7782a9c0391ff32c7a'
REPTRAN_CAP_HEAD = '9d78567ffb55a2fe187e256a2abaf994aaad453f'
REPTRAN_CAP_RUN = 34053349932
REPTRAN_CAP_JOB = 101540778940
REPTRAN_CAP_ARTIFACT = 9995224987
REPTRAN_CAP_DIGEST = 'sha256:fd906b1060594a6e80884f3847e4fdcc43e8ede7f231d04cfe797fbcf4204e79'
UVSPEC_SHA256 = '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
LIBRADTRAN_DATA_SHA256 = 'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7'
FROZEN_HISTORICAL_HEAD = '5e9a3a0ece29c824912090b00db2bffda11d0804'

class Exec004Error(RuntimeError):
    pass

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Exec004Error(f'cannot import {path}')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def review_contract() -> dict[str, Any]:
    return {
        'schemaVersion': 1,
        'status': 'FROZEN_EXEC004_REPTRAN_SCIENCE_RUNTIME_REVIEW_ONLY_NOT_AUTHORIZED',
        'executionId': EXECUTION_ID,
        'control': {
            'run': CONTROL_RUN, 'job': CONTROL_JOB, 'artifact': CONTROL_ARTIFACT,
            'digest': CONTROL_DIGEST, 'proofSha256': CONTROL_PROOF_SHA,
            'candidateSeedCount': 198, 'seedCanonicalSha256': SEED_CANONICAL,
            'rowsCanonicalSha256': ROWS_CANONICAL,
        },
        'authorizationTimeRecheck': {
            'head': RECHECK_HEAD, 'run': RECHECK_RUN, 'job': RECHECK_JOB,
            'artifact': RECHECK_ARTIFACT, 'digest': RECHECK_DIGEST,
            'proofSha256': RECHECK_PROOF_SHA,
            'status': 'PASS_LUNAR_FINITE_DISK_EXEC004_AUTHORIZATION_TIME_RECHECK_ZERO_RUNTIME_NOT_ALLOCATED_NOT_AUTHORIZED',
        },
        'reptranPrerequisites': {
            'prestageHead': REPTRAN_PRESTAGE_HEAD, 'prestageRun': REPTRAN_PRESTAGE_RUN,
            'prestageArtifact': REPTRAN_PRESTAGE_ARTIFACT, 'prestageDigest': REPTRAN_PRESTAGE_DIGEST,
            'capabilityHead': REPTRAN_CAP_HEAD, 'capabilityRun': REPTRAN_CAP_RUN,
            'capabilityJob': REPTRAN_CAP_JOB, 'capabilityArtifact': REPTRAN_CAP_ARTIFACT,
            'capabilityDigest': REPTRAN_CAP_DIGEST, 'molecularAbsorption': 'reptran',
            'historicalCrsFallbackAllowed': False,
        },
        'frozenScience': {
            'wavelengthNm': 550.0, 'geometryCount': 6, 'directionsPerGeometry': 33,
            'totalDirectionalCases': 198, 'photonHistoriesPerDirectionalCase': 5_000_000,
            'totalPhotonHistories': 990_000_000, 'acceptanceThreshold': None,
            'mandatorySpectralFollowOnNm': [450.0, 650.0, 750.0],
            'descriptiveEvaluatorUnchanged': True,
            'molecularAbsorption': 'reptran',
        },
        'runtime': {
            'package': 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1',
            'uvspecSha256': UVSPEC_SHA256,
            'libRadtranDataTreeSha256': LIBRADTRAN_DATA_SHA256,
            'frozenHistoricalRuntimeHead': FROZEN_HISTORICAL_HEAD,
        },
        'protectedBoundaries': {
            'candidateSeedsApplied': False, 'candidateSeedUniverseAllocated': False,
            'scientificExecutionAuthorized': False, 'solverExecuted': False,
            'resultOpened': False, 'finiteDiskAdequacyValidated': False,
            'empiricalAtmosphericMoonlightValidated': False,
            'taylorOrJerusalemUsed': False, 'totalSkyValidated': False,
            'productionAuthorized': False,
        },
    }

def _require_hex(value: Any, n: int, label: str) -> str:
    value = str(value or '')
    if not re.fullmatch(rf'[0-9a-f]{{{n}}}', value):
        raise Exec004Error(f'{label} must be {n}-hex')
    return value

def load_authorization() -> dict[str, Any]:
    if not AUTH_PATH.is_file():
        raise Exec004Error('exec004 authorization file absent; review package cannot self-authorize')
    a = json.loads(AUTH_PATH.read_text(encoding='utf-8'))
    if a.get('authorizationId') != EXECUTION_ID + '-authorization' or a.get('executionId') != EXECUTION_ID:
        raise Exec004Error('authorization identity drift')
    if a.get('status') != 'AUTHORIZED_ONE_SHOT_ATTEMPT1_ONLY_AFTER_SOLVER_FREE_REPTRAN_REVIEW':
        raise Exec004Error('authorization status drift')
    r = a.get('authorizationTimeRecheck') or {}
    expected = (RECHECK_HEAD, RECHECK_RUN, RECHECK_JOB, RECHECK_ARTIFACT, RECHECK_DIGEST, RECHECK_PROOF_SHA)
    observed = (r.get('head'), r.get('run'), r.get('job'), r.get('artifact'), r.get('digest'), r.get('proofSha256'))
    if observed != expected:
        raise Exec004Error('authorization-time recheck binding drift')
    review = a.get('scienceWorkflowReview') or {}
    if review.get('status') != 'PASS_LUNAR_FINITE_DISK_EXEC004_REPTRAN_SCIENCE_WORKFLOW_SOLVER_FREE':
        raise Exec004Error('solver-free science-workflow review not bound')
    _require_hex(review.get('head'), 40, 'scienceWorkflowReview.head')
    if int(review.get('run') or 0) <= 0 or int(review.get('job') or 0) <= 0 or int(review.get('artifact') or 0) <= 0:
        raise Exec004Error('scienceWorkflowReview run/job/artifact missing')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', str(review.get('artifactDigest') or '')):
        raise Exec004Error('scienceWorkflowReview artifact digest malformed')
    _require_hex(review.get('workflowSha256'), 64, 'scienceWorkflowReview.workflowSha256')
    _require_hex(review.get('runtimeSha256'), 64, 'scienceWorkflowReview.runtimeSha256')
    _require_hex(review.get('rendererAdapterSha256'), 64, 'scienceWorkflowReview.rendererAdapterSha256')
    if EXECUTION_WORKFLOW_PATH.is_file() and _sha256(EXECUTION_WORKFLOW_PATH) != review['workflowSha256']:
        raise Exec004Error('execution workflow bytes differ from reviewed bytes')
    if _sha256(Path(__file__)) != review['runtimeSha256']:
        raise Exec004Error('exec004 runtime bytes differ from reviewed bytes')
    if _sha256(REPTRAN_ADAPTER_PATH) != review['rendererAdapterSha256']:
        raise Exec004Error('exec004 REPTRAN adapter bytes differ from reviewed bytes')
    c = a.get('control') or {}
    expected_c = (CONTROL_RUN, CONTROL_JOB, CONTROL_ARTIFACT, CONTROL_DIGEST, CONTROL_PROOF_SHA, SEED_CANONICAL, ROWS_CANONICAL)
    observed_c = (c.get('run'), c.get('job'), c.get('artifact'), c.get('digest'), c.get('proofSha256'), c.get('seedCanonicalSha256'), c.get('rowsCanonicalSha256'))
    if observed_c != expected_c:
        raise Exec004Error('fresh-control binding drift')
    rp = a.get('reptranPrerequisites') or {}
    required_rp = {
        'prestageHead': REPTRAN_PRESTAGE_HEAD, 'prestageRun': REPTRAN_PRESTAGE_RUN,
        'prestageArtifact': REPTRAN_PRESTAGE_ARTIFACT, 'prestageDigest': REPTRAN_PRESTAGE_DIGEST,
        'capabilityHead': REPTRAN_CAP_HEAD, 'capabilityRun': REPTRAN_CAP_RUN,
        'capabilityJob': REPTRAN_CAP_JOB, 'capabilityArtifact': REPTRAN_CAP_ARTIFACT,
        'capabilityDigest': REPTRAN_CAP_DIGEST, 'molAbsParam': 'reptran',
        'historicalCrsFallbackAllowed': False,
    }
    for key, val in required_rp.items():
        if rp.get(key) != val:
            raise Exec004Error(f'REPTRAN prerequisite drift: {key}')
    frozen = a.get('frozenExecution') or {}
    required = {
        'wavelengthNm': 550.0, 'totalDirectionalCases': 198,
        'photonHistoriesPerDirectionalCase': 5_000_000, 'totalPhotonHistories': 990_000_000,
        'candidateSeedCount': 198, 'candidateSeedCanonicalSha256': SEED_CANONICAL,
        'candidateSeedRowsCanonicalSha256': ROWS_CANONICAL,
        'uvspecSha256': UVSPEC_SHA256, 'libRadtranDataTreeSha256': LIBRADTRAN_DATA_SHA256,
        'aod550': 0.1, 'lambertianAlbedo': 0.15, 'molAbsParam': 'reptran',
    }
    for key, val in required.items():
        if frozen.get(key) != val:
            raise Exec004Error(f'frozenExecution drift: {key}')
    result = a.get('resultContract') or {}
    if result.get('acceptanceThreshold') is not None:
        raise Exec004Error('result-dependent threshold forbidden')
    if result.get('mandatorySpectralFollowOnWavelengthsNm') != [450.0, 650.0, 750.0]:
        raise Exec004Error('spectral follow-on drift')
    one = a.get('oneShotRules') or {}
    for key in ('githubRerunForbidden','retryForbidden','resumeForbidden','seedReuseForbiddenAfterAnyExecutionAttempt','resultOpeningOnlyThroughFrozenEvaluator','fullPaginatedIssue60ReleaseBarrierRequired'):
        if one.get(key) is not True:
            raise Exec004Error(f'one-shot rule drift: {key}')
    if one.get('githubRunAttemptMustEqual') != 1:
        raise Exec004Error('attempt-1 rule drift')
    if any((a.get('protectedBoundaries') or {}).values()):
        raise Exec004Error('protected boundary opened')
    return a

def _base(*, require_authorization: bool):
    if not BASE_RUNTIME_PATH.is_file():
        raise Exec004Error('exact frozen historical exec002 runtime tree not materialized')
    base = _load('lunar_fd_exec004_base_runtime', BASE_RUNTIME_PATH)
    base.EXPECTED_EXECUTION_ID = EXECUTION_ID
    base.EXPECTED_SEED_CANONICAL = SEED_CANONICAL
    base.EXPECTED_ROWS_CANONICAL = ROWS_CANONICAL
    base.EXPECTED_RECHECK_ARTIFACT_ID = RECHECK_ARTIFACT
    base.EXPECTED_AUTH_REVIEW_ARTIFACT_ID = 0
    base.LUNAR_INPUT_PATH = REPTRAN_ADAPTER_PATH
    if require_authorization:
        base.load_authorization = load_authorization
    return base

def validate_candidate_ledger(path: Path) -> dict[str, Any]:
    base = _base(require_authorization=False)
    row = base.load_candidate_ledger(path)
    return {'status':'PASS_EXEC004_CANDIDATE_LEDGER_BINDING','candidateSeedCount':row['candidateSeedCount'],
            'candidateSeedCanonicalSha256':row['candidateSeedCanonicalSha256'],
            'candidateRowsCanonicalSha256':row['candidateRowsCanonicalSha256'],'seedLiteralsLogged':False}

def prepare_shard(**kwargs):
    return _base(require_authorization=True).prepare_shard(**kwargs)

def evaluate_result_root(*, candidate_ledger_path: Path, result_root: Path, output_path: Path) -> dict[str, Any]:
    base = _base(require_authorization=True)
    report = base.evaluate_result_root(candidate_ledger_path=candidate_ledger_path, result_root=result_root, output_path=output_path)
    auth = load_authorization()
    report.pop('authorizationReviewArtifactId', None)
    report['authorizationTimeRecheckArtifactId'] = RECHECK_ARTIFACT
    report['scienceWorkflowReviewArtifactId'] = int(auth['scienceWorkflowReview']['artifact'])
    report['executionId'] = EXECUTION_ID
    report['molecularAbsorption'] = 'reptran'
    report['finiteMoonDiskValidated'] = False
    report['empiricalAtmosphericMoonlightValidated'] = False
    report['totalSkyValidated'] = False
    report['productionAuthorized'] = False
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    return report

def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='command', required=True)
    s.add_parser('validate-review'); s.add_parser('validate-authorization')
    c=s.add_parser('validate-candidate-ledger'); c.add_argument('--candidate-ledger',type=Path,required=True)
    prep=s.add_parser('prepare-shard')
    for flag in ('data-dir','atmosphere-file','atlas-file','runtime-report','candidate-ledger','output-root'):
        prep.add_argument('--'+flag,type=Path,required=True)
    prep.add_argument('--shard-index',type=int,required=True); prep.add_argument('--shard-count',type=int,required=True)
    ev=s.add_parser('evaluate'); ev.add_argument('--candidate-ledger',type=Path,required=True); ev.add_argument('--result-root',type=Path,required=True); ev.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    if a.command=='validate-review':
        print(json.dumps(review_contract(),indent=2,sort_keys=True)); return 0
    if a.command=='validate-authorization':
        auth=load_authorization(); print(json.dumps({'status':'PASS_EXEC004_AUTHORIZATION_BINDING','executionId':auth['executionId']},sort_keys=True)); return 0
    if a.command=='validate-candidate-ledger':
        print(json.dumps(validate_candidate_ledger(a.candidate_ledger),indent=2,sort_keys=True)); return 0
    if a.command=='prepare-shard':
        r=prepare_shard(data_dir=a.data_dir,atmosphere_file=a.atmosphere_file,atlas_file=a.atlas_file,runtime_report=a.runtime_report,candidate_ledger_path=a.candidate_ledger,output_root=a.output_root,shard_index=a.shard_index,shard_count=a.shard_count)
        print(json.dumps({'status':r['status'],'executionId':r['executionId'],'shardIndex':r['shardIndex'],'caseCount':r['caseCount'],'seedLiteralsSerializedInManifest':r['seedLiteralsSerializedInManifest']},sort_keys=True)); return 0
    r=evaluate_result_root(candidate_ledger_path=a.candidate_ledger,result_root=a.result_root,output_path=a.output)
    print(json.dumps({'classification':r.get('classification'),'executionComplete':r.get('executionComplete'),'finiteMoonDiskValidated':r.get('finiteMoonDiskValidated'),'mandatorySpectralFollowOnRequired':r.get('mandatorySpectralFollowOnRequired')},sort_keys=True)); return 0

if __name__=='__main__':
    raise SystemExit(main())
