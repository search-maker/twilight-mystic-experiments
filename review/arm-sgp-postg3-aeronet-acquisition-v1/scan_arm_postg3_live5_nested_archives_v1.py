#!/usr/bin/env python3
"""Result-blind filename/provenance scan for the five still-live ARM SGP cases.

Scans direct files plus members of local ZIP archives. It never opens NetCDF/CDF
payloads and never extracts or reads SASZE science values. Output is a tiny CSV/JSON
inventory showing where required non-radiance gate source files already exist locally.
"""
from __future__ import annotations
import argparse, csv, fnmatch, hashlib, json, os, zipfile
from pathlib import Path

CASES = {
    "2024-01-27_dusk": "20240128",
    "2024-02-01_dusk": "20240202",
    "2024-03-27_dusk": "20240328",
    "2024-03-28_dusk": "20240329",
    "2024-05-31_dusk": "20240601",
}
COMPONENTS = {
    "ARSCL_KAZR": ["sgparsclkazr1kolliasC1.c1*{d}*", "sgparsclkazr1kolliasC1.c0*{d}*"],
    "CEIL": ["sgpceilC1.b1*{d}*"],
    "MPL_FEATURE_SUPPORT": ["sgpmpl*{d}*", "sgp*feature*{d}*"],
    "HSRL": ["sgphsrlC1.a1*{d}*"],
    "RLPROFBE_RAMAN": ["sgprlprofbeC1.c1*{d}*"],
    "MFRSR_AOD": ["sgpmfrsr7nchaod1michC1.c1*{d}*"],
    "CSPHOT": ["sgpcsphotaodfiltqav3C1.a1*{d}*"],
    "SONDE": ["sgpsondewnpnC1.b1*{d}*"],
    "MFR_UP": ["sgpmfr10mC1.b1*{d}*"],
    "MFRSR_DOWN": ["sgpmfrsrC1.b1*{d}*"],
    "QCRAD_C2": ["sgpqcrad1longC1.c2*{d}*", "sgpqcrad* C1.c2*{d}*"],
    "GECOMI_OZONE": ["gecomi*{d}*", "*omi*{d}*"],
}

def dates_around(s: str):
    from datetime import datetime, timedelta
    d=datetime.strptime(s,"%Y%m%d")
    return [(d+timedelta(days=k)).strftime("%Y%m%d") for k in (-1,0,1)]

def sha256_file(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def matches(name: str, patterns):
    b=os.path.basename(name).lower()
    return any(fnmatch.fnmatch(b,p.lower()) for p in patterns)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--out',default='ARM_SGP_POSTG3_LIVE5_NESTED_ARCHIVE_SCAN_V1')
    args=ap.parse_args(); root=args.root.resolve()
    direct=[]; zips=[]
    for p in root.rglob('*'):
        if not p.is_file(): continue
        if p.suffix.lower() in ('.nc','.cdf'): direct.append(p)
        elif p.suffix.lower()=='.zip': zips.append(p)
    requirements=[]
    for cid,d in CASES.items():
        ds=dates_around(d)
        for comp,tmpl in COMPONENTS.items():
            pats=[t.format(d=x) for x in ds for t in tmpl]
            requirements.append((cid,comp,pats))
    rows=[]
    for cid,comp,pats in requirements:
        for p in direct:
            if matches(p.name,pats):
                rows.append({'case_id':cid,'component':comp,'container_type':'DIRECT','container_path':str(p),'member_name':p.name,'member_size':p.stat().st_size,'container_sha256':'','note':'payload_not_opened'})
    for zp in zips:
        try:
            zsha=sha256_file(zp)
            with zipfile.ZipFile(zp) as z:
                infos=z.infolist()
                for cid,comp,pats in requirements:
                    for i in infos:
                        if i.is_dir(): continue
                        if matches(i.filename,pats):
                            rows.append({'case_id':cid,'component':comp,'container_type':'ZIP_MEMBER','container_path':str(zp),'member_name':i.filename,'member_size':i.file_size,'container_sha256':zsha,'note':'member_payload_not_opened'})
        except Exception as e:
            rows.append({'case_id':'','component':'','container_type':'ZIP_ERROR','container_path':str(zp),'member_name':'','member_size':'','container_sha256':'','note':type(e).__name__+': '+str(e)})
    fields=['case_id','component','container_type','container_path','member_name','member_size','container_sha256','note']
    csvp=Path(args.out+'.csv'); jsp=Path(args.out+'.json')
    with csvp.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    summary={'schema':1,'root':str(root),'direct_netcdf_cdf_count':len(direct),'zip_count':len(zips),'match_rows':len(rows),'cases':{},'holdout_firewall':{'netcdf_payloads_opened':False,'sasze_radiance_opened':False,'zip_member_payloads_opened':False}}
    for cid in CASES:
        summary['cases'][cid]={c:sum(1 for r in rows if r['case_id']==cid and r['component']==c) for c in COMPONENTS}
    jsp.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(csvp); print(jsp)
if __name__=='__main__': main()
