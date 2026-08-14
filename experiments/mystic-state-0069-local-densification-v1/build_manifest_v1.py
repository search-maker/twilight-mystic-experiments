#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
from typing import Any

PROTOCOL_ID='mystic-state-0069-local-training-densification-v1'
PROTOCOL_CANON='9dbc150881b11481d7d0e267cb14d9507051d15442c21853b3256875db5d3c64'
BASE_MANIFEST_CANON='7351a47582ca0a328059256566b24ce10c0e6ff5d802f53ff35e133540a83819'
MANIFEST_ID='mystic-state-0069-local-densification-execution-manifest-v1'

class Refusal(RuntimeError): pass
def req(c:bool,m:str)->None:
    if not c: raise Refusal(m)
def canon(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding='utf-8')); req(isinstance(x,dict),f'object required: {p}'); return x

def build(protocol:dict[str,Any],base:dict[str,Any])->dict[str,Any]:
    req(protocol.get('protocolId')==PROTOCOL_ID and protocol.get('governance')=='MYSTIC-STATE-0069','protocol identity drift')
    ph=protocol.get('protocolCanonicalSha256'); req(ph==PROTOCOL_CANON and ph==canon({k:v for k,v in protocol.items() if k!='protocolCanonicalSha256'}),'protocol canonical drift')
    req(base.get('manifestId')=='public-tier2-v1-core-stage1-execution-manifest-v1' and base.get('manifestSha256')==BASE_MANIFEST_CANON,'base stage1 manifest drift')
    e=protocol.get('execution') or {}; d=protocol.get('design') or {}
    req((d.get('newGeometryCount'),e.get('caseCount'),e.get('totalConfiguredPhotonHistories'),e.get('proposedFreshScientificOrdinal'))==(14,28,560000000,23),'preregistered accounting drift')
    geoms=[]
    for row in d.get('geometries') or []:
        g=copy.deepcopy(row.get('geometry') or {}); g['geometryId']=row['geometryId']; g['label']=row['label']; g['role']='surrogate-training'; geoms.append(g)
    cases=[]
    for i,row in enumerate(e.get('cases') or [],start=1):
        c=copy.deepcopy(row); c['executionStage']='TRAINING_DENSIFICATION'; c['ordinalWithinCampaign']=i; c['scientificValuesReadableAfterExecution']=True; cases.append(c)
    req(len(geoms)==14 and len(cases)==28,'manifest row count drift')
    m={
      'schemaVersion':1,
      'manifestId':MANIFEST_ID,
      'status':'REVIEW_ONLY_FROZEN_TRAINING_DENSIFICATION_MANIFEST_NO_AUTHORIZATION',
      'governance':'MYSTIC-STATE-0069',
      'scientificOrdinal':23,
      'trainingOnly':True,
      'geometryCount':14,
      'caseCount':28,
      'configuredPhotonHistories':560000000,
      'sourceBindings':{
        'preregistrationProtocolId':PROTOCOL_ID,
        'preregistrationCanonicalSha256':PROTOCOL_CANON,
        'baseTier2Stage1ManifestCanonicalSha256':BASE_MANIFEST_CANON,
      },
      'runtimePackage':copy.deepcopy(base['runtimePackage']),
      'runtimeIdentityRequired':copy.deepcopy(base['runtimeIdentityRequired']),
      'frozenInputs':copy.deepcopy(base['frozenInputs']),
      'artifactContract':copy.deepcopy(base['artifactContract']),
      'executionGuards':{
        'workflowAttemptExactly':1,
        'syntaxChecksPerCaseExactly':1,
        'solverExecutionsPerCaseExactly':1,
        'githubRerunAllowed':False,
        'retryAllowed':False,
        'resumeAllowed':False,
        'adaptiveContinuationAllowed':False,
      },
      'closedBoundaries':{
        'ordinal22ValuesMayBeRead':False,
        'protectedHoldoutOpeningAuthorized':False,
        'modelFitAuthorized':False,
        'productionPromotionAuthorized':False,
        'workerBLaneReactivated':False,
        'workerCLaneReactivated':False,
      },
      'geometries':geoms,
      'cases':cases,
    }
    req(m['runtimePackage']['exactPackageSpec']=='rubin-libradtran=2.0.6=py312pl5321he9373c2_1','runtime package drift')
    req(m['runtimeIdentityRequired']['uvspecSha256']=='2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3','uvspec identity drift')
    req(m['frozenInputs']['molecularAbsorption']=='crs' and m['frozenInputs']['mcSpherical']=='1D' and m['frozenInputs']['wavelengthDomainNm']==[380.0,780.0],'physics drift')
    req([c['seed'] for c in cases]==list(range(2100000101,2100000129)),'seed identity drift')
    m['manifestSha256']=canon(m); return m

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--protocol',type=Path,required=True); ap.add_argument('--base-manifest',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    try:
        m=build(load(a.protocol),load(a.base_manifest)); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(m,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8'); print(m['manifestSha256']); return 0
    except Exception as e:
        print(json.dumps({'status':'REFUSED','reason':str(e)},sort_keys=True)); return 2
if __name__=='__main__': raise SystemExit(main())
