#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-held-out-confirmation-timeout-continuation-v1"; METHODS=("reference-vroom","alis")
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f"expected object {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def mod(p:Path):
 s=importlib.util.spec_from_file_location("conv",p)
 if s is None or s.loader is None:raise ValueError("cannot load convergence")
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def records(root:Path)->list[dict[str,Any]]:return [load(p) for p in sorted(root.rglob("case-result.json"))]
def mean_vector(rows:list[dict[str,Any]])->list[float]:return [sum(float(r["selectedNodeRadiance"][i]) for r in rows)/len(rows) for i in range(15)]
def source_summary(item:dict[str,Any],method:str)->dict[str,Any]:
 group=item["groupId"]
 if group in {"g01-reference-bridge","g06-late-opposite-high-aerosol"}:
  if method=="reference-vroom":s=item.get("vroomStatistics")
  else:
   selected=item.get("selectedAlisReferenceNm");matches=[x for x in item.get("candidateAlisReferences",[]) if x.get("referenceNm")==selected];s=matches[0].get("alisStatistics") if len(matches)==1 else None
 else:s=item.get("methodStatistics",{}).get(method)
 if not isinstance(s,dict):raise ValueError(f"source summary missing {group} {method}")
 return s
def validate_case_rows(rows:list[dict[str,Any]],expected_count:int,group:str)->None:
 if len(rows)!=expected_count:raise ValueError(f"expected {expected_count} {group} rows, found {len(rows)}")
 for r in rows:
  if r.get("status")!="COMPLETED" or r.get("solver",{}).get("exitCode")!=0 or r.get("solver",{}).get("timedOut") is not False or r.get("syntax",{}).get("exitCode")!=0:raise ValueError(f"incomplete case {r.get('caseId')}")
  value=r.get("selectedPhotopicContributionCdM2")
  if not isinstance(value,(int,float)) or not math.isfinite(float(value)) or value<=0 or len(r.get("selectedNodeRadiance",[]))!=15:raise ValueError(f"invalid case output {r.get('caseId')}")
