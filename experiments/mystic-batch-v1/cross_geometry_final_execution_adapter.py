#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

STAGE_ID="cross-geometry-final-convergence-v1"
ADAPTER_ID="mystic-cross-geometry-final-execution-v1"
BASE_ADAPTER=Path(__file__).with_name("cross_geometry_adapter.py")
GROUPS={"g01-reference-bridge","g05-mid-opposite-low","g06-late-opposite-high-aerosol"}

class AdapterRefusal(RuntimeError): pass

def load(path:Path)->dict[str,Any]:
    v=json.loads(path.read_text())
    if not isinstance(v,dict): raise AdapterRefusal(f"expected JSON object: {path}")
    return v

def dump(v:Any)->str: return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def text_sha(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()
def base_module():
    spec=importlib.util.spec_from_file_location("cross_geometry_base_adapter",BASE_ADAPTER)
    if spec is None or spec.loader is None: raise AdapterRefusal("cannot load base adapter")
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def validate_manifest(p:dict[str,Any])->None:
    required={"schemaVersion":1,"stageId":STAGE_ID,"batchId":"cross-geometry-final-convergence-screening-v1","mode":"scientific-proposal","proposalOnly":True,"scientificExecution":False,"successDoesNotAuthorizeProduction":True,"adapterId":"mystic-cross-geometry-v1"}
    stale={k:(p.get(k),v) for k,v in required.items() if p.get(k)!=v}
    if stale: raise AdapterRefusal(f"proposal header mismatch: {stale}")
    cases=p.get("cases")
    if not isinstance(cases,list) or len(cases)!=26: raise AdapterRefusal("proposal must contain 26 cases")
    if [c.get("ordinal") for c in cases]!=list(range(1,27)): raise AdapterRefusal("ordinals changed")
    if {c.get("groupId") for c in cases}!=GROUPS: raise AdapterRefusal("geometry set changed")
    if sum(c.get("photonHistories",0) for c in cases)!=520_000_000: raise AdapterRefusal("photon sum changed")
    diag=[c for c in cases if c.get("purpose")=="alis-reference-diagnostic"]
    cont=[c for c in cases if c.get("purpose")=="continuation"]
    if len(diag)!=18 or len(cont)!=8: raise AdapterRefusal("purpose accounting changed")
    if {c.get("alisSpectralImportanceSamplingNm") for c in diag}!={500.0,550.0,600.0}: raise AdapterRefusal("ALIS reference candidates changed")
    if any(c.get("method")!="alis" for c in diag): raise AdapterRefusal("diagnostic method changed")
    seeds=[c.get("seed") for c in cases]
    if len(set(seeds))!=26 or any(not isinstance(s,int) or s<1 for s in seeds): raise AdapterRefusal("seeds invalid")

def validate_runtime(p:dict[str,Any],r:dict[str,Any])->None:
    runtime=p.get("runtime")
    fields=("uvspecSha256","uvspecHelpSha256","libRadtranDataTreeSha256","atmosphereSha256","runtimeLockRawSha256")
    if r.get("schemaVersion")!=1 or r.get("stageId")!="mystic-batch-v1": raise AdapterRefusal("runtime report header mismatch")
    if r.get("scientificSolverExecuted") is not False or r.get("syntaxCheckExecuted") is not False: raise AdapterRefusal("runtime report must precede execution")
    stale={f:(r.get(f),runtime.get(f)) for f in fields if r.get(f)!=runtime.get(f)}
    if stale: raise AdapterRefusal(f"runtime identity mismatch: {stale}")

def prepare_case(proposal_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,output_dir:Path)->dict[str,Any]:
    p=load(proposal_path); r=load(runtime_report_path); validate_manifest(p); validate_runtime(p,r)
    base=base_module(); case,geometry=base.resolve_case(p,case_id); inputs=base.normalized_inputs(p,case,geometry)
    if case.get("method")=="alis":
        ref=case.get("alisSpectralImportanceSamplingNm",p["frozenInputs"]["alisSpectralImportanceSamplingNm"])
        if ref not in {405.0,500.0,550.0,600.0}: raise AdapterRefusal("unsupported ALIS importance wavelength")
        inputs["alisSpectralImportanceSamplingNm"]=float(ref)
    case_dir=output_dir/case_id; case_dir.mkdir(parents=True,exist_ok=False)
    text=base.render_input(inputs,data_dir.resolve(),repository_root.resolve(),case_dir.resolve())
    (case_dir/"input-resolved.txt").write_text(text)
    prepared={"schemaVersion":1,"stageId":STAGE_ID,"adapterId":ADAPTER_ID,"status":"PREPARED_FOR_ONE_AUTHORIZED_FINAL_CASE","scientificSolverExecuted":False,"syntaxCheckExecuted":False,"batchId":p["batchId"],"caseId":case_id,"groupId":case["groupId"],"method":case["method"],"block":case["block"],"purpose":case["purpose"],"alisSpectralImportanceSamplingNm":inputs.get("alisSpectralImportanceSamplingNm"),"proposalRawSha256":sha(proposal_path),"runtimeReportRawSha256":sha(runtime_report_path),"baseAdapterRawSha256":sha(BASE_ADAPTER),"inputResolvedSha256":text_sha(text),"inputs":inputs,"inputPath":str(case_dir/"input-resolved.txt"),"boundary":"input prepared after exact runtime verification; one syntax check and at most one solver are delegated to the guarded executor"}
    (case_dir/"cross-geometry-final-prepared.json").write_text(dump(prepared)); return prepared
