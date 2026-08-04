#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
from typing import Any
STAGE_ID='mystic-batch-v1';SOURCE_STAGE='twilight-surrogate-tier-1-execution-v1'
class PlanError(RuntimeError):pass
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise PlanError(f'expected object: {p}')
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def build(manifest_path:Path,guard_path:Path,adapter_path:Path,runtime_lock_path:Path,workflow_path:Path)->dict[str,Any]:
 m,g=load(manifest_path),load(guard_path)
 if m.get('stageId')!=SOURCE_STAGE or len(m.get('cases',[]))!=96:raise PlanError('execution manifest invalid')
 if g.get('status')!='AUTHORIZED' or g.get('caseCount')!=96 or g.get('configuredMcPhotonsSum')!=6960000000:raise PlanError('authorization guard invalid')
 cases=[];matrix=[];schedule=m.get('limits',{}).get('timeoutScheduleSeconds',{})
 for c in m['cases']:
  p=int(c['photonHistories']);timeout=int(schedule.get(str(p),0))
  if timeout not in {900,1200,1800,2400}:raise PlanError(f'timeout missing for {p}')
  cases.append({k:c[k] for k in ('ordinal','caseId','groupId','method','block','seed','photonHistories','alisSpectralImportanceSamplingNm','role','executionTierId')})
  matrix.append({'case_id':c['caseId'],'ordinal':c['ordinal'],'seed':c['seed'],'photon_histories':p,'timeout_seconds':timeout,'role':c['role']})
 return {'schemaVersion':1,'stageId':STAGE_ID,'batchId':m['batchId'],'scientificExecution':True,'scientificDiagnostic':True,'successDoesNotAuthorizeProduction':True,'authorizationRef':g['authorizationRef'],'authorizationOrdinal':g['authorizationOrdinal'],'executionKey':g['executionKey'],'manifestRawSha256':raw(manifest_path),'scientificAdapterRawSha256':raw(adapter_path),'runtimeLockRawSha256':raw(runtime_lock_path),'executionWorkflowRawSha256':raw(workflow_path),'caseCount':96,'configuredMcPhotonsSum':6960000000,'maximumParallel':8,'cases':cases,'matrix':matrix,'boundary':'authorized tier-1 Monte Carlo cases only; no model fitting or production use'}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--guard-report',type=Path,required=True);p.add_argument('--adapter',type=Path,required=True);p.add_argument('--runtime-lock',type=Path,required=True);p.add_argument('--workflow',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--github-output',type=Path);a=p.parse_args()
 try:r=build(a.manifest,a.guard_report,a.adapter,a.runtime_lock,a.workflow);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r));
 except Exception as e:print(dump({'status':'REFUSED','stageId':STAGE_ID,'reason':str(e)}),file=sys.stderr,end='');return 2
 if a.github_output:
  with a.github_output.open('a') as h:h.write('matrix='+json.dumps({'include':r['matrix']},separators=(',',':'))+'\nmax_parallel=8\n')
 print(dump(r),end='');return 0
if __name__=='__main__':raise SystemExit(main())
