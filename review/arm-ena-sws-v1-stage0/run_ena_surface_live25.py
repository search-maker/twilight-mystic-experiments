#!/usr/bin/env python3
"""Credential-safe result-blind E6 runner for ENA/SWS V1 live25.

Runs only after E0/E2/E3/E4/E5/E7 pass. It never queries or opens SWS.
Raw surface NetCDF/CDF files are temporary; provenance hashes are retained.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,os,re,tempfile,urllib.parse,urllib.request
from pathlib import Path
from typing import Any
import ena_surface_gate_v1 as E6

BASE='https://adc.arm.gov/armlive'
DS={
 'mfr':['enamfr10mC1.b1'],
 'mfrsr':['enamfrsrC1.b1'],
 'gnd':['enagndrad60sC1.b1'],
 'sky':['enaskyrad60sC1.b1'],
 'sebs':['enasebsC1.b1'],
}
UPSTREAM='E0_E2_E3_E4_E5_E7_PASS__E6_PENDING'

def sha256_file(p: Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()

def arm_json(pair,ds,start,end):
 if 'sws' in ds.lower(): raise RuntimeError('SWS_FORBIDDEN_IN_E6')
 q=urllib.parse.urlencode({'user':pair,'ds':ds,'start':start,'end':end,'wt':'json'})
 req=urllib.request.Request(BASE+'/query?'+q,headers={'User-Agent':'arm-ena-sws-v1-e6-live25/1'})
 with urllib.request.urlopen(req,timeout=120) as r: return json.loads(r.read().decode('utf-8'))

def walk_names(x):
 out=[]
 def w(v):
  if isinstance(v,dict):
   for z in v.values(): w(z)
  elif isinstance(v,list):
   for z in v: w(z)
  elif isinstance(v,str):
   n=os.path.basename(v)
   if n.lower().endswith(('.nc','.cdf')): out.append(n)
 w(x); return sorted(set(out))

def nextday(day): return (dt.date.fromisoformat(day)+dt.timedelta(days=1)).isoformat()

def query_day(pair,ds,day):
 obj=arm_json(pair,ds,day,nextday(day)); pat=re.compile(r'^'+re.escape(ds)+r'\.(\d{8})\.',re.I); ymd=day.replace('-','')
 return [n for n in walk_names(obj) if (m:=pat.match(n)) and m.group(1)==ymd and 'sws' not in n.lower()]

def download(pair,name,p):
 if 'sws' in name.lower(): raise RuntimeError('SWS_FORBIDDEN_IN_E6')
 q=urllib.parse.urlencode({'user':pair,'file':name}); req=urllib.request.Request(BASE+'/saveData?'+q,headers={'User-Agent':'arm-ena-sws-v1-e6-live25/1'})
 with urllib.request.urlopen(req,timeout=600) as r,p.open('wb') as f:
  while True:
   b=r.read(8*1024*1024)
   if not b: break
   f.write(b)

def discover(pair,ds,days):
 names=[]; errors=[]
 for day in days:
  try: names.extend(query_day(pair,ds,day))
  except Exception as e: errors.append({'datastream':ds,'date':day,'error_type':type(e).__name__})
 return sorted(set(names)),errors

def upstream_pass(path: Path)->set[str]:
 with path.open(encoding='utf-8') as f: rows=list(csv.DictReader(f))
 return {r['case_id'] for r in rows if r.get('terminal')==UPSTREAM}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--windows',type=Path,required=True); ap.add_argument('--live25',type=Path,required=True); ap.add_argument('--native-ledger',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args()
 a.output_dir.mkdir(parents=True,exist_ok=True)
 with a.windows.open(encoding='utf-8') as f: windows={r['case_id']:r for r in csv.DictReader(f)}
 live=json.loads(a.live25.read_text(encoding='utf-8')); cases=live['cases']; assert len(cases)==25
 eligible=upstream_pass(a.native_ledger)
 uid=os.environ.get('ARM_USER_ID','').strip(); token=os.environ.get('ARM_ACCESS_TOKEN','').strip(); creds=bool(uid and token)
 receipt={'schema':1,'control_comments':['5488714659','5488750527'],'case_count':25,'upstream_e6_pending_count':len(eligible),'credentials_present':creds,'science_result_produced':False,
          'datastreams':DS,'windows_sha256':sha256_file(a.windows),'live25_sha256':sha256_file(a.live25),'native_ledger_sha256':sha256_file(a.native_ledger),
          'sws_queried':False,'sws_downloaded':False,'protected_sws_values_opened':False,'stage_b_authorized':False}
 if not creds:
  receipt['status']='AUTH_REQUIRED_NO_SCIENCE_RESULT'; (a.output_dir/'ena_surface_live25_auth_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0
 if not eligible:
  receipt['status']='NO_UPSTREAM_E6_PENDING_CASES'; receipt['science_result_produced']=True; (a.output_dir/'ena_surface_live25_summary.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0
 pair=uid+':'+token; ledger=[]; provenance=[]
 for item in cases:
  cid=item['case_id']; row={'case_id':cid,'upstream_state':UPSTREAM if cid in eligible else 'NOT_E6_ELIGIBLE','protected_sws_values_opened':False}
  if cid not in eligible: row['e6']='NOT_RUN_UPSTREAM_INELIGIBLE'; ledger.append(row); continue
  w=windows[cid]; days=[x for x in w['e4_e6_utc_dates'].split(';') if x]; start=E6.parse_iso(w['e4_e6_daylight_start_utc']) if hasattr(E6,'parse_iso') else dt.datetime.fromisoformat(w['e4_e6_daylight_start_utc'].replace('Z','+00:00')).timestamp(); end=E6.parse_iso(w['e4_e6_daylight_end_utc']) if hasattr(E6,'parse_iso') else dt.datetime.fromisoformat(w['e4_e6_daylight_end_utc'].replace('Z','+00:00')).timestamp()
  with tempfile.TemporaryDirectory(prefix='ena_e6_') as td:
   root=Path(td); paths={k:[] for k in DS}; source=[]; discovery=[]
   for fam,dstreams in DS.items():
    for ds in dstreams:
     names,errs=discover(pair,ds,days); discovery.extend(errs)
     for name in names:
      p=root/name
      try:
       download(pair,name,p); paths[fam].append(p); source.append({'family':fam,'datastream':ds,'filename':name,'size_bytes':p.stat().st_size,'sha256':sha256_file(p)})
      except Exception as e: discovery.append({'datastream':ds,'filename':name,'error_type':type(e).__name__})
   try: result=E6.evaluate_surface_gate(paths['mfr'],paths['mfrsr'],paths['gnd'],paths['sky'],paths['sebs'],start,end)
   except Exception as e: result={'pass':False,'disposition':'E6_ANALYSIS_ERROR_FAIL_CLOSED','error_type':type(e).__name__,'sws_values_opened':False,'stage_b_authorized':False}
   row['e6']=result.get('disposition'); row['e6_result']=result; row['discovery_errors']=discovery
   provenance.append({'case_id':cid,'sources':source,'source_count':len(source),'sws_queried':False,'sws_downloaded':False})
  ledger.append(row)
 with (a.output_dir/'ena_surface_live25_gate_ledger.jsonl').open('w',encoding='utf-8') as f:
  for r in ledger: f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
 with (a.output_dir/'ena_surface_live25_provenance.jsonl').open('w',encoding='utf-8') as f:
  for r in provenance: f.write(json.dumps(r,sort_keys=True,allow_nan=False)+'\n')
 counts={}
 for r in ledger:
  state=str(r.get('e6')); counts[state]=counts.get(state,0)+1
 receipt.update({'status':'E6_COMPLETE_FOR_UPSTREAM_ELIGIBLE_CASES','science_result_produced':True,'e6_counts':counts,'e6_pass_count':counts.get('PASS_SURFACE_RETRIEVED_WITH_BROADBAND_CORROBORATION',0)})
 (a.output_dir/'ena_surface_live25_summary.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)); return 0
if __name__=='__main__': raise SystemExit(main())
