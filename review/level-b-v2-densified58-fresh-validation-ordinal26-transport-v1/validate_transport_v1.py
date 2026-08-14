#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
TRANSPORT=ROOT/'review/level-b-v2-densified58-fresh-validation-ordinal26-transport-v1/transport-v1.json'
AUTH=ROOT/'review/level-b-v2-densified58-fresh-validation-ordinal26-transport-v1/authorization.json'
GUARD=ROOT/'review/level-b-v2-densified58-fresh-validation-ordinal26-transport-v1/allocation_guard_v1.py'
AUTH_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-ordinal26-authorization-review-v1.yml'
EXEC_WF=ROOT/'.github/workflows/level-b-v2-densified58-fresh-validation-ordinal26-execution-v1.yml'

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
    req((t.get('schemaVersion'),t.get('transportId'),t.get('status'),t.get('governance'),t.get('sourceMainAtTransportFreeze'))==(1,'level-b-v2-densified58-fresh-validation-ordinal26-transport-v1','REVIEW_ONLY_ORDINAL26_AUTHORIZATION_LOCK_AND_DISPATCH_TRANSPORT_NO_AUTHORIZATION_NO_ALLOCATION','MYSTIC-STATE-0070','c5d0e55a55638b1691a746fd95c1f29aeffe5959'),'transport identity drift')
    rb=t['recoveryBindings'];expected={
      'recoveryPath':('review/level-b-v2-densified58-fresh-validation-recovery-v3/recovery-v3.json','bf0020ac268893a9998ed1c868d48b2fef7de961'),
      'contractPath':('review/level-b-v2-densified58-fresh-validation-recovery-v3/contract-v3.json','41a31583fff413b226faab77f108032e5fdf6091'),
      'evaluatorPath':('review/level-b-v2-densified58-fresh-validation-recovery-v3/fresh_validation_v3.py','90137ba43503c17f20e4c919cb020b2252f7e57b'),
      'manifestBuilderPath':('experiments/level-b-v2-densified58-fresh-validation-recovery-v3/build_manifest_v3.py','b670f65039fdbafd5ef2da1fba9bf9750f783fcd'),
      'executorPath':('experiments/level-b-v2-densified58-fresh-validation-recovery-v3/executor_v3.py','57572e7770f83b7d23b55f8011dffdd286efa58d'),
      'adapterPath':('experiments/level-b-v2-densified58-fresh-validation-v1/adapter_v1.py','5cd736d78c5b82d124b5b95548063677dbfe0ce9')}
    for k,(p,sha) in expected.items():
        sk=k.replace('Path','GitBlobSha');req(rb[k]==p and rb[sk]==sha,f'{k} binding drift');req(blob(p)==sha,f'live blob drift: {p}')
    req(rb['baseExecutorGitBlobSha']=='5bf0477f0d5100dcb73da8027233e8415ce9021c','base executor drift')
    tb=t['transportBindings'];pairs={
      'allocationGuardPath':('review/level-b-v2-densified58-fresh-validation-ordinal26-transport-v1/allocation_guard_v1.py','690a173ff8e35767e38d3bd5bf2c6e143c0924db'),
      'authorizationReviewWorkflowPath':('.github/workflows/level-b-v2-densified58-fresh-validation-ordinal26-authorization-review-v1.yml','90bae0881be0454f6cb5aa1cfb4aeff297702285'),
      'executionWorkflowPath':('.github/workflows/level-b-v2-densified58-fresh-validation-ordinal26-execution-v1.yml','014fc632d07004ebec6b82c0845d19c552bf2cd4')}
    for k,(p,sha) in pairs.items():
        sk=k.replace('Path','GitBlobSha');req(tb[k]==p and tb[sk]==sha,f'{k} binding drift');req(blob(p)==sha,f'live transport blob drift: {p}')
    ident=t['scientificIdentityCandidate'];req((ident['scientificOrdinal'],ident['authorizationBranch'],ident['allocationLockBranch'],ident['dispatchBranch'],ident['executionKey'])==(26,'authorization/level-b-v2-densified58-fresh-validation-ordinal26-v1','allocation/level-b-v2-densified58-fresh-validation-ordinal26-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1','level-b-v2-densified58:fresh-protected-validation:26'),'ordinal26 identity drift');req(ident['reservedSeeds']==list(range(2101000049,2101000073)),'ordinal26 seed drift');req((ident['geometryCount'],ident['caseCount'],ident['configuredPhotonHistories'])==(6,24,960_000_000),'ordinal26 accounting drift')
    a=t['allocationProtocol'];req(a['ownershipPrimitive']=='ATOMIC_GIT_BRANCH_REF' and a['allocationLockRequiredBeforeMarkerWrite'] is True and a['allocationLockMustPointToExactAuthorizationHead'] is True and a['onlySuccessfulLockCreatorShouldWriteMarker'] is True,'allocation lock semantics drift');req(a['minimumExactMarkerCopies']==1 and a['duplicateByteIdenticalMarkerCopiesAllowed'] is True and a['anyDistinctOrdinal26AllocationBodyIsRefusal'] is True and a['dispatchRequiresLockLogicalMarkerAndSoleDispatchRun'] is True,'marker semantics drift')
    guard=module('ordinal26_allocation_guard_static',GUARD);head='0123456789abcdef0123456789abcdef01234567';body=guard.exact_marker(head);one=guard.validate_logical_markers([{'body':body}],head);two=guard.validate_logical_markers([{'body':body},{'body':body}],head);req(one['exactMarkerCopies']==1 and two['exactMarkerCopies']==2,'identical marker copies not idempotent')
    failed=False
    try:guard.validate_logical_markers([{'body':body},{'body':body+'-different'}],head)
    except Exception:failed=True
    req(failed,'distinct marker body did not refuse')
    failed=False
    try:guard.validate_logical_markers([],head)
    except Exception:failed=True
    req(failed,'missing marker did not refuse')
    fs=t['frozenScience'];req(fs['modelSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7' and fs['representationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','model/representation drift');req(all(fs[k] is True for k in ('sixGeometrySourceUnchanged','definitionOfDoneUnchanged','supportRuleUnchanged','physicsInputsUnchanged','runtimeIdentityUnchanged')),'frozen science drift');req(fs['modelRetuningAuthorized'] is False and fs['geometryRetuningAuthorized'] is False and fs['definitionOfDoneChangeAuthorized'] is False,'retuning opened');req(all(v is False for v in t['reviewSurface'].values()),'review surface opened')
    auth_text=AUTH_WF.read_text(encoding='utf-8');exec_text=EXEC_WF.read_text(encoding='utf-8');req('authorization/level-b-v2-densified58-fresh-validation-ordinal26-v1' in auth_text,'auth branch trigger missing');req('dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1' in exec_text,'dispatch branch trigger missing');req('allocation_guard_v1.py dispatch' in exec_text,'shared allocation guard not used by execution');req('executor_v3.py' in exec_text and 'build_manifest_v3.py' in exec_text and 'fresh_validation_v3.py evaluate' in exec_text,'v3 execution surface drift');req('github.event.pull_request.head.sha' in auth_text and 'GITHUB_SHA' not in auth_text,'authorization merge-ref regression');req('workflow_dispatch:' not in auth_text and 'workflow_dispatch:' not in exec_text and 'schedule:' not in auth_text and 'schedule:' not in exec_text,'manual/scheduled trigger present')
    if require_review_inert:req(not AUTH.exists(),'authorization file present during transport review')
    return {'status':'PASS','transportId':t['transportId'],'scientificOrdinal':26,'reservedSeedCount':24,'authorizationFilePresent':AUTH.exists(),'allocationSemantics':'ATOMIC_LOCK_PLUS_LOGICAL_IDEMPOTENT_MARKER','scientificSolverExecutionAuthorizedByTransportReview':False,'protectedValuesRead':False}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--require-review-inert',action='store_true');a=ap.parse_args()
    try:print(json.dumps(validate(a.require_review_inert),sort_keys=True));return 0
    except Exception as e:print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
