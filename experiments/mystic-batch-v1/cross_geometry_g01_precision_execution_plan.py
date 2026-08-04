#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
STAGE_ID="g01-fixed-precision-diagnosis-execution-v1"
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict):raise ValueError(f"expected object {p}")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def build(manifest:dict[str,Any],guard:dict[str,Any])->dict[str,Any]:
 if manifest.get("stageId")!=STAGE_ID or guard.get("status")!="AUTHORIZED" or guard.get("stageId")!=STAGE_ID:raise ValueError("manifest/guard mismatch")
 cases=manifest.get("cases");limits=manifest.get("limits",{})
 if not isinstance(cases,list) or len(cases)!=4 or sum(x.get("photonHistories",0) for x in cases)!=200_000_000:raise ValueError("case count/photon sum changed")
 expected_limits={"maximumCases":4,"maximumParallel":4,"maximumConfiguredMcPhotonsSum":200_000_000,"maximumPhotonHistoriesPerBlock":50_000_000,"perCaseTimeoutSeconds":900}
 if limits!=expected_limits:raise ValueError(f"limits changed: {limits}")
 matrix={"include":[{"case_id":x["caseId"],"ordinal":x["ordinal"],"seed":x["seed"],"block":x["block"],"photon_histories":x["photonHistories"]} for x in cases]}
 return {"schemaVersion":1,"stageId":STAGE_ID,"status":"PLAN_FROZEN","matrix":matrix,"caseCount":4,"configuredMcPhotonsSum":200_000_000,"maxParallel":4,"timeoutSeconds":900,"boundary":"four fresh 50M g01 precision blocks only"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--guard-report",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--github-output",type=Path);a=p.parse_args()
 try:
  r=build(load(a.manifest),load(a.guard_report));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r))
  if a.github_output:
   with a.github_output.open("a") as f:
    f.write("matrix="+json.dumps(r["matrix"],separators=(",",":"))+"\nmax_parallel=4\ntimeout_seconds=900\n")
  print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