def analyze(proposal_path:Path,source_final_path:Path,source_pilot_path:Path,source_g01_root:Path,new_root:Path,summary_path:Path,audit_path:Path,convergence_path:Path,output_dir:Path)->dict[str,Any]:
 proposal,source,pilot,summary,audit=map(load,(proposal_path,source_final_path,source_pilot_path,summary_path,audit_path));conv=mod(convergence_path)
 if proposal.get("stageId")!=STAGE_ID or source.get("status")!="FINAL_CONVERGENCE_ANALYZED":raise ValueError("wrong source/proposal")
 if summary.get("classification")!="BATCH_NUMERICALLY_COMPLETE" or summary.get("caseCountCompleted")!=8 or summary.get("caseCountFailed")!=0 or summary.get("configuredMcPhotonsSum")!=1600000000:raise ValueError("new aggregate incomplete")
 if audit.get("status")!="PASSED" or audit.get("caseResultCount")!=8:raise ValueError("new independent audit failed")
 g01=records(source_g01_root);g06=records(new_root);validate_case_rows(g01,4,"g01");validate_case_rows(g06,8,"g06")
 source_results={x["groupId"]:x for x in source["geometryResults"]};geometry_map={x["geometryId"]:x for x in pilot["geometries"]}
 accepted=[];results=[]
 for group,rows in (("g01-reference-bridge",g01),("g06-late-opposite-high-aerosol",g06)):
  alis=conv.method_summary([float(r["selectedPhotopicContributionCdM2"]) for r in rows],mean_vector(rows),None);vroom=source_summary(source_results[group],"reference-vroom");decision=conv.classify({"reference-vroom":vroom,"alis":alis},{"integratedMeanRatioAlisToVroomClosedInterval":[0.5,2.0],"minimumVroomPhotopicWeightFractionNodeRatioInsideInterval":0.80,"maximumRelativeStandardErrorOfMean":1.0});precise=alis["relativeStandardErrorOfMean"]<=0.08 and vroom["relativeStandardErrorOfMean"]<=0.10;compatible=0.5<=decision["meanRatioAlisToVroom"]<=2.0 and decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"]>=0.80;classification="HELD_OUT_CONFIRMATION_PASSED" if precise and compatible else ("HELD_OUT_CONFIRMATION_INCONCLUSIVE_PRECISION_CAP_REACHED" if not precise else "HELD_OUT_CONFIRMATION_DISCREPANCY");result={"groupId":group,"classification":classification,"heldOutBlockCount":len(rows),"methodStatistics":{"reference-vroom":vroom,"alis":alis},"methodOrigins":{"reference-vroom":"frozen-final-convergence-reference","alis":"preserved-held-out-confirmation" if group.startswith("g01") else "fresh-timeout-continuation"},"meanRatioAlisToVroom":decision["meanRatioAlisToVroom"],"vroomPhotopicWeightFractionNodeRatioInsideInterval":decision["vroomPhotopicWeightFractionNodeRatioInsideInterval"],"nodeMeanRatiosAlisToVroom":decision["nodeMeanRatiosAlisToVroom"],"nextAction":"REFERENCE_DATASET_ELIGIBLE_PENDING_OBSERVATION_VALIDATION" if classification.endswith("PASSED") else "TECHNICAL_DIAGNOSIS_REQUIRED_NO_AUTOMATIC_MORE_BLOCKS"};results.append(result)
  if classification.endswith("PASSED"):accepted.append({"groupId":group,"geometry":geometry_map[group],"methodStatistics":result["methodStatistics"],"methodOrigins":result["methodOrigins"],"meanRatioAlisToVroom":result["meanRatioAlisToVroom"],"nodeAgreementFraction":result["vroomPhotopicWeightFractionNodeRatioInsideInterval"]})
 carried=[]
 for group,item in sorted(source_results.items()):
  if group in {"g01-reference-bridge","g06-late-opposite-high-aerosol"}:continue
  if item.get("classification")!="SCREENING_AGREEMENT":raise ValueError(f"carried geometry not agreement {group}")
  carried.append({"groupId":group,"geometry":geometry_map[group],"methodStatistics":item["methodStatistics"],"methodOrigins":{m:"frozen-final-convergence-screening" for m in METHODS},"meanRatioAlisToVroom":item["meanRatioAlisToVroom"],"nodeAgreementFraction":item["vroomPhotopicWeightFractionNodeRatioInsideInterval"],"sourceClassification":"SCREENING_AGREEMENT"})
 complete=len(accepted)==2 and not source.get("technicalDiagnosisRequiredGeometryIds") and len(carried)==4
 counts={}
 for r in results:counts[r["classification"]]=counts.get(r["classification"],0)+1
 output={"schemaVersion":1,"stageId":STAGE_ID,"status":"TIMEOUT_CONTINUATION_ANALYZED","sourceFailedRunId":30871800549,"newCaseResultCount":8,"newConfiguredMcPhotonsSum":1600000000,"preservedG01CaseResultCount":4,"geometryResults":results,"classificationCounts":counts,"computationalReferenceScreeningComplete":complete,"noAutomaticAdditionalBlocks":True,"screeningOnly":True,"successDoesNotAuthorizeProduction":True,"boundary":"preserved g01 plus fresh g06 timeout continuation; observation validation remains required"}
 readiness={"schemaVersion":1,"status":"COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE" if complete else "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS","computationalReferenceScreeningComplete":complete,"acceptedReferenceGeometryCount":len(carried)+len(accepted),"heldOutConfirmationFailureCount":2-len(accepted),"technicalDiagnosisRequiredGeometryIds":[r["groupId"] for r in results if not r["classification"].endswith("PASSED")],"productionModelReady":False,"observationValidationRequired":True,"surrogateTrainingAutomaticallyAuthorized":False,"noAutomaticAdditionalBlocks":True}
 dataset={"schemaVersion":1,"status":"AUDITED_COMPUTATIONAL_REFERENCE_DATASET" if complete else "INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET","sourceStageId":STAGE_ID,"screeningOnly":True,"observationValidationRequired":True,"records":carried+accepted}
 output_dir.mkdir(parents=True,exist_ok=True);(output_dir/"timeout-continuation-analysis.json").write_text(dump(output));(output_dir/"reference-readiness.json").write_text(dump(readiness));(output_dir/"audited-reference-dataset.json").write_text(dump(dataset));return output
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--proposal",type=Path,required=True);p.add_argument("--source-final-analysis",type=Path,required=True);p.add_argument("--source-pilot-manifest",type=Path,required=True);p.add_argument("--source-g01-root",type=Path,required=True);p.add_argument("--new-cases-root",type=Path,required=True);p.add_argument("--summary",type=Path,required=True);p.add_argument("--audit",type=Path,required=True);p.add_argument("--convergence-module",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args()
 try:r=analyze(a.proposal,a.source_final_analysis,a.source_pilot_manifest,a.source_g01_root,a.new_cases_root,a.summary,a.audit,a.convergence_module,a.output_dir);print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
