#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
from typing import Any
STAGE_ID="g01-fixed-precision-diagnosis-execution-v1";SOURCE_RUN_ID=30875148389;SHA=re.compile(r"^[0-9a-f]{64}$")
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f"expected object {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def git(root:Path,*args:str)->str:return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def validate(root:Path,auth_path:Path,template_path:Path,proposal_path:Path,source_audit_path:Path,paths:dict[str,Path],authorization_ref:str,execution_key:str,ordinal:int,require_context:bool=True,require_one_purpose:bool=True)->dict[str,Any]:
 if require_context:
  expected={"GITHUB_ACTIONS":"true","GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_RUN_ATTEMPT":"1"};stale={k:(os.getenv(k),v) for k,v in expected.items() if os.getenv(k)!=v}
  if stale:raise ValueError(f"wrong GitHub context {stale}")
 a,t,p,s=map(load,(root/auth_path,root/template_path,root/proposal_path,source_audit_path))
 if a.keys()!=t.keys():raise ValueError("authorization schema differs")
 if t.get("authorized") is not False or t.get("authorizationOrdinal")!=0:raise ValueError("template not disabled")
 if p.get("stageId")!=STAGE_ID or s.get("status")!="SOURCE_G01_FIXED_PROPOSAL_AUDITED" or s.get("sourceRunId")!=SOURCE_RUN_ID:raise ValueError("source audit/proposal invalid")
 expected={"schemaVersion":1,"stageId":STAGE_ID,"authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"executionKey":execution_key,"sourceDiagnosisRunId":30876899126,"sourceRunId":SOURCE_RUN_ID,"proposalRawSha256":raw(root/proposal_path),"sourceAuditRawSha256":raw(source_audit_path),"executionAdapterRawSha256":raw(root/paths["executionAdapter"]),"executionPlanRawSha256":raw(root/paths["executionPlan"]),"analysisDriverRawSha256":raw(root/paths["analysisDriver"]),"sourceAuditCodeRawSha256":raw(root/paths["sourceAuditCode"]),"duplicateRunAuditRawSha256":raw(root/paths["duplicateRunAudit"]),"runtimeProbeRawSha256":raw(root/paths["runtimeProbe"]),"executionWorkflowRawSha256":raw(root/paths["executionWorkflow"]),"runtimeLockRawSha256":raw(root/paths["runtimeLock"]),"executorRawSha256":raw(root/paths["executor"]),"aggregateRawSha256":raw(root/paths["aggregate"]),"auditRawSha256":raw(root/paths["audit"]),"convergenceModuleRawSha256":raw(root/paths["convergenceModule"]),"baseAdapterRawSha256":raw(root/paths["baseAdapter"]),"sourcePilotManifestRawSha256":raw(root/paths["sourcePilotManifest"]),"authorizationOrdinal":ordinal,"consumed":False,"exactAuthorizationCommit":None}
 for k,v in expected.items():
  if a.get(k)!=v:raise ValueError(f"authorization stale {k}: {a.get(k)} != {v}")
 for k,v in expected.items():
  if k.endswith("RawSha256") and (not isinstance(v,str) or not SHA.fullmatch(v)):raise ValueError(f"invalid hash {k}")
 head=git(root,"rev-parse","HEAD");parent=git(root,"rev-parse","HEAD^")
 if head!=authorization_ref or a.get("exactAuthorizationParentCommit")!=parent:raise ValueError("authorization ref/parent mismatch")
 if require_one_purpose:
  changed=git(root,"diff","--name-only",parent,head).splitlines()
  if changed!=[auth_path.as_posix()]:raise ValueError(f"authorization commit not one-purpose: {changed}")
 return {"schemaVersion":1,"stageId":STAGE_ID,"status":"AUTHORIZED","sourceDiagnosisRunId":30876899126,"sourceRunId":SOURCE_RUN_ID,"executionKey":execution_key,"authorizationRef":head,"authorizationParentCommit":parent,"authorizationOrdinal":ordinal,"manifestRawSha256":raw(root/proposal_path),"caseCount":4,"configuredMcPhotonsSum":200_000_000,"boundary":"four fresh g01 50M blocks after audited precision-only gap; no retry and no automatic further blocks"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--repository-root",type=Path,required=True);p.add_argument("--authorization",type=Path,required=True);p.add_argument("--authorization-template",type=Path,required=True);p.add_argument("--proposal",type=Path,required=True);p.add_argument("--source-audit",type=Path,required=True);p.add_argument("--authorization-ref",required=True);p.add_argument("--execution-key",required=True);p.add_argument("--authorization-ordinal",type=int,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();root=a.repository_root.resolve();base=Path("experiments/mystic-batch-v1");paths={"executionAdapter":base/"cross_geometry_g01_precision_execution_adapter.py","executionPlan":base/"cross_geometry_g01_precision_execution_plan.py","analysisDriver":base/"cross_geometry_g01_precision_analysis_driver.py","sourceAuditCode":base/"cross_geometry_g01_precision_source_audit.py","duplicateRunAudit":base/"duplicate_run_audit.py","runtimeProbe":base/"runtime_probe.py","executionWorkflow":Path(".github/workflows/mystic-batch-v1-cross-geometry-g01-precision-continuation.yml"),"runtimeLock":base/"runtime-lock.micromamba.json","executor":base/"scientific_case_executor.py","aggregate":base/"scientific_aggregate.py","audit":base/"scientific_audit.py","convergenceModule":base/"cross_geometry_convergence_v2.py","baseAdapter":base/"cross_geometry_adapter.py","sourcePilotManifest":base/"manifest.cross-geometry-pilot.proposal.json"}
 try:r=validate(root,a.authorization,a.authorization_template,a.proposal,a.source_audit,paths,a.authorization_ref,a.execution_key,a.authorization_ordinal);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r));print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED_BEFORE_SYNTAX_OR_SOLVER","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
