#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from common_v1 import *
def classify_0014(rows,contract):
    require(len(rows)==4 and {r['block'] for r in rows}=={1,2,3,4},'train0014 block universe drift'); stats={}; any_zero=False
    for ch in PRIMARY:
        vals=[float(r['channels'][ch]) for r in sorted(rows,key=lambda x:x['block'])]; any_zero=any_zero or any(v==0.0 for v in vals)
        try: stats[ch]=sample_stats(vals)
        except Refusal: stats[ch]={'mean':sum(vals)/4.0 if all(math.isfinite(v) for v in vals) else None,'sampleStd':None,'rsem':None}
    rs=[v['rsem'] for v in stats.values()]; bad=any_zero or any(x is None or not math.isfinite(x) or x>0.08 for x in rs)
    if bad: cls='FRESH_TRAINING_PRECISION_NOT_ESTABLISHED'
    elif all(x<=0.05 for x in rs): cls='FRESH_TRAINING_PRECISION_AT_FINAL_TARGET'
    else: cls='FRESH_TRAINING_PRECISION_WITHIN_HISTORICAL_MAXIMUM'
    return {'classification':cls,'statistics':stats,'anyExactZeroPrimaryBlock':any_zero,'automaticTrainingAdmission':False,'automaticExtension':False,'valuesAdmittedAsTrainingLabels':False}
def classify_0037(rows,contract):
    require(len(rows)==12,'train0037 case universe drift'); hist=contract['train0037']['historicalPrimaryChannelMeans']; centers={}
    for center in (500.0,550.0,600.0):
        rr=sorted([r for r in rows if float(r['importanceCenterNm'])==center],key=lambda x:x['block']); require(len(rr)==4 and {r['block'] for r in rr}=={1,2,3,4},f'center {center} block universe drift')
        stats={}; any_zero=False; hist_ok=True
        for ch in PRIMARY:
            vals=[float(r['channels'][ch]) for r in rr]; any_zero=any_zero or any(v==0.0 for v in vals)
            try: s=sample_stats(vals)
            except Refusal: s={'mean':sum(vals)/4.0 if all(math.isfinite(v) for v in vals) else None,'sampleStd':None,'rsem':None}
            stats[ch]=s
            ratio=None if s['mean'] is None else s['mean']/float(hist[ch]); hist_ok=hist_ok and ratio is not None and math.isfinite(ratio) and 0.5<=ratio<=2.0; s['historicalMeanRatio']=ratio
        rs=[x['rsem'] for x in stats.values()]; bad=any_zero or not hist_ok or any(x is None or not math.isfinite(x) or x>0.08 for x in rs)
        cls='CENTER_PRECISION_NOT_ESTABLISHED' if bad else ('CENTER_PRECISION_AT_FINAL_TARGET' if all(x<=0.05 for x in rs) else 'CENTER_PRECISION_WITHIN_HISTORICAL_MAXIMUM')
        centers[str(int(center))]={'classification':cls,'statistics':stats,'anyExactZeroPrimaryBlock':any_zero,'historicalMeanScreenPassed':hist_ok}
    pairwise={}; pairwise_ok=True
    for a,b in ((500,550),(500,600),(550,600)):
        pairwise[f'{a}:{b}']={}
        for ch in PRIMARY:
            ma=centers[str(a)]['statistics'][ch]['mean']; mb=centers[str(b)]['statistics'][ch]['mean']; ratio=None if ma is None or mb is None or mb<=0 else ma/mb; ok=ratio is not None and math.isfinite(ratio) and 0.5<=ratio<=2.0; pairwise_ok=pairwise_ok and ok; pairwise[f'{a}:{b}'][ch]={'ratio':ratio,'passesFrozenScreen':ok}
    return {'centers':centers,'pairwiseMeanScreens':pairwise,'allPairwiseMeanScreensPassed':pairwise_ok,'automaticCenterSelection':False,'automaticTrainingAdmission':False,'comparisonValuesAdmittedAsTrainingLabels':False,'separatePostComparisonDecisionRequired':True,'separateFreshTrainingAcquisitionRequiredAfterAnyLaterNomination':True,'statisticalEquivalenceClaim':False}
def analyze(evidence,contract):
    verify_self(contract,'analysisContractSha256'); require(contract['status']=='REVIEW_ONLY_FROZEN_BEFORE_ANY_FRESH_RESULT','analysis contract boundary drift'); require(evidence.get('status')=='NORMALIZED_ATTEMPT1_FRESH_EVIDENCE','evidence status drift'); require(evidence.get('analysisContractSha256')==contract['analysisContractSha256'],'analysis binding drift'); require(evidence.get('evidenceSha256')==canon({k:v for k,v in evidence.items() if k!='evidenceSha256'}),'normalized evidence self-hash drift'); variant=evidence['variant']; rows=evidence['cases']; body=classify_0014(rows,contract) if variant=='train0014' else classify_0037(rows,contract); out={'schemaVersion':1,'analysisId':f'public-tier1-training-continuation-{variant}-analysis-v1','status':'ANALYZED_WITHOUT_DOWNSTREAM_ADMISSION','variant':variant,'analysisContractSha256':contract['analysisContractSha256'],'normalizedEvidenceSha256':evidence['evidenceSha256'],'result':body,'downstreamBoundary':contract['downstreamBoundary']}; out['analysisSha256']=canon(out); return out
def main():
    p=argparse.ArgumentParser(); p.add_argument('--evidence',type=Path,required=True); p.add_argument('--contract',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try: o=analyze(load(a.evidence),load(a.contract)); a.output.write_text(json.dumps(o,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({'status':'PASSED','analysisSha256':o['analysisSha256']})); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)})); return 2
if __name__=='__main__': raise SystemExit(main())
