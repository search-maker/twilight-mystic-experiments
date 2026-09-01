#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

STAGE='taylor-cams-broadband-closure-v1'
EXECUTION_KEY='taylor-cams-broadband-closure-v1:scientific:1'
ROWS=list(range(1,33))
SITE_KM=0.262
T0=datetime(2025,8,8,0,tzinfo=timezone.utc)
T3=datetime(2025,8,8,3,tzinfo=timezone.utc)
CAMS_PROFILE_SHA='6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359'
BASE_PHOTONS=20000
LOCAL_PHOTONS=10000
EXTERNAL_PHOTONS=5000
AOD_SIGMA=0.049232200070782176
EXTERNAL_LOW=0.1632
EXTERNAL_HIGH=0.4768
SEEDS={'base':956000000,'local_minus':957000000,'local_plus':958000000,'external_low':959000000,'external_high':960000000}
SMOKE_SEED=955999001

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

def load_manifest(path:Path):
    m=json.loads(path.read_text())
    if m.get('stageId')!=STAGE or m.get('executionKey')!=EXECUTION_KEY: raise Failure('wrong manifest identity')
    if m['frozenRows']!=ROWS: raise Failure('row universe changed')
    mm=m['mystic']
    if mm['basePhotonsPerRay']!=BASE_PHOTONS or mm['localAodSensitivityPhotonsPerRay']!=LOCAL_PHOTONS or mm['externalEnvelopePhotonsPerRay']!=EXTERNAL_PHOTONS: raise Failure('photon contract changed')
    if m['aod']['localSigma']!=AOD_SIGMA or m['aod']['externalEnvelope']!=[EXTERNAL_LOW,EXTERNAL_HIGH]: raise Failure('AOD contract changed')
    return m

def load_cams_profile(path:Path):
    if sha(path)!=CAMS_PROFILE_SHA: raise Failure('CAMS profile checksum mismatch')
    rows=list(csv.DictReader(path.open(newline='')))
    by={T0:[],T3:[]}
    for r in rows:
        lead=int(r['leadHour'])
        if lead==12: t=T0
        elif lead==15: t=T3
        else: continue
        by[t].append((int(r['modelLevel']),float(r['heightAGL_m']),float(r['extinction532_m-1'])))
    profiles={}; sanity={}
    for t in (T0,T3):
        rr=by[t]
        if len(rr)!=137 or sorted(x[0] for x in rr)!=list(range(1,138)): raise Failure(f'CAMS level universe invalid at {t}: {len(rr)}')
        pts=sorted((h,b) for _,h,b in rr)
        z=np.array([p[0] for p in pts],float); beta=np.array([p[1] for p in pts],float)
        if np.any(np.diff(z)<=0) or np.any(beta<0) or z[0]<0: raise Failure('invalid CAMS height/extinction profile')
        z=np.concatenate(([0.0],z)); beta=np.concatenate(([beta[0]],beta))
        integ=float(np.trapezoid(beta,z))
        if not integ>0: raise Failure('non-positive CAMS extinction integral')
        profiles[t]=[(float(a),float(b)) for a,b in zip(z,beta)]
        sanity[t.isoformat()]={'levelCount':137,'firstFullLevelAGLM':float(z[1]),'topAGLM':float(z[-1]),'integratedTau532Discrete':integ,'peakExtinctionM1':float(beta.max())}
    return profiles,sanity

def beta_at(points,z_m):
    x=np.array([p[0] for p in points],float); y=np.array([p[1] for p in points],float)
    return float(np.interp(z_m,x,y,left=y[0],right=0.0))

def time_beta(profiles,t,z_m):
    if not T0<=t<=T3: raise Failure(f'observation outside CAMS interpolation interval: {t}')
    w=(t-T0).total_seconds()/(T3-T0).total_seconds()
    return (1-w)*beta_at(profiles[T0],z_m)+w*beta_at(profiles[T3],z_m)

def layer_tau_raw(profiles,t,lo_abs_km,hi_abs_km):
    if hi_abs_km<=lo_abs_km: return 0.0
    lo=(lo_abs_km-SITE_KM)*1000.0; hi=(hi_abs_km-SITE_KM)*1000.0
    anchors={lo,hi}
    for pts in profiles.values():
        for z,_ in pts:
            if lo<z<hi: anchors.add(z)
    zz=np.array(sorted(anchors),float)
    bb=np.array([time_beta(profiles,t,float(v)) for v in zz],float)
    return float(np.trapezoid(bb,zz))

