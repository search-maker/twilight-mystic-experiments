#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
from typing import Any
from freshness import AUTH_BRANCH, DISPATCH_BRANCH, EXECUTION_KEY, TITLE, validate_preauthorization, validate_authorization_review

HERE=Path(__file__).resolve().parent; CONTRACT=HERE/'transport-contract.v6.json'; BINDING=HERE/'review-binding.v6.json'
SHA40=re.compile(r'^[0-9a-f]{40}$')
class AuthorizationRefusal(RuntimeError): pass
def require(c,m):
    if not c: raise AuthorizationRefusal(m)
def load(p:Path): return json.loads(p.read_text())
def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def selfhash(v,field): x=dict(v);x[field]=None;return hashlib.sha256(canon(x)).hexdigest()
def validate_static():
    c=load(CONTRACT); b=load(BINDING)
    require(c.get('contractSha256')==selfhash(c,'contractSha256'),'contract self-hash mismatch')
    require(b.get('bindingSha256')==selfhash(b,'bindingSha256'),'binding self-hash mismatch')
    return c,b

def validate_enabled_document(auth:dict[str,Any], live_main:str, c:dict[str,Any], b:dict[str,Any]):
    require(auth.get('enabled') is True,'authorization document not enabled')
    require(auth.get('status')=='AUTHORIZED_PENDING_SEPARATE_DISPATCH','authorization status drift')
    require(auth.get('authorizationOrdinal')==14,'authorization ordinal drift')
    require(auth.get('executionKey')==EXECUTION_KEY,'execution key drift')
    require(auth.get('runTitle')==TITLE,'run title drift')
    require(auth.get('authorizationBranch')==AUTH_BRANCH,'authorization branch drift')
    require(auth.get('dispatchBranch')==DISPATCH_BRANCH,'dispatch branch drift')
    require(auth.get('exactAuthorizationParentCommit')==live_main,'authorization parent not live main')
    require(auth.get('exactAuthorizationCommit') is None,'authorization document must not embed own commit SHA')
    require(auth.get('reviewBindingSha256')==b['bindingSha256'],'review binding drift')
    require(auth.get('transportContractSha256')==c['contractSha256'],'transport contract binding drift')
    require(auth.get('solverExecutionAuthorized') is True,'authorization does not authorize solver execution')
    require(auth.get('dispatchAuthorized') is False and auth.get('automaticDispatch') is False,'authorization may not auto-dispatch')
    for key in ('githubRerunAllowed','resumeAllowed','retryAllowed','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'):
        require(auth.get(key) is False,f'forbidden authorization flag {key}')

def review(auth:dict[str,Any], ctx:dict[str,Any])->dict[str,Any]:
    c,b=validate_static(); live=ctx.get('liveMain'); head=ctx.get('headSha'); parent=ctx.get('parentSha'); pr=ctx.get('pr') or {}
    require(isinstance(live,str) and SHA40.fullmatch(live),'live main invalid')
    require(isinstance(head,str) and SHA40.fullmatch(head),'authorization head invalid')
    require(parent==live,'authorization commit parent is not then-live main')
    require(ctx.get('parentCount')==1,'authorization commit must have exactly one parent')
    require(ctx.get('changedPaths')==c['authorizationRules']['changedPathsExactly'],'authorization commit must change exactly one authorization path')
    validate_enabled_document(auth,live,c,b)
    require(pr.get('number',0)>0,'authorization PR number invalid')
    require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR must be Draft/open/unmerged')
    require(pr.get('headBranch')==AUTH_BRANCH and pr.get('baseBranch')=='main','authorization PR branch/base drift')
    require(pr.get('headRepo')==c['repository'] and pr.get('baseRepo')==c['repository'],'authorization PR must be same-repository')
    require(pr.get('headSha')==head,'authorization PR head mismatch')
    require(ctx.get('runAttempt')==1,'authorization review must be attempt 1')
    require(ctx.get('eventName')=='pull_request' and ctx.get('eventAction')=='opened','authorization review must be PR opened event')
    require(ctx.get('scientificRuntimeSetupPerformed') is False,'authorization review may not set up scientific runtime')
    require(ctx.get('scientificExecutionPerformed') is False,'authorization review may not execute scientific process')
    validate_authorization_review(ctx.get('freshness') or {},head)
    return {'status':'AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME','authorizationHead':head,'authorizationParent':parent,'authorizationPr':pr['number'],'scientificExecutionPerformed':False,'ordinalAllocatedReservedOrConsumedByReview':False}

def preauthorize(ctx:dict[str,Any])->dict[str,Any]:
    validate_static(); validate_preauthorization(ctx.get('freshness') or {})
    require(ctx.get('authorizationCreated') is False,'authorization already created')
    require(ctx.get('scientificExecutionPerformed') is False,'scientific execution already occurred')
    return {'status':'PREAUTHORIZATION_FRESHNESS_PASS','authorizationCreationPermitted':True,'scientificExecutionPerformed':False,'ordinalAllocatedReservedOrConsumed':False}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('mode',choices=['preauthorize','review']); ap.add_argument('--context',type=Path,required=True); ap.add_argument('--authorization',type=Path); ap.add_argument('--output',type=Path)
    a=ap.parse_args()
    try:
        ctx=load(a.context); out=preauthorize(ctx) if a.mode=='preauthorize' else review(load(a.authorization),ctx)
        text=json.dumps(out,indent=2,sort_keys=True)+'\n'; a.output.write_text(text) if a.output else print(text,end=''); return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
