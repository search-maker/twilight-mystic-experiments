#!/usr/bin/env python3
"""Vectorized generator for the frozen ENA/SWS E0 dusk event universe.

Physics/convention is identical to audit_ena_sws_e0.py: NREL SPA via
pvlib.solarposition.spa_python, geometric/unrefracted elevation, pressure=0,
ENA C1 coordinates/elevation, and binary refinement for -6/-7/-8. The only
optimization is batching SPA evaluations across civil dates.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, importlib.util, json, sys
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pvlib
UTC=dt.timezone.utc; LOCAL_TZ=ZoneInfo('Atlantic/Azores')
SITE_LAT=39.0916; SITE_LON=-28.0257; SITE_ALT_M=30.0
START_DATE=dt.date(2017,4,5); END_DATE=dt.date(2019,9,27)
TARGETS=(-8.0,-7.0,-6.0); EXPECTED=906

def date_list():
    out=[]; d=START_DATE
    while d<=END_DATE: out.append(d); d+=dt.timedelta(days=1)
    return out

def spa(index):
    r=pvlib.solarposition.spa_python(index,latitude=SITE_LAT,longitude=SITE_LON,altitude=SITE_ALT_M,
        pressure=0.0,temperature=12.0,delta_t=None,how='numpy')
    return np.asarray(r['elevation'],dtype=float)

def iso(ts): return ts.to_pydatetime().astimezone(UTC).isoformat(timespec='microseconds').replace('+00:00','Z')

def coarse_brackets(days):
    left={t:[] for t in TARGETS}; right={t:[] for t in TARGETS}; fl={t:[] for t in TARGETS}
    for day in days:
        a=dt.datetime.combine(day,dt.time.min,tzinfo=LOCAL_TZ); b=a+dt.timedelta(days=1)
        grid=pd.date_range(pd.Timestamp(a.astimezone(UTC)),pd.Timestamp(b.astimezone(UTC)),freq='600s',inclusive='both')
        elev=spa(grid)
        for target in TARGETS:
            f=elev-target; found=[]
            for i in range(len(grid)-1):
                if not (np.isfinite(f[i]) and np.isfinite(f[i+1])): continue
                if elev[i+1]>=elev[i]: continue
                if f[i]==0 or f[i+1]==0 or f[i]*f[i+1]<0: found.append(i)
            if len(found)!=1: raise RuntimeError(f'{day} target {target}: expected one dusk bracket, got {len(found)}')
            i=found[0]; left[target].append(grid[i].value); right[target].append(grid[i+1].value); fl[target].append(float(f[i]))
    return {t:(np.asarray(left[t],dtype=np.int64),np.asarray(right[t],dtype=np.int64),np.asarray(fl[t],dtype=float)) for t in TARGETS}

def refine_batch(left_ns,right_ns,f_left,target):
    left=left_ns.copy(); right=right_ns.copy(); fl=f_left.copy()
    for _ in range(45):
        mid=left+(right-left)//2; stuck=(mid==left)|(mid==right)
        if np.all(stuck): break
        fm=spa(pd.DatetimeIndex(mid,tz='UTC'))-target
        in_left=(fl*fm<=0)
        right=np.where(in_left,mid,right); left=np.where(in_left,left,mid); fl=np.where(in_left,fl,fm)
    return left+(right-left)//2

def generate_rows():
    days=date_list(); brackets=coarse_brackets(days); roots={t:refine_batch(*brackets[t],target=t) for t in TARGETS}; rows=[]
    for i,day in enumerate(days):
        t8=pd.Timestamp(int(roots[-8.0][i]),tz='UTC'); t7=pd.Timestamp(int(roots[-7.0][i]),tz='UTC'); t6=pd.Timestamp(int(roots[-6.0][i]),tz='UTC')
        if not (t6<t7<t8): raise RuntimeError(f'bad dusk order {day}')
        rows.append({'case_id':f'{day.isoformat()}_dusk','local_civil_date':day.isoformat(),'event':'dusk',
                     't_minus8_utc':iso(t8),'t_minus7_utc':iso(t7),'t_minus6_utc':iso(t6)})
    if len(rows)!=EXPECTED: raise RuntimeError(f'expected {EXPECTED}, got {len(rows)}')
    return rows

def write_csv(path,rows):
    fields=['case_id','local_civil_date','event','t_minus8_utc','t_minus7_utc','t_minus6_utc']
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def load_reference(path):
    spec=importlib.util.spec_from_file_location('ena_ref',path)
    if spec is None or spec.loader is None: raise RuntimeError('cannot import reference')
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def reference_one(ref,day):
    a=dt.datetime.combine(day,dt.time.min,tzinfo=ref.LOCAL_TZ); b=a+dt.timedelta(days=1)
    grid=pd.date_range(pd.Timestamp(a.astimezone(UTC)),pd.Timestamp(b.astimezone(UTC)),freq='120s',inclusive='both')
    p=pvlib.solarposition.spa_python(grid,latitude=ref.SITE_LAT,longitude=ref.SITE_LON,altitude=ref.SITE_ALT_M,
        pressure=0.0,temperature=12.0,delta_t=None,how='numpy'); elev=np.asarray(p['elevation'],dtype=float); roots={}
    for target in ref.TARGET_ELEVATIONS:
        f=elev-target; found=[]
        for i in range(len(grid)-1):
            if not (np.isfinite(f[i]) and np.isfinite(f[i+1])): continue
            if elev[i+1]>=elev[i]: continue
            if f[i]==0 or f[i+1]==0 or f[i]*f[i+1]<0: found.append(i)
        if len(found)!=1: raise RuntimeError((day,target,len(found)))
        i=found[0]; roots[int(abs(target))]=ref.refine_crossing(grid[i],grid[i+1],target)
    return {'t_minus8_utc':ref.iso_utc(roots[8]),'t_minus7_utc':ref.iso_utc(roots[7]),'t_minus6_utc':ref.iso_utc(roots[6])}

def verify_samples(rows,ref_path):
    ref=load_reference(ref_path); by={r['local_civil_date']:r for r in rows}
    samples=['2017-04-05','2017-10-29','2018-03-25','2018-06-21','2018-12-21','2019-03-31','2019-09-27']; reports=[]; max_us=0.0
    for text in samples:
        old=reference_one(ref,dt.date.fromisoformat(text)); new=by[text]; diffs={}
        for key in ('t_minus8_utc','t_minus7_utc','t_minus6_utc'):
            us=abs((pd.Timestamp(old[key])-pd.Timestamp(new[key])).total_seconds())*1e6; diffs[key]=us; max_us=max(max_us,us)
        reports.append({'date':text,'differences_microseconds':diffs,'reference':old,'vectorized':{k:new[k] for k in old}})
    if max_us>1.0: raise RuntimeError(f'vectorized/reference drift exceeds 1 us: {max_us}')
    return {'sample_count':len(samples),'max_abs_difference_microseconds':max_us,'samples':reports}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--reference-script',type=Path); a=ap.parse_args()
    rows=generate_rows(); a.output.parent.mkdir(parents=True,exist_ok=True); write_csv(a.output,rows); raw=a.output.read_bytes()
    result={'count':len(rows),'sha256':hashlib.sha256(raw).hexdigest(),'first':rows[0],'last':rows[-1]}
    if a.reference_script: result['reference_check']=verify_samples(rows,a.reference_script.resolve())
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()
