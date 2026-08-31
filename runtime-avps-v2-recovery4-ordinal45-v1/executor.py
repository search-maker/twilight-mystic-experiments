from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py"
ADAPTER_PATH=Path(__file__).with_name("runtime_adapter.py")
CONTRACT_PATH=Path(__file__).with_name("runtime_contract.json")
BASE_BLOB="bb1e4276d6383127a6b7e820fc2568d87d5de4b0"
STAGE="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4"
GUARD_STATUS="EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_AUTHORIZED"
ORDINAL=45
EXECUTION_KEY="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4:numerical:45"
AUTH_HEAD="6e095b4b1603c90dcee0943295909b30cd1b374d"
AUTH_PR=774
DISPATCH_BRANCH="dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45"
SEED_CANONICAL="ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de"
FOUR_ALIAS="5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"

class ExecutionRefusal(RuntimeError): pass

def git_blob_sha1(path: Path)->str:
    raw=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise ExecutionRefusal(f"cannot load {path}")
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def validate_bound_sources(repository_root: Path)->None:
    expected={
      repository_root/"review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py":BASE_BLOB,
      repository_root/"review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py":"c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
      repository_root/"review/aerosol-vertical-profile-sensitivity-v2-control-v1/runtime_stage.py":"0d3ac10f3ef7d22f0205854233a6c37cbba03f7c",
      repository_root/"experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py":"e23d724e99c1cf9b0b862f8ab48356bd3d9bc56c",
      repository_root/"experiments/aerosol-family-challenge-v2-r8/derived_channels.py":"ccfd04d4c21188966351f4257e92893d7ce340c7",
      repository_root/"experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat":"3bb3db96580d555ef758f57cabd6cac55b61cebb"}
    for p,h in expected.items():
        if not p.is_file() or git_blob_sha1(p)!=h: raise ExecutionRefusal(f"bound source byte drift: {p}")

def load_contract(repository_root: Path)->dict[str,Any]:
    c=json.loads(CONTRACT_PATH.read_text())
    if c.get("status")!="REVIEW_ONLY_EXECUTION_CONTROL_FROZEN_DISPATCH_NOT_AUTHORIZED" or c.get("scientificOrdinal")!=ORDINAL or c.get("executionKey")!=EXECUTION_KEY: raise ExecutionRefusal("runtime identity contract drift")
    d=c.get("caseDesign") or {}
    if (d.get("expectedCaseCount"),d.get("expectedGroupCount"),d.get("expectedAnalysisCellCount"),d.get("expectedStatesPerGroup"),d.get("photonHistoriesPerCase"))!=(360,72,24,5,20_000_000): raise ExecutionRefusal("frozen case design drift")
    return c

def validate_authorization(auth):
    a=load("avps_recovery4_executor_adapter",ADAPTER_PATH)
    try: a.validate_authorization(auth)
    except Exception as e: raise ExecutionRefusal(str(e)) from e

def validate_guard(g):
    exact={"status":GUARD_STATUS,"scientificOrdinal":ORDINAL,"executionKey":EXECUTION_KEY,"authorizationHead":AUTH_HEAD,"authorizationPr":AUTH_PR,"dispatchBranch":DISPATCH_BRANCH,"dispatchBranchHeadSha":AUTH_HEAD,"workflowRunAttempt":1,"allocationMarkerCount":1,"consumedMarkerCount":1,"candidateSeedCanonicalSha256":SEED_CANONICAL,"fourAliasDataTreeSha256":FOUR_ALIAS,"preSolverRepositoryGlobalSeedRecheckPassed":True,"solverExecutionPermittedNow":True,"githubRerun":False,"retryAllowed":False,"resumeAllowed":False}
    for k,v in exact.items():
        if g.get(k)!=v: raise ExecutionRefusal(f"recovery4 guard drift: {k}")
    run=g.get("workflowRunId")
    if isinstance(run,bool) or not isinstance(run,int) or run<=0: raise ExecutionRefusal("workflow run id invalid")

def _configured():
    if not BASE_PATH.is_file() or git_blob_sha1(BASE_PATH)!=BASE_BLOB: raise ExecutionRefusal("base executor byte drift")
    b=load("avps_recovery4_base_executor",BASE_PATH)
    b.STAGE=STAGE; b.EXPECTED_GUARD_STATUS=GUARD_STATUS; b.EXPECTED_AUTH_HEAD=AUTH_HEAD; b.EXPECTED_AUTH_PR=AUTH_PR
    b.EXPECTED_ORDINAL=ORDINAL; b.EXPECTED_EXECUTION_KEY=EXECUTION_KEY; b.EXPECTED_SEED_CANONICAL=SEED_CANONICAL
    b.ADAPTER_PATH=ADAPTER_PATH; b.CONTRACT_PATH=CONTRACT_PATH
    b.validate_bound_sources=validate_bound_sources; b.load_contract=load_contract; b.validate_authorization=validate_authorization; b.validate_guard=validate_guard
    return b

def execute_case(*args,**kwargs):
    return _configured().execute_case(*args,**kwargs)
