#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any
STAGE_ID="cross-geometry-held-out-confirmation-timeout-continuation-v1"; ADAPTER_ID="mystic-cross-geometry-timeout-continuation-v1"; BASE_ADAPTER=Path(__file__).with_name("cross_geometry_adapter.py")
class AdapterRefusal(RuntimeError): pass
def load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text());
 if not isinstance(v,dict): raise AdapterRefusal("expected object")
 return v
def dump(v:Any)->str:return json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"
def raw(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def textsha(t:str)->str:return hashlib.sha256(t.encode()).hexdigest()
def base_module():
 s=importlib.util.spec_from_file_location("base",BASE_ADAPTER)
 if s is None or s.loader is None: raise AdapterRefusal("cannot load base adapter")
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def validate_manifest(m:dict[str,Any])->None:
 req={"schemaVersion":1,"stageId":STAGE_ID,"batchId":STAGE_ID,"mode":"scientific-proposal","proposalOnly":True,"scientificExecution":False,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"adapterId":"mystic-cross-geometry-v1"}
 stale={k:(m.get(k),v) for k,v in req.items() if m.get(k)!=v}
 if stale: raise AdapterRefusal(f"header mismatch {stale}")
 cases=m.get("cases");
 if not isinstance(cases,list) or len(cases)!=8: raise AdapterRefusal("exactly 8 continuation cases required")
 if [c.get("ordinal") for c in cases]!=list(range(1,9)): raise AdapterRefusal("ordinals changed")
 if any(c.get("groupId")!="g06-late-opposite-high-aerosol" or c.get("method")!="alis" or c.get("photonHistories")!=200000000 or float(c.get("alisSpectralImportanceSamplingNm",0))!=500.0 for c in cases): raise AdapterRefusal("continuation case contract changed")
 if len({c.get("seed") for c in cases})!=8 or set(c.get("seed") for c in cases)&{82501,82502,82503,82504}: raise AdapterRefusal("fresh seeds required")
def validate_runtime(m:dict[str,Any],r:dict[str,Any])->None:
 fields=("uvspecSha256","uvspecHelpSha256","libRadtranDataTreeSha256","atmosphereSha256","runtimeLockRawSha256")
 if r.get("scientificSolverExecuted") is not False or r.get("syntaxCheckExecuted") is not False: raise AdapterRefusal("runtime must precede execution")
 stale={f:(r.get(f),m["runtime"].get(f)) for f in fields if r.get(f)!=m["runtime"].get(f)}
 if stale: raise AdapterRefusal(f"runtime mismatch {stale}")
def prepare_case(proposal_path:Path,runtime_report_path:Path,case_id:str,data_dir:Path,repository_root:Path,output_dir:Path)->dict[str,Any]:
 m=load(proposal_path); r=load(runtime_report_path); validate_manifest(m); validate_runtime(m,r); base=base_module(); case,geometry=base.resolve_case(m,case_id); inputs=base.normalized_inputs(m,case,geometry); inputs["alisSpectralImportanceSamplingNm"]=500.0; d=output_dir/case_id; d.mkdir(parents=True,exist_ok=False); text=base.render_input(inputs,data_dir.resolve(),repository_root.resolve(),d.resolve()); (d/"input-resolved.txt").write_text(text); prepared={"schemaVersion":1,"stageId":STAGE_ID,"adapterId":ADAPTER_ID,"status":"PREPARED_FOR_ONE_AUTHORIZED_TIMEOUT_CONTINUATION_CASE","scientificSolverExecuted":False,"syntaxCheckExecuted":False,"batchId":m["batchId"],"caseId":case_id,"groupId":case["groupId"],"method":case["method"],"block":case["block"],"purpose":case["purpose"],"alisSpectralImportanceSamplingNm":500.0,"proposalRawSha256":raw(proposal_path),"runtimeReportRawSha256":raw(runtime_report_path),"baseAdapterRawSha256":raw(BASE_ADAPTER),"inputResolvedSha256":textsha(text),"inputs":inputs,"inputPath":str(d/"input-resolved.txt"),"boundary":"one fresh 200M subblock; one syntax check and at most one solver execution; no retry"}; (d/"timeout-continuation-prepared.json").write_text(dump(prepared)); return prepared
