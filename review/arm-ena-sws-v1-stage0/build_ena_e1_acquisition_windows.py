#!/usr/bin/env python3
"""Build deterministic result-blind E2-E7 acquisition windows for the 380 ENA E1 survivors.

Control: Issue #60 comment 5488472383.
No atmospheric or SWS values are read. Solar crossings use the same NREL SPA/pvlib
geometric, unrefracted convention as ENA E0. The survivor set is reconstructed only
from the already-frozen contiguous PASS ranges JSON. Crossing refinement is vectorized
across all 380 dates; this changes runtime only, not physics or gate semantics.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pvlib

UTC=dt.timezone.utc
LOCAL_TZ=ZoneInfo('Atlantic/Azores')
SITE_LAT=39.0916; SITE_LON=-28.0257; SITE_ALT_M=30.0
TARGETS=(-12.0,-8.0,-7.0,-6.0)
EXPECTED=380
CONTROL_COMMENT='5488472383'

def spa(index):
    r=pvlib.solarposition.spa_python(index,latitude=SITE_LAT,longitude=SITE_LON,
        altitude=SITE_ALT_M,pressure=0.0,temperature=12.0,delta_t=None,how='numpy')
    return np.asarray(r['elevation'],dtype=float)

def iso(ts):
    return ts.to_pydatetime().astimezone(UTC).isoformat(timespec='microseconds').replace('+00:00','Z')

def survivor_days(obj):
    out=[]
    for r in obj['ranges']:
        a=dt.date.fromisoformat(r['start']); b=dt.date.fromisoformat(r['end']); d=a; n=0
        while d<=b: out.append(d); n+=1; d+=dt.timedelta(days=1)
        if n!=int(r['count']): raise RuntimeError(f'range count mismatch {r}')
    if len(out)!=EXPECTED or len(set(out))!=EXPECTED: raise RuntimeError(f'expected {EXPECTED} unique days, got {len(out)}')
    excluded=str(obj.get('excluded_margin_case','')).removesuffix('_dusk')
    if excluded in {d.isoformat() for d in out}: raise RuntimeError('numerical-margin excluded case leaked into survivors')
    return out

def coarse_brackets(days):
    left={t:[] for t in TARGETS}; right={t:[] for t in TARGETS}; fl={t:[] for t in TARGETS}
    for day in days:
        a=dt.datetime.combine(day,dt.time.min,tzinfo=LOCAL_TZ); b=a+dt.timedelta(days=1)
        grid=pd.date_range(pd.Timestamp(a.astimezone(UTC)),pd.Timestamp(b.astimezone(UTC)),freq='600s',inclusive='both')
        elev=spa(grid)
        for target in TARGETS:
            f=elev-target; hits=[]
            for i in range(len(grid)-1):
                if not (np.isfinite(f[i]) and np.isfinite(f[i+1])): continue
                if elev[i+1]>=elev[i]: continue
                if f[i]==0 or f[i+1]==0 or f[i]*f[i+1]<0: hits.append(i)
            if len(hits)!=1: raise RuntimeError(f'{day} {target}: expected one dusk bracket, got {len(hits)}')
            i=hits[0]; left[target].append(grid[i].value); right[target].append(grid[i+1].value); fl[target].append(float(f[i]))
    return {t:(np.asarray(left[t],dtype=np.int64),np.asarray(right[t],dtype=np.int64),np.asarray(fl[t],dtype=float)) for t in TARGETS}

def refine_batch(left_ns,right_ns,f_left,target):
    left=left_ns.copy(); right=right_ns.copy(); fl=f_left.copy()
    for _ in range(45):
        mid=left+(right-left)//2
        stuck=(mid==left)|(mid==right)
        if np.all(stuck): break
        fm=spa(pd.DatetimeIndex(mid,tz='UTC'))-target
        in_left=(fl*fm<=0)
        right=np.where(in_left,mid,right)
        left=np.where(in_left,left,mid)
        fl=np.where(in_left,fl,fm)
    return left+(right-left)//2

def roots_for_days(days):
    brackets=coarse_brackets(days)
    return {t:refine_batch(*brackets[t],target=t) for t in TARGETS}

def utc_dates(a,b):
    x=a.date(); y=b.date(); out=[]
    while x<=y: out.append(x.isoformat()); x+=dt.timedelta(days=1)
    return ';'.join(out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--ranges',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args()
    src=a.ranges.read_bytes(); obj=json.loads(src); days=survivor_days(obj); roots=roots_for_days(days); rows=[]
    for i,day in enumerate(days):
        t12=pd.Timestamp(int(roots[-12.0][i]),tz='UTC'); t8=pd.Timestamp(int(roots[-8.0][i]),tz='UTC')
        t7=pd.Timestamp(int(roots[-7.0][i]),tz='UTC'); t6=pd.Timestamp(int(roots[-6.0][i]),tz='UTC')
        if not (t6<t7<t8<t12): raise RuntimeError(f'bad dusk order {day}')
        e2a=t6-pd.Timedelta(seconds=600); e2b=t12+pd.Timedelta(seconds=600)
        e4a=t6-pd.Timedelta(hours=3); e4b=t6
        e5a=t7-pd.Timedelta(hours=6); e5b=t7+pd.Timedelta(hours=6)
        e7a=t7-pd.Timedelta(hours=12); e7b=t7+pd.Timedelta(hours=12)
        rows.append({
          'case_id':f'{day.isoformat()}_dusk','local_civil_date':day.isoformat(),
          't_minus6_utc':iso(t6),'t_minus7_utc':iso(t7),'t_minus8_utc':iso(t8),'t_minus12_utc':iso(t12),
          'e2_e3_guard_start_utc':iso(e2a),'e2_e3_guard_end_utc':iso(e2b),
          'e4_e6_daylight_start_utc':iso(e4a),'e4_e6_daylight_end_utc':iso(e4b),
          'e5_sonde_window_start_utc':iso(e5a),'e5_reference_utc':iso(t7),'e5_sonde_window_end_utc':iso(e5b),
          'e7_ozone_window_start_utc':iso(e7a),'e7_reference_utc':iso(t7),'e7_ozone_window_end_utc':iso(e7b),
          'e0_sws_utc_dates':utc_dates(t6-pd.Timedelta(seconds=31),t8+pd.Timedelta(seconds=31)),
          'e2_e3_utc_dates':utc_dates(e2a,e2b),'e4_e6_utc_dates':utc_dates(e4a,e4b),
          'e5_sonde_utc_dates':utc_dates(e5a,e5b),'e7_ozone_utc_dates':utc_dates(e7a,e7b),
        })
    a.output_dir.mkdir(parents=True,exist_ok=True)
    csvp=a.output_dir/'ena_sws_e1_380_acquisition_windows.csv'
    with csvp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    gates={k:sorted({d for row in rows for d in row[k].split(';')}) for k in
           ['e0_sws_utc_dates','e2_e3_utc_dates','e4_e6_utc_dates','e5_sonde_utc_dates','e7_ozone_utc_dates']}
    summary={
      'schema':2,'control_comment':CONTROL_COMMENT,'survivor_count':len(rows),
      'source_ranges_sha256':hashlib.sha256(src).hexdigest(),'csv_sha256':hashlib.sha256(csvp.read_bytes()).hexdigest(),
      'first_case':rows[0]['case_id'],'last_case':rows[-1]['case_id'],
      'unique_utc_day_counts':{k:len(v) for k,v in gates.items()},'unique_utc_days':gates,
      'geometry_method':'pvlib.solarposition.spa_python pressure=0 vectorized refinement; same frozen ENA E0 convention',
      'protected_sws_values_opened':False,'atmospheric_values_opened':False,'stage_b_authorized':False,
    }
    (a.output_dir/'ena_sws_e1_380_acquisition_windows_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__': main()
