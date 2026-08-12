#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'training-continuation-transport-v1'))
from common_v1 import canon,load,require,verify_self
CONTRACT_SHA='0c3cc4fb8cbf56f9975b0957e1a8b3429310e23c7aae20d6020f1dbb7803384a'
AUTH_BRANCH='authorization/training-continuation-train0014-ordinal18'; DISPATCH_BRANCH='dispatch/training-continuation-train0014-ordinal18'; AUTH_PATH='experiments/training-continuation-train0014-ordinal18-activation-v1/authorization.ordinal18.json'; AUTH_REVIEW_WORKFLOW='.github/workflows/training-continuation-train0014-ordinal18-authorization-review.yml'; EXECUTION_WORKFLOW='.github/workflows/training-continuation-train0014-ordinal18-execution.yml'
MARKER_RE=re.compile(r'^ORDINAL18_TRAIN0014_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$',re.I); ORDINAL_RE=re.compile(r'ordinal[-_]?([1-9][0-9]*)',re.I)

def verify_contract(c): verify_self(c,'activationContractSha256'); require(c['activationContractSha256']==CONTRACT_SHA and c.get('status')=='REVIEW_ONLY_ACTIVATION_NOT_AUTHORIZED','activation contract drift')
def validate_auth(a,c,main):
    verify_self(a,'authorizationSha256'); expected={'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'variant':'train0014','authorizationOrdinal':18,'executionKey':c['executionKey'],'runTitle':c['runTitle'],'authorizationBranch':AUTH_BRANCH,'dispatchBranch':DISPATCH_BRANCH,'exactAuthorizationParentCommit':main,'exactAuthorizationCommit':None,'preregistrationSha256':c['bindings']['preregistrationSha256'],'executionManifestSha256':c['bindings']['executionManifestSha256'],'analysisContractSha256':c['bindings']['analysisContractSha256'],'transportContractSha256':c['bindings']['transportContractSha256'],'activationContractSha256':c['activationContractSha256'],'runtimeIdentitySha256':c['bindings']['runtimeIdentitySha256'],'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'automaticDispatch':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'trainingAdmissionAuthorized':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False}; require({k:v for k,v in a.items() if k!='authorizationSha256'}==expected,'authorization exact surface drift')
def prior_ordinals(branches,runs):
    vals=[]
    for n in [str(x.get('name') or '') for x in branches]+[str(x.get('head_branch') or '') for x in runs if x.get('event')=='push']:
        if n==DISPATCH_BRANCH: continue
        if n.startswith('dispatch/'):
            m=ORDINAL_RE.search(n)
            if m: vals.append(int(m.group(1)))
    return vals

def review(a,c,ctx):
    verify_contract(c); require(ctx.get('eventName')=='push' and ctx.get('runAttempt')==1 and ctx.get('refName')==DISPATCH_BRANCH,'execution must be exact attempt-1 dispatch push'); head=ctx.get('headSha'); main=ctx.get('liveMain'); require(isinstance(head,str) and len(head)==40 and isinstance(main,str) and len(main)==40,'SHA context missing'); require(ctx.get('dispatchBranchHeadSha')==head and ctx.get('authorizationParent')==main,'dispatch/auth parent drift'); require(ctx.get('changedFiles')==[AUTH_PATH],'dispatch head must be one-file authorization child'); validate_auth(a,c,main)
    pr=ctx.get('pr') or {}; require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR must remain Draft/open'); require(pr.get('headSha')==head and pr.get('headBranch')==AUTH_BRANCH and pr.get('baseSha')==main,'authorization PR identity drift')
    rr=ctx.get('authorizationReview') or {}; require(rr.get('workflow')==AUTH_REVIEW_WORKFLOW and rr.get('headSha')==head and rr.get('prNumber')==pr.get('number'),'authorization review identity drift'); require(rr.get('runAttempt')==1 and rr.get('status')=='completed' and rr.get('conclusion')=='success','authorization review not successful attempt 1'); require(rr.get('scientificRuntimeSetupPerformed') is False and rr.get('scientificExecutionPerformed') is False,'authorization review crossed runtime boundary')
    branches=ctx.get('branches') or []; names=[str(x.get('name') or '') for x in branches]; require(names.count(AUTH_BRANCH)==1 and names.count(DISPATCH_BRANCH)==1,'expected exact auth+dispatch refs'); exact=sorted(n for n in names if n.startswith('authorization/training-continuation-train0014-ordinal') or n.startswith('dispatch/training-continuation-train0014-ordinal')); require(exact==sorted([AUTH_BRANCH,DISPATCH_BRANCH]),f'unexpected train0014 auth/dispatch refs: {exact}');
    for n in (AUTH_BRANCH,DISPATCH_BRANCH): require((next(x for x in branches if x.get('name')==n).get('commit') or {}).get('sha')==head,f'{n} head drift')
    current=int(ctx.get('currentRunId') or 0); prior=[]
    for r in (ctx.get('runs') or []):
        if int(r.get('id') or 0)==current: continue
        if r.get('event')=='push' and (r.get('head_branch')==DISPATCH_BRANCH or str(r.get('path') or '').endswith(EXECUTION_WORKFLOW.split('/')[-1])): prior.append(int(r.get('id') or 0))
    require(not prior,f'prior train0014 scientific run exists: {prior}'); bad=[{'id':x.get('id'),'name':x.get('name')} for x in (ctx.get('artifacts') or []) if str(x.get('name') or '').startswith('training-continuation-train0014-case-')]; require(not bad,f'prior case artifact exists: {bad}')
    exact_marker=[]; all_markers=[]
    for x in (ctx.get('issue60Comments') or []):
        body=str(x.get('body') or '').strip(); m=MARKER_RE.fullmatch(body)
        if not m: continue
        all_markers.append(body)
        if m.group(1).lower()==head.lower() and m.group(2).lower()==main.lower() and int(m.group(3))==int(pr.get('number') or 0): exact_marker.append(body)
    require(len(exact_marker)==1 and len(all_markers)==1,'expected exactly one globally unique exact ordinal18 train0014 marker'); ords=prior_ordinals(branches,ctx.get('runs') or []); require(ords and max(ords)==17,'latest prior scientific ordinal is not exactly 17'); require(ctx.get('mainAuthorizationPathPresent') is False,'authorization path exists on main')
    out={'schemaVersion':1,'status':'EXECUTION_GUARD_PASSED_READY_FOR_4_CASES','authorizationOrdinal':18,'authorizationHead':head,'authorizationParent':main,'prNumber':pr.get('number'),'latestPriorConsumedScientificOrdinal':17,'caseCount':4,'runtimeIdentitySha256':c['bindings']['runtimeIdentitySha256'],'scientificRuntimeSetupAuthorizedAfterThisGuard':True,'scientificExecutionAuthorizedAfterThisGuard':True,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'automaticTrainingAdmission':False}; out['guardSha256']=canon(out); return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--authorization',type=Path,required=True); p.add_argument('--contract',type=Path,required=True); p.add_argument('--context',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=review(load(a.authorization),load(a.contract),load(a.context)); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o,sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e),'scientificExecutionPerformed':False},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
