#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, statistics, sys
from pathlib import Path
from typing import Any
STAGE_ID='g01-fixed-precision-diagnosis-execution-v1'
SOURCE_RUN_ID=30875148389
DIAGNOSIS_RUN_ID=30876899126
DIAGNOSIS_HEAD='9d6f155936578b8d409d25dfe57c7b741bda6915'
DIAGNOSIS_ARTIFACT='g01-fixed-precision-diagnosis-proposal-v1'
DIAGNOSIS_DIGEST='sha256:8b53ff4b0fd16a0523b186fe41bfcab3238f80e34e10b4be7dda257c716b4db4'
EXPECTED_OLD={f'cgc-g01-alis-r{i}':(80600+i,50_000_000) for i in range(1,5)}
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f'expected object {p}')
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def one(root:Path,name:str)->Path:
 m=list(root.rglob(name))
 if len(m)!=1:raise ValueError(f'expected one {name}, found {len(m)}')
 return m[0]
def artifact(listing:dict[str,Any],name:str,digest:str)->dict[str,Any]:
 m=[x for x in listing.get('artifacts',[]) if isinstance(x,dict) and x.get('name')==name]
 if len(m)!=1 or m[0].get('expired') is not False or m[0].get('digest')!=digest:raise ValueError(f'artifact binding changed: {name}')
 return m[0]
def finite(v:Any)->float:
 x=float(v)
 if not math.isfinite(x):raise ValueError('nonfinite numeric')
 return x
