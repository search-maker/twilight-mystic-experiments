from __future__ import annotations
import hashlib, importlib.util, json, os, shutil, subprocess, sys, time, zipfile
from pathlib import Path

CB='review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-authorization-control-v1'
CH='5685d5c313071014a94c816ee26b129f1f17a7fc'; CP=766; CR=33360847786; CA=9746918484
CD='5a8f7b17273499e68521c95f91354d2d1d1a50a40758128b762859e2f5c5a16c'; CT=5474307907
AB='authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45'
DB='dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45'
AP='review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-authorization-control-v1/authorization.json'
ASH='d1ca682466935efb10d304919fbbf51f6a266c16fd1e0f2e9a4eca2bc9f300c1'; ABL='96ee8299d00bd72cdb73de4583670730ce89c73b'
SSH='ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de'; RSH='c439de417520b330c037e2628df02b6955f652563300aa5ef30477abf7661a98'
O42='e627a689ada0493a8a5b9cdafc4aba0198fbabec'; O42B='491d1b6653bea0fcc5275269723a76aa1af52300'
RUNS={41:33236295233,42:33259899524,43:33298433506,44:33334396129}; M44=5471141364
FENCE='AVPS_V2_RECOVERY4_SUCCESSOR_AUTHORIZATION_REVIEW_GLOBAL_SCAN_V1'; TARGET=45
R4='review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-seed-global-control-v1/seed_ledger.py'
SC='experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py'; FR='experiments/aerosol-family-challenge-v2-r8/execution-candidate/freshness.py'; OR='experiments/aerosol-family-challenge-v2-r8/execution-candidate/preauthorization_ordinal.py'
BLOBS={R4:'16af5c68ae7e3cfc0cfbef4c8e2022517bf2ae91',SC:'4c6d704fa24228284780bcb1dd7c52537b4c5b0d',FR:'732f803b5261e7986582dd7e0d69a66f70432b1e',OR:'7ca8efd17ae9e7ec2baa32fe935e5173ca6d173f'}

def die(x): raise SystemExit(x)
def sh(*a,binary=False): return subprocess.check_output(a,text=not binary).strip() if not binary else subprocess.check_output(a)
def api(ep,binary=False):
    for n in range(3):
        try: return sh('gh','api',ep,binary=binary)
        except subprocess.CalledProcessError:
            if n==2: raise
            time.sleep(4*(n+1))
