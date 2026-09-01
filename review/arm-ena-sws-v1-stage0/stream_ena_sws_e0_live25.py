#!/usr/bin/env python3
"""Holdout-safe E0 streamer for the exact 25 ENA cases surviving public mandatory gates.

Uses the already-reviewed E0 auditor for every scientific decision. Raw SWS bytes
exist only inside TemporaryDirectory and are deleted before advancing. Protected
photometric values remain unread.
"""
from __future__ import annotations
import argparse,csv,importlib.util,json,os,sys,tempfile
from pathlib import Path
from typing import Any

def load(path: Path,name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot import {path}')
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def append_jsonl(path: Path,obj: dict[str,Any]):
    with path.open('a',encoding='utf-8') as f: f.write(json.dumps(obj,sort_keys=True,allow_nan=False)+'\n')

def main():
    ap=argparse.ArgumentParser(); here=Path(__file__).resolve().parent
    ap.add_argument('--e0-script',type=Path,default=here/'audit_ena_sws_e0.py'); ap.add_argument('--transport-script',type=Path,default=here/'stream_ena_sws_e0_from_arm_live.py')
    ap.add_argument('--windows',type=Path,required=True); ap.add_argument('--live25',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    e0=load(a.e0_script,'ena_e0_safe'); tr=load(a.transport_script,'ena_e0_transport')
    with a.windows.open(encoding='utf-8') as f: windows={r['case_id']:r for r in csv.DictReader(f)}
    live=json.loads(a.live25.read_text(encoding='utf-8')); cases=live['cases']
    if len(cases)!=25 or len({x['case_id'] for x in cases})!=25: raise RuntimeError('live25 identity mismatch')
    uid=os.environ.get('ARM_USER_ID','').strip(); token=os.environ.get('ARM_ACCESS_TOKEN','').strip()
    receipt={'schema':1,'case_count':25,'credentials_present':bool(uid and token),'science_result_produced':False,'protected_variable_values_read':False,'raw_sws_files_retained':False,'stage_b_authorized':False,
             'required_datastream':'enaswsC1.b1','live25_file_sha256':tr.sha256_file(a.live25),'windows_sha256':tr.sha256_file(a.windows)}
    if not uid or not token:
        receipt['status']='AUTH_REQUIRED_NO_SCIENCE_RESULT'; (a.output_dir/'ena_sws_e0_live25_auth_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0
    pair=uid+':'+token; ledger=[]; prov=[]; schemas=[]
    for item in cases:
        cid=item['case_id']; w=windows[cid]
        event=e0.Event(cid,w['local_civil_date'],'dusk',w['t_minus8_utc'],w['t_minus7_utc'],w['t_minus6_utc'])
        names=[]; qerrors=[]
        for day in e0.needed_dates(event):
            try: names.extend(tr.query_day(pair,tr.DATASTREAM,day,tr.FILE_RE))
            except Exception as exc: qerrors.append(f'{day}:{type(exc).__name__}')
        names=sorted(set(names))
        if qerrors:
            ledger.append({**event.__dict__,'disposition':'ARM_LIVE_QUERY_ERROR','read_errors':' | '.join(qerrors),'protected_variable_values_read':False}); continue
        if not names:
            ledger.append({**event.__dict__,'disposition':'SOURCE_FILE_MISSING','read_errors':'','protected_variable_values_read':False}); continue
        with tempfile.TemporaryDirectory(prefix='ena_sws_live25_') as td:
            root=Path(td); src=[]
            try:
                for name in names:
                    p=root/name; tr.download_native(pair,name,p); src.append({'filename':name,'size_bytes':p.stat().st_size,'sha256':tr.sha256_file(p)}); schemas.append(tr.safe_schema_snapshot(e0,p,'sws'))
                idx=e0.index_files(root,e0.SWS_RE); row=tr.row_without_raw_paths(e0.audit(event,root,idx)); row['protected_variable_values_read']=False; row['raw_sws_files_retained']=False; ledger.append(row)
                prov.append({'case_id':cid,'source_files':src,'protected_variable_values_read':False,'raw_sws_files_retained':False})
            except Exception as exc:
                ledger.append({**event.__dict__,'disposition':'STREAM_AUDIT_ERROR','read_errors':f'{type(exc).__name__}:{exc}','protected_variable_values_read':False,'raw_sws_files_retained':False})
    fields=[]
    for r in ledger:
        for k in r:
            if k not in fields: fields.append(k)
    with (a.output_dir/'ena_sws_e0_live25_ledger.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(ledger)
    with (a.output_dir/'ena_sws_e0_live25_provenance.jsonl').open('w',encoding='utf-8') as f:
        for x in prov: f.write(json.dumps(x,sort_keys=True)+'\n')
    with (a.output_dir/'ena_sws_e0_live25_schema.jsonl').open('w',encoding='utf-8') as f:
        for x in schemas: f.write(json.dumps(x,sort_keys=True)+'\n')
    counts={}
    for r in ledger: counts[r['disposition']]=counts.get(r['disposition'],0)+1
    receipt.update({'status':'E0_COMPLETE','science_result_produced':True,'processed_case_count':len(ledger),'disposition_counts':counts,'primary_e0_pass_count':counts.get('E0_PASS_BLIND_CANDIDATE',0)})
    (a.output_dir/'ena_sws_e0_live25_summary.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
