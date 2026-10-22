#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

STAGE='taylor-hrrr-vertical-sensitivity-v3'
ROWS=list(range(23,33))
PHOTONS=50000
SITE_KM=0.262
TIMEOUT=120
T1=datetime(2025,8,8,1,tzinfo=timezone.utc)
T2=datetime(2025,8,8,2,tzinfo=timezone.utc)

class Failure(RuntimeError): pass

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def load_module(path:Path):
    spec=importlib.util.spec_from_file_location('taylor_v1',path)
    if spec is None or spec.loader is None: raise Failure('cannot import frozen Taylor runner')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def parse_utc(s:str)->datetime:
    return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)

def load_hrrr_raw(path:Path):
    if sha(path)!='929e787c15f8d689bf63a732152eb552e621542325e4942d4d48bf91eb6d75a9':
        raise Failure('HRRR raw profile checksum mismatch')
    rows=list(csv.DictReader(path.open(newline='')))
    by_time={T1:{},T2:{}}; colmd={}
    for r in rows:
        t=parse_utc(r['valid_time_utc'])
        if t not in by_time: continue
        if r['variable_from_idx']=='COLMD' and r['level_desc_from_idx']=='entire atmosphere (considered as a single layer)':
            colmd.setdefault(t,[]).append(float(r['value']))
        if r['product']!='nat' or r['type_of_level']!='hybrid': continue
        v=r['variable_from_idx']
        if v not in {'HGT','MASSDEN','PRES'}: continue
        lev=int(round(float(r['level'])))
        if 1<=lev<=50: by_time[t].setdefault(lev,{})[v]=float(r['value'])
    profiles={}; sanity={}
    for t in (T1,T2):
        d=by_time[t]
        if sorted(d)!=list(range(1,51)): raise Failure(f'HRRR hybrid level universe wrong at {t}')
        if any(not {'HGT','MASSDEN','PRES'} <= set(d[i]) for i in range(1,51)): raise Failure('HRRR HGT/MASSDEN/PRES join incomplete')
        ground=d[1]['HGT']
        pts=[(d[i]['HGT']-ground,d[i]['MASSDEN'],d[i]['PRES']) for i in range(1,51)]
        z=np.array([p[0] for p in pts],float); rho=np.array([p[1] for p in pts],float)
        if abs(z[0])>1e-8 or np.any(np.diff(z)<=0) or np.any(rho<0): raise Failure('invalid HRRR vertical profile')
        integ=float(np.trapezoid(rho,z))
        cvals=colmd.get(t,[])
        if not cvals or max(cvals)-min(cvals)>1e-12: raise Failure('HRRR COLMD duplicate mismatch/missing')
        c=float(cvals[0]); ratio=integ/c
        if not 0.98<=ratio<=1.02: raise Failure(f'HRRR rho dz / COLMD sanity failed: {ratio}')
        profiles[t]=[(float(a),float(b)) for a,b,_ in pts]
        sanity[t.isoformat()]={'groundHgtM':ground,'integratedKgM2':integ,'colmdKgM2':c,'integralToColumnRatio':ratio,'levelCount':50}
    return profiles,sanity

def rho_at(points,z_m):
    x=np.array([p[0] for p in points],float); y=np.array([p[1] for p in points],float)
    return float(np.interp(z_m,x,y,left=y[0],right=0.0))

def time_interp_rho(profiles,t,z_m):
    if not T1<=t<=T2: raise Failure('Taylor row outside frozen HRRR interpolation interval')
    w=(t-T1).total_seconds()/3600.0
    return (1-w)*rho_at(profiles[T1],z_m)+w*rho_at(profiles[T2],z_m)

def layer_mass(profiles,t,lo_abs_km,hi_abs_km):
    if hi_abs_km<=lo_abs_km: return 0.0
    lo_agl=(lo_abs_km-SITE_KM)*1000.0; hi_agl=(hi_abs_km-SITE_KM)*1000.0
    anchors={lo_agl,hi_agl}
    for pts in profiles.values():
        for z,_ in pts:
            if lo_agl<z<hi_agl: anchors.add(z)
    z=np.array(sorted(anchors),float)
    rho=np.array([time_interp_rho(profiles,t,float(v)) for v in z],float)
    return float(np.trapezoid(rho,z))

