#!/usr/bin/env python3
"""Evaluate the already-frozen ENA/SWS V1 E4 CSPHOT/AERONET side only.

Control: Issue #60 comment 5488472383. This script reads no SWS data and cannot
promote E4 primary eligibility by itself because independent MFRSR remains mandatory.
It may, however, fail a case if the mandatory AERONET/CSPHOT side itself fails the
predeclared count or stability gates.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, io, json, math
from pathlib import Path
from typing import Any
import numpy as np

CONTROL_COMMENT='5488472383'
EXPECTED_CASES=380
MIN_COUNT=5
MAX_P90_P10=0.015
SITE='ARM_Graciosa'

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def parse_iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(dt.timezone.utc)

def find_header(lines: list[str]) -> int:
    for i,line in enumerate(lines):
        if 'AERONET_Site' in line and 'Date(' in line and 'Time(' in line:
            return i
    raise RuntimeError('AERONET CSV header not found')

def parse_date_time(date_text: str,time_text: str) -> dt.datetime:
    # V3 normally uses dd:mm:yyyy and hh:mm:ss.
    for fmt in ('%d:%m:%Y %H:%M:%S','%d-%m-%Y %H:%M:%S','%Y-%m-%d %H:%M:%S'):
        try: return dt.datetime.strptime(date_text.strip()+' '+time_text.strip(),fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError: pass
    raise ValueError(f'unrecognized AERONET datetime {date_text!r} {time_text!r}')

def load_aeronet(path: Path) -> tuple[list[dict[str,Any]],str,list[str]]:
    raw=path.read_text(encoding='utf-8',errors='replace')
    lines=[x for x in raw.splitlines() if x.strip()]
    idx=find_header(lines)
    reader=csv.DictReader(io.StringIO('\n'.join(lines[idx:])))
    fields=reader.fieldnames or []
    date_col=next((x for x in fields if x.startswith('Date(')),None)
    time_col=next((x for x in fields if x.startswith('Time(')),None)
    site_col=next((x for x in fields if x=='AERONET_Site'),None)
    # Direct-sun AOD column only; never substitute SDA-derived 500 nm.
    aod_col=next((x for x in fields if x.strip().lower() in {'aod_500nm','aod_500_nm'}),None)
    if not date_col or not time_col or not site_col: raise RuntimeError('missing required AERONET identity/time columns')
    if not aod_col: raise RuntimeError('native direct-sun AOD_500nm column is absent; frozen E4 forbids interpolation/substitution')
    rows=[]; sites=set()
    for r in reader:
        sites.add(str(r.get(site_col,'')).strip())
        try:
            t=parse_date_time(str(r[date_col]),str(r[time_col]))
            v=float(str(r[aod_col]).strip())
        except Exception:
            continue
        if not math.isfinite(v) or v<=-900: continue
        rows.append({'time':t,'aod500':v,'site':str(r.get(site_col,'')).strip()})
    bad_sites=sorted(x for x in sites if x and x!=SITE)
    if bad_sites: raise RuntimeError(f'unexpected AERONET site identities: {bad_sites[:5]}')
    return rows,aod_col,fields

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--windows',type=Path,required=True); ap.add_argument('--aeronet',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args()
    with a.windows.open(encoding='utf-8') as f: cases=list(csv.DictReader(f))
    if len(cases)!=EXPECTED_CASES: raise RuntimeError(f'expected {EXPECTED_CASES} windows, got {len(cases)}')
    aer,aod_col,fields=load_aeronet(a.aeronet)
    out=[]; counts={}
    for c in cases:
        lo=parse_iso(c['e4_e6_daylight_start_utc']); hi=parse_iso(c['e4_e6_daylight_end_utc'])
        vals=np.asarray([r['aod500'] for r in aer if r['site']==SITE and lo<=r['time']<=hi],dtype=float)
        n=int(vals.size)
        median=float(np.median(vals)) if n else None
        p10=float(np.percentile(vals,10,method='linear')) if n else None
        p90=float(np.percentile(vals,90,method='linear')) if n else None
        spread=(p90-p10) if n else None
        if n<MIN_COUNT: disposition='FAIL_CSPHOT_MIN_COUNT'
        elif spread is None or spread>MAX_P90_P10: disposition='FAIL_CSPHOT_STABILITY'
        else: disposition='PASS_CSPHOT_SIDE_ONLY_MFRSR_REQUIRED'
        counts[disposition]=counts.get(disposition,0)+1
        out.append({
            'case_id':c['case_id'],'window_start_utc':c['e4_e6_daylight_start_utc'],'window_end_utc':c['e4_e6_daylight_end_utc'],
            'aeronet_site':SITE,'aod_column':aod_col,'valid_count':n,
            'median_aod500':('' if median is None else f'{median:.9f}'),
            'p10_aod500':('' if p10 is None else f'{p10:.9f}'),'p90_aod500':('' if p90 is None else f'{p90:.9f}'),
            'p90_minus_p10':('' if spread is None else f'{spread:.9f}'),'disposition':disposition,
            'e4_primary_pass':False,'mfrsr_still_required':True,'protected_sws_values_opened':False,
        })
    a.output_dir.mkdir(parents=True,exist_ok=True)
    csvp=a.output_dir/'ena_sws_e4_aeronet_side_380.csv'
    with csvp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    summary={
      'schema':1,'control_comment':CONTROL_COMMENT,'case_count':len(out),'aeronet_site':SITE,
      'aeronet_raw_sha256':sha256_file(a.aeronet),'windows_sha256':sha256_file(a.windows),'output_csv_sha256':sha256_file(csvp),
      'aod_column':aod_col,'source_row_count_valid_500nm':len(aer),'disposition_counts':counts,
      'thresholds':{'min_valid_level2_count':MIN_COUNT,'p90_minus_p10_max':MAX_P90_P10,'wavelength_nm':500,'interpolation_allowed':False},
      'semantic_boundary':'CSPHOT/AERONET side only; MFRSR remains mandatory for primary E4; no ranking',
      'e4_primary_cases_promoted':0,'protected_sws_values_opened':False,'stage_b_authorized':False,
    }
    (a.output_dir/'ena_sws_e4_aeronet_side_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
