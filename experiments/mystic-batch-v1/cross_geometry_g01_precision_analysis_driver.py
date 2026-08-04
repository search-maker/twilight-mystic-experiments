#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, statistics, sys
from pathlib import Path
from typing import Any
STAGE_ID="g01-fixed-precision-diagnosis-execution-v1";SOURCE_STAGE="cross-geometry-held-out-confirmation-timeout-continuation-v1"
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f"expected object {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def mod(p:Path):
 s=importlib.util.spec_from_file_location("conv",p)
 if s is None or s.loader is None:raise ValueError("cannot load convergence module")
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def records(root:Path)->list[dict[str,Any]]:return [load(p) for p in sorted(root.rglob("case-result.json"))]
def validate_rows(rows:list[dict[str,Any]],expected:int,prefix:str)->None:
 if len(rows)!=expected:raise ValueError(f"expected {expected} rows, found {len(rows)}")
 for r in rows:
  if not str(r.get("caseId","")).startswith(prefix) or r.get("status")!="COMPLETED" or r.get("solver",{}).get("exitCode")!=0 or r.get("solver",{}).get("timedOut") is not False or r.get("syntax",{}).get("exitCode")!=0:raise ValueError(f"invalid case {r.get('caseId')}")
  value=r.get("selectedPhotopicContributionCdM2");nodes=r.get("selectedNodeRadiance")
  if not isinstance(value,(int,float)) or not math.isfinite(float(value)) or value<=0 or not isinstance(nodes,list) or len(nodes)!=15:raise ValueError(f"invalid output {r.get('caseId')}")
def mean_vector(rows:list[dict[str,Any]])->list[float]:return [statistics.mean(float(r["selectedNodeRadiance"][i]) for r in rows) for i in range(15)]
def normalize_stats(conv,value:dict[str,Any])->dict[str,Any]:
 vals=value.get("valuesCdM2");nodes=value.get("nodeMeanRadiance")
 if isinstance(vals,list) and len(vals)>=2 and isinstance(nodes,list) and len(nodes)==15:return conv.method_summary([float(x) for x in vals],[float(x) for x in nodes],None)
 return value
