#!/usr/bin/env python3
from __future__ import annotations

import argparse, copy, hashlib, importlib.util, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
BASE_CONTRACT_REL=Path('review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json')
BASE_CORE_REL=Path('review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py')
RECOVERY_ID='level-b-v2-densified58-fresh-validation-ordinal27-recovery-v4'
EFFECTIVE_CONTRACT_ID='level-b-v2-densified58-fresh-protected-validation-v4-ordinal27-recovery'
EFFECTIVE_STATUS='REVIEW_ONLY_FRESH_PROTECTED_VALIDATION_RECOVERY_V4_NO_AUTHORIZATION_NO_VALUES_OPENED'

class Refusal(RuntimeError):pass

def req(c:bool,m:str)->None:
    if not c:raise Refusal(m)
def canon(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text(encoding='utf-8'));req(isinstance(v,dict),f'object required: {p}');return v
def write(p:Path,v:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
def module(n:str,p:Path):
    s=importlib.util.spec_from_file_location(n,p);req(s is not None and s.loader is not None,f'cannot load {p}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def base_contract(repo_root:Path)->dict[str,Any]:
    b=load(repo_root/BASE_CONTRACT_REL);core=module('fv1_base_v4',repo_root/BASE_CORE_REL);core.validate_contract(b);return b

def validate_recovery(r:dict[str,Any])->None:
    req((r.get('schemaVersion'),r.get('recoveryId'),r.get('status'),r.get('governance'),r.get('sourceMainAtRecoveryFreeze'))==(4,RECOVERY_ID,'REVIEW_ONLY_PREFLIGHT_ARTIFACT_PATH_RECOVERY_FRESH_VALUES_STILL_SEALED','MYSTIC-STATE-0070','55a0698a65d296e93889382e2be42bc49c6a8002'),'recovery identity drift')
    req(r['baseScientificContract']=={'path':BASE_CONTRACT_REL.as_posix(),'gitBlobSha':'aad11350311ce3768488e64ed72edc3e48646ff9'},'base contract binding drift')
    req(r['frozenModel']['modelSha256']=='91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7','model drift');req(r['frozenModel']['representationPackageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','representation drift')
    for key,start,stop,run in (('ordinal24Refusal',2101000001,2101000024,31840757436),('ordinal25Refusal',2101000025,2101000048,31842973699)):
        o=r[key];req(o['dispatchRunId']==run and o['solverExecutionCount']==0 and o['protectedValuesRead'] is False and o['identityConsumed'] is True,key+' refusal drift');req(o['retiredSeeds']==list(range(start,stop+1)),key+' seeds drift')
    o=r['ordinal26Refusal'];req((o['authorizationHeadSha'],o['authorizationPullRequest'],o['authorizationReviewRunId'],o['dispatchRunId'],o['preflightArtifactId'])==('ff530df1f31af39ca26e48b1d953a523bd554c80',201,31844677176,31844855497,9235548762),'ordinal26 identity drift');req(o['preflightConclusion']=='success' and o['caseJobCount']==24 and o['terminalCaseFailureCount']==24 and o['evaluationConclusion']=='skipped' and o['runArtifactCount']==25,'ordinal26 accounting drift');req(o['preflightManifestZipMember']=='tmp/o26-manifest.json' and o['caseManifestPathRequested']=='/tmp/v0070-o26-preflight/o26-manifest.json','ordinal26 path evidence drift');req(o['syntaxCheckCount']==0 and o['solverExecutionCount']==0 and o['protectedValuesRead'] is False and o['ordinal22ValuesRead'] is False and o['identityConsumed'] is True,'ordinal26 exposure drift');req(o['retiredSeeds']==list(range(2101000049,2101000073)),'ordinal26 seeds drift')
    n=r['nextScientificIdentity'];req((n['scientificOrdinal'],n['authorizationBranch'],n['allocationLockBranch'],n['dispatchBranch'],n['executionKey'])==(27,'authorization/level-b-v2-densified58-fresh-validation-ordinal27-v1','allocation/level-b-v2-densified58-fresh-validation-ordinal27-v1','dispatch/level-b-v2-densified58-fresh-validation-ordinal27-v1','level-b-v2-densified58:fresh-protected-validation:27'),'ordinal27 identity drift');req(n['reservedSeeds']==list(range(2101000073,2101000097)),'ordinal27 seeds drift');req((n['geometryCount'],n['blocksPerGeometry'],n['caseCount'],n['photonHistoriesPerBlock'],n['configuredPhotonHistories'])==(6,4,24,40_000_000,960_000_000),'ordinal27 accounting drift');req(n['allocatedAtRecoveryReview'] is False and n['consumedAtRecoveryReview'] is False,'ordinal27 allocated during review')
    a=r['allocationSemantics'];req(a['atomicLockRequiredBeforeMarkerWrite'] and a['allocationLockMustPointToExactAuthorizationHead'] and a['duplicateByteIdenticalMarkerCommentsAllowed'] and a['minimumExactMarkerCopies']==1 and a['distinctMarkerBodiesForSameOrdinalAllowed'] is False and a['dispatchRequiresLockAndLogicalMarker'],'allocation semantics drift')
    t=r['artifactTransportRecovery'];req(t['fixScope']=='CASE_DOWNLOAD_MANIFEST_PATH_ONLY' and t['provenZipMember']=='tmp/o26-manifest.json' and t['futureManifestZipMember']=='tmp/o27-manifest.json' and t['futureDownloadedManifestPath']=='/tmp/v0070-o27-preflight/tmp/o27-manifest.json' and t['flatteningAssumptionAllowed'] is False and t['scientificPayloadChangeAuthorized'] is False,'artifact transport recovery drift')
    req(all(r['frozenScience'][k] is True for k in ('sameSixGeometries','sameModel','sameRepresentation','sameDefinitionOfDone','sameSupportRule','samePhysicsInputs','sameRuntimeIdentity')),'frozen science drift');req(r['frozenScience']['modelRetuningAuthorized'] is False and r['frozenScience']['geometryRetuningAuthorized'] is False and r['frozenScience']['definitionOfDoneChangeAuthorized'] is False,'retuning opened');req(all(v is False for v in r['reviewSurface'].values()),'review surface opened')

def effective_contract(r:dict[str,Any],repo_root:Path)->dict[str,Any]:
    validate_recovery(r);b=base_contract(repo_root);p=copy.deepcopy(b);p['schemaVersion']=4;p['contractId']=EFFECTIVE_CONTRACT_ID;p['status']=EFFECTIVE_STATUS;p['sourceMainAtFreeze']=r['sourceMainAtRecoveryFreeze'];p['executionEnvelope']['candidateScientificOrdinal']=27;p['executionEnvelope']['reservedSeeds']=list(r['nextScientificIdentity']['reservedSeeds']);p['executionEnvelope']['scientificOrdinalAllocated']=False;p['recoveryProvenance']={'recoveryId':RECOVERY_ID,'ordinal24DispatchRunId':31840757436,'ordinal25DispatchRunId':31842973699,'ordinal26DispatchRunId':31844855497,'ordinal24ProtectedValuesRead':False,'ordinal25ProtectedValuesRead':False,'ordinal26ProtectedValuesRead':False,'ordinal24SolverExecutionCount':0,'ordinal25SolverExecutionCount':0,'ordinal26SolverExecutionCount':0,'ordinal26PreflightArtifactId':9235548762,'ordinal26PreflightManifestZipMember':'tmp/o26-manifest.json','nextScientificOrdinal':27,'nextAuthorizationBranch':r['nextScientificIdentity']['authorizationBranch'],'nextAllocationLockBranch':r['nextScientificIdentity']['allocationLockBranch'],'nextDispatchBranch':r['nextScientificIdentity']['dispatchBranch'],'nextExecutionKey':r['nextScientificIdentity']['executionKey'],'artifactPathRecovery':'PRESERVE_TMP_PREFIX_ON_DOWNLOAD'};validate_contract(p,r,repo_root);return p

def validate_contract(p:dict[str,Any],r:dict[str,Any],repo_root:Path)->None:
    validate_recovery(r);b=base_contract(repo_root);req((p.get('schemaVersion'),p.get('contractId'),p.get('status'),p.get('governance'),p.get('sourceMainAtFreeze'))==(4,EFFECTIVE_CONTRACT_ID,EFFECTIVE_STATUS,'MYSTIC-STATE-0070',r['sourceMainAtRecoveryFreeze']),'effective identity drift')
    for k in ('authorization','boundaries','failureSemantics','geometrySelection','modelAndEvaluation','runtimeIdentityRequired','sourceBindings'):req(p[k]==b[k],f'frozen subtree drift: {k}')
    be=copy.deepcopy(b['executionEnvelope']);ne=copy.deepcopy(p['executionEnvelope'])
    for e in (be,ne):e.pop('candidateScientificOrdinal',None);e.pop('reservedSeeds',None);e.pop('scientificOrdinalAllocated',None)
    req(ne==be,'execution envelope changed beyond identity/seeds');req(p['executionEnvelope']['candidateScientificOrdinal']==27 and p['executionEnvelope']['reservedSeeds']==list(range(2101000073,2101000097)) and p['executionEnvelope']['scientificOrdinalAllocated'] is False,'ordinal27 envelope drift')

def expected_cases(p:dict[str,Any],r:dict[str,Any],repo_root:Path)->list[dict[str,Any]]:
    validate_contract(p,r,repo_root);out=[];seeds=p['executionEnvelope']['reservedSeeds'];i=0
    for g in p['geometrySelection']['selectedGeometries']:
        suffix=str(g['geometryId']).removeprefix('v0070-')
        for block in range(1,5):out.append({'caseId':f'v0070-o27-{suffix}-b{block}','geometryId':g['geometryId'],'block':block,'seed':int(seeds[i]),'photonHistories':40_000_000,'alisSpectralImportanceSamplingNm':550.0});i+=1
    req(i==24 and len({x['caseId'] for x in out})==24,'ordinal27 case construction drift');req([x['seed'] for x in out]==list(range(2101000073,2101000097)),'ordinal27 seed order drift');return out

def patched_base(r:dict[str,Any],repo_root:Path):
    b=module('fv1_reused_v4',repo_root/BASE_CORE_REL);b.validate_contract=lambda p:validate_contract(p,r,repo_root);b.expected_cases=lambda p:expected_cases(p,r,repo_root);return b

def evaluate(r:dict[str,Any],cases_root:Path,model_dir:Path,representation_dir:Path,repo_root:Path,output:Path)->dict[str,Any]:
    p=effective_contract(r,repo_root);b=patched_base(r,repo_root);res=b.evaluate(p,cases_root,model_dir,representation_dir,repo_root,output);res.pop('resultSha256',None);res['schemaVersion']=4;res['stageId']='LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_EVALUATION_V4_ORDINAL27_RECOVERY';res['recoveryId']=RECOVERY_ID;res['scientificOrdinal']=27;res['ordinal24ProtectedValuesRead']=False;res['ordinal25ProtectedValuesRead']=False;res['ordinal26ProtectedValuesRead']=False;res['ordinal24SolverExecutionCount']=0;res['ordinal25SolverExecutionCount']=0;res['ordinal26SolverExecutionCount']=0;res['resultSha256']=canon(res);write(output,res);return res

def main()->int:
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
    for n in ('validate','cases'):
        q=sub.add_parser(n);q.add_argument('--recovery',type=Path,required=True);q.add_argument('--repo-root',type=Path,default=ROOT)
    e=sub.add_parser('evaluate');e.add_argument('--recovery',type=Path,required=True);e.add_argument('--cases-root',type=Path,required=True);e.add_argument('--model-dir',type=Path,required=True);e.add_argument('--representation-dir',type=Path,required=True);e.add_argument('--repo-root',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    try:
        r=load(a.recovery);p=effective_contract(r,a.repo_root)
        if a.cmd=='validate':print(json.dumps({'status':'PASS','recoveryId':RECOVERY_ID,'scientificOrdinal':27,'caseCount':len(expected_cases(p,r,a.repo_root)),'protectedValuesRead':False,'solverExecutionAuthorized':False},sort_keys=True))
        elif a.cmd=='cases':print(json.dumps(expected_cases(p,r,a.repo_root),sort_keys=True,separators=(',',':')))
        else:evaluate(r,a.cases_root,a.model_dir,a.representation_dir,a.repo_root,a.output)
        return 0
    except Exception as error:print(json.dumps({'status':'REFUSED','reason':str(error)},sort_keys=True),file=__import__('sys').stderr);return 2
if __name__=='__main__':raise SystemExit(main())
