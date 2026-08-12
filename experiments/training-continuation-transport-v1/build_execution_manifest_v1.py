#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from common_v1 import *
CASES={'train0014':('caseDesign','cases',4,200000000),'train0037':('comparisonDesign','cases',12,1200000000)}
def build(repo:Path,variant:str,prereg_path:Path,contract_path:Path,analysis_path:Path)->dict:
    c=load(contract_path); verify_self(c,'contractSha256'); ac=load(analysis_path); verify_self(ac,'analysisContractSha256'); require(ac.get('transportContractSha256')==c['contractSha256'],'analysis/transport binding drift'); require(c['status']=='REVIEW_ONLY_DISABLED_TRANSPORT_NOT_AUTHORIZED','transport boundary drift')
    spec=c['sourcePreregistrations'][variant]; p=load(prereg_path); require(p.get('preregistrationSha256')==spec['preregistrationSha256'],'preregistration identity drift')
    rootkey,casekey,count,total=CASES[variant]; cases=(p.get(rootkey) or {}).get(casekey); require(isinstance(cases,list) and len(cases)==count,'case universe drift')
    require(sum(int(x['photonHistories']) for x in cases)==total,'photon budget drift'); require(len({x['seed'] for x in cases})==count,'seed uniqueness drift'); require([x['seed'] for x in cases]==spec['seeds'],'seed set/order drift')
    rows=[]
    for x in cases:
        cid=x['caseId']; path=repo/spec['renderedTemplateRoot']/cid/'input-template.txt'; require(path.is_file(),f'missing frozen template: {cid}'); require(sha_file(path)==x['templateSha256'],f'frozen template hash drift: {cid}')
        rows.append({'caseId':cid,'geometryId':x['geometryId'],'method':x['method'],'importanceCenterNm':float(x['importanceCenterNm']),'block':int(x.get('trainingAcquisitionBlock',x.get('comparisonBlock'))),'seed':int(x['seed']),'photonHistories':int(x['photonHistories']),'templatePath':path.relative_to(repo).as_posix(),'templateSha256':x['templateSha256'],'templatePhysicalFingerprintSha256':x['templatePhysicalFingerprintSha256']})
    m={'schemaVersion':1,'manifestId':f'public-tier1-training-continuation-{variant}-execution-manifest-v1','status':'DISABLED_EXECUTION_MANIFEST_REVIEW_ONLY','variant':variant,'transportContractSha256':c['contractSha256'],'analysisContractSha256':ac['analysisContractSha256'],'preregistrationSha256':spec['preregistrationSha256'],'caseCount':count,'totalPhotonHistories':total,'cases':rows,'executionBoundary':{'authorizationOrdinalAllocated':False,'scientificExecutionAuthorized':False,'dispatchAuthorized':False,'githubRerunAllowed':False,'retryAllowed':False,'resumeAllowed':False}}
    m['manifestSha256']=canon(m); return m
def main():
    a=argparse.ArgumentParser(); a.add_argument('--repository-root',type=Path,required=True); a.add_argument('--variant',choices=CASES,required=True); a.add_argument('--preregistration',type=Path,required=True); a.add_argument('--contract',type=Path,required=True); a.add_argument('--analysis-contract',type=Path,required=True); a.add_argument('--output',type=Path,required=True); z=a.parse_args()
    try: m=build(z.repository_root.resolve(),z.variant,z.preregistration,z.contract,z.analysis_contract); z.output.write_bytes((json.dumps(m,indent=2,sort_keys=True)+'\n').encode('utf-8')); print(json.dumps({'status':'PASSED','manifestSha256':m['manifestSha256'],'caseCount':m['caseCount']})); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)})); return 2
if __name__=='__main__': raise SystemExit(main())
