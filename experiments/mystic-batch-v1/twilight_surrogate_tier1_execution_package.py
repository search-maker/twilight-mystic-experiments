#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from pathlib import Path
from typing import Any

STAGE_ID='twilight-surrogate-tier-1-execution-v1'
SOURCE_STAGE='twilight-surrogate-tier-1-proposal-v1'
ADAPTER_ID='mystic-twilight-tier1-execution-v1'

class PackageError(RuntimeError): pass

def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text())
 if not isinstance(v,dict): raise PackageError(f'expected object: {p}')
 return v

def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def build(proposal_path:Path,pilot_path:Path)->dict[str,Any]:
 proposal,pilot=load(proposal_path),load(pilot_path)
 required={'schemaVersion':1,'stageId':SOURCE_STAGE,'status':'PROPOSAL_ONLY_NOT_AUTHORIZATION','proposalOnly':True,'scientificExecution':False,'authorizationRequired':True,'geometryCount':48,'caseCount':96,'configuredMcPhotonsSum':6960000000,'executionTierId':'tier-1-provisional','method':'alis'}
 stale={k:(proposal.get(k),v) for k,v in required.items() if proposal.get(k)!=v}
 if stale:raise PackageError(f'tier-1 proposal mismatch: {stale}')
 if proposal.get('surrogateTrainingAutomaticallyAuthorized') is not False or proposal.get('productionModelReady') is not False:raise PackageError('proposal safety boundary changed')
 if len(proposal.get('geometries',[]))!=48 or len(proposal.get('cases',[]))!=96:raise PackageError('tier-1 object count changed')
 if [c.get('ordinal') for c in proposal['cases']]!=list(range(1,97)):raise PackageError('case ordinal sequence changed')
 if any(c.get('method')!='alis' or c.get('executionTierId')!='tier-1-provisional' or c.get('role') not in {'surrogate-training','internal-holdout'} for c in proposal['cases']):raise PackageError('case method, tier, or role changed')
 if any(c.get('photonHistories') not in {20000000,50000000,100000000,200000000} for c in proposal['cases']):raise PackageError('case photon schedule changed')
 if len({c.get('seed') for c in proposal['cases']})!=96:raise PackageError('case seeds not unique')
 if sum(c.get('photonHistories',0) for c in proposal['cases'])!=6960000000:raise PackageError('photon accounting changed')
 allowed={500.0,550.0,600.0}
 if any(float(c.get('alisSpectralImportanceSamplingNm',-1)) not in allowed for c in proposal['cases']):raise PackageError('case ALIS importance reference unsupported')
 if pilot.get('stageId')!='cross-geometry-pilot-v1' or pilot.get('adapterId')!='mystic-cross-geometry-v1':raise PackageError('pilot runtime source changed')
 runtime=pilot.get('runtime');frozen=copy.deepcopy(pilot.get('frozenInputs'))
 if not isinstance(runtime,dict) or not isinstance(frozen,dict):raise PackageError('runtime or frozen inputs missing')
 frozen['alisSpectralImportanceSamplingNm']=550.0
 return {
  'schemaVersion':1,'stageId':STAGE_ID,'sourceProposalStageId':SOURCE_STAGE,'batchId':proposal['batchId'],'mode':'scientific-proposal','proposalOnly':True,'scientificExecution':False,'successDoesNotAuthorizeProduction':True,'observationValidationRequired':True,'adapterId':ADAPTER_ID,
  'sourceTier1ProposalRawSha256':raw(proposal_path),'sourcePilotManifestRawSha256':raw(pilot_path),'source':proposal['source'],'bindings':proposal['bindings'],'runtime':runtime,'frozenInputs':frozen,
  'limits':{'maximumCases':96,'maximumParallel':8,'maximumConfiguredMcPhotonsSum':6960000000,'timeoutScheduleSeconds':{'20000000':900,'50000000':1200,'100000000':1800,'200000000':2400}},
  'caseSpecificAlisSpectralImportanceSampling':True,'externalValidationAnchorIds':proposal['externalValidationAnchorIds'],'trainingGeometryIds':proposal['trainingGeometryIds'],'internalHoldoutGeometryIds':proposal['internalHoldoutGeometryIds'],'geometries':proposal['geometries'],'cases':proposal['cases'],
  'surrogateTrainingAutomaticallyAuthorized':False,'productionModelReady':False,'boundary':'execution proposal package only; no syntax check, solver, authorization, model fitting, or production use'
 }

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--proposal',type=Path,required=True);p.add_argument('--pilot-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 try:r=build(a.proposal,a.pilot_manifest);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r));print(dump(r),end='');return 0
 except Exception as e:print(dump({'status':'REFUSED','stageId':STAGE_ID,'reason':str(e)}),file=sys.stderr,end='');return 2
if __name__=='__main__':raise SystemExit(main())
