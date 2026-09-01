#!/usr/bin/env python3
"""Staged ARM Live atmospheric runner for the exact ENA/SWS V1 live25.

Order: E2 -> MFRSR side of E4 -> E5 -> E3. E7 is already passed by construction;
E0 is supplied by the separate holdout-safe streamer. E6 remains a separately
frozen surface-schema gate and is never silently promoted here.

Raw native atmospheric files are temporary. No SWS photometric value is read.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,json,os,re,tempfile,urllib.parse,urllib.request
from pathlib import Path
from typing import Any
import ena_native_gate_core_v1 as G

BASE='https://adc.arm.gov/armlive'
DS={
 'arscl':['enaarsclkazr1kolliasC1.c1','enaarsclkazr1kolliasC1.c0'],
 'ceil':['enaceilC1.b1'],
 'raman':['enarlprofbeC1.c1','enarlproffex1thorC1.c0'],
 'mfrsr':['enamfrsr7nchaod1michC1.c1','enamfrsr7nchaod1michC1.c0','enamfrsraod1michC1.c1','enamfrsraod1michC1.c0'],
 'sonde':['enasondewnpnC1.b1'],
}

def sha256_file(p: Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()

def arm_json(pair,ds,start,end):
 q=urllib.parse.urlencode({'user':pair,'ds':ds,'start':start,'end':end,'wt':'json'})
 req=urllib.request.Request(BASE+'/query?'+q,headers={'User-Agent':'arm-ena-sws-v1-native-live25/1'})
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

def nextday(day):
 d=dt.date.fromisoformat(day)+dt.timedelta(days=1); return d.isoformat()

def query_day(pair,ds,day):
 obj=arm_json(pair,ds,day,nextday(day)); pat=re.compile(r'^'+re.escape(ds)+r'\.(\d{8})\.',re.I); ymd=day.replace('-','')
 return [n for n in walk_names(obj) if (m:=pat.match(n)) and m.group(1)==ymd]

def download(pair,name,p):
 q=urllib.parse.urlencode({'user':pair,'file':name}); req=urllib.request.Request(BASE+'/saveData?'+q,headers={'User-Agent':'arm-ena-sws-v1-native-live25/1'})
 with urllib.request.urlopen(req,timeout=600) as r,p.open('wb') as f:
  while True:
   b=r.read(8*1024*1024)
   if not b: break
   f.write(b)

def discover(pair,candidates,days):
 errors=[]
 for ds in candidates:
  names=[]; ok=True
  for day in days:
   try: names.extend(query_day(pair,ds,day))
   except Exception as e: errors.append(f'{ds}:{day}:{type(e).__name__}'); ok=False
  names=sorted(set(names))
  if ok and names: return ds,names,errors
  if not ok: return None,[],errors
 return None,[],errors

def aggregate_cloud(reports,key_clear,key_pos):
 if any(bool(r.get(key_pos)) for r in reports): return {'positive':True,'clear':False}
 if any(bool(r.get(key_clear)) for r in reports): return {'positive':False,'clear':True}
 return {'positive':False,'clear':False}

def e0_pass_set(path: Path|None):
 if path is None or not path.exists(): return None
 with path.open(encoding='utf-8') as f:
  rows=list(csv.DictReader(f))
 return {r['case_id'] for r in rows if r.get('disposition')=='E0_PASS_BLIND_CANDIDATE'}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--windows',type=Path,required=True); ap.add_argument('--live25',type=Path,required=True); ap.add_argument('--e0-ledger',type=Path,default=None); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args()
 a.output_dir.mkdir(parents=True,exist_ok=True)
 with a.windows.open(encoding='utf-8') as f: windows={r['case_id']:r for r in csv.DictReader(f)}
 live=json.loads(a.live25.read_text(encoding='utf-8')); cases=live['cases']; assert len(cases)==25
 uid=os.environ.get('ARM_USER_ID','').strip(); token=os.environ.get('ARM_ACCESS_TOKEN','').strip(); creds=bool(uid and token)
 required={cid:{'e2_e3_dates':windows[cid]['e2_e3_utc_dates'].split(';'),'e4_dates':windows[cid]['e4_e6_utc_dates'].split(';'),'e5_dates':windows[cid]['e5_sonde_utc_dates'].split(';')} for cid in [x['case_id'] for x in cases]}
 receipt={'schema':1,'case_count':25,'credentials_present':creds,'science_result_produced':False,'datastream_candidates':DS,'required_dates_by_case':required,'live25_sha256':sha256_file(a.live25),'windows_sha256':sha256_file(a.windows),'protected_sws_values_opened':False,'stage_b_authorized':False}
 if not creds:
  receipt['status']='AUTH_REQUIRED_NO_SCIENCE_RESULT'; (a.output_dir/'ena_native_live25_auth_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0
 pair=uid+':'+token; e0pass=e0_pass_set(a.e0_ledger)
 if e0pass is None: raise SystemExit('credentials present but E0 ledger absent; run holdout-safe E0 first')
 ledger=[]; provenance=[]
 for item in cases:
  cid=item['case_id']; w=windows[cid]; row={'case_id':cid,'e7':'PASS_EXACT_TIME_TOTAL_COLUMN_RETRIEVED','e0':('PASS' if cid in e0pass else 'FAIL_OR_MISSING'),'protected_sws_values_opened':False}
  if cid not in e0pass:
   row['terminal']='E0_NOT_PASS'; ledger.append(row); continue
  start=G.parse_iso(w['e2_e3_guard_start_utc']); end=G.parse_iso(w['e2_e3_guard_end_utc']); days=required[cid]['e2_e3_dates']
  with tempfile.TemporaryDirectory(prefix='ena_native25_') as td:
   root=Path(td); source=[]
   # E2 mandatory streams
   reports={}
   for fam,fn in [('arscl',G.analyze_arscl),('ceil',G.analyze_ceil),('raman',G.analyze_raman)]:
    ds,names,errs=discover(pair,DS[fam],days); famreps=[]
    if errs and not names: reports[fam]={'discovery_errors':errs,'reports':[]}; continue
    for name in names:
     p=root/name; download(pair,name,p); source.append({'family':fam,'datastream':ds,'filename':name,'size_bytes':p.stat().st_size,'sha256':sha256_file(p)})
     try: famreps.append(fn(p,start,end))
     except Exception as e: famreps.append({'source_file':name,'error':f'{type(e).__name__}:{e}'})
    reports[fam]={'datastream':ds,'reports':famreps}
   ar=aggregate_cloud(reports.get('arscl',{}).get('reports',[]),'clear_evidence','positive')
   ce=aggregate_cloud(reports.get('ceil',{}).get('reports',[]),'clear_evidence','positive')
   rr=aggregate_cloud(reports.get('raman',{}).get('reports',[]),'cloud_clear_evidence','cloud_positive')
   if ar['positive'] or ce['positive'] or rr['positive']: e2='CLOUD_OR_HYDROMETEOR_PRESENT'
   elif ar['clear'] and ce['clear'] and rr['clear']: e2='CLEAR_MULTI_SENSOR'
   else: e2='CLEAR_EVIDENCE_INSUFFICIENT'
   row['e2']=e2; row['e2_sources']={k:{'datastream':v.get('datastream'),'reports':v.get('reports',[])} for k,v in reports.items()}
   if e2!='CLEAR_MULTI_SENSOR': row['terminal']='E2_'+e2; provenance.append({'case_id':cid,'sources':source}); ledger.append(row); continue
   # E4 MFRSR completion
   ds,names,errs=discover(pair,DS['mfrsr'],required[cid]['e4_dates']); mreps=[]
   for name in names:
    p=root/name
    if not p.exists(): download(pair,name,p); source.append({'family':'mfrsr','datastream':ds,'filename':name,'size_bytes':p.stat().st_size,'sha256':sha256_file(p)})
    try: mreps.append(G.analyze_mfrsr(p,G.parse_iso(w['e4_e6_daylight_start_utc']),G.parse_iso(w['e4_e6_daylight_end_utc']),float(item['aeronet_median_aod500'])))
    except Exception as e: mreps.append({'source_file':name,'pass':False,'reason':f'ERROR:{type(e).__name__}:{e}'})
   passing=[x for x in mreps if x.get('pass')]
   row['e4_mfrsr']={'datastream':ds,'reports':mreps,'discovery_errors':errs}
   if not passing: row['terminal']='E4_MFRSR_FAIL_OR_MISSING'; provenance.append({'case_id':cid,'sources':source}); ledger.append(row); continue
   row['e4']='PASS_BOTH_SOURCES'
   # E5 two-sided raw sonde
   ds,names,errs=discover(pair,DS['sonde'],required[cid]['e5_dates']); sreps=[]
   for name in names:
    p=root/name
    if not p.exists(): download(pair,name,p); source.append({'family':'sonde','datastream':ds,'filename':name,'size_bytes':p.stat().st_size,'sha256':sha256_file(p)})
    try: sreps.append(G.analyze_sonde(p))
    except Exception as e: sreps.append({'source_file':name,'usable':False,'reason':f'ERROR:{type(e).__name__}:{e}'})
   pairrep=G.choose_sonde_pair(sreps,G.parse_iso(w['e5_reference_utc']),6.0); row['e5']=pairrep
   if not pairrep.get('pass'): row['terminal']='E5_NO_TWO_SIDED_SUPPORT'; provenance.append({'case_id':cid,'sources':source}); ledger.append(row); continue
   # E3 Raman profile from the same cloud-vetted Raman file(s)
   rreps=reports.get('raman',{}).get('reports',[]); usable=[x for x in rreps if x.get('e3_profile_usable') and not x.get('cloud_positive')]
   row['e3']='PASS_RETRIEVED_355NM_SHAPE' if usable else 'MISSING_OR_UNRESOLVED_VERTICAL_AEROSOL_SHAPE'
   if not usable: row['terminal']='E3_PROFILE_MISSING'; provenance.append({'case_id':cid,'sources':source}); ledger.append(row); continue
   row['terminal']='E0_E2_E3_E4_E5_E7_PASS__E6_PENDING'; provenance.append({'case_id':cid,'sources':source}); ledger.append(row)
  # temp dir deleted here
 fields=[]
 for r in ledger:
  flat={k:(json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v) for k,v in r.items()}; r.clear(); r.update(flat)
  for k in r:
   if k not in fields: fields.append(k)
 with (a.output_dir/'ena_native_live25_gate_ledger.csv').open('w',encoding='utf-8',newline='') as f:
  wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader(); wr.writerows(ledger)
 with (a.output_dir/'ena_native_live25_provenance.jsonl').open('w',encoding='utf-8') as f:
  for x in provenance: f.write(json.dumps(x,sort_keys=True)+'\n')
 counts={}
 for r in ledger: counts[r['terminal']]=counts.get(r['terminal'],0)+1
 receipt.update({'status':'NATIVE_GATES_E2_E4_E5_E3_COMPLETE_E6_PENDING','science_result_produced':True,'terminal_counts':counts,'e6_pending_count':counts.get('E0_E2_E3_E4_E5_E7_PASS__E6_PENDING',0)})
 (a.output_dir/'ena_native_live25_summary.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n'); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
