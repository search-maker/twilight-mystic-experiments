#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any

PREREG_SHA='a801000ea0af81a109f9e0e1ec2b28befa0703e4ec47e9f85ee1b10b448a95b6'
PILOT_MANIFEST_SHA='be81c717cd943415ac51dc2b5356010b3d584b5279228c525d2defccc4680e0f'
SOURCE_MAIN_SHA='41e4ef5aa42817d7d1d67bb417428671e03eb9d0'
ARTIFACT_PREFIX='full-spectrum-estimator-confirmation-v1-case-'
MANIFEST_ID='public-tier1-full-spectrum-estimator-confirmation-execution-manifest-v1'

class Refusal(RuntimeError): pass

def canon(v: Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def raw_sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text())
    if not isinstance(v,dict): raise Refusal(f'expected object: {p}')
    return v

def verify_prereg(pr:dict[str,Any])->None:
    supplied=pr.get('preregistrationSha256'); t=dict(pr); t['preregistrationSha256']=None
    if supplied!=PREREG_SHA or supplied!=canon(t): raise Refusal('confirmation preregistration identity/self-hash drift')
    if pr.get('status')!='REVIEW_ONLY_FROZEN_BEFORE_ANY_CONFIRMATION_RESULT': raise Refusal('confirmation preregistration status drift')
    xb=pr.get('executionBoundary') or {}
    if xb.get('scientificExecutionAuthorized') is not False or xb.get('workflowDispatchAuthorized') is not False or xb.get('authorizationOrdinalAllocated') is not False: raise Refusal('review-only confirmation boundary drift')

def verify_pilot_manifest(m:dict[str,Any])->None:
    supplied=m.get('manifestSha256')
    if supplied!=PILOT_MANIFEST_SHA or supplied!=canon({k:v for k,v in m.items() if k!='manifestSha256'}): raise Refusal('pilot execution manifest identity/self-hash drift')
    if m.get('caseCount')!=44 or len(m.get('cases') or [])!=44: raise Refusal('pilot case universe drift')

def build(pr:dict[str,Any], pilot:dict[str,Any], repository_root:Path)->dict[str,Any]:
    verify_prereg(pr); verify_pilot_manifest(pilot)
    pilot_by={r['caseId']:r for r in pilot['cases']}
    candidates={c['candidateId']:c for c in pr['candidates']}
    cases=[]
    for frozen in pr['caseDesign']['cases']:
        cand=candidates.get(frozen['candidateId'])
        if cand is None: raise Refusal('confirmation case references unknown candidate')
        source_id=cand['pilotCaseIds'][0]
        source=pilot_by.get(source_id)
        if source is None: raise Refusal(f'source pilot case missing: {source_id}')
        if source.get('geometryId')!=frozen.get('geometryId') or source.get('method')!='alis-alt-importance' or float(source['numericalMethod']['mc_spectral_is_nm'])!=float(frozen['importanceCenterNm']) or source.get('photonHistories')!=frozen.get('photonHistories'):
            raise Refusal(f'confirmation/source pilot method-physics binding drift: {frozen["caseId"]}')
        row=copy.deepcopy(source)
        row['caseId']=frozen['caseId']
        row['replicate']=frozen['confirmationBlock']
        row['seed']=frozen['seed']
        row['requiredCommonDirectives']['mc_randomseed']=frozen['seed']
        row['confirmationBlock']=frozen['confirmationBlock']
        row['candidateId']=frozen['candidateId']
        row['sourcePilotCaseId']=source_id
        row['sourcePilotCasePair']=list(cand['pilotCaseIds'])
        template=repository_root/'review/full-spectrum-estimator-pilot-v2/rendered-review-v5'/source_id/'input-template.txt'
        if not template.is_file(): raise Refusal(f'frozen source pilot input template missing: {source_id}')
        row['sourcePilotInputTemplateSha256']=raw_sha(template)
        cases.append(row)
    if len(cases)!=24 or len({r['caseId'] for r in cases})!=24 or len({r['seed'] for r in cases})!=24: raise Refusal('confirmation case identity/seed count drift')
    if {r['seed'] for r in cases}!=set(range(1600000001,1600000025)): raise Refusal('confirmation seed universe drift')
    required=list(pilot['artifactContract']['requiredMembersByMethod']['alis-alt-importance'])
    artifact_names=[ARTIFACT_PREFIX+r['caseId'] for r in cases]
    out={
      'schemaVersion':1,
      'manifestId':MANIFEST_ID,
      'manifestSha256':None,
      'status':'DISABLED_EXECUTION_PACKAGE_REVIEW_ONLY',
      'sourceBindings':{
        'confirmationPreregistrationId':pr['preregistrationId'],
        'confirmationPreregistrationSha256':PREREG_SHA,
        'pilotExecutionManifestId':pilot['manifestId'],
        'pilotExecutionManifestSha256':PILOT_MANIFEST_SHA,
        'sourceMainShaAtPackageStart':SOURCE_MAIN_SHA,
        'ordinal16ScientificRunId':31546667072,
        'ordinal16PostprocessV8RunId':31556854044,
        'ordinal16ScreeningArtifactId':9126300230,
        'ordinal16ScreeningAnalysisSha256':'69d877c5c90e80dfd0956d73f1790d30129423ab58b6414ac24d776bc2c7120f',
      },
      'caseCount':24,
      'cases':cases,
      'runtimeIdentityRequired':copy.deepcopy(pilot['runtimeIdentityRequired']),
      'artifactContract':{
        'artifactNamePrefix':ARTIFACT_PREFIX,
        'expectedArtifactNames':artifact_names,
        'expectedArtifactNamesSha256':canon(artifact_names),
        'requiredMembersByMethod':{'alis-alt-importance':required},
        'oneImmutableArtifactPerCase':True,
        'workflowRunAttempt':1,
        'syntaxCheckCountExactly':1,
        'solverExecutionCountExactly':1,
        'githubRerunAllowed':False,
        'retryAllowed':False,
        'resumeAllowed':False,
      },
      'executionBoundary':{
        'scientificExecutionAuthorized':False,
        'authorizationOrdinalAllocated':False,
        'dispatchBranchAllocated':False,
        'executionWorkflowPresent':False,
        'modelFittingAuthorized':False,
        'modelSelectionAuthorized':False,
        'holdoutValidationOpeningAuthorized':False,
        'tier2Authorized':False,
        'productionPromotionAuthorized':False,
      },
    }
    out['manifestSha256']=canon({k:v for k,v in out.items() if k!='manifestSha256'})
    return out

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); ap.add_argument('--preregistration',type=Path,required=True); ap.add_argument('--pilot-manifest',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        v=build(load(a.preregistration),load(a.pilot_manifest),a.repository_root.resolve()); a.output.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':'PASSED','manifestSha256':v['manifestSha256'],'caseCount':v['caseCount'],'scientificExecutionAuthorized':False},indent=2,sort_keys=True)); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e),'scientificExecutionAuthorized':False},indent=2,sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
