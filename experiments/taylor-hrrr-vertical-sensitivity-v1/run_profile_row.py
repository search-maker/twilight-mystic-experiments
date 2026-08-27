#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

STAGE='taylor-hrrr-vertical-sensitivity-v1'
ROWS=list(range(23,33))
PHOTONS=50000
SITE_KM=0.262
TIMEOUT=120

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

def load_hrrr(path:Path):
    groups={}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            t=parse_utc(r['valid_time_utc'])
            groups.setdefault(t,[]).append((float(r['height_m_agl']),float(r['smoke_kg_m3'])))
    for t in groups: groups[t].sort()
    need=[datetime(2025,8,8,1,tzinfo=timezone.utc),datetime(2025,8,8,2,tzinfo=timezone.utc)]
    if any(t not in groups for t in need): raise Failure('HRRR 01/02 UTC profiles missing')
    if any(len(groups[t])!=50 for t in need): raise Failure('HRRR expected 50 hybrid levels')
    return groups

def rho_at(points,z_m):
    x=np.array([p[0] for p in points],float); y=np.array([p[1] for p in points],float)
    return float(np.interp(z_m,x,y,left=y[0],right=0.0))

def time_interp_rho(groups,t,z_m):
    t1=datetime(2025,8,8,1,tzinfo=timezone.utc); t2=datetime(2025,8,8,2,tzinfo=timezone.utc)
    if not t1 <= t <= t2: raise Failure('row time outside frozen HRRR interpolation interval')
    w=(t-t1).total_seconds()/3600.0
    return (1-w)*rho_at(groups[t1],z_m)+w*rho_at(groups[t2],z_m)

def atmosphere_levels(path:Path):
    out=[]
    for line in path.read_text().splitlines():
        s=line.strip()
        if not s or s.startswith('#'): continue
        out.append(float(s.split()[0]))
    if any(out[i] <= out[i+1] for i in range(len(out)-1)): raise Failure('atmosphere not top-down')
    if out[-1]!=0.0: raise Failure('expected AFGLUS 0 km bottom')
    return out

def layer_mass(groups,t,lo_km,hi_km):
    lo=max(lo_km,SITE_KM); hi=hi_km
    if hi<=lo: return 0.0
    lo_agl=(lo-SITE_KM)*1000.0; hi_agl=(hi-SITE_KM)*1000.0
    anchors={lo_agl,hi_agl}
    for pts in groups.values():
        for z,_ in pts:
            if lo_agl<z<hi_agl: anchors.add(z)
    z=np.array(sorted(anchors),float)
    rho=np.array([time_interp_rho(groups,t,float(v)) for v in z],float)
    return float(np.trapezoid(rho,z))

def write_tau_profile(atm:Path,groups,t,out:Path):
    levels=atmosphere_levels(atm)
    tau={z:0.0 for z in levels}; masses=[]
    for i in range(len(levels)-1):
        hi=levels[i]; lo=levels[i+1]
        m=layer_mass(groups,t,lo,hi); tau[lo]=m; masses.append(m)
    total=sum(masses)
    if not total>0: raise Failure('zero HRRR integrated smoke mass')
    for z in tau: tau[z]/=total
    if abs(sum(tau.values())-1.0)>1e-10: raise Failure('tau profile not normalized')
    lines=['# HRRR-Smoke shape-only aerosol tau profile; normalized sum=1 before aerosol_set_tau_at_wvl']
    lines += [f'{z:10.6f} {tau[z]:.15e}' for z in levels]
    out.write_text('\n'.join(lines)+'\n')
    return {'integratedSmokeKgM2':total,'tauSum':sum(tau.values()),'profileSha256':sha(out)}

def render(base,data_dir:Path,atmosphere:Path,case_dir:Path,obs,ray,aod,seed,tau_file:Path|None):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    sza=90.0-float(obs['sun_alt_geometric_deg'])
    umu=-math.cos(math.radians(ray['thetaDeg']))
    pressure=float(obs['surface_pressure_hpa'])
    solar=data_dir/'solar_flux/atlas_plus_modtran'
    lines=[f'data_files_path {data_dir}',f'atmosphere_file {atmosphere}',f'source solar {solar}',
        'mol_abs_param crs','wavelength 550 550','day_of_year 220',f'sza {sza:.8f}','phi0 0.0',
        'rte_solver mystic','mc_spherical 1D',f'mc_photons {PHOTONS}','mc_vroom off','mc_std',
        f'mc_randomseed {seed}',f'mc_basename {case_dir / "mc"}','mc_spectral_is 550.0','albedo 0.150000','aerosol_default']
    if tau_file is not None: lines.append(f'aerosol_file tau {tau_file.resolve()}')
    lines += [f'aerosol_set_tau_at_wvl 550 {aod:.8f}',f'pressure {pressure:.4f}',
              'atm_z_grid '+' '.join(f'{z:.6f}' for z in grid),'zout 0.000000',
              f'umu {umu:.10f}',f'phi {ray["relativeAzimuthDeg"]:.8f}','quiet']
    return '\n'.join(lines)+'\n'

def run_uvspec(uvspec:Path,text:str,cwd:Path,syntax=False):
    cmd=[str(uvspec)]+(['-c'] if syntax else [])
    t=time.monotonic(); p=subprocess.run(cmd,input=text,text=True,capture_output=True,cwd=cwd,timeout=TIMEOUT)
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
        try: w=float(p[0]); v=float(p[-1])
        except ValueError: continue
        if math.isfinite(w) and math.isfinite(v): vals.append((w,v))
    if not vals: raise Failure(f'no spectral data in {path}')
    w,v=min(vals,key=lambda x:abs(x[0]-550.0))
    if abs(w-550.0)>0.11: raise Failure(f'no 550 nm output; nearest {w}')
    return float(v),len(vals)

