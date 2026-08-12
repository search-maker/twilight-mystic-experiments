#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'training-continuation-transport-v1'))
from common_v1 import canon,load,require,verify_self
CONTRACT_SHA='0c3cc4fb8cbf56f9975b0957e1a8b3429310e23c7aae20d6020f1dbb7803384a'
AUTH_BRANCH='authorization/training-continuation-train0014-ordinal18'
DISPATCH_BRANCH='dispatch/training-continuation-train0014-ordinal18'
AUTH_PATH='experiments/training-continuation-train0014-ordinal18-activation-v1/authorization.ordinal18.json'
EXECUTION_WORKFLOW='.github/workflows/training-continuation-train0014-ordinal18-execution.yml'
MARKER_RE=re.compile(r'^ORDINAL18_TRAIN0014_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=[0-9a-f]{40} parent=[0-9a-f]{40} pr=[1-9][0-9]*$',re.I)
ORDINAL_RE=re.compile(r'ordinal[-_]?([1-9][0-9]*)',re.I)

def verify_contract(c):
    verify_self(c,'activationContractSha256'); require(c['activationContractSha256']==CONTRACT_SHA,'activation contract identity drift'); require(c.get('status')=='REVIEW_ONLY_ACTIVATION_NOT_AUTHORIZED','activation status drift')

def validate_auth(a,c,main):
    verify_self(a,'authorizationSha256')
    expected={
      'schemaVersion':1,'status':'AUTHORIZED_PENDING_SEPARATE_DISPATCH','enabled':True,'variant':'train0014','authorizationOrdinal':18,
      'executionKey':c['executionKey'],'runTitle':c['runTitle'],'authorizationBranch':AUTH_BRANCH,'dispatchBranch':DISPATCH_BRANCH,
      'exactAuthorizationParentCommit':main,'exactAuthorizationCommit':None,
      'preregistrationSha256':c['bindings']['preregistrationSha256'],'executionManifestSha256':c['bindings']['executionManifestSha256'],'analysisContractSha256':c['bindings']['analysisContractSha256'],'transportContractSha256':c['bindings']['transportContractSha256'],'activationContractSha256':c['activationContractSha256'],'runtimeIdentitySha256':c['bindings']['runtimeIdentitySha256'],
      'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'automaticDispatch':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False,'trainingAdmissionAuthorized':False,'modelFittingAuthorized':False,'modelSelectionAuthorized':False,'holdoutValidationOpeningAuthorized':False,'tier2Authorized':False,'productionPromotionAuthorized':False,
    }
    bare={k:v for k,v in a.items() if k!='authorizationSha256'}; require(bare==expected,'authorization exact field/value surface drift')

def prior_ordinals(branches,runs):
    vals=[]
    for n in [str(x.get('name') or '') for x in branches]+[str(x.get('head_branch') or '') for x in runs if x.get('event')=='push']:
        if n in (AUTH_BRANCH,DISPATCH_BRANCH): continue
        if n.startswith('dispatch/'):
            m=ORDINAL_RE.search(n)
            if m: vals.append(int(m.group(1)))
    return vals

def review(auth,c,ctx):
    verify_contract(c); require(ctx.get('eventName')=='pull_request' and ctx.get('runAttempt')==1,'authorization review must be attempt-1 pull_request')
    require(ctx.get('headBranch')==AUTH_BRANCH,'wrong authorization branch'); head=ctx.get('headSha'); main=ctx.get('liveMain'); require(isinstance(head,str) and len(head)==40 and isinstance(main,str) and len(main)==40,'SHA context missing')
    validate_auth(auth,c,main); require(ctx.get('authorizationParent')==main,'authorization parent is not live main'); require(ctx.get('changedFiles')==[AUTH_PATH],'authorization must be one-file child')
    pre=ctx.get('freshPreauthorization') or {}; require(pre.get('status')=='PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED' and pre.get('variant')=='train0014','fresh preauthorization not clean'); require(pre.get('latestConsumedScientificOrdinal')==17 and pre.get('nextAvailableScientificOrdinalIfAllocatedLater')==18,'ordinal 18 is no longer fresh'); require(not any((pre.get('seedCollisions') or {}).values()),'fresh preauthorization seed collision')
    pr=ctx.get('pr') or {}; require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR must remain Draft/open'); require(pr.get('headSha')==head and pr.get('headBranch')==AUTH_BRANCH and pr.get('baseSha')==main,'authorization PR identity drift')
    branches=ctx.get('branches') or []; names=[str(x.get('name') or '') for x in branches]; require(names.count(AUTH_BRANCH)==1 and DISPATCH_BRANCH not in names,'authorization/dispatch branch freshness drift'); row=next(x for x in branches if x.get('name')==AUTH_BRANCH); require((row.get('commit') or {}).get('sha')==head,'authorization branch head drift')
    runs=ctx.get('runs') or []; current=int(ctx.get('currentRunId') or 0); prior=[]
    for r in runs:
        if int(r.get('id') or 0)==current: continue
        if r.get('event')=='push' and (r.get('head_branch')==DISPATCH_BRANCH or str(r.get('path') or '').endswith(EXECUTION_WORKFLOW.split('/')[-1])): prior.append(int(r.get('id') or 0))
    require(not prior,f'prior train0014 scientific run exists: {prior}')
    bad=[{'id':x.get('id'),'name':x.get('name')} for x in (ctx.get('artifacts') or []) if str(x.get('name') or '').startswith('training-continuation-train0014-case-')]; require(not bad,f'prior train0014 case artifact exists: {bad}')
    markers=[str(x.get('body') or '').strip() for x in (ctx.get('issue60Comments') or []) if MARKER_RE.fullmatch(str(x.get('body') or '').strip())]; require(not markers,'ordinal18 train0014 marker already exists')
    ords=prior_ordinals(branches,runs); require(ords and max(ords)==17,'latest prior scientific ordinal is not exactly 17'); require(ctx.get('mainAuthorizationPathPresent') is False,'authorization path already exists on main')
    out={'schemaVersion':1,'status':'AUTHORIZATION_REVIEW_PASSED_NOT_DISPATCHED','authorizationOrdinal':18,'authorizationHead':head,'authorizationParent':main,'prNumber':pr.get('number'),'latestPriorConsumedScientificOrdinal':17,'runtimeIdentitySha256':c['bindings']['runtimeIdentitySha256'],'scientificRuntimeSetupPerformed':False,'scientificExecutionPerformed':False,'dispatchBranchPresent':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False}; out['reviewSha256']=canon(out); return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--authorization',type=Path,required=True); p.add_argument('--contract',type=Path,required=True); p.add_argument('--context',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=review(load(a.authorization),load(a.contract),load(a.context)); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o,sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e),'scientificExecutionPerformed':False},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
