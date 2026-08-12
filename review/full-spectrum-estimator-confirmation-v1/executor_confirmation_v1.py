#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
from typing import Any, Callable

MANIFEST_ID='public-tier1-full-spectrum-estimator-confirmation-execution-manifest-v1'
DISPATCH_RE=re.compile(r'^dispatch/full-spectrum-estimator-confirmation-v1-ordinal[1-9][0-9]*$')
class ExecutionRefusal(RuntimeError): pass

def require(c:bool,m:str)->None:
    if not c: raise ExecutionRefusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text()); require(isinstance(v,dict),f'expected object: {p}'); return v

def validate_manifest(m:dict[str,Any])->None:
    require(m.get('manifestId')==MANIFEST_ID,'confirmation execution manifest id drift')
    require(m.get('manifestSha256')==canon({k:v for k,v in m.items() if k!='manifestSha256'}),'confirmation execution manifest self-hash drift')
    require(m.get('caseCount')==24 and len(m.get('cases') or [])==24,'confirmation execution case universe drift')

def validate_execution_context(expected_dispatch_branch:str)->None:
    require(isinstance(expected_dispatch_branch,str) and DISPATCH_RE.fullmatch(expected_dispatch_branch) is not None,'invalid expected confirmation dispatch branch')
    require(os.getenv('GITHUB_ACTIONS')=='true','not GitHub Actions context')
    require(os.getenv('GITHUB_EVENT_NAME')=='push','not exact push context')
    require(os.getenv('GITHUB_RUN_ATTEMPT')=='1','not exact attempt-1 context')
    require(os.getenv('GITHUB_REF_NAME')==expected_dispatch_branch,'not exact confirmation dispatch branch')

def resolve_template(template_raw:bytes, *, data_dir:Path, output_root:Path)->bytes:
    text=template_raw.decode('utf-8')
    repl={
      '${LIBRADTRAN_DATA}':str(data_dir.resolve()),
      '${ATMOSPHERE_FILE}':str((data_dir/'atmmod/afglus.dat').resolve()),
      '${SOLAR_FLUX_FILE}':str((data_dir/'solar_flux/atlas_plus_modtran').resolve()),
      '${OUTPUT_DIR}':str(output_root.resolve()),
    }
    for k,v in repl.items(): text=text.replace(k,v)
    require('${' not in text,'unresolved confirmation input placeholder')
    return text.encode()

def _run(command:list[str],text:str,cwd:Path,timeout:int)->dict[str,Any]:
    try:
        r=subprocess.run(command,input=text,text=True,capture_output=True,cwd=cwd,timeout=timeout,check=False)
        return {'exitCode':r.returncode,'timedOut':False,'stdout':r.stdout,'stderr':r.stderr}
    except subprocess.TimeoutExpired as e:
        return {'exitCode':None,'timedOut':True,'stdout':e.stdout or '','stderr':e.stderr or ''}

