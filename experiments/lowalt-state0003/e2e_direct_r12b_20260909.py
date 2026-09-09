#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, os, shutil, sys, urllib.error, urllib.request, zipfile
from pathlib import Path

PREDECESSOR_RUN_ID=34376364203
PREDECESSOR_JOB_ID=102550069784
PREDECESSOR_ARTIFACT_ID=10114041694
PREDECESSOR_ARTIFACT_DIGEST='sha256:4f396d33c772c330db3aeba58a746395edadcf01ce54c20fe17de5091d57d1c5'
PREDECESSOR_HEAD='0fd6a6af84829edcb233e747724e71c8cc7eda68'

HERE=Path(__file__).resolve().parent
ORIGINAL=HERE/'e2e_direct_r12_20260909.py'
spec=importlib.util.spec_from_file_location('lowalt_r12_frozen',ORIGINAL)
if spec is None or spec.loader is None: raise RuntimeError('cannot import frozen R12 driver')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def api_download_noauth_redirect(url:str, token:str, out:Path):
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28','User-Agent':'lowalt-state-0003-r12b'})
    opener=urllib.request.build_opener(NoRedirect())
    redirect=[]; final=url
    try:
        response=opener.open(req,timeout=180)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301,302,303,307,308): raise
        loc=exc.headers.get('Location')
        if not loc: raise RuntimeError(f'artifact redirect {exc.code} without Location')
        redirect=[{'status':exc.code,'from':url,'to':loc.split('?')[0]}]
        final=loc
        response=urllib.request.urlopen(urllib.request.Request(loc,headers={'User-Agent':'lowalt-state-0003-r12b'}),timeout=300)
    with response as r, out.open('wb') as f:
        shutil.copyfileobj(r,f,1024*1024)
    e=Path(os.environ['EVIDENCE_DIR']); routes=e/'download-routes'; routes.mkdir(parents=True,exist_ok=True)
    mod.write_json(routes/(out.name+'.json'),{'schemaVersion':1,'requestedUrl':url,'redirectChain':redirect,'finalUrlWithoutQuery':final.split('?')[0],'authorizationForwardedToRedirectTarget':False,'bytes':out.stat().st_size,'sha256':mod.sha_file(out)})

mod.api_download=api_download_noauth_redirect
_original_acquire=mod.acquire_source

def acquire_source_compact(e:Path,gf:Path):
    lib=_original_acquire(e,gf)
    source=e/'source'
    # Preserve the literal 64930... wire object and exact extracted source/reference,
    # but discard redundant outer ZIP and decoded 284 MB tar after all hashes bind.
    for name in ('source-artifact.zip','libRadtran-2.0.6.tar'):
        p=source/name
        if p.exists(): p.unlink()
    return lib
mod.acquire_source=acquire_source_compact

def verify_predecessor(e:Path):
    gh=os.environ['GH_TOKEN']; repo=os.environ['GITHUB_REPOSITORY']
    run=mod.api_get(f'https://api.github.com/repos/{repo}/actions/runs/{PREDECESSOR_RUN_ID}',gh)
    assert int(run['id'])==PREDECESSOR_RUN_ID and run['run_attempt']==1 and run['head_sha']==PREDECESSOR_HEAD
    assert run['status']=='completed' and run['conclusion']=='failure'
    jobs=mod.api_get(f'https://api.github.com/repos/{repo}/actions/runs/{PREDECESSOR_RUN_ID}/jobs',gh)['jobs']
    assert len(jobs)==1 and int(jobs[0]['id'])==PREDECESSOR_JOB_ID
    arts=mod.api_get(f'https://api.github.com/repos/{repo}/actions/runs/{PREDECESSOR_RUN_ID}/artifacts',gh)['artifacts']
    art=[a for a in arts if int(a['id'])==PREDECESSOR_ARTIFACT_ID]
    assert len(art)==1 and art[0].get('digest')==PREDECESSOR_ARTIFACT_DIGEST and not art[0]['expired']
    z=e/'predecessor-r12-attempt1-evidence.zip'; api_download_noauth_redirect(f'https://api.github.com/repos/{repo}/actions/artifacts/{PREDECESSOR_ARTIFACT_ID}/zip',gh,z)
    assert mod.sha_file(z)==PREDECESSOR_ARTIFACT_DIGEST.split(':',1)[1]
    with zipfile.ZipFile(z) as q:
        names=set(q.namelist()); assert 'fatal-barrier.json' in names
        fatal=json.loads(q.read('fatal-barrier.json'))
        assert fatal['classification']=='STATE_0003_E2E_DIRECT_R12_EXECUTION_BARRIER'
        assert fatal['auditMayHaveOpened'] is False and fatal['errorType']=='HTTPError' and '401' in fatal['error']
        forbidden=('solver-direct-result.json','comparison.json','development-summary.json','final-summary.json')
        assert not any(any(name.endswith(x) for x in forbidden) for name in names)
        assert not any(name.startswith('cases/') for name in names)
    z.unlink()
    mod.write_json(e/'mechanical-successor-boundary.json',{'schemaVersion':1,'classification':'STATE_0003_R12B_MECHANICAL_SUCCESSOR_FROM_PREPROCESSING_BLOCKED_R12','predecessorRunId':PREDECESSOR_RUN_ID,'predecessorJobId':PREDECESSOR_JOB_ID,'predecessorArtifactId':PREDECESSOR_ARTIFACT_ID,'predecessorArtifactDigest':PREDECESSOR_ARTIFACT_DIGEST,'predecessorBarrier':'GitHub artifact redirect download returned HTTP 401 before governing source bytes and before any case preprocessing','predecessorAuditOpened':False,'predecessorCasePreprocessingObserved':False,'scientificMatrixAndAcceptanceContractPreservedByteForByte':True,'scientificCaseIdentitiesRemainUnconsumed':True,'mechanicalChangeOnly':'do not forward Authorization header from GitHub API request to signed artifact redirect target','retuningAfterResult':False,'protectedResultOpened':False,'taylorOrJerusalemUsed':False,'productionChanged':False,'fiveDegreeSeamChanged':False})

def main():
    e=Path(os.environ['EVIDENCE_DIR']); e.mkdir(parents=True,exist_ok=True)
    verify_predecessor(e)
    return mod.main()

if __name__=='__main__':
    try: rc=main()
    except Exception as exc:
        e=Path(os.environ.get('EVIDENCE_DIR','/tmp/lowalt_e2e_r12b')); e.mkdir(parents=True,exist_ok=True)
        mod.write_json(e/'fatal-barrier-r12b.json',{'schemaVersion':1,'classification':'STATE_0003_E2E_DIRECT_R12B_EXECUTION_BARRIER','errorType':type(exc).__name__,'error':str(exc),'auditMayHaveOpened':any((e/'cases'/r[0]/'comparison.json').exists() for r in mod.CASE_ROWS if r[1]=='audit')})
        mod.manifest(e); raise
    raise SystemExit(rc)
