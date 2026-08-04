#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, statistics, sys
from pathlib import Path
from typing import Any
STAGE_ID='twilight-surrogate-tier-1-analysis-v1';SOURCE_STAGE='twilight-surrogate-tier-1-execution-v1';NODES=15
class AnalysisError(RuntimeError):pass
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise AnalysisError(f'expected object: {p}')
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n'
def rows(root:Path)->list[dict[str,Any]]:return [load(p) for p in sorted(root.rglob('case-result.json'))]
def summary(vals:list[float],node_rows:list[list[float]])->dict[str,Any]:
 n=len(vals);mean=statistics.fmean(vals);std=statistics.stdev(vals) if n>1 else 0.0;rsem=(std/math.sqrt(n))/mean if mean else math.inf
 return {'blockCount':n,'meanCdM2':mean,'sampleStdCdM2':std,'relativeStandardErrorOfMean':rsem,'nodeMeanRadiance':[statistics.fmean(r[i] for r in node_rows) for i in range(NODES)]}
def analyze(manifest_path:Path,cases_root:Path,batch_summary_path:Path,audit_path:Path)->tuple[dict[str,Any],dict[str,Any]]:
 m,b,a=load(manifest_path),load(batch_summary_path),load(audit_path)
 if m.get('stageId')!=SOURCE_STAGE or len(m.get('geometries',[]))!=48 or len(m.get('cases',[]))!=96:raise AnalysisError('manifest invalid')
 if b.get('classification')!='BATCH_NUMERICALLY_COMPLETE' or b.get('caseCountCompleted')!=96 or b.get('configuredMcPhotonsSum')!=6960000000:raise AnalysisError('aggregate incomplete')
 if a.get('status')!='PASSED' or a.get('caseResultCount')!=96:raise AnalysisError('independent audit failed')
 allrows=rows(cases_root)
 if len(allrows)!=96:raise AnalysisError(f'expected 96 case rows, found {len(allrows)}')
 expected={c['caseId']:c for c in m['cases']};bygroup:dict[str,list[dict[str,Any]]]={}
 for r in allrows:
  cid=r.get('caseId');e=expected.get(cid)
  if e is None or r.get('status')!='COMPLETED' or r.get('solver',{}).get('exitCode')!=0 or r.get('solver',{}).get('timedOut') is not False:raise AnalysisError(f'invalid case {cid}')
  if r.get('seed')!=e['seed'] or r.get('photonHistories')!=e['photonHistories'] or len(r.get('selectedNodeRadiance',[]))!=NODES:raise AnalysisError(f'case invariant changed {cid}')
  bygroup.setdefault(e['groupId'],[]).append(r)
 geometry_map={g['geometryId']:g for g in m['geometries']};points=[];continuation=[];target=[]
 for gid in sorted(geometry_map):
  group=bygroup.get(gid,[])
  if len(group)!=2:raise AnalysisError(f'expected two blocks for {gid}')
  vals=[float(r['selectedPhotopicContributionCdM2']) for r in group]
  if any(not math.isfinite(v) or v<=0 for v in vals):raise AnalysisError(f'invalid luminance {gid}')
  s=summary(vals,[[float(v) for v in r['selectedNodeRadiance']] for r in group]);rsem=s['relativeStandardErrorOfMean'];classification='PRECISION_TARGET_MET' if rsem<=.05 else 'PRECISION_ACCEPTED' if rsem<=.08 else 'ADAPTIVE_CONTINUATION_REQUIRED'
  if classification=='PRECISION_TARGET_MET':target.append(gid)
  if classification=='ADAPTIVE_CONTINUATION_REQUIRED':continuation.append(gid)
  group_cases=[c for c in m['cases'] if c['groupId']==gid]
  roles={c['role'] for c in group_cases}
  if len(group_cases)!=2 or len(roles)!=1:raise AnalysisError(f'role or block contract changed for {gid}')
  role=next(iter(roles))
  points.append({'geometryId':gid,'geometry':geometry_map[gid],'role':role,'classification':classification,'statistics':s,'caseIds':sorted(r['caseId'] for r in group),'eligibleForProvisionalFit':classification!='ADAPTIVE_CONTINUATION_REQUIRED' and role=='surrogate-training','eligibleForInternalHoldout':classification!='ADAPTIVE_CONTINUATION_REQUIRED' and role=='internal-holdout'})
 accepted=48-len(continuation)
 analysis={'schemaVersion':1,'stageId':STAGE_ID,'status':'TIER_1_ANALYZED','geometryCount':48,'caseCount':96,'configuredMcPhotonsSum':6960000000,'precisionTargetGeometryCount':len(target),'precisionAcceptedGeometryCount':accepted,'adaptiveContinuationRequiredGeometryIds':continuation,'allPointsWithinMaximumRsem':not continuation,'points':points,'surrogateTrainingAutomaticallyAuthorized':False,'productionModelReady':False,'observationValidationRequired':True,'boundary':'Monte Carlo precision analysis only; no surrogate fit, physical validation, or production claim'}
 dataset={'schemaVersion':1,'stageId':STAGE_ID,'status':'TIER_1_NUMERICAL_DATASET_COMPLETE' if not continuation else 'TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION','records':points,'trainingRecordCount':sum(p['eligibleForProvisionalFit'] for p in points),'internalHoldoutRecordCount':sum(p['eligibleForInternalHoldout'] for p in points),'adaptiveContinuationRequiredGeometryIds':continuation,'surrogateTrainingAutomaticallyAuthorized':False,'observationValidationRequired':True}
 return analysis,dataset
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--cases-root',type=Path,required=True);p.add_argument('--summary',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
 try:x,d=analyze(a.manifest,a.cases_root,a.summary,a.audit);a.output_dir.mkdir(parents=True,exist_ok=True);(a.output_dir/'tier1-analysis.json').write_text(dump(x));(a.output_dir/'tier1-numerical-dataset.json').write_text(dump(d));print(dump(x),end='');return 0
 except Exception as e:print(dump({'status':'REFUSED','stageId':STAGE_ID,'reason':str(e)}),file=sys.stderr,end='');return 2
if __name__=='__main__':raise SystemExit(main())
