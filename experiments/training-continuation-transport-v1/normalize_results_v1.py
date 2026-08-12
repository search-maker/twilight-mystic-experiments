#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,math
from pathlib import Path
from common_v1 import *
V6='8fb7c9eae30e7f2b28fdf67291f682ae2770ea9c'; V7='fe45136d595e6039b355d68cd2a926259af0ac40'
def mod(name,p):
    s=importlib.util.spec_from_file_location(name,p); require(s and s.loader,f'cannot load {p}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def normalize(repo:Path,manifest:dict,rawroot:Path,contract:dict)->dict:
    verify_self(contract,'analysisContractSha256'); verify_self(manifest,'manifestSha256'); require(manifest.get('analysisContractSha256')==contract['analysisContractSha256'],'manifest/analysis binding drift'); require(manifest['status']=='DISABLED_EXECUTION_MANIFEST_REVIEW_ONLY','manifest boundary drift')
    p6=repo/'review/full-spectrum-estimator-pilot-v2/normalize_full_spectrum_estimator_pilot_results_v6.py'; p7=repo/'review/full-spectrum-estimator-pilot-v2/normalize_full_spectrum_estimator_pilot_results_v7.py'; require(git_blob_sha1(p6)==V6 and git_blob_sha1(p7)==V7,'frozen normalizer code identity drift'); v6=mod('tc_v6',p6); v7=mod('tc_v7',p7)
    rows=[]
    for case in manifest['cases']:
        d=rawroot/case['caseId']; required=['case-result.json','prepared.json','input-resolved.txt','runtime-report.json','randomseed','syntax-stdout.txt','syntax-stderr.txt','solver-stdout.txt','solver-stderr.txt','mc.rad.spc','mc.rad.std.spc']; require(d.is_dir(),f'missing case directory: {case["caseId"]}'); require({p.name for p in d.iterdir() if p.is_file()}==set(required),f'exact raw member set drift: {case["caseId"]}')
        r=load(d/'case-result.json'); require(r.get('contentSha256')==canon({k:v for k,v in r.items() if k!='contentSha256'}),'case-result self-hash drift'); require(r.get('status')=='COMPLETED' and r.get('caseId')==case['caseId'],'case result identity/status drift');
        for k,w in [('workflowRunAttempt',1),('syntaxCheckCount',1),('solverExecutionCount',1),('retryPerformed',False),('resumePerformed',False),('githubRerun',False),('seed',case['seed']),('photonHistories',case['photonHistories'])]: require(r.get(k)==w,f'case result drift {case["caseId"]}.{k}')
        inp=(d/'input-resolved.txt').read_bytes(); require(sha_bytes(inp)==r.get('inputResolvedSha256'),'input hash drift'); require(sha_file(d/'runtime-report.json')==r.get('runtimeReportRawSha256'),'runtime report hash drift'); require(f'mc_randomseed {case["seed"]}'.encode() in inp and f'mc_photons {case["photonHistories"]}'.encode() in inp and f'mc_spectral_is {case["importanceCenterNm"]:.1f}'.encode() in inp,'resolved directive drift'); require(v6.physical_fingerprint(inp)==case['templatePhysicalFingerprintSha256'],'physical fingerprint drift')
        wl,rad=v7.parse_spectrum_v7((d/'mc.rad.spc').read_bytes(),8001,0.05); swl,srad=v7.parse_spectrum_v7((d/'mc.rad.std.spc').read_bytes(),8001,0.05); require(wl==swl,'std grid drift'); require(all(math.isfinite(x) and x>=0 for x in rad+srad),'invalid spectrum value'); ch=v6.channels(wl,rad); require(set(ch)==set(PRIMARY),'channel surface drift'); require(all(math.isfinite(float(v)) and float(v)>=0 for v in ch.values()),'invalid channel value')
        rows.append({'caseId':case['caseId'],'geometryId':case['geometryId'],'method':case['method'],'importanceCenterNm':case['importanceCenterNm'],'block':case['block'],'seed':case['seed'],'photonHistories':case['photonHistories'],'channels':ch,'zeroHitByChannel':{k:float(ch[k])==0.0 for k in PRIMARY}})
    out={'schemaVersion':1,'evidenceId':f'public-tier1-training-continuation-{manifest["variant"]}-normalized-evidence-v1','status':'NORMALIZED_ATTEMPT1_FRESH_EVIDENCE','variant':manifest['variant'],'analysisContractSha256':contract['analysisContractSha256'],'executionManifestSha256':manifest['manifestSha256'],'caseCount':len(rows),'cases':rows,'exactZeroPreserved':True,'epsilonSubstitutionUsed':False,'holdoutValuesRead':False}; out['evidenceSha256']=canon(out); return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--repository-root',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--raw-root',type=Path,required=True); p.add_argument('--contract',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:o=normalize(a.repository_root.resolve(),load(a.manifest),a.raw_root,load(a.contract)); a.output.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':'PASSED','evidenceSha256':o['evidenceSha256']})); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)})); return 2
if __name__=='__main__': raise SystemExit(main())
