#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2, 3, 4, 5, 6]
PHOTONS = 200_000
SEED_BASE = {1:961_000_000,2:962_000_000,3:963_000_000,4:964_000_000,5:965_000_000,6:966_000_000}
REFERENCE_PHOTONS = 50_000
REFERENCE_SEED_BASE = 955_000_000


def load_module(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot import {path}')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def normalize(text: str):
    out=[]
    for line in text.splitlines():
        s=line.strip()
        if s.startswith('mc_photons '): out.append('mc_photons <PHOTONS>')
        elif s.startswith('mc_randomseed '): out.append('mc_randomseed <SEED>')
        elif s.startswith('mc_basename '): out.append('mc_basename <CASE_DIR>')
        else: out.append(line)
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline-runner',type=Path,required=True)
    ap.add_argument('--observations',type=Path,required=True)
    ap.add_argument('--response',type=Path,required=True)
    ap.add_argument('--data-dir',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()

    base=load_module('frozen_taylor_v1',a.baseline_runner)
    tables=base.load_response(a.response)
    rays=base.quadrature(tables)
    if len(rays)!=64: raise RuntimeError('expected exact 64-ray Taylor quadrature')
    data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve()

    new_seeds=[]; audit=[]
    for row in ROWS:
        obs=base.load_observation(a.observations,row); aod=float(obs['aod550_primary_frozen'])
        for rep in REPLICATES:
            for ray in rays:
                idx=int(ray['rayIndex'])
                newseed=SEED_BASE[rep]+row*1000+idx
                refseed=REFERENCE_SEED_BASE+row*1000+idx
                new_seeds.append(newseed)
                ref=base.render(data,atm,Path('/tmp/ref')/f'r{row}'/f'q{rep}'/f'x{idx}',obs,ray,aod,REFERENCE_PHOTONS,refseed)
                new=base.render(data,atm,Path('/tmp/new')/f'r{row}'/f'q{rep}'/f'x{idx}',obs,ray,aod,PHOTONS,newseed)
                if normalize(ref)!=normalize(new):
                    raise RuntimeError(f'physical input drift row={row} rep={rep} ray={idx}')
                if 'aerosol_file tau ' in new:
                    raise RuntimeError('unexpected aerosol_file tau in default-only input')
                if f'mc_photons {PHOTONS}' not in new or f'mc_randomseed {newseed}' not in new:
                    raise RuntimeError('new photon/seed line mismatch')
                audit.append({'row':row,'replicate':rep,'rayIndex':idx,'seed':newseed,'inputSha256':hashlib.sha256(new.encode()).hexdigest()})

    old={base0+row*1000+ray for base0 in (955_000_000,956_000_000,957_000_000,958_000_000,959_000_000,960_000_000) for row in ROWS for ray in range(1,65)}
    if len(new_seeds)!=1152 or len(set(new_seeds))!=1152: raise RuntimeError('fresh seed universe not exactly 1152 unique')
    if set(new_seeds)&old: raise RuntimeError('fresh 200k seeds overlap consumed 50k namespaces')

    a.output.mkdir(parents=True,exist_ok=False)
    result={'schemaVersion':1,'stageId':'taylor-broadband-photon-scaling-200k-v1','status':'DRY_INPUT_IDENTITY_PASS','rows':ROWS,'replicates':REPLICATES,'photonsPerRay':PHOTONS,'auditCount':len(audit),'uniqueSeedCount':len(set(new_seeds)),'solverCallsIfAuthorized':1152,'configuredPhotonHistoriesIfAuthorized':230_400_000,'normalizedIntentionalDifferences':['mc_photons','mc_randomseed','mc_basename'],'audit':audit}
    (a.output/'preflight.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('status','auditCount','uniqueSeedCount','solverCallsIfAuthorized','configuredPhotonHistoriesIfAuthorized')},sort_keys=True))

if __name__=='__main__': main()