def effective_weight(base,tables,ray):
    T0=float(base.interp_table(tables['hoya_cm500_1mm_transmittance'],np.array([550.0]),left=0,right=0)[0])
    ratio=1.0/math.sqrt(1.0-(math.sin(math.radians(ray['thetaDeg']))**2)/(base.N_FILTER**2))
    angle_factor=T0**(ratio-1.0) if T0>0 else 0.0
    return float(ray['normalizedWeight'])*angle_factor

def execute_condition(base,uvspec,data_dir,atm,obs,rays,tables,aod,row,condition,tau_file,out):
    rec=[]; seed_base=943000000 if condition=='default_vertical' else 944000000
    for ray in rays:
        rd=out/condition/f"ray-{ray['rayIndex']:02d}"; rd.mkdir(parents=True,exist_ok=False)
        seed=seed_base+row*1000+ray['rayIndex']
        text=render(base,data_dir,atm,rd,obs,ray,aod,seed,tau_file if condition!='default_vertical' else None)
        (rd/'input-resolved.txt').write_text(text)
        sec=run_uvspec(uvspec,text,rd,syntax=False)
        rad=rd/'mc.rad.spc'; std=rd/'mc.rad.std.spc'
        if not rad.is_file() or not std.is_file(): raise Failure('missing MYSTIC spectra')
        q,n=parse_550(rad); qs,_=parse_550(std)
        rec.append({'rayIndex':ray['rayIndex'],'thetaDeg':ray['thetaDeg'],'relativeAzimuthDeg':ray['relativeAzimuthDeg'],
                    'weight550':effective_weight(base,tables,ray),'seed':seed,'q550':q,'qStd550':abs(qs),
                    'solverSeconds':sec,'spectrumRows':n,'inputSha256':hashlib.sha256(text.encode()).hexdigest(),
                    'radianceSha256':sha(rad),'stdSha256':sha(std)})
    sw=sum(r['weight550'] for r in rec)
    q=sum(r['weight550']*r['q550'] for r in rec)/sw
    qs=math.sqrt(sum((r['weight550']*r['qStd550'])**2 for r in rec))/sw
    return rec,q,qs,sw

def syntax_probe(base,uvspec,data_dir,atm,obs,ray,aod,tau_file,out):
    for condition,tf in [('default_vertical',None),('hrrr_smoke_shape',tau_file)]:
        d=out/condition; d.mkdir(parents=True,exist_ok=True)
        text=render(base,data_dir,atm,d,obs,ray,aod,999000001 if tf is None else 999000002,tf)
        (d/'input-resolved.txt').write_text(text); run_uvspec(uvspec,text,d,syntax=True)
    (out/'syntax-pass.json').write_text(json.dumps({'status':'PASS','row':int(obs['row'])},indent=2)+'\n')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--baseline-runner',type=Path,required=True)
    ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True)
    ap.add_argument('--hrrr-profile',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True)
    ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--syntax-only',action='store_true')
    a=ap.parse_args()
    if a.row not in ROWS: raise Failure('row outside frozen diagnostic universe')
    base=load_module(a.baseline_runner); obs=base.load_observation(a.observations,a.row); tables=base.load_response(a.response); rays=base.quadrature(tables)
    groups=load_hrrr(a.hrrr_profile); t=parse_utc(obs['utc']); out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    atm=(a.data_dir/'atmmod/afglus.dat').resolve(); data=a.data_dir.resolve(); u=a.uvspec.resolve()
    tau_meta=write_tau_profile(atm,groups,t,out/'hrrr-shape-tau.dat'); aod=float(obs['aod550_primary_frozen'])
    if a.syntax_only:
        syntax_probe(base,u,data,atm,obs,rays[0],aod,out/'syntax'); print(json.dumps({'status':'SYNTAX_PASS','row':a.row,'tau':tau_meta},sort_keys=True)); return
    drec,dq,dqs,sw=execute_condition(base,u,data,atm,obs,rays,tables,aod,a.row,'default_vertical',None,out)
    hrec,hq,hqs,_=execute_condition(base,u,data,atm,obs,rays,tables,aod,a.row,'hrrr_smoke_shape',out/'hrrr-shape-tau.dat',out)
    delta=-2.5*math.log10(hq/dq)
    result={'schemaVersion':1,'stageId':STAGE,'status':'COMPLETED','row':a.row,'utc':obs['utc'],
            'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'observedSQM':float(obs['observed_sqm_mag_arcsec2']),
            'comparisonRole':obs['comparison_role'],'aod550':aod,'surfacePressureHpa':float(obs['surface_pressure_hpa']),
            'photonsPerRayPerCondition':PHOTONS,'rayCount':len(rays),'effectiveWeightSum550':sw,'hrrrTauProfile':tau_meta,
            'defaultQ550':dq,'defaultQStd550':dqs,'hrrrShapeQ550':hq,'hrrrShapeQStd550':hqs,'deltaMag550HrrrMinusDefault':delta,
            'defaultRays':drec,'hrrrShapeRays':hrec,
            'interpretation':'Vertical-shape sensitivity only; HRRR smoke mass is used as a normalized shape, not as calibrated total aerosol extinction.'}
    (out/'row-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['status','row','sunAltGeometricDeg','aod550','defaultQ550','hrrrShapeQ550','deltaMag550HrrrMinusDefault']},sort_keys=True))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(exc)}),file=sys.stderr); raise