def write_tau_profile(base,atmosphere:Path,profiles,t,out:Path):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)  # ascending: 0.262,1,...120
    masses=[]
    for i in range(len(grid)-1): masses.append(layer_mass(profiles,t,grid[i],grid[i+1]))
    total=sum(masses)
    if not total>0: raise Failure('zero above-site HRRR integrated smoke mass')
    # aerosol_file tau uses layer optical depths. Associate each layer with its
    # lower boundary, as in the libRadtran tau-profile convention. Top level is 0.
    tau={grid[i]:masses[i]/total for i in range(len(masses))}; tau[grid[-1]]=0.0
    if abs(sum(tau.values())-1.0)>1e-10: raise Failure('site-grid tau profile not normalized')
    desc=list(reversed(grid))
    out.write_text('# HRRR-Smoke vertical-shape proxy on exact common site grid; layer tau sum=1\n'+'\n'.join(f'{z:.6f} {tau[z]:.15e}' for z in desc)+'\n')
    return {'gridBottomKm':grid[0],'gridTopKm':grid[-1],'layerCount':len(grid)-1,
            'aboveSiteIntegratedSmokeKgM2':total,'tauSum':sum(tau.values()),'tauFileSha256':sha(out)}

def render(base,data_dir:Path,atmosphere:Path,case_dir:Path,obs,ray,aod,seed,tau_file:Path|None):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    sza=90.0-float(obs['sun_alt_geometric_deg'])
    umu=-math.cos(math.radians(ray['thetaDeg']))
    pressure=float(obs['surface_pressure_hpa'])
    solar=data_dir/'solar_flux/atlas_plus_modtran'
    lines=[f'data_files_path {data_dir}',f'atmosphere_file {atmosphere}',f'source solar {solar}',
           'wavelength 550','day_of_year 220',f'sza {sza:.8f}','phi0 0.0','rte_solver mystic','mc_spherical 1D',
           f'mc_photons {PHOTONS}','mc_vroom off','mc_std',f'mc_randomseed {seed}',f'mc_basename {case_dir / "mc"}',
           'albedo 0.150000','aerosol_default']
    if tau_file is not None: lines.append(f'aerosol_file tau {tau_file.resolve()}')
    lines += [f'aerosol_set_tau_at_wvl 550 {aod:.8f}',f'pressure {pressure:.4f}',
              'atm_z_grid '+' '.join(f'{z:.6f}' for z in grid),'zout 0.000000',
              f'umu {umu:.10f}',f'phi {ray["relativeAzimuthDeg"]:.8f}','quiet']
    return '\n'.join(lines)+'\n'

