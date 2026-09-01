#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

STAGE = "koomen-support-envelope-v1"
EXECUTION_KEY = "koomen-support-envelope-v1:scientific:49"
ROWS = list(range(18, 28))
REPLICATE_BASES = [1541000000, 1542000000, 1543000000, 1544000000]
PHOTONS = 200000
SITE_KM = 0.262
T0 = datetime(2025, 8, 8, 0, tzinfo=timezone.utc)
T3 = datetime(2025, 8, 8, 3, tzinfo=timezone.utc)
CAMS_PROFILE_SHA = "6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359"
RINGS_DEG = [0.15, 0.30, 0.45, 0.60, 0.75]
AZIMUTHS_DEG = [22.5 * i for i in range(16)]
CIE_WL = np.arange(380.0, 781.0, 10.0)
V_PHOT = np.array([
    0.00004,0.00012,0.0004,0.0012,0.0040,0.0116,0.023,0.038,
    0.060,0.09098,0.13902,0.20802,0.323,0.503,0.710,0.862,
    0.954,0.99495,0.995,0.952,0.870,0.757,0.631,0.503,0.381,
    0.265,0.175,0.107,0.061,0.032,0.017,0.00821,0.004102,
    0.002091,0.001047,0.00052,0.000249,0.00012,0.00006,0.00003,
    0.000015,
], float)

class Failure(RuntimeError):
    pass

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise Failure(f"cannot import {path}")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)

def load_observation(path: Path, row: int):
    rr=[r for r in csv.DictReader(path.open(newline="")) if int(r["row"])==row]
    if len(rr)!=1: raise Failure(f"row {row} not unique")
    return rr[0]

def load_cams_profile(path: Path):
    if sha(path)!=CAMS_PROFILE_SHA: raise Failure("CAMS profile checksum mismatch")
    rows=list(csv.DictReader(path.open(newline="")))
    by={T0:[],T3:[]}
    for r in rows:
        lead=int(r["leadHour"])
        t=T0 if lead==12 else T3 if lead==15 else None
        if t is not None:
            by[t].append((int(r["modelLevel"]),float(r["heightAGL_m"]),float(r["extinction532_m-1"])))
    out={}
    for t in (T0,T3):
        rr=by[t]
        if len(rr)!=137 or sorted(x[0] for x in rr)!=list(range(1,138)):
            raise Failure("invalid CAMS level universe")
        pts=sorted((h,b) for _,h,b in rr)
        z=np.array([p[0] for p in pts],float); b=np.array([p[1] for p in pts],float)
        if np.any(np.diff(z)<=0) or np.any(b<0) or z[0]<0: raise Failure("invalid CAMS profile")
        out[t]=(np.concatenate(([0.0],z)),np.concatenate(([b[0]],b)))
    return out

def beta_at(profile,z):
    x,y=profile
    return float(np.interp(z,x,y,left=y[0],right=0.0))

def time_beta(profiles,t,z):
    if not T0<=t<=T3: raise Failure("observation outside CAMS interpolation interval")
    w=(t-T0).total_seconds()/(T3-T0).total_seconds()
    return (1-w)*beta_at(profiles[T0],z)+w*beta_at(profiles[T3],z)

def layer_tau_raw(profiles,t,lo_abs_km,hi_abs_km):
    lo=(lo_abs_km-SITE_KM)*1000.0; hi=(hi_abs_km-SITE_KM)*1000.0
    anchors={lo,hi}
    for x,_ in profiles.values():
        anchors.update(float(z) for z in x if lo<z<hi)
    zz=np.array(sorted(anchors),float); bb=np.array([time_beta(profiles,t,float(z)) for z in zz],float)
    return float(np.trapezoid(bb,zz))

