#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
TRANSPORT=ROOT/'review/level-b-v2-densified58-fresh-validation-ordinal27-transport-v1/transport-v1.json'
AUTH=ROOT/'review/level-b-v2-densified58-fresh-validation-ordinal27-transport-v1/authorization.json'
GUARD=ROOT/'review/level-b-v2-densified58-fresh-validation-ordinal27-transport-v1/allocation_guard_v1.py'
AUTH_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-ordinal27-authorization-review-v1.yml'
EXEC_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-ordinal27-execution-v1.yml'

class Refusal(RuntimeError):pass

def req(c:bool,m:str)->None:
    if not c:raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding='utf-8'));req(isinstance(v,dict),f'object required: {p}');return v
def blob(p:str)->str:return subprocess.check_output(['git','rev-parse',f'HEAD:{p}'],text=True).strip()
def module(name:str,p:Path):
    s=importlib.util.spec_from_file_location(name,p);req(s is not None and s.loader is not None,f'cannot load {p}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def validate(require_review_inert:bool)->dict[str,Any]:
    t=load(TRANSPORT)
    req((t.get('schemaVersion'),t.get('transportId'),t.get('status'),t.get('governance'),t.get('sourceMainAtTransportFreeze'))==(1,'level-b-v2-densified58-fresh-validation-ordinal27-transport-v1','REVIEW_ONLY_ORDINAL27_AUTHORIZATION_LOCK_AND_DISPATCH_TRANSPORT_NO_AUTHORIZATION_NO_ALLOCATION','MYSTIC-STATE-0070','18b0036ce5d4fc38c812f90cacb521f5338cd6c1'),'transport identity drift')
    rb=t['recoveryBindings'];expected={
      'recoveryPath':('review/level-b-v2-densified58-fresh-validation-recovery-v4/recovery-v4.json','6b22421d0f030c947fe9c29c38d7da02362076f3'),
      'contractPath':('review/level-b-v2-densified58-fresh-validation-recovery-v4/contract-v4.json','ce0edbfa40848fd04ee545c0b3047a5cb2fbcd76'),
      'evaluatorPath':('review/level-b-v2-densified58-fresh-validation-recovery-v4/fresh_validation_v4.py','fccabb0a8b426cff033fc4b7d9b101b331fef2c7'),
      'manifestBuilderPath':('experiments/level-b-v2-densified58-fresh-validation-recovery-v4/build_manifest_v4.py','d6205ab89edf308ebc8d04b1dfc28d0e3fa445f2'),
      'executorPath':('experiments/level-b-v2-densified58-fresh-validation-recovery-v4/executor_v4.py','7f789ab13b3371dfc07590395b3ed458c07ad92d'),
      'adapterPath':('experiments/level-b-v2-densified58-fresh-validation-v1/adapter_v1.py','5cd736d78c5b82d124b5b95548063677dbfe0ce9')}
    for k,(p,sha) in expected.items():
        sk=k.replace('Path','GitBlobSha');req(rb[k]==p and rb[sk]==sha,f'{k} binding drift');req(blob(p)==sha,f'live blob drift: {p}')
    req(rb['baseExecutorGitBlobSha']=='5bf0477f0d5100dcb73da8027233e8415ce9021c','base executor drift')
    tb=t['transportBindings'];pairs={
      'allocationGuardPath':('review/level-b-v2-densified58-fresh-validation-ordinal27-transport-v1/allocation_guard_v1.py','f9560010162ea72f3005f5c0e9f2ae99c2cd90f6'),
      'authorizationReviewWorkflowPath':('.github/workflows/level-b-v2-densified58-fresh-validation-ordinal27-authorization-review-v1.yml','0b9f2c03bc14aaa590c67506793d90402668ba6f'),
      'executionWorkflowPath':('.github/workflows/level-b-v2-densified58-fresh-validation-ordinal27-execution-v1.yml','bd5c22dc42fe6ba2ba0e59c3a0db7d7efabea881')}
    for k,(p,sha) in pairs.items():
        sk=k.replace('Path','GitBlobSha');req(tb[k]==p and tb[sk]==sha,f'{k} binding drift');req(blob(p)==sha,f'live transport blob drift: {p}')
    ident=t['scientificIdentityCandidate'];req((ident['scientificOrdinal'],ident['authorizationBranch'],ident['allocationLockBranch'],ident['dispatchBranch'],ident['executionKey'])==(27,'authorization/level-b-v2-densified58-fresh-validation-ordinal27-v1','allocation/level-b-v2-densified58-fresh-validation-ordinal27-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1','level-b-v2-densified58:fresh-protected-validation:27'),'ordinal27 identity drift');req(ident['reservedSeeds']==list(range(2101000073,2101000097)),'ordinal27 seed drift');req((ident['geometryCount'],ident['caseCount'],ident['configuredPhotonHistories'])==(6,24,960_000_000),'ordinal27 accounting drift')
    a=t['allocationProtocol'];req(a['ownershipPrimitive']=='ATOMIC_GIT_BRANCH_REF' and a['allocationLockRequiredBeforeMarkerWrite'] and a['allocationLockMustPointToExactAuthorizationHead'] and a['onlySuccessfulLockCreatorShouldWriteMarker'],'allocation lock semantics drift');req(a['minimumExactMarkerCopies']==1 and a['duplicateByteIdenticalMarkerCopiesAllowed'] and a['anyDistinctOrdinal27AllocationBodyIsRefusal'] and a['dispatchRequiresLockLogicalMarkerAndSoleDispatchRun'],'marker semantics drift')
    guard=module('ordinal27_allocation_guard_static',GUARD);head='0123456789abcdef0123456789abcdef01234567';body=guard.exact_marker(head);one=guard.validate_logical_markers([{'body':body}],head);two=guard.validate_logical_markers([{'body':body},{'body':body}],head);req(one['exactMarkerCopies']==1 and two['exactMarkerCopies']==2,'identical marker copies not idempotent')
    failed=False
    try:guard.validate_logical_markers([{'body':body},{'body':body+'-different'}],head)
    except Exception:failed=True
    req(failed,'distinct marker body did not refuse')
    path=t['artifactTransportContract'];req(path['preflightManifestUploadPath']=='/tmp/o27-manifest.json' and path['uploadedZipMember']=='tmp/o27-manifest.json' and path['caseDownloadRoot']=='/tmp/v0070-o27-preflight' and path['caseManifestPath']=='/tmp/v0070-o27-preflight/tmp/o27-manifest.json' and path['flatCaseManifestPathMustBeAbsent']=='/tmp/v0070-o27-preflight/o27-manifest.json' and path['casePathProofRequiredBeforeRuntimeProbe'] is True and path['flatteningAssumptionAllowed'] is False,'artifact path contract drift')
    fs=t['frozenScience'];req(fs['modelSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7' and fs['representationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','model/representation drift');req(all(fs[k] is True for k in ('sixGeometrySourceUnchanged','definitionOfDoneUnchanged','supportRuleUnchanged','physicsInputsUnchanged','runtimeIdentityUnchanged')),'frozen science drift');req(fs['modelRetuningAuthorized'] is False and fs['geometryRetuningAuthorized'] is False and fs['definitionOfDoneChangeAuthorized'] is False,'retuning opened');req(all(v is False for v in t['reviewSurface'].values()),'review surface opened')
    auth_text=AUTH_WF.read_text(encoding='utf-8');exec_text=EXEC_WF.read_text(encoding='utf-8');req('authorization/level-b-v2-densified58-fresh-validation-ordinal27-v1' in auth_text,'auth branch trigger missing');req('dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1' in exec_text,'dispatch branch trigger missing');req('allocation_guard_v1.py dispatch' in exec_text,'shared allocation guard not used');req('executor_v4.py' in exec_text and 'build_manifest_v4.py' in exec_text and 'fresh_validation_v4.py evaluate' in exec_text,'v4 execution surface drift');req('DOWNLOADED_MANIFEST: /tmp/v0070-o27-preflight/tmp/o27-manifest.json' in exec_text,'corrected manifest env missing');req('test -f "$DOWNLOADED_MANIFEST"' in exec_text and 'test ! -f /tmp/v0070-o27-preflight/o27-manifest.json' in exec_text,'case path fail-closed proof missing');req('--manifest "$DOWNLOADED_MANIFEST"' in exec_text,'executor does not use corrected manifest path');req('/tmp/v0070-o27-preflight/o27-manifest.json --runtime-report' not in exec_text,'old flat manifest path survived');req('github.event.pull_request.head.sha' in auth_text and 'GITHUB_SHA' not in auth_text,'authorization merge-ref regression');req('workflow_dispatch:' not in auth_text and 'workflow_dispatch:' not in exec_text and 'schedule:' not in auth_text and 'schedule:' not in exec_text,'manual/scheduled trigger present')
    if require_review_inert:req(not AUTH.exists(),'authorization file present during transport review')
    return {'status':'PASS','transportId':t['transportId'],'scientificOrdinal':27,'reservedSeedCount':24,'authorizationFilePresent':AUTH.exists(),'allocationSemantics':'ATOMIC_LOCK_PLUS_LOGICAL_IDEMPOTENT_MARKER','artifactDownloadedManifestPath':path['caseManifestPath'],'scientificSolverExecutionAuthorizedByTransportReview':False,'protectedValuesRead':False}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--require-review-inert',action='store_true');a=ap.parse_args()
    try:print(json.dumps(validate(a.require_review_inert),sort_keys=True));return 0
    except Exception as e:print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
