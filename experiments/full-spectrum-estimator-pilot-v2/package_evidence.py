#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
CONTRACT=HERE/'transport-contract.v6.json'; BINDING=HERE/'review-binding.v6.json'; TEMPLATE=HERE/'authorization-template.ordinal14.json'
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def rawsha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def selfhash(v:dict[str,Any],field:str)->str:
    x=dict(v); x[field]=None; return hashlib.sha256(canon(x)).hexdigest()
def load(p:Path): return json.loads(p.read_text())
def require(c,m):
    if not c: raise RuntimeError(m)

def verify_static(repository_root:Path)->dict[str,Any]:
    c=load(CONTRACT); b=load(BINDING); t=load(TEMPLATE)
    require(c['contractSha256']==selfhash(c,'contractSha256'),'transport contract self-hash mismatch')
    require(b['bindingSha256']==selfhash(b,'bindingSha256'),'review binding self-hash mismatch')
    require(c['authorizationRules']['templateRawSha256']==rawsha(TEMPLATE),'authorization template raw hash mismatch')
    require(t['enabled'] is False and t['exactAuthorizationCommit'] is None and t['exactAuthorizationParentCommit'] is None,'authorization template not disabled')
    for row in b['reviewPaths']+[b['contractWorkflow']]:
        p=repository_root/row['destinationPath']; require(p.is_file(),f'missing bound review path {row["destinationPath"]}')
        require(p.stat().st_size==row['size'],f'bound review size drift {row["destinationPath"]}')
        require(rawsha(p)==row['sha256'],f'bound review hash drift {row["destinationPath"]}')
    manifest=load(repository_root/c['scientificPayload']['executionManifestPath'])
    require(manifest['caseCount']==44 and manifest['configuredPhotonHistoriesSum']==5600000000,'scientific manifest cardinality drift')
    seeds=[x['seed'] for x in manifest['cases']]
    require(seeds==list(range(970001,970045)),'scientific seed sequence drift')
    return {'status':'STATIC_BINDING_PASS','reviewPathsVerified':len(b['reviewPaths'])+1,'caseCount':44,'scientificExecutionPerformed':False,'authorizationCreated':False,'ordinalAllocatedReservedOrConsumed':False}

def matrix(repository_root:Path)->list[dict[str,Any]]:
    c=load(CONTRACT); m=load(repository_root/c['scientificPayload']['executionManifestPath'])
    return [{'caseId':x['caseId'],'method':x['method'],'seed':x['seed'],'photonHistories':x['photonHistories']} for x in m['cases']]

def build_acquisition(repository_root:Path, artifacts_json:Path, zip_dir:Path)->dict[str,Any]:
    c=load(CONTRACT); m=load(repository_root/c['scientificPayload']['executionManifestPath'])
    meta=load(artifacts_json); rows=meta.get('artifacts') if isinstance(meta,dict) else meta
    require(isinstance(rows,list),'artifact metadata JSON missing artifacts list')
    by_name={x.get('name'):x for x in rows if isinstance(x,dict)}
    out_rows=[]
    for case in m['cases']:
        name=f"full-spectrum-estimator-pilot-v2-case-{case['caseId']}"
        a=by_name.get(name); require(isinstance(a,dict),f'missing current-run artifact metadata: {name}')
        digest=a.get('digest'); require(isinstance(digest,str) and digest.startswith('sha256:'),f'missing GitHub ZIP digest: {name}')
        zp=zip_dir/f'{name}.zip'; require(zp.is_file(),f'missing downloaded artifact ZIP: {name}')
        observed=rawsha(zp); require(observed==digest.removeprefix('sha256:'),f'artifact ZIP digest mismatch: {name}')
        out_rows.append({'caseId':case['caseId'],'artifactId':int(a['id']),'artifactName':name,'githubZipDigest':digest,'downloadedZipSha256':observed,'localZipPath':str(zp.resolve()),'bytesOpenedAfterTransportBinding':True})
    acq={'schemaVersion':1,'manifestId':'public-tier1-full-spectrum-estimator-pilot-acquisition-manifest-v4','protocolSha256':m['protocolSha256'],'executionManifestSha256':m['manifestSha256'],'partial':False,'observedArtifactCount':len(out_rows),'artifacts':out_rows}
    acq['manifestSha256']=hashlib.sha256(canon(acq)).hexdigest()
    return acq

def main()->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    v=sub.add_parser('verify-static'); v.add_argument('--repository-root',type=Path,required=True); v.add_argument('--output',type=Path)
    m=sub.add_parser('matrix'); m.add_argument('--repository-root',type=Path,required=True); m.add_argument('--output',type=Path)
    ba=sub.add_parser('build-acquisition'); ba.add_argument('--repository-root',type=Path,required=True); ba.add_argument('--artifacts-json',type=Path,required=True); ba.add_argument('--zip-dir',type=Path,required=True); ba.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); root=a.repository_root.resolve()
    if a.cmd=='verify-static': out=verify_static(root)
    elif a.cmd=='matrix': out={'include':matrix(root)}
    else: out=build_acquisition(root,a.artifacts_json,a.zip_dir)
    text=json.dumps(out,indent=2,sort_keys=True)+'\n'
    if a.output: a.output.write_text(text)
    else: print(text,end='')
    return 0
if __name__=='__main__': raise SystemExit(main())
