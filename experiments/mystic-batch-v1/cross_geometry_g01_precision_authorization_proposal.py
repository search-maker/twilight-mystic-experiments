#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from typing import Any
STAGE_ID="g01-fixed-precision-diagnosis-execution-v1"
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f"expected object {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def git(root:Path,*args:str)->str:return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def build(root:Path,source_audit:Path,output:Path)->dict[str,Any]:
 base=Path("experiments/mystic-batch-v1");proposal=base/"g01-fixed-diagnostic-execution.proposal.json";audit=load(source_audit)
 if audit.get("status")!="SOURCE_G01_FIXED_PROPOSAL_AUDITED" or audit.get("stageId")!=STAGE_ID:raise ValueError("source audit not eligible")
 paths={"executionAdapter":base/"cross_geometry_g01_precision_execution_adapter.py","executionPlan":base/"cross_geometry_g01_precision_execution_plan.py","analysisDriver":base/"cross_geometry_g01_precision_analysis_driver.py","sourceAuditCode":base/"cross_geometry_g01_precision_source_audit.py","duplicateRunAudit":base/"duplicate_run_audit.py","runtimeProbe":base/"runtime_probe.py","executionWorkflow":Path(".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-continuation.yml"),"runtimeLock":base/"runtime-lock.micromamba.json","executor":base/"scientific_case_executor.py","aggregate":base/"scientific_aggregate.py","audit":base/"scientific_audit.py","convergenceModule":base/"cross_geometry_convergence_v2.py","baseAdapter":base/"cross_geometry_adapter.py","sourcePilotManifest":base/"manifest.cross-geometry-pilot.proposal.json"}
 parent=git(root,"rev-parse","HEAD")
 result={"schemaVersion":1,"stageId":STAGE_ID,"authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"executionKey":"g01-fixed-precision-diagnosis-execution-v1:screening:7","sourceDiagnosisRunId":30876899126,"sourceRunId":30875148389,"proposalRawSha256":raw(root/proposal),"sourceAuditRawSha256":raw(source_audit),"executionAdapterRawSha256":raw(root/paths["executionAdapter"]),"executionPlanRawSha256":raw(root/paths["executionPlan"]),"analysisDriverRawSha256":raw(root/paths["analysisDriver"]),"sourceAuditCodeRawSha256":raw(root/paths["sourceAuditCode"]),"duplicateRunAuditRawSha256":raw(root/paths["duplicateRunAudit"]),"runtimeProbeRawSha256":raw(root/paths["runtimeProbe"]),"executionWorkflowRawSha256":raw(root/paths["executionWorkflow"]),"runtimeLockRawSha256":raw(root/paths["runtimeLock"]),"executorRawSha256":raw(root/paths["executor"]),"aggregateRawSha256":raw(root/paths["aggregate"]),"auditRawSha256":raw(root/paths["audit"]),"convergenceModuleRawSha256":raw(root/paths["convergenceModule"]),"baseAdapterRawSha256":raw(root/paths["baseAdapter"]),"sourcePilotManifestRawSha256":raw(root/paths["sourcePilotManifest"]),"exactAuthorizationParentCommit":parent,"exactAuthorizationCommit":None,"authorizationOrdinal":7,"consumed":False,"note":"One-purpose proposal only. Create a separate one-file authorization commit; do not merge that authorization PR and do not Re-run."}
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(dump(result));return result
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--repository-root",type=Path,required=True);p.add_argument("--source-audit",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 try:r=build(a.repository_root.resolve(),a.source_audit,a.output);print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