def run_uvspec(uvspec:Path,text:str,cwd:Path,syntax=False):
    cmd=[str(uvspec)]+(['-c'] if syntax else [])
    t=time.monotonic()
    try: p=subprocess.run(cmd,input=text,text=True,capture_output=True,cwd=cwd,timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc: raise Failure(f'uvspec timeout syntax={syntax}') from exc
    if p.returncode!=0:
        (cwd/('syntax.stdout' if syntax else 'solver.stdout')).write_text(p.stdout or '')
        (cwd/('syntax.stderr' if syntax else 'solver.stderr')).write_text(p.stderr or '')
        raise Failure(f'uvspec exit {p.returncode}, syntax={syntax}')
    return time.monotonic()-t

def parse_550(path:Path):
    vals=[]
    for line in path.read_text(errors='replace').splitlines():
        p=line.split()
        if len(p)<2: continue
        try: row=tuple(map(float,p))
        except ValueError: continue
        if all(math.isfinite(x) for x in row): vals.append(row)
    if len(vals)!=1: raise Failure(f'expected exactly one finite 550-nm row in {path}, got {len(vals)}')
    if abs(vals[0][0]-550.0)>1e-8: raise Failure(f'wrong wavelength in {path}: {vals[0][0]}')
    return float(vals[0][-1]),vals[0]

def effective_weight(base,tables,ray):
    T0=float(base.interp_table(tables['hoya_cm500_1mm_transmittance'],np.array([550.0]),left=0,right=0)[0])
    ratio=1.0/math.sqrt(1.0-(math.sin(math.radians(ray['thetaDeg']))**2)/(base.N_FILTER**2))
    angle_factor=T0**(ratio-1.0) if T0>0 else 0.0
    return float(ray['normalizedWeight'])*angle_factor

def execute_condition(base,uvspec,data_dir,atm,obs,rays,tables,aod,row,condition,tau_file,out):
    records=[]; seed_base=949000000 if condition=='default_vertical' else 950000000
    for ray in rays:
        rd=out/condition/f"ray-{ray['rayIndex']:02d}"; rd.mkdir(parents=True,exist_ok=False)
        seed=seed_base+row*1000+ray['rayIndex']
        text=render(base,data_dir,atm,rd,obs,ray,aod,seed,tau_file if condition=='hrrr_smoke_shape' else None)
        inp=rd/'input-resolved.txt'; inp.write_text(text)
        syntax_sec=run_uvspec(uvspec,text,rd,syntax=True)
        solver_sec=run_uvspec(uvspec,text,rd,syntax=False)
        rad=rd/'mc.rad.spc'; std=rd/'mc.rad.std.spc'
        if not rad.is_file() or not std.is_file(): raise Failure('missing MYSTIC 550-nm spectra')
        q,radrow=parse_550(rad); qs,stdrow=parse_550(std)
        if q<0 or qs<0: raise Failure('negative radiance or standard deviation')
        records.append({'rayIndex':ray['rayIndex'],'thetaDeg':ray['thetaDeg'],'relativeAzimuthDeg':ray['relativeAzimuthDeg'],
                        'weight550':effective_weight(base,tables,ray),'seed':seed,'q550':q,'qStd550':qs,
                        'syntaxSeconds':syntax_sec,'solverSeconds':solver_sec,'radRow':radrow,'stdRow':stdrow,
                        'inputSha256':hashlib.sha256(text.encode()).hexdigest(),'radianceSha256':sha(rad),'stdSha256':sha(std)})
    q=sum(r['weight550']*r['q550'] for r in records)
    qs=math.sqrt(sum((r['weight550']*r['qStd550'])**2 for r in records))
    return records,q,qs,sum(r['weight550'] for r in records)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--baseline-runner',type=Path,required=True)
    ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True)
    ap.add_argument('--hrrr-raw',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True)
    ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args()
    if a.row not in ROWS: raise Failure('row outside frozen diagnostic universe')
    base=load_module(a.baseline_runner); obs=base.load_observation(a.observations,a.row); tables=base.load_response(a.response); rays=base.quadrature(tables)
    profiles,sanity=load_hrrr_raw(a.hrrr_raw); t=parse_utc(obs['utc'])
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    atm=(a.data_dir/'atmmod/afglus.dat').resolve(); data=a.data_dir.resolve(); u=a.uvspec.resolve()
    tau_meta=write_tau_profile(base,atm,profiles,t,out/'hrrr-site-grid-tau.dat'); aod=float(obs['aod550_primary_frozen'])
    drec,dq,dqs,sw=execute_condition(base,u,data,atm,obs,rays,tables,aod,a.row,'default_vertical',None,out)
    hrec,hq,hqs,_=execute_condition(base,u,data,atm,obs,rays,tables,aod,a.row,'hrrr_smoke_shape',out/'hrrr-site-grid-tau.dat',out)
    if dq<=0 or hq<=0: raise Failure('non-positive aggregate 550-nm radiance')
    delta=-2.5*math.log10(hq/dq)
    sigma_delta=(2.5/math.log(10))*math.sqrt((dqs/dq)**2+(hqs/hq)**2)
    result={'schemaVersion':3,'stageId':STAGE,'status':'COMPLETED','row':a.row,'utc':obs['utc'],
            'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'observedSQM':float(obs['observed_sqm_mag_arcsec2']),
            'comparisonRole':obs['comparison_role'],'aod550':aod,'surfacePressureHpa':float(obs['surface_pressure_hpa']),
            'spectralMode':'true monochromatic 550 nm; no ALIS','photonsPerRayPerCondition':PHOTONS,'rayCount':len(rays),
            'effectiveWeightSum550':sw,'hrrrRawSha256':sha(a.hrrr_raw),'hrrrColumnSanity':sanity,'hrrrTauProfile':tau_meta,
            'defaultQ550':dq,'defaultQStd550':dqs,'hrrrShapeQ550':hq,'hrrrShapeQStd550':hqs,
            'deltaMag550HrrrMinusDefault':delta,'deltaMag550McSigmaApprox':sigma_delta,
            'defaultRays':drec,'hrrrShapeRays':hrec,
            'interpretation':'Vertical-shape sensitivity only; HRRR smoke mass is a normalized shape proxy, not calibrated total-aerosol extinction.'}
    (out/'row-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['status','row','sunAltGeometricDeg','aod550','defaultQ550','hrrrShapeQ550','deltaMag550HrrrMinusDefault','deltaMag550McSigmaApprox']},sort_keys=True))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(exc)}),file=sys.stderr); raise