def audit(execution_proposal:Path,diagnosis_dir:Path,diagnosis_run_path:Path,diagnosis_artifacts_path:Path,source_analysis_dir:Path,source_preflight_dir:Path,source_run_path:Path,source_artifacts_path:Path)->dict[str,Any]:
 p=load(execution_proposal); dp_path=one(diagnosis_dir,'g01-fixed-diagnostic-proposal.json'); dr_path=one(diagnosis_dir,'g01-diagnosis-readiness.json'); dd_path=one(diagnosis_dir,'g01-precision-diagnosis.json'); dp,dr,dd=map(load,(dp_path,dr_path,dd_path))
 if p.get('stageId')!=STAGE_ID or dp.get('stageId')!=STAGE_ID:raise ValueError('execution/diagnosis stage mismatch')
 core=('batchId','cases','limits','analysisPlan','selectedAlisReferenceNm','selectedGeometryIds','sourceRunId','sourceAnalysisArtifactId','sourceAnalysisArtifactDigest','diagnosisRawSha256')
 stale={k:(p.get(k),dp.get(k)) for k in core if p.get(k)!=dp.get(k)}
 if stale:raise ValueError(f'execution copy differs from reviewed diagnosis proposal: {stale}')
 if raw(dd_path)!=dp.get('diagnosisRawSha256') or dd.get('status')!='G01_MONTE_CARLO_PRECISION_DIAGNOSED' or dd.get('failureMode')!='MONTE_CARLO_PRECISION_ONLY':raise ValueError('diagnosis hash/status changed')
 if dr.get('status')!='G01_FIXED_PRECISION_DIAGNOSIS_PROPOSED_PENDING_SEPARATE_AUTHORIZATION' or dr.get('executionAuthorized') is not False or dr.get('noAutomaticAdditionalBlocks') is not True:raise ValueError('diagnosis readiness changed')
 d_run=load(diagnosis_run_path);d_art=load(diagnosis_artifacts_path)
 required={'id':DIAGNOSIS_RUN_ID,'status':'completed','conclusion':'success','event':'pull_request','run_attempt':1,'head_branch':'agent/g01-precision-diagnosis-v1','head_sha':DIAGNOSIS_HEAD,'name':'G01 fixed precision diagnosis proposal','path':'.github/workflows/g01-fixed-precision-diagnosis-proposal.yml'}
 stale={k:(d_run.get(k),v) for k,v in required.items() if d_run.get(k)!=v}
 if stale:raise ValueError(f'diagnosis run boundary changed: {stale}')
 da=artifact(d_art,DIAGNOSIS_ARTIFACT,DIAGNOSIS_DIGEST)
 if da.get('id')!=8879848416:raise ValueError('diagnosis artifact id changed')
 source_run=load(source_run_path);source_artifacts=load(source_artifacts_path)
 required={'id':SOURCE_RUN_ID,'status':'completed','conclusion':'success','event':'workflow_dispatch','run_attempt':1,'head_branch':'main','head_sha':'68617143a92ed8aef12e0cbdbaaf66a77c731bb1','name':'MYSTIC held-out timeout continuation v1 scientific execution','path':'.github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml'}
 stale={k:(source_run.get(k),v) for k,v in required.items() if source_run.get(k)!=v}
 if stale:raise ValueError(f'ordinal-6 run boundary changed: {stale}')
 title=str(source_run.get('display_title',''))
 for token in ('7a348428327f1dfbac3d0606e7661ecd766d5b92','cross-geometry-held-out-confirmation-timeout-continuation-v1:screening:6','ordinal=6'):
  if token not in title:raise ValueError(f'ordinal-6 title missing {token}')
 artifact(source_artifacts,'cross-geometry-timeout-continuation-v1-analysis',p['sourceAnalysisArtifactDigest']);artifact(source_artifacts,'cross-geometry-timeout-continuation-v1-preflight',p['sourcePreflightArtifactDigest'])
 analysis_path=one(source_analysis_dir,'timeout-continuation-analysis.json');readiness_path=one(source_analysis_dir,'reference-readiness.json');dataset_path=one(source_analysis_dir,'audited-reference-dataset.json')
 analysis,readiness,dataset=map(load,(analysis_path,readiness_path,dataset_path))
 results={x.get('groupId'):x for x in analysis.get('geometryResults',[]) if isinstance(x,dict)};g01=results.get('g01-reference-bridge');g06=results.get('g06-late-opposite-high-aerosol')
 if not isinstance(g01,dict) or g01.get('classification')!='HELD_OUT_CONFIRMATION_INCONCLUSIVE_PRECISION_CAP_REACHED' or not isinstance(g06,dict) or g06.get('classification')!='HELD_OUT_CONFIRMATION_PASSED':raise ValueError('ordinal-6 geometry classification changed')
 alis=g01['methodStatistics']['alis'];vroom=g01['methodStatistics']['reference-vroom'];ratio=finite(g01['meanRatioAlisToVroom']);fraction=finite(g01['vroomPhotopicWeightFractionNodeRatioInsideInterval'])
 if not (0.08<float(alis['relativeStandardErrorOfMean'])<0.10 and float(vroom['relativeStandardErrorOfMean'])<=0.10 and 0.5<=ratio<=2.0 and fraction>=0.80):raise ValueError('not a precision-only gap')
 if readiness.get('technicalDiagnosisRequiredGeometryIds')!=['g01-reference-bridge'] or readiness.get('acceptedReferenceGeometryCount')!=5 or readiness.get('noAutomaticAdditionalBlocks') is not True:raise ValueError('ordinal-6 readiness changed')
 if dataset.get('status')!='INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET' or len(dataset.get('records',[]))!=5:raise ValueError('ordinal-6 dataset changed')
 old_paths=sorted((source_preflight_dir/'source-g01').rglob('case-result.json'))
 if len(old_paths)!=4:raise ValueError('preserved g01 case count changed')
 vals=[];rows=[]
 for path in old_paths:
  r=load(path);cid=r.get('caseId');exp=EXPECTED_OLD.get(cid)
  if exp is None or r.get('status')!='COMPLETED' or (r.get('seed'),r.get('photonHistories'))!=exp or r.get('solver',{}).get('exitCode')!=0 or r.get('solver',{}).get('timedOut') is not False:raise ValueError(f'preserved case changed: {cid}')
  value=finite(r['selectedPhotopicContributionCdM2']);vals.append(value);rows.append({'caseId':cid,'rawSha256':raw(path),'valueCdM2':value})
 mean=statistics.mean(vals);cv=statistics.stdev(vals)/mean;rsem=cv/math.sqrt(4);projected=cv/math.sqrt(8)
 if abs(rsem-float(alis['relativeStandardErrorOfMean']))>1e-12 or projected>0.08:raise ValueError('precision diagnosis did not reproduce')
 return {'schemaVersion':1,'stageId':STAGE_ID,'status':'SOURCE_G01_FIXED_PROPOSAL_AUDITED','sourceDiagnosisRunId':DIAGNOSIS_RUN_ID,'sourceDiagnosisArtifactId':da['id'],'sourceDiagnosisArtifactDigest':DIAGNOSIS_DIGEST,'sourceRunId':SOURCE_RUN_ID,'sourceAnalysisArtifactDigest':p['sourceAnalysisArtifactDigest'],'sourcePreflightArtifactDigest':p['sourcePreflightArtifactDigest'],'sourceAnalysisRawSha256':raw(analysis_path),'sourceReadinessRawSha256':raw(readiness_path),'sourceDatasetRawSha256':raw(dataset_path),'diagnosisProposalRawSha256':raw(dp_path),'diagnosisRawSha256':raw(dd_path),'preservedG01CaseResults':sorted(rows,key=lambda x:x['caseId']),'preservedBlockCount':4,'preservedRelativeStandardErrorOfMean':rsem,'projectedRelativeStandardErrorAtEightBlocks':projected,'integratedMeanRatioAlisToVroom':ratio,'vroomPhotopicWeightFractionNodeRatioInsideInterval':fraction,'recommendedFreshBlockCount':4,'recommendedPhotonsPerBlock':50_000_000,'noAutomaticAdditionalBlocksAfterContinuation':True,'boundary':'reviewed diagnosis artifact plus immutable ordinal-6 source audited; four fresh blocks only'}
def main()->int:
 a=argparse.ArgumentParser();a.add_argument('--execution-proposal',type=Path,required=True);a.add_argument('--diagnosis-dir',type=Path,required=True);a.add_argument('--diagnosis-run',type=Path,required=True);a.add_argument('--diagnosis-artifacts',type=Path,required=True);a.add_argument('--source-analysis-dir',type=Path,required=True);a.add_argument('--source-preflight-dir',type=Path,required=True);a.add_argument('--source-run',type=Path,required=True);a.add_argument('--source-artifacts',type=Path,required=True);a.add_argument('--output',type=Path,required=True);x=a.parse_args()
 try:r=audit(x.execution_proposal,x.diagnosis_dir,x.diagnosis_run,x.diagnosis_artifacts,x.source_analysis_dir,x.source_preflight_dir,x.source_run,x.source_artifacts);x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(dump(r));print(dump(r),end='');return 0
 except Exception as e:print(dump({'status':'REFUSED','stageId':STAGE_ID,'reason':str(e)}),file=sys.stderr,end='');return 2
if __name__=='__main__':raise SystemExit(main())