def execute_case(*,repository_root:Path,manifest_path:Path,render_report_path:Path,template_root:Path,case_id:str,data_dir:Path,output_root:Path,uvspec:Path,runtime_report:Path,timeout:int,allow_execution:bool,expected_dispatch_branch:str,runner:Callable[...,dict[str,Any]]|None=None)->dict[str,Any]:
    require(allow_execution,'--allow-execution required')
    validate_execution_context(expected_dispatch_branch)
    m=load(manifest_path); validate_manifest(m)
    rows=[x for x in m['cases'] if x.get('caseId')==case_id]; require(len(rows)==1,'case not uniquely present in confirmation manifest'); case=rows[0]
    require(case.get('method')=='alis-alt-importance','confirmation v1 execution permits ALIS candidate cases only')
    runtime=load(runtime_report); req=m['runtimeIdentityRequired']
    for k in ('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256'):
        require(runtime.get(k)==req.get(k),f'runtime identity drift: {k}')
    rr=load(render_report_path); require(rr.get('manifestSha256')==m['manifestSha256'] and rr.get('caseCount')==24 and rr.get('scientificExecutionPerformed') is False,'confirmation render report boundary drift')
    require(rr.get('renderSha256')==canon({k:v for k,v in rr.items() if k!='renderSha256'}),'confirmation render report self-hash drift')
    rrows=[x for x in rr.get('cases',[]) if x.get('caseId')==case_id]; require(len(rrows)==1,'confirmation render report case binding drift')
    template=template_root/case_id/'input-template.txt'; require(template.is_file(),f'confirmation input template missing: {case_id}')
    template_raw=template.read_bytes(); require(hashlib.sha256(template_raw).hexdigest()==rrows[0].get('confirmationTemplateSha256'),f'confirmation input template hash drift: {case_id}')
    case_dir=output_root/case_id; case_dir.mkdir(parents=True,exist_ok=False)
    inp=resolve_template(template_raw,data_dir=data_dir,output_root=output_root); (case_dir/'input-resolved.txt').write_bytes(inp)
    require(f'mc_randomseed {case["seed"]}'.encode() in inp,'resolved seed drift')
    require(f'mc_photons {case["photonHistories"]}'.encode() in inp,'resolved photon count drift')
    (case_dir/'runtime-report.json').write_bytes(runtime_report.read_bytes()); (case_dir/'randomseed').write_text(f'{case["seed"]}\n')
    prepared={'schemaVersion':1,'stageId':'full-spectrum-estimator-confirmation-v1-prepared','caseId':case_id,'candidateId':case['candidateId'],'geometryId':case['geometryId'],'method':case['method'],'confirmationBlock':case['confirmationBlock'],'seed':case['seed'],'photonHistories':case['photonHistories'],'inputResolvedSha256':hashlib.sha256(inp).hexdigest(),'executionManifestSha256':m['manifestSha256']}
    (case_dir/'prepared.json').write_text(json.dumps(prepared,sort_keys=True,separators=(',',':'))+'\n')
    run=runner or _run; text=inp.decode()
    syntax=run([str(uvspec),'-c'],text,case_dir,60); (case_dir/'syntax-stdout.txt').write_text(str(syntax['stdout'])); (case_dir/'syntax-stderr.txt').write_text(str(syntax['stderr'])); require(not syntax['timedOut'] and syntax['exitCode']==0,'single syntax check failed')
    solver=run([str(uvspec)],text,case_dir,timeout); (case_dir/'solver-stdout.txt').write_text(str(solver['stdout'])); (case_dir/'solver-stderr.txt').write_text(str(solver['stderr'])); require(not solver['timedOut'] and solver['exitCode']==0,'single solver execution failed')
    required=m['artifactContract']['requiredMembersByMethod']['alis-alt-importance']
    for name in required:
        if name=='case-result.json': continue
        p=case_dir/name; require(p.is_file(),f'required raw member missing: {name}')
        if name not in {'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt'}: require(p.stat().st_size>0,f'unexpected empty required raw member: {name}')
    hashes={name:sha(case_dir/name) for name in required if name!='case-result.json'}
    result={'schemaVersion':1,'stageId':'full-spectrum-estimator-confirmation-v1','status':'COMPLETED','caseId':case_id,'candidateId':case['candidateId'],'confirmationBlock':case['confirmationBlock'],'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,'seed':case['seed'],'photonHistories':case['photonHistories'],'inputResolvedSha256':sha(case_dir/'input-resolved.txt'),'runtimeReportRawSha256':sha(case_dir/'runtime-report.json'),'radianceOutputSha256':sha(case_dir/'mc.rad.spc'),'stdRadianceOutputSha256':sha(case_dir/'mc.rad.std.spc'),'rawMemberSha256ByBasename':hashes}
    result['contentSha256']=canon(result); (case_dir/'case-result.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n'); return result

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--repository-root',type=Path,required=True); p.add_argument('--execution-manifest',type=Path,required=True); p.add_argument('--render-report',type=Path,required=True); p.add_argument('--template-root',type=Path,required=True); p.add_argument('--case-id',required=True); p.add_argument('--data-dir',type=Path,required=True); p.add_argument('--output-root',type=Path,required=True); p.add_argument('--uvspec',type=Path,required=True); p.add_argument('--runtime-report',type=Path,required=True); p.add_argument('--timeout-seconds',type=int,default=1800); p.add_argument('--allow-execution',action='store_true'); p.add_argument('--expected-dispatch-branch',required=True); a=p.parse_args()
    try:
        print(json.dumps(execute_case(repository_root=a.repository_root,manifest_path=a.execution_manifest,render_report_path=a.render_report,template_root=a.template_root,case_id=a.case_id,data_dir=a.data_dir,output_root=a.output_root,uvspec=a.uvspec,runtime_report=a.runtime_report,timeout=a.timeout_seconds,allow_execution=a.allow_execution,expected_dispatch_branch=a.expected_dispatch_branch),sort_keys=True)); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