def write_tau_profile(base,atmosphere,profiles,t,out):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    layer=[layer_tau_raw(profiles,t,grid[i],grid[i+1]) for i in range(len(grid)-1)]
    total=sum(layer)
    if not total>0: raise Failure("zero CAMS above-site integral")
    tau={grid[i]:layer[i]/total for i in range(len(layer))}; tau[grid[-1]]=0.0
    out.write_text("# CAMS 532-nm vertical extinction shape normalized to unit layer tau; proxy only\n"+"\n".join(f"{z:.6f} {tau[z]:.15e}" for z in reversed(grid))+"\n")
    return {"tauSum":sum(tau.values()),"sourceProfileSha256":CAMS_PROFILE_SHA,"tauFileSha256":sha(out)}

def render_profile(base,data_dir,atmosphere,case_dir,obs,ray,aod,seed,tau_file):
    grid=base.atmosphere_grid(atmosphere,SITE_KM)
    sza=90.0-float(obs["sun_alt_geometric_deg"])
    umu=-math.cos(math.radians(ray["thetaDeg"]))
    solar=data_dir/"solar_flux/atlas_plus_modtran"
    lines=[f"data_files_path {data_dir}",f"atmosphere_file {atmosphere}",f"source solar {solar}","mol_abs_param crs","wavelength 380 780","day_of_year 220",f"sza {sza:.8f}","phi0 0.0","rte_solver mystic","mc_spherical 1D",f"mc_photons {PHOTONS}","mc_vroom off","mc_std",f"mc_randomseed {seed}",f"mc_basename {case_dir/'mc'}","mc_spectral_is 550.0","albedo 0.150000","aerosol_default",f"aerosol_file tau {tau_file.resolve()}",f"aerosol_set_tau_at_wvl 550 {aod:.8f}",f"pressure {float(obs['surface_pressure_hpa']):.4f}","atm_z_grid "+" ".join(f"{z:.6f}" for z in grid),"zout 0.000000",f"umu {umu:.10f}",f"phi {ray['relativeAzimuthDeg']:.8f}","quiet"]
    return "\n".join(lines)+"\n"

def directions():
    out=[{"directionIndex":0,"radiusDeg":0.0,"thetaDeg":0.0,"relativeAzimuthDeg":0.0,"ring":"center"}]
    idx=0
    for r in RINGS_DEG:
        for az in AZIMUTHS_DEG:
            idx+=1
            out.append({"directionIndex":idx,"radiusDeg":r,"thetaDeg":r,"relativeAzimuthDeg":az,"ring":f"r{r:.2f}"})
    if len(out)!=81: raise Failure("direction grid changed")
    return out

def integrate_operators(base,rad,std,theta,tables):
    wl,L=base.parse_spectrum(rad); w2,S=base.parse_spectrum(std)
    if len(wl)!=len(w2) or np.max(np.abs(wl-w2))>1e-8: raise Failure("std wavelength mismatch")
    v=np.interp(wl,CIE_WL,V_PHOT,left=0.0,right=0.0)
    phot=float(np.trapezoid(L*v,wl))
    C0=base.interp_table(tables["sqm_combined_onaxis_response_digitization"],wl,left=0,right=0)
    T0=base.interp_table(tables["hoya_cm500_1mm_transmittance"],wl,left=0,right=0)
    ratio=1.0/math.sqrt(1.0-(math.sin(math.radians(theta))**2)/(1.55**2))
    af=np.where(T0>0,np.power(T0,ratio-1.0),0.0)
    sqm=float(np.trapezoid(L*C0*af,wl))
    if not phot>0 or not sqm>0: raise Failure("non-positive operator integral")
    return phot,sqm

