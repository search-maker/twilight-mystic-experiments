#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import numpy as np

TARGET_ROWS=[23,24,25]
FIVE_ROWS=[22,23,24,25,26]
REPLICATES=[1,2,3,4,5,6]
NEW_STAGE='taylor-timing-derivative-200k-v1'
PRIOR_STAGE='taylor-broadband-photon-scaling-200k-v1'


def find_one(root:Path,name:str)->Path:
    p=list(root.rglob(name))
    if len(p)!=1: raise RuntimeError(f'expected one {name}, got {len(p)}')
    return p[0]


def sample_stats(vals):
    x=[float(v) for v in vals]
    if len(x)!=6 or any(not math.isfinite(v) for v in x): raise RuntimeError('expected exactly six finite values')
    m=statistics.mean(x); sd=statistics.stdev(x)
    return {'values':x,'mean':m,'sampleSd':sd,'se':sd/math.sqrt(6.0),'min':min(x),'max':max(x)}


def load_results(root:Path,stage:str,rows):
    out={}
    for p in root.rglob('row-replicate-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')!=stage or x.get('status')!='COMPLETED': continue
        key=(int(x['row']),int(x['replicate']))
        if key in out: raise RuntimeError(f'duplicate result {key} for {stage}')
        out[key]=x
    expected={(r,q) for r in rows for q in REPLICATES}
    if set(out)!=expected: raise RuntimeError(f'{stage}: exact result universe mismatch: {sorted(out)}')
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--new-neighbor-results-root',type=Path,required=True); ap.add_argument('--prior-200k-results-root',type=Path,required=True); ap.add_argument('--legacy-analysis-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    new=load_results(a.new_neighbor_results_root,NEW_STAGE,[22,26]); prior=load_results(a.prior_200k_results_root,PRIOR_STAGE,[23,24,25]); allres={**new,**prior}
    if set(allres)!={(r,q) for r in FIVE_ROWS for q in REPLICATES}: raise RuntimeError('combined five-row result universe mismatch')
    if any(int(x['photonsPerRay'] if 'photonsPerRay' in x else x['photonsPerRayPerCondition'])!=200_000 for x in allres.values()): raise RuntimeError('mixed photon budget')

    legacy_metrics=json.loads(find_one(a.legacy_analysis_root,'metrics.json').read_text())
    q0=float(legacy_metrics['zeroPoint']['qVegaSurfaceBrightness0MagArcsec2'])
    if not math.isfinite(q0) or q0<=0: raise RuntimeError('invalid immutable Vega SQM zero point')
    with find_one(a.legacy_analysis_root,'comparison.csv').open(newline='') as f: legacy={int(r['row']):r for r in csv.DictReader(f)}
    if set(legacy)!=set(range(1,33)): raise RuntimeError('legacy Taylor comparison universe mismatch')

    times=[]; mean_q={}; mean_mag={}; row_q_stats={}
    for row in FIVE_ROWS:
        vals=[float(allres[(row,rep)]['defaultQ']) for rep in REPLICATES]
        s=sample_stats(vals); row_q_stats[row]=s; mean_q[row]=s['mean']; mean_mag[row]=-2.5*math.log10(s['mean']/q0)
        times.append(__import__('datetime').datetime.fromisoformat(legacy[row]['utc'].replace('Z','+00:00')).timestamp())
    mags=np.array([mean_mag[r] for r in FIVE_ROWS],float); ts=np.array(times,float); central_grad=np.gradient(mags,ts)
    central={row:float(central_grad[i]) for i,row in enumerate(FIVE_ROWS)}

    replicate_grad={row:[] for row in FIVE_ROWS}
    replicate_timing={row:[] for row in FIVE_ROWS}
    for rep in REPLICATES:
        rmags=np.array([-2.5*math.log10(float(allres[(row,rep)]['defaultQ'])/q0) for row in FIVE_ROWS],float)
        g=np.gradient(rmags,ts)
        for i,row in enumerate(FIVE_ROWS):
            replicate_grad[row].append(float(g[i])); replicate_timing[row].append(abs(float(g[i]))*30.0)

    rows=[]; details={}
    for row in TARGET_ROWS:
        dg=sample_stats(replicate_grad[row]); tg=sample_stats(replicate_timing[row]); new_sigma=abs(central[row])*30.0; legacy_sigma=float(legacy[row]['sigma_timing'])
        rec={'row':row,'utc':legacy[row]['utc'],'sunAltGeometricDeg':float(legacy[row]['sun_alt_geometric_deg']),'sixSeed200kMeanQ':mean_q[row],'sixSeed200kMeanModelMag':mean_mag[row],'centralDmagDtMagPerSecond':central[row],'centralDmagDtMagPerMinute':central[row]*60.0,'renewedTimingSigmaMagFor30s':new_sigma,'legacyTimingSigmaMagFor30s':legacy_sigma,'newMinusLegacyTimingSigmaMag':new_sigma-legacy_sigma,'replicateDerivativeMeanMagPerSecond':dg['mean'],'replicateDerivativeSampleSdMagPerSecond':dg['sampleSd'],'replicateDerivativeSeMagPerSecond':dg['se'],'replicateTimingSigmaMeanMag':tg['mean'],'replicateTimingSigmaSampleSdMag':tg['sampleSd'],'replicateTimingSigmaSeMag':tg['se']}; rows.append(rec); details[str(row)]={'central':rec,'replicateSignedDerivative':dg,'replicateTimingSigma':tg}

    with (a.output/'row-summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    out={'schemaVersion':1,'stageId':NEW_STAGE,'status':'TIMING_DERIVATIVE_EMPIRICAL_AUDIT_COMPLETE','fiveRowUniverse':FIVE_ROWS,'targetRows':TARGET_ROWS,'replicates':REPLICATES,'photonBudgetPerRay':200_000,'immutableVegaSqmQ0':q0,'rowMeanQ':{str(r):row_q_stats[r] for r in FIVE_ROWS},'rows':details,'boundary':'Numerical reconvergence of the exact Taylor-v1 numpy.gradient model-time derivative at rows23-25 using six-seed 200k default-atmosphere results. The +/-30 s observation timing contract is unchanged; no residual fitting or physical model change.'}; (a.output/'metrics.json').write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n')
    lines=['# Taylor late-primary timing-derivative 200k reconvergence','', 'Exact Taylor-v1 `numpy.gradient(model_mag, timestamp)` reconstructed on rows22-26 using six-seed 200k mean Q at every row.','', '|row|legacy timing sigma|renewed timing sigma|difference|dmag/dt (mag/min)|replicate SD of timing sigma|','|---:|---:|---:|---:|---:|---:|']
    for r in rows: lines.append(f"|{r['row']}|{r['legacyTimingSigmaMagFor30s']:.5f}|{r['renewedTimingSigmaMagFor30s']:.5f}|{r['newMinusLegacyTimingSigmaMag']:+.5f}|{r['centralDmagDtMagPerMinute']:+.5f}|{r['replicateTimingSigmaSampleSdMag']:.5f}|")
    lines += ['','**Boundary:** the observer timestamp uncertainty remains +/-30 s. Only the model derivative used to propagate it is reconverged.']; (a.output/'report.md').write_text('\n'.join(lines)+'\n'); print((a.output/'report.md').read_text())
if __name__=='__main__': main()
