from __future__ import annotations
import hashlib, importlib.util, io, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

ROOT=Path.cwd(); INFRA=Path(__file__).resolve().parents[2]
SUBJECT_PR=1026; SUBJECT_HEAD='5028cb7c7cd585d720749f0d572aa15e2f614bf9'; SUBJECT_BRANCH='review/avps-v2-postconsumption-successor-ordinal46-authorization-child-v1-20260909'
CONTROL_HEAD='1e55c28a38c016175ba8b350933730b615060e4f'; CONTROL_BRANCH='review/avps-v2-postconsumption-successor-authorization-control-replacement-v2-20260909'; MAIN='8cd85cf393e2d86a1b6d7325654747460a13e697'
RBR='review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-v1-20260910'; STAGE='AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEW_GLOBAL_SCAN_V1'
WF='.github/workflows/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-v1.yml'; SCRIPT='review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-v1/review_authorization.py'; ART='avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-v1-proof'
AUTH='review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v2/authorization.json'; AUTH_SHA='442b76aee266baea248848a2a84ae017cac864fdde3aa8f6f119baef45660cc5'; AUTH_BLOB='3dd0f80ff878d09987a91af0b4860a449fd41a92'
AB='authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal-46'; DB='dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal-46'; KEY='aerosol-vertical-profile-sensitivity-v2-postconsumption-successor:numerical:46'
CA=10130865093; CR=34419338768; CD='sha256:f83fd355a91fe86665b9df84e59d340412a8a009f1c19ce5c71a3a7fa8d23adf'; RR='980cf9351040f1f5a91490e75f7d5e5a1cc522f915bb75727c833c2d3408efca'; RC='614bbb1e9eaadd0782949895696d59734de8932b3af56c978ad122bea2f41567'
SSH='6ace6be3b0298f3fa35cdc522a3375c0480a4154371c15bbbf4a3f930a5d17cd'; RSH='30c0c1e38755f2c04b59448569c15c38a8b3b850c73d235ea38ce8f880d30f8b'
CTRL='review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v2/authorization_control.py'; CTRL_BLOB='a75611614de6b1ecafc216b2affa5bde639a5516'
ORDINAL45_CONSUMED_MARKER='ORDINAL45_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_CONSUMED'

class Refusal(RuntimeError): pass
def req(x,m):
    if not x: raise Refusal(m)
def run(*a,cwd=ROOT,check=True):
    p=subprocess.run(a,cwd=cwd,text=True,capture_output=True)
    if check and p.returncode: raise Refusal(f"command failed {a}: {p.stdout}\n{p.stderr}")
    return p