def js(ep): return json.loads(api(ep))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m
def canon(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def comments():
    out=[]; p=1
    while True:
        b=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/issues/60/comments?per_page=100&page={p}'); out+=b
        if len(b)<100:return out
        p+=1

def bind_identity(head,base,pr,s):
    if os.environ.get('GITHUB_EVENT_NAME')!='pull_request_target' or os.environ.get('GITHUB_RUN_ATTEMPT')!='1': die('wrong event/attempt')
    if os.environ['PR_BRANCH']!=AB or os.environ['PR_BASE_BRANCH']!=CB or base!=CH or sh('git','rev-parse','HEAD')!=head: die('head/base identity drift')
    subprocess.run(['git','fetch','--no-tags','origin',CB,O42],check=True)
    if sh('git','rev-parse',f'origin/{CB}')!=CH: die('control branch drift')
    parents=[x.split()[1] for x in sh('git','cat-file','-p','HEAD').splitlines() if x.startswith('parent ')]
    if parents!=[CH] or sh('git','diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()!=[AP]: die('authorization not exact one-file direct child')
    raw=Path(AP).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ASH or sh('git','rev-parse',f'HEAD:{AP}')!=ABL: die('authorization bytes drift')
    for p,b in BLOBS.items():
        if sh('git','rev-parse',f'HEAD:{p}')!=b: die('frozen support blob drift '+p)
    if sh('git','rev-parse',f'{O42}:review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py')!=O42B: die('ordinal42 native ledger drift')
    if shutil.which('uvspec'): die('uvspec available in zero-runtime review')
    cur=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/pulls/{pr}'); ctl=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/pulls/{CP}')
    if cur['state']!='open' or cur['draft'] is not True or cur.get('merged_at') or cur['head']['sha']!=head or cur['base']['sha']!=CH or cur['head']['repo']['full_name']!=cur['base']['repo']['full_name']: die('authorization PR drift')
    if ctl['state']!='open' or ctl['draft'] is not True or ctl.get('merged_at') or ctl['head']['sha']!=CH: die('control PR drift')
    r=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{CR}'); a=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/artifacts/{CA}'); t=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/issues/comments/{CT}')
    if r['run_attempt']!=1 or r['status']!='completed' or r['conclusion']!='success' or r['head_sha']!=CH: die('control run drift')
    if a.get('digest')!='sha256:'+CD or a.get('expired') is not False: die('control artifact drift')
    if 'TRANSITION_ELIGIBLE_NOT_ALLOCATED' not in str(t.get('body') or ''): die('control transition drift')
    for n,rid in RUNS.items():
        rr=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/runs/{rid}')
        if rr['run_attempt']!=1 or rr['status']!='completed' or rr['conclusion']!='failure': die(f'consumed ordinal {n} run drift')
    if str(js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/issues/comments/{M44}').get('body') or '').strip()!='ORDINAL44_AVPS_V2_POSTCONSUMPTION_RECOVERY3_DISPATCH_CONSUMED': die('ordinal44 marker drift')
    z=s/'control.zip'; z.write_bytes(api(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/artifacts/{CA}/zip',binary=True))
    if hashlib.sha256(z.read_bytes()).hexdigest()!=CD: die('control zip digest drift')
    with zipfile.ZipFile(z) as q:q.extractall(s/'control')
    prop=s/'control/authorization.proposed.json'; rec=s/'control/control-review-receipt.json'
    if not prop.is_file() or not rec.is_file() or prop.read_bytes()!=raw: die('proposal artifact byte mismatch')
    aa=json.loads(raw); rr=json.loads(rec.read_text())
    req={'scientificOrdinal':45,'nextOrdinalHardCoded':False,'authorizationBranch':AB,'dispatchBranch':DB,'exactAuthorizationParentCommit':CH,'candidateSeedCount':72,'candidateSeedCanonicalSha256':SSH,'candidateRowsCanonicalSha256':RSH,'caseCount':360,'commonRandomNumberGroupCount':72,'statesPerGroup':5,'photonHistoriesPerCase':20000000,'dispatchAuthorized':False,'resultOpeningAuthorized':False,'levelBOpeningAuthorized':False,'protectedHoldoutOpeningAuthorized':False,'productionAuthorized':False,'taylorOrJerusalemFitAuthorized':False,'newMappingAuthorized':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False}
    for k,v in req.items():
        if aa.get(k)!=v: die('proposal semantic drift '+k)
    if rr.get('status')!='PASS_RECOVERY4_AUTHORIZATION_CONTROL_PROPOSAL_NOT_ALLOCATED_NOT_DISPATCHED' or rr.get('scientificOrdinalAllocated') is not False or rr.get('dispatchCreated') is not False: die('control receipt boundary drift')

def ledger(s):
    wt=Path(os.environ.get('RUNNER_TEMP','/tmp'))/'avps-r4-auth-review-ord42'; shutil.rmtree(wt,ignore_errors=True); subprocess.run(['git','worktree','add','--detach',str(wt),O42],check=True,stdout=subprocess.DEVNULL)
    try:
        os.environ['AVPS_ORDINAL42_LEDGER_PATH']=str(wt/'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py')
        x=load('r4ledger',R4).validate_ledger(); seeds={int(v) for v in x['candidateSeeds']}
        if len(seeds)!=72 or x['candidateSeedCanonicalSha256']!=SSH or x['candidateRowsCanonicalSha256']!=RSH: die('recovery4 ledger drift')
        (s/'candidate-ledger.json').write_text(json.dumps(x,sort_keys=True)+'\n')
        return seeds
    finally: subprocess.run(['git','worktree','remove','--force',str(wt)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def tracked(s):
    (s/'files.nul').write_bytes(subprocess.check_output(['git','ls-files','-z'])); (s/'policy.json').write_text('{"schemaVersion":2,"requiredTrackedSelfLedgerPaths":[],"futureEvidenceSelfLedgerPaths":[]}\n')
    subprocess.run([sys.executable,'review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/tracked_tree_seed_scan.py','--repo-root','.','--file-list',str(s/'files.nul'),'--candidate-seed-ledger',str(s/'candidate-ledger.json'),'--allow-self-ledger-json',str(s/'policy.json'),'--output',str(s/'tracked.json')],check=True)
    x=json.loads((s/'tracked.json').read_text())
    if x.get('trackedTreeExternalCollisionCount')!=0 or x.get('exactHeadTrackedTreeByteScanPassed') is not True: die('tracked-tree collision/refusal')

def fence(head,pr,runid):
    prefix=f'WRITE_QUIET_BEGIN | {FENCE} | branch={AB} | head={head} | base={CH} | pr={pr}'
    for _ in range(90):
        rows=comments(); begins=[r for r in rows if str(r.get('body') or '').startswith(prefix)]
        if len(begins)==1: break
        time.sleep(10)
    else: die('exact review fence not observed uniquely')
    bid=begins[0]['id']; later=[r for r in rows if r['id']>bid]
    if any(str(r.get('body') or '').startswith(f'WRITE_QUIET_END | {FENCE}') for r in later): die('review fence already closed')
    bad=('NOT_ADMISSIBLE','DO NOT USE','FAIL-CLOSED')
    if any('RECOVERY4' in str(r.get('body') or '').upper() and any(x in str(r.get('body') or '').upper() for x in bad) for r in later): die('newer Recovery4 refusal')
    for _ in range(90):
        active=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/runs?status=in_progress&per_page=100')['workflow_runs']; queued=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/runs?status=queued&per_page=100')['workflow_runs']
        if not [r for r in active+queued if int(r['id'])!=runid]: break
        time.sleep(10)
    else: die('workflows never quiescent')
    time.sleep(45)
    active=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/runs?status=in_progress&per_page=100')['workflow_runs']; queued=js(f'repos/{os.environ["GITHUB_REPOSITORY"]}/actions/runs?status=queued&per_page=100')['workflow_runs']
    if [r for r in active+queued if int(r['id'])!=runid]: die('workflow churn resumed')

def scan(head,pr,runid,seeds,s):
    fr=load('freshness',FR); sys.modules['freshness']=fr; sc=load('scanner',SC); od=load('ordinal',OR)
    for n in range(3):
        try: ctx,stable,snap,post=sc.collect_stable(os.environ['GITHUB_REPOSITORY'],60,os.environ['GITHUB_TOKEN'],runid,seeds,'authorization-recheck'); break
        except Exception:
            if n==2: raise
            time.sleep(3*(n+1))
    rep=sc.evaluate_context(ctx,seeds,runid,stable_double_enumeration_passed=True,stable_context_sha256_value=stable,audit_mode='authorization-recheck',expected_branch_name=AB,expected_repo_head=head,snapshot_fence=snap,post_fence_arrival_counts=post)
    if rep.get('repositoryGlobalCollisionCount')!=0 or rep.get('repositoryGlobalDoubleEnumerationStable') is not True or rep.get('repositoryGlobalPostFenceCandidateSeedCollisionCount')!=0 or rep.get('auditedBranchHeadMatchesRepositoryHead') is not True: die('global seed recheck failed')
    obs=od.authoritative_global_ordinal_observations(ctx,current_run_id=runid)
    def self45(r):
        if int(r['ordinal'])!=45:return False
        sf,id=str(r.get('surface') or ''),str(r.get('id') or '')
        if sf=='branch' and id==AB:return True
        if sf in ('pull-request','pull-request-prose') and id==str(pr):return True
        return sf=='workflow-run' and any(str(x.get('id'))==id and x.get('head_branch')==AB and x.get('head_sha')==head for x in ctx.get('runs',[]))
    non=[r for r in obs if not self45(r)]; consumed={int(r['ordinal']) for r in non if r.get('reason')=='exact-consumed-marker'}
    if not {41,42,43,44}.issubset(consumed) or any(int(r['ordinal'])==45 for r in non) or max(int(r['ordinal']) for r in non)!=44: die('ordinal surface drift')
    if DB in {str(r.get('name') or '') for r in ctx.get('branches',[])} or any(str(r.get('body') or '').strip().upper().startswith('ORDINAL45_') for r in ctx.get('issue60Comments',[])): die('ordinal45 already allocated/dispatched')
    ev=s/'evidence'; ev.mkdir(exist_ok=True)
    (ev/'repository-global-seed-recheck.json').write_text(json.dumps(rep,indent=2,sort_keys=True)+'\n')
    receipt={'schemaVersion':1,'status':'PASS_RECOVERY4_SUCCESSOR_AUTHORIZATION_REVIEWED_NOT_ALLOCATED_NOT_DISPATCHED','authorizationPr':pr,'authorizationHead':head,'authorizationParent':CH,'authorizationJsonSha256':ASH,'authorizationJsonGitBlobSha1':ABL,'scientificOrdinal':45,'candidateSeedCount':72,'candidateSeedCanonicalSha256':SSH,'candidateRowsCanonicalSha256':RSH,'nonSelfGlobalOrdinalMaxObserved':44,'independentTargetOrdinalObservationCount':0,'consumedScientificOrdinalsRequired':[41,42,43,44],'scientificOrdinalAllocated':False,'dispatchCreated':False,'solverExecutionPerformed':False,'resultOpeningPerformed':False,'levelBOpened':False,'protectedHoldoutOpened':False,'productionAuthorized':False,'taylorOrJerusalemUsed':False,'newMappingAuthorized':False,'rerunRetryResumeAllowed':False}
    receipt['contentSha256']=canon(receipt); (ev/'authorization-review-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

def main():
    h=os.environ['HEAD_SHA']; b=os.environ['BASE_SHA']; pr=int(os.environ['PR_NUMBER']); rid=int(os.environ['GITHUB_RUN_ID']); s=Path('avps-r4-auth-review-scratch'); shutil.rmtree(s,ignore_errors=True); s.mkdir()
    bind_identity(h,b,pr,s); seeds=ledger(s); tracked(s); fence(h,pr,rid); scan(h,pr,rid,seeds,s)
    if sh('git','status','--porcelain','--untracked-files=no'): die('tracked tree changed')
if __name__=='__main__': main()
