#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

CONTRACT_REL=Path('review/level-b-v3-fresh-validation-implementation-v1/contract-v1.json')
CORE_REL=Path('review/level-b-v3-fresh-validation-implementation-v1/fresh_validation_v1.py')
MANIFEST_REL=Path('experiments/level-b-v3-fresh-validation-v1/build_manifest_v1.py')
ADAPTER_REL=Path('experiments/level-b-v3-fresh-validation-v1/adapter_v1.py')
EXECUTOR_REL=Path('experiments/level-b-v3-fresh-validation-v1/executor_v1.py')
BASE_EVAL_REL=Path('review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py')

class Refusal(RuntimeError): pass

def req(c,m):
    if not c: raise Refusal(m)

def module(n,p):
    s=importlib.util.spec_from_file_location(n,p); req(s is not None and s.loader is not None,f'load failure {p}'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,required=True); ap.add_argument('--materialized-dir',type=Path,required=True); ap.add_argument('--base-model-dir',type=Path,required=True); a=ap.parse_args()
    root=a.repo_root; p=json.loads((root/CONTRACT_REL).read_text())
    core=module('v3_validation_core_tests',root/CORE_REL); manifest=module('v3_manifest_tests',root/MANIFEST_REL); adapter=module('v3_adapter_tests',root/ADAPTER_REL); executor=module('v3_executor_tests',root/EXECUTOR_REL); base_eval=module('v3_frozen_dod_tests',root/BASE_EVAL_REL)
    parity=core.training_parity(p,a.materialized_dir,a.base_model_dir,root)
    req(parity['status']=='PASS' and parity['protectedValuesRead'] is False and parity['ordinal27ValuesRead'] is False,'training parity failed')
    cases=core.expected_cases(p); req(len(cases)==24 and cases[0]['seed']==2110000001 and cases[-1]['seed']==2110000024,'case universe drift')
    m=manifest.build(root); req(m['manifestSha256']==manifest.selfhash(m),'manifest self hash drift'); adapter.validate_manifest(m)
    req(executor.BRANCH_RE.fullmatch('dispatch/level-b-v3-fresh-validation-ordinal28-v1') is not None,'exact dispatch branch rejected')
    for bad in ('dispatch/level-b-v3-fresh-validation-ordinal27-v1','dispatch/level-b-v3-fresh-validation-ordinal28-v2','review/level-b-v3-fresh-validation-implementation-v1'):
        req(executor.BRANCH_RE.fullmatch(bad) is None,f'nonexact dispatch branch accepted: {bad}')
    channels=('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')
    records=[]
    for i in range(6):
        records.append({'insideValidatedSupport':True,'shapePerCaseNrmse':0.0,'shapeWorstSingleCoefficientNormalizedError':0.0,'channelErrors':{ch:{'signedLogError':0.0,'absoluteLogError':0.0,'uncertaintyNormalizedError':0.0,'baselineAbsoluteLogError':1.0} for ch in channels}})
    ok=base_eval.summarize_records(records,p); req(ok['definitionOfDonePassed'] is True,'known-pass DoD case failed')
    records[0]['channelErrors']['photopicLuminanceCdM2']={'signedLogError':0.3500000001,'absoluteLogError':0.3500000001,'uncertaintyNormalizedError':1.0,'baselineAbsoluteLogError':1.0}
    bad=base_eval.summarize_records(records,p); req(bad['definitionOfDonePassed'] is False and bad['channelSummary']['photopicLuminanceCdM2']['passes'] is False,'worst-error threshold not enforced')
    records[0]['channelErrors']['photopicLuminanceCdM2']={'signedLogError':0.35,'absoluteLogError':0.35,'uncertaintyNormalizedError':1.0,'baselineAbsoluteLogError':1.0}
    edge=base_eval.summarize_records(records,p); req(edge['channelSummary']['photopicLuminanceCdM2']['worstAbsoluteLogError']==0.35 and edge['channelSummary']['photopicLuminanceCdM2']['passes'] is True,'inclusive frozen 0.35 edge drift')
    print(json.dumps({'status':'PASS','caseCount':24,'trainingParity':parity,'manifestSha256':m['manifestSha256'],'exactDispatchGuard':True,'frozenDodKnownAnswer':True,'protectedValuesRead':False,'ordinal27ValuesRead':False},sort_keys=True)); return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); raise SystemExit(2)
