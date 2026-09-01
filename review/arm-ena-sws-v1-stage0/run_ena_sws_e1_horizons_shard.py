#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,importlib.util,json,math,re,sys,tempfile,time,urllib.parse,urllib.request
from pathlib import Path
from typing import Any
UTC=dt.timezone.utc
CONTRACT='ARM_ENA_SWS_V1_E1_LUNAR_GEOMETRY_JPL_HORIZONS_COPY_SGP_G3_V1'
CONTROL_COMMENT='5487892240'
FROZEN_UNIVERSE_SHA256='87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41'
SITE='-28.0257,39.0916,0.030'; EXPECTED_E_LON=331.974300; EXPECTED_LAT=39.091600; EXPECTED_ALT_KM=0.030
THRESHOLD=-10.0; MARGIN=0.010; EXPECTED_COUNT=906
API='https://ssd.jpl.nasa.gov/api/horizons.api'

def load_module(name:str,path:Path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None: raise RuntimeError(f'cannot import {path}')
 m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def parse_iso(s:str)->dt.datetime:return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def fmt_horizons(x:dt.datetime)->str:return x.strftime('%Y-%m-%d %H:%M:%S.%f')
def parse_horizons_time(s:str)->dt.datetime:return dt.datetime.strptime(s.strip(),'%Y-%b-%d %H:%M:%S.%f').replace(tzinfo=UTC)

def frozen_rows(generator_path:Path)->list[dict[str,str]]:
 gen=load_module('ena_e1_generator',generator_path)
 rows=gen.generate_rows()
 with tempfile.TemporaryDirectory(prefix='ena_e1_universe_') as td:
  p=Path(td)/'u.csv';gen.write_csv(p,rows);digest=sha_file(p)
 if digest!=FROZEN_UNIVERSE_SHA256:raise RuntimeError(f'frozen universe hash mismatch: {digest}')
 if len(rows)!=EXPECTED_COUNT:raise RuntimeError(f'frozen universe count mismatch: {len(rows)}')
 return rows

def shard_bounds(n:int,index:int,count:int)->tuple[int,int]:
 if count<=0 or not 0<=index<count:raise ValueError('invalid shard index/count')
 return n*index//count,n*(index+1)//count

def query_url(start:dt.datetime,stop:dt.datetime,n:int)->str:
 params={'format':'text','COMMAND':"'301'",'OBJ_DATA':"'NO'",'MAKE_EPHEM':"'YES'",'EPHEM_TYPE':"'OBSERVER'",'CENTER':"'coord@399'",'COORD_TYPE':"'GEODETIC'",'SITE_COORD':f"'{SITE}'",'START_TIME':f"'{fmt_horizons(start)}'",'STOP_TIME':f"'{fmt_horizons(stop)}'",'STEP_SIZE':f"'{n}'",'TIME_TYPE':"'UT'",'REF_SYSTEM':"'ICRF'",'APPARENT':"'AIRLESS'",'QUANTITIES':"'4'",'TIME_DIGITS':"'FRACSEC'",'EXTRA_PREC':"'YES'",'CSV_FORMAT':"'YES'",'ELEV_CUT':"'-90'",'SKIP_DAYLT':"'NO'"}
 return API+'?'+urllib.parse.urlencode(params,safe="',@-")

def fetch(url:str)->bytes:
 last=None
 for delay in (0,2,5):
  if delay:time.sleep(delay)
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'ARM-ENA-E1-Horizons-validation/1.0'})
   with urllib.request.urlopen(req,timeout=90) as r:return r.read()
  except Exception as exc:last=exc
 raise RuntimeError(f'Horizons query failed after 3 attempts: {type(last).__name__}:{last}')

