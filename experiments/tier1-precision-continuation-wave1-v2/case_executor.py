#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

STAGE_ID = "tier1-precision-continuation-wave1-ordinal8-execution-v2"
NODES = [470,480,490,500,510,520,530,540,560,580,590,600,610,640,660]
CIE = [0.09098,0.13902,0.20802,0.323,0.503,0.71,0.862,0.954,0.995,0.87,0.757,0.631,0.503,0.175,0.061]


class ExecutionRefusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("wave1_execution_adapter", path)
    if spec is None or spec.loader is None:
        raise ExecutionRefusal("adapter unavailable")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def verify_context(allow_execution: bool) -> None:
    if not allow_execution:
        raise ExecutionRefusal("--allow-execution required")
    expected = {"GITHUB_ACTIONS":"true","GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_RUN_ATTEMPT":"1"}
    stale = {key:(os.getenv(key), value) for key,value in expected.items() if os.getenv(key) != value}
    if stale:
        raise ExecutionRefusal(f"not exact first-attempt workflow_dispatch: {stale}")


def parse_spectrum(path: Path) -> list[float]:
    found: dict[int,float] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts=line.split()
        if len(parts)<2: continue
        try: wavelength=float(parts[0]); value=float(parts[-1])
        except ValueError: continue
        for node in NODES:
            if abs(wavelength-node)<=1e-7: found[node]=value
    if sorted(found) != NODES:
        raise ExecutionRefusal("partial selected-node spectrum")
    values=[found[node] for node in NODES]
    if any(not math.isfinite(v) or v<0 for v in values):
        raise ExecutionRefusal("nonfinite or negative selected-node value")
    return values


def _run(command: list[str], text: str, cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        result=subprocess.run(command,input=text,text=True,capture_output=True,cwd=cwd,timeout=timeout,check=False)
        return {"exitCode":result.returncode,"timedOut":False,"stdout":result.stdout,"stderr":result.stderr}
    except subprocess.TimeoutExpired as exc:
        return {"exitCode":None,"timedOut":True,"stdout":exc.stdout or "","stderr":exc.stderr or ""}


def execute_case(manifest_path: Path, runtime_path: Path, adapter_path: Path, case_id: str, data_dir: Path, repository_root: Path, uvspec: Path, output_root: Path, timeout_seconds: int, allow_execution: bool, runner: Callable[...,dict[str,Any]]=_run) -> dict[str, Any]:
    verify_context(allow_execution)
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    matches=[case for case in manifest.get("cases",[]) if case.get("caseId")==case_id]
    if len(matches)!=1: raise ExecutionRefusal("case selection changed")
    case=matches[0]
    adapter=load_module(adapter_path)
    prepared=adapter.prepare_case(manifest_path,runtime_path,case_id,data_dir,repository_root,output_root)
    case_dir=output_root/case_id; text=(case_dir/"input-resolved.txt").read_text(encoding="utf-8")
    syntax=runner([str(uvspec),"-c"],text,case_dir,60)
    (case_dir/"syntax-stdout.txt").write_text(str(syntax["stdout"]),encoding="utf-8")
    (case_dir/"syntax-stderr.txt").write_text(str(syntax["stderr"]),encoding="utf-8")
    if syntax["timedOut"] or syntax["exitCode"]!=0: raise ExecutionRefusal("single syntax check failed")
    solver=runner([str(uvspec)],text,case_dir,timeout_seconds)
    (case_dir/"solver-stdout.txt").write_text(str(solver["stdout"]),encoding="utf-8")
    (case_dir/"solver-stderr.txt").write_text(str(solver["stderr"]),encoding="utf-8")
    if solver["timedOut"] or solver["exitCode"]!=0: raise ExecutionRefusal("single solver execution failed")
    radiance=case_dir/"mc.rad.spc"; std=case_dir/"mc.rad.std.spc"
    if not radiance.is_file() or not std.is_file(): raise ExecutionRefusal("required raw output missing")
    values=parse_spectrum(radiance); std_values=parse_spectrum(std)
    photopic=683.002*10.0*sum((v/1000.0)*w for v,w in zip(values,CIE))
    result={"schemaVersion":1,"stageId":STAGE_ID,"status":"COMPLETED","caseId":case_id,"groupId":case["groupId"],"block":case["block"],"role":case["role"],"seed":case["seed"],"photonHistories":case["photonHistories"],"manifestSha256":manifest["manifestSha256"],"runtimeReportSha256":hashlib.sha256(runtime_path.read_bytes()).hexdigest(),"inputSha256":prepared["inputResolvedSha256"],"radianceOutputSha256":hashlib.sha256(radiance.read_bytes()).hexdigest(),"stdOutputSha256":hashlib.sha256(std.read_bytes()).hexdigest(),"syntaxCheckCount":1,"solverExecutionCount":1,"selectedNodeRadiance":values,"selectedNodeStdRadiance":std_values,"selectedPhotopicContributionCdM2":photopic,"zeroHit":all(v==0 for v in values),"fittingSurfaceExposed":False,"retryAllowed":False,"resumeAllowed":False}
    result["contentSha256"]=canonical_sha256(result)
    (case_dir/"case-result.json").write_text(dump(result),encoding="utf-8",newline="\n")
    return result


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--runtime-report",type=Path,required=True); p.add_argument("--adapter",type=Path,required=True); p.add_argument("--case-id",required=True); p.add_argument("--data-dir",type=Path,required=True); p.add_argument("--repository-root",type=Path,required=True); p.add_argument("--uvspec",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--timeout-seconds",type=int,required=True); p.add_argument("--allow-execution",action="store_true"); a=p.parse_args()
    try: print(dump(execute_case(a.manifest,a.runtime_report,a.adapter,a.case_id,a.data_dir,a.repository_root,a.uvspec,a.output_root,a.timeout_seconds,a.allow_execution)),end=""); return 0
    except Exception as exc: print(dump({"stageId":STAGE_ID,"status":"REFUSED","reason":str(exc)}),end="",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())