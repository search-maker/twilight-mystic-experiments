#!/usr/bin/env python3
"""Evaluate frozen ENA/SWS V1 E7 using exact-time TEMIS/KNMI OMI overpasses.

Control: Issue #60 comment 5488602564. This script reads no SWS data.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json, math, re
from pathlib import Path
from typing import Any

UTC=dt.timezone.utc
CONTROL_COMMENT='5488602564'
EXPECTED=37
MAX_HOURS=12.0
MAX_DISTANCE_KM=100.0

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def parse_iso(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)

def fnum(s: str) -> float:
    return float(s.replace('D','E').replace('d','e'))

def numeric_tokens(line: str) -> list[str]:
    return re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?',line)

def parse_temis(path: Path) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    """Parse documented TEMIS OMI overpass order, allowing common date/time layouts.

    Documented fields after date/time: lat, lon, distance_km, sza_deg, ozone_DU,
    ozone_error_DU, slant_0p1DU, cloud_fraction, cloud_top_pressure_hPa,
    pixel_row, InstrumentConfigurationId.
    """
    rows=[]; rejects=0; data_lines=0
    for line_no,line in enumerate(path.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        s=line.strip()
        if not s or s.startswith(('#','!','%',';')): continue
        toks=numeric_tokens(s)
        if len(toks)<12: continue
        data_lines+=1
        parsed=None
        # Layout A: YYYY MM DD HH MM SS ...
        try:
            y,m,d,hh,mm,ss=[int(float(toks[i])) for i in range(6)]
            if 1990<=y<=2100 and 1<=m<=12 and 1<=d<=31 and 0<=hh<=23 and 0<=mm<=59 and 0<=ss<=60:
                t=dt.datetime(y,m,d,hh,mm,min(ss,59),tzinfo=UTC)
                rest=toks[6:]
                if len(rest)>=10: parsed=(t,rest)
        except Exception: pass
        # Layout B: YYYYMMDD HHMMSS ...
        if parsed is None:
            try:
                ds=str(int(float(toks[0]))); ts=str(int(float(toks[1]))).zfill(6)
                if len(ds)==8 and ds.startswith(('19','20')):
                    t=dt.datetime.strptime(ds+ts,'%Y%m%d%H%M%S').replace(tzinfo=UTC)
                    rest=toks[2:]
                    if len(rest)>=10: parsed=(t,rest)
            except Exception: pass
        # Layout C: YYYY DOY fractional_hour ... (rare fallback)
        if parsed is None:
            try:
                y=int(float(toks[0])); doy=int(float(toks[1])); hour=fnum(toks[2])
                if 1990<=y<=2100 and 1<=doy<=366 and 0<=hour<24:
                    t=dt.datetime(y,1,1,tzinfo=UTC)+dt.timedelta(days=doy-1,hours=hour)
                    rest=toks[3:]
                    if len(rest)>=10: parsed=(t,rest)
            except Exception: pass
        if parsed is None:
            rejects+=1; continue
        t,rest=parsed
        try:
            lat,lon,dist,sza,ozone,err=[fnum(x) for x in rest[:6]]
            slant=fnum(rest[6]) if len(rest)>6 else math.nan
            cloud=fnum(rest[7]) if len(rest)>7 else math.nan
            ctp=fnum(rest[8]) if len(rest)>8 else math.nan
            pixel=fnum(rest[9]) if len(rest)>9 else math.nan
            config=fnum(rest[10]) if len(rest)>10 else math.nan
        except Exception:
            rejects+=1; continue
        valid=(math.isfinite(lat) and math.isfinite(lon) and math.isfinite(dist) and 0<=dist<MAX_DISTANCE_KM
               and math.isfinite(ozone) and ozone>0 and math.isfinite(err) and err>=0)
        rows.append({'file_order':len(rows),'line_no':line_no,'time':t,'lat':lat,'lon':lon,'distance_km':dist,
                     'sza_deg':sza,'ozone_du':ozone,'ozone_error_du':err,'slant_0p1du':slant,
                     'cloud_fraction':cloud,'cloud_top_pressure_hpa':ctp,'pixel_row':pixel,'instrument_configuration_id':config,
                     'valid':valid})
    meta={'parsed_rows':len(rows),'candidate_data_lines':data_lines,'rejected_data_lines':rejects,
          'valid_rows':sum(bool(r['valid']) for r in rows)}
    if not rows: raise RuntimeError(f'no TEMIS OMI overpass rows parsed; meta={meta}')
    return rows,meta

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--windows',type=Path,required=True); ap.add_argument('--survivors',type=Path,required=True)
    ap.add_argument('--temis',type=Path,required=True); ap.add_argument('--source-url',required=True); ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args()
    with a.windows.open(encoding='utf-8') as f: all_windows={r['case_id']:r for r in csv.DictReader(f)}
    sobj=json.loads(a.survivors.read_text(encoding='utf-8'))
    case_ids=[x['case_id'] for x in sobj['survivors']]
    if len(case_ids)!=EXPECTED or len(set(case_ids))!=EXPECTED: raise RuntimeError('37-survivor identity mismatch')
    temis,parse_meta=parse_temis(a.temis)
    out=[]; counts={}
    for cid in case_ids:
        w=all_windows[cid]; ref=parse_iso(w['e7_reference_utc'])
        candidates=[]
        for r in temis:
            if not r['valid']: continue
            off=abs((r['time']-ref).total_seconds())/3600.0
            if off<=MAX_HOURS:
                candidates.append((off,r['distance_km'],r['time'],r['file_order'],r))
        if not candidates:
            disp='MISSING_EXACT_TIME_TOTAL_COLUMN'; selected=None
        else:
            candidates.sort(key=lambda x:(x[0],x[1],x[2],x[3])); selected=candidates[0][4]; disp='PASS_EXACT_TIME_TOTAL_COLUMN_RETRIEVED'
        counts[disp]=counts.get(disp,0)+1
        row={'case_id':cid,'t7_utc':w['e7_reference_utc'],'window_start_utc':w['e7_ozone_window_start_utc'],'window_end_utc':w['e7_ozone_window_end_utc'],
             'disposition':disp,'ozone_column_label':('RETRIEVED' if selected else 'MISSING'),'vertical_profile_shape_label':('ASSUMED' if selected else 'MISSING'),
             'protected_sws_values_opened':False}
        if selected:
            row.update({'omi_time_utc':selected['time'].isoformat().replace('+00:00','Z'),
                        'abs_time_offset_hours':f"{abs((selected['time']-ref).total_seconds())/3600.0:.6f}",
                        'pixel_lat':f"{selected['lat']:.6f}",'pixel_lon':f"{selected['lon']:.6f}",'distance_km':f"{selected['distance_km']:.3f}",
                        'ozone_du':f"{selected['ozone_du']:.6f}",'ozone_error_du':f"{selected['ozone_error_du']:.6f}",
                        'cloud_fraction_diagnostic':('' if not math.isfinite(selected['cloud_fraction']) else f"{selected['cloud_fraction']:.6f}"),
                        'pixel_row':('' if not math.isfinite(selected['pixel_row']) else f"{selected['pixel_row']:.0f}"),
                        'instrument_configuration_id':('' if not math.isfinite(selected['instrument_configuration_id']) else f"{selected['instrument_configuration_id']:.0f}")})
        else:
            row.update({'omi_time_utc':'','abs_time_offset_hours':'','pixel_lat':'','pixel_lon':'','distance_km':'','ozone_du':'','ozone_error_du':'',
                        'cloud_fraction_diagnostic':'','pixel_row':'','instrument_configuration_id':''})
        out.append(row)
    a.output_dir.mkdir(parents=True,exist_ok=True); csvp=a.output_dir/'ena_sws_e7_temis_omi_37.csv'
    fields=list(out[0]);
    with csvp.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
    summary={'schema':1,'control_comment':CONTROL_COMMENT,'case_count':len(out),'source_url':a.source_url,'raw_sha256':sha256_file(a.temis),
             'windows_sha256':sha256_file(a.windows),'survivors_sha256':sha256_file(a.survivors),'output_csv_sha256':sha256_file(csvp),
             'parse_meta':parse_meta,'disposition_counts':counts,'selection_rule':'min abs time offset, then distance, timestamp, file order',
             'max_abs_time_hours':MAX_HOURS,'max_station_distance_km_exclusive':MAX_DISTANCE_KM,
             'protected_sws_values_opened':False,'stage_b_authorized':False}
    (a.output_dir/'ena_sws_e7_temis_omi_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