def out(*a,cwd=ROOT): return run(*a,cwd=cwd).stdout.strip()
def blob(p):
    b=p.read_bytes(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def canon(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def load(name,p):
    s=importlib.util.spec_from_file_location(name,p); req(s and s.loader,f'cannot load {p}'); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

def ctrl():
    p=ROOT/CTRL; req(blob(p)==CTRL_BLOB,'Control-V2 wrapper byte drift'); return load('avps46_review_ctrl',p)

def wq(c,repo,tok,rh,rpr,expect=None):
    from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin, record_write_quiet_end
    rows=c.core.pages(c.core.repo_url(repo,'issues/60/comments'),tok); begins={}; seen=set(); closed=set()
    for r in rows:
        b=str(r.get('body') or '')
        if record_write_quiet_end(b,int(r['id']),seen,closed): continue
        if is_write_quiet_begin(b): seen.add(int(r['id'])); begins[int(r['id'])]=r
    u=sorted(x for x in seen if x not in closed); req(len(u)==1,f'expected own WQ only, got {u}'); bid=u[0]
    if expect is not None: req(bid==expect,'WQ begin changed')
    first=str(begins[bid].get('body') or '').splitlines()[0].strip(); req(first.startswith(f'WRITE_QUIET_BEGIN | {STAGE} |'),'wrong WQ stage')
    for x in (f'branch={RBR}',f'head={rh}',f'base={SUBJECT_HEAD}',f'subject_pr={SUBJECT_PR}',f'subject_head={SUBJECT_HEAD}',f'control_parent={CONTROL_HEAD}'): req(x in first,f'WQ missing {x}')
    return {'begin':bid,'count':len(rows),'tail':max(int(r['id']) for r in rows)}

def mutable(c,repo,tok,status):
    rows=[]; total=None; page=1
    while True:
        p=c.core.req_json(c.core.repo_url(repo,f'actions/runs?status={status}&per_page=100&page={page}'),tok); req(isinstance(p,dict) and isinstance(p.get('workflow_runs'),list),f'bad Actions {status} payload')
        n=int(p.get('total_count') or 0); total=n if total is None else total; req(n==total,f'Actions {status} count changed during pagination'); q=list(p['workflow_runs']); rows+=q
        if len(q)<100: break
        page+=1; req(page<1000,'Actions pagination runaway')
    req(len(rows)==total and len({int(r.get('id') or 0) for r in rows})==len(rows),f'Actions {status} pagination/ID mismatch'); return rows

def quiesce(c,a):
    sts=('in_progress','queued','waiting','requested','pending')
    for _ in range(90):
        b=[]; counts={}
        for s in sts:
            q=mutable(c,a.repo,a.tok,s); counts[s]=len(q); b += [r for r in q if int(r.get('id') or 0)!=a.run]
        if not b:
            time.sleep(20); final={}; b=[]
            for s in sts:
                q=mutable(c,a.repo,a.tok,s); final[s]=len(q); b += [r for r in q if int(r.get('id') or 0)!=a.run]
            req(not b,f'Actions resumed before scan {[r.get("id") for r in b]}'); return {'allPages':True,'initial':counts,'final':final}
        time.sleep(10)
    raise Refusal('Actions never quiescent')

def static(c,a):
    req(a.event=='pull_request' and a.action=='opened' and a.attempt==1,'wrong event/action/attempt'); req(a.rb==RBR and a.base==SUBJECT_HEAD and a.bb==SUBJECT_BRANCH,'review carrier identity drift')
    req(out('git','rev-parse','HEAD')==SUBJECT_HEAD and out('git','rev-parse',f'HEAD:{AUTH}')==AUTH_BLOB,'subject checkout/authorization drift'); req(hashlib.sha256((ROOT/AUTH).read_bytes()).hexdigest()==AUTH_SHA,'authorization raw-byte drift')
    req(out('git','rev-parse','HEAD',cwd=INFRA)==a.rh,'reviewer checkout drift'); req(not out('git','rev-list','--merges',f'{SUBJECT_HEAD}..{a.rh}',cwd=INFRA),'reviewer merge found')
    paths=sorted(x for x in out('git','diff','--name-only',f'{SUBJECT_HEAD}...{a.rh}',cwd=INFRA).splitlines() if x); req(paths==sorted([WF,SCRIPT]),f'reviewer changed paths {paths}')
    req(c.core.branch_head(a.repo,'main',a.tok)==MAIN and c.core.branch_head(a.repo,SUBJECT_BRANCH,a.tok)==SUBJECT_HEAD and c.core.branch_head(a.repo,CONTROL_BRANCH,a.tok)==CONTROL_HEAD and c.core.branch_head(a.repo,RBR,a.tok)==a.rh,'branch/main drift')
    p=c.core.current_pr(a.repo,SUBJECT_PR,a.tok); req(p.get('state')=='open' and p.get('draft') is True and p.get('merged_at') is None and p['head']['sha']==SUBJECT_HEAD and p['base']['sha']==CONTROL_HEAD and int(p.get('commits') or 0)==1 and int(p.get('changed_files') or 0)==1,'PR1026 drift')
    rp=c.core.current_pr(a.repo,a.rpr,a.tok); req(rp.get('state')=='open' and rp.get('draft') is True and rp.get('merged_at') is None and rp['head']['sha']==a.rh and rp['head']['ref']==RBR and rp['base']['sha']==SUBJECT_HEAD and rp['base']['ref']==SUBJECT_BRANCH,'reviewer PR drift')
    sr=c.core.req_json(c.core.repo_url(a.repo,f'actions/runs/{a.run}'),a.tok); req(sr.get('event')=='pull_request' and int(sr.get('run_attempt') or 0)==1 and sr.get('head_sha')==a.rh and sr.get('head_branch')==RBR and sr.get('path')==WF,'self-run registration drift')
    req(shutil.which('uvspec') is None,'uvspec present in zero-runtime review'); return paths

def control_artifact(c,a,subject):
    r=c.core.req_json(c.core.repo_url(a.repo,f'actions/runs/{CR}'),a.tok); req(r.get('status')=='completed' and r.get('conclusion')=='success' and int(r.get('run_attempt') or 0)==1 and r.get('head_sha')==CONTROL_HEAD,'Control-V2 run drift')
    p=c.core.req_json(c.core.repo_url(a.repo,f'actions/runs/{CR}/artifacts?per_page=100'),a.tok); q=[x for x in p.get('artifacts',[]) if int(x.get('id') or 0)==CA]; req(len(q)==1 and q[0].get('name')=='vertical-profile-v2-postconsumption-successor-authorization-control-v2-proof' and q[0].get('digest')==CD and q[0].get('expired') is False,'Control-V2 artifact drift')
    raw=c.safe_request_bytes(c.core.repo_url(a.repo,f'actions/artifacts/{CA}/zip'),a.tok); req('sha256:'+hashlib.sha256(raw).hexdigest()==CD,'Control-V2 ZIP digest drift')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=z.namelist(); req(len(names)==27 and 'authorization-proposal.json' in names and 'authorization-control-receipt.json' in names,'Control-V2 ZIP layout drift'); prop=z.read('authorization-proposal.json'); rr=z.read('authorization-control-receipt.json')
    req(hashlib.sha256(prop).hexdigest()==AUTH_SHA and prop==subject,'proposal/PR1026 byte mismatch'); req(hashlib.sha256(rr).hexdigest()==RR,'Control-V2 receipt raw SHA drift'); rec=json.loads(rr); saved=rec.get('receiptSha256'); chk=dict(rec); chk.pop('receiptSha256',None); req(saved==RC and canon(chk)==RC,'corrected Control-V2 receipt self-hash drift'); req(rec.get('status')=='PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_CONTROL_PROPOSAL_ONLY_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED' and rec.get('controlHead')==CONTROL_HEAD and rec.get('controlRunId')==CR,'Control-V2 receipt identity/status drift'); return rec

def selfobs(row,payload,rpr,rh):
    if int(row.get('ordinal') or -1)!=46: return False
    s=str(row.get('surface') or ''); i=str(row.get('id') or '')
    if s=='branch' and i in (SUBJECT_BRANCH,RBR): return True
    if s in ('pull-request','pull-request-prose') and i in (str(SUBJECT_PR),str(rpr)): return True
    if s=='workflow-run':
        for x in payload.get('runs',[]):
            if str(x.get('id') or '')==i and ((x.get('head_branch')==SUBJECT_BRANCH and x.get('head_sha')==SUBJECT_HEAD) or (x.get('head_branch')==RBR and x.get('head_sha')==rh)): return True
    return False

def review(a):
    req(not out('git','status','--porcelain','--untracked-files=no'),'tracked subject workspace dirty'); u=[x for x in out('git','status','--porcelain').splitlines() if x.startswith('?? ')]; req(all(x=='?? review-infra/' for x in u),f'unexpected untracked subject workspace {u}'); c=ctrl(); req(not out('git','status','--porcelain',cwd=INFRA),'reviewer workspace dirty'); a.ev.mkdir(parents=True,exist_ok=False)
    paths=static(c,a); pre=wq(c,a.repo,a.tok,a.rh,a.rpr); subject=(ROOT/AUTH).read_bytes(); crec=control_artifact(c,a,subject); source_api=c.core.verify_source_api(a.repo,a.tok)
    source,h42,tmp=c.core.source_worktree(a.repo)
    try:
        c.core.verify_source_code(source); sw,lm=c.core.load_source_modules(source,h42); sc=sw.mod; c.core.require_bound_scanner_mode(sc); sc.REVIEW_PROOF_ARTIFACT_NAME=ART; led=c.core.validate_source_ledger(lm,h42); req(led['candidateSeedCanonicalSha256']==SSH and led['candidateRowsCanonicalSha256']==RSH,'fresh ledger drift'); tracked=c.core.tracked_tree_scan(a.ev,led); seeds={int(x) for x in led['candidateSeeds']}; req(len(seeds)==72,'seed cardinality drift')
        guard=wq(c,a.repo,a.tok,a.rh,a.rpr,pre['begin']); req(guard['tail']==pre['tail'],'#60 tail changed before scan'); ag=quiesce(c,a); guard=wq(c,a.repo,a.tok,a.rh,a.rpr,pre['begin']); req(guard['tail']==pre['tail'],'#60 tail changed immediately before scan'); req(c.core.branch_head(a.repo,'main',a.tok)==MAIN and c.core.branch_head(a.repo,SUBJECT_BRANCH,a.tok)==SUBJECT_HEAD,'base moved before scan')
        ctx,stable,fence,post=sc.collect_stable(a.repo,60,a.tok,a.run,seeds,'authorization-recheck'); rep=sc.evaluate_context(ctx,seeds,a.run,stable_double_enumeration_passed=True,stable_context_sha256_value=stable,audit_mode='authorization-recheck',expected_branch_name=RBR,expected_repo_head=a.rh,snapshot_fence=fence,post_fence_arrival_counts=post)
        for k,v in {'candidateSeedCount':72,'repositoryGlobalCollisionCount':0,'repositoryGlobalCollisionSurfaceScanPassed':True,'repositoryGlobalDoubleEnumerationStable':True,'repositoryGlobalEnumerationPassCount':2,'auditedBranchHeadMatchesRepositoryHead':True,'repositoryGlobalPostFenceCandidateSeedCollisionCount':0,'allStatePullRequestsInspected':True,'allStateIssuesInspected':True,'allRepositoryIssueCommentsInspected':True,'allRepositoryPullReviewCommentsInspected':True,'allRepositoryCommitCommentsInspected':True}.items(): req(rep.get(k)==v,f'global scan drift {k}={rep.get(k)!r}')
        req(not sc.final_review_proof_artifacts(a.repo,a.tok,a.run),'prior review-proof artifact identity exists')
    finally: c.core.cleanup_worktrees(source,h42,tmp)
    consumed45=c.core.verify_consumed45(a.repo,a.tok); preauth=c.core.load('avps46_review_surface',ROOT/c.core.PREAUTH_SURFACE_PATH); payload=preauth.collect(a.repo,a.tok); latest=preauth.latest_consumed_or_dispatched_ordinal(payload); req(latest==45,f'latest consumed/dispatched={latest}')
    _,_,om=preauth._modules(); obs=om.authoritative_global_ordinal_observations(payload,current_run_id=a.run); non=[x for x in obs if not selfobs(x,payload,a.rpr,a.rh)]; req(non and max(int(x['ordinal']) for x in non)==45,'non-self global ordinal max drift'); req(not [x for x in non if int(x['ordinal'])==46],f'non-self ordinal46 occupancy'); consumed={int(x['ordinal']) for x in non if x.get('reason')=='exact-consumed-marker'}; req({41,42,43,44,45}.issubset(consumed),f'consumed markers incomplete {sorted(consumed)}')
    auth=json.loads(subject); branches={str(x.get('name') or '') for x in payload.get('branches',[])}; req(AB not in branches and DB not in branches,'live ordinal46 auth/dispatch ref exists'); comments=[str(x.get('body') or '').strip() for x in payload.get('issue60Comments',[])]; req(sum(1 for x in comments if x==ORDINAL45_CONSUMED_MARKER)==1,'ordinal45 consumed marker count drift'); req(not any(x.upper().startswith('ORDINAL46_') for x in comments),'ordinal46 allocation/consumed marker exists')
    paths2={auth['proposedPublisherWorkflowPath'],auth['proposedScienceWorkflowPath']}; req(not any(str(x.get('path') or '') in paths2 for x in payload.get('runs',[])),'ordinal46 proposed publisher/science run exists'); fresh,_,_=preauth._modules(); ks=c.proposal_aware_execution_key_scan(payload,KEY,46,fresh.positive_candidate_claims,current_pr=SUBJECT_PR,current_run_id=a.run); req(ks['authoritativeExecutionKeyUseCount']==0,f'authoritative execution-key use {ks["authoritativeExecutionKeyUseRows"]}')
    gp=run('git','grep','-n','-F',KEY,check=False); lines=[x for x in gp.stdout.splitlines() if x]; req(gp.returncode==0 and len(lines)==1 and lines[0].startswith(AUTH+':'),'tracked execution-key occurrence not self-only')
    false=('scientificOrdinalAllocated','ordinalReserved','authorizationRefCreated','authorizationCreated','candidateSeedsAppliedToCases','seedUniverseConsumed','dispatchCreated','publisherInvoked','scienceInvoked','scientificExecutionAuthorized','solverExecutionAuthorized','scientificRuntime','solverExecuted','protectedResultsOpened','levelBOpened','protectedHoldoutOpened','newMappingOccurred','productionOccurred','taylorOrJerusalemUsed','githubRerunAllowed','retryAllowed','resumeAllowed'); req(auth['scientificOrdinal']==46 and auth['latestPriorConsumedOrDispatchedScientificOrdinal']==45 and auth['authorizationBranch']==AB and auth['dispatchBranch']==DB and auth['executionKey']==KEY and auth['candidateSeedCount']==72 and auth['candidateSeedCanonicalSha256']==SSH and auth['candidateRowsCanonicalSha256']==RSH and all(auth.get(k) is False for k in false),'PR1026 frozen semantics drift')
    installed=c.core.verify_installed_blobs(source_api['identity']); postwq=wq(c,a.repo,a.tok,a.rh,a.rpr,pre['begin']); req(postwq['tail']==pre['tail'],'#60 tail changed during review'); req(c.core.branch_head(a.repo,'main',a.tok)==MAIN and c.core.branch_head(a.repo,SUBJECT_BRANCH,a.tok)==SUBJECT_HEAD and c.core.branch_head(a.repo,RBR,a.tok)==a.rh,'final branch/main drift')
    write(a.ev/'repository-global-seed-recheck.json',rep); write(a.ev/'global-ordinal-observations.json',obs); write(a.ev/'proposal-aware-execution-key-scan.json',ks); write(a.ev/'mutable-actions-quiescence.json',ag); write(a.ev/'control-v2-receipt.json',crec); write(a.ev/'consumed-ordinal45-readback.json',consumed45); write(a.ev/'installed-byte-readback.json',installed); write(a.ev/'write-quiet-pre.json',pre); write(a.ev/'write-quiet-post.json',postwq)
    receipt={'schemaVersion':1,'status':'PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEWED_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED','reviewerPr':a.rpr,'reviewerHead':a.rh,'reviewerBranch':RBR,'reviewRunId':a.run,'reviewRunAttempt':a.attempt,'subjectAuthorizationPr':SUBJECT_PR,'subjectAuthorizationHead':SUBJECT_HEAD,'subjectAuthorizationParent':CONTROL_HEAD,'authorizationJsonSha256':AUTH_SHA,'authorizationJsonGitBlobSha1':AUTH_BLOB,'controlArtifact':CA,'controlArtifactDigest':CD,'controlReceiptRawSha256':RR,'controlReceiptCanonicalSelfSha256':RC,'writeQuietBeginCommentId':pre['begin'],'candidateSeedCount':72,'candidateSeedCanonicalSha256':SSH,'candidateRowsCanonicalSha256':RSH,'trackedTreeExternalCollisionCount':tracked.get('trackedTreeExternalCollisionCount'),'repositoryGlobalCollisionCount':rep.get('repositoryGlobalCollisionCount'),'repositoryGlobalDoubleEnumerationStable':rep.get('repositoryGlobalDoubleEnumerationStable'),'repositoryGlobalStableContextSha256':rep.get('repositoryGlobalStableContextSha256'),'repositoryGlobalSnapshotFenceSha256':rep.get('repositoryGlobalSnapshotFenceSha256'),'latestPriorConsumedOrDispatchedScientificOrdinal':latest,'nonSelfGlobalScientificOrdinalMax':45,'nextAvailableScientificOrdinal':46,'authorizationBranch':AB,'dispatchBranch':DB,'executionKey':KEY,'authoritativeExecutionKeyUseCount':ks['authoritativeExecutionKeyUseCount']}
    receipt.update({k:False for k in false}); receipt['receiptSha256']=canon(receipt); write(a.ev/'authorization-review-receipt.json',receipt); print(json.dumps(receipt,sort_keys=True))

def main():
    p=__import__('argparse').ArgumentParser()
    for n in ('repo','tok','rh','rb','base','bb','event','action'): p.add_argument('--'+n,required=True)
    for n in ('rpr','run','attempt'): p.add_argument('--'+n,type=int,required=True)
    p.add_argument('--ev',type=Path,required=True); a=p.parse_args(); review(a)
if __name__=='__main__': main()
