#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any

KEYS=('sunDepressionDeg','targetAltitudeDeg','relativeAzimuthDeg','observerElevationM','aod550')
EXCLUDE_PARTS=(
    'review/level-b-v3-future-fresh-validation-source-v1/',
    'review/level-b-v3-fresh-validation-implementation-v1/',
)

class Refusal(RuntimeError): pass

def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)

def load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text(encoding='utf-8')); req(isinstance(v,dict),f'object required: {path}'); return v

def geom_tuple(d:dict[str,Any])->tuple[float,...]|None:
    if not all(k in d for k in KEYS): return None
    try: out=tuple(float(d[k]) for k in KEYS)
    except Exception: return None
    if not all(math.isfinite(x) for x in out): return None
    return out

def walk(v:Any):
    if isinstance(v,dict):
        g=geom_tuple(v)
        if g is not None: yield g
        for x in v.values(): yield from walk(x)
    elif isinstance(v,list):
        for x in v: yield from walk(x)

def same(a:tuple[float,...],b:tuple[float,...],tol:float=1e-12)->bool:
    return all(abs(x-y)<=tol for x,y in zip(a,b))

def audit(repo_root:Path,contract_path:Path)->dict[str,Any]:
    p=load(contract_path)
    candidates=[(x['geometryId'],geom_tuple(x['geometry'])) for x in p['geometrySelection']['selectedGeometries']]
    req(all(g is not None for _,g in candidates) and len(candidates)==6,'candidate geometry drift')
    lines=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=repo_root,text=True).splitlines()
    seen=set(); collisions=[]; parsed=0
    for line in lines:
        parts=line.split(' ',1)
        if len(parts)!=2: continue
        sha,path=parts
        if not path.endswith('.json') or any(x in path for x in EXCLUDE_PARTS) or sha in seen: continue
        seen.add(sha)
        try:
            raw=subprocess.check_output(['git','cat-file','blob',sha],cwd=repo_root,stderr=subprocess.DEVNULL)
            if not all(k.encode() in raw for k in (KEYS[0],KEYS[1],KEYS[2],KEYS[3],KEYS[4])): continue
            obj=json.loads(raw); parsed+=1
        except Exception:
            continue
        for found in walk(obj):
            for gid,want in candidates:
                assert want is not None
                if same(found,want):
                    collisions.append({'geometryId':gid,'path':path,'blob':sha,'geometry':dict(zip(KEYS,found))})
    if collisions:
        raise Refusal('repository geometry collision outside prereg/review source: '+json.dumps(collisions[:20],sort_keys=True))
    return {'status':'PASS','candidateGeometryCount':6,'uniqueJsonBlobsInspected':len(seen),'geometryBearingJsonBlobsParsed':parsed,'collisionCount':0,'protectedValuesRead':False,'ordinal27ValuesRead':False}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,required=True); ap.add_argument('--contract',type=Path,required=True); a=ap.parse_args()
    try: print(json.dumps(audit(a.repo_root,a.contract),sort_keys=True)); return 0
    except Exception as e: print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
