#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,shutil,sys,tempfile
from pathlib import Path
from typing import Any
CONTRACT='ARM_ENA_SWS_V1_E1_LUNAR_GEOMETRY_JPL_HORIZONS_COPY_SGP_G3_V1'
FROZEN_UNIVERSE_SHA256='87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41'
EXPECTED_COUNT=906

def sha_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def load_module(name:str,path:Path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None:raise RuntimeError(f'cannot import {path}')
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def frozen_rows(generator:Path)->list[dict[str,str]]:
 g=load_module('ena_e1_aggregate_generator',generator)
 rows=g.generate_rows()
 with tempfile.TemporaryDirectory(prefix='ena_e1_agg_u_') as td:
  p=Path(td)/'u.csv';g.write_csv(p,rows);d=sha_file(p)
 if d!=FROZEN_UNIVERSE_SHA256:raise RuntimeError(f'frozen universe hash mismatch {d}')
 if len(rows)!=EXPECTED_COUNT:raise RuntimeError(f'frozen universe count mismatch {len(rows)}')
 return rows

def read_csv(p:Path)->list[dict[str,str]]:
 with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write_csv(p:Path,rows:list[dict[str,Any]]):
 fields=sorted({k for r in rows for k in r})
 with p.open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def verify_manifest(root:Path)->None:
 p=root/'manifest.json'
 if not p.exists():raise RuntimeError(f'missing manifest {root}')
 m=json.loads(p.read_text())
 if m.get('contract')!=CONTRACT or m.get('source_universe_sha256')!=FROZEN_UNIVERSE_SHA256 or m.get('protected_sws_values_opened') is not False:raise RuntimeError(f'manifest contract/firewall mismatch {root}')
 files=m.get('files');
 if not isinstance(files,dict) or not files:raise RuntimeError(f'empty manifest {root}')
 for rel,meta in files.items():
  f=root/rel
  if not f.is_file():raise RuntimeError(f'manifest file missing {f}')
  if f.stat().st_size!=int(meta['size']) or sha_file(f)!=meta['sha256']:raise RuntimeError(f'manifest hash/size mismatch {f}')

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--shards-root',type=Path,required=True);ap.add_argument('--generator',type=Path,required=True);ap.add_argument('--shard-count',type=int,default=18);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args()
 frozen=frozen_rows(a.generator.resolve());summaries=list(a.shards_root.resolve().rglob('summary.json'))
 if len(summaries)!=a.shard_count:raise RuntimeError(f'expected {a.shard_count} shard summaries, found {len(summaries)}')
 by_shard={};all_rows=[]
 for sp in summaries:
  root=sp.parent;verify_manifest(root);s=json.loads(sp.read_text());idx=int(s['shard_index'])
  if idx in by_shard:raise RuntimeError(f'duplicate shard {idx}')
  if s.get('contract')!=CONTRACT or s.get('source_universe_sha256')!=FROZEN_UNIVERSE_SHA256 or int(s.get('shard_count'))!=a.shard_count or s.get('protected_sws_values_opened') is not False:raise RuntimeError(f'shard summary mismatch {idx}')
  lo=EXPECTED_COUNT*idx//a.shard_count;hi=EXPECTED_COUNT*(idx+1)//a.shard_count
  if int(s['shard_start_index'])!=lo or int(s['shard_stop_index_exclusive'])!=hi or int(s['shard_case_count'])!=hi-lo:raise RuntimeError(f'shard boundary mismatch {idx}')
  rows=read_csv(root/'ena_sws_e1_lunar_gate_shard.csv')
  if len(rows)!=hi-lo:raise RuntimeError(f'shard CSV row count mismatch {idx}')
  for r in rows:
   if r.get('contract')!=CONTRACT or r.get('source_universe_sha256')!=FROZEN_UNIVERSE_SHA256 or str(r.get('protected_sws_values_opened')).lower()!='false':raise RuntimeError(f'row contract/firewall mismatch {r.get("case_id")}')
   if r.get('e1_disposition') not in {'QUERY_FAILED','QUERY_VALIDATION_FAIL'}:
    rp=root/r['raw_file']
    if not rp.is_file() or sha_file(rp)!=r['raw_sha256']:raise RuntimeError(f'raw evidence missing/hash mismatch {r.get("case_id")}')
  by_shard[idx]=(root,rows);all_rows.extend(rows)
 if sorted(by_shard)!=list(range(a.shard_count)):raise RuntimeError('shard index coverage incomplete')
 if len(all_rows)!=EXPECTED_COUNT:raise RuntimeError(f'aggregate row count {len(all_rows)}')
 all_rows.sort(key=lambda r:int(r['universe_index']))
 seen=set()
 for i,(r,f) in enumerate(zip(all_rows,frozen)):
  if int(r['universe_index'])!=i:raise RuntimeError(f'universe index gap/drift at {i}')
  if r['case_id'] in seen:raise RuntimeError(f'duplicate case {r["case_id"]}')
  seen.add(r['case_id'])
  for key in ('case_id','local_civil_date','t_minus8_utc','t_minus7_utc','t_minus6_utc'):
   if r[key]!=f[key]:raise RuntimeError(f'frozen identity/anchor drift {r["case_id"]} {key}')
 out=a.output_dir.resolve();rawout=out/'raw';rawout.mkdir(parents=True,exist_ok=True)
 for root,rows in by_shard.values():
  for r in rows:
   if r.get('raw_file'):
    src=root/r['raw_file'];dst=rawout/f"{r['case_id']}.txt"
    if dst.exists():raise RuntimeError(f'duplicate raw destination {dst.name}')
    shutil.copy2(src,dst)
 write_csv(out/'ena_sws_e1_lunar_gate.csv',all_rows)
 counts={}
 for r in all_rows:counts[r['e1_disposition']]=counts.get(r['e1_disposition'],0)+1
 pass_rows=[r for r in all_rows if r['e1_disposition']=='PASS']
 unresolved=[r for r in all_rows if r['e1_disposition']=='UNRESOLVED_NUMERICAL_MARGIN']
 bad=[r for r in all_rows if r['e1_disposition'] in {'QUERY_FAILED','QUERY_VALIDATION_FAIL'}]
 summary={'contract':CONTRACT,'source_universe_sha256':FROZEN_UNIVERSE_SHA256,'candidate_count':EXPECTED_COUNT,'shard_count':a.shard_count,'counts':counts,'pass_count':len(pass_rows),'unresolved_count':len(unresolved),'query_or_validation_failure_count':len(bad),'pass_case_ids':[r['case_id'] for r in pass_rows],'unresolved_case_ids':[r['case_id'] for r in unresolved],'protected_sws_values_opened':False,'stage_b_authorized':False,'integrity_verified_906_of_906':True}
 (out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 files={}
 for p in sorted(out.rglob('*')):
  if p.is_file() and p.name!='manifest.json':files[str(p.relative_to(out))]={'size':p.stat().st_size,'sha256':sha_file(p)}
 (out/'manifest.json').write_text(json.dumps({'contract':CONTRACT,'source_universe_sha256':FROZEN_UNIVERSE_SHA256,'files':files,'protected_sws_values_opened':False},indent=2,sort_keys=True)+'\n',encoding='utf-8')
 print(json.dumps(summary,sort_keys=True))
 return 2 if bad else 0
if __name__=='__main__':raise SystemExit(main())
