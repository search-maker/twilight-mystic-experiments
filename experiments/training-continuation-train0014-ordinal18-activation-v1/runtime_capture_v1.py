#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'training-continuation-transport-v1'))
from common_v1 import canon,load,require,verify_self

def build(probe:dict)->dict:
    require(probe.get('status')=='RUNTIME_IDENTITY_CAPTURED','runtime probe status drift')
    require(probe.get('scientificSolverExecuted') is False and probe.get('syntaxCheckExecuted') is False,'runtime probe crossed no-science boundary')
    out={
      'schemaVersion':1,'stageId':'training-continuation-runtime-identity-v1','status':'RUNTIME_IDENTITY_CAPTURED_SELF_HASHED',
      'scientificSolverExecuted':False,'syntaxCheckExecuted':False,
      'uvspecSha256':probe.get('uvspecSha256'),'uvspecHelpSha256':probe.get('uvspecHelpSha256'),
      'libRadtranDataTreeSha256':probe.get('libRadtranDataTreeSha256'),'libRadtranDataFileCount':probe.get('libRadtranDataFileCount'),'libRadtranDataByteCount':probe.get('libRadtranDataByteCount'),
      'atmosphereSha256':probe.get('atmosphereSha256'),'runtimeLockRawSha256':probe.get('runtimeLockRawSha256'),
      'python':probe.get('python'),'pythonImplementation':probe.get('pythonImplementation'),'architecture':probe.get('architecture'),'runnerImage':probe.get('runnerImage'),'runnerArch':probe.get('runnerArch'),
      'environmentSpec':'runner=ubuntu-24.04;channel=conda-forge;python=3.12.4;rubin-libradtran=2.0.6=py312pl5321he9373c2_1',
      'boundary':'runtime identity only; uvspec help may run, but no syntax check or scientific solver executes',
    }
    for key in ('uvspecSha256','uvspecHelpSha256','libRadtranDataTreeSha256','atmosphereSha256','runtimeLockRawSha256'):
        require(isinstance(out[key],str) and len(out[key])==64,f'runtime field missing: {key}')
    out['runtimeIdentitySha256']=canon(out); return out

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('--probe',type=Path,required=True); p.add_argument('--expected',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    try:
        expected=load(a.expected); verify_self(expected,'expectedRuntimeContractSha256'); require(expected.get('status')=='REVIEW_ONLY_EXPECTED_RUNTIME_IDENTITY','expected runtime contract drift')
        actual=build(load(a.probe)); require(actual==expected.get('runtimeIdentity'),'runtime identity mismatch against frozen expected identity')
        a.output.write_text(json.dumps(actual,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':'PASSED','runtimeIdentitySha256':actual['runtimeIdentitySha256']})); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e),'scientificSolverExecuted':False,'syntaxCheckExecuted':False},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
