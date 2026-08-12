#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
MANIFEST_SHA='9344ed18cfa93849d730cf080fe9f6c4c57f0cc5ea7b1be7ba9aa15d501c3fa8'
ACQ_ID='public-tier1-full-spectrum-estimator-confirmation-acquisition-manifest-v1'
PREFIX='full-spectrum-estimator-confirmation-v1-case-'
class Refusal(RuntimeError): pass
def require(c,m):
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path): return json.loads(p.read_text())
def build(manifest,artifacts_json,zip_dir:Path,run_id:int,run_attempt:int,ordinal:int,head_sha:str):
    require(manifest.get('manifestSha256')==MANIFEST_SHA and manifest.get('caseCount')==24,'confirmation execution manifest drift')
    require(run_attempt==1 and ordinal==17 and len(head_sha)==40,'source run identity drift')
    cases={c['caseId']:c for c in manifest['cases']}; arts=artifacts_json.get('artifacts',[])
    selected=[a for a in arts if str(a.get('name') or '').startswith(PREFIX)]
    require(len(selected)==24,'expected exactly 24 confirmation case artifacts')
    by_name={a['name']:a for a in selected}; require(len(by_name)==24,'duplicate confirmation artifact names')
    rows=[]
    for case in manifest['cases']:
        cid=case['caseId']; name=PREFIX+cid; require(name in by_name,f'missing confirmation artifact: {cid}'); a=by_name[name]
        require(a.get('expired') is False,'confirmation artifact expired')
        aid=a.get('id'); require(isinstance(aid,int) and aid>0,'confirmation artifact id missing')
        p=zip_dir/(name+'.zip'); require(p.is_file(),f'downloaded confirmation ZIP missing: {cid}'); zsha=sha(p)
        require(a.get('digest')=='sha256:'+zsha,f'GitHub/downloaded ZIP digest mismatch: {cid}')
        rows.append({'caseId':cid,'artifactId':aid,'artifactName':name,'githubDigest':a['digest'],'zipSha256':zsha})
    out={'schemaVersion':1,'acquisitionId':ACQ_ID,'acquisitionSha256':None,'executionManifestSha256':MANIFEST_SHA,'sourceRunId':run_id,'sourceRunAttempt':1,'sourceOrdinal':17,'sourceHeadSha':head_sha,'caseCount':24,'cases':rows}
    out['acquisitionSha256']=canon(out); return out

def main():
    p=argparse.ArgumentParser(); p.add_argument('--execution-manifest',type=Path,required=True); p.add_argument('--artifacts-json',type=Path,required=True); p.add_argument('--zip-dir',type=Path,required=True); p.add_argument('--source-run-id',type=int,required=True); p.add_argument('--source-run-attempt',type=int,required=True); p.add_argument('--source-ordinal',type=int,required=True); p.add_argument('--source-head-sha',required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        v=build(load(a.execution_manifest),load(a.artifacts_json),a.zip_dir,a.source_run_id,a.source_run_attempt,a.source_ordinal,a.source_head_sha); a.output.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':'PASSED','caseCount':24,'acquisitionSha256':v['acquisitionSha256']},sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
