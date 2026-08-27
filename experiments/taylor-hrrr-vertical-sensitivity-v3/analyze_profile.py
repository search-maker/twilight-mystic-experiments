#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np

STAGE='taylor-hrrr-vertical-sensitivity-v3'

def find_results(root):
    out=[]
    for p in root.rglob('row-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')==STAGE and x.get('status')=='COMPLETED': out.append(x)
    out.sort(key=lambda x:x['row'])
    if [x['row'] for x in out]!=list(range(23,33)): raise SystemExit('expected completed rows 23-32 exactly')
    return out

def find_comparison(root):
    cand=list(root.rglob('comparison.csv'))
    if len(cand)!=1: raise SystemExit(f'expected exactly one frozen baseline comparison.csv, got {len(cand)}')
    with cand[0].open(newline='') as f: return {int(r['row']):r for r in csv.DictReader(f)}

def stats(vals):
    a=np.array(vals,float)
    return {'n':int(len(a)),'mean':float(a.mean()),'rms':float(np.sqrt(np.mean(a*a))),'min':float(a.min()),'max':float(a.max())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--baseline-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); rows=find_results(a.results_root); base=find_comparison(a.baseline_root); a.output.mkdir(parents=True,exist_ok=False)
    rec=[]
    for x in rows:
        b=base[x['row']]
        dm=float(x['deltaMag550HrrrMinusDefault']); dms=float(x['deltaMag550McSigmaApprox'])
        bm=float(b['model']); obs=float(b['observed']); br=float(b['residual'])
        approx=bm+dm; rr=br-dm
        rec.append({'row':x['row'],'utc':x['utc'],'sun_alt_geometric_deg':x['sunAltGeometricDeg'],'role':x['comparisonRole'],
                    'aod550':x['aod550'],'observed_sqm_mag':obs,'baseline_broadband_model_mag':bm,
                    'baseline_residual_obs_minus_model':br,'default_q550':x['defaultQ550'],'default_q550_std':x['defaultQStd550'],
                    'hrrr_shape_q550':x['hrrrShapeQ550'],'hrrr_shape_q550_std':x['hrrrShapeQStd550'],
                    'delta_mag_550_hrrr_minus_default':dm,'delta_mag_550_mc_sigma_approx':dms,
                    'approx_broadband_model_plus_delta550':approx,'approx_residual_after_delta550':rr})
    with (a.output/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rec[0])); w.writeheader(); w.writerows(rec)
    late_primary=[r for r in rec if r['row']<=25]; secondary=[r for r in rec if r['row']>=26]; late=[r for r in rec if r['row']>=25]
    metrics={
      'deltaMag550AllRows':stats([r['delta_mag_550_hrrr_minus_default'] for r in rec]),
      'deltaSignalToMcSigma':stats([r['delta_mag_550_hrrr_minus_default']/r['delta_mag_550_mc_sigma_approx'] for r in rec if r['delta_mag_550_mc_sigma_approx']>0]),
      'rows23to25LatePrimary':{'delta':stats([r['delta_mag_550_hrrr_minus_default'] for r in late_primary]),'baselineResidual':stats([r['baseline_residual_obs_minus_model'] for r in late_primary]),'approxResidualAfterDelta550':stats([r['approx_residual_after_delta550'] for r in late_primary])},
      'rows26to32Secondary':{'delta':stats([r['delta_mag_550_hrrr_minus_default'] for r in secondary]),'baselineResidual':stats([r['baseline_residual_obs_minus_model'] for r in secondary]),'approxResidualAfterDelta550':stats([r['approx_residual_after_delta550'] for r in secondary])},
      'rows25to32LateRise':{'delta':stats([r['delta_mag_550_hrrr_minus_default'] for r in late]),'baselineResidual':stats([r['baseline_residual_obs_minus_model'] for r in late]),'approxResidualAfterDelta550':stats([r['approx_residual_after_delta550'] for r in late])},
      'direction':{'positiveDeltaRows':int(sum(r['delta_mag_550_hrrr_minus_default']>0 for r in rec)),'negativeDeltaRows':int(sum(r['delta_mag_550_hrrr_minus_default']<0 for r in rec)),'positiveMeans':'HRRR-shaped low aerosol makes MYSTIC darker at 550 nm, the direction required to reduce a positive observed-minus-model late residual.'},
      'interpretationBoundary':'Primary scientific output is the direct 550-nm default-vs-HRRR vertical-shape difference. The broadband residual-after-delta columns are preregistered orientation-only approximations. HRRR smoke is a vertical-shape proxy, not an exact total-aerosol extinction profile. Rows26-32 remain non-acceptance secondary observations because lunar/background scattering is not modeled.'}
    (a.output/'metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True,allow_nan=False)+'\n')
    lines=['# Taylor HRRR vertical-shape sensitivity v3','',
      'One-shot frozen diagnostic: each row keeps the same independently frozen AOD550, solar geometry, pressure, aerosol-default scattering optical properties, observer elevation treatment, and 64-ray SQM angular quadrature. Only the aerosol optical-depth vertical distribution is replaced by the normalized NOAA HRRR-Smoke shape. Direct MYSTIC comparison is truly monochromatic at 550 nm, without ALIS.','',
      f"- Mean direct 550-nm shift, rows 23-32: **{metrics['deltaMag550AllRows']['mean']:+.4f} mag** (range **{metrics['deltaMag550AllRows']['min']:+.4f} to {metrics['deltaMag550AllRows']['max']:+.4f}**).",
      f"- Direction: **{metrics['direction']['positiveDeltaRows']}/10** rows become darker with the HRRR-shaped profile.",
      f"- Rows 25-32 mean frozen broadband residual: **{metrics['rows25to32LateRise']['baselineResidual']['mean']:+.4f} mag**; orientation-only residual after adding the independent 550-nm profile shift: **{metrics['rows25to32LateRise']['approxResidualAfterDelta550']['mean']:+.4f} mag**.",
      '','Per row:','',
      '|row|Sun alt|baseline obs-model|direct 550 shift|MC sigma shift|orientation residual after shift|','|---:|---:|---:|---:|---:|---:|']
    for r in rec:
        lines.append(f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['baseline_residual_obs_minus_model']:+.3f}|{r['delta_mag_550_hrrr_minus_default']:+.3f}|{r['delta_mag_550_mc_sigma_approx']:.3f}|{r['approx_residual_after_delta550']:+.3f}|")
    lines += ['','**Boundary:** the last column is not a new broadband SQM calculation. It adds the independently computed monochromatic 550-nm vertical-profile shift to the previously frozen broadband prediction only to show direction and approximate scale. A full CAMS/species-resolved broadband rerun would still be required for a revised validation claim.']
    (a.output/'report.md').write_text('\n'.join(lines)+'\n')
    print((a.output/'report.md').read_text())
if __name__=='__main__': main()
