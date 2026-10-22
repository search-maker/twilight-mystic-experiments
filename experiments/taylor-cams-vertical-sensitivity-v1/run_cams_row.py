#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

STAGE='taylor-cams-vertical-sensitivity-v1'
ROWS=list(range(23,33))
SITE_KM=0.262
T0=datetime(2025,8,8,0,tzinfo=timezone.utc)
T3=datetime(2025,8,8,3,tzinfo=timezone.utc)
CAMSPROFILE_SHA='6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359'
PHOTONS=50000
DEFAULT_SEED_BASE=953000000
CAMS_SEED_BASE=954000000

class Failure(RuntimeError): pass

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise Failure(f'cannot import {path}')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def parse_utc(s:str)->datetime:
    return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)

def load_cams_profile(path:Path):
    if sha(path)!=CAMSPROFILE_SHA: raise Failure('CAMS profile checksum mismatch')
    rows=list(csv.DictReader(path.open(newline='')))
    by={T0:[],T3:[]}
    for r in rows:
        lead=int(r['leadHour'])
        if lead==12: t=T0
        elif lead==15: t=T3
        else: continue
        by[t].append((int(r['modelLevel']),float(r['heightAGL_m']),float(r['extinction532_m-1'])))
    sanity={}
    profiles={}
    for t in (T0,T3):
        rr=by[t]
        if len(rr)!=137 or sorted(x[0] for x in rr)!=list(range(1,138)):
            raise Failure(f'CAMS level universe invalid at {t}: {len(rr)}')
        pts=sorted((h,b) for _,h,b in rr)
        z=np.array([p[0] for p in pts],float); beta=np.array([p[1] for p in pts],float)
        if np.any(np.diff(z)<=0) or np.any(beta<0) or z[0]<0: raise Failure('invalid CAMS height/extinction profile')
        # Full levels begin about 10 m AGL. Anchor the ground with the lowest-level extinction.
        z=np.concatenate(([0.0],z)); beta=np.concatenate(([beta[0]],beta))
        integ=float(np.trapezoid(beta,z))
        if not integ>0: raise Failure('non-positive CAMS integrated extinction')
        profiles[t]=[(float(a),float(b)) for a,b in zip(z,beta)]
        sanity[t.isoformat()]={'levelCount':137,'firstFullLevelAGLM':float(z[1]),'topAGLM':float(z[-1]),'integratedExtinctionTau532Discrete':integ,'peakExtinctionM1':float(beta.max()),'profileSha256':CAMSPROFILE_SHA}
    return profiles,sanity

def beta_at(points,z_m):
    x=np.array([p[0] for p in points],float); y=np.array([p[1] for p in points],float)
    return float(np.interp(z_m,x,y,left=y[0],right=0.0))

def time_beta(profiles,t,z_m):
    if not T0<=t<=T3: raise Failure(f'Taylor row outside CAMS interpolation interval: {t}')
    w=(t-T0).total_seconds()/(T3-T0).total_seconds()
    return (1-w)*beta_at(profiles[T0],z_m)+w*beta_at(profiles[T3],z_m)

def layer_shape_tau(profiles,t,lo_abs_km,hi_abs_km):
    if hi_abs_km<=lo_abs_km: return 0.0
    lo=(lo_abs_km-SITE_KM)*1000.0; hi=(hi_abs_km-SITE_KM)*1000.0
    anchors={lo,hi}
    for pts in profiles.values():
        for z,_ in pts:
            if lo<z<hi: anchors.add(z)
    z=np.array(sorted(anchors),float)
    b=np.array([time_beta(profiles,t,float(v)) for v in z],float)
    return float(np.trapezoid(b,z))

def write_tau_profile(helper,base,atmosphere:Path,profiles,t,out:Path):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    layer=[]
    for i in range(len(grid)-1): layer.append(layer_shape_tau(profiles,t,grid[i],grid[i+1]))
    total=sum(layer)
    if not total>0: raise Failure('zero above-site CAMS extinction integral')
    tau={grid[i]:layer[i]/total for i in range(len(layer))}; tau[grid[-1]]=0.0
    if abs(sum(tau.values())-1.0)>1e-10: raise Failure('CAMS tau profile not normalized')
    out.write_text('# CAMS aerext532 normalized vertical shape on exact site grid; layer tau sum=1\n'+'\n'.join(f'{z:.6f} {tau[z]:.15e}' for z in reversed(grid))+'\n')
    return {'gridBottomKm':grid[0],'gridTopKm':grid[-1],'layerCount':len(grid)-1,'interpolatedAboveSiteTau532BeforeNormalization':total,'tauSum':sum(tau.values()),'tauFileSha256':sha(out)}