def analyze(proposal_path:Path,source_analysis_dir:Path,source_preflight_dir:Path,new_root:Path,summary_path:Path,audit_path:Path,convergence_path:Path,pilot_path:Path,output_dir:Path)->dict[str,Any]:
 proposal=load(proposal_path);source=load(source_analysis_dir/"timeout-continuation-analysis.json");readiness=load(source_analysis_dir/"reference-readiness.json");dataset=load(source_analysis_dir/"audited-reference-dataset.json");summary=load(summary_path);audit=load(audit_path);pilot=load(pilot_path);conv=mod(convergence_path)
 if proposal.get("stageId")!=STAGE_ID or source.get("stageId")!=SOURCE_STAGE or source.get("status")!="TIMEOUT_CONTINUATION_ANALYZED":raise ValueError("wrong proposal/source")
 if source.get("computationalReferenceScreeningComplete") is not False or readiness.get("technicalDiagnosisRequiredGeometryIds")!=["g01-reference-bridge"]:raise ValueError("source is not exact g01 precision gap")
 if summary.get("classification")!="BATCH_NUMERICALLY_COMPLETE" or summary.get("caseCountCompleted")!=4 or summary.get("caseCountFailed")!=0 or summary.get("configuredMcPhotonsSum")!=200_000_000:raise ValueError("new aggregate incomplete")
 if audit.get("status")!="PASSED" or audit.get("caseResultCount")!=4:raise ValueError("new independent audit failed")
 old=records(source_preflight_dir/"source-g01");new=records(new_root);validate_rows(old,4,"cgc-g01-alis-r");validate_rows(new,4,"g01pd-alis-b")
 rows=old+new;alis=conv.method_summary([float(r["selectedPhotopicContributionCdM2"]) for r in rows],mean_vector(rows),None)
 source_results={x["groupId"]:x for x in source["geometryResults"]};g01_source=source_results["g01-reference-bridge"];vroom=g01_source["methodStatistics"]["reference-vroom"]
 decision=conv.classify({"reference-vroom":vroom,"alis":alis},{"integratedMeanRatioAlisToVroomClosedInterval":[0.5,2.0],"minimumVroomPhotopicWeightFractionNodeRatioInsideInterval":0.80,"maximumRelativeStandardErrorOfMean":1.0})
 precise=alis["relativeStandardErrorOfMean"]<=0.08 and vroom["relativeStandardErrorOfMean"]<=0.10;compatible=0.5<=decision["meanRatioAlisToVroom"]<=2.0 and decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"]>=0.80;passed=precise and compatible
 classification="G01_FIXED_PRECISION_DIAGNOSIS_PASSED" if passed else ("G01_PERSISTENT_HIGH_VARIANCE" if not precise else "G01_METHOD_DISCREPANCY")
 geometry=next(x for x in pilot["geometries"] if x["geometryId"]=="g01-reference-bridge")
 source_records=dataset.get("records");
 if not isinstance(source_records,list) or len(source_records)!=5:raise ValueError("source dataset not exact five-record set")
 normalized=[]
 for record in source_records:
  rec=json.loads(json.dumps(record));rec["methodStatistics"]={k:normalize_stats(conv,v) for k,v in rec["methodStatistics"].items()};normalized.append(rec)
 g01_record={"groupId":"g01-reference-bridge","geometry":geometry,"methodStatistics":{"reference-vroom":normalize_stats(conv,vroom),"alis":alis},"methodOrigins":{"reference-vroom":"frozen-final-convergence-reference","alis":"preserved-plus-fresh-held-out-precision-continuation"},"meanRatioAlisToVroom":decision["meanRatioAlisToVroom"],"nodeAgreementFraction":decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"]}
 final_records=sorted(normalized+([g01_record] if passed else []),key=lambda x:x["groupId"])
 output={"schemaVersion":1,"stageId":STAGE_ID,"status":"G01_FIXED_PRECISION_EXECUTION_ANALYZED","sourceRunId":proposal["sourceRunId"],"newCaseResultCount":4,"newConfiguredMcPhotonsSum":200_000_000,"preservedHeldOutBlockCount":4,"finalHeldOutBlockCount":8,"classification":classification,"computationalReferenceScreeningComplete":passed,"g01Result":{"classification":classification,"methodStatistics":{"reference-vroom":normalize_stats(conv,vroom),"alis":alis},"meanRatioAlisToVroom":decision["meanRatioAlisToVroom"],"vroomPhotopicWeightFractionNodeRatioInsideInterval":decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"],"nodeMeanRatiosAlisToVroom":decision["nodeMeanRatiosAlisToVroom"],"nextAction":"REFERENCE_DATASET_ELIGIBLE_PENDING_OBSERVATION_VALIDATION" if passed else "TECHNICAL_DIAGNOSIS_REQUIRED_NO_MORE_AUTOMATIC_BLOCKS"},"noAutomaticAdditionalBlocks":True,"screeningOnly":True,"successDoesNotAuthorizeProduction":True,"boundary":"eight independent g01 held-out ALIS blocks; final precision continuation; observation validation remains required"}
 final_readiness={"schemaVersion":1,"status":"COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE" if passed else "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS","computationalReferenceScreeningComplete":passed,"acceptedReferenceGeometryCount":6 if passed else 5,"heldOutConfirmationFailureCount":0 if passed else 1,"technicalDiagnosisRequiredGeometryIds":[] if passed else ["g01-reference-bridge"],"productionModelReady":False,"observationValidationRequired":True,"surrogateTrainingAutomaticallyAuthorized":False,"noAutomaticAdditionalBlocks":True}
 final_dataset={"schemaVersion":1,"status":"AUDITED_COMPUTATIONAL_REFERENCE_DATASET" if passed else "INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET","sourceStageId":STAGE_ID,"screeningOnly":True,"observationValidationRequired":True,"records":final_records}
 output_dir.mkdir(parents=True,exist_ok=True);(output_dir/"g01-fixed-precision-execution-analysis.json").write_text(dump(output));(output_dir/"reference-readiness.json").write_text(dump(final_readiness));(output_dir/"audited-reference-dataset.json").write_text(dump(final_dataset));return output
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--proposal",type=Path,required=True);p.add_argument("--source-analysis-dir",type=Path,required=True);p.add_argument("--source-preflight-dir",type=Path,required=True);p.add_argument("--new-cases-root",type=Path,required=True);p.add_argument("--summary",type=Path,required=True);p.add_argument("--audit",type=Path,required=True);p.add_argument("--convergence-module",type=Path,required=True);p.add_argument("--source-pilot-manifest",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args()
 try:r=analyze(a.proposal,a.source_analysis_dir,a.source_preflight_dir,a.new_cases_root,a.summary,a.audit,a.convergence_module,a.source_pilot_manifest,a.output_dir);print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
