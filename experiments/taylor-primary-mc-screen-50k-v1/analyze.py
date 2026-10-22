#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math,statistics
from pathlib import Path
ANCHORS=[1,5,9,13,17,21]; REPLICATES=[1,2,3,4,5,6]; STAGE='taylor-primary-mc-screen-50k-v1'; REPEATABILITY=0.0621462261; MAG_FACTOR=2.5/math.log(10.0)

def stats(vals):
    x=[float(v) for v in vals]
    if len(x)!=6 or any(not math.isfinite(v) for v in x): raise RuntimeError('expected exactly six finite values')
    m=statistics.mean(x); sd=statistics.stdev(x)
    return {'values':x,'mean':m,'sampleSd':sd,'se':sd/math.sqrt(6.0),'cv':sd/abs(m),'min':min(x),'max':max(x)}

def find_one(root,name):
    p=list(root.rglob(name))
    if len(p)!=1: raise RuntimeError(f'expected one {name}, got {len(p)}')
    return p[0]

def load_new(root):
    out={}
    for p in root.rglob('row-replicate-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')!=STAGE or x.get('status')!='COMPLETED': continue
        key=(int(x['row']),int(x['replicate']))
        if key in out: raise RuntimeError(f'duplicate {key}')
        out[key]=x
    expected={(r,q) for r in ANCHORS for q in REPLICATES}
    if set(out)!=expected: raise RuntimeError(f'exact anchor universe mismatch: {sorted(out)}')
    return out

def p90(vals):
    x=sorted(float(v) for v in vals); return x[int(0.9*(len(x)-1))]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--late50-root',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    new=load_new(a.results_root)
    late=json.loads(find_one(a.late50_root,'metrics.json').read_text())
    if late.get('stageId')!='taylor-broadband-mc-repro-v1' or late.get('status')!='EMPIRICAL_BETWEEN_SEED_AUDIT_COMPLETE' or late.get('rowUniverse')!=[23,24,25] or int(late.get('photonBudgetPerRayPerCondition',-1))!=50_000: raise RuntimeError('wrong immutable late-50k reference')
    obs={int(r['row']):r for r in csv.DictReader(a.observations.open(newline=''))}
    if set(obs)!=set(range(1,33)): raise RuntimeError('observation universe mismatch')
    rows=[]; details={}
    for row in ANCHORS:
        rr=[new[(row,q)] for q in REPLICATES]
        if any(int(x['photonsPerRay'])!=50_000 or int(x['rayCount'])!=64 for x in rr): raise RuntimeError(f'row {row}: metadata drift')
        q=stats([x['defaultQ'] for x in rr]); sig=[float(x['defaultQStdConservative']) for x in rr]; medsig=statistics.median(sig); mag_sd=MAG_FACTOR*q['sampleSd']/q['mean']; mag_se=MAG_FACTOR*q['se']/q['mean']
        byrep={rep:{int(z['rayIndex']):z for z in new[(row,rep)]['rays']} for rep in REPLICATES}; ratios=[]
        for ray in range(1,65):
            vals=[float(byrep[rep][ray]['q']) for rep in REPLICATES]; rsd=statistics.stdev(vals); rmsig=statistics.median(float(byrep[rep][ray]['qStdConservative']) for rep in REPLICATES)
            if rmsig>0: ratios.append(rsd/rmsig)
        if len(ratios)!=64: raise RuntimeError('ray ratio universe incomplete')
        rec={'row':row,'sunAltGeometricDeg':float(rr[0]['sunAltGeometricDeg']),'meanQ':q['mean'],'sampleSdQ':q['sampleSd'],'seQ':q['se'],'cvQ':q['cv'],'magnitudeEquivalentSingleRunSdMag':mag_sd,'magnitudeEquivalentSixRunMeanSeMag':mag_se,'singleRunSdAsFractionOfDatasetRepeatability':mag_sd/REPEATABILITY,'medianReportedAggregateQStd':medsig,'empiricalSdToMedianReportedAggregateSigma':None if medsig==0 else q['sampleSd']/medsig,'raySdToReportedSigmaMedian':statistics.median(ratios),'raySdToReportedSigmaP90':p90(ratios),'raySdToReportedSigmaMax':max(ratios)}; rows.append(rec); details[str(row)]={'q':q,'reportedAggregateSigmas':sig,'summary':rec}
    combined=[]
    for r in rows: combined.append({'row':r['row'],'sunAltGeometricDeg':r['sunAltGeometricDeg'],'magnitudeEquivalentSingleRunSdMag':r['magnitudeEquivalentSingleRunSdMag'],'cvQ':r['cvQ'],'source':'fresh-anchor-50k'})
    for row in [23,24,25]:
        q=late['rows'][str(row)]['defaultQ']; mag_sd=MAG_FACTOR*float(q['sampleSd'])/float(q['mean']); combined.append({'row':row,'sunAltGeometricDeg':float(obs[row]['sun_alt_geometric_deg']),'magnitudeEquivalentSingleRunSdMag':mag_sd,'cvQ':float(q['cv']),'source':'immutable-late-50k'})
    combined.sort(key=lambda x:x['row'])
    out={'schemaVersion':1,'stageId':STAGE,'status':'PRIMARY_MC_SCREEN_COMPLETE','photonBudgetPerRay':50_000,'datasetRepeatabilityRandomMag':REPEATABILITY,'anchorRows':ANCHORS,'lateReferenceRows':[23,24,25],'anchors':details,'combinedScreen':combined,'boundary':'Numerical broadband Monte Carlo screening only; no Taylor residuals, chi-square, atmosphere fitting, Level-B/F/tau/production, or human-model conclusion.'}; (a.output/'metrics.json').write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+'\n')
    with (a.output/'anchor-summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    lines=['# Taylor primary-interval 50k broadband Monte Carlo screen','', 'Six evenly spaced preselected anchors plus immutable late-primary rows23-25. No residuals are used.','', '|row|Sun alt|single-run empirical numerical SD (mag)|SD / dataset repeatability|CV(Q)|empirical SD / reported aggregate sigma|ray ratio median / p90 / max|','|---:|---:|---:|---:|---:|---:|---:|']
    by={r['row']:r for r in rows}
    for c in combined:
        if c['row'] in by:
            r=by[c['row']]; lines.append(f"|{r['row']}|{r['sunAltGeometricDeg']:.3f}|{r['magnitudeEquivalentSingleRunSdMag']:.4f}|{r['singleRunSdAsFractionOfDatasetRepeatability']:.2f}|{100*r['cvQ']:.2f}%|{r['empiricalSdToMedianReportedAggregateSigma']:.1f}|{r['raySdToReportedSigmaMedian']:.1f} / {r['raySdToReportedSigmaP90']:.1f} / {r['raySdToReportedSigmaMax']:.1f}|")
        else:
            lines.append(f"|{c['row']}|{c['sunAltGeometricDeg']:.3f}|{c['magnitudeEquivalentSingleRunSdMag']:.4f}|{c['magnitudeEquivalentSingleRunSdMag']/REPEATABILITY:.2f}|{100*c['cvQ']:.2f}%|—|—|")
    lines += ['','**Boundary:** this screen determines where numerical reconvergence is needed; it does not itself reclassify Taylor validation.']; (a.output/'report.md').write_text('\n'.join(lines)+'\n'); print((a.output/'report.md').read_text())
if __name__=='__main__': main()
