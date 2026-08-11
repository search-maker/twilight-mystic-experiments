#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, urllib.parse
from pathlib import Path
from typing import Any
import candidate_v7 as v7
import github_surface as transport_api

HERE=Path(__file__).resolve().parent
CONTRACT=HERE/'transport-contract.v8.json'
BINDING=HERE/'review-binding.v6.json'
TEMPLATE=HERE/'authorization-template.ordinal16.json'
AUTH_BRANCH='authorization/full-spectrum-estimator-pilot-v2-ordinal16'
DISPATCH_BRANCH='dispatch/full-spectrum-estimator-pilot-v2-ordinal16'
EXECUTION_KEY='full-spectrum-estimator-pilot-v2:numerical:16'
TITLE='Full-spectrum estimator pilot v2 ordinal 16'
CANDIDATE_ORDINAL=16
PRIOR_ORDINAL=15
SCIENTIFIC_WORKFLOW='.github/workflows/full-spectrum-estimator-pilot-v2-ordinal16-execution-v8.yml'
AUTHORIZATION_REVIEW_WORKFLOW='.github/workflows/full-spectrum-estimator-pilot-v2-authorization-review-v8.yml'
MARKER_RE=re.compile(r'^ORDINAL16_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=([0-9a-f]{40}) parent=([0-9a-f]{40}) pr=([1-9][0-9]*)$',re.I)
PRIOR_TOKEN=re.compile(r'ordinal\s*[-:#]?\s*15\b',re.I)
CANDIDATE_TOKEN=re.compile(r'ordinal\s*[-:#]?\s*16\b',re.I)
ORDINAL_FROM_DISPATCH=re.compile(r'ordinal[-_]?([0-9]+)',re.I)
SHA40=re.compile(r'^[0-9a-f]{40}$')

