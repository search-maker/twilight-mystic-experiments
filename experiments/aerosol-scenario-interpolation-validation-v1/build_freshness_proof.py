from __future__ import annotations
import argparse, hashlib, importlib.util, json, re
from pathlib import Path
from typing import Any

STAGE="aerosol-scenario-interpolation-validation-v1"
SHA40=re.compile(r"^[0-9a-f]{40}$")
class Refusal(RuntimeError): pass

def load_module(name:str,path:Path):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def canon(v:Any)->str: return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def build(stage:Path,tracked:dict[str,Any],global_report:dict[str,Any],geometry:dict[str,Any],head:str)->dict[str,Any]:
    if SHA40.fullmatch(head) is None: raise Refusal("bad main SHA")
    seed=load_module("asiv_seed_ledger_proof",stage/"seed_ledger.py"); ledger=seed.validate(); rows=seed.derive_rows()
    if tracked.get("candidateSeedCount")!=24 or tracked.get("trackedTreeExternalCollisionCount")!=0 or tracked.get("exactHeadTrackedTreeByteScanPassed") is not True: raise Refusal("tracked-tree seed audit failed")
    if global_report.get("auditMode")!="authorization-recheck" or global_report.get("candidateSeedCount")!=24: raise Refusal("repository-global seed audit identity drift")
    for key,want in (("repositoryGlobalCollisionCount",0),("repositoryGlobalPostFenceCandidateSeedCollisionCount",0)):
        if global_report.get(key)!=want: raise Refusal(f"{key} failed")
    if global_report.get("repositoryGlobalCollisionSurfaceScanPassed") is not True or global_report.get("repositoryGlobalDoubleEnumerationStable") is not True: raise Refusal("repository-global seed audit failed")
    if global_report.get("auditedBranchHeadMatchesRepositoryHead") is not True or global_report.get("repositoryHeadExpected")!=head or global_report.get("auditedBranchHeadShaObserved")!=head: raise Refusal("seed audit head binding failed")
    if geometry.get("status")!="PASS_FRESH_HOLDOUT_GEOMETRY_NO_PRIOR_NONSELF_COLLISION" or geometry.get("auditedMainHead")!=head: raise Refusal("geometry freshness failed")
    if geometry.get("trackedGeometryCollisionCount")!=0 or geometry.get("metadataGeometryCollisionCount")!=0 or geometry.get("holdoutGeometryCount")!=8: raise Refusal("geometry collision exists")
    if ledger.get("candidateSeedCanonicalSha256")!=canon(ledger["candidateSeeds"]) or ledger.get("candidateRowsCanonicalSha256")!=canon(rows): raise Refusal("seed ledger hash drift")
    return {"schemaVersion":1,"stageId":STAGE+"-preauthorization-freshness-proof","status":"PASS_ASIV_SEED_AND_GEOMETRY_AUTHORIZATION_RECHECK_NOT_ALLOCATED","auditedMainHead":head,"candidateSeedCount":24,"candidateSeedCanonicalSha256":ledger["candidateSeedCanonicalSha256"],"candidateRowsCanonicalSha256":ledger["candidateRowsCanonicalSha256"],"allCollisionCountersZero":True,"trackedTreeExternalCollisionCount":0,"repositoryGlobalCollisionCount":0,"repositoryGlobalDoubleEnumerationStable":True,"repositoryGlobalStableContextSha256":global_report.get("repositoryGlobalStableContextSha256"),"holdoutGeometryCount":8,"trackedGeometryCollisionCount":0,"metadataGeometryCollisionCount":0,"geometryMetadataStableContextSha256":geometry.get("repositoryMetadataStableContextSha256"),"scientificOrdinalAllocated":False,"authorizationCreated":False,"dispatchCreated":False,"scientificExecutionAuthorized":False,"solverExecutionAuthorized":False,"resultOpeningAuthorized":False}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--stage-dir",type=Path,required=True); ap.add_argument("--tracked-tree-report",type=Path,required=True); ap.add_argument("--repository-global-report",type=Path,required=True); ap.add_argument("--geometry-report",type=Path,required=True); ap.add_argument("--expected-main-head",required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    out=build(a.stage_dir,json.loads(a.tracked_tree_report.read_text()),json.loads(a.repository_global_report.read_text()),json.loads(a.geometry_report.read_text()),a.expected_main_head); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); return 0
if __name__=="__main__": raise SystemExit(main())