def execute(base,uvspec,text,case_dir,theta,tables):
    case_dir.mkdir(parents=True,exist_ok=False)
    (case_dir/"input-resolved.txt").write_text(text)
    base.run_process(uvspec,text,case_dir,syntax=True)
    base.run_process(uvspec,text,case_dir,syntax=False)
    rad=case_dir/"mc.rad.spc"; std=case_dir/"mc.rad.std.spc"
    if not rad.is_file() or not std.is_file(): raise Failure("missing MYSTIC spectra")
    phot,sqm=integrate_operators(base,rad,std,theta,tables)
    rec={"photopicQ":phot,"sqmConditionalQ":sqm,"inputSha256":hashlib.sha256(text.encode()).hexdigest(),"radianceSha256":sha(rad),"stdSha256":sha(std)}
    shutil.rmtree(case_dir,ignore_errors=True)
    return rec

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--row",type=int,required=True); ap.add_argument("--replicate",type=int,required=True)
    ap.add_argument("--baseline-runner",type=Path,required=True); ap.add_argument("--observations",type=Path,required=True)
    ap.add_argument("--response",type=Path,required=True); ap.add_argument("--cams-profile",type=Path,required=True)
    ap.add_argument("--uvspec",type=Path,required=True); ap.add_argument("--data-dir",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True)
    a=ap.parse_args()
    if a.row not in ROWS or not 1<=a.replicate<=4: raise Failure("row/replicate outside frozen universe")
    base=load_module(a.baseline_runner,"taylor_v1")
    obs=load_observation(a.observations,a.row); tables=base.load_response(a.response)
    profiles=load_cams_profile(a.cams_profile); t=parse_utc(obs["utc"])
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False)
    data=a.data_dir.resolve(); atmosphere=(data/"atmmod/afglus.dat").resolve(); uvspec=a.uvspec.resolve()
    tau_path=out/"cams-site-grid-tau.dat"; tau_meta=write_tau_profile(base,atmosphere,profiles,t,tau_path)
    aod=float(obs["aod550_primary_frozen"])
    seed=REPLICATE_BASES[a.replicate-1]+a.row*1000
    records=[]
    for d in directions():
        ray={"thetaDeg":d["thetaDeg"],"relativeAzimuthDeg":d["relativeAzimuthDeg"]}
        bdir=out/"work"/"baseline"/f"d-{d['directionIndex']:02d}"
        pdir=out/"work"/"profile"/f"d-{d['directionIndex']:02d}"
        btext=base.render(data,atmosphere,bdir,obs,ray,aod,PHOTONS,seed)
        ptext=render_profile(base,data,atmosphere,pdir,obs,ray,aod,seed,tau_path)
        br=execute(base,uvspec,btext,bdir,d["thetaDeg"],tables)
        pr=execute(base,uvspec,ptext,pdir,d["thetaDeg"],tables)
        records.append({**d,"seed":seed,"baseline":br,"profile":pr})
    result={"schemaVersion":1,"stageId":STAGE,"executionKey":EXECUTION_KEY,"status":"COMPLETED","row":a.row,"replicate":a.replicate,"replicateSeedBase":REPLICATE_BASES[a.replicate-1],"seedReusedAcrossDirectionsAndCasesForCRN":seed,"utc":obs["utc"],"comparisonRole":obs["comparison_role"],"sunAltGeometricDeg":float(obs["sun_alt_geometric_deg"]),"aod550FrozenIdenticalBetweenCases":aod,"photonsPerDirectionPerCase":PHOTONS,"directionCount":81,"supportRadiusDeg":0.75,"spectralMode":"MYSTIC ALIS 380-780 nm; mc_spectral_is 550 nm","operators":{"photopic":"standard CIE photopic V(lambda), conditional diagnostic only; not claimed exact historical P22+filter","sqmConditional":"frozen original-SQM spectral/filter-angle response; angular weighting NOT applied"},"profileProvenance":tau_meta,"records":records,"scientificBoundary":{"exactKoomenAcceptanceReconstructed":False,"weightedKoomenMagnitudeReported":False,"TaylorResidualUsedToChooseAnything":False,"productionAuthorized":False}}
    (out/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"status":"COMPLETED","row":a.row,"replicate":a.replicate,"directionCount":81,"solverCalls":162,"seed":seed},sort_keys=True))

if __name__=="__main__":
    main()
