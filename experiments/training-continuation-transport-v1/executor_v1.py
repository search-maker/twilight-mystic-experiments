#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess
from pathlib import Path
from common_v1 import *

def resolve(raw:bytes,data:Path,out:Path)->bytes:
    t=raw.decode(); repl={'${LIBRADTRAN_DATA}':str(data.resolve()),'${ATMOSPHERE_FILE}':str((data/'atmmod/afglus.dat').resolve()),'${SOLAR_FLUX_FILE}':str((data/'solar_flux/atlas_plus_modtran').resolve()),'${OUTPUT_DIR}':str(out.resolve())}
    for k,v in repl.items(): t=t.replace(k,v)
    require('${' not in t,'unresolved input placeholder'); return t.encode()

def run(cmd,text,cwd,timeout):
    try:r=subprocess.run(cmd,input=text,text=True,capture_output=True,cwd=cwd,timeout=timeout,check=False); return r.returncode,False,r.stdout,r.stderr
    except subprocess.TimeoutExpired as e:return None,True,e.stdout or '',e.stderr or ''

def verify_runtime(runtime:dict,auth:dict)->None:
    verify_self(runtime,'runtimeIdentitySha256')
    require(runtime['runtimeIdentitySha256']==auth.get('runtimeIdentitySha256'),'authorization/runtime identity drift')
    for key in ('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256'):
        v=runtime.get(key); require(isinstance(v,str) and len(v)==64,f'runtime identity missing: {key}')

def execute(repo,manifest,analysis,auth,runtime_path,case_id,data,outroot,uvspec,timeout):
    verify_self(manifest,'manifestSha256'); require(manifest['status']=='DISABLED_EXECUTION_MANIFEST_REVIEW_ONLY','manifest drift')
    verify_self(analysis,'analysisContractSha256'); require(manifest.get('analysisContractSha256')==analysis['analysisContractSha256'],'manifest/analysis binding drift')
    verify_self(auth,'authorizationSha256'); require(auth.get('enabled') is True and auth.get('scientificExecutionAuthorized') is True and auth.get('dispatchAuthorized') is True,'authorization not enabled')
    require(auth.get('transportContractSha256')==manifest['transportContractSha256'] and auth.get('analysisContractSha256')==analysis['analysisContractSha256'] and auth.get('preregistrationSha256')==manifest['preregistrationSha256'],'authorization binding drift'); require(auth.get('variant')==manifest['variant'],'authorization variant drift')
    runtime=load(runtime_path); verify_runtime(runtime,auth)
    require(os.getenv('GITHUB_ACTIONS')=='true' and os.getenv('GITHUB_EVENT_NAME')=='push' and os.getenv('GITHUB_RUN_ATTEMPT')=='1','not attempt-1 GitHub push context'); require(os.getenv('GITHUB_REF_NAME')==auth.get('dispatchBranch'),'dispatch branch mismatch'); require(auth.get('githubRerunAllowed') is False and auth.get('retryAllowed') is False and auth.get('resumeAllowed') is False,'retry boundary drift')
    rows=[x for x in manifest['cases'] if x['caseId']==case_id]; require(len(rows)==1,'case id not unique'); c=rows[0]; src=repo/c['templatePath']; raw=src.read_bytes(); require(sha_bytes(raw)==c['templateSha256'],'frozen input template hash drift')
    caseout=outroot/case_id; caseout.mkdir(parents=True,exist_ok=False); inp=resolve(raw,data,outroot); require(f'mc_randomseed {c["seed"]}'.encode() in inp and f'mc_photons {c["photonHistories"]}'.encode() in inp and f'mc_spectral_is {c["importanceCenterNm"]:.1f}'.encode() in inp,'resolved execution directives drift'); (caseout/'input-resolved.txt').write_bytes(inp); (caseout/'randomseed').write_text(str(c['seed'])+'\n'); (caseout/'runtime-report.json').write_bytes(runtime_path.read_bytes()); (caseout/'prepared.json').write_text(json.dumps({'stageId':'training-continuation-v1-prepared','caseId':case_id,'variant':manifest['variant'],'seed':c['seed'],'photonHistories':c['photonHistories'],'executionManifestSha256':manifest['manifestSha256'],'analysisContractSha256':analysis['analysisContractSha256'],'runtimeIdentitySha256':runtime['runtimeIdentitySha256'],'inputResolvedSha256':sha_bytes(inp)},sort_keys=True,separators=(',',':'))+'\n')
    ec,to,so,se=run([str(uvspec),'-c'],inp.decode(),caseout,60); (caseout/'syntax-stdout.txt').write_text(str(so)); (caseout/'syntax-stderr.txt').write_text(str(se)); require(not to and ec==0,'syntax check failed'); ec,to,so,se=run([str(uvspec)],inp.decode(),caseout,timeout); (caseout/'solver-stdout.txt').write_text(str(so)); (caseout/'solver-stderr.txt').write_text(str(se)); require(not to and ec==0,'solver execution failed'); require((caseout/'mc.rad.spc').is_file() and (caseout/'mc.rad.std.spc').is_file(),'required raw spectra missing')
    r={'schemaVersion':1,'stageId':'training-continuation-v1','status':'COMPLETED','variant':manifest['variant'],'caseId':case_id,'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'seed':c['seed'],'photonHistories':c['photonHistories'],'inputResolvedSha256':sha_file(caseout/'input-resolved.txt'),'runtimeReportRawSha256':sha_file(caseout/'runtime-report.json'),'runtimeIdentitySha256':runtime['runtimeIdentitySha256']}; r['contentSha256']=canon(r); (caseout/'case-result.json').write_text(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n'); return r

def main():
    p=argparse.ArgumentParser(); p.add_argument('--repository-root',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--analysis-contract',type=Path,required=True); p.add_argument('--authorization',type=Path,required=True); p.add_argument('--runtime-report',type=Path,required=True); p.add_argument('--case-id',required=True); p.add_argument('--data-dir',type=Path,required=True); p.add_argument('--output-root',type=Path,required=True); p.add_argument('--uvspec',type=Path,required=True); p.add_argument('--timeout-seconds',type=int,default=1800); p.add_argument('--allow-execution',action='store_true'); a=p.parse_args()
    try: require(a.allow_execution,'--allow-execution required'); print(json.dumps(execute(a.repository_root.resolve(),load(a.manifest),load(a.analysis_contract),load(a.authorization),a.runtime_report,a.case_id,a.data_dir,a.output_root,a.uvspec,a.timeout_seconds),sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
