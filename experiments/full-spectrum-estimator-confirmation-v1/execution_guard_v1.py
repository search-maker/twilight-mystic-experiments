#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

CONTRACT_ID='public-tier1-full-spectrum-estimator-confirmation-v1-ordinal17-transport-v1'
CONTRACT_SHA='cab2d3d2d3bd92727f104b0fc906a51dbde293e0baa5678058ced7305b888c77'
AUTH_BRANCH='authorization/full-spectrum-estimator-confirmation-v1-ordinal17'
DISPATCH_BRANCH='dispatch/full-spectrum-estimator-confirmation-v1-ordinal17'
AUTH_PATH='experiments/full-spectrum-estimator-confirmation-v1/authorization.ordinal17.json'
AUTH_REVIEW_WORKFLOW='.github/workflows/full-spectrum-estimator-confirmation-v1-authorization-review-v1.yml'
EXECUTION_WORKFLOW='.github/workflows/full-spectrum-estimator-confirmation-v1-ordinal17-execution-v1.yml'
RUN_TITLE='Full-spectrum estimator confirmation v1 ordinal 17'
EXECUTION_KEY='full-spectrum-estimator-confirmation-v1:numerical:17'
MARKER_RE=re.compile(r'^ORDINAL17_CONFIRMATION_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$',re.I)
ORDINAL_RE=re.compile(r'ordinal[-_]?([1-9][0-9]*)',re.I)

class Refusal(RuntimeError): pass

def require(c:bool,m:str)->None:
    if not c: raise Refusal(m)

def canon(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text()); require(isinstance(v,dict),f'expected object: {p}'); return v

def verify_contract(c:dict[str,Any])->None:
    require(c.get('contractId')==CONTRACT_ID and c.get('contractSha256')==CONTRACT_SHA,'transport contract identity drift')
    b=dict(c); b['contractSha256']=None
    require(canon(b)==CONTRACT_SHA,'transport contract self-hash mismatch')
    require(c.get('status')=='REVIEW_ONLY_TRANSPORT_NOT_AUTHORIZED','transport contract status drift')
    tb=c.get('transportBoundary') or {}
    require(all(v is False for v in tb.values()),'transport review opened an authorization/downstream boundary')

def validate_authorization(a:dict[str,Any],live_main:str)->None:
    expected={
      'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'authorizationOrdinal':17,
      'executionKey':EXECUTION_KEY,'runTitle':RUN_TITLE,'authorizationBranch':AUTH_BRANCH,'dispatchBranch':DISPATCH_BRANCH,
      'exactAuthorizationParentCommit':live_main,'exactAuthorizationCommit':None,
      'confirmationPreregistrationSha256':'a801000ea0af81a109f9e0e1ec2b28befa0703e4ec47e9f85ee1b10b448a95b6',
      'confirmationExecutionManifestSha256':'9344ed18cfa93849d730cf080fe9f6c4c57f0cc5ea7b1be7ba9aa15d501c3fa8',
      'confirmationAnalysisContractSha256':'08f30045f6f595e5e11cca5401aa4e1ea88862651ed5d7439671a538bc532cc7',
      'transportContractSha256':CONTRACT_SHA,'solverExecutionAuthorized':True,'dispatchAuthorized':False,'automaticDispatch':False,
      'githubRerunAllowed':False,'resumeAllowed':False,'retryAllowed':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,
      'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False,
    }
    require(set(a)==set(expected),'authorization field surface drift')
    for k,v in expected.items(): require(a.get(k)==v,f'authorization value drift: {k}')

def _prior_ordinals(branches:list[dict[str,Any]],runs:list[dict[str,Any]])->list[int]:
    values=[]
    for b in branches:
        name=str(b.get('name') or '')
        if name==DISPATCH_BRANCH: continue
        if name.startswith('dispatch/'):
            m=ORDINAL_RE.search(name)
            if m: values.append(int(m.group(1)))
    for r in runs:
        if r.get('event')!='push': continue
        name=str(r.get('head_branch') or '')
        if name==DISPATCH_BRANCH: continue
        if name.startswith('dispatch/'):
            m=ORDINAL_RE.search(name)
            if m: values.append(int(m.group(1)))
    return values