def semantic_validate(text:str,start:dt.datetime,stop:dt.datetime,n:int)->dict[str,Any]:
 errors=[]
 m=re.search(r'^API VERSION:\s*([^\r\n]+)',text,re.M);api_version=m.group(1).strip() if m else ''
 try:api_num=float(re.match(r'\d+(?:\.\d+)?',api_version).group(0)) if api_version else float('nan')
 except Exception:api_num=float('nan')
 if not math.isfinite(api_num) or api_num<1.0:errors.append('API_VERSION_INVALID')
 if 'API SOURCE: NASA/JPL Horizons API' not in text:errors.append('API_SOURCE_INVALID')
 if not re.search(r'^Target body name:\s*Moon \(301\)',text,re.M):errors.append('TARGET_NOT_MOON_301')
 if not re.search(r'^Center body name:\s*Earth \(399\)',text,re.M):errors.append('CENTER_NOT_EARTH_399')
 gm=re.search(r'^Center geodetic\s*:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))',text,re.M)
 geo=None
 if gm:
  geo=tuple(float(gm.group(i)) for i in (1,2,3))
  if abs(((geo[0]-EXPECTED_E_LON+180)%360)-180)>5e-6:errors.append('CENTER_LONGITUDE_MISMATCH')
  if abs(geo[1]-EXPECTED_LAT)>5e-6:errors.append('CENTER_LATITUDE_MISMATCH')
  if abs(geo[2]-EXPECTED_ALT_KM)>5e-4:errors.append('CENTER_ALTITUDE_MISMATCH')
 else:errors.append('CENTER_GEODETIC_MISSING')
 if 'Atmos refraction: NO (AIRLESS)' not in text:errors.append('AIRLESS_REFRACTION_HEADER_MISSING')
 if not re.search(r'Azimuth_\(a-app\),\s*Elevation_\(a-app\)',text):errors.append('AZ_EL_HEADING_MISSING')
 for token in ('Airless apparent azimuth and elevation of target center.','TOPOCENTRIC ONLY.','Units: DEGREES'):
  if token not in text:errors.append('FOOTER_MISSING:'+token)
 soe=re.search(r'\$\$SOE\s*\n(.*?)\n\$\$EOE',text,re.S);parsed=[]
 if not soe:errors.append('SOE_EOE_MISSING')
 else:
  for line in soe.group(1).splitlines():
   if not line.strip():continue
   parts=next(csv.reader([line]))
   if len(parts)<5:errors.append('EPHEMERIS_ROW_TOO_SHORT');continue
   try:stamp=parse_horizons_time(parts[0]);elev=float(parts[4].strip())
   except Exception:errors.append('EPHEMERIS_ROW_PARSE_FAIL');continue
   parsed.append((stamp,elev))
 if not parsed:errors.append('NO_PARSED_EPHEMERIS_ROWS')
 if parsed:
  if len(parsed)!=n+1:errors.append(f'SAMPLE_COUNT_MISMATCH:{len(parsed)}!={n+1}')
  if abs((parsed[0][0]-start).total_seconds())>0.0011:errors.append('START_ENDPOINT_NOT_COVERED')
  if abs((parsed[-1][0]-stop).total_seconds())>0.0011:errors.append('STOP_ENDPOINT_NOT_COVERED')
  if any(parsed[i+1][0]<=parsed[i][0] for i in range(len(parsed)-1)):errors.append('TIMESTAMPS_NOT_STRICTLY_INCREASING')
 duration=(stop-start).total_seconds();effective=duration/n
 if effective<0.5-1e-12:errors.append('EFFECTIVE_SPACING_BELOW_FROZEN_HALF_SECOND')
 mx=max((x[1] for x in parsed),default=None)
 return {'ok':not errors,'errors':errors,'api_version':api_version,'center_geodetic':geo,'sample_count':len(parsed),'first_timestamp':parsed[0][0].isoformat().replace('+00:00','Z') if parsed else None,'last_timestamp':parsed[-1][0].isoformat().replace('+00:00','Z') if parsed else None,'max_moon_elevation_deg':mx,'effective_spacing_s':effective}

def classify(mx:float|None,valid:bool)->str:
 if not valid or mx is None:return 'QUERY_VALIDATION_FAIL'
 if abs(mx-THRESHOLD)<=MARGIN:return 'UNRESOLVED_NUMERICAL_MARGIN'
 return 'PASS' if mx<=THRESHOLD else 'FAIL'

