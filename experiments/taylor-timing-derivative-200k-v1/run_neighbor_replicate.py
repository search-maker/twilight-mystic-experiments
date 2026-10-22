#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

STAGE='taylor-timing-derivative-200k-v1'
ROWS=[22,26]
REPLICATES=[1,2,3,4,5,6]
PHOTONS=200_000
SEED_BASE={1:973_000_000,2:974_000_000,3:975_000_000,4:976_000_000,5:977_000_000,6:978_000_000}

class Failure(RuntimeError): pass

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def load_module(path:Path):
    s=importlib.util.spec_from_file_location('frozen_taylor_v1',path)
    if s is None or s.loader is None: raise Failure(f'cannot import {path}')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def aggregate(records):
    q=sum(float(r['normalizedWeight'])*float(r['q']) for r in records)
    qstd=math.sqrt(sum((float(r['normalizedWeight'])*float(r['qStdConservative']))**2 for r in records))
    return q,qstd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--row',type=int,required=True); ap.add_argument('--replicate',type=int,choices=REPLICATES,required=True); ap.add_argument('--baseline-runner',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--uvspec',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args()
    if a.row not in ROWS: raise Failure('row outside frozen timing-neighbor universe')
    base=load_module(a.baseline_runner); obs=base.load_observation(a.observations,a.row); tables=base.load_response(a.response); rays=base.quadrature(tables)
    if len(rays)!=64: raise Failure('expected exact 64-ray Taylor quadrature')
    out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=False); work=out/'work'; data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve(); u=a.uvspec.resolve(); aod=float(obs['aod550_primary_frozen']); seedbase=SEED_BASE[a.replicate]
    records=[]
    for ray in rays:
        idx=int(ray['rayIndex']); seed=seedbase+a.row*1000+idx; case=work/f'ray-{idx:02d}'
        rec=base.execute_one(u,data,atm,obs,ray,aod,PHOTONS,seed,case,tables,False); records.append(rec)
    q,qstd=aggregate(records)
    if not math.isfinite(q) or q<=0 or not math.isfinite(qstd) or qstd<0: raise Failure('invalid aggregate broadband result')
    shutil.rmtree(work,ignore_errors=True)
    result={'schemaVersion':1,'stageId':STAGE,'status':'COMPLETED','row':a.row,'replicate':a.replicate,'utc':obs['utc'],'sunAltGeometricDeg':float(obs['sun_alt_geometric_deg']),'aod550Frozen':aod,'surfacePressureHpa':float(obs['surface_pressure_hpa']),'photonsPerRay':PHOTONS,'rayCount':len(rays),'seedBase':seedbase,'defaultQ':q,'defaultQStdConservative':qstd,'baselineRunnerSha256':sha(a.baseline_runner),'observationsSha256':sha(a.observations),'responseSha256':sha(a.response),'rays':records,'boundary':'Default-atmosphere 200k timing-neighbor numerical reconvergence only; no residual fitting or physical model change.'}
    (out/'row-replicate-result.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({k:result[k] for k in ('status','row','replicate','defaultQ','defaultQStdConservative')},sort_keys=True))
if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'status':'FAILED','stageId':STAGE,'error':str(exc)}),file=sys.stderr); raise