def review(authorization:dict[str,Any],contract:dict[str,Any],ctx:dict[str,Any])->dict[str,Any]:
    verify_contract(contract)
    require(ctx.get('eventName')=='push' and ctx.get('runAttempt')==1,'execution must be exact attempt-1 push')
    require(ctx.get('refName')==DISPATCH_BRANCH,'wrong dispatch branch')
    head=ctx.get('headSha'); main=ctx.get('liveMain')
    require(isinstance(head,str) and len(head)==40 and isinstance(main,str) and len(main)==40,'execution SHA context missing')
    require(ctx.get('dispatchBranchHeadSha')==head,'dispatch branch head drift')
    require(ctx.get('authorizationParent')==main,'authorization parent is not live main')
    require(ctx.get('changedFiles')==[AUTH_PATH],'dispatch head must be one-file authorization child')
    validate_authorization(authorization,main)

    pr=ctx.get('pr') or {}
    require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR must remain open Draft and unmerged at dispatch')
    require(pr.get('headSha')==head and pr.get('headBranch')==AUTH_BRANCH and pr.get('baseSha')==main,'authorization PR identity drift at dispatch')

    rr=ctx.get('authorizationReview') or {}
    require(rr.get('workflow')==AUTH_REVIEW_WORKFLOW,'authorization-review workflow identity drift')
    require(rr.get('headSha')==head and rr.get('prNumber')==pr.get('number'),'authorization-review head/PR drift')
    require(rr.get('runAttempt')==1 and rr.get('status')=='completed' and rr.get('conclusion')=='success','authorization-review is not exact successful attempt 1')
    require(rr.get('scientificRuntimeSetupPerformed') is False and rr.get('scientificExecutionPerformed') is False,'authorization review performed scientific runtime')

    branches=ctx.get('branches') or []
    names=[str(b.get('name') or '') for b in branches]
    require(names.count(AUTH_BRANCH)==1 and names.count(DISPATCH_BRANCH)==1,'expected exactly one authorization and one dispatch ref')
    exact_candidate_refs=sorted(n for n in names if n.startswith('authorization/full-spectrum-estimator-confirmation-v1-') or n.startswith('dispatch/full-spectrum-estimator-confirmation-v1-'))
    require(exact_candidate_refs==sorted([AUTH_BRANCH,DISPATCH_BRANCH]),f'unexpected confirmation authorization/dispatch refs: {exact_candidate_refs}')
    for expected_name in (AUTH_BRANCH,DISPATCH_BRANCH):
        row=next(b for b in branches if b.get('name')==expected_name)
        require((row.get('commit') or {}).get('sha')==head,f'{expected_name} head drift')

    current_run=int(ctx.get('currentRunId') or 0)
    runs=ctx.get('runs') or []
    prior_scientific=[]
    for r in runs:
        rid=int(r.get('id') or 0)
        if rid==current_run: continue
        path=str(r.get('path') or '')
        if r.get('event')=='push' and (r.get('head_branch')==DISPATCH_BRANCH or path.endswith(EXECUTION_WORKFLOW.split('/')[-1])):
            prior_scientific.append(rid)
    require(not prior_scientific,f'prior confirmation scientific run exists: {prior_scientific}')

    artifacts=ctx.get('artifacts') or []
    bad_artifacts=[{'id':a.get('id'),'name':a.get('name')} for a in artifacts if str(a.get('name') or '').startswith('full-spectrum-estimator-confirmation-v1-case-')]
    require(not bad_artifacts,f'prior confirmation case artifact exists before execution: {bad_artifacts}')

    comments=ctx.get('issue60Comments') or []
    exact=[]
    for c in comments:
        body=str(c.get('body') or '').strip()
        m=MARKER_RE.fullmatch(body)
        if not m: continue
        if m.group(1).lower()==head.lower() and m.group(2).lower()==main.lower() and int(m.group(3))==int(pr.get('number') or 0):
            exact.append(body)
    require(len(exact)==1,'expected exactly one exact ordinal17 confirmation marker')
    all_markers=[str(c.get('body') or '').strip() for c in comments if MARKER_RE.fullmatch(str(c.get('body') or '').strip())]
    require(len(all_markers)==1,'ordinal17 confirmation marker is not globally unique')

    ords=_prior_ordinals(branches,runs)
    require(ords and max(ords)==16,'latest prior consumed scientific ordinal is not exactly 16')
    require(ctx.get('mainAuthorizationPathPresent') is False,'authorization path unexpectedly exists on main')

    out={
      'schemaVersion':1,'status':'EXECUTION_GUARD_PASSED_READY_FOR_24_CASES','authorizationOrdinal':17,
      'authorizationHead':head,'authorizationParent':main,'prNumber':pr.get('number'),
      'latestPriorConsumedScientificOrdinal':16,'priorConfirmationScientificRunCount':0,'priorConfirmationCaseArtifactCount':0,
      'exactMarkerCount':1,'authorizationBranchHeadMatches':True,'dispatchBranchHeadMatches':True,
      'caseCount':24,'scientificRuntimeSetupAuthorizedAfterThisGuard':True,'scientificExecutionAuthorizedAfterThisGuard':True,
      'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'automaticDownstreamTransition':False,
    }
    out['guardSha256']=canon(out)
    return out

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--authorization',type=Path,required=True); p.add_argument('--contract',type=Path,required=True); p.add_argument('--context',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        value=review(load(a.authorization),load(a.contract),load(a.context)); a.output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'); print(json.dumps(value,sort_keys=True)); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e),'scientificExecutionPerformed':False},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
