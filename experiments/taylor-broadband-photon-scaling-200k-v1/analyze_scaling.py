#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ROWS=[23,24,25]
REPLICATES=[1,2,3,4,5,6]
STAGE='taylor-broadband-photon-scaling-200k-v1'
PHOTONS=200_000
MAG_FACTOR=2.5/math.log(10.0)


def stats(vals):
    x=[float(v) for v in vals]
    if len(x)!=6 or any(not math.isfinite(v) for v in x): raise RuntimeError('expected exactly six finite values')
    m=statistics.mean(x); sd=statistics.stdev(x)
    return {'values':x,'n':6,'mean':m,'sampleSd':sd,'se':sd/math.sqrt(6.0),'cv':sd/abs(m),'min':min(x),'max':max(x)}


def p90(vals):
    x=sorted(float(v) for v in vals)
    return x[int(0.9*(len(x)-1))]


def find_one(root:Path,name:str):
    p=list(root.rglob(name))
    if len(p)!=1: raise RuntimeError(f'expected one {name}, got {len(p)}')
    return p[0]


def load_200(root:Path):
    out={}
    for p in root.rglob('row-replicate-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')!=STAGE or x.get('status')!='COMPLETED': continue
        key=(int(x['row']),int(x['replicate']))
        if key in out: raise RuntimeError(f'duplicate 200k result {key}')
        out[key]=x
    expected={(r,q) for r in ROWS for q in REPLICATES}
    if set(out)!=expected: raise RuntimeError(f'exact 200k result universe mismatch: {sorted(out)}')
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--reference-50k-root',type=Path,required=True); ap.add_argument('--results-200k-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=False)

    metrics50=json.loads(find_one(a.reference_50k_root,'metrics.json').read_text())
    if metrics50.get('stageId')!='taylor-broadband-mc-repro-v1' or metrics50.get('status')!='EMPIRICAL_BETWEEN_SEED_AUDIT_COMPLETE': raise RuntimeError('wrong immutable 50k reference stage')
    if metrics50.get('rowUniverse')!=ROWS or metrics50.get('replicateUniverse')!=REPLICATES or int(metrics50.get('photonBudgetPerRayPerCondition',-1))!=50_000: raise RuntimeError('wrong immutable 50k universe')

    with find_one(a.reference_50k_root,'ray-summary.csv').open(newline='') as f:
        ray50={(int(r['row']),int(r['rayIndex'])):r for r in csv.DictReader(f)}
    if set(ray50)!={(row,ray) for row in ROWS for ray in range(1,65)}: raise RuntimeError('wrong 50k ray-summary universe')

    res=load_200(a.results_200k_root)
    row_records=[]; ray_records=[]; detailed={}
    for row in ROWS:
        rr=[res[(row,rep)] for rep in REPLICATES]
        if any(int(x['photonsPerRay'])!=PHOTONS or int(x['rayCount'])!=64 for x in rr): raise RuntimeError(f'row {row}: 200k case metadata drift')
        qstats=stats([x['defaultQ'] for x in rr])
        sig=[float(x['defaultQStdConservative']) for x in rr]
        medsig=statistics.median(sig)
        ref=metrics50['rows'][str(row)]['defaultQ']
        mean50=float(ref['mean']); sd50=float(ref['sampleSd']); se50=float(ref['se']); cv50=float(ref['cv'])
        ratio=qstats['sampleSd']/sd50
        cvratio=qstats['cv']/cv50
        mean_diff=qstats['mean']-mean50
        combined_se=math.sqrt(qstats['se']**2+se50**2)
        mean_z=None if combined_se==0 else mean_diff/combined_se
        mag_sd=MAG_FACTOR*qstats['sampleSd']/qstats['mean']

        byr={rep:{int(x['rayIndex']):x for x in res[(row,rep)]['rays']} for rep in REPLICATES}
        ratios=[]
        for ray in range(1,65):
            vals=[float(byr[rep][ray]['q']) for rep in REPLICATES]
            s200=statistics.stdev(vals)
            s50=float(ray50[(row,ray)]['defaultQSampleSdSixSeeds'])
            if s50<=0: raise RuntimeError(f'row {row} ray {ray}: nonpositive 50k empirical SD')
            rat=s200/s50; ratios.append(rat)
            ray_records.append({'row':row,'rayIndex':ray,'sampleSd50k':s50,'sampleSd200k':s200,'sdRatio200kTo50k':rat})
        ray_summary={'median':statistics.median(ratios),'p90NearestRank':p90(ratios),'max':max(ratios),'min':min(ratios)}
        rec={'row':row,'meanQ50k':mean50,'sampleSdQ50k':sd50,'cvQ50k':cv50,'meanQ200k':qstats['mean'],'sampleSdQ200k':qstats['sampleSd'],'seQ200k':qstats['se'],'cvQ200k':qstats['cv'],'magnitudeEquivalentEmpiricalSd200k':mag_sd,'medianReportedQStd200k':medsig,'empiricalSdToMedianReportedSigma200k':None if medsig==0 else qstats['sampleSd']/medsig,'sdRatio200kTo50k':ratio,'cvRatio200kTo50k':cvratio,'sdRatioRelativeToIdealHalf':ratio/0.5,'meanDifference200kMinus50k':mean_diff,'combinedMeanSeIndependentSamples':combined_se,'meanDifferenceOverCombinedSe':mean_z,'raySdRatioMedian':ray_summary['median'],'raySdRatioP90':ray_summary['p90NearestRank'],'raySdRatioMax':ray_summary['max']}
        row_records.append(rec)
        detailed[str(row)]={'reference50k':{'mean':mean50,'sampleSd':sd50,'se':se50,'cv':cv50},'fresh200k':qstats,'reported200kQStdConservative':sig,'magnitudeEquivalentEmpiricalSd200k':mag_sd,'sdRatio200kTo50k':ratio,'cvRatio200kTo50k':cvratio,'sdRatioRelativeToIdealHalf':ratio/0.5,'meanDifference200kMinus50k':mean_diff,'combinedMeanSeIndependentSamples':combined_se,'meanDifferenceOverCombinedSe':mean_z,'raySdRatio200kTo50k':ray_summary}

    with (a.output/'row-summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row_records[0])); w.writeheader(); w.writerows(row_records)
    with (a.output/'ray-summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(ray_records[0])); w.writeheader(); w.writerows(ray_records)
    out={'schemaVersion':1,'stageId':STAGE,'status':'PHOTON_SCALING_50K_TO_200K_COMPLETE','reference50kArtifactId':9634873751,'reference50kArtifactSha256':'f6e36e4310ef5d3c8eb16cd56e0063ad01185e4ebd498ef0789c31609d443a57','referencePhotonBudgetPerRay':50_000,'freshPhotonBudgetPerRay':PHOTONS,'idealIndependentMonteCarloSdRatioForFourfoldPhotonIncrease':0.5,'rows':detailed,'boundary':'Numerical convergence audit only; no Taylor residual scoring, atmosphere fitting/validation, Level-B/F/tau/production, or human-model conclusion.'}
    (a.output/'metrics.json').write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n')
    lines=['# Taylor broadband photon-scaling 50k -> 200k audit','', 'Six independent seeds at each photon budget. The `0.5` SD ratio is a descriptive square-root Monte Carlo reference, not a pass/fail threshold.','', '|row|SD 50k|SD 200k|SD ratio|ratio / 0.5|CV 50k|CV 200k|mag-equiv SD 200k|mean shift / combined SE|ray SD ratio median / p90 / max|','|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in row_records:
        lines.append(f"|{r['row']}|{r['sampleSdQ50k']:.6g}|{r['sampleSdQ200k']:.6g}|{r['sdRatio200kTo50k']:.3f}|{r['sdRatioRelativeToIdealHalf']:.3f}|{100*r['cvQ50k']:.2f}%|{100*r['cvQ200k']:.2f}%|{r['magnitudeEquivalentEmpiricalSd200k']:.4f} mag|{r['meanDifferenceOverCombinedSe']:+.2f}|{r['raySdRatioMedian']:.2f} / {r['raySdRatioP90']:.2f} / {r['raySdRatioMax']:.2f}|")
    lines += ['','**Boundary:** one 4x photon step does not establish a full convergence law. Any further photon budget is a separate preregistered identity.']
    (a.output/'report.md').write_text('\n'.join(lines)+'\n'); print((a.output/'report.md').read_text())

if __name__=='__main__': main()
