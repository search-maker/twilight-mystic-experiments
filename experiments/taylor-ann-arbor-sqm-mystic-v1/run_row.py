#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np

STAGE='taylor-ann-arbor-sqm-mystic-v1'
OMEGA_OFFICIAL=1.532
THETA_MAX=65.0
N_RADIAL=8
N_AZ=8
N_FILTER=1.55
PRIMARY_PHOTONS=20000
SENS_PHOTONS=5000
SENS=[0.05,0.10,0.15,0.20,0.30,0.40]
TIMEOUT=90

class Failure(RuntimeError): pass

def sha(path: Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()

def load_manifest(path:Path):
    x=json.loads(path.read_text());
    if x.get('stageId')!=STAGE or x.get('executionKey')!='taylor-ann-arbor-sqm-mystic-v1:scientific:1': raise Failure('wrong manifest')
    if x['mystic']['primaryPhotonsPerRay']!=PRIMARY_PHOTONS or x['mystic']['sensitivityPhotonsPerRay']!=SENS_PHOTONS: raise Failure('photon contract changed')
    if x['aodSensitivity550']!=SENS: raise Failure('sensitivity contract changed')
    return x

def load_observation(path:Path,row:int):
    with path.open(newline='') as f:
        matches=[r for r in csv.DictReader(f) if int(r['row'])==row]
    if len(matches)!=1: raise Failure(f'row {row} not unique')
    return matches[0]

def load_response(path:Path):
    tables={}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            if r['table']=='constants': continue
            tables.setdefault(r['table'],[]).append((float(r['x']),float(r['response'])))
    for k in tables: tables[k].sort()
    required={'hoya_cm500_1mm_transmittance','sqm_combined_onaxis_response_digitization','sqm_original_angular_response_digitization'}
    if not required <= set(tables): raise Failure('response tables missing')
    return tables

def interp_table(points,x,left=0.0,right=0.0):
    xp=np.array([p[0] for p in points],float); yp=np.array([p[1] for p in points],float)
    return np.interp(x,xp,yp,left=left,right=right)

def quadrature(tables):
    x,w=np.polynomial.legendre.leggauss(N_RADIAL)
    mu0=math.cos(math.radians(THETA_MAX))
    mu=0.5*(1-mu0)*x+0.5*(1+mu0)
    wmu=0.5*(1-mu0)*w
    rays=[]; idx=0
    ang=tables['sqm_original_angular_response_digitization']
    dphi=2*math.pi/N_AZ
    for im,(m,wm) in enumerate(zip(mu,wmu)):
        theta=math.degrees(math.acos(float(m)))
        D=float(interp_table(ang,np.array([theta]),left=1.0,right=0.0)[0])
        for ia in range(N_AZ):
            idx+=1
            phi=(ia+0.5)*360.0/N_AZ
            rays.append({'rayIndex':idx,'thetaDeg':theta,'targetAltitudeDeg':90-theta,'relativeAzimuthDeg':phi,'angularResponse':D,'weightSr':float(wm)*dphi*D,'normalizedWeight':float(wm)*dphi*D/OMEGA_OFFICIAL})
    omega=sum(r['weightSr'] for r in rays)
    if abs(omega-1.5344451183556775)>1e-10: raise Failure(f'quadrature changed: {omega}')
    return rays

def atmosphere_grid(atmosphere:Path,site_km:float):
    levels=[]
    for line in atmosphere.read_text().splitlines():
        s=line.strip()
        if not s or s.startswith('#'): continue
        try: levels.append(float(s.split()[0]))
        except Exception as exc: raise Failure('bad atmosphere grid') from exc
    if any(levels[i]<=levels[i+1] for i in range(len(levels)-1)): raise Failure('atmosphere not descending')
    above=sorted(v for v in levels if v>site_km)
    grid=[site_km,*above]
    if len(grid)<2: raise Failure('site outside atmosphere')
    return grid

def render(data_dir:Path, atmosphere:Path, case_dir:Path, obs, ray, aod, photons, seed):
    site_km=0.262
    grid=atmosphere_grid(atmosphere,site_km)
    sza=90.0-float(obs['sun_alt_geometric_deg'])
    umu=-math.cos(math.radians(ray['thetaDeg']))
    pressure=float(obs['surface_pressure_hpa'])
    grid_line='atm_z_grid '+' '.join(f'{z:.6f}' for z in grid)
    solar=data_dir/'solar_flux/atlas_plus_modtran'
    lines=[
        f'data_files_path {data_dir}',
        f'atmosphere_file {atmosphere}',
        f'source solar {solar}',
        'mol_abs_param crs',
        'wavelength 380 780',
        'day_of_year 220',
        f'sza {sza:.8f}',
        'phi0 0.0',
        'rte_solver mystic',
        'mc_spherical 1D',
        f'mc_photons {photons}',
        'mc_vroom off',
        'mc_std',
        f'mc_randomseed {seed}',
        f'mc_basename {case_dir / "mc"}',
        'mc_spectral_is 550.0',
        'albedo 0.150000',
        'aerosol_default',
        f'aerosol_set_tau_at_wvl 550 {aod:.8f}',
        f'pressure {pressure:.4f}',
        grid_line,
        'zout 0.000000',
        f'umu {umu:.10f}',
        f'phi {ray["relativeAzimuthDeg"]:.8f}',
        'quiet',
    ]
    return '\n'.join(lines)+'\n'

def run_process(uvspec:Path,text:str,cwd:Path,syntax=False):
    cmd=[str(uvspec)]+(['-c'] if syntax else [])
    t=time.monotonic()
    try: p=subprocess.run(cmd,input=text,text=True,capture_output=True,cwd=cwd,timeout=TIMEOUT)
    except subprocess.TimeoutExpired as exc: raise Failure(f'uvspec timeout syntax={syntax}') from exc
    if p.returncode!=0:
        (cwd/('syntax.stderr' if syntax else 'solver.stderr')).write_text(p.stderr or '')
        (cwd/('syntax.stdout' if syntax else 'solver.stdout')).write_text(p.stdout or '')
        raise Failure(f'uvspec exit {p.returncode} syntax={syntax}')
    return time.monotonic()-t

def parse_spectrum(path:Path):
    wl=[]; val=[]
    for line in path.read_text(errors='replace').splitlines():
        p=line.split()
        if len(p)<2: continue
        try: w=float(p[0]); v=float(p[-1])
        except ValueError: continue
        if 379.999<=w<=780.001 and math.isfinite(v): wl.append(w); val.append(v)
    if len(wl)<1000: raise Failure(f'too few spectrum rows {path}: {len(wl)}')
    order=np.argsort(wl)
    return np.array(wl)[order],np.array(val)[order]

def integrate_ray(rad:Path,std:Path,theta:float,tables):
    wl,L=parse_spectrum(rad); w2,S=parse_spectrum(std)
    if len(wl)!=len(w2) or np.max(np.abs(wl-w2))>1e-8: raise Failure('std wavelength mismatch')
    C0=interp_table(tables['sqm_combined_onaxis_response_digitization'],wl,left=0,right=0)
    T0=interp_table(tables['hoya_cm500_1mm_transmittance'],wl,left=0,right=0)
    ratio=1.0/math.sqrt(1.0-(math.sin(math.radians(theta))**2)/(N_FILTER**2))
    angle_factor=np.where(T0>0,np.power(T0,ratio-1.0),0.0)
    R=C0*angle_factor
    q=float(np.trapezoid(L*R,wl))
    qstd=float(np.trapezoid(np.abs(S*R),wl))
    return q,qstd,len(wl),float(wl[0]),float(wl[-1])

def gzip_file(path:Path):
    gz=path.with_suffix(path.suffix+'.gz')
    with path.open('rb') as src,gzip.open(gz,'wb',compresslevel=6) as dst: shutil.copyfileobj(src,dst)
    path.unlink(); return gz

def execute_one(uvspec,data_dir,atmosphere,obs,ray,aod,photons,seed,case_dir,tables,keep_raw):
    case_dir.mkdir(parents=True,exist_ok=False)
    text=render(data_dir,atmosphere,case_dir,obs,ray,aod,photons,seed)
    inp=case_dir/'input-resolved.txt'; inp.write_text(text)
    ts=run_process(uvspec,text,case_dir,syntax=True)
    tr=run_process(uvspec,text,case_dir,syntax=False)
    rad=case_dir/'mc.rad.spc'; std=case_dir/'mc.rad.std.spc'
    if not rad.is_file() or not std.is_file(): raise Failure(f'missing MYSTIC spectra in {case_dir}')
    q,qstd,n,w0,w1=integrate_ray(rad,std,ray['thetaDeg'],tables)
    rec={'rayIndex':ray['rayIndex'],'thetaDeg':ray['thetaDeg'],'relativeAzimuthDeg':ray['relativeAzimuthDeg'],'normalizedWeight':ray['normalizedWeight'],'aod550':aod,'photons':photons,'seed':seed,'q':q,'qStdConservative':qstd,'syntaxSeconds':ts,'solverSeconds':tr,'spectrumRows':n,'wavelengthStartNm':w0,'wavelengthEndNm':w1,'inputSha256':hashlib.sha256(text.encode()).hexdigest(),'radianceSha256':sha(rad),'stdSha256':sha(std)}
    if keep_raw:
        rec['radianceGzip']=gzip_file(rad).name; rec['stdGzip']=gzip_file(std).name
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

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--manifest',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args(); m=load_manifest(a.manifest); obs=load_observation(a.observations,a.row); tables=load_response(a.response); rays=quadrature(tables)
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False); atm=(a.data_dir/'atmmod/afglus.dat').resolve(); u=a.uvspec.resolve(); data=a.data_dir.resolve()
    if not 1<=a.row<=32: raise Failure('row outside frozen universe')
    primary=obs['primary_solar_geometry']=='true'
    base=[]
    for ray in rays:
        seed=941000000+a.row*1000+ray['rayIndex']
        base.append(execute_one(u,data,atm,obs,ray,float(obs['aod550_primary_frozen']),PRIMARY_PHOTONS,seed,out/'base'/f"ray-{ray['rayIndex']:02d}",tables,True))
    q,qs=aggregate(base)
    sens=[]
    if primary:
        for ia,aod in enumerate(SENS,1):
            rr=[]
            for ray in rays:
                seed=942000000+ia*100000+a.row*1000+ray['rayIndex']
                rr.append(execute_one(u,data,atm,obs,ray,aod,SENS_PHOTONS,seed,out/'sensitivity-work'/f'aod-{aod:.2f}'/f"ray-{ray['rayIndex']:02d}",tables,False))
            qq,ss=aggregate(rr); sens.append({'aod550':aod,'q':qq,'qStdConservative':ss,'rayCount':len(rr),'photonsPerRay':SENS_PHOTONS})
        shutil.rmtree(out/'sensitivity-work',ignore_errors=True)
    result={'schemaVersion':1,'stageId':STAGE,'status':'COMPLETED','row':a.row,'utc':obs['utc'],'comparisonRole':obs['comparison_role'],'observedSQM':float(obs['observed_sqm_mag_arcsec2']),'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'aod550Primary':float(obs['aod550_primary_frozen']),'surfacePressureHpa':float(obs['surface_pressure_hpa']),'primaryQ':q,'primaryQStdConservative':qs,'rayCount':len(base),'quadratureWeightedSolidAngleSr':sum(r['weightSr'] for r in rays),'effectiveSolidAngleOfficialSr':OMEGA_OFFICIAL,'primaryPhotonsPerRay':PRIMARY_PHOTONS,'baseRays':base,'aodSensitivity':sens,'scientificExecution':True,'successDoesNotAuthorizeProduction':True}
    (out/'row-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','row','utc','comparisonRole','primaryQ','primaryQStdConservative','aod550Primary')},sort_keys=True))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(exc)}),file=sys.stderr)
        raise