def execute(helper,base,uvspec,data_dir,atm,obs,rays,tables,aod,row,tau_file,seed_base,out,condition):
    records=[]
    for ray in rays:
        rd=out/condition/f"ray-{ray['rayIndex']:02d}"; rd.mkdir(parents=True,exist_ok=False)
        seed=seed_base+row*1000+ray['rayIndex']
        text=helper.render(base,data_dir,atm,rd,obs,ray,aod,seed,tau_file)
        (rd/'input-resolved.txt').write_text(text)
        syntax_sec=helper.run_uvspec(uvspec,text,rd,syntax=True)
        solver_sec=helper.run_uvspec(uvspec,text,rd,syntax=False)
        rad=rd/'mc.rad.spc'; std=rd/'mc.rad.std.spc'
        if not rad.is_file() or not std.is_file(): raise Failure('missing MYSTIC output')
        q,radrow=helper.parse_550(rad); qs,stdrow=helper.parse_550(std)
        if q<0 or qs<0: raise Failure('negative radiance/std')
        records.append({'rayIndex':ray['rayIndex'],'thetaDeg':ray['thetaDeg'],'relativeAzimuthDeg':ray['relativeAzimuthDeg'],'weight550':helper.effective_weight(base,tables,ray),'seed':seed,'q550':q,'qStd550':qs,'syntaxSeconds':syntax_sec,'solverSeconds':solver_sec,'radRow':radrow,'stdRow':stdrow,'inputSha256':hashlib.sha256(text.encode()).hexdigest(),'radianceSha256':sha(rad),'stdSha256':sha(std)})
    q=sum(r['weight550']*r['q550'] for r in records)
    qs=math.sqrt(sum((r['weight550']*r['qStd550'])**2 for r in records))
    return records,q,qs,sum(r['weight550'] for r in records)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--helper-runner',type=Path,required=True); ap.add_argument('--baseline-runner',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--cams-profile',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args()
    if a.row not in ROWS: raise Failure('row outside frozen universe')
    helper=load_module(a.helper_runner,'hrrr_helper'); base=load_module(a.baseline_runner,'taylor_v1')
    if helper.PHOTONS!=PHOTONS: raise Failure('helper photon contract mismatch')
    obs=base.load_observation(a.observations,a.row); tables=base.load_response(a.response); rays=base.quadrature(tables)
    if len(rays)!=64: raise Failure('expected 64 rays')
    profiles,sanity=load_cams_profile(a.cams_profile); t=parse_utc(obs['utc'])
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve(); u=a.uvspec.resolve()
    tau_path=out/'cams-site-grid-tau.dat'; tau_meta=write_tau_profile(helper,base,atm,profiles,t,tau_path)
    aod=float(obs['aod550_primary_frozen'])
    drec,dq,dqs,sw=execute(helper,base,u,data,atm,obs,rays,tables,aod,a.row,None,DEFAULT_SEED_BASE,out,'default_vertical')
    crec,cq,cqs,_=execute(helper,base,u,data,atm,obs,rays,tables,aod,a.row,tau_path,CAMS_SEED_BASE,out,'cams_ext532_shape')
    if dq<=0 or cq<=0: raise Failure('non-positive aggregate radiance')
    delta=-2.5*math.log10(cq/dq)
    sigma=(2.5/math.log(10))*math.sqrt((dqs/dq)**2+(cqs/cq)**2)
    result={'schemaVersion':1,'stageId':STAGE,'status':'COMPLETED','row':a.row,'utc':obs['utc'],'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'observedSQM':float(obs['observed_sqm_mag_arcsec2']),'comparisonRole':obs['comparison_role'],'aod550':aod,'surfacePressureHpa':float(obs['surface_pressure_hpa']),'spectralMode':'true monochromatic 550 nm; no ALIS','camsProfileWavelengthNm':532,'photonsPerRayPerCondition':PHOTONS,'rayCount':len(rays),'effectiveWeightSum550':sw,'camsProfileSha256':sha(a.cams_profile),'camsEndpointSanity':sanity,'camsTauProfile':tau_meta,'defaultQ550':dq,'defaultQStd550':dqs,'camsShapeQ550':cq,'camsShapeQStd550':cqs,'deltaMag550CamsMinusDefault':delta,'deltaMag550McSigmaApprox':sigma,'defaultRays':drec,'camsShapeRays':crec,'interpretation':'Vertical-shape sensitivity only. CAMS aerext532 supplies normalized total-aerosol vertical shape from one prior forecast cycle; row AOD550 and aerosol_default scattering optical properties remain independently frozen.'}
    (out/'row-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['status','row','sunAltGeometricDeg','aod550','defaultQ550','camsShapeQ550','deltaMag550CamsMinusDefault','deltaMag550McSigmaApprox']},sort_keys=True))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(exc)}),file=sys.stderr); raise
