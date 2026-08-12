#!/usr/bin/env python3
from pathlib import Path
import json,tempfile,sys
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
from common_v1 import *
from analyze_normalized_evidence_v1 import analyze

def main():
    tc=load(HERE/'transport-contract.v1.json'); verify_self(tc,'contractSha256'); ac=load(HERE/'analysis-contract.v1.json'); verify_self(ac,'analysisContractSha256')
    assert tc['status']=='REVIEW_ONLY_DISABLED_TRANSPORT_NOT_AUTHORIZED'; assert all(v is False for v in tc['transportBoundary'].values()); assert tc['workflowSurface']['scientificExecutionWorkflowIncluded'] is False
    for name in ('authorization-template.train0014.v1.json','authorization-template.train0037.v1.json'):
        t=load(HERE/name); verify_self(t,'templateSha256'); assert t['enabled'] is False and t['authorizationOrdinal'] is None and t['scientificExecutionAuthorized'] is False and t['dispatchAuthorized'] is False
    rows=[]
    vals={'photopicLuminanceCdM2':[1,1,1,1],'scotopicLuminanceScotCdM2':[2,2,2,2],'johnsonVEffectiveRadiance_mW_m2_nm_sr':[3,3,3,3]}
    for i in range(4): rows.append({'caseId':f'x{i}','block':i+1,'importanceCenterNm':600.0,'channels':{k:v[i] for k,v in vals.items()}})
    ev={'status':'NORMALIZED_ATTEMPT1_FRESH_EVIDENCE','variant':'train0014','analysisContractSha256':ac['analysisContractSha256'],'cases':rows}; ev['evidenceSha256']=canon(ev); o=analyze(ev,ac); assert o['result']['classification']=='FRESH_TRAINING_PRECISION_AT_FINAL_TARGET'; assert o['result']['automaticTrainingAdmission'] is False
    rows[0]['channels']['photopicLuminanceCdM2']=0.0; ev['evidenceSha256']=canon({k:v for k,v in ev.items() if k!='evidenceSha256'}); o=analyze(ev,ac); assert o['result']['classification']=='FRESH_TRAINING_PRECISION_NOT_ESTABLISHED' and o['result']['anyExactZeroPrimaryBlock'] is True
    # train0037 no auto selection and historical/pairwise screens frozen
    rr=[]; hist=ac['train0037']['historicalPrimaryChannelMeans']
    for center in (500.0,550.0,600.0):
        for b in range(1,5): rr.append({'caseId':f'{center}-{b}','block':b,'importanceCenterNm':center,'channels':dict(hist)})
    ev={'status':'NORMALIZED_ATTEMPT1_FRESH_EVIDENCE','variant':'train0037','analysisContractSha256':ac['analysisContractSha256'],'cases':rr}; ev['evidenceSha256']=canon(ev); o=analyze(ev,ac); assert all(x['classification']=='CENTER_PRECISION_AT_FINAL_TARGET' for x in o['result']['centers'].values()); assert o['result']['automaticCenterSelection'] is False and o['result']['separatePostComparisonDecisionRequired'] is True
    # hash mutation refusal
    bad=dict(tc); bad['status']='x'
    try: verify_self(bad,'contractSha256'); raise AssertionError('mutation accepted')
    except Refusal: pass
    print('PASS: training continuation transport/analysis contract tests')
if __name__=='__main__': main()