def write_tau_profile(base,atmosphere:Path,profiles,t,out:Path):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    layer=[layer_tau_raw(profiles,t,grid[i],grid[i+1]) for i in range(len(grid)-1)]
    total=sum(layer)
    if not total>0: raise Failure('zero above-site CAMS extinction integral')
    tau={grid[i]:layer[i]/total for i in range(len(layer))}; tau[grid[-1]]=0.0
    if abs(sum(tau.values())-1.0)>1e-10: raise Failure('CAMS tau profile not normalized')
    out.write_text('# CAMS aerext532 normalized vertical shape on exact Taylor site grid; layer tau sum=1\n'+'\n'.join(f'{z:.6f} {tau[z]:.15e}' for z in reversed(grid))+'\n')
    return {'gridBottomKm':grid[0],'gridTopKm':grid[-1],'layerCount':len(grid)-1,'interpolatedAboveSiteTau532BeforeNormalization':total,'tauSum':sum(tau.values()),'tauFileSha256':sha(out)}

def render(base,data_dir:Path,atmosphere:Path,case_dir:Path,obs,ray,aod,photons,seed,tau_file:Path):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    sza=90.0-float(obs['sun_alt_geometric_deg'])
    umu=-math.cos(math.radians(ray['thetaDeg']))
    pressure=float(obs['surface_pressure_hpa'])
    solar=data_dir/'solar_flux/atlas_plus_modtran'
    lines=[
        f'data_files_path {data_dir}',f'atmosphere_file {atmosphere}',f'source solar {solar}',
        'mol_abs_param crs','wavelength 380 780','day_of_year 220',f'sza {sza:.8f}','phi0 0.0',
        'rte_solver mystic','mc_spherical 1D',f'mc_photons {photons}','mc_vroom off','mc_std',
        f'mc_randomseed {seed}',f'mc_basename {case_dir / "mc"}','mc_spectral_is 550.0','albedo 0.150000',
        'aerosol_default',f'aerosol_file tau {tau_file.resolve()}',f'aerosol_set_tau_at_wvl 550 {aod:.8f}',
        f'pressure {pressure:.4f}','atm_z_grid '+' '.join(f'{z:.6f}' for z in grid),'zout 0.000000',
        f'umu {umu:.10f}',f'phi {ray["relativeAzimuthDeg"]:.8f}','quiet']
    return '\n'.join(lines)+'\n'

def execute_one(base,uvspec,data_dir,atm,obs,ray,aod,photons,seed,case_dir,tables,tau_file,keep_raw):
    case_dir.mkdir(parents=True,exist_ok=False)
    text=render(base,data_dir,atm,case_dir,obs,ray,aod,photons,seed,tau_file)
    inp=case_dir/'input-resolved.txt'; inp.write_text(text)
    syntax_s=base.run_process(uvspec,text,case_dir,syntax=True)
    solver_s=base.run_process(uvspec,text,case_dir,syntax=False)
    rad=case_dir/'mc.rad.spc'; std=case_dir/'mc.rad.std.spc'
    if not rad.is_file() or not std.is_file(): raise Failure(f'missing MYSTIC spectra in {case_dir}')
    q,qstd,n,w0,w1=base.integrate_ray(rad,std,ray['thetaDeg'],tables)
    if q<0 or qstd<0 or not math.isfinite(q) or not math.isfinite(qstd): raise Failure('invalid integrated SQM response')
    rec={'rayIndex':ray['rayIndex'],'thetaDeg':ray['thetaDeg'],'relativeAzimuthDeg':ray['relativeAzimuthDeg'],'normalizedWeight':ray['normalizedWeight'],'aod550':aod,'photons':photons,'seed':seed,'q':q,'qStdConservative':qstd,'syntaxSeconds':syntax_s,'solverSeconds':solver_s,'spectrumRows':n,'wavelengthStartNm':w0,'wavelengthEndNm':w1,'inputSha256':hashlib.sha256(text.encode()).hexdigest(),'radianceSha256':sha(rad),'stdSha256':sha(std)}
    if keep_raw:
        rec['radianceGzip']=base.gzip_file(rad).name; rec['stdGzip']=base.gzip_file(std).name
    else:
        for p in case_dir.glob('mc*'): p.unlink(missing_ok=True)
        inp.unlink(missing_ok=True)
        try: case_dir.rmdir()
        except OSError: pass
    return rec

def aggregate(records):
    q=sum(r['normalizedWeight']*r['q'] for r in records)
    s=math.sqrt(sum((r['normalizedWeight']*r['qStdConservative'])**2 for r in records))
    return q,s

