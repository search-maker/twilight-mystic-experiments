#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path
ROWS=[1,5,9,13,17,21]; REPLICATES=[1,2,3,4,5,6]; PHOTONS=50_000
SEED_BASE={1:979_000_000,2:980_000_000,3:981_000_000,4:982_000_000,5:983_000_000,6:984_000_000}
REFERENCE_SEED_BASE=941_000_000

def load(path):
    s=importlib.util.spec_from_file_location('frozen_taylor_v1',path)
    if s is None or s.loader is None: raise RuntimeError(f'cannot import {path}')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def normalize(text):
    out=[]
    for line in text.splitlines():
        s=line.strip()
        if s.startswith('mc_randomseed '): out.append('mc_randomseed <SEED>')
        elif s.startswith('mc_basename '): out.append('mc_basename <CASE>')
        else: out.append(line)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--baseline-runner',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    base=load(a.baseline_runner); tables=base.load_response(a.response); rays=base.quadrature(tables)
    if len(rays)!=64: raise RuntimeError('expected exact 64-ray Taylor quadrature')
    data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve(); seeds=[]; audit=[]
    for row in ROWS:
        obs=base.load_observation(a.observations,row); aod=float(obs['aod550_primary_frozen'])
        for rep in REPLICATES:
            for ray in rays:
                idx=int(ray['rayIndex']); newseed=SEED_BASE[rep]+row*1000+idx; refseed=REFERENCE_SEED_BASE+row*1000+idx; seeds.append(newseed)
                ref=base.render(data,atm,Path('/tmp/ref')/f'r{row}'/f'p{rep}'/f'x{idx}',obs,ray,aod,PHOTONS,refseed)
                new=base.render(data,atm,Path('/tmp/new')/f'r{row}'/f'p{rep}'/f'x{idx}',obs,ray,aod,PHOTONS,newseed)
                if normalize(ref)!=normalize(new): raise RuntimeError(f'physical/model input drift row={row} rep={rep} ray={idx}')
                if f'mc_photons {PHOTONS}' not in new: raise RuntimeError('50k photon identity changed')
                if f'aerosol_set_tau_at_wvl 550 {aod:.8f}' not in new: raise RuntimeError('frozen row AOD changed')
                if 'aerosol_file tau ' in new: raise RuntimeError('unexpected aerosol_file tau')
                audit.append({'row':row,'replicate':rep,'rayIndex':idx,'seed':newseed,'inputSha256':hashlib.sha256(new.encode()).hexdigest()})
    if len(audit)!=2304 or len(seeds)!=2304 or len(set(seeds))!=2304: raise RuntimeError('anchor seed/audit universe mismatch')
    consumed={base0+row*1000+ray for base0 in range(955_000_000,979_000_000,1_000_000) for row in ROWS for ray in range(1,65)}
    if set(seeds)&consumed: raise RuntimeError('anchor seeds overlap consumed Taylor broadband namespaces')
    a.output.mkdir(parents=True,exist_ok=False); result={'schemaVersion':1,'stageId':'taylor-primary-mc-screen-50k-v1','status':'DRY_ANCHOR_IDENTITY_PASS','rows':ROWS,'replicates':REPLICATES,'photonsPerRay':PHOTONS,'uniqueSeedCount':len(set(seeds)),'auditCount':len(audit),'solverCallsIfAuthorized':2304,'configuredPhotonHistoriesIfAuthorized':115_200_000,'audit':audit}; (a.output/'preflight.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({k:result[k] for k in ('status','uniqueSeedCount','auditCount','solverCallsIfAuthorized','configuredPhotonHistoriesIfAuthorized')},sort_keys=True))
if __name__=='__main__': main()
