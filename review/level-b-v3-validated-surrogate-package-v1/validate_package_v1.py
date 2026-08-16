#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
import numpy as np
class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('package'); a=ap.parse_args(); root=Path(a.package)
    req(sorted(p.name for p in root.iterdir())==['model-artifact-materialization-v1.json','spectral-representation-v2.npz','validated-surrogate-package-v1.json'],'package member drift')
    m=json.loads((root/'validated-surrogate-package-v1.json').read_text()); claim=m.pop('packageManifestSha256'); req(canon(m)==claim,'package manifest self hash drift')
    req(m['status']=='COMPUTATIONALLY_VALIDATED_SURROGATE_PACKAGE_READY_NO_PRODUCTION','package status drift')
    req(m['packageBuild']['protectedTruthCopied'] is False and m['packageBuild']['scientificExecutionPerformed'] is False,'package boundary drift')
    req(sha(root/'model-artifact-materialization-v1.json')==m['model']['artifactMemberFileSha256'],'model byte hash drift')
    req(sha(root/'spectral-representation-v2.npz')==m['representation']['packageSha256'],'representation byte hash drift')
    with np.load(root/'spectral-representation-v2.npz',allow_pickle=False) as z: req(z['integration_weights'].shape==(3,8001) and z['selected_nullspace_pca_components'].shape==(10,8001),'representation shape drift')
    req(m['validationBinding']['scientificStatus']=='PASS_FROZEN_FRESH_DOD','scientific PASS drift')
    req(m['consumerBoundaries']['productionPromotionAuthorized'] is False and m['consumerBoundaries']['workerBIntegrationAuthorizedByThisPackage'] is False,'consumer gate opened')
    print(json.dumps({'status':'PASS','packageManifestSha256':claim,'modelCanonicalSha256':m['model']['modelCanonicalSha256'],'representationPackageSha256':m['representation']['packageSha256']},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
