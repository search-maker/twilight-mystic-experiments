#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
from typing import Any
import numpy as np

class Refusal(RuntimeError): pass
def req(c: bool, m: str) -> None:
    if not c: raise Refusal(m)
def sha_file(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v: Any) -> str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p: Path) -> dict[str,Any]:
    v=json.loads(p.read_text()); req(isinstance(v,dict),f'object required: {p}'); return v

def verify_manifest(m: dict[str,Any]) -> None:
    req(m.get('packageId')=='level-b-v3-computationally-validated-surrogate-package-v1','package id drift')
    req(m.get('governance')=='MYSTIC-STATE-0072','governance drift')
    req(m['validationBinding']['scientificStatus']=='PASS_FROZEN_FRESH_DOD' and m['validationBinding']['definitionOfDonePassed'] is True,'PASS binding required')
    req(m['model']['modelCanonicalSha256']=='c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9','model drift')
    req(m['representation']['packageSha256']=='2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763','representation drift')
    req(m['packageContents']['includesOrdinal28ProtectedTruthRecords'] is False,'protected truths forbidden')
    req(m['consumerBoundaries']['productionPromotionAuthorized'] is False,'production opened')
    req(m['consumerBoundaries']['workerBIntegrationAuthorizedByThisPackage'] is False,'Worker-B opened')

def verify_model(path: Path, m: dict[str,Any]) -> None:
    req(sha_file(path)==m['model']['artifactMemberFileSha256'],'model member byte hash drift')
    x=load(path)
    y=dict(x); claim=y.pop('artifactCanonicalSha256',None); req(claim==m['model']['artifactCanonicalSha256'] and canon(y)==claim,'model artifact canonical drift')
    model=dict(x['model']); mclaim=model.pop('modelCanonicalSha256',None); req(mclaim==m['model']['modelCanonicalSha256'] and canon(model)==mclaim,'model canonical drift')
    req(x['selectedSpec']['candidateId']==m['model']['selectedCandidateId'],'candidate drift')
    req(x['model']['kind']==m['model']['kind'],'model kind drift')

def verify_rep(path: Path, m: dict[str,Any]) -> None:
    req(sha_file(path)==m['representation']['packageSha256'],'representation package hash drift')
    with np.load(path,allow_pickle=False) as z:
        req(set(z.files)=={'wavelength_nm','integration_weights','grand_mean_nullspace_residual','selected_nullspace_pca_components','resolved_pca_indices'},'representation members drift')
        req(z['wavelength_nm'].shape==(8001,) and float(z['wavelength_nm'][0])==380.0 and float(z['wavelength_nm'][-1])==780.0,'wavelength grid drift')
        req(z['integration_weights'].shape==(3,8001),'integration weights drift')
        req(z['selected_nullspace_pca_components'].shape==(10,8001),'PCA component drift')
        req(z['grand_mean_nullspace_residual'].shape==(8001,),'grand mean drift')

def verify_binding(path: Path, m: dict[str,Any]) -> None:
    x=load(path); y=dict(x); claim=y.pop('bindingSelfSha256',None)
    req(claim==m['validationBinding']['bindingSelfSha256'] and canon(y)==claim,'result binding self hash drift')
    req(x['evaluation']['sourceStatus']=='PASS_FROZEN_FRESH_DOD' and x['evaluation']['definitionOfDonePassed'] is True,'terminal PASS drift')
    req(x['frozenIdentities']['modelCanonicalSha256']==m['model']['modelCanonicalSha256'],'binding model drift')
    req(x['frozenIdentities']['representationPackageSha256']==m['representation']['packageSha256'],'binding representation drift')

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); ap.add_argument('--model',required=True); ap.add_argument('--representation',required=True); ap.add_argument('--result-binding',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    m=load(Path(a.manifest)); verify_manifest(m); verify_model(Path(a.model),m); verify_rep(Path(a.representation),m); verify_binding(Path(a.result_binding),m)
    out=Path(a.out); shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
    final=json.loads(json.dumps(m)); final['status']='COMPUTATIONALLY_VALIDATED_SURROGATE_PACKAGE_READY_NO_PRODUCTION'; final['packageBuild']={'modelFileSha256':sha_file(Path(a.model)),'representationFileSha256':sha_file(Path(a.representation)),'protectedTruthCopied':False,'scientificExecutionPerformed':False}
    final['packageManifestSha256']=canon(final)
    (out/'validated-surrogate-package-v1.json').write_text(json.dumps(final,indent=2,sort_keys=True,allow_nan=False)+'\n')
    shutil.copyfile(a.model,out/'model-artifact-materialization-v1.json')
    shutil.copyfile(a.representation,out/'spectral-representation-v2.npz')
    print(json.dumps({'status':final['status'],'packageManifestSha256':final['packageManifestSha256'],'members':sorted(p.name for p in out.iterdir())},sort_keys=True))
    return 0
if __name__=='__main__': raise SystemExit(main())
