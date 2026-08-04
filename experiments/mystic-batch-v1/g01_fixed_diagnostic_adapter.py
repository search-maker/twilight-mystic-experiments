#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

STAGE_ID="g01-fixed-precision-diagnosis-execution-v1"
ADAPTER_ID="mystic-g01-fixed-precision-diagnosis-v1"
BASE=Path(__file__).with_name("cross_geometry_adapter.py")

class AdapterError(RuntimeError):pass

def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text())
 if not isinstance(v,dict):raise AdapterError(f"expected object: {p}")
 return v

def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def text_sha(t:str)->str:return hashlib.sha256(t.encode()).hexdigest()
def base_module():
 spec=importlib.util.spec_from_file_location("g01_base_adapter",BASE)
 if spec is None or spec.loader is None:raise AdapterError("base adapter unavailable")
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_manifest(m:dict[str,Any])->None:
 required={"schemaVersion":1,"stageId":STAGE_ID,"batchId":"g01-fixed-precision-diagnosis-v1","mode":"scientific-proposal","proposalOnly":True,"scientificExecution":False,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"adapterId":ADAPTER_ID,"noAutomaticAdditionalBlocks":True}
 stale={k:(m.get(k),v) for k,v in required.items() if m.get(k)!=v}
 if stale:raise AdapterError(f"manifest mismatch: {stale}")
 cases=m.get("cases");geometries=m.get("geometries")
 if not isinstance(cases,list) or len(cases)!=4 or not isinstance(geometries,list) or len(geometries)!=1:raise AdapterError("exact four cases and one geometry required")
 if [c.get("ordinal") for c in cases]!=[1,2,3,4]:raise AdapterError("case ordinals changed")
 if [c.get("caseId") for c in cases]!=[f"g01pd-alis-b{i}" for i in range(5,9)]:raise AdapterError("case IDs changed")
 if [c.get("seed") for c in cases]!=[84601,84602,84603,84604]:raise AdapterError("seeds changed")
 if [c.get("block") for c in cases]!=[5,6,7,8]:raise AdapterError("blocks changed")
 if any(c.get("groupId")!="g01-reference-bridge" or c.get("method")!="alis" or c.get("photonHistories")!=50000000 or float(c.get("alisSpectralImportanceSamplingNm",-1))!=600.0 for c in cases):raise AdapterError("case contract changed")

def validate_runtime(m:dict[str,Any],r:dict[str,Any])->None:
 fields=("uvspecSha256","uvspecHelpSha256","libRadtranDataTreeSha256","atmosphereSha256","runtimeLockRawSha256")
 if r.get("schemaVersion")!=1 or r.get("stageId")!="mystic-batch-v1" or r.get("scientificSolverExecuted") is not False or r.get("syntaxCheckExecuted") is not False:raise AdapterError("runtime report invalid")
 stale={field:(r.get(field),m.get("runtime",{}).get(field)) for field in fields if r.get(field)!=m.get("runtime",{}).get(field)}
 if stale:raise AdapterError(f"runtime mismatch: {stale}")

def prepare_case(manifest_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,output_dir:Path)->dict[str,Any]:
 m,r=load(manifest_path),load(runtime_report_path);validate_manifest(m);validate_runtime(m,r);base=base_module();case,geometry=base.resolve_case(m,case_id);inputs=base.normalized_inputs(m,case,geometry);inputs["alisSpectralImportanceSamplingNm"]=600.0;case_dir=output_dir/case_id;case_dir.mkdir(parents=True,exist_ok=False);text=base.render_input(inputs,data_dir.resolve(),repository_root.resolve(),case_dir.resolve());path=case_dir/"input-resolved.txt";path.write_text(text);result={"schemaVersion":1,"stageId":STAGE_ID,"adapterId":ADAPTER_ID,"status":"PREPARED_FOR_ONE_AUTHORIZED_G01_FIXED_DIAGNOSTIC_CASE","caseId":case_id,"groupId":case["groupId"],"method":"alis","block":case["block"],"purpose":case["purpose"],"alisSpectralImportanceSamplingNm":600.0,"proposalRawSha256":raw(manifest_path),"runtimeReportRawSha256":raw(runtime_report_path),"baseAdapterRawSha256":raw(BASE),"inputResolvedSha256":text_sha(text),"inputs":inputs,"inputPath":str(path),"boundary":"one fresh 50M g01 diagnostic block; one syntax check and at most one solver execution; no retry"};(case_dir/"g01-fixed-diagnostic-prepared.json").write_text(dump(result));return result
