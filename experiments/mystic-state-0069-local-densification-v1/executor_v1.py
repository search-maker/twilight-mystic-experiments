#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, os, re, sys
from pathlib import Path

STAGE1_REL=Path('experiments/tier2-stage1-execution-v1/executor_v1.py')
BRANCH_RE=re.compile(r'^dispatch/mystic-state-0069-ordinal23-v1$')
GRID_SHA='b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
STAGE_ID='mystic-state-0069-local-densification-execution-v1'
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def module(name:str,path:Path):
    s=importlib.util.spec_from_file_location(name,path); req(s is not None and s.loader is not None,f'load failure {path}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def parse_full_spectrum(path:Path):
    toks=[]; rad=[]
    for line in path.read_text(encoding='utf-8',errors='strict').splitlines():
        p=line.split()
        if not p: continue
        req(len(p)>=2 and re.fullmatch(r'[0-9]+\.[0-9]{5}',p[0]) is not None,'spectrum serialization drift')
        row=[float(x) for x in p]; req(all(math.isfinite(x) for x in row) and all(x>=0 for x in row[1:]),'invalid spectrum value'); toks.append(p[0]); rad.append(row[-1])
    req(len(toks)==8001 and toks[0]=='380.00000' and toks[-1]=='780.00000','raw spectrum grid/count drift')
    req(hashlib.sha256(('\n'.join(toks)+'\n').encode()).hexdigest()==GRID_SHA,'raw spectrum token grid drift'); return [float(x) for x in toks],rad

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--runtime-report',type=Path,required=True); p.add_argument('--adapter',type=Path,required=True); p.add_argument('--case-id',required=True); p.add_argument('--data-dir',type=Path,required=True); p.add_argument('--repository-root',type=Path,required=True); p.add_argument('--uvspec',type=Path,required=True); p.add_argument('--output-root',type=Path,required=True); p.add_argument('--timeout-seconds',type=int,required=True); p.add_argument('--expected-dispatch-branch',required=True); p.add_argument('--allow-execution',action='store_true'); a=p.parse_args()
    base=module('m0069_stage1_executor',a.repository_root/STAGE1_REL); base.BRANCH_RE=BRANCH_RE; base.STAGE_ID=STAGE_ID; base.parse_full_spectrum=parse_full_spectrum
    try:
        r=base.execute_case(a.manifest,a.runtime_report,a.adapter,a.case_id,a.data_dir,a.repository_root,a.uvspec,a.output_root,a.timeout_seconds,a.allow_execution,a.expected_dispatch_branch); r.pop('contentSha256',None); r['stageId']=STAGE_ID; r['protectedHoldoutValueExposed']=False; r['modelFittingSurfaceExposed']=False; r['contentSha256']=base.canon(r); d=a.output_root/a.case_id; (d/'case-result.json').write_text(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8'); print(json.dumps(r,sort_keys=True)); return 0
    except Exception as e:
        f={'schemaVersion':1,'stageId':STAGE_ID,'status':'FAILED_OR_REFUSED_TERMINAL_ATTEMPT1','caseId':a.case_id,'workflowRunAttempt':int(os.getenv('GITHUB_RUN_ATTEMPT') or 0),'retryPerformed':False,'resumePerformed':False,'githubRerun':False,'reason':str(e),'protectedHoldoutValueExposed':False,'modelFittingSurfaceExposed':False}; f['contentSha256']=base.canon(f)
        try:
            d=a.output_root/a.case_id; d.mkdir(parents=True,exist_ok=True); (d/'case-result.json').write_text(json.dumps(f,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        except Exception: pass
        print(json.dumps(f,sort_keys=True),file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
