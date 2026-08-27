#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np

def find_results(root):
    out=[]
    for p in root.rglob('row-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')=='taylor-hrrr-vertical-sensitivity-v1' and x.get('status')=='COMPLETED': out.append(x)
    out.sort(key=lambda x:x['row'])
    if [x['row'] for x in out]!=list(range(23,33)): raise SystemExit('expected rows 23-32 exactly')
    return out

def find_comparison(root):
    cand=list(root.rglob('comparison.csv'))
    if len(cand)!=1: raise SystemExit(f'expected one baseline comparison.csv, got {len(cand)}')
    with cand[0].open(newline='') as f: return {int(r['row']):r for r in csv.DictReader(f)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--baseline-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); rows=find_results(a.results_root); base=find_comparison(a.baseline_root); a.output.mkdir(parents=True,exist_ok=False)
    rec=[]
    for x in rows:
        b=base[x['row']]; dm=float(x['deltaMag550HrrrMinusDefault']); bm=float(b['model']); obs=float(b['observed']); br=float(b['residual'])
        approx=bm+dm; rr=obs-approx
        rec.append({'row':x['row'],'utc':x['utc'],'sun_alt_geometric_deg':x['sunAltGeometricDeg'],'role':x['comparisonRole'],
                    'aod550':x['aod550'],'baseline_broadband_model_mag':bm,'observed_sqm_mag':obs,'baseline_residual_obs_minus_model':br,
                    'default_q550':x['defaultQ550'],'hrrr_shape_q550':x['hrrrShapeQ550'],'delta_mag_550_hrrr_minus_default':dm,
                    'approx_broadband_model_plus_delta550':approx,'approx_residual_after_delta550':rr})
    with (a.output/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rec[0])); w.writeheader(); w.writerows(rec)
    dm=np.array([r['delta_mag_550_hrrr_minus_default'] for r in rec])
    primary=[r for r in rec if r['row']<=25]; secondary=[r for r in rec if r['row']>=26]
    metrics={'deltaMag550':{'mean':float(dm.mean()),'min':float(dm.min()),'max':float(dm.max()),'rowsPositive':int((dm>0).sum())},
             'rows23to25':{'meanDelta':float(np.mean([r['delta_mag_550_hrrr_minus_default'] for r in primary])),
                           'baselineResiduals':[r['baseline_residual_obs_minus_model'] for r in primary],
                           'approxResidualsAfterDelta550':[r['approx_residual_after_delta550'] for r in primary]},
             'rows26to32':{'meanDelta':float(np.mean([r['delta_mag_550_hrrr_minus_default'] for r in secondary])),
                           'baselineResidualMean':float(np.mean([r['baseline_residual_obs_minus_model'] for r in secondary])),
                           'approxResidualMeanAfterDelta550':float(np.mean([r['approx_residual_after_delta550'] for r in secondary]))},
             'interpretationBoundary':'550-nm vertical-shape diagnostic only. Adding deltaMag550 to broadband SQM is an approximate orientation metric, not a broadband recalculation or validation.'}
    (a.output/'metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True,allow_nan=False)+'\n')
    lines=['# Taylor HRRR vertical-shape sensitivity v1','','This one-shot diagnostic keeps each row AOD550 fixed and changes only the aerosol optical-depth vertical distribution from libRadtran aerosol_default to a normalized HRRR-Smoke mass-density shape. Aerosol SSA/phase-family and all geometry are otherwise unchanged. The solver comparison itself is monochromatic at 550 nm.','',f"- Mean 550-nm equivalent darkening (HRRR shape - default): **{metrics['deltaMag550']['mean']:+.4f} mag**",f"- Range across rows 23-32: **{metrics['deltaMag550']['min']:+.4f} to {metrics['deltaMag550']['max']:+.4f} mag**",f"- Rows with darker HRRR-shaped result: **{metrics['deltaMag550']['rowsPositive']}/10**",'', 'Per-row:','', '|row|Sun alt|baseline residual|delta 550|approx residual after delta|','|---:|---:|---:|---:|---:|']
    for r in rec: lines.append(f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['baseline_residual_obs_minus_model']:+.3f}|{r['delta_mag_550_hrrr_minus_default']:+.3f}|{r['approx_residual_after_delta550']:+.3f}|")
    lines += ['','**Boundary:** the last column is only an orientation calculation obtained by adding the monochromatic 550-nm shift to the already-frozen broadband SQM model. It is not a new broadband SQM forward model. HRRR smoke is a shape proxy, not a claim that all aerosol was smoke.']
    (a.output/'report.md').write_text('\n'.join(lines)+'\n')
    print((a.output/'report.md').read_text())
if __name__=='__main__': main()
