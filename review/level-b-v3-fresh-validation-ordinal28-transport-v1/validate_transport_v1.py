#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
TRANSPORT=ROOT/'review/level-b-v3-fresh-validation-ordinal28-transport-v1/transport-v1.json'
AUTH=ROOT/'review/level-b-v3-fresh-validation-ordinal28-transport-v1/authorization.json'
GUARD=ROOT/'review/level-b-v3-fresh-validation-ordinal28-transport-v1/allocation_guard_v1.py'
AUTH_WF=ROOT/'.github/workflows/level-b-v3-fresh-validation-ordinal28-authorization-review-v1.yml'
EXEC_WF=ROOT/'.github/workflows/level-b-v3-fresh-validation-ordinal28-execution-v1.yml'

class Refusal(RuntimeError):pass

def req(c:bool,m:str)->None:
    if not c:raise Refusal(m)
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding='utf-8'));req(isinstance(v,dict),f'object required: {p}');return v
def blob(p:str)->str:return subprocess.check_output(['git','rev-parse',f'HEAD:{p}'],cwd=ROOT,text=True).strip()
def module(name:str,p:Path):
    s=importlib.util.spec_from_file_location(name,p);req(s is not None and s.loader is not None,f'cannot load {p}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def validate(require_review_inert:bool)->dict[str,Any]:
    t=load(TRANSPORT)
    req((t.get('schemaVersion'),t.get('transportId'),t.get('status'),t.get('governance'),t.get('sourceMainAtTransportFreeze'))==(1,'level-b-v3-fresh-validation-ordinal28-transport-v1','REVIEW_ONLY_ORDINAL28_AUTHORIZATION_LOCK_AND_DISPATCH_TRANSPORT_NO_AUTHORIZATION_NO_ALLOCATION','MYSTIC-STATE-0072','969748e765fafd68d8876f1c1bd311b0fd712031'),'transport identity drift')
    ib=t['implementationBindings']; expected={
      'contractPath':('review/level-b-v3-fresh-validation-implementation-v1/contract-v1.json','2ff6850b3018c2bf8cc2ad84dec0e01055ad9623'),
      'evaluatorPath':('review/level-b-v3-fresh-validation-implementation-v1/fresh_validation_v1.py','93f34f226dad3004d921b9beae00706157a22be6'),
      'freshnessAuditPath':('review/level-b-v3-fresh-validation-implementation-v1/freshness_v1.py','403f36fd98c2add500c0b8aeb4a5f2b016ba255a'),
      'manifestBuilderPath':('experiments/level-b-v3-fresh-validation-v1/build_manifest_v1.py','0f7244e8a187f1fc1f92d1b3466cfc9af7c0f26d'),
      'adapterPath':('experiments/level-b-v3-fresh-validation-v1/adapter_v1.py','4c4e5e23c86c1a97241ebdaca8ee5f59229bcdb4'),
      'executorPath':('experiments/level-b-v3-fresh-validation-v1/executor_v1.py','86bef9c12c71559d972fa6190747224c1f84716c'),
      'futureSourcePath':('review/level-b-v3-future-fresh-validation-source-v1/contract-v1.json','105b1560dbb1dacaba891a6828ca04a28d756e6b')}
    for k,(p,sha) in expected.items():
        sk=k.replace('Path','GitBlobSha');req(ib[k]==p and ib[sk]==sha,f'{k} binding drift');req(blob(p)==sha,f'live implementation blob drift: {p}')
    tb=t['transportBindings']; pairs={
      'allocationGuardPath':('review/level-b-v3-fresh-validation-ordinal28-transport-v1/allocation_guard_v1.py','2e6854078f70fed7b0e9140d1185184da1e0087c'),
      'authorizationReviewWorkflowPath':('.github/workflows/level-b-v3-fresh-validation-ordinal28-authorization-review-v1.yml','0be5a2b65fcd56da409ce71c6454d86087bb0acf'),
      'executionWorkflowPath':('.github/workflows/level-b-v3-fresh-validation-ordinal28-execution-v1.yml','5123b299df83f00eb906689038ae60fbee88e10e'),
      'syntheticEvaluatePath':('review/level-b-v3-fresh-validation-ordinal28-transport-v1/synthetic_evaluate_v1.py','4c0b5de12879d5610a90da39a8bf3f1251770197')}
    for k,(p,sha) in pairs.items():
        sk=k.replace('Path','GitBlobSha');req(tb[k]==p and tb[sk]==sha,f'{k} binding drift');req(blob(p)==sha,f'live transport blob drift: {p}')
    ident=t['scientificIdentityCandidate'];req((ident['scientificOrdinal'],ident['authorizationBranch'],ident['allocationLockBranch'],ident['dispatchBranch'],ident['executionKey'])==(28,'authorization/level-b-v3-fresh-validation-ordinal28-v1','allocation/level-b-v3-fresh-validation-ordinal28-v1','dispatch/level-b-v3-fresh-validation-ordinal28-v1','level-b-v3:fresh-protected-validation:28'),'ordinal28 identity drift');req(ident['reservedSeeds']==list(range(2110000001,2110000025)),'ordinal28 seed drift');req((ident['geometryCount'],ident['caseCount'],ident['configuredPhotonHistories'])==(6,24,960_000_000),'ordinal28 accounting drift')
    a=t['allocationProtocol'];req(a['ownershipPrimitive']=='ATOMIC_GIT_BRANCH_REF' and a['allocationLockRequiredBeforeMarkerWrite'] and a['allocationLockMustPointToExactAuthorizationHead'] and a['onlySuccessfulLockCreatorShouldWriteMarker'],'allocation lock semantics drift');req(a['minimumExactMarkerCopies']==1 and a['duplicateByteIdenticalMarkerCopiesAllowed'] and a['anyDistinctOrdinal28AllocationBodyIsRefusal'] and a['dispatchRequiresLockLogicalMarkerAndSoleDispatchRun'],'marker semantics drift')
    guard=module('ordinal28_allocation_guard_static',GUARD);head='0123456789abcdef0123456789abcdef01234567';body=guard.exact_marker(head);one=guard.validate_markers([{'body':body}],head);two=guard.validate_markers([{'body':body},{'body':body}],head);req(one['exactMarkerCopies']==1 and two['exactMarkerCopies']==2,'identical marker copies not idempotent')
    failed=False
    try:guard.validate_markers([{'body':body},{'body':body+'-different'}],head)
    except Exception:failed=True
    req(failed,'distinct marker body did not refuse')
    path=t['artifactTransportContract'];req(path['preflightManifestUploadPath']=='/tmp/o28-manifest.json' and path['uploadedZipMember']=='tmp/o28-manifest.json' and path['caseDownloadRoot']=='/tmp/v0072-o28-preflight' and path['caseManifestPath']=='/tmp/v0072-o28-preflight/tmp/o28-manifest.json' and path['flatCaseManifestPathMustBeAbsent']=='/tmp/v0072-o28-preflight/o28-manifest.json' and path['casePathProofRequiredBeforeRuntimeProbe'] is True and path['flatteningAssumptionAllowed'] is False,'artifact path contract drift')
    fs=t['frozenScience'];req(fs['modelCanonicalSha256']=='c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9' and fs['modelArtifactCanonicalSha256']=='d7f77416c782dd6226be0898f722fb880096638156517177cf1252b96b66f015' and fs['representationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','model/representation drift');req(all(fs[k] is True for k in ('sixGeometrySourceUnchanged','definitionOfDoneUnchangedFromOrdinal27','supportRuleUnchanged','physicsInputsUnchanged','runtimeIdentityUnchanged')),'frozen science drift');req(fs['modelRetuningAuthorized'] is False and fs['geometryRetuningAuthorized'] is False and fs['definitionOfDoneChangeAuthorized'] is False and fs['ordinal27MayInfluenceModelOrEvaluation'] is False,'retuning/leakage opened')
    fr=t['freshnessProtocol'];req(fr['repositoryWideGeometryCollisionAuditRequiredAtReview'] and fr['repositoryWideGeometryCollisionAuditRequiredAgainAtAuthorization'] and fr['repositoryWideGeometryCollisionAuditRequiredAgainAtDispatch'] and fr['collisionOutcome']=='ABANDON_WHOLE_SOURCE_PROTOCOL_NO_POINT_REPLACEMENT' and fr['ordinalAndSeedFreshnessRequiredAtReviewAuthorizationAndDispatch'],'freshness protocol drift')
    req(all(v is False for v in t['reviewSurface'].values()),'review surface opened')
    auth_text=AUTH_WF.read_text(encoding='utf-8');exec_text=EXEC_WF.read_text(encoding='utf-8')
    req('authorization/level-b-v3-fresh-validation-ordinal28-v1' in auth_text,'auth branch trigger missing');req('dispatch/level-b-v3-fresh-validation-ordinal28-v1' in exec_text,'dispatch branch trigger missing');req('allocation_guard_v1.py dispatch' in exec_text,'shared allocation guard missing');req('freshness_v1.py' in auth_text and 'freshness_v1.py' in exec_text,'repeated geometry freshness proof missing');req('executor_v1.py --manifest "$DOWNLOADED_MANIFEST"' in exec_text,'frozen executor path drift');req('fresh_validation_v1.py evaluate' in exec_text,'frozen evaluator path drift');req('DOWNLOADED_MANIFEST: /tmp/v0072-o28-preflight/tmp/o28-manifest.json' in exec_text,'correct manifest env missing');req('test -f "$DOWNLOADED_MANIFEST"' in exec_text and 'test ! -f /tmp/v0072-o28-preflight/o28-manifest.json' in exec_text,'manifest path proof missing');req('github.event.pull_request.head.sha' in auth_text and 'GITHUB_SHA' not in auth_text,'authorization merge-ref regression');req('workflow_dispatch:' not in auth_text and 'workflow_dispatch:' not in exec_text and 'schedule:' not in auth_text and 'schedule:' not in exec_text,'manual/scheduled trigger present')
    req('2110000001-2110000024' in exec_text and 'ordinal=28' in exec_text,'dispatch allocation identity proof missing')
    if require_review_inert:req(not AUTH.exists(),'authorization file present during transport review')
    return {'status':'PASS','transportId':t['transportId'],'scientificOrdinal':28,'reservedSeedCount':24,'authorizationFilePresent':AUTH.exists(),'allocationSemantics':'ATOMIC_LOCK_PLUS_LOGICAL_IDEMPOTENT_MARKER','artifactDownloadedManifestPath':path['caseManifestPath'],'scientificSolverExecutionAuthorizedByTransportReview':False,'protectedValuesRead':False,'ordinal27ValuesRead':False}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--require-review-inert',action='store_true');a=ap.parse_args()
    try:print(json.dumps(validate(a.require_review_inert),sort_keys=True));return 0
    except Exception as e:print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True));return 2
if __name__=='__main__':raise SystemExit(main())
