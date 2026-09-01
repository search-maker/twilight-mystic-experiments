#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math,hashlib
from datetime import datetime
from pathlib import Path
import numpy as np

OMEGA=1.532; THMAX=65.0; NR=8; NA=8; NREF=1.55
OBS_RANDOM=0.0621462261; FACTORY_SYS=0.10; RESPONSE_SYS=0.05; AOD_SIGMA=0.049232200070782176
OMEGA_ARCSEC2=(math.pi/(180.0*3600.0))**2

def tables(path):
 d={}
 with path.open(newline='') as f:
  for r in csv.DictReader(f):
   if r['table']=='constants': continue
   d.setdefault(r['table'],[]).append((float(r['x']),float(r['response'])))
 for k in d: d[k].sort()
 return d

def interp(points,x,left=0,right=0):
 return np.interp(x,np.array([p[0] for p in points]),np.array([p[1] for p in points]),left=left,right=right)

def quad(t):
 x,w=np.polynomial.legendre.leggauss(NR); mu0=math.cos(math.radians(THMAX)); mu=.5*(1-mu0)*x+.5*(1+mu0); ww=.5*(1-mu0)*w; out=[]
 for m,wm in zip(mu,ww):
  th=math.degrees(math.acos(float(m))); D=float(interp(t['sqm_original_angular_response_digitization'],np.array([th]),left=1,right=0)[0])
  for ia in range(NA): out.append((th,float(wm)*2*math.pi/NA*D/OMEGA))
 return out

def vega_q(fits_path:Path,t):
 from astropy.io import fits
 with fits.open(fits_path) as hd:
  data=hd[1].data; wl=np.asarray(data['WAVELENGTH'],float)/10.0; flux=np.asarray(data['FLUX'],float)*10.0 # CALSPEC erg/s/cm2/A -> mW/m2/nm
 sel=(wl>=380)&(wl<=780); wl=wl[sel]; flux=flux[sel]
 C0=interp(t['sqm_combined_onaxis_response_digitization'],wl,0,0); T0=interp(t['hoya_cm500_1mm_transmittance'],wl,0,0)
 total=0.0
 for th,w in quad(t):
  ratio=1/math.sqrt(1-(math.sin(math.radians(th))**2)/(NREF**2)); af=np.where(T0>0,np.power(T0,ratio-1),0); R=C0*af
  q=float(np.trapezoid((flux/OMEGA_ARCSEC2)*R,wl)); total+=w*q
 return total

def load_results(root:Path):
 out=[]
 for p in root.rglob('row-result.json'):
  x=json.loads(p.read_text());
  if x.get('status')=='COMPLETED': out.append(x)
 out.sort(key=lambda x:x['row'])
 if [x['row'] for x in out]!=list(range(1,33)): raise RuntimeError(f'need exact rows 1..32, got {[x["row"] for x in out]}')
 return out

def mag(q,q0): return -2.5*math.log10(q/q0)
def mag_sigma(q,s): return 2.5/math.log(10)*s/q if q>0 else math.inf

def extrap(xs,ys,x):
 xs=np.asarray(xs,float); ys=np.asarray(ys,float)
 if x<=xs[0]: i,j=0,1
 elif x>=xs[-1]: i,j=-2,-1
 else:
  j=int(np.searchsorted(xs,x)); i=j-1
 return float(ys[i]+(ys[j]-ys[i])*(x-xs[i])/(xs[j]-xs[i]))

