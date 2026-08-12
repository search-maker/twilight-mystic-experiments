#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from common_v1 import *
ORD=re.compile(r'ordinal[-_]?([1-9][0-9]*)',re.I)
def flatten_list(p):
    x=json.loads(p.read_text()); require(isinstance(x,list),'pages malformed'); return [r for page in x for r in page]
def flatten_obj(p,key):
    x=json.loads(p.read_text()); require(isinstance(x,list),'pages malformed'); return [r for page in x for r in page.get(key,[])]
def consumed(branches,runs):
    out=[]
    for name in [str(x.get('name') or '') for x in branches]+[str(x.get('head_branch') or '') for x in runs if x.get('event')=='push']:
        if name.startswith('dispatch/'):
            m=ORD.search(name)
            if m: out.append(int(m.group(1)))
    return out
def build(contract,variant,branches,runs,artifacts):
    verify_self(contract,'contractSha256'); spec=contract['sourcePreregistrations'][variant]; ords=consumed(branches,runs); require(ords,'no consumed ordinal history found'); latest=max(ords); nexto=latest+1
    seeds=set(spec['seeds']); branch_text='\n'.join(str(x.get('name') or '') for x in branches); run_text='\n'.join(json.dumps(x,sort_keys=True) for x in runs); art_text='\n'.join(json.dumps(x,sort_keys=True) for x in artifacts)
    prefix=f'training-continuation-{variant}'
    require(prefix not in branch_text.lower(),'variant branch/ref collision already exists'); scientific_runs=[int(x.get('id') or 0) for x in runs if x.get('event')=='push' and prefix in json.dumps(x).lower()]; require(not scientific_runs,f'prior scientific push run exists: {scientific_runs}'); scientific_artifacts=[{'id':x.get('id'),'name':x.get('name')} for x in artifacts if prefix in str(x.get('name') or '').lower()]; require(not scientific_artifacts,f'prior scientific artifact exists: {scientific_artifacts}')
    out={'schemaVersion':1,'reportId':f'public-tier1-training-continuation-{variant}-preauthorization-review-v1','status':'PREAUTHORIZATION_SURFACE_CLEAN_NOT_ALLOCATED','variant':variant,'transportContractSha256':contract['contractSha256'],'candidateSeedCount':len(seeds),'candidateSeedRange':[min(seeds),max(seeds)],'latestConsumedScientificOrdinal':latest,'nextAvailableScientificOrdinalIfAllocatedLater':nexto,'authorizationOrdinalAllocated':False,'authorizationRefAllocated':False,'executionKeyAllocated':False,'dispatchBranchAllocated':False,'scientificExecutionAuthorized':False,'dispatchAuthorized':False,'repositoryGlobalBranchesInspected':True,'repositoryGlobalActionsRunsInspected':True,'repositoryGlobalActionsArtifactsInspected':True,'note':'Fresh report only. It does not allocate the reported ordinal and must be repeated after transport merge immediately before authorization.'}; out['reportSha256']=canon(out); return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--contract',type=Path,required=True); p.add_argument('--variant',choices=['train0014','train0037'],required=True); p.add_argument('--branches-pages',type=Path,required=True); p.add_argument('--runs-pages',type=Path,required=True); p.add_argument('--artifacts-pages',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=build(load(a.contract),a.variant,flatten_list(a.branches_pages),flatten_obj(a.runs_pages,'workflow_runs'),flatten_obj(a.artifacts_pages,'artifacts')); a.output.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o,sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)})); return 2
if __name__=='__main__': raise SystemExit(main())
