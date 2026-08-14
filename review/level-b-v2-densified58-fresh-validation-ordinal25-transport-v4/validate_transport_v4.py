#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSPORT_REL = Path('review/level-b-v2-densified58-fresh-validation-ordinal25-transport-v4/transport-v4.json')
AUTH_REL = Path('review/level-b-v2-densified58-fresh-validation-ordinal25-transport-v4/authorization.json')
AUTH_WF_REL = Path('.github/workflows/level-b-v2-densified58-fresh-validation-ordinal25-authorization-review-v4.yml')
EXEC_WF_REL = Path('.github/workflows/level-b-v2-densified58-fresh-validation-ordinal25-execution-v4.yml')


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def blob(path: str) -> str:
    return subprocess.check_output(['git', 'rev-parse', f'HEAD:{path}'], text=True).strip()


def validate(require_review_inert: bool) -> dict:
    t = load(ROOT / TRANSPORT_REL)
    req((t.get('schemaVersion'), t.get('transportId'), t.get('status'), t.get('governance')) == (
        4,
        'level-b-v2-densified58-fresh-validation-ordinal25-transport-v4',
        'REVIEW_ONLY_ORDINAL25_AUTHORIZATION_AND_DISPATCH_TRANSPORT_NO_AUTHORIZATION_FILE_NO_ALLOCATION',
        'MYSTIC-STATE-0070',
    ), 'transport identity drift')
    req(t.get('sourceMainAtTransportFreeze') == '03c49af35c6bfe06f941fd35150bc4d47d8991ba', 'transport source-main drift')

    src = t['recoverySource']
    expected_src = {
        'recoveryContractPath': ('review/level-b-v2-densified58-fresh-validation-recovery-v2/contract-v2.json', '1370e53bd33cff442be9c4525e7a7dcb7710084f'),
        'recoveryRecordPath': ('review/level-b-v2-densified58-fresh-validation-recovery-v2/recovery-v2.json', '25d6783197d3b5334a277828ce133adaae9d98a3'),
        'evaluatorPath': ('review/level-b-v2-densified58-fresh-validation-recovery-v2/fresh_validation_v2.py', 'a1f81d88fb9099a1b269de598067f7a9e7109537'),
        'manifestBuilderPath': ('experiments/level-b-v2-densified58-fresh-validation-recovery-v2/build_manifest_v2.py', '6a27b9f3a54c079d6ce864c8cd1938f2f9ee83a5'),
        'adapterPath': ('experiments/level-b-v2-densified58-fresh-validation-v1/adapter_v1.py', '5cd736d78c5b82d124b5b95548063677dbfe0ce9'),
        'executorPath': ('experiments/level-b-v2-densified58-fresh-validation-recovery-v2/executor_v2.py', '661f3c3bf4fef94c46eca096fd059f1a124a8e3c'),
    }
    for path_key, (path, sha) in expected_src.items():
        sha_key = path_key.replace('Path', 'GitBlobSha')
        req(src[path_key] == path, f'{path_key} drift')
        req(src[sha_key] == sha, f'{sha_key} drift')
        req(blob(path) == sha, f'live blob drift: {path}')
    req(src['frozenBaseExecutorGitBlobSha'] == '5bf0477f0d5100dcb73da8027233e8415ce9021c', 'base executor binding drift')

    wf = t['workflowBindings']
    req(wf['authorizationReviewWorkflowPath'] == AUTH_WF_REL.as_posix(), 'auth workflow path drift')
    req(wf['authorizationReviewWorkflowGitBlobSha'] == '63816f0c580c45f4415be6ea116fd9c832a42e91', 'auth workflow blob drift')
    req(wf['executionWorkflowPath'] == EXEC_WF_REL.as_posix(), 'execution workflow path drift')
    req(wf['executionWorkflowGitBlobSha'] == '65239aefa4b238e3078c4ec53bc6fc24a278e954', 'execution workflow blob drift')
    req(blob(AUTH_WF_REL.as_posix()) == wf['authorizationReviewWorkflowGitBlobSha'], 'auth workflow live blob drift')
    req(blob(EXEC_WF_REL.as_posix()) == wf['executionWorkflowGitBlobSha'], 'execution workflow live blob drift')

    ident = t['scientificIdentityCandidate']
    req((ident['scientificOrdinal'], ident['authorizationBranch'], ident['dispatchBranch'], ident['executionKey']) == (
        25,
        'authorization/level-b-v2-densified58-fresh-validation-ordinal25-v1',
        'dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1',
        'level-b-v2-densified58:fresh-protected-validation:25',
    ), 'ordinal25 identity drift')
    req(ident['reservedSeeds'] == list(range(2101000025,2101000049)), 'ordinal25 seed drift')
    req((ident['geometryCount'],ident['caseCount'],ident['configuredPhotonHistories']) == (6,24,960_000_000), 'ordinal25 accounting drift')

    old = t['ordinal24ImmutableRefusal']
    req((old['authorizationHeadSha'],old['authorizationPullRequest'],old['allocationMarkerCommentId'],old['dispatchRunId']) == (
        '520ff3cc5f8fee2defc1a0a950bfa7a40974479c',194,5298149901,31840757436
    ), 'ordinal24 refusal binding drift')
    req(old['dispatchRunAttempt']==1 and old['dispatchRunConclusion']=='failure', 'ordinal24 run state drift')
    req(old['syntaxCheckCount']==0 and old['solverExecutionCount']==0 and old['protectedValuesRead'] is False, 'ordinal24 exposure drift')
    req(old['scientificIdentityConsumed'] is True and old['retiredSeeds']==list(range(2101000001,2101000025)), 'ordinal24 retirement drift')

    science=t['frozenScience']
    req(science['sixGeometrySourceUnchanged'] is True and science['definitionOfDoneUnchanged'] is True and science['physicsInputsUnchanged'] is True and science['runtimeIdentityUnchanged'] is True, 'frozen science drift')
    req(science['modelSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7', 'model drift')
    req(science['representationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763', 'representation drift')
    req(science['modelRetuningAuthorized'] is False and science['geometryRetuningAuthorized'] is False and science['definitionOfDoneChangeAuthorized'] is False, 'retuning boundary opened')
    req(all(v is False for v in t['reviewSurface'].values()), 'review surface opened')

    auth_text=(ROOT/AUTH_WF_REL).read_text(encoding='utf-8')
    exec_text=(ROOT/EXEC_WF_REL).read_text(encoding='utf-8')
    req("authorization/level-b-v2-densified58-fresh-validation-ordinal25-v1" in auth_text, 'auth trigger identity missing')
    req("dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1" in exec_text, 'dispatch trigger identity missing')
    req("ref: ${{ github.event.pull_request.head.sha }}" in auth_text, 'auth checkout is not exact PR head')
    req('GITHUB_SHA' not in auth_text, 'auth workflow reintroduced merge-ref GITHUB_SHA identity')
    req('executor_v2.py' in exec_text and 'build_manifest_v2.py' in exec_text and 'fresh_validation_v2.py evaluate' in exec_text, 'v2 execution surface not bound')
    req('workflow_dispatch:' not in auth_text and 'workflow_dispatch:' not in exec_text, 'manual dispatch surface present')
    req('schedule:' not in auth_text and 'schedule:' not in exec_text, 'scheduled dispatch surface present')
    if require_review_inert:
        req(not (ROOT/AUTH_REL).exists(), 'authorization file present during transport review')

    return {
        'status':'PASS',
        'transportId':t['transportId'],
        'scientificOrdinal':25,
        'reservedSeedCount':24,
        'authorizationFilePresent':(ROOT/AUTH_REL).exists(),
        'protectedValuesRead':False,
        'scientificSolverExecutionAuthorizedByTransportReview':False,
    }


def main() -> int:
    ap=argparse.ArgumentParser();ap.add_argument('--require-review-inert',action='store_true');args=ap.parse_args()
    try:
        print(json.dumps(validate(args.require_review_inert),sort_keys=True));return 0
    except Exception as error:
        print(json.dumps({'status':'REFUSED','reason':str(error)},sort_keys=True));return 2


if __name__=='__main__':
    raise SystemExit(main())