def metrics(rows, common_sys):
 r=np.array([x['residual'] for x in rows]); sig=np.array([x['sigma_random'] for x in rows]); n=len(rows)
 C=np.diag(sig**2)+common_sys**2*np.ones((n,n)); inv=np.linalg.inv(C); chi=float(r@inv@r); red=chi/n
 mean=float(r.mean()); rms=float(np.sqrt(np.mean(r*r))); mae=float(np.mean(np.abs(r))); mx=float(np.max(np.abs(r))); se=float(math.sqrt(float(np.sum(sig**2)))/n); bz=mean/math.sqrt(common_sys**2+se**2)
 # one-constant-offset shape diagnostic, random errors only
 W=np.diag(1/sig**2); one=np.ones(n); off=float((one@W@r)/(one@W@one)); rr=r-off; shchi=float(rr@W@rr); shred=shchi/max(1,n-1); shrms=float(np.sqrt(np.mean(rr*rr)))
 return {'n':n,'meanResidualMag':mean,'rmsMag':rms,'maeMag':mae,'maxAbsMag':mx,'covarianceChi2':chi,'covarianceReducedChi2':red,'biasZ':bz,'commonSystematicMag':common_sys,'shapeDiagnosticConstantOffsetMag':off,'shapeRmsAfterOffsetMag':shrms,'shapeChi2':shchi,'shapeReducedChi2':shred,'absoluteConsistent':abs(bz)<=2 and red<=2,'shapeConsistentDiagnostic':shred<=2}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--results-root',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--vega',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
 t=tables(a.response); q0=vega_q(a.vega,t); res=load_results(a.results_root)
 rows=[]
 for x in res:
  mm=mag(x['primaryQ'],q0); mc=mag_sigma(x['primaryQ'],x['primaryQStdConservative'])
  sensA=[s['aod550'] for s in x['aodSensitivity']]; sensM=[mag(s['q'],q0) for s in x['aodSensitivity']]
  if sensA:
   # derivative near the independently frozen primary AOD, using the predeclared sweep only
   aa=x['aod550Primary']; j=max(1,min(len(sensA)-1,int(np.searchsorted(sensA,aa)))); i=j-1; deriv=(sensM[j]-sensM[i])/(sensA[j]-sensA[i]); aodsig=abs(deriv)*AOD_SIGMA
   lo=extrap(sensA,sensM,0.1632); hi=extrap(sensA,sensM,0.4768); external=max(abs(lo-mm),abs(hi-mm))
  else: deriv=aodsig=external=math.nan
  rows.append({'row':x['row'],'utc':x['utc'],'role':x['comparisonRole'],'observed':x['observedSQM'],'model':mm,'residual':x['observedSQM']-mm,'sigma_mc':mc,'sigma_aod_local':aodsig,'aod_derivative_mag_per_aod':deriv,'cams_external_envelope_model_halfspan_mag':external,'aod550':x['aod550Primary'],'sun_alt_geometric_deg':x['sunAltGeometricDeg']})
 # Timing uncertainty from the untouched model curve: central numerical time derivative * 30 s.
 ts=np.array([datetime.fromisoformat(r['utc'].replace('Z','+00:00')).timestamp() for r in rows]); mm=np.array([r['model'] for r in rows]); dmdt=np.gradient(mm,ts)
 for r,d in zip(rows,dmdt):
  r['sigma_timing']=abs(float(d))*30.0
  aod=0.0 if not math.isfinite(r['sigma_aod_local']) else r['sigma_aod_local']
  r['sigma_random']=math.sqrt(OBS_RANDOM**2+r['sigma_mc']**2+r['sigma_timing']**2+aod**2)
 common=math.sqrt(FACTORY_SYS**2+RESPONSE_SYS**2)
 primary=[r for r in rows if r['row']<=25]; nominal=[r for r in rows if 8<=r['row']<=25]; secondary=[r for r in rows if r['row']>=26]
 M={'schemaVersion':1,'zeroPoint':{'system':'Vega synthetic SQM response','calspec':a.vega.name,'qVegaSurfaceBrightness0MagArcsec2':q0},'uncertainty':{'datasetRepeatabilityRandomMag':OBS_RANDOM,'factoryAbsoluteSystematicMag':FACTORY_SYS,'responseDigitizationSystematicMag':RESPONSE_SYS,'combinedCommonSystematicMag':common,'localAodSigma':AOD_SIGMA,'externalCamsEnvelopeAOD':[0.1632,0.4768]},'primarySolarRows1to25':metrics(primary,common),'primaryNominalSQMRangeRows8to25':metrics(nominal,common),'secondaryRows26to32DescriptiveOnly':metrics(secondary,common)}
 for k in ('primarySolarRows1to25','primaryNominalSQMRangeRows8to25'):
  z=M[k]; z['classification']='ABSOLUTE_CONSISTENT' if z['absoluteConsistent'] else 'ABSOLUTE_INCONSISTENT'; z['shapeClassification']='SHAPE_CONSISTENT' if z['shapeConsistentDiagnostic'] else 'SHAPE_INCONSISTENT'
 # CSVs
 fields=list(rows[0].keys())
 with (a.output/'comparison.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
 with (a.output/'uncertainty_budget.csv').open('w',newline='') as f:
  ff=['row','sigma_random','sigma_mc','sigma_timing','sigma_aod_local','cams_external_envelope_model_halfspan_mag']
  w=csv.DictWriter(f,fieldnames=ff); w.writeheader(); w.writerows([{k:r[k] for k in ff} for r in rows])
 (a.output/'metrics.json').write_text(json.dumps(M,indent=2,sort_keys=True,allow_nan=False)+'\n')
 # Plots
 import matplotlib.pyplot as plt
 x=[r['sun_alt_geometric_deg'] for r in rows]; o=[r['observed'] for r in rows]; p=[r['model'] for r in rows]; s=[r['sigma_random'] for r in rows]
 fig,ax=plt.subplots(figsize=(9,5)); ax.plot(x,o,'o-',label='Taylor observed SQM'); ax.plot(x,p,'o-',label='Direct MYSTIC -> original SQM response'); ax.fill_between(x,np.array(p)-np.array(s),np.array(p)+np.array(s),alpha=.2,label='row random uncertainty'); ax.axvline(-6,linestyle='--',linewidth=1); ax.invert_xaxis(); ax.invert_yaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('mag/arcsec^2'); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output/'observed_vs_mystic.png',dpi=180); plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,5)); rr=[r['residual'] for r in rows]; ax.errorbar(x,rr,yerr=s,fmt='o-',capsize=2,label='Observed - MYSTIC'); ax.axhline(0,linewidth=1); ax.axhspan(-common,common,alpha=.15,label='common SQM/response systematic'); ax.axvline(-6,linestyle='--',linewidth=1); ax.invert_xaxis(); ax.set_xlabel('Geometric topocentric Sun altitude (deg)'); ax.set_ylabel('Residual (mag)'); ax.legend(); ax.grid(alpha=.25); fig.tight_layout(); fig.savefig(a.output/'residuals.png',dpi=180); plt.close(fig)
 # AOD sweep table
 with (a.output/'aod_sensitivity.csv').open('w',newline='') as f:
  w=csv.writer(f); w.writerow(['row','aod550','model_sqm_mag_arcsec2'])
  for x in res:
   for s in x['aodSensitivity']: w.writerow([x['row'],s['aod550'],mag(s['q'],q0)])
 # Report
 pmet=M['primarySolarRows1to25']; nmet=M['primaryNominalSQMRangeRows8to25']
 answer='YES' if pmet['absoluteConsistent'] else 'NO'
 shape='YES' if pmet['shapeConsistentDiagnostic'] else 'NO'
 report=f'''# Taylor 2025-08-07 direct-MYSTIC validation result

## Primary answer

**Does the existing direct MYSTIC model reproduce Taylor's measured twilight sky within the frozen atmosphere and SQM uncertainty contract? {answer}.**

Primary solar subset: rows 1-25 (geometric Sun altitude > -6 deg). No AOD or SQM offset was fit to Taylor. The one-offset calculation below is diagnostic only.

- N = {pmet['n']}
- mean observed-minus-model residual = {pmet['meanResidualMag']:.4f} mag
- RMS = {pmet['rmsMag']:.4f} mag
- MAE = {pmet['maeMag']:.4f} mag
- max |residual| = {pmet['maxAbsMag']:.4f} mag
- covariance reduced chi-square = {pmet['covarianceReducedChi2']:.3f}
- absolute bias z = {pmet['biasZ']:.3f}
- classification = **{pmet['classification']}**

Shape diagnostic: constant offset {pmet['shapeDiagnosticConstantOffsetMag']:.4f} mag, RMS after offset {pmet['shapeRmsAfterOffsetMag']:.4f} mag, reduced chi-square {pmet['shapeReducedChi2']:.3f}; **{pmet['shapeClassification']}** (shape-consistent: {shape}).

## Published nominal SQM bright-range submetric

Rows 8-25 are separately reported because Unihedron describes about 7-23 mag/arcsec2 as the normal accurate range. This submetric was declared before solver results and does not replace the 25-row primary universe.

- N = {nmet['n']}
- mean residual = {nmet['meanResidualMag']:.4f} mag
- RMS = {nmet['rmsMag']:.4f} mag
- covariance reduced chi-square = {nmet['covarianceReducedChi2']:.3f}
- classification = **{nmet['classification']}**

## Uncertainty contract

Random row uncertainty combines empirical Taylor night-to-night repeatability (0.062146 mag), conservative MYSTIC Monte Carlo uncertainty, +/-30 s timing propagated from the model curve, and local CAMS AOD sigma 0.04923 propagated through the preregistered AOD sweep. A common absolute systematic of sqrt(0.10^2+0.05^2) = {common:.4f} mag combines the published SQM factory calibration uncertainty and the response-digitization allowance. The much broader external CAMS 49% North-America envelope is reported separately and is not treated as Gaussian 1-sigma.

## Secondary late rows

Rows 26-32 are descriptive only. The run contains solar MYSTIC but no validated lunar-scattered-light or artificial/natural-background model, so these rows cannot reject or validate the solar model.
'''
 (a.output/'report.md').write_text(report)
 print(report)

if __name__=='__main__': main()
