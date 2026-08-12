#!/usr/bin/env python3
import json,sys,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
T=ROOT.parent/'training-continuation-transport-v1'
sys.path.insert(0,str(T)); from common_v1 import canon,verify_self

def load(n): return json.loads((ROOT/n).read_text())
def main():
    a=load('activation-contract.v1.json'); verify_self(a,'activationContractSha256'); assert a['status']=='REVIEW_ONLY_ACTIVATION_NOT_AUTHORIZED'; assert a['proposedScientificOrdinal']==18; assert all(v is False for v in a['activationBoundary'].values())
    r=load('post-merge-preauthorization-audit.v1.json'); verify_self(r,'auditSha256'); assert r['latestConsumedScientificOrdinal']==17 and r['nextAvailableScientificOrdinalIfAllocatedLater']==18; assert r['authorizationOrdinalAllocated'] is False
    e=load('expected-runtime-identity.v1.json'); verify_self(e,'expectedRuntimeContractSha256'); verify_self(e['runtimeIdentity'],'runtimeIdentitySha256')
    m=load('execution-manifest.train0014.v1.json'); verify_self(m,'manifestSha256'); assert m['caseCount']==4 and m['totalPhotonHistories']==200000000 and [x['seed'] for x in m['cases']]==[1700000001,1700000002,1700000003,1700000004]
    t=load('authorization-template.ordinal18.v1.json'); verify_self(t,'templateSha256'); assert t['enabled'] is False and t['scientificExecutionAuthorized'] is False and t['dispatchAuthorized'] is False
    print('activation contract tests: PASS')
if __name__=='__main__': main()
