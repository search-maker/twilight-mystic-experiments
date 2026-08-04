#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-held-out-confirmation-timeout-continuation-v1";ORDINAL=6;KEY=STAGE_ID+":screening:6";SOURCE_RUN=30871800549
BASE=Path("experiments/mystic-batch-v1")
PATHS={"authorization":BASE/"authorization.cross-geometry-timeout-continuation.json","template":BASE/"authorization.cross-geometry-timeout-continuation-template.json","proposal":BASE/"cross-geometry-confirmation-timeout-continuation.proposal.json","executionAdapter":BASE/"cross_geometry_confirmation_timeout_execution_adapter.py","executionPlan":BASE/"cross_geometry_confirmation_timeout_execution_plan.py","analysisDriver":BASE/"cross_geometry_confirmation_timeout_analysis_driver.py","sourceAuditCode":BASE/"cross_geometry_confirmation_timeout_source_audit.py","duplicateRunAudit":BASE/"duplicate_run_audit.py","runtimeProbe":BASE/"runtime_probe.py","executionWorkflow":Path(".github/workflows/mystic-batch-v1-cross-geometry-confirmation-timeout-continuation.yml"),"runtimeLock":BASE/"runtime-lock.micromamba.json","executor":BASE/"scientific_case_executor.py","aggregate":BASE/"scientific_aggregate.py","audit":BASE/"scientific_audit.py","convergenceModule":BASE/"cross_geometry_convergence_v2.py","baseAdapter":BASE/"cross_geometry_adapter.py","sourcePilotManifest":BASE/"manifest.cross-geometry-pilot.proposal.json"}
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f"expected object {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def git(root:Path,*args:str)->str:return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def build(root:Path,source_audit_path:Path)->dict[str,Any]:
 root=root.resolve();abs={k:root/v for k,v in PATHS.items()};
 for k,p in abs.items():
  if not p.is_file():raise ValueError(f"missing {k}: {p}")
 a,t,p,s=load(abs["authorization"]),load(abs["template"]),load(abs["proposal"]),load(source_audit_path)
 if a!=t or a.get("authorized") is not False:raise ValueError("active authorization is not disabled template")
 if p.get("stageId")!=STAGE_ID or p.get("sourceFailedRunId")!=SOURCE_RUN or s.get("status")!="SOURCE_TIMEOUT_FAILURE_AUDITED":raise ValueError("wrong proposal/source audit")
 head=git(root,"rev-parse","HEAD")
 auth={"schemaVersion":1,"stageId":STAGE_ID,"authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"executionKey":KEY,"sourceFailedRunId":SOURCE_RUN,"proposalRawSha256":raw(abs["proposal"]),"sourceAuditRawSha256":raw(source_audit_path),"executionAdapterRawSha256":raw(abs["executionAdapter"]),"executionPlanRawSha256":raw(abs["executionPlan"]),"analysisDriverRawSha256":raw(abs["analysisDriver"]),"sourceAuditCodeRawSha256":raw(abs["sourceAuditCode"]),"duplicateRunAuditRawSha256":raw(abs["duplicateRunAudit"]),"runtimeProbeRawSha256":raw(abs["runtimeProbe"]),"executionWorkflowRawSha256":raw(abs["executionWorkflow"]),"runtimeLockRawSha256":raw(abs["runtimeLock"]),"executorRawSha256":raw(abs["executor"]),"aggregateRawSha256":raw(abs["aggregate"]),"auditRawSha256":raw(abs["audit"]),"convergenceModuleRawSha256":raw(abs["convergenceModule"]),"baseAdapterRawSha256":raw(abs["baseAdapter"]),"sourcePilotManifestRawSha256":raw(abs["sourcePilotManifest"]),"exactAuthorizationParentCommit":head,"exactAuthorizationCommit":None,"authorizationOrdinal":ORDINAL,"consumed":False,"note":"One-purpose timeout continuation: preserve g01, execute eight fresh 200M g06 subblocks; no Re-run or production authorization."}
 if set(auth)!=set(t):raise ValueError("authorization schema changed")
 return {"schemaVersion":1,"stageId":STAGE_ID,"status":"PROPOSAL_ONLY_NOT_AUTHORIZATION","sourceCommit":head,"sourceFailedRunId":SOURCE_RUN,"authorizationOrdinal":ORDINAL,"executionKey":KEY,"caseCount":8,"configuredMcPhotonsSum":1600000000,"authorization":auth,"boundary":"proposal artifact only; later one-purpose authorization commit and manual dispatch required"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--repository-root",type=Path,required=True);p.add_argument("--source-audit",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 try:r=build(a.repository_root,a.source_audit);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r));print(dump({k:r[k] for k in ("status","sourceFailedRunId","authorizationOrdinal","executionKey","caseCount","configuredMcPhotonsSum")}),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
