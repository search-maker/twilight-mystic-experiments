#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math
from datetime import datetime
from pathlib import Path
import numpy as np

STAGE='taylor-cams-broadband-closure-v1'
OBS_RANDOM=0.0621462261
FACTORY_SYS=0.10
RESPONSE_SYS=0.05
COMMON_SYS=math.sqrt(FACTORY_SYS**2+RESPONSE_SYS**2)

def mag(q,q0): return -2.5*math.log10(q/q0)
def mag_sigma(q,s): return 2.5/math.log(10)*s/q if q>0 else math.inf

def find_one(root:Path,name:str)->Path:
    c=list(root.rglob(name))
    if len(c)!=1: raise RuntimeError(f'expected exactly one {name}, got {len(c)}')
    return c[0]

def load_results(root:Path):
    out=[]
    for p in root.rglob('row-result.json'):
        x=json.loads(p.read_text())
        if x.get('stageId')==STAGE and x.get('status')=='COMPLETED': out.append(x)
    out.sort(key=lambda x:x['row'])
    if [x['row'] for x in out]!=list(range(1,33)): raise RuntimeError(f'need rows 1..32 exactly, got {[x["row"] for x in out]}')
    if sum(x['scientificSolverCalls'] for x in out)!=10240: raise RuntimeError('solver-call accounting mismatch')
    if sum(x['scientificPhotonHistories'] for x in out)!=102400000: raise RuntimeError('photon accounting mismatch')
    return out

def load_baseline(root:Path):
    m=json.loads(find_one(root,'metrics.json').read_text())
    q0=float(m['zeroPoint']['qVegaSurfaceBrightness0MagArcsec2'])
    with find_one(root,'comparison.csv').open(newline='') as f: rows={int(r['row']):r for r in csv.DictReader(f)}
    if sorted(rows)!=list(range(1,33)): raise RuntimeError('baseline comparison row universe mismatch')
    return q0,rows,m

