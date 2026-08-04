#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
from typing import Any

STAGE_ID = "cross-geometry-held-out-confirmation-timeout-continuation-v1"
SOURCE_STAGE = "cross-geometry-selected-reference-confirmation-v1"
EXPECTED_SOURCE_RUN = 30871800549
EXPECTED_AUTH = "81b46da6e535e11a5e56b45572979288728805b3"
EXPECTED_KEY = "cross-geometry-selected-reference-confirmation-v1:screening:5"

def load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text())
    if not isinstance(value,dict): raise ValueError(f"expected object: {path}")
    return value

def dump(value: Any)->str: return json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n"
def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(proposal_path: Path, source_manifest_path: Path, source_run_path: Path, source_artifacts_path: Path, cases_root: Path)->dict[str,Any]:
    proposal,manifest,run,artifacts=map(load,(proposal_path,source_manifest_path,source_run_path,source_artifacts_path))
    if proposal.get("stageId")!=STAGE_ID or proposal.get("sourceFailedRunId")!=EXPECTED_SOURCE_RUN: raise ValueError("wrong continuation proposal")
    if sha(source_manifest_path)!=proposal.get("sourceManifestRawSha256"): raise ValueError("source manifest hash changed")
    if manifest.get("stageId")!=SOURCE_STAGE or manifest.get("limits",{}).get("perCaseTimeoutSeconds")!=1800: raise ValueError("wrong source manifest")
    if run.get("id")!=EXPECTED_SOURCE_RUN or run.get("event")!="workflow_dispatch" or run.get("run_attempt")!=1 or run.get("conclusion")!="failure": raise ValueError("wrong source run metadata")
    title=str(run.get("display_title", ""))
    for token in (EXPECTED_AUTH,EXPECTED_KEY,"ordinal=5"):
        if token not in title: raise ValueError(f"source run title missing {token}")
    listed={item.get("name"):item.get("digest") for item in artifacts.get("artifacts",[]) if isinstance(item,dict)}
    if listed.get("cross-geometry-held-out-confirmation-v1-preflight")!=proposal.get("sourcePreflightArtifactDigest"): raise ValueError("source preflight digest changed")
    for name,digest in proposal.get("sourceCaseArtifactDigests",{}).items():
        if listed.get(name)!=digest: raise ValueError(f"source case artifact digest changed: {name}")
    planned={case["caseId"]:case for case in manifest["cases"]}
    paths=sorted(cases_root.rglob("case-result.json"))
    if len(paths)!=8: raise ValueError(f"expected 8 source case results, found {len(paths)}")
    successes=[]; timeouts=[]
    for path in paths:
        record=load(path); case_id=record.get("caseId"); case=planned.get(case_id)
        if case is None: raise ValueError(f"unplanned source case {case_id}")
        if record.get("manifestRawSha256")!=sha(source_manifest_path) or record.get("seed")!=case["seed"] or record.get("photonHistories")!=case["photonHistories"]: raise ValueError(f"source case invariant changed: {case_id}")
        if case["groupId"]=="g01-reference-bridge":
            if record.get("status")!="COMPLETED" or record.get("solver",{}).get("exitCode")!=0 or record.get("solver",{}).get("timedOut") is not False: raise ValueError(f"g01 source result not complete: {case_id}")
            value=record.get("selectedPhotopicContributionCdM2")
            if not isinstance(value,(int,float)) or not math.isfinite(float(value)) or value<=0: raise ValueError(f"g01 source value invalid: {case_id}")
            successes.append({"caseId":case_id,"rawSha256":sha(path)})
        else:
            failure=record.get("failure",{}).get("detail",{})
            if record.get("status")!="FAILED" or failure.get("timedOut") is not True or record.get("solver",{}).get("timedOut") is not True: raise ValueError(f"g06 source failure was not timeout: {case_id}")
            elapsed=float(failure.get("elapsedSeconds",0))
            if not 1799.0<=elapsed<=1802.0 or record.get("selectedNodeRadiance")!=[] or record.get("selectedPhotopicContributionCdM2") is not None: raise ValueError(f"g06 timeout boundary changed: {case_id}")
            timeouts.append({"caseId":case_id,"elapsedSeconds":elapsed,"rawSha256":sha(path)})
    if len(successes)!=4 or len(timeouts)!=4: raise ValueError("source success/timeout partition changed")
    return {"schemaVersion":1,"stageId":STAGE_ID,"status":"SOURCE_TIMEOUT_FAILURE_AUDITED","sourceRunId":EXPECTED_SOURCE_RUN,"preservedSuccessCount":4,"timedOutFailureCount":4,"preservedG01Results":sorted(successes,key=lambda x:x["caseId"]),"failedG06Results":sorted(timeouts,key=lambda x:x["caseId"]),"sourceManifestRawSha256":sha(source_manifest_path),"boundary":"source run first attempt audited; g01 preserved, g06 timeout outputs rejected; no Re-run"}

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--proposal",type=Path,required=True); p.add_argument("--source-manifest",type=Path,required=True); p.add_argument("--source-run",type=Path,required=True); p.add_argument("--source-artifacts",type=Path,required=True); p.add_argument("--cases-root",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    try:
        result=audit(a.proposal,a.source_manifest,a.source_run,a.source_artifacts,a.cases_root); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(dump(result)); print(dump(result),end=""); return 0
    except Exception as exc: print(dump({"status":"REFUSED","stageId":STAGE_ID,"reason":str(exc)}),end="",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
