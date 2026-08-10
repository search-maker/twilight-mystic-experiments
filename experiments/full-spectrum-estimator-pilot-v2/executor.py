#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from typing import Any, Callable

HERE=Path(__file__).resolve().parent
REVIEW_REL=Path('review/full-spectrum-estimator-pilot-v2')
class ExecutionRefusal(RuntimeError): pass
def require(c,m):
    if not c: raise ExecutionRefusal(m)
def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path): return json.loads(p.read_text())

def resolve_input(repository_root:Path, case_id:str, data_dir:Path, output_root:Path)->bytes:
    template=repository_root/REVIEW_REL/'rendered-review-v5'/case_id/'input-template.txt'
    require(template.is_file(),f'reviewed input template missing: {case_id}')
    text=template.read_text()
    replacements={
      '${LIBRADTRAN_DATA}':str(data_dir.resolve()),
      '${ATMOSPHERE_FILE}':str((data_dir/'atmmod/afglus.dat').resolve()),
      '${SOLAR_FLUX_FILE}':str((data_dir/'solar_flux/atlas_plus_modtran').resolve()),
      '${WAVELENGTH_GRID_1NM}':str((repository_root/REVIEW_REL/'wavelength-grid-1nm.dat').resolve()),
      '${OUTPUT_DIR}':str(output_root.resolve()),
    }
    for k,v in replacements.items(): text=text.replace(k,v)
    require('${' not in text,'unresolved input placeholder')
    return text.encode()

def case_from_manifest(repository_root:Path, case_id:str)->dict[str,Any]:
    p=repository_root/REVIEW_REL/'full-spectrum-estimator-pilot-execution-manifest-v4.json'; m=load(p)
    rows=[x for x in m['cases'] if x['caseId']==case_id]; require(len(rows)==1,'case not uniquely present in frozen manifest'); return rows[0]

def _run(command:list[str], text:str, cwd:Path, timeout:int)->dict[str,Any]:
    try:
        r=subprocess.run(command,input=text,text=True,capture_output=True,cwd=cwd,timeout=timeout,check=False)
        return {'exitCode':r.returncode,'timedOut':False,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as exc:
        return {'exitCode':None,'timedOut':True,'stdout':exc.stdout or '', 'stderr':exc.stderr or ''}

def _canon(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def execute_case(repository_root:Path, case_id:str, data_dir:Path, output_root:Path, uvspec:Path, runtime_report:Path, timeout:int, allow_execution:bool, runner:Callable[...,dict[str,Any]]|None=None)->dict[str,Any]:
    require(allow_execution,'--allow-execution required')
    require(os.getenv('GITHUB_ACTIONS')=='true' and os.getenv('GITHUB_EVENT_NAME')=='push' and os.getenv('GITHUB_RUN_ATTEMPT')=='1','not exact GitHub Actions attempt-1 push context')
    require(os.getenv('GITHUB_REF_NAME')=='dispatch/full-spectrum-estimator-pilot-v2-ordinal14','not exact dispatch branch')
    manifest_path=repository_root/REVIEW_REL/'full-spectrum-estimator-pilot-execution-manifest-v4.json'
    manifest=load(manifest_path); case=case_from_manifest(repository_root,case_id); runtime=load(runtime_report)
    required_runtime=manifest['runtimeIdentityRequired']
    for key in ('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256'):
        require(runtime.get(key)==required_runtime.get(key),f'runtime identity drift: {key}')
    case_dir=output_root/case_id; case_dir.mkdir(parents=True,exist_ok=False)
    inp=resolve_input(repository_root,case_id,data_dir,output_root); (case_dir/'input-resolved.txt').write_bytes(inp)
    require(f'mc_randomseed {case["seed"]}'.encode() in inp,'resolved seed drift'); require(f'mc_photons {case["photonHistories"]}'.encode() in inp,'resolved photon count drift')
    (case_dir/'runtime-report.json').write_bytes(runtime_report.read_bytes())
    (case_dir/'randomseed').write_text(f'{case["seed"]}\n',encoding='utf-8')
    prepared={'schemaVersion':1,'stageId':'full-spectrum-estimator-pilot-v2-prepared','caseId':case_id,'geometryId':case['geometryId'],'method':case['method'],'replicate':case['replicate'],'seed':case['seed'],'photonHistories':case['photonHistories'],'inputResolvedSha256':hashlib.sha256(inp).hexdigest(),'executionManifestSha256':manifest['manifestSha256']}
    (case_dir/'prepared.json').write_text(json.dumps(prepared,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    if case['method']=='reference-vroom-1nm':
        grid=repository_root/REVIEW_REL/'wavelength-grid-1nm.dat'; (case_dir/'wavelength-grid-1nm.dat').write_bytes(grid.read_bytes())
    run=runner or _run
    text=inp.decode('utf-8')
    syntax=run([str(uvspec),'-c'],text,case_dir,60)
    (case_dir/'syntax-stdout.txt').write_text(str(syntax['stdout']),encoding='utf-8'); (case_dir/'syntax-stderr.txt').write_text(str(syntax['stderr']),encoding='utf-8')
    require(not syntax['timedOut'] and syntax['exitCode']==0,'single syntax check failed')
    solver=run([str(uvspec)],text,case_dir,timeout)
    (case_dir/'solver-stdout.txt').write_text(str(solver['stdout']),encoding='utf-8'); (case_dir/'solver-stderr.txt').write_text(str(solver['stderr']),encoding='utf-8')
    require(not solver['timedOut'] and solver['exitCode']==0,'single solver execution failed')
    required_members=manifest['artifactContract']['requiredMembersByMethod'][case['method']]
    for name in required_members:
        if name=='case-result.json': continue
        path=case_dir/name
        require(path.is_file(),f'required raw member missing: {name}')
        if name not in {'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt'}:
            require(path.stat().st_size>0,f'unexpected empty required raw member: {name}')
    raw_hashes={name:sha(case_dir/name) for name in required_members if name!='case-result.json'}
    result={'schemaVersion':1,'stageId':'full-spectrum-estimator-pilot-v2','status':'COMPLETED','caseId':case_id,'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,'seed':case['seed'],'photonHistories':case['photonHistories'],'inputResolvedSha256':sha(case_dir/'input-resolved.txt'),'runtimeReportRawSha256':sha(case_dir/'runtime-report.json'),'radianceOutputSha256':sha(case_dir/'mc.rad.spc'),'stdRadianceOutputSha256':sha(case_dir/'mc.rad.std.spc'),'rawMemberSha256ByBasename':raw_hashes}
    result['contentSha256']=_canon(result)
    (case_dir/'case-result.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
    return result

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repository-root',type=Path,required=True); ap.add_argument('--case-id',required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-root',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True); ap.add_argument('--runtime-report',type=Path,required=True); ap.add_argument('--timeout-seconds',type=int,default=1800); ap.add_argument('--allow-execution',action='store_true'); a=ap.parse_args()
    try: print(json.dumps(execute_case(a.repository_root,a.case_id,a.data_dir,a.output_root,a.uvspec,a.runtime_report,a.timeout_seconds,a.allow_execution),sort_keys=True)); return 0
    except Exception as exc: print(json.dumps({'status':'REFUSED','reason':str(exc)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
