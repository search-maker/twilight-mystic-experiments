#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-final-convergence-v1"

def load(p:Path)->dict[str,Any]:
    v=json.loads(p.read_text())
    if not isinstance(v,dict): raise ValueError("expected JSON object")
    return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def compact(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False)
def build_plan(proposal_path:Path,guard_path:Path)->dict[str,Any]:
    p,g=load(proposal_path),load(guard_path)
    if g.get("status")!="AUTHORIZED" or g.get("stageId")!=STAGE_ID: raise ValueError("guard did not pass")
    if p.get("stageId")!=STAGE_ID or p.get("batchId")!=g.get("batchId"): raise ValueError("proposal/guard mismatch")
    ordered=sorted(p["cases"],key=lambda c:c["ordinal"]); limits=p["limits"]
    matrix={"include":[{"case_id":c["caseId"],"ordinal":c["ordinal"],"seed":c["seed"],"photon_histories":c["photonHistories"],"group_id":c["groupId"],"method":c["method"],"block":c["block"],"purpose":c["purpose"],"alis_reference_nm":c.get("alisSpectralImportanceSamplingNm",0)} for c in ordered]}
    return {"schemaVersion":1,"stageId":"mystic-batch-v1","scientificPurpose":STAGE_ID,"batchId":p["batchId"],"mode":"scientific","scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"manifestPath":str(proposal_path),"manifestRawSha256":g["proposalRawSha256"],"scientificAdapterRawSha256":g["executionAdapterRawSha256"],"runtimeLockRawSha256":g["runtimeLockRawSha256"],"executionWorkflowRawSha256":g["executionWorkflowRawSha256"],"authorizationRef":g["authorizationRef"],"authorizationOrdinal":g["authorizationOrdinal"],"executionKey":g["executionKey"],"sourceScreeningRawSha256":g["sourceScreeningRawSha256"],"sourceConvergenceV2RawSha256":g["sourceConvergenceV2RawSha256"],"sourceProvenanceRawSha256":g["sourceProvenanceRawSha256"],"caseCount":len(ordered),"maximumParallel":limits["maximumParallel"],"perCaseTimeoutSeconds":limits["perCaseTimeoutSeconds"],"configuredMcPhotonsSum":sum(c["photonHistories"] for c in ordered),"cases":ordered,"matrix":matrix,"boundary":"exact bounded final-convergence matrix; no syntax or solver executed by planning"}
def main()->int:
    a=argparse.ArgumentParser();a.add_argument("--proposal",type=Path,required=True);a.add_argument("--guard-report",type=Path,required=True);a.add_argument("--output",type=Path,required=True);a.add_argument("--github-output",type=Path);x=a.parse_args()
    try:
        p=build_plan(x.proposal,x.guard_report);x.output.parent.mkdir(parents=True,exist_ok=True);x.output.write_text(dump(p))
        if x.github_output:
            with x.github_output.open("a") as h:
                h.write(f"matrix={compact(p['matrix'])}\nmax_parallel={p['maximumParallel']}\ncase_count={p['caseCount']}\ntimeout_seconds={p['perCaseTimeoutSeconds']}\n")
        print(dump({"status":"PLANNED","stageId":STAGE_ID,"caseCount":p["caseCount"]}),end="");return 0
    except Exception as e: print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),end="",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
