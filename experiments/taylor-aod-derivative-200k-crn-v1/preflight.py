#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2, 3, 4, 5, 6]
AODS = [0.30, 0.40]
PHOTONS = 200_000
SEED_BASE = {1:967_000_000,2:968_000_000,3:969_000_000,4:970_000_000,5:971_000_000,6:972_000_000}


def load_module(path: Path):
    spec=importlib.util.spec_from_file_location('frozen_taylor_v1',path)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot import {path}')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def normalize_pair(text: str):
    out=[]
    for line in text.splitlines():
        s=line.strip()
        if s.startswith('mc_basename '): out.append('mc_basename <CONDITION>')
        elif s.startswith('aerosol_set_tau_at_wvl 550 '): out.append('aerosol_set_tau_at_wvl 550 <AOD>')
        else: out.append(line)
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--baseline-runner',type=Path,required=True); ap.add_argument('--observations',type=Path,required=True); ap.add_argument('--response',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); base=load_module(a.baseline_runner); tables=base.load_response(a.response); rays=base.quadrature(tables)
    if len(rays)!=64: raise RuntimeError('expected exact 64-ray Taylor quadrature')
    data=a.data_dir.resolve(); atm=(data/'atmmod/afglus.dat').resolve(); audit=[]; seeds=[]
    for row in ROWS:
        obs=base.load_observation(a.observations,row)
        for rep in REPLICATES:
            for ray in rays:
                idx=int(ray['rayIndex']); seed=SEED_BASE[rep]+row*1000+idx; seeds.append(seed)
                lo=base.render(data,atm,Path('/tmp/aod030')/f'r{row}'/f'p{rep}'/f'x{idx}',obs,ray,0.30,PHOTONS,seed)
                hi=base.render(data,atm,Path('/tmp/aod040')/f'r{row}'/f'p{rep}'/f'x{idx}',obs,ray,0.40,PHOTONS,seed)
                if normalize_pair(lo)!=normalize_pair(hi): raise RuntimeError(f'paired physical input drift row={row} rep={rep} ray={idx}')
                for text,aod in ((lo,0.30),(hi,0.40)):
                    if text.count('aerosol_default')!=1 or text.count('aerosol_set_tau_at_wvl 550 ')!=1: raise RuntimeError('aerosol line count mismatch')
                    if 'aerosol_file tau ' in text: raise RuntimeError('unexpected aerosol_file tau')
                    if f'aerosol_set_tau_at_wvl 550 {aod:.8f}' not in text: raise RuntimeError('exact AOD line missing')
                    if f'mc_photons {PHOTONS}' not in text or f'mc_randomseed {seed}' not in text: raise RuntimeError('paired photons/seed mismatch')
                audit.append({'row':row,'replicate':rep,'rayIndex':idx,'seed':seed,'lowInputSha256':hashlib.sha256(lo.encode()).hexdigest(),'highInputSha256':hashlib.sha256(hi.encode()).hexdigest()})
    if len(audit)!=1152 or len(seeds)!=1152 or len(set(seeds))!=1152: raise RuntimeError('paired seed/audit universe mismatch')
    consumed={base0+row*1000+ray for base0 in (955_000_000,956_000_000,957_000_000,958_000_000,959_000_000,960_000_000,961_000_000,962_000_000,963_000_000,964_000_000,965_000_000,966_000_000) for row in ROWS for ray in range(1,65)}
    if set(seeds)&consumed: raise RuntimeError('new AOD derivative seeds overlap consumed Taylor broadband namespaces')
    a.output.mkdir(parents=True,exist_ok=False)
    result={'schemaVersion':1,'stageId':'taylor-aod-derivative-200k-crn-v1','status':'PAIRED_AOD_INPUT_IDENTITY_PASS','rows':ROWS,'replicates':REPLICATES,'aodConditions':AODS,'photonsPerRayPerCondition':PHOTONS,'pairedSeedCount':len(set(seeds)),'pairedAuditCount':len(audit),'solverCallsIfAuthorized':2304,'configuredPhotonHistoriesIfAuthorized':460_800_000,'audit':audit}
    (a.output/'preflight.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n'); print(json.dumps({k:result[k] for k in ('status','pairedSeedCount','pairedAuditCount','solverCallsIfAuthorized','configuredPhotonHistoriesIfAuthorized')},sort_keys=True))

if __name__=='__main__': main()
