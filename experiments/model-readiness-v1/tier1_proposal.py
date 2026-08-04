#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any
STAGE_ID="twilight-surrogate-tier-1-proposal-v1";TIER_ID="tier-1-provisional"
SOURCE_STAGE_ID="cross-geometry-held-out-confirmation-timeout-continuation-v1"
SOURCE_ARTIFACT="cross-geometry-timeout-continuation-v1-analysis"
SOURCE_PROFILES={
 "cross-geometry-held-out-confirmation-timeout-continuation-v1":{"status":"TIMEOUT_CONTINUATION_ANALYZED","artifact":"cross-geometry-timeout-continuation-v1-analysis","workflowName":"MYSTIC held-out timeout continuation v1 scientific execution","workflowPath":".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml"},
 "g01-fixed-precision-diagnosis-execution-v1":{"status":"G01_FIXED_PRECISION_EXECUTION_ANALYZED","artifact":"g01-fixed-precision-diagnosis-execution-v1-analysis","workflowName":"MYSTIC g01 fixed precision diagnosis execution v1","workflowPath":".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-continuation.yml"},
}
class ProposalError(RuntimeError):pass
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ProposalError(f"expected JSON object: {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw_sha256(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def load_module(name:str,path:Path):
 s=importlib.util.spec_from_file_location(name,path)
 if s is None or s.loader is None:raise ProposalError(f"cannot load module: {path}")
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def validate_source(analysis:dict[str,Any],source_run:dict[str,Any],source_artifacts:dict[str,Any])->dict[str,Any]:
 stage=analysis.get("stageId");profile=SOURCE_PROFILES.get(stage)
 if profile is None:raise ProposalError(f"unsupported source stage: {stage}")
 required_analysis={"schemaVersion":1,"stageId":stage,"status":profile["status"],"computationalReferenceScreeningComplete":True,"noAutomaticAdditionalBlocks":True,"screeningOnly":True,"successDoesNotAuthorizeProduction":True}
 stale={k:(analysis.get(k),v) for k,v in required_analysis.items() if analysis.get(k)!=v}
 if stale:raise ProposalError(f"source analysis is not complete and eligible: {stale}")
 required_run={"status":"completed","conclusion":"success","event":"workflow_dispatch","run_attempt":1,"head_branch":"main","name":profile["workflowName"],"path":profile["workflowPath"]}
 stale={k:(source_run.get(k),v) for k,v in required_run.items() if source_run.get(k)!=v}
 if stale:raise ProposalError(f"source run boundary changed: {stale}")
 run_id=source_run.get("id");head_sha=source_run.get("head_sha")
 if not isinstance(run_id,int) or run_id<1 or not isinstance(head_sha,str) or len(head_sha)!=40:raise ProposalError("source run identity invalid")
 artifacts=source_artifacts.get("artifacts")
 if not isinstance(artifacts,list):raise ProposalError("source artifact list missing")
 matches=[x for x in artifacts if isinstance(x,dict) and x.get("name")==profile["artifact"]]
 if len(matches)!=1:raise ProposalError(f"expected one source analysis artifact, found {len(matches)}")
 artifact=matches[0];digest=artifact.get("digest");artifact_id=artifact.get("id")
 if artifact.get("expired") is not False or not isinstance(digest,str) or not digest.startswith("sha256:") or len(digest)!=71 or not isinstance(artifact_id,int) or artifact_id<1:raise ProposalError("source artifact invalid")
 workflow_run=artifact.get("workflow_run")
 if isinstance(workflow_run,dict) and workflow_run.get("id") not in (None,run_id):raise ProposalError("source artifact belongs to another run")
 return {"runId":run_id,"headSha":head_sha,"stageId":stage,"artifactId":artifact_id,"artifactName":profile["artifact"],"artifactDigest":digest}
def build(dataset_path:Path,readiness_path:Path,analysis_path:Path,source_run_path:Path,source_artifacts_path:Path,reference_contract_path:Path,training_design_code_path:Path,training_design_spec_path:Path,importance_policy_path:Path):
 dataset=load(dataset_path);readiness=load(readiness_path);analysis=load(analysis_path);source=validate_source(analysis,load(source_run_path),load(source_artifacts_path))
 reference_contract=load_module("reference_dataset_contract",reference_contract_path);training_design=load_module("training_design",training_design_code_path);anchors=reference_contract.validate(dataset,readiness);full_design=training_design.build(training_design.load(training_design_spec_path),importance_policy_path)
 if anchors.get("status")!="REFERENCE_ANCHORS_VALIDATED" or anchors.get("anchorCount")!=6 or anchors.get("trainingAutomaticallyAuthorized") is not False:raise ProposalError("reference anchors not valid")
 tiers=full_design.get("executionTiers");matches=[x for x in tiers if isinstance(x,dict) and x.get("tierId")==TIER_ID] if isinstance(tiers,list) else []
 if len(matches)!=1:raise ProposalError("tier-1 summary missing/duplicated")
 tier=matches[0];geometry_ids=tier.get("geometryIds");case_ids=tier.get("caseIds")
 if not isinstance(geometry_ids,list) or not isinstance(case_ids,list):raise ProposalError("tier-1 IDs missing")
 gs=set(geometry_ids);cs=set(case_ids);geometries=[x for x in full_design.get("geometries",[]) if x.get("geometryId") in gs];cases=[x for x in full_design.get("cases",[]) if x.get("caseId") in cs]
 if len(geometries)!=48 or len(cases)!=96:raise ProposalError(f"tier-1 size changed: {len(geometries)} geometries, {len(cases)} cases")
 if {x.get("geometryId") for x in geometries}!=gs or {x.get("caseId") for x in cases}!=cs or any(x.get("executionTierId")!=TIER_ID for x in geometries+cases):raise ProposalError("tier selection mismatch")
 photon_sum=sum(int(x.get("photonHistories",-1)) for x in cases)
 if photon_sum!=tier.get("configuredMcPhotonsSum") or photon_sum!=6_960_000_000:raise ProposalError(f"tier-1 photon sum changed: {photon_sum}")
 if [x.get("ordinal") for x in cases]!=list(range(1,97)) or len({x.get("seed") for x in cases})!=96:raise ProposalError("tier-1 ordinals/seeds changed")
 anchor_ids=sorted(x["groupId"] for x in anchors["anchors"])
 if anchor_ids!=sorted(full_design.get("externalValidationAnchorIds",[])):raise ProposalError("anchor IDs differ from frozen design")
 training_ids=[x for x in full_design.get("trainingGeometryIds",[]) if x in gs];holdout_ids=[x for x in full_design.get("internalHoldoutGeometryIds",[]) if x in gs]
 if set(training_ids)&set(holdout_ids) or set(training_ids)|set(holdout_ids)!=gs:raise ProposalError("training/holdout partition invalid")
 bindings={"sourceAnalysisRawSha256":raw_sha256(analysis_path),"sourceDatasetRawSha256":raw_sha256(dataset_path),"sourceReadinessRawSha256":raw_sha256(readiness_path),"referenceContractRawSha256":raw_sha256(reference_contract_path),"trainingDesignCodeRawSha256":raw_sha256(training_design_code_path),"trainingDesignSpecRawSha256":raw_sha256(training_design_spec_path),"importancePolicyRawSha256":raw_sha256(importance_policy_path)}
 proposal={"schemaVersion":1,"stageId":STAGE_ID,"batchId":"twilight-surrogate-space-filling-v1-tier-1","status":"PROPOSAL_ONLY_NOT_AUTHORIZATION","mode":"scientific-proposal","proposalOnly":True,"scientificExecution":False,"successDoesNotAuthorizeProduction":True,"observationValidationRequired":True,"authorizationRequired":True,"source":source,"bindings":bindings,"executionTierId":TIER_ID,"purpose":tier.get("purpose"),"geometryCount":48,"caseCount":96,"configuredMcPhotonsSum":photon_sum,"method":"alis","blocksPerGeometry":full_design.get("blocksPerGeometry"),"sampling":full_design.get("sampling"),"importanceSamplingPolicy":full_design.get("importanceSamplingPolicy"),"parameterRanges":full_design.get("parameterRanges"),"photonSchedule":full_design.get("photonSchedule"),"trainingGeometryIds":training_ids,"internalHoldoutGeometryIds":holdout_ids,"externalValidationAnchorIds":anchor_ids,"geometries":geometries,"cases":cases,"adaptiveContinuation":full_design.get("adaptiveContinuation"),"surrogateTrainingAutomaticallyAuthorized":False,"productionModelReady":False,"boundary":"tier-1 proposal only; six computational anchors are excluded from fitting; separate one-purpose authorization and observation validation remain required"}
 tier_readiness={"schemaVersion":1,"stageId":STAGE_ID,"status":"TIER_1_PROPOSAL_READY_PENDING_SEPARATE_AUTHORIZATION","referenceAnchorCount":6,"geometryCount":48,"caseCount":96,"configuredMcPhotonsSum":photon_sum,"scientificExecution":False,"executionAuthorized":False,"surrogateTrainingAuthorized":False,"productionModelReady":False,"observationValidationRequired":True,"sourceRunId":source["runId"],"sourceArtifactDigest":source["artifactDigest"]}
 return anchors,proposal,tier_readiness
def main()->int:
 p=argparse.ArgumentParser()
 for name in ("dataset","readiness","analysis","source-run","source-artifacts","reference-contract","training-design-code","training-design-spec","importance-policy","output-dir"):p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args()
 try:
  anchors,proposal,readiness=build(a.dataset,a.readiness,a.analysis,a.source_run,a.source_artifacts,a.reference_contract,a.training_design_code,a.training_design_spec,a.importance_policy);a.output_dir.mkdir(parents=True,exist_ok=True);(a.output_dir/"validated-reference-anchors.json").write_text(dump(anchors));(a.output_dir/"tier-1-scientific-proposal.json").write_text(dump(proposal));(a.output_dir/"tier-1-readiness.json").write_text(dump(readiness));print(dump(readiness),end="");return 0
 except Exception as e:print(dump({"schemaVersion":1,"stageId":STAGE_ID,"status":"REFUSED","reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
