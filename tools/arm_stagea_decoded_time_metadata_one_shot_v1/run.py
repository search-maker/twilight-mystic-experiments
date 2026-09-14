#!/usr/bin/env python3
"""Fail-closed Stage-A decoded-time metadata one-shot.

Install/self-test is non-science. Future extraction requires a separate direct
Coordinator authorization bound to the installed workflow blob and main SHA.
Only native time coordinates and HSRL header/QC metadata are read; raw arrays and
science values are never persisted or emitted.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,io,json,math,os,re,statistics,sys,urllib.parse,urllib.request
from pathlib import Path

REPO="search-maker/twilight-mystic-experiments"; ISSUE=60
API=f"https://api.github.com/repos/{REPO}"; ARM="https://adc.arm.gov/armlive"
WF=".github/workflows/arm-stagea-decoded-time-metadata-one-shot-v1.yml"
PRIORITY_SHA="345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0"
REQUEST_SHA="5ec3fb6b052d886091a77704bf425abcb0d04ea4279727c3a37b4f5ab6e63318"
STREAMS=("sgpsaszefilterbandsC1.a1","sgphsrlC1.a1","sgprlprofbeC1.c1","sgparsclkazr1kolliasC1.c0","sgpceilC1.b1")
ALIASES={"sgpsaszefilterbandsC1.a1":"sasze_filterbands","sgphsrlC1.a1":"hsrl","sgprlprofbeC1.c1":"rlprofbe","sgparsclkazr1kolliasC1.c0":"arscl","sgpceilC1.b1":"ceil"}
COLS=("case_id","stream","core_start_utc","core_end_utc","source_files","source_sha256s","decoded_time_basis","code_version","sample_count_core","left_bracket_utc","right_bracket_utc","left_bracket_delta_s","right_bracket_delta_s","median_positive_cadence_s","max_gap_s","duplicate_count","nonfinite_or_masked_count","continuity_pass","failure_reason")
QC=("qc_level_backsct","qc_aerosol_depol","qc_volume_depol")
AUTH_PREFIX="COORDINATOR::ARM_STAGEA_DECODED_TIME_METADATA_ONE_SHOT_"
FORBID=("REVOK","SUSPEND","HALT","NOT_AUTH","AUTH_FALSE","CLOSED")

class Refusal(RuntimeError): pass
def h(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def fh(p:Path)->str:return h(p.read_bytes())
def z(s:str)->dt.datetime:return dt.datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(dt.timezone.utc)
def zs(x:dt.datetime)->str:return x.astimezone(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
def err(e:BaseException)->str:
 n=type(e).__name__;return n if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",n) else "Refusal"

def priority(path:Path):
 if fh(path)!=PRIORITY_SHA: raise Refusal("priority digest mismatch")
 with path.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
 if len(rows)!=20: raise Refusal("priority row count mismatch")
 ids=[]
 for r in rows:
  ev=r["event"].lower(); cid=f"{r['local_civil_date']}_{ev}"; z(r["t_minus6_utc"]);z(r["t_minus8_utc"]);ids.append(cid)
 if len(set(ids))!=20: raise Refusal("priority case identity mismatch")
 return rows

def gj(url,token):
 req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","Authorization":f"Bearer {token}","X-GitHub-Api-Version":"2022-11-28","User-Agent":"arm-stagea-decoded-time-metadata-v1"})
 try:
  with urllib.request.urlopen(req,timeout=120) as r:return json.loads(r.read().decode())
 except Exception as e: raise Refusal("GitHub read failed: "+err(e)) from None

def comments(token):
 out=[]
 for page in range(1,101):
  b=gj(f"{API}/issues/{ISSUE}/comments?per_page=100&page={page}",token)
  if not isinstance(b,list):raise Refusal("comment response invalid")
  out+=b
  if len(b)<100:break
 else:raise Refusal("comment pagination bound")
 return out

def canon(rows):
 out=[];seen=set()
 for r in rows:
  i=r.get("id");b=r.get("body");c=r.get("created_at")
  if not isinstance(i,int) or i in seen or not isinstance(b,str) or not isinstance(c,str):raise Refusal("comment ledger invalid")
  seen.add(i);out.append({"created_at":c,"id":i,"body":b})
 out.sort(key=lambda x:(x["created_at"],x["id"],x["body"]))
 raw=json.dumps(out,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode();return out,h(raw)
def title(body):return next((x.strip() for x in body.splitlines() if x.strip()),"")
def wq_open(c):
 begins={};closed=set()
 for j,r in enumerate(c):
  t=title(r["body"]).upper()
  if "WRITE_QUIET_BEGIN" in t:begins[r["id"]]=j
  if any(x in t for x in ("WRITE_QUIET_END","WRITE_QUIET_RELEASE","FENCE_RELEASE")):
   for m in re.finditer(r"\bbegin\s*[:=]\s*`?(\d+)`?",r["body"],re.I):
    i=int(m.group(1));
    if i in begins and j>begins[i]:closed.add(i)
 return sorted(set(begins)-closed)
def kv(body):
 o={}
 for line in body.splitlines()[1:]:
  m=re.fullmatch(r"\s*([A-Za-z0-9_]+)\s*:\s*`?([^`\r\n]+?)`?\s*",line)
  if m:
   if m.group(1) in o:raise Refusal("duplicate authorization field")
   o[m.group(1)]=m.group(2).strip()
 return o

def preflight(auth_id:int,wf_blob:str):
 if os.getenv("ARM_USER_ID") or os.getenv("ARM_ACCESS_TOKEN"):raise Refusal("governance subprocess refuses ARM credentials")
 gh=os.getenv("GITHUB_TOKEN","").strip();
 if not gh:raise Refusal("GITHUB_TOKEN missing")
 if os.getenv("GITHUB_EVENT_NAME")!="workflow_dispatch" or os.getenv("GITHUB_REF")!="refs/heads/main" or os.getenv("GITHUB_REF_TYPE")!="branch" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":raise Refusal("not exact attempt1 main dispatch")
 if not re.fullmatch(r"[0-9a-f]{40}",wf_blob):raise Refusal("workflow blob malformed")
 rb=gj(API,gh); mb=gj(f"{API}/git/ref/heads/main",gh); ib=gj(f"{API}/issues/{ISSUE}",gh)
 a,d1=canon(comments(gh)); b,d2=canon(comments(gh)); ma=gj(f"{API}/git/ref/heads/main",gh); ia=gj(f"{API}/issues/{ISSUE}",gh)
 if rb.get("default_branch")!="main" or mb["object"]["sha"]!=ma["object"]["sha"] or d1!=d2 or a!=b or ib.get("comments")!=ia.get("comments") or len(b)!=ia.get("comments"):raise Refusal("live governance snapshot unstable")
 main=ma["object"]["sha"]
 if main!=os.getenv("GITHUB_SHA"):raise Refusal("dispatch SHA not current main")
 if wq_open(b):raise Refusal("unmatched WRITE_QUIET")
 row=next((r for r in b if r["id"]==auth_id),None)
 if not row:raise Refusal("authorization identity absent")
 t=title(row["body"]);u=t.upper()
 if not t.startswith(AUTH_PREFIX) or "AUTHORIZED" not in u or any(x in u for x in FORBID):raise Refusal("authorization title not positive direct ARM transition")
 direct=[r for r in b if title(r["body"]).startswith("COORDINATOR::ARM_STAGEA_DECODED_TIME_METADATA_ONE_SHOT_")]
 if not direct or direct[-1]["id"]!=auth_id:raise Refusal("authorization is not latest direct Stage-A one-shot claim")
 x=kv(row["body"]); need={"workflow":WF,"event":"workflow_dispatch","ref":"refs/heads/main","run_attempt":"1","priority_ledger_sha256":PRIORITY_SHA,"canonical_request_sha256":REQUEST_SHA,"one_shot":"true","result_blind":"true","workflow_blob_sha":wf_blob,"main":main}
 for k,v in need.items():
  if x.get(k)!=v:raise Refusal("authorization binding mismatch: "+k)
 return {"schema":1,"status":"PASS","authorization_comment_id":auth_id,"workflow_path":WF,"workflow_blob_sha":wf_blob,"main_sha":main,"event":"workflow_dispatch","ref":"refs/heads/main","run_attempt":1,"issue60_comment_count":len(b),"issue60_latest_comment_id":b[-1]["id"],"issue60_atomic_ledger_sha256":d2,"arm_credentials_read":False,"arm_network_access_performed":False,"native_file_open_performed":False,"science_values_read":False}

def arm_json(url):
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"arm-stagea-decoded-time-metadata-v1"}),timeout=120) as r:return json.loads(r.read().decode())
 except Exception as e:raise Refusal("ARM query failed: "+err(e)) from None
def query(pair,stream,start,end):
 q=urllib.parse.urlencode({"user":pair,"ds":stream,"start":start.date().isoformat(),"end":end.date().isoformat(),"wt":"json"}); obj=arm_json(ARM+"/query?"+q);names=set()
 def walk(v):
  if isinstance(v,dict):
   for y in v.values():walk(y)
  elif isinstance(v,list):
   for y in v:walk(y)
  elif isinstance(v,str):
   n=os.path.basename(v)
   if n.endswith((".nc",".cdf")) and n.startswith(stream+"."):names.add(n)
 walk(obj);return sorted(names)
def download(pair,name):
 q=urllib.parse.urlencode({"user":pair,"file":name});req=urllib.request.Request(ARM+"/saveData?"+q,headers={"User-Agent":"arm-stagea-decoded-time-metadata-v1"})
 try:
  with urllib.request.urlopen(req,timeout=180) as r:return r.read()
 except Exception as e:raise Refusal("ARM native transfer failed: "+err(e)) from None

def decode(raw,stream):
 from netCDF4 import Dataset,num2date
 ds=Dataset("inmemory.nc",memory=raw);times=[];masked=0;basis="";ver="";fp=""
 try:
  if "time" in ds.variables:
   v=ds.variables["time"]; vals=v[:]; units=getattr(v,"units",None);cal=getattr(v,"calendar","standard");basis="time + units/calendar"
   if not units:raise Refusal("time units missing")
   for x in vals.ravel():
    try:
     y=float(x)
     if not math.isfinite(y):masked+=1;continue
     t=num2date(y,units,calendar=cal,only_use_cftime_datetimes=False,only_use_python_datetimes=True);times.append(t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t.astimezone(dt.timezone.utc))
    except Exception:masked+=1
  elif "base_time" in ds.variables and "time_offset" in ds.variables:
   base=float(ds.variables["base_time"][:]);off=ds.variables["time_offset"][:];basis="base_time + time_offset"
   epoch=dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)
   for x in off.ravel():
    try:
     y=float(x)
     if not math.isfinite(y):masked+=1;continue
     times.append(epoch+dt.timedelta(seconds=base+y))
    except Exception:masked+=1
  else:raise Refusal("decoded sample-time coordinate absent")
  if stream=="sgphsrlC1.a1":
   ver=str(getattr(ds,"code_version","")); meta={"code_version":ver}
   for n in QC:
    if n not in ds.variables:raise Refusal("required HSRL QC metadata variable absent")
    v=ds.variables[n];meta[n]={"dtype":str(v.dtype),"dimensions":list(v.dimensions),"shape":list(v.shape),"attributes":{a:str(v.getncattr(a)) for a in v.ncattrs()}}
   for a in ds.ncattrs():
    if any(k in a.lower() for k in ("calib","version","wavelength","process")):meta[a]=str(ds.getncattr(a))
   fp=h(json.dumps(meta,sort_keys=True,separators=(",",":")).encode())
  return sorted(times),masked,basis,ver,fp
 finally:ds.close()

def summarize(cid,stream,cs,ce,recs):
 pts=[];masked=0;basis=set();vers=set();fps=set();files=[]
 for n,sh,t,m,b,v,fp in recs:
  files.append((n,sh));pts+=t;masked+=m;basis.add(b)
  if v:vers.add(v)
  if fp:fps.add(fp)
 pts.sort();uniq=sorted(set(pts));dups=len(pts)-len(uniq);left=max((t for t in uniq if t<=cs),default=None);right=min((t for t in uniq if t>=ce),default=None);core=[t for t in uniq if cs<=t<=ce];gaps=[(b-a).total_seconds() for a,b in zip(uniq,uniq[1:]) if b>a];med=statistics.median(gaps) if gaps else math.nan;mx=max(gaps) if gaps else math.nan;ok=bool(left and right and core and gaps and math.isfinite(med) and mx<=2*med+1e-9)
 if stream=="sgphsrlC1.a1":ok=ok and vers=={"2.6.7"} and bool(fps)
 fail="" if ok else "decoded_time_continuity_or_required_provenance_failed"
 row={"case_id":cid,"stream":ALIASES[stream],"core_start_utc":zs(cs),"core_end_utc":zs(ce),"source_files":sorted(n for n,_ in files),"source_sha256s":[sh for n,sh in sorted(files)],"decoded_time_basis":" + ".join(sorted(basis)),"code_version":",".join(sorted(vers)),"sample_count_core":len(core),"left_bracket_utc":zs(left) if left else "","right_bracket_utc":zs(right) if right else "","left_bracket_delta_s":(cs-left).total_seconds() if left else "","right_bracket_delta_s":(right-ce).total_seconds() if right else "","median_positive_cadence_s":med if math.isfinite(med) else "","max_gap_s":mx if math.isfinite(mx) else "","duplicate_count":dups,"nonfinite_or_masked_count":masked,"continuity_pass":"PASS" if ok else "FAIL","failure_reason":fail}
 return row,fps

def write_rows(rows,out):
 out.mkdir(parents=True,exist_ok=True);cp=out/"stageA_actual_time_continuity_v2.csv";jp=out/"stageA_actual_time_continuity_v2.json"
 with cp.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=COLS);w.writeheader()
  for r in rows:
   q=dict(r);q["source_files"]=json.dumps(q["source_files"],separators=(",",":"));q["source_sha256s"]=json.dumps(q["source_sha256s"],separators=(",",":"));w.writerow(q)
 jp.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n",encoding="utf-8");return cp,jp

def receipt(auth,blob):return {"schema":1,"purpose":"ARM_STAGEA_DECODED_TIME_METADATA_ONE_SHOT_V1","status":"FAIL_CLOSED","authorization_comment_id":auth,"workflow_path":WF,"workflow_blob_sha":blob,"main_sha":os.getenv("GITHUB_SHA",""),"event":os.getenv("GITHUB_EVENT_NAME",""),"ref":os.getenv("GITHUB_REF",""),"run_id":os.getenv("GITHUB_RUN_ID",""),"run_attempt":int(os.getenv("GITHUB_RUN_ATTEMPT","0") or 0),"priority_ledger_sha256":PRIORITY_SHA,"canonical_request_sha256":REQUEST_SHA,"continuity_csv_sha256":None,"continuity_json_sha256":None,"row_count":0,"hsrl_code_version_set":[],"hsrl_header_metadata_fingerprints":[],"source_file_count":0,"arm_query_performed":False,"native_file_download_performed":False,"native_file_open_performed":False,"decoded_time_extraction_performed":False,"credential_values_logged":False,"raw_native_files_persisted":False,"raw_time_arrays_persisted":False,"science_arrays_read":False,"heldout_sws_sasze_radiance_opened":False,"stage_b_authorized":False,"mystic_science_authorized":False,"taylor_or_jerusalem_used":False,"production_authorized":False,"error_type":None}

def extract(p,out,auth,blob):
 r=receipt(auth,blob);out.mkdir(parents=True,exist_ok=True);rp=out/"receipt.json"
 try:
  uid=os.getenv("ARM_USER_ID","").strip();tok=os.getenv("ARM_ACCESS_TOKEN","").strip()
  if not uid or not tok:raise Refusal("ARM credentials absent")
  if os.getenv("GITHUB_EVENT_NAME")!="workflow_dispatch" or os.getenv("GITHUB_REF")!="refs/heads/main" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":raise Refusal("extract refuses non-attempt1 main dispatch")
  pair=uid+":"+tok;rows=[];versions=set();fps=set();src=set();r["arm_query_performed"]=True
  for x in priority(p):
   ev=x["event"].lower();cid=f"{x['local_civil_date']}_{ev}";a=z(x["t_minus6_utc"]);b=z(x["t_minus8_utc"]);cs,ce=min(a,b),max(a,b)
   for stream in STREAMS:
    names=query(pair,stream,cs-dt.timedelta(days=1),ce+dt.timedelta(days=1));
    if not names or len(names)>8:raise Refusal("native filename set missing or unbounded")
    rec=[]
    for n in names:
     raw=download(pair,n);r["native_file_download_performed"]=True;sh=h(raw);t,m,basis,v,fp=decode(raw,stream);r["native_file_open_performed"]=True;r["decoded_time_extraction_performed"]=True;rec.append((n,sh,t,m,basis,v,fp));src.add((n,sh))
    row,f=summarize(cid,stream,cs,ce,rec);rows.append(row);fps|=f
    if stream=="sgphsrlC1.a1" and row["code_version"]:versions|=set(row["code_version"].split(","))
  if len(rows)!=100:raise Refusal("output row count not 100")
  cp,jp=write_rows(rows,out)
  from tools.arm_stagea_time_continuity_contract_v1 import verify as v
  c=v.load_priority_cases(p);cr=v.load_csv_rows(cp);jr=v.load_json_rows(jp);v.verify_json_equivalence(cr,jr);v.verify_rows(cr,c)
  r.update(status="PASS",continuity_csv_sha256=fh(cp),continuity_json_sha256=fh(jp),row_count=100,hsrl_code_version_set=sorted(versions),hsrl_header_metadata_fingerprints=sorted(fps),source_file_count=len(src))
  rp.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n");print("ARM_STAGEA_DECODED_TIME_METADATA_PASS");return 0
 except Exception as e:
  r["error_type"]=err(e);rp.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n");print("ARM_STAGEA_DECODED_TIME_METADATA_FAIL_CLOSED",file=sys.stderr);return 2

def selftest(p,wf=None):
 assert len(priority(p))==20
 c,d=canon([{"id":2,"created_at":"2026-01-01T00:00:01Z","body":"B"},{"id":1,"created_at":"2026-01-01T00:00:00Z","body":"A"}]);assert [x["id"] for x in c]==[1,2] and re.fullmatch(r"[0-9a-f]{64}",d)
 assert not wq_open(canon([{"id":1,"created_at":"2026-01-01T00:00:00Z","body":"WRITE_QUIET_BEGIN::X"},{"id":2,"created_at":"2026-01-01T00:00:01Z","body":"WRITE_QUIET_END::X\nbegin=1"}])[0])
 if wf:
  t=wf.read_text();
  for s in ("workflow_dispatch:","github.run_attempt == 1","env -u ARM_USER_ID -u ARM_ACCESS_TOKEN","ARM_USER_ID: ${{ secrets.ARM_USER_ID }}","ARM_ACCESS_TOKEN: ${{ secrets.ARM_ACCESS_TOKEN }}"):assert s in t
 print("ARM_STAGEA_DECODED_TIME_METADATA_SELF_TEST_PASS");return 0

def main(argv=None):
 p=argparse.ArgumentParser();s=p.add_subparsers(dest="cmd",required=True);a=s.add_parser("self-test");a.add_argument("--priority",type=Path,required=True);a.add_argument("--workflow",type=Path);a=s.add_parser("preflight");a.add_argument("--authorization-comment",type=int,required=True);a.add_argument("--workflow-blob-sha",required=True);a=s.add_parser("extract");a.add_argument("--priority",type=Path,required=True);a.add_argument("--output-dir",type=Path,required=True);a.add_argument("--authorization-comment",type=int,required=True);a.add_argument("--workflow-blob-sha",required=True);x=p.parse_args(argv)
 if x.cmd=="self-test":return selftest(x.priority,x.workflow)
 if x.cmd=="preflight":print(json.dumps(preflight(x.authorization_comment,x.workflow_blob_sha),sort_keys=True,separators=(",",":")));return 0
 return extract(x.priority,x.output_dir,x.authorization_comment,x.workflow_blob_sha)
if __name__=="__main__":raise SystemExit(main())
