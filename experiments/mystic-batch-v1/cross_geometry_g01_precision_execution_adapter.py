#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any

STAGE_ID = "g01-fixed-precision-diagnosis-execution-v1"
ADAPTER_ID = "mystic-cross-geometry-g01-precision-execution-v1"
BASE_ADAPTER = Path(__file__).with_name("cross_geometry_adapter.py")

def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict): raise ValueError(f"expected object: {path}")
    return value

def dump(value: Any) -> str: return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
def raw(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def text_sha(text: str) -> str: return hashlib.sha256(text.encode()).hexdigest()
def base_module():
    spec = importlib.util.spec_from_file_location("cross_geometry_base_adapter", BASE_ADAPTER)
    if spec is None or spec.loader is None: raise ValueError("cannot load base adapter")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def validate_manifest(proposal: dict[str, Any]) -> None:
    required = {"schemaVersion":1,"stageId":STAGE_ID,"batchId":"g01-fixed-precision-diagnosis-v1","mode":"scientific-proposal","proposalOnly":True,"scientificExecution":False,"scientificDiagnostic":True,"successDoesNotAuthorizeProduction":True,"adapterId":"mystic-cross-geometry-v1"}
    stale={k:(proposal.get(k),v) for k,v in required.items() if proposal.get(k)!=v}
    if stale: raise ValueError(f"manifest header changed: {stale}")
    cases=proposal.get("cases"); geometries=proposal.get("geometries")
    if not isinstance(cases,list) or len(cases)!=4 or [x.get("ordinal") for x in cases]!=[1,2,3,4]: raise ValueError("exactly four ordered cases required")
    if not isinstance(geometries,list) or len(geometries)!=1 or geometries[0].get("geometryId")!="g01-reference-bridge": raise ValueError("g01 geometry changed")
    expected_blocks=[5,6,7,8]
    for case,block in zip(cases,expected_blocks):
        if case.get("groupId")!="g01-reference-bridge" or case.get("method")!="alis" or case.get("block")!=block or case.get("photonHistories")!=50_000_000 or float(case.get("alisSpectralImportanceSamplingNm",-1))!=600.0: raise ValueError(f"case boundary changed: {case.get('caseId')}")
    if len({x.get("seed") for x in cases})!=4: raise ValueError("seeds not unique")

def validate_runtime(proposal: dict[str, Any], report: dict[str, Any]) -> None:
    fields=("uvspecSha256","uvspecHelpSha256","libRadtranDataTreeSha256","atmosphereSha256","runtimeLockRawSha256")
    runtime=proposal.get("runtime",{})
    if report.get("schemaVersion")!=1 or report.get("stageId")!="mystic-batch-v1" or report.get("scientificSolverExecuted") is not False or report.get("syntaxCheckExecuted") is not False: raise ValueError("runtime report invalid")
    stale={k:(report.get(k),runtime.get(k)) for k in fields if report.get(k)!=runtime.get(k)}
    if stale: raise ValueError(f"runtime identity changed: {stale}")

def prepare_case(proposal_path: Path, runtime_report_path: Path, case_id: str, data_dir: Path, repository_root: Path, output_dir: Path) -> dict[str, Any]:
    proposal, report = load(proposal_path), load(runtime_report_path)
    validate_manifest(proposal); validate_runtime(proposal, report)
    base=base_module(); case,geometry=base.resolve_case(proposal,case_id); inputs=base.normalized_inputs(proposal,case,geometry); inputs["alisSpectralImportanceSamplingNm"]=600.0
    case_dir=output_dir/case_id; case_dir.mkdir(parents=True,exist_ok=False)
    text=base.render_input(inputs,data_dir.resolve(),repository_root.resolve(),case_dir.resolve()); input_path=case_dir/"input-resolved.txt"; input_path.write_text(text)
    prepared={"schemaVersion":1,"stageId":STAGE_ID,"adapterId":ADAPTER_ID,"status":"PREPARED_FOR_ONE_AUTHORIZED_G01_PRECISION_CASE","scientificSolverExecuted":False,"syntaxCheckExecuted":False,"batchId":proposal["batchId"],"caseId":case_id,"groupId":case["groupId"],"method":case["method"],"block":case["block"],"purpose":case["purpose"],"alisSpectralImportanceSamplingNm":600.0,"proposalRawSha256":raw(proposal_path),"runtimeReportRawSha256":raw(runtime_report_path),"baseAdapterRawSha256":raw(BASE_ADAPTER),"inputResolvedSha256":text_sha(text),"inputs":inputs,"inputPath":str(input_path),"boundary":"one fresh g01 held-out precision block; one syntax check and at most one solver execution"}
    (case_dir/"cross-geometry-g01-precision-prepared.json").write_text(dump(prepared)); return prepared
