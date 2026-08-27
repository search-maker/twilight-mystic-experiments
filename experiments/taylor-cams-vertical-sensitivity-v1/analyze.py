#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
import numpy as np

STAGE='taylor-cams-vertical-sensitivity-v1'

def stats(vals):
    a=np.asarray(vals,float); return {'n':int(a.size),'mean':float(a.mean()),'rms':float(np.sqrt(np.mean(a*a))),'min':float(a.min()),'max':float(a.max())}

def find_results(root:Path):
    xs=[]
    for p in root.rglob('row-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')==STAGE and x.get('status')=='COMPLETED': xs.append(x)
    xs.sort(key=lambda x:x['row'])
    if [x['row'] for x in xs]!=list(range(23,33)): raise SystemExit('expected rows 23-32 exactly')
    return xs

def baseline(root:Path):
    fs=list(root.rglob('comparison.csv'))
    if len(fs)!=1: raise SystemExit(f'expected one baseline comparison.csv, got {len(fs)}')
    return {int(r['row']):r for r in csv.DictReader(fs[0].open(newline=''))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--baseline-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    xs=find_results(a.results_root); b=baseline(a.baseline_root); a.output.mkdir(parents=True,exist_ok=False)
    rec=[]
    for x in xs:
        z=b[x['row']]; dm=float(x['deltaMag550CamsMinusDefault']); sig=float(x['deltaMag550McSigmaApprox']); residual=float(z['residual']); model=float(z['model']); observed=float(z['observed'])
        rec.append({'row':x['row'],'utc':x['utc'],'sun_alt_geometric_deg':x['sunAltGeometricDeg'],'role':x['comparisonRole'],'aod550_frozen':x['aod550'],'observed_sqm_mag':observed,'baseline_broadband_model_mag':model,'baseline_residual_obs_minus_model':residual,'default_q550':x['defaultQ550'],'default_q550_std':x['defaultQStd550'],'cams_shape_q550':x['camsShapeQ550'],'cams_shape_q550_std':x['camsShapeQStd550'],'delta_mag_550_cams_minus_default':dm,'delta_mag_550_mc_sigma_approx':sig,'orientation_only_model_plus_delta550':model+dm,'orientation_only_residual_after_delta550':residual-dm})
    with (a.output/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rec[0])); w.writeheader(); w.writerows(rec)
    late=[r for r in rec if r['row']>=25]; primary=[r for r in rec if r['row']<=25]; secondary=[r for r in rec if r['row']>=26]
    m={'deltaMag550AllRows':stats([r['delta_mag_550_cams_minus_default'] for r in rec]),'direction':{'positiveDeltaRows':sum(r['delta_mag_550_cams_minus_default']>0 for r in rec),'negativeDeltaRows':sum(r['delta_mag_550_cams_minus_default']<0 for r in rec)},'rows23to25LatePrimary':{'delta':stats([r['delta_mag_550_cams_minus_default'] for r in primary]),'baselineResidual':stats([r['baseline_residual_obs_minus_model'] for r in primary]),'orientationResidualAfterDelta':stats([r['orientation_only_residual_after_delta550'] for r in primary])},'rows26to32Secondary':{'delta':stats([r['delta_mag_550_cams_minus_default'] for r in secondary]),'baselineResidual':stats([r['baseline_residual_obs_minus_model'] for r in secondary]),'orientationResidualAfterDelta':stats([r['orientation_only_residual_after_delta550'] for r in secondary])},'rows25to32LateRise':{'delta':stats([r['delta_mag_550_cams_minus_default'] for r in late]),'baselineResidual':stats([r['baseline_residual_obs_minus_model'] for r in late]),'orientationResidualAfterDelta':stats([r['orientation_only_residual_after_delta550'] for r in late])},'signalToMcSigma':stats([r['delta_mag_550_cams_minus_default']/r['delta_mag_550_mc_sigma_approx'] for r in rec if r['delta_mag_550_mc_sigma_approx']>0]),'boundary':'Primary output is the direct monochromatic 550-nm CAMS-shape minus aerosol_default difference. Broadband residual-after-delta is orientation-only and is not a revised SQM validation.'}
    (a.output/'metrics.json').write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n')
    lines=['# Taylor CAMS vertical-shape sensitivity v1','',
      'Frozen diagnostic: row-specific AOD550, solar geometry, pressure, aerosol-default scattering optical properties, observer elevation treatment and 64-ray original-SQM angular weighting are unchanged. Only the normalized aerosol optical-depth vertical distribution is replaced by the independently retrieved CAMS total-aerosol extinction (532 nm) shape, interpolated between valid 00Z and 03Z from one prior forecast cycle. MYSTIC is directly compared at true monochromatic 550 nm.','',
      f"- Mean direct shift rows 23-32: **{m['deltaMag550AllRows']['mean']:+.4f} mag** (range **{m['deltaMag550AllRows']['min']:+.4f} to {m['deltaMag550AllRows']['max']:+.4f}**).",
      f"- Direction: **{m['direction']['positiveDeltaRows']}/10** rows darker under CAMS vertical shape.",
      f"- Rows 25-32 baseline broadband residual mean: **{m['rows25to32LateRise']['baselineResidual']['mean']:+.4f} mag**; orientation-only mean residual after direct 550-nm shift: **{m['rows25to32LateRise']['orientationResidualAfterDelta']['mean']:+.4f} mag**.",'','|row|Sun alt|baseline obs-model|CAMS vertical shift 550|MC sigma|orientation residual after shift|','|---:|---:|---:|---:|---:|---:|']
    for r in rec: lines.append(f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['baseline_residual_obs_minus_model']:+.3f}|{r['delta_mag_550_cams_minus_default']:+.3f}|{r['delta_mag_550_mc_sigma_approx']:.3f}|{r['orientation_only_residual_after_delta550']:+.3f}|")
    lines += ['','**Boundary:** this is a vertical-shape diagnostic, not a broadband rerun. The CAMS 532-nm extinction is used only for normalized vertical shape; the model keeps the independently frozen AOD550 and aerosol-default optical-property family.']
    (a.output/'report.md').write_text('\n'.join(lines)+'\n'); print((a.output/'report.md').read_text())

if __name__=='__main__': main()