def execute_condition(base,uvspec,data_dir,atm,obs,rays,tables,row,name,aod,photons,tau_file,out,keep_raw=False):
    records=[]; seed_base=SEEDS[name]
    root=out/name
    for ray in rays:
        seed=seed_base+row*1000+ray['rayIndex']
        records.append(execute_one(base,uvspec,data_dir,atm,obs,ray,aod,photons,seed,root/f"ray-{ray['rayIndex']:02d}",tables,tau_file,keep_raw))
    q,s=aggregate(records)
    if not q>0: raise Failure(f'non-positive aggregate q for {name}')
    result={'name':name,'aod550':aod,'photonsPerRay':photons,'rayCount':len(records),'q':q,'qStdConservative':s}
    if keep_raw: result['rays']=records
    else: shutil.rmtree(root,ignore_errors=True)
    return result

def technical_smoke(base,uvspec,data_dir,atm,obs,rays,tables,tau_file,out):
    ray=rays[0]; rd=out/'technical-smoke-ray-01'; rd.mkdir(parents=True,exist_ok=False)
    aod=float(obs['aod550_primary_frozen'])
    text=render(base,data_dir,atm,rd,obs,ray,aod,1000,SMOKE_SEED,tau_file)
    (rd/'input-resolved.txt').write_text(text)
    syntax_s=base.run_process(uvspec,text,rd,syntax=True); solver_s=base.run_process(uvspec,text,rd,syntax=False)
    rad=rd/'mc.rad.spc'; std=rd/'mc.rad.std.spc'; q,qstd,n,w0,w1=base.integrate_ray(rad,std,ray['thetaDeg'],tables)
    if not(q>=0 and qstd>=0 and n>=1000 and 379.9<=w0<=380.1 and 779.9<=w1<=780.1): raise Failure('technical smoke spectrum invalid')
    r={'schemaVersion':1,'stageId':STAGE,'status':'PASS','scientificUseProhibited':True,'row':int(obs['row']),'rayIndex':ray['rayIndex'],'photons':1000,'seed':SMOKE_SEED,'q':q,'qStdConservative':qstd,'spectrumRows':n,'wavelengthStartNm':w0,'wavelengthEndNm':w1,'syntaxSeconds':syntax_s,'solverSeconds':solver_s}
    (out/'technical-smoke.json').write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps(r,sort_keys=True))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--baseline-runner',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--cams-profile',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--technical-smoke',action='store_true')
    a=ap.parse_args(); load_manifest(a.manifest)
    if a.row not in ROWS: raise Failure('row outside frozen universe')
    base=load_module(a.baseline_runner,'taylor_v1'); obs=base.load_observation(a.observations,a.row); tables=base.load_response(a.response); rays=base.quadrature(tables)
    if len(rays)!=64: raise Failure('expected 64 rays')
    profiles,sanity=load_cams_profile(a.cams_profile); t=parse_utc(obs['utc'])
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False); data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve(); u=a.uvspec.resolve()
    tau_path=out/'cams-site-grid-tau.dat'; tau_meta=write_tau_profile(base,atm,profiles,t,tau_path)
    if a.technical_smoke:
        technical_smoke(base,u,data,atm,obs,rays,tables,tau_path,out); return
    center=float(obs['aod550_primary_frozen']); local_minus=max(0.001,center-AOD_SIGMA); local_plus=center+AOD_SIGMA
    conditions=[
        ('base',center,BASE_PHOTONS,True),
        ('local_minus',local_minus,LOCAL_PHOTONS,False),
        ('local_plus',local_plus,LOCAL_PHOTONS,False),
        ('external_low',EXTERNAL_LOW,EXTERNAL_PHOTONS,False),
        ('external_high',EXTERNAL_HIGH,EXTERNAL_PHOTONS,False)]
    results={}
    for name,aod,photons,keep in conditions: results[name]=execute_condition(base,u,data,atm,obs,rays,tables,a.row,name,aod,photons,tau_path,out,keep)
    result={'schemaVersion':1,'stageId':STAGE,'executionKey':EXECUTION_KEY,'status':'COMPLETED','row':a.row,'utc':obs['utc'],'comparisonRole':obs['comparison_role'],'observedSQM':float(obs['observed_sqm_mag_arcsec2']),'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'surfacePressureHpa':float(obs['surface_pressure_hpa']),'aod550PrimaryFrozen':center,'spectralMode':'MYSTIC ALIS 380-780 nm, mc_spectral_is 550 nm','camsProfileWavelengthNm':532,'camsProfileSha256':sha(a.cams_profile),'camsEndpointSanity':sanity,'camsTauProfile':tau_meta,'conditions':results,'rayCount':64,'scientificSolverCalls':320,'scientificPhotonHistories':3200000,'scientificExecution':True,'successDoesNotAuthorizeProduction':True}
    (out/'row-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'status':'COMPLETED','row':a.row,'sunAltGeometricDeg':result['sunAltGeometricDeg'],'baseQ':results['base']['q'],'aod550':center},sort_keys=True))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(exc)}),file=sys.stderr); raise
