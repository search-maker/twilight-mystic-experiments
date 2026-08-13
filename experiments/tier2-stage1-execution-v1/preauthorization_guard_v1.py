#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, re
from pathlib import Path
from typing import Any
ORD=re.compile(r'^dispatch/.*ordinal([1-9][0-9]*)',re.I)
NUM=re.compile(r'(?<![0-9_])[0-9_]{7,20}(?![0-9_])')
SHA40=re.compile(r'^[0-9a-f]{40}$')
class Refusal(RuntimeError): pass
def req(c,m):
    if not c: raise Refusal(m)
def canon(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def selfhash(v,field):
    x=copy.deepcopy(v); x[field]=None; return canon(x)
def load(p):
    x=json.loads(Path(p).read_text()); req(isinstance(x,dict),f'object required: {p}'); return x
def consumed_ordinals(branches,runs):
    vals=[]
    for n in [str(x.get('name') or '') for x in branches]+[str(x.get('head_branch') or '') for x in runs if x.get('event')=='push']:
        m=ORD.match(n)
        if m: vals.append(int(m.group(1)))
    return vals
def seed_literals(text,candidates):
    out=[]
    for token in NUM.findall(text):
        s=token.replace('_','')
        if s.isdigit() and int(s) in candidates: out.append(int(s))
    return sorted(set(out))
def evaluate(contract,manifest,ctx):
    req(contract.get('contractSha256')==selfhash(contract,'contractSha256'),'transport contract selfhash drift')
    req(manifest.get('manifestSha256')==selfhash(manifest,'manifestSha256'),'manifest selfhash drift')
    req(ctx.get('eventName')=='pull_request' and ctx.get('runAttempt')==1,'authorization review must be attempt-1 PR')
    auth=ctx.get('authorization') or {}; req(set(auth)==set(contract['authorization']['expectedFieldNames']),'authorization exact field surface drift'); latest_expected=contract['sourceBindings']['latestConsumedScientificOrdinal']; ords=consumed_ordinals(ctx.get('branches',[]),ctx.get('runs',[])); req(ords and max(ords)==latest_expected,'latest consumed scientific ordinal drift')
    candidate=max(ords)+1; req(auth.get('scientificOrdinal')==candidate,'authorization ordinal is not fresh next ordinal')
    expected_branch=contract['authorization']['authorizationBranchTemplate'].format(scientificOrdinal=candidate); dispatch=contract['authorization']['dispatchBranchTemplate'].format(scientificOrdinal=candidate); key=contract['authorization']['executionKeyTemplate'].format(scientificOrdinal=candidate)
    req(auth.get('schemaVersion')==1 and auth.get('status')=='AUTHORIZED_PENDING_SEPARATE_DISPATCH' and auth.get('enabled') is True,'authorization header drift')
    req(auth.get('authorizationBranch')==expected_branch and auth.get('dispatchBranch')==dispatch and auth.get('executionKey')==key,'authorization identity drift')
    req(auth.get('manifestSha256')==manifest['manifestSha256'] and auth.get('transportContractSha256')==contract['contractSha256'],'authorization payload binding drift')
    for k in ('scientificExecutionAuthorized','dispatchAuthorized'): req(auth.get(k) is True,f'{k} must be true in reviewed authorization')
    for k in ('automaticDispatch','githubRerunAllowed','retryAllowed','resumeAllowed','solverExecutionPerformed','protectedHoldoutOpeningAuthorized','modelFittingAuthorized','modelSelectionAuthorized','productionPromotionAuthorized','stage2Authorized'):
        req(auth.get(k) is False,f'closed authorization boundary drift: {k}')
    req(ctx.get('headBranch')==expected_branch and ctx.get('headSha')==ctx.get('pr',{}).get('headSha') and ctx.get('parentSha')==ctx.get('liveMain')==ctx.get('pr',{}).get('baseSha'),'authorization exact-head/main binding drift')
    req(auth.get('exactAuthorizationParentCommit')==ctx.get('parentSha'),'authorization parent binding drift')
    req(ctx.get('changedFiles')==[contract['authorization']['path']],'authorization commit must change exact one file')
    req(ctx.get('mainAuthorizationPathPresent') is False,'authorization path already exists on main')
    req(ctx.get('pr',{}).get('state')=='open' and ctx.get('pr',{}).get('draft') is True,'authorization PR must remain draft during review')
    branches=ctx.get('branches',[]); auth_matches=[b for b in branches if b.get('name')==expected_branch]; req(len(auth_matches)==1 and (auth_matches[0].get('commit') or {}).get('sha')==ctx.get('headSha'),'authorization branch/head not exact unique'); req(not any(b.get('name')==dispatch for b in branches),'dispatch branch already exists')
    current=int(ctx.get('currentRunId') or 0); runs=ctx.get('runs',[]); hist_auth=[r for r in runs if r.get('head_branch')==expected_branch and r.get('head_sha')!=ctx.get('headSha')]; req(not hist_auth,f'prior authorization-branch identity reuse exists: {[r.get("id") for r in hist_auth]}')
    prior_dispatch=[r for r in runs if r.get('head_branch')==dispatch]; req(not prior_dispatch,f'prior dispatch run exists: {[r.get("id") for r in prior_dispatch]}')
    scientific_prefixes=('tier2-stage1-case-','tier2-stage1-preflight','tier2-stage1-aggregate','tier2-stage1-audit','tier2-stage1-handoff')
    prior_art=[{'id':a.get('id'),'name':a.get('name')} for a in ctx.get('artifacts',[]) if str(a.get('name') or '').startswith(scientific_prefixes)]; req(not prior_art,f'prior Tier2 stage1 scientific artifact exists: {prior_art[:8]}')
    tracked=ctx.get('trackedSeedAudit') or {}; req(tracked.get('status')=='PASSED_EXACT_HEAD_TRACKED_TREE_100_SEED_NEGATIVE_COLLISION_CHECK' and tracked.get('repoHead')==ctx.get('headSha') and tracked.get('externalCollisionCount')==0,'tracked-tree seed audit incomplete')
    first=contract['seedAudit']['candidateFirstSeed']; last=contract['seedAudit']['candidateLastSeed']; candidates=set(range(first,last+1)); allowed_issue_ids=set(contract['seedAudit'].get('allowedIssue60SelfLedgerCommentIds') or [])
    issue_external=[]; allowed_seen=set()
    for c in ctx.get('issue60Comments',[]):
        body=str(c.get('body') or ''); hits=seed_literals(body,candidates); cid=c.get('id')
        if not hits: continue
        if cid in allowed_issue_ids:
            req(hits==[first,last] and contract['sourceBindings']['campaignContractSha256'] in body,'allowed Issue #60 self-ledger comment drift')
            allowed_seen.add(cid)
        else:
            issue_external.append({'id':cid,'seeds':hits[:8]})
    req(allowed_seen==allowed_issue_ids,f'expected Issue #60 self-ledger comment missing/drifted: {sorted(allowed_issue_ids-allowed_seen)}')
    req(not issue_external,f'Issue #60 external candidate seed declaration(s): {issue_external[:8]}')
    meta=json.dumps({'branches':ctx.get('branches',[]),'runs':ctx.get('runs',[]),'artifacts':ctx.get('artifacts',[])},sort_keys=True)
    meta_hits=seed_literals(meta,candidates); req(not meta_hits,f'candidate seed appears on external branch/run/artifact metadata: {meta_hits[:8]}')
    marker=re.compile(rf'^ORDINAL{candidate}_TIER2_STAGE1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED\b',re.I); markers=[c.get('id') for c in ctx.get('issue60Comments',[]) if marker.search(str(c.get('body') or '').strip())]; req(not markers,f'prior exact allocation marker exists: {markers}')
    identity_text=json.dumps({'runs':runs,'artifacts':ctx.get('artifacts',[]),'comments':ctx.get('issue60Comments',[])},sort_keys=True); req(key not in identity_text and dispatch not in identity_text,'execution key or dispatch identity already observed')
    out={'schemaVersion':1,'guardId':'public-tier2-v1-core-stage1-preauthorization-guard-v1','status':'AUTHORIZATION_IDENTITY_REVIEW_PASSED_DISPATCH_NOT_YET_CREATED','candidateScientificOrdinal':candidate,'executionKey':key,'authorizationBranch':expected_branch,'dispatchBranch':dispatch,'manifestSha256':manifest['manifestSha256'],'transportContractSha256':contract['contractSha256'],'all100CandidateSeedsRechecked':True,'repositoryGlobalBranchesInspected':True,'repositoryGlobalActionsRunsInspected':True,'repositoryGlobalActionsArtifactsInspected':True,'controlIssue60CommentsInspected':True,'authorizationIdentityAllocatedByReviewedCommit':True,'scientificExecutionAuthorized':True,'dispatchAuthorized':True,'automaticDispatch':False,'solverExecutionPerformed':False,'protectedHoldoutOpeningAuthorized':False,'stage2Authorized':False}
    out['guardSha256']=canon(out); return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--contract',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--context',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=evaluate(load(a.contract),load(a.manifest),load(a.context)); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(o['guardSha256']); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
