#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p):
    x=json.loads(Path(p).read_text()); req(isinstance(x,dict),f'object required: {p}'); return x
def evaluate(contract,manifest,auth,review_guard,ctx):
    req(set(auth)==set(contract['authorization']['expectedFieldNames']),'authorization exact field surface drift')
    ordinal=auth.get('scientificOrdinal'); req(isinstance(ordinal,int) and ordinal>0,'authorization ordinal invalid')
    dispatch=contract['authorization']['dispatchBranchTemplate'].format(scientificOrdinal=ordinal); auth_branch=contract['authorization']['authorizationBranchTemplate'].format(scientificOrdinal=ordinal); key=contract['authorization']['executionKeyTemplate'].format(scientificOrdinal=ordinal)
    req(ctx.get('eventName')=='push' and ctx.get('runAttempt')==1 and ctx.get('refName')==dispatch,'not exact attempt-1 dispatch push')
    req(ctx.get('headSha')==ctx.get('authorizationCommitSha'),'dispatch head must equal reviewed authorization commit')
    req(ctx.get('parentSha')==ctx.get('liveMain')==auth.get('exactAuthorizationParentCommit'),'live main moved since authorization parent')
    req(ctx.get('changedFiles')==[contract['authorization']['path']],'dispatch head must be one-purpose authorization commit')
    req(auth.get('status')=='AUTHORIZED_PENDING_SEPARATE_DISPATCH' and auth.get('enabled') is True and auth.get('scientificExecutionAuthorized') is True and auth.get('dispatchAuthorized') is True,'authorization not enabled for stage1')
    req(auth.get('dispatchBranch')==dispatch and auth.get('authorizationBranch')==auth_branch and auth.get('executionKey')==key,'authorization identity drift')
    req(auth.get('manifestSha256')==manifest.get('manifestSha256') and auth.get('transportContractSha256')==contract.get('contractSha256'),'authorization payload binding drift')
    for k in ('automaticDispatch','githubRerunAllowed','retryAllowed','resumeAllowed','solverExecutionPerformed','protectedHoldoutOpeningAuthorized','modelFittingAuthorized','modelSelectionAuthorized','productionPromotionAuthorized','stage2Authorized'): req(auth.get(k) is False,f'closed boundary drift: {k}')
    req(review_guard.get('status')=='AUTHORIZATION_IDENTITY_REVIEW_PASSED_DISPATCH_NOT_YET_CREATED' and review_guard.get('candidateScientificOrdinal')==ordinal and review_guard.get('executionKey')==key and review_guard.get('authorizationBranch')==auth_branch and review_guard.get('dispatchBranch')==dispatch and review_guard.get('manifestSha256')==manifest['manifestSha256'] and review_guard.get('transportContractSha256')==contract['contractSha256'] and review_guard.get('authorizationIdentityAllocatedByReviewedCommit') is True and review_guard.get('solverExecutionPerformed') is False and review_guard.get('protectedHoldoutOpeningAuthorized') is False and review_guard.get('stage2Authorized') is False,'authorization review guard evidence drift')
    ar=ctx.get('authorizationReview') or {}; req(ar.get('headSha')==ctx.get('headSha') and ar.get('headBranch')==auth_branch and ar.get('runAttempt')==1 and ar.get('status')=='completed' and ar.get('conclusion')=='success','exact authorization review attempt-1 success missing')
    pr=ctx.get('authorizationPr') or {}; req(pr.get('state')=='open' and pr.get('headSha')==ctx.get('headSha') and pr.get('headBranch')==auth_branch and pr.get('merged') is False,'authorization PR identity/merge state drift')
    tracked=ctx.get('trackedSeedAudit') or {}; req(tracked.get('status')=='PASSED_EXACT_HEAD_TRACKED_TREE_100_SEED_NEGATIVE_COLLISION_CHECK' and tracked.get('repoHead')==ctx.get('headSha') and tracked.get('externalCollisionCount')==0,'fresh dispatch seed audit failed')
    req(ctx.get('mainAuthorizationPathPresent') is False,'authorization path unexpectedly exists on main')
    current=int(ctx.get('currentRunId') or 0); runs=ctx.get('runs',[]); prior=[r for r in runs if r.get('head_branch')==dispatch and int(r.get('id') or 0)!=current]; req(not prior,f'prior dispatch run exists: {[r.get("id") for r in prior]}')
    prefixes=('tier2-stage1-case-','tier2-stage1-preflight','tier2-stage1-aggregate','tier2-stage1-audit','tier2-stage1-handoff')
    arts=[a for a in ctx.get('artifacts',[]) if str(a.get('name') or '').startswith(prefixes)]; req(not arts,f'prior scientific artifact exists: {[(a.get("id"),a.get("name")) for a in arts[:8]]}')
    marker=re.compile(rf'^ORDINAL{ordinal}_TIER2_STAGE1_DISPATCH_CONSUMED\b',re.I); req(not any(marker.search(str(c.get('body') or '').strip()) for c in ctx.get('issue60Comments',[])),'dispatch consumed marker already exists')
    out={'schemaVersion':1,'guardId':'public-tier2-v1-core-stage1-execution-guard-v1','status':'EXACT_ONE_USE_STAGE1_DISPATCH_AUTHORIZED','scientificOrdinal':ordinal,'executionKey':key,'authorizationCommitSha':ctx['headSha'],'manifestSha256':manifest['manifestSha256'],'transportContractSha256':contract['contractSha256'],'workflowRunAttempt':1,'stage1CaseCount':76,'configuredPhotonHistories':2_120_000_000,'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'solverExecutionPermittedNow':True,'protectedHoldoutOpeningAuthorized':False,'stage2Authorized':False,'retryAllowed':False,'resumeAllowed':False,'githubRerunAllowed':False}
    out['guardSha256']=canon(out); return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--contract',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--authorization',type=Path,required=True); p.add_argument('--review-guard',type=Path,required=True); p.add_argument('--context',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=evaluate(load(a.contract),load(a.manifest),load(a.authorization),load(a.review_guard),load(a.context)); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(o['guardSha256']); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