def metrics(rows,common_sys):
    r=np.array([x['residual'] for x in rows],float); sig=np.array([x['sigma_random'] for x in rows],float); n=len(rows)
    C=np.diag(sig**2)+common_sys**2*np.ones((n,n)); inv=np.linalg.inv(C); chi=float(r@inv@r); red=chi/n
    mean=float(r.mean()); rms=float(np.sqrt(np.mean(r*r))); mae=float(np.mean(np.abs(r))); mx=float(np.max(np.abs(r)))
    se=float(math.sqrt(float(np.sum(sig**2)))/n); bz=mean/math.sqrt(common_sys**2+se**2)
    W=np.diag(1/sig**2); one=np.ones(n); off=float((one@W@r)/(one@W@one)); rr=r-off; shchi=float(rr@W@rr); shred=shchi/max(1,n-1); shrms=float(np.sqrt(np.mean(rr*rr)))
    return {'n':n,'meanResidualMag':mean,'rmsMag':rms,'maeMag':mae,'maxAbsMag':mx,'covarianceChi2':chi,'covarianceReducedChi2':red,'biasZ':bz,'commonSystematicMag':common_sys,'shapeDiagnosticConstantOffsetMag':off,'shapeRmsAfterOffsetMag':shrms,'shapeChi2':shchi,'shapeReducedChi2':shred,'absoluteConsistent':abs(bz)<=2 and red<=2,'shapeConsistentDiagnostic':shred<=2}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--baseline-root',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=False)
    res=load_results(a.results_root); q0,old,oldmetrics=load_baseline(a.baseline_root)
    rows=[]
    for x in res:
        c=x['conditions']; b=c['base']; model=mag(b['q'],q0); mc=mag_sigma(b['q'],b['qStdConservative'])
        ml=mag(c['local_minus']['q'],q0); mp=mag(c['local_plus']['q'],q0); el=mag(c['external_low']['q'],q0); eh=mag(c['external_high']['q'],q0)
        aodsig=max(abs(ml-model),abs(mp-model)); external=max(abs(el-model),abs(eh-model))
        o=old[x['row']]; obs=float(x['observedSQM']); residual=obs-model
        rows.append({'row':x['row'],'utc':x['utc'],'role':x['comparisonRole'],'sun_alt_geometric_deg':x['sunAltGeometricDeg'],'aod550':x['aod550PrimaryFrozen'],'observed':obs,'old_default_vertical_model':float(o['model']),'old_default_vertical_residual':float(o['residual']),'cams_vertical_broadband_model':model,'residual':residual,'model_shift_cams_minus_default':model-float(o['model']),'sigma_mc':mc,'sigma_aod_local':aodsig,'aod_local_minus_model':ml,'aod_local_plus_model':mp,'cams_external_envelope_model_halfspan_mag':external,'aod_external_low_model':el,'aod_external_high_model':eh})
    ts=np.array([datetime.fromisoformat(r['utc'].replace('Z','+00:00')).timestamp() for r in rows]); mm=np.array([r['cams_vertical_broadband_model'] for r in rows]); dmdt=np.gradient(mm,ts)
    for r,d in zip(rows,dmdt):
        r['sigma_timing']=abs(float(d))*30.0
        r['sigma_random']=math.sqrt(OBS_RANDOM**2+r['sigma_mc']**2+r['sigma_timing']**2+r['sigma_aod_local']**2)
        r['combined_row_sigma_with_common_for_direction']=math.sqrt(r['sigma_random']**2+COMMON_SYS**2)
        r['late_positive_residual_z']=max(0.0,r['residual'])/r['combined_row_sigma_with_common_for_direction']
        r['additive_background_direction']='WRONG_SIGN_FOR_MISSING_ADDITIVE_LIGHT' if r['residual']>0 else 'COMPATIBLE_DIRECTION_FOR_MISSING_ADDITIVE_LIGHT'
        r['absolute_residual_improvement_vs_old']=abs(r['old_default_vertical_residual'])-abs(r['residual'])
    primary=[r for r in rows if r['row']<=25]; nominal=[r for r in rows if 8<=r['row']<=25]; late=[r for r in rows if r['row']>=26]; rise=[r for r in rows if r['row']>=25]
    P=metrics(primary,COMMON_SYS); N=metrics(nominal,COMMON_SYS); L=metrics(late,COMMON_SYS); R=metrics(rise,COMMON_SYS); A=metrics(rows,COMMON_SYS)
    for z in (P,N,L,R,A):
        z['classification']='ABSOLUTE_CONSISTENT' if z['absoluteConsistent'] else 'ABSOLUTE_INCONSISTENT'; z['shapeClassification']='SHAPE_CONSISTENT' if z['shapeConsistentDiagnostic'] else 'SHAPE_INCONSISTENT'
    strong_wrong=[r for r in late if r['residual']>0 and r['late_positive_residual_z']>2]
    closure='BROADBAND_CAMS_VERTICAL_CLOSURE_SUPPORTED' if P['absoluteConsistent'] and not strong_wrong else 'BROADBAND_CAMS_VERTICAL_CLOSURE_NOT_FULLY_SUPPORTED'
    M={'schemaVersion':1,'stageId':STAGE,'classification':closure,'zeroPoint':{'system':'frozen Vega synthetic original-SQM response from baseline analysis','qVegaSurfaceBrightness0MagArcsec2':q0},'uncertainty':{'datasetRepeatabilityRandomMag':OBS_RANDOM,'factoryAbsoluteSystematicMag':FACTORY_SYS,'responseDigitizationSystematicMag':RESPONSE_SYS,'combinedCommonSystematicMag':COMMON_SYS,'localAodSigma':0.049232200070782176,'localAodPropagation':'direct center+/-sigma CAMS-shape broadband runs; conservative max one-sided model shift','externalCamsEnvelopeAOD':[0.1632,0.4768]},'primarySolarRows1to25':P,'primaryNominalRows8to25':N,'lateRows26to32':L,'lateRiseRows25to32':R,'allRowsReference':A,'lateAdditiveBackgroundDirection':{'strongWrongSignRowCount':len(strong_wrong),'strongWrongSignRows':[r['row'] for r in strong_wrong],'maxPositiveResidualZ':max(r['late_positive_residual_z'] for r in late),'rule':'omitted moon/airglow/artificial/natural background adds radiance, so it can only reduce model magnitude; a positive observed-minus-solar-only-model residual is wrong-sign, with >2 combined-row-sigma reported as strong'},'comparisonToOriginal':{'meanModelShiftRows1to32':float(np.mean([r['model_shift_cams_minus_default'] for r in rows])),'meanModelShiftRows25to32':float(np.mean([r['model_shift_cams_minus_default'] for r in rise])),'meanOldResidualRows25to32':float(np.mean([r['old_default_vertical_residual'] for r in rise])),'meanNewResidualRows25to32':float(np.mean([r['residual'] for r in rise])),'rmsOldResidualRows25to32':float(np.sqrt(np.mean(np.square([r['old_default_vertical_residual'] for r in rise])))),'rmsNewResidualRows25to32':float(np.sqrt(np.mean(np.square([r['residual'] for r in rise]))))}}
    with (a.output/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (a.output/'metrics.json').write_text(json.dumps(M,indent=2,sort_keys=True,allow_nan=False)+'\n')
    with (a.output/'aod_sensitivity.csv').open('w',newline='') as f:
        ff=['row','aod550','cams_vertical_broadband_model','aod_local_minus_model','aod_local_plus_model','aod_external_low_model','aod_external_high_model','sigma_aod_local','cams_external_envelope_model_halfspan_mag']
        w=csv.DictWriter(f,fieldnames=ff); w.writeheader(); w.writerows([{k:r[k] for k in ff} for r in rows])
    import matplotlib.pyplot as plt
    x=[r['sun_alt_geometric_deg'] for r in rows]; obs=[r['observed'] for r in rows]; new=[r['cams_vertical_broadband_model'] for r in rows]; oldm=[r['old_default_vertical_model'] for r in rows]
    fig,ax=plt.subplots(figsize=(9,5)); ax.plot(x,obs,'o-',label='Taylor observed SQM'); ax.plot(x,new,'o-',label='MYSTIC + CAMS vertical profile'); ax.plot(x,oldm,'--',label='Original aerosol_default MYSTIC'); ax.axvline(-6,linestyle='--',linewidth=1); ax.invert_xaxis(); ax.invert_yaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('mag/arcsec^2'); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output/'observed_vs_models.png',dpi=180); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5)); rr=[r['residual'] for r in rows]; ss=[r['sigma_random'] for r in rows]; ax.errorbar(x,rr,yerr=ss,fmt='o-',capsize=2,label='Observed - CAMS-profile MYSTIC'); ax.axhline(0,linewidth=1); ax.axhspan(-COMMON_SYS,COMMON_SYS,alpha=.15,label='common SQM/response systematic'); ax.axvline(-6,linestyle='--',linewidth=1); ax.invert_xaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('Residual (mag)'); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output/'residuals.png',dpi=180); plt.close(fig)
    lines=['# Taylor CAMS broadband closure result','',f"**Classification: {closure}.**",'',
        'This is the frozen 380-780 nm original-SQM forward-operator closure run. Each Taylor row retains the original independently frozen AOD550, geometry, pressure, calibration and 64-ray angular response. Only the aerosol optical-depth vertical distribution is replaced by the independently retrieved CAMS total-aerosol extinction-at-532-nm shape, interpolated in time. No SQM offset or AOD was fit to Taylor.','',
        f"Primary rows 1-25: mean residual **{P['meanResidualMag']:+.4f} mag**, RMS **{P['rmsMag']:.4f}**, reduced chi-square **{P['covarianceReducedChi2']:.3f}**, bias z **{P['biasZ']:+.3f}**, **{P['classification']}**; shape **{P['shapeClassification']}**.",
        f"Rows 25-32: old mean residual **{M['comparisonToOriginal']['meanOldResidualRows25to32']:+.4f} mag** -> new **{M['comparisonToOriginal']['meanNewResidualRows25to32']:+.4f} mag**; old RMS **{M['comparisonToOriginal']['rmsOldResidualRows25to32']:.4f}** -> new **{M['comparisonToOriginal']['rmsNewResidualRows25to32']:.4f}**.",
        f"Late rows 26-32: strong wrong-sign positive residuals (>2 combined row sigma) = **{len(strong_wrong)}**, rows **{[r['row'] for r in strong_wrong]}**; max positive residual z **{M['lateAdditiveBackgroundDirection']['maxPositiveResidualZ']:.2f}**.",'',
        '|row|Sun alt|observed|old model|new CAMS model|old residual|new residual|CAMS-old shift|random sigma|late +res z|','|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['observed']:.3f}|{r['old_default_vertical_model']:.3f}|{r['cams_vertical_broadband_model']:.3f}|{r['old_default_vertical_residual']:+.3f}|{r['residual']:+.3f}|{r['model_shift_cams_minus_default']:+.3f}|{r['sigma_random']:.3f}|{r['late_positive_residual_z']:.2f}|")
    lines += ['','## Boundary','', 'This closes the broadband original-SQM vertical-profile test, but it does not add moonlight, airglow or artificial background. Those are additive radiance terms: they can explain a model that is too dark, but cannot explain a model that is already too bright. CAMS aerext532 supplies the normalized vertical shape; aerosol spectral single-scattering/phase-function properties remain the frozen `aerosol_default` family. No production promotion follows from this result.']
    (a.output/'report.md').write_text('\n'.join(lines)+'\n'); print((a.output/'report.md').read_text())

if __name__=='__main__': main()
