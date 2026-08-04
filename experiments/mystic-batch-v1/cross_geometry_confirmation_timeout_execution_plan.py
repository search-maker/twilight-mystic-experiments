#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-held-out-confirmation-timeout-continuation-v1"
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict): raise ValueError("expected object")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def build(manifest_path:Path,guard_path:Path)->dict[str,Any]:
 m,g=load(manifest_path),load(guard_path)
 if m.get("stageId")!=STAGE_ID or g.get("status")!="AUTHORIZED" or g.get("stageId")!=STAGE_ID: raise ValueError("wrong manifest or guard")
 if g.get("manifestRawSha256")!=sha(manifest_path): raise ValueError("manifest hash mismatch")
 cases=m["cases"]; total=sum(c["photonHistories"] for c in cases)
 return {"schemaVersion":1,"stageId":"mystic-batch-v1","mode":"scientific","scientificExecution":True,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"scientificPurpose":STAGE_ID,"batchId":m["batchId"],"manifestPath":str(manifest_path),"manifestRawSha256":sha(manifest_path),"scientificAdapterRawSha256":g["executionAdapterRawSha256"],"runtimeLockRawSha256":g["runtimeLockRawSha256"],"executionWorkflowRawSha256":g["executionWorkflowRawSha256"],"authorizationRef":g["authorizationRef"],"authorizationOrdinal":g["authorizationOrdinal"],"executionKey":g["executionKey"],"caseCount":len(cases),"configuredMcPhotonsSum":total,"maximumParallel":8,"perCaseTimeoutSeconds":2400,"cases":cases,"matrix":{"include":[{"case_id":c["caseId"],"ordinal":c["ordinal"],"seed":c["seed"],"block":c["block"],"photon_histories":c["photonHistories"]} for c in cases]},"boundary":"eight fresh 200M g06 subblocks; no source g01 rerun"}
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--manifest",type=Path,required=True);p.add_argument("--guard-report",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--github-output",type=Path);a=p.parse_args()
 try:
  r=build(a.manifest,a.guard_report);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(dump(r));
  if a.github_output:a.github_output.write_text(f"matrix={json.dumps(r['matrix'],separators=(',',':'))}\nmax_parallel=8\ntimeout_seconds=2400\n")
  print(dump(r),end="");return 0
 except Exception as e:print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(e)}),file=sys.stderr,end="");return 2
if __name__=="__main__":raise SystemExit(main())
