#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, os, re, sys, tempfile
from pathlib import Path
from typing import Any, Callable
STAGE_ID='public-tier2-v1-core-stage1-execution-v1'; BRANCH_RE=re.compile(r'^dispatch/tier2-stage1-ordinal[1-9][0-9]*-v3$'); HIST_REL=Path('experiments/full-spectrum-estimator-pilot-v2/executor.py')
class Refusal(RuntimeError):pass
def req(c:bool,m:str)->None:
    if not c:raise Refusal(m)
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v:Any)->str:return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8'));req(isinstance(x,dict),f'object required: {p}');return x
def module(name:str,path:Path):
    req(path.is_file(),f'reviewed reference missing: {path}');s=importlib.util.spec_from_file_location(name,path);req(s is not None and s.loader is not None,f'reference load failure: {path}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def validate_context(allow_execution:bool,expected_dispatch_branch:str)->None:
    req(allow_execution,'--allow-execution required');req(BRANCH_RE.fullmatch(expected_dispatch_branch) is not None,'invalid expected dispatch branch');expected={'GITHUB_ACTIONS':'true','GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1','GITHUB_REF_NAME':expected_dispatch_branch};stale={k:(os.getenv(k),v) for k,v in expected.items() if os.getenv(k)!=v};req(not stale,f'not exact attempt-1 authorized push context: {stale}')
def parse_full_spectrum(path:Path)->tuple[list[float],list[float]]:
    wl=[];rad=[]
    for line in path.read_text(encoding='utf-8',errors='strict').splitlines():
        p=line.split()
        if len(p)<2:continue
        try:w=float(p[0]);v=float(p[-1])
        except ValueError:continue
        req(math.isfinite(w) and math.isfinite(v) and v>=0.0,'invalid raw spectrum value');wl.append(w);rad.append(v)
    req(len(wl)==8001 and abs(wl[0]-380.0)<1e-8 and abs(wl[-1]-780.0)<1e-8,'raw spectrum grid/count drift');req(all(wl[i+1]>wl[i] and abs((wl[i+1]-wl[i])-0.05)<1e-7 for i in range(len(wl)-1)),'raw spectrum step/order drift');return wl,rad
def compatibility_manifest(m:dict[str,Any],c:dict[str,Any])->dict[str,Any]:
    return {'manifestSha256':m['manifestSha256'],'runtimeIdentityRequired':m['runtimeIdentityRequired'],'cases':[{'caseId':c['caseId'],'geometryId':c['geometryId'],'method':'alis','replicate':c['block'],'seed':c['seed'],'photonHistories':c['photonHistories']}],'artifactContract':{'requiredMembersByMethod':{'alis':m['artifactContract']['requiredMembers']}}}
def execute_case(manifest_path:Path,runtime_path:Path,adapter_path:Path,case_id:str,data_dir:Path,repository_root:Path,uvspec:Path,output_root:Path,timeout_seconds:int,allow_execution:bool,expected_dispatch_branch:str,runner:Callable[...,dict[str,Any]]|None=None)->dict[str,Any]:
    validate_context(allow_execution,expected_dispatch_branch);req(timeout_seconds>0,'invalid timeout')
    m=load(manifest_path);rows=[c for c in m.get('cases',[]) if c.get('caseId')==case_id];req(len(rows)==1,'case not unique');c=rows[0];a=module('tier2_stage1_adapter',adapter_path);h=module('tier2_historical_executor',repository_root/HIST_REL);captured={}
    with tempfile.TemporaryDirectory(prefix='tier2-stage1-compat-') as td:
        compat=Path(td);(compat/'full-spectrum-estimator-pilot-execution-manifest-v4.json').write_text(json.dumps(compatibility_manifest(m,c),sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8');h.REVIEW_REL=compat;h.DISPATCH_BRANCH_RE=BRANCH_RE
        def resolve_input(_repository_root:Path,_case_id:str,_data_dir:Path,_output_root:Path)->bytes:
            case_dir=_output_root/_case_id;text,p=a.render_case(manifest_path,runtime_path,_case_id,_data_dir,_repository_root,case_dir);captured['prepared']=p;return text.encode()
        h.resolve_input=resolve_input
        prior=h.execute_case(repository_root,case_id,data_dir,output_root,uvspec,runtime_path,timeout_seconds,allow_execution,runner=runner,expected_dispatch_branch=expected_dispatch_branch)
    req(prior.get('workflowRunAttempt')==1 and prior.get('syntaxCheckCount')==1 and prior.get('solverExecutionCount')==1 and prior.get('retryPerformed') is False and prior.get('resumePerformed') is False and prior.get('githubRerun') is False,'historical executor one-use boundary drift');req('prepared' in captured,'adapter preparation evidence missing')
    case_dir=output_root/case_id;(case_dir/'prepared.json').write_text(json.dumps(captured['prepared'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8');required=m['artifactContract']['requiredMembers']
    for name in required:
        if name=='case-result.json':continue
        p=case_dir/name;req(p.is_file(),f'required raw member missing: {name}')
        if name not in {'syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt'}:req(p.stat().st_size>0,f'unexpected empty raw member: {name}')
    wl,rad=parse_full_spectrum(case_dir/'mc.rad.spc');swl,_=parse_full_spectrum(case_dir/'mc.rad.std.spc');req(wl==swl,'radiance/std wavelength grid mismatch');raw_hash={name:sha(case_dir/name) for name in required if name!='case-result.json'};p=captured['prepared']
    result={'schemaVersion':1,'stageId':STAGE_ID,'status':'COMPLETED','caseId':case_id,'geometryId':c['geometryId'],'block':c['block'],'role':c['role'],'workflowRunAttempt':1,'syntaxCheckCount':1,'solverExecutionCount':1,'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'syntaxExitCode':0,'solverExitCode':0,'syntaxTimedOut':False,'solverTimedOut':False,'seed':c['seed'],'photonHistories':c['photonHistories'],'executionManifestSha256':m['manifestSha256'],'inputResolvedSha256':p['inputResolvedSha256'],'physicalInputCanonicalSha256':p['physicalInputCanonicalSha256'],'runtimeReportRawSha256':sha(case_dir/'runtime-report.json'),'radianceOutputSha256':sha(case_dir/'mc.rad.spc'),'stdRadianceOutputSha256':sha(case_dir/'mc.rad.std.spc'),'rawMemberSha256ByBasename':raw_hash,'rawSpectrumNodeCount':8001,'rawAllZero':all(v==0.0 for v in rad),'historicalExecutorPath':HIST_REL.as_posix(),'fittingSurfaceExposed':False,'protectedHoldoutValueExposed':False};result['contentSha256']=canon(result);(case_dir/'case-result.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8');return result
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--runtime-report',type=Path,required=True);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--case-id',required=True);p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--repository-root',type=Path,required=True);p.add_argument('--uvspec',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--timeout-seconds',type=int,required=True);p.add_argument('--expected-dispatch-branch',required=True);p.add_argument('--allow-execution',action='store_true');a=p.parse_args()
    try:print(json.dumps(execute_case(a.manifest,a.runtime_report,a.adapter,a.case_id,a.data_dir,a.repository_root,a.uvspec,a.output_root,a.timeout_seconds,a.allow_execution,a.expected_dispatch_branch),sort_keys=True));return 0
    except Exception as e:
        failure={'schemaVersion':1,'stageId':STAGE_ID,'status':'FAILED_OR_REFUSED_TERMINAL_ATTEMPT1','caseId':a.case_id,'workflowRunAttempt':int(os.getenv('GITHUB_RUN_ATTEMPT') or 0),'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'reason':str(e),'protectedHoldoutValueExposed':False};failure['contentSha256']=canon(failure)
        try:d=a.output_root/a.case_id;d.mkdir(parents=True,exist_ok=True);(d/'case-result.json').write_text(json.dumps(failure,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        except Exception:pass
        print(json.dumps(failure,sort_keys=True),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