class Refusal(RuntimeError): pass
def require(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def load(p:Path): return json.loads(p.read_text())
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def rawsha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def selfhash(v:dict[str,Any],field:str)->str:
    x=dict(v); x[field]=None; return hashlib.sha256(canon(x)).hexdigest()

def positive_candidate_claims(text:str)->list[str]:
    # Reuse the reviewed v7 prose grammar without allowing historical ordinal 15
    # text to alias the new candidate. First mask every exact prior token, then
    # map only candidate ordinal 16 onto the v7 parser's candidate token.
    source=text or ''
    direct=[]
    for raw in source.splitlines():
        line=raw.strip()
        if MARKER_RE.fullmatch(line): direct.append(line)
    masked=PRIOR_TOKEN.sub('prior-scientific-ordinal',source)
    translated=CANDIDATE_TOKEN.sub('ordinal 15',masked)
    return direct+v7.positive_candidate_claims(translated)

def matching_marker(text:str,head:str,parent:str,pr:int)->bool:
    m=MARKER_RE.fullmatch((text or '').strip())
    return bool(m and m.group(1).lower()==head.lower() and m.group(2).lower()==parent.lower() and int(m.group(3))==int(pr))

def _is_candidate_scientific_run(run:dict[str,Any])->bool:
    hb=run.get('head_branch') or ''
    if hb==DISPATCH_BRANCH: return True
    if (run.get('event') or '')!='push': return False
    path=run.get('path') or ''; title=(run.get('display_title') or '').strip(); name=(run.get('name') or '').strip()
    return path==SCIENTIFIC_WORKFLOW or EXECUTION_KEY in title or title.lower()==TITLE.lower() or name.lower()==(TITLE+' execution v8').lower()

def _failed_authorization_ref_reusable(auth_head:str|None,prs:list[dict[str,Any]],runs:list[dict[str,Any]])->bool:
    if not auth_head: return False
    matching=[p for p in prs if (p.get('head') or {}).get('ref')==AUTH_BRANCH and (p.get('head') or {}).get('sha')==auth_head]
    closed=[p for p in matching if p.get('state')=='closed' and p.get('merged_at') is None]
    if len(closed)!=1 or any(p.get('state')=='open' for p in matching): return False
    rr=[r for r in runs if (r.get('head_branch') or '')==AUTH_BRANCH and (r.get('head_sha') or '')==auth_head and (r.get('path') or '')==AUTHORIZATION_REVIEW_WORKFLOW and (r.get('event') or '')=='pull_request']
    failed=[r for r in rr if int(r.get('run_attempt') or 0)==1 and r.get('status')=='completed' and r.get('conclusion')=='failure']
    success=[r for r in rr if r.get('status')=='completed' and r.get('conclusion')=='success']
    return len(failed)==1 and not success

def build_surface(payload:dict[str,Any],current_pr:int|None=None,marker_head:str|None=None,marker_parent:str|None=None,current_run_id:int|None=None)->dict[str,Any]:
    branches=payload.get('branches',[]); runs=payload.get('runs',[]); prs=payload.get('pulls',[]); issues=payload.get('issues',[]); comments=payload.get('issue60Comments',[])
    names=[b.get('name','') for b in branches]; prior=[]
    for name in names:
        if name==DISPATCH_BRANCH: continue
        if 'dispatch/' in name:
            m=ORDINAL_FROM_DISPATCH.search(name)
            if m: prior.append(int(m.group(1)))
    for r in runs:
        hb=r.get('head_branch') or ''
        if hb and hb!=DISPATCH_BRANCH and 'dispatch/' in hb:
            m=ORDINAL_FROM_DISPATCH.search(hb)
            if m: prior.append(int(m.group(1)))
    candidate_runs=[r for r in runs if not(current_run_id and int(r.get('id') or 0)==int(current_run_id)) and _is_candidate_scientific_run(r)]
    positive=[]
    for pr in prs:
        if current_pr and int(pr.get('number') or 0)==current_pr: continue
        positive.extend(positive_candidate_claims((pr.get('title') or '')+'\n'+(pr.get('body') or '')))
    for issue in issues:
        if issue.get('pull_request'): continue
        positive.extend(positive_candidate_claims((issue.get('title') or '')+'\n'+(issue.get('body') or '')))
    marker_count=0
    for c in comments:
        body=c.get('body') or ''
        if marker_head and marker_parent and current_pr and matching_marker(body,marker_head,marker_parent,current_pr): marker_count+=1; continue
        positive.extend(positive_candidate_claims(body))
    auth_head=dispatch_head=None
    for b in branches:
        if b.get('name')==AUTH_BRANCH: auth_head=(b.get('commit') or {}).get('sha')
        if b.get('name')==DISPATCH_BRANCH: dispatch_head=(b.get('commit') or {}).get('sha')
    latest=max(prior) if prior else None
    return {'latestPriorConsumedScientificOrdinal':latest,'nextAvailableScientificOrdinal':latest+1 if latest is not None else None,'candidatePriorScientificRunCount':len(candidate_runs),'authorizationBranchExists':AUTH_BRANCH in names,'authorizationBranchHeadSha':auth_head,'authorizationBranchReusableAfterFailedReview':_failed_authorization_ref_reusable(auth_head,prs,runs),'dispatchBranchExists':DISPATCH_BRANCH in names,'dispatchBranchHeadSha':dispatch_head,'positiveCandidateClaimsExcludingCurrent':len(positive),'matchingAuthorizationMarkers':marker_count,'activeAuthorizationPathOnMainExists':bool(payload.get('activeAuthorizationPathOnMainExists')),'allStatePullRequestsInspected':True,'allStateIssuesInspected':True,'allActionsRunsInspected':True,'allBranchesInspected':True,'issue60AndCommentsInspected':True,'candidateCodePathsOnMainInspected':True}

def collect(repository:str,token:str)->dict[str,Any]:
    base=f'https://api.github.com/repos/{repository}'; branches=transport_api._pages(base+'/branches',token); pulls=transport_api._pages(base+'/pulls?state=all',token); issues=transport_api._pages(base+'/issues?state=all',token); comments=transport_api._pages(base+'/issues/60/comments',token); issue60=transport_api._api(base+'/issues/60',token)
    runs=[]; page=1
    while True:
        value=transport_api._api(base+f'/actions/runs?per_page=100&page={page}',token); rows=value.get('workflow_runs',[]); runs.extend(rows)
        if len(rows)<100: break
        page+=1
    path='experiments/full-spectrum-estimator-pilot-v2/authorization.ordinal16.json'; exists,_=transport_api._exists(base+'/contents/'+urllib.parse.quote(path,safe='/')+'?ref=main',token)
    return {'branches':branches,'runs':runs,'pulls':pulls,'issues':issues,'issue60':issue60,'issue60Comments':comments,'activeAuthorizationPathOnMainExists':exists}

def validate_common(ctx:dict[str,Any],dispatch_must_be_absent:bool=True)->None:
    require(ctx.get('latestPriorConsumedScientificOrdinal')==PRIOR_ORDINAL,'latest prior consumed scientific ordinal is not 15')
    require(ctx.get('candidatePriorScientificRunCount')==0,'candidate has prior scientific runs')
    if dispatch_must_be_absent: require(ctx.get('dispatchBranchExists') is False,'candidate dispatch branch already exists')
    require(ctx.get('positiveCandidateClaimsExcludingCurrent')==0,'positive candidate ordinal claim already exists')
    for key,msg in [('allStatePullRequestsInspected','all-state pull requests not inspected'),('allStateIssuesInspected','all-state issues not inspected'),('allActionsRunsInspected','all Actions runs not inspected'),('allBranchesInspected','all branches not inspected'),('issue60AndCommentsInspected','Issue #60 surface not inspected'),('candidateCodePathsOnMainInspected','candidate code paths on main not inspected')]: require(ctx.get(key) is True,msg)
def validate_preauthorization(ctx:dict[str,Any])->None:
    validate_common(ctx); auth_exists=ctx.get('authorizationBranchExists') is True; reusable=ctx.get('authorizationBranchReusableAfterFailedReview') is True
    require((not auth_exists) or reusable,'candidate authorization branch already exists and is not an unconsumed failed-review ref'); require(ctx.get('activeAuthorizationPathOnMainExists') is False,'active authorization file already exists on main'); require(ctx.get('matchingAuthorizationMarkers')==0,'authorization marker already exists'); require(ctx.get('nextAvailableScientificOrdinal')==CANDIDATE_ORDINAL,'ordinal 16 is not next available')
def validate_authorization_review(ctx:dict[str,Any],head:str)->None:
    validate_common(ctx); require(ctx.get('authorizationBranchExists') is True,'authorization branch missing during authorization review'); require(ctx.get('authorizationBranchHeadSha')==head,'authorization branch head differs from reviewed head'); require(ctx.get('activeAuthorizationPathOnMainExists') is False,'active authorization file already exists on main'); require(ctx.get('matchingAuthorizationMarkers')==0,'authorization marker must not pre-exist review')
def validate_dispatch(ctx:dict[str,Any],head:str,post_dispatch:bool=False)->None:
    validate_common(ctx,dispatch_must_be_absent=not post_dispatch); require(ctx.get('authorizationBranchExists') is True,'authorization branch missing before dispatch'); require(ctx.get('authorizationBranchHeadSha')==head,'authorization head drift before dispatch'); require(ctx.get('matchingAuthorizationMarkers')==1,'exactly one matching authorization marker required')
    if post_dispatch: require(ctx.get('dispatchBranchExists') is True,'dispatch branch missing after dispatch transition'); require(ctx.get('dispatchBranchHeadSha')==head,'dispatch branch head differs from authorization head')

def validate_static(repository_root:Path|None=None)->tuple[dict[str,Any],dict[str,Any]]:
    c=load(CONTRACT); b=load(BINDING); t=load(TEMPLATE)
    require(c.get('contractSha256')==selfhash(c,'contractSha256'),'contract self-hash mismatch'); require(b.get('bindingSha256')==selfhash(b,'bindingSha256'),'binding self-hash mismatch'); require(c['authorizationRules']['templateRawSha256']==rawsha(TEMPLATE),'template raw hash mismatch'); require(t.get('enabled') is False and t.get('exactAuthorizationCommit') is None and t.get('exactAuthorizationParentCommit') is None,'authorization template not disabled')
    if repository_root is not None:
        for row in b['reviewPaths']+[b['contractWorkflow']]:
            p=repository_root/row['destinationPath']; require(p.is_file(),f'missing bound review path {row["destinationPath"]}'); require(p.stat().st_size==row['size'],f'bound review size drift {row["destinationPath"]}'); require(rawsha(p)==row['sha256'],f'bound review hash drift {row["destinationPath"]}')
        m=load(repository_root/c['scientificPayload']['executionManifestPath']); require(m['caseCount']==44 and m['configuredPhotonHistoriesSum']==5600000000,'scientific manifest cardinality drift'); require([x['seed'] for x in m['cases']]==list(range(970001,970045)),'scientific seed sequence drift')
    return c,b

def validate_enabled_document(auth:dict[str,Any],live_main:str,c:dict[str,Any],b:dict[str,Any])->None:
    require(auth.get('enabled') is True,'authorization document not enabled'); require(auth.get('status')=='AUTHORIZED_PENDING_SEPARATE_DISPATCH','authorization status drift'); require(auth.get('authorizationOrdinal')==16,'authorization ordinal drift'); require(auth.get('executionKey')==EXECUTION_KEY,'execution key drift'); require(auth.get('runTitle')==TITLE,'run title drift'); require(auth.get('authorizationBranch')==AUTH_BRANCH,'authorization branch drift'); require(auth.get('dispatchBranch')==DISPATCH_BRANCH,'dispatch branch drift'); require(auth.get('exactAuthorizationParentCommit')==live_main,'authorization parent not live main'); require(auth.get('exactAuthorizationCommit') is None,'authorization document must not embed own commit SHA'); require(auth.get('reviewBindingSha256')==b['bindingSha256'],'review binding drift'); require(auth.get('transportContractSha256')==c['contractSha256'],'transport contract binding drift'); require(auth.get('solverExecutionAuthorized') is True,'authorization does not authorize solver execution'); require(auth.get('dispatchAuthorized') is False and auth.get('automaticDispatch') is False,'authorization may not auto-dispatch')
    for key in ('githubRerunAllowed','resumeAllowed','retryAllowed','modelFittingAuthorized','modelSelectionAuthorized','holdoutValidationOpeningAuthorized','tier2Authorized','productionPromotionAuthorized'): require(auth.get(key) is False,f'forbidden authorization flag {key}')
def review(auth:dict[str,Any],ctx:dict[str,Any])->dict[str,Any]:
    c,b=validate_static(); live=ctx.get('liveMain'); head=ctx.get('headSha'); parent=ctx.get('parentSha'); pr=ctx.get('pr') or {}
    require(isinstance(live,str) and SHA40.fullmatch(live),'live main invalid'); require(isinstance(head,str) and SHA40.fullmatch(head),'authorization head invalid'); require(parent==live,'authorization commit parent is not then-live main'); require(ctx.get('parentCount')==1,'authorization commit must have exactly one parent'); require(ctx.get('changedPaths')==c['authorizationRules']['changedPathsExactly'],'authorization commit must change exactly one authorization path'); validate_enabled_document(auth,live,c,b); require(pr.get('number',0)>0,'authorization PR number invalid'); require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR must be Draft/open/unmerged'); require(pr.get('headBranch')==AUTH_BRANCH and pr.get('baseBranch')=='main','authorization PR branch/base drift'); require(pr.get('headRepo')==c['repository'] and pr.get('baseRepo')==c['repository'],'authorization PR must be same-repository'); require(pr.get('headSha')==head,'authorization PR head mismatch'); require(ctx.get('runAttempt')==1,'authorization review must be attempt 1'); require(ctx.get('eventName')=='pull_request' and ctx.get('eventAction')=='opened','authorization review must be PR opened event'); require(ctx.get('scientificRuntimeSetupPerformed') is False,'authorization review may not set up scientific runtime'); require(ctx.get('scientificExecutionPerformed') is False,'authorization review may not execute scientific process'); validate_authorization_review(ctx.get('freshness') or {},head)
    return {'status':'AUTHORIZATION_REVIEW_PASS_ZERO_RUNTIME','authorizationHead':head,'authorizationParent':parent,'authorizationPr':pr['number'],'scientificExecutionPerformed':False,'ordinalAllocatedReservedOrConsumedByReview':False}
def preauthorize(ctx:dict[str,Any])->dict[str,Any]:
    validate_static(); validate_preauthorization(ctx.get('freshness') or {}); require(ctx.get('authorizationCreated') is False,'authorization already created'); require(ctx.get('scientificExecutionPerformed') is False,'scientific execution already occurred'); return {'status':'PREAUTHORIZATION_FRESHNESS_PASS','authorizationCreationPermitted':True,'scientificExecutionPerformed':False,'ordinalAllocatedReservedOrConsumed':False}
def dispatch_evaluate(auth:dict[str,Any],ctx:dict[str,Any],post_dispatch:bool=False)->dict[str,Any]:
    c,b=validate_static(); head=ctx.get('authorizationHead'); parent=ctx.get('authorizationParent'); pr=ctx.get('pr') or {}; rr=ctx.get('authorizationReview') or {}
    require(isinstance(head,str) and SHA40.fullmatch(head),'authorization head invalid'); require(isinstance(parent,str) and SHA40.fullmatch(parent),'authorization parent invalid'); require(ctx.get('liveMain')==parent,'live main moved after authorization review'); validate_enabled_document(auth,parent,c,b); require(pr.get('state')=='open' and pr.get('draft') is True and pr.get('merged') is False,'authorization PR no longer Draft/open/unmerged'); require(pr.get('headBranch')==AUTH_BRANCH and pr.get('headSha')==head,'authorization PR head/branch drift'); require(rr.get('headSha')==head and rr.get('prNumber')==pr.get('number'),'authorization review identity drift'); require(rr.get('workflow')==c['authorizationReviewRules']['workflow'],'authorization review workflow drift'); require(rr.get('runAttempt')==1 and rr.get('conclusion')=='success','exact successful attempt-1 authorization review required'); require(rr.get('scientificRuntimeSetupPerformed') is False and rr.get('scientificExecutionPerformed') is False,'authorization review was not zero-runtime'); validate_dispatch(ctx.get('freshness') or {},head,post_dispatch=post_dispatch); markers=ctx.get('issue60Markers') or []; good=[m for m in markers if matching_marker(m,head,parent,int(pr.get('number') or 0))]; require(len(good)==1 and len(markers)==1,'exactly one exact Issue #60 authorization marker required'); return {'status':'DISPATCH_ELIGIBLE_NOT_CREATED','authorizationHead':head,'authorizationParent':parent,'authorizationPr':pr['number'],'dispatchBranchMayPointTo':head,'scientificExecutionPerformed':False}
def execution_evaluate(auth:dict[str,Any],ctx:dict[str,Any])->dict[str,Any]:
    d=dispatch_evaluate(auth,ctx.get('dispatchEligibility') or {},post_dispatch=True); head=d['authorizationHead']; require(ctx.get('githubActions') is True,'scientific execution must run in GitHub Actions'); require(ctx.get('eventName')=='push','scientific workflow is push-only'); require(ctx.get('refName')==DISPATCH_BRANCH,'scientific workflow trigger branch drift'); require(ctx.get('headSha')==head,'dispatch ref does not point to reviewed authorization head'); require(ctx.get('dispatchBranchHeadSha')==head,'live dispatch branch head drift'); require(ctx.get('runAttempt')==1,'scientific workflow attempt must be exactly 1'); require(ctx.get('priorMatchingScientificRuns')==0,'candidate scientific workflow has prior run; retry/rerun refused'); require(ctx.get('resumeRequested') is False,'resume refused'); require(ctx.get('retryRequested') is False,'retry refused'); require(ctx.get('automaticDownstreamTransition') is False,'automatic downstream scientific transition refused'); return {'status':'SCIENTIFIC_EXECUTION_GUARD_PASS','authorizationHead':head,'runAttempt':1,'oneSyntaxCheckPerCase':True,'solverExecutionsPerCaseMaximum':1,'automaticFittingAuthorized':False}
def matrix(repository_root:Path)->dict[str,Any]:
    c,_=validate_static(repository_root); m=load(repository_root/c['scientificPayload']['executionManifestPath']); return {'include':[{'caseId':x['caseId'],'method':x['method'],'seed':x['seed'],'photonHistories':x['photonHistories']} for x in m['cases']]}
def compact_matrix_output(repository_root:Path)->str: return json.dumps(matrix(repository_root),sort_keys=True,separators=(',',':'),ensure_ascii=False)
def write_output(value:Any,path:Path|None)->None:
    text=json.dumps(value,indent=2,sort_keys=True)+'\n'
    if path: path.write_text(text)
    else: print(text,end='')
def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('surface'); s.add_argument('--repository',required=True); s.add_argument('--output',type=Path,required=True); s.add_argument('--current-pr',type=int); s.add_argument('--marker-head'); s.add_argument('--marker-parent'); s.add_argument('--current-run-id',type=int); s.add_argument('--token-env',default='GITHUB_TOKEN')
    p=sub.add_parser('preauthorize'); p.add_argument('--context',type=Path,required=True); p.add_argument('--output',type=Path)
    r=sub.add_parser('review'); r.add_argument('--authorization',type=Path,required=True); r.add_argument('--context',type=Path,required=True); r.add_argument('--output',type=Path)
    d=sub.add_parser('dispatch-guard'); d.add_argument('--authorization',type=Path,required=True); d.add_argument('--context',type=Path,required=True); d.add_argument('--post-dispatch',action='store_true'); d.add_argument('--output',type=Path)
    e=sub.add_parser('execution-guard'); e.add_argument('--authorization',type=Path,required=True); e.add_argument('--context',type=Path,required=True); e.add_argument('--output',type=Path)
    q=sub.add_parser('verify-static'); q.add_argument('--repository-root',type=Path,required=True); q.add_argument('--output',type=Path)
    m=sub.add_parser('matrix'); m.add_argument('--repository-root',type=Path,required=True); m.add_argument('--output',type=Path)
    a=ap.parse_args()
    try:
        if a.cmd=='surface':
            token=os.getenv(a.token_env); require(bool(token),f'missing {a.token_env}'); write_output(build_surface(collect(a.repository,token),a.current_pr,a.marker_head,a.marker_parent,a.current_run_id),a.output)
        elif a.cmd=='preauthorize': write_output(preauthorize(load(a.context)),a.output)
        elif a.cmd=='review': write_output(review(load(a.authorization),load(a.context)),a.output)
        elif a.cmd=='dispatch-guard': write_output(dispatch_evaluate(load(a.authorization),load(a.context),a.post_dispatch),a.output)
        elif a.cmd=='execution-guard': write_output(execution_evaluate(load(a.authorization),load(a.context)),a.output)
        elif a.cmd=='verify-static':
            c,b=validate_static(a.repository_root.resolve()); write_output({'status':'STATIC_BINDING_V8_PASS','reviewPathsVerified':len(b['reviewPaths'])+1,'caseCount':c['scientificPayload']['caseCount'],'scientificExecutionPerformed':False},a.output)
        elif a.cmd=='matrix': write_output(matrix(a.repository_root.resolve()),a.output)
        return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