def write_csv(p:Path,rows:list[dict[str,Any]]):
 fields=sorted({k for r in rows for k in r})
 with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--generator',type=Path,required=True);ap.add_argument('--shard-index',type=int,required=True);ap.add_argument('--shard-count',type=int,default=18);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args()
 rows=frozen_rows(a.generator.resolve());lo,hi=shard_bounds(len(rows),a.shard_index,a.shard_count);selected=rows[lo:hi]
 out=a.output_dir.resolve();rawdir=out/'raw';rawdir.mkdir(parents=True,exist_ok=True);results=[]
 for universe_index,r in enumerate(selected,start=lo):
  start=min(parse_iso(r['t_minus6_utc']),parse_iso(r['t_minus8_utc']));stop=max(parse_iso(r['t_minus6_utc']),parse_iso(r['t_minus8_utc']));duration=(stop-start).total_seconds();n=max(1,math.floor(duration/0.5));url=query_url(start,stop,n)
  try:
   raw=fetch(url);text=raw.decode('utf-8','strict');raw_path=rawdir/f"{r['case_id']}.txt";raw_path.write_bytes(raw);v=semantic_validate(text,start,stop,n);disp=classify(v['max_moon_elevation_deg'],v['ok']);err=' | '.join(v['errors'])
  except Exception as exc:
   raw=b'';raw_path=None;v={'api_version':'','sample_count':0,'max_moon_elevation_deg':None,'effective_spacing_s':duration/n,'first_timestamp':None,'last_timestamp':None,'center_geodetic':None};disp='QUERY_FAILED';err=f'{type(exc).__name__}:{exc}'
  results.append({'contract':CONTRACT,'control_comment':CONTROL_COMMENT,'source_universe_sha256':FROZEN_UNIVERSE_SHA256,'universe_index':universe_index,'case_id':r['case_id'],'local_civil_date':r['local_civil_date'],'t_minus8_utc':r['t_minus8_utc'],'t_minus7_utc':r['t_minus7_utc'],'t_minus6_utc':r['t_minus6_utc'],'start_time_utc':start.isoformat().replace('+00:00','Z'),'stop_time_utc':stop.isoformat().replace('+00:00','Z'),'duration_s':duration,'step_size_N':n,'effective_spacing_s':v['effective_spacing_s'],'sample_count':v['sample_count'],'first_response_timestamp':v['first_timestamp'],'last_response_timestamp':v['last_timestamp'],'max_moon_elevation_deg':v['max_moon_elevation_deg'],'threshold_deg':THRESHOLD,'margin_deg':MARGIN,'api_version_reported':v['api_version'],'center_geodetic_reported':json.dumps(v['center_geodetic']),'raw_sha256':sha_bytes(raw) if raw else '','raw_file':str(raw_path.relative_to(out)) if raw_path else '','e1_disposition':disp,'error':err,'query_url':url,'protected_sws_values_opened':False})
  time.sleep(1)
 write_csv(out/'ena_sws_e1_lunar_gate_shard.csv',results)
 counts={}
 for r in results:counts[r['e1_disposition']]=counts.get(r['e1_disposition'],0)+1
 summary={'contract':CONTRACT,'control_comment':CONTROL_COMMENT,'source_universe_sha256':FROZEN_UNIVERSE_SHA256,'candidate_count_total':len(rows),'shard_index':a.shard_index,'shard_count':a.shard_count,'shard_start_index':lo,'shard_stop_index_exclusive':hi,'shard_case_count':len(selected),'counts':counts,'site_coord':SITE,'threshold_deg':THRESHOLD,'margin_deg':MARGIN,'protected_sws_values_opened':False,'stage_b_authorized':False}
 (out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 files={}
 for p in sorted(out.rglob('*')):
  if p.is_file() and p.name!='manifest.json':files[str(p.relative_to(out))]={'size':p.stat().st_size,'sha256':sha_file(p)}
 (out/'manifest.json').write_text(json.dumps({'contract':CONTRACT,'source_universe_sha256':FROZEN_UNIVERSE_SHA256,'shard_index':a.shard_index,'files':files,'protected_sws_values_opened':False},indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps(summary,sort_keys=True))
 return 2 if any(r['e1_disposition'] in ('QUERY_FAILED','QUERY_VALIDATION_FAIL') for r in results) else 0
if __name__=='__main__':raise SystemExit(main())
