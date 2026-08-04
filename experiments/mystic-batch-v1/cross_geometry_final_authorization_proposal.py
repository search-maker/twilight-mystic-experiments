#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-final-convergence-v1"; ORDINAL=4; EXECUTION_KEY=f"{STAGE_ID}:screening:{ORDINAL}"; PKG=Path("experiments/mystic-batch-v1")
PATHS={"authorization":PKG/"authorization.cross-geometry-final.json","authorizationTemplate":PKG/"authorization.cross-geometry-final-execution-template.json","proposal":PKG/"manifest.cross-geometry-final-convergence.proposal.json","sourceScreening":PKG/"results/screening-analysis.cross-geometry-stage-two-3.json","sourceConvergence":PKG/"results/convergence-v2.cross-geometry-stage-two-3.json","sourceProvenance":PKG/"results/final-convergence-source-provenance.json","baseAdapter":PKG/"cross_geometry_adapter.py","executionAdapter":PKG/"cross_geometry_final_execution_adapter.py","duplicateRunAudit":PKG/"duplicate_run_audit.py","runtimeProbe":PKG/"runtime_probe.py","executionWorkflow":Path(".github/workflows/mystic-batch-v1-cross-geometry-final-execution.yml"),"runtimeLock":PKG/"runtime-lock.micromamba.json","plan":PKG/"cross_geometry_final_execution_plan.py","analysisDriver":PKG/"cross_geometry_final_analysis_driver.py","convergenceModule":PKG/"cross_geometry_convergence_v2.py","executor":PKG/"scientific_case_executor.py","aggregate":PKG/"scientific_aggregate.py","audit":PKG/"scientific_audit.py"}
def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text())
    if not isinstance(v,dict):raise ValueError(f"expected object: {p}")
    return v
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def git(root:Path,*args:str)->str:return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def build(root:Path)->dict[str,Any]:
    root=root.resolve();a={k:root/v for k,v in PATHS.items()}
    for k,p in a.items():
        if not p.is_file():raise ValueError(f"missing {k}: {p}")
    active,tmpl=load(a["authorization"]),load(a["authorizationTemplate"])
    if active!=tmpl or active.get("authorized") is not False or active.get("authorizationOrdinal")!=0:raise ValueError("active authorization is not exactly disabled")
    p=load(a["proposal"])
    if p.get("stageId")!=STAGE_ID or p.get("proposalOnly") is not True or len(p.get("cases",[]))!=26:raise ValueError("proposal boundary changed")
    source=git(root,"rev-parse","HEAD")
    auth={**tmpl,"authorized":True,"scientificExecution":True,"scientificDiagnostic":True,"executionKey":EXECUTION_KEY,"batchId":p["batchId"],"proposalPath":PATHS["proposal"].as_posix(),"proposalRawSha256":sha(a["proposal"]),"sourceScreeningRawSha256":sha(a["sourceScreening"]),"sourceConvergenceV2RawSha256":sha(a["sourceConvergence"]),"sourceProvenanceRawSha256":sha(a["sourceProvenance"]),"authorizationTemplateRawSha256":sha(a["authorizationTemplate"]),"baseAdapterRawSha256":sha(a["baseAdapter"]),"executionAdapterRawSha256":sha(a["executionAdapter"]),"duplicateRunAuditRawSha256":sha(a["duplicateRunAudit"]),"runtimeProbeRawSha256":sha(a["runtimeProbe"]),"executionWorkflowRawSha256":sha(a["executionWorkflow"]),"runtimeLockRawSha256":sha(a["runtimeLock"]),"planRawSha256":sha(a["plan"]),"analysisDriverRawSha256":sha(a["analysisDriver"]),"convergenceModuleRawSha256":sha(a["convergenceModule"]),"executorRawSha256":sha(a["executor"]),"aggregateRawSha256":sha(a["aggregate"]),"auditRawSha256":sha(a["audit"]),"exactAuthorizationParentCommit":source,"exactAuthorizationCommit":None,"authorizationOrdinal":ORDINAL,"consumed":False,"note":"Proposal only. A later one-purpose commit may replace only authorization.cross-geometry-final.json; a separate reviewed manual dispatch is required."}
    return {"schemaVersion":1,"stageId":STAGE_ID,"status":"PROPOSAL_ONLY_NOT_AUTHORIZATION","executionAuthorizedByProposal":False,"sourceCommit":source,"executionKey":EXECUTION_KEY,"authorizationOrdinal":ORDINAL,"caseCount":26,"configuredMcPhotonsSum":520_000_000,"proposedAuthorization":auth,"boundary":"computes exact authorization JSON only; no syntax check, solver, or dispatch"}
def main()->int:
    q=argparse.ArgumentParser();q.add_argument("--repository-root",type=Path,default=Path("."));q.add_argument("--output",type=Path,required=True);x=q.parse_args()
    try:r=build(x.repository_root);x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(dump(r));print(dump(r),end="");return 0
    except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),end="",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
