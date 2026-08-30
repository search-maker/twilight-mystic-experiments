from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated-avps-v2-recovery3-ordinal44-runtime-identity"
BASE_EXECUTOR = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py"
BASE_AGGREGATOR = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py"
BASE_ADAPTER = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py"
CONTRACT = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/identity-contract.review.json"

EXPECTED_BLOBS = {
    BASE_EXECUTOR: "bb1e4276d6383127a6b7e820fc2568d87d5de4b0",
    BASE_AGGREGATOR: "ef24a0d30af3dfb46a6b764f3e426465da870fbe",
    BASE_ADAPTER: "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
    ROOT / "review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-seed-freshness-v1/seed_ledger.py": "a4fc0b95c3627a310c0c17a1ae8b89701511b3b8",
    ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/runtime_stage.py": "0d3ac10f3ef7d22f0205854233a6c37cbba03f7c",
    ROOT / "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1/execution-candidate/process_runner.py": "e23d724e99c1cf9b0b862f8ab48356bd3d9bc56c",
    ROOT / "experiments/aerosol-family-challenge-v2-r8/derived_channels.py": "ccfd04d4c21188966351f4257e92893d7ce340c7",
    ROOT / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat": "3bb3db96580d555ef758f57cabd6cac55b61cebb",
}


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_sources() -> None:
    for path, expected in EXPECTED_BLOBS.items():
        if not path.is_file() or git_blob_sha1(path) != expected:
            raise SystemExit(f"bound source byte drift: {path}")
    c = json.loads(CONTRACT.read_text())
    if c.get("scientificOrdinal") != 44 or c.get("newMappingAuthorized") is not False:
        raise SystemExit("identity contract drift")


ADAPTER = r'''from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1/adapter.py"
BASE_BLOB = "c245eac2fe5b5d026e46ec4253bc377c5fde97ec"
STAGE = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3"
AUTH_STATUS = "AUTHORIZED_POSTCONSUMPTION_RECOVERY3_PENDING_SEPARATE_ALLOCATION_AND_DISPATCH"
ORDINAL = 44
EXECUTION_KEY = "aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44"
AUTH_HEAD = "dd3a4c692af505389e9feb1e5f5480fa389110a3"
AUTH_PR = 718
AUTH_BRANCH = "authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
DISPATCH_BRANCH = "dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
SEED_CANONICAL = "d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
ROWS_CANONICAL = "b6a519eadacdb99ea53c52d483c8acfeba05829643cb988de21682a53fc47896"
NAMESPACE = "aerosol-vertical-profile-sensitivity-v2|postconsumption-recovery3|group-seed|sha256-v1"
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED

class AdapterRefusal(RuntimeError): pass

def git_blob_sha1(path: Path) -> str:
    raw=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def load(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise AdapterRefusal(f"cannot load {path}")
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def _base():
    if git_blob_sha1(BASE_PATH)!=BASE_BLOB: raise AdapterRefusal("base adapter byte drift")
    return load("avps_recovery3_base_adapter",BASE_PATH)

def validate_authorization(auth: dict[str,Any]) -> None:
    exact={"stageId":STAGE,"status":AUTH_STATUS,"scientificOrdinal":ORDINAL,"executionKey":EXECUTION_KEY,
           "authorizationBranch":AUTH_BRANCH,"dispatchBranch":DISPATCH_BRANCH,
           "candidateSeedCanonicalSha256":SEED_CANONICAL,"candidateRowsCanonicalSha256":ROWS_CANONICAL,
           "candidateSeedCount":72,"caseCount":360,"commonRandomNumberGroupCount":72,"statesPerGroup":5,
           "photonHistoriesPerCase":20_000_000}
    for k,v in exact.items():
        if auth.get(k)!=v: raise AdapterRefusal(f"recovery3 authorization drift: {k}")
    if auth.get("scientificExecutionAuthorized") is not True or auth.get("solverExecutionAuthorized") is not True:
        raise AdapterRefusal("science/solver authorization missing")
    for k in ("dispatchAuthorized","automaticDispatch","resultOpeningAuthorized","levelBOpeningAuthorized","protectedHoldoutOpeningAuthorized","productionAuthorized","taylorOrJerusalemFitAuthorized"):
        if auth.get(k) is not False: raise AdapterRefusal(f"forbidden authorization boundary crossed: {k}")
    for k in ("githubRerunAllowed","retryAllowed","resumeAllowed"):
        if auth.get(k) is not False: raise AdapterRefusal(f"one-shot boundary weakened: {k}")

def _seed_rows(base) -> list[dict[str,Any]]:
    skeleton=base._skeleton(); groups=skeleton.get("groups")
    if not isinstance(groups,list) or len(groups)!=72: raise AdapterRefusal("72-group skeleton drift")
    rows=[]; used=set()
    for group in groups:
        gid=str(group["groupId"]); counter=0
        material=f"{NAMESPACE}|groupId={gid}|counter={counter}"
        digest=hashlib.sha256(material.encode()).hexdigest()
        seed=(int(digest[:16],16)%SPAN)+MIN_SEED
        if seed in used: raise AdapterRefusal("unexpected recovery3 seed collision")
        used.add(seed); rows.append({"groupId":gid,"collisionCounter":counter,"derivationMaterialSha256":digest,"seed":seed})
    seeds=[int(r["seed"]) for r in rows]
    if canonical(seeds)!=SEED_CANONICAL or canonical(rows)!=ROWS_CANONICAL: raise AdapterRefusal("recovery3 seed identity drift")
    return rows

def seed_receipt() -> dict[str,Any]:
    base=_base(); rows=_seed_rows(base)
    return {"seedCount":len(rows),"seedCanonicalSha256":canonical([r["seed"] for r in rows]),"rowsCanonicalSha256":canonical(rows)}

def _configured():
    base=_base(); rows=_seed_rows(base); seed_map={r["groupId"]:int(r["seed"]) for r in rows}
    base.STAGE=STAGE; base.EXPECTED_SEED_CANONICAL=SEED_CANONICAL; base.EXPECTED_ROWS_CANONICAL=ROWS_CANONICAL
    base.validate_authorization=validate_authorization; base._seed_map=lambda: dict(seed_map)
    return base

def authorized_case_universe(auth: dict[str,Any]) -> list[dict[str,Any]]:
    return _configured().authorized_case_universe(auth)

def prepare_case_files(case,auth,data_dir,repository_root,profile_dir,output_root):
    return _configured().prepare_case_files(case,auth,data_dir,repository_root,profile_dir,output_root)
'''

EXECUTOR = r'''from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-executor-parity-v1/executor.py"
ADAPTER_PATH=Path(__file__).with_name("runtime_adapter.py")
CONTRACT_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/identity-contract.review.json"
BASE_BLOB="bb1e4276d6383127a6b7e820fc2568d87d5de4b0"
STAGE="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3"
GUARD_STATUS="EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY3_DISPATCH_AUTHORIZED"
ORDINAL=44
EXECUTION_KEY="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44"
AUTH_HEAD="dd3a4c692af505389e9feb1e5f5480fa389110a3"
AUTH_PR=718
DISPATCH_BRANCH="dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-ordinal-44"
SEED_CANONICAL="d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
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
    c=json.loads((repository_root/CONTRACT_PATH.relative_to(ROOT)).read_text())
    if c.get("status")!="REVIEW_ONLY_EXECUTION_CONTROL_FROZEN_DISPATCH_NOT_AUTHORIZED" or c.get("scientificOrdinal")!=ORDINAL or c.get("executionKey")!=EXECUTION_KEY: raise ExecutionRefusal("runtime identity contract drift")
    d=c.get("caseDesign") or {}
    if (d.get("expectedCaseCount"),d.get("expectedGroupCount"),d.get("expectedAnalysisCellCount"),d.get("expectedStatesPerGroup"),d.get("photonHistoriesPerCase"))!=(360,72,24,5,20_000_000): raise ExecutionRefusal("frozen case design drift")
    return c

def validate_authorization(auth):
    a=load("avps_recovery3_executor_adapter",ADAPTER_PATH)
    try: a.validate_authorization(auth)
    except Exception as e: raise ExecutionRefusal(str(e)) from e

def validate_guard(g):
    exact={"status":GUARD_STATUS,"scientificOrdinal":ORDINAL,"executionKey":EXECUTION_KEY,"authorizationHead":AUTH_HEAD,"authorizationPr":AUTH_PR,"dispatchBranch":DISPATCH_BRANCH,"dispatchBranchHeadSha":AUTH_HEAD,"workflowRunAttempt":1,"allocationMarkerCount":1,"consumedMarkerCount":1,"candidateSeedCanonicalSha256":SEED_CANONICAL,"fourAliasDataTreeSha256":FOUR_ALIAS,"preSolverRepositoryGlobalSeedRecheckPassed":True,"solverExecutionPermittedNow":True,"githubRerun":False,"retryAllowed":False,"resumeAllowed":False}
    for k,v in exact.items():
        if g.get(k)!=v: raise ExecutionRefusal(f"recovery3 guard drift: {k}")
    run=g.get("workflowRunId")
    if isinstance(run,bool) or not isinstance(run,int) or run<=0: raise ExecutionRefusal("workflow run id invalid")

def _configured():
    if not BASE_PATH.is_file() or git_blob_sha1(BASE_PATH)!=BASE_BLOB: raise ExecutionRefusal("base executor byte drift")
    b=load("avps_recovery3_base_executor",BASE_PATH)
    b.STAGE=STAGE; b.EXPECTED_GUARD_STATUS=GUARD_STATUS; b.EXPECTED_AUTH_HEAD=AUTH_HEAD; b.EXPECTED_AUTH_PR=AUTH_PR
    b.EXPECTED_ORDINAL=ORDINAL; b.EXPECTED_EXECUTION_KEY=EXECUTION_KEY; b.EXPECTED_SEED_CANONICAL=SEED_CANONICAL
    b.ADAPTER_PATH=ADAPTER_PATH; b.CONTRACT_PATH=CONTRACT_PATH
    b.validate_bound_sources=validate_bound_sources; b.load_contract=load_contract; b.validate_authorization=validate_authorization; b.validate_guard=validate_guard
    return b

def execute_case(*args,**kwargs):
    return _configured().execute_case(*args,**kwargs)
'''

AGGREGATOR = r'''from __future__ import annotations
import hashlib, importlib.util, json, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py"
ADAPTER_PATH=Path(__file__).with_name("runtime_adapter.py")
CONTRACT_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3-runtime-identity-v1/identity-contract.review.json"
BASE_BLOB="ef24a0d30af3dfb46a6b764f3e426465da870fbe"
STAGE="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3"
ORDINAL=44
EXECUTION_KEY="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery3:numerical:44"
AUTH_HEAD="dd3a4c692af505389e9feb1e5f5480fa389110a3"
SEED_CANONICAL="d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf"
FOUR_ALIAS="5e1814dd36cf861fd85477a97607299248f8272268df7bf428d31bbb6aa4354a"

class AggregateRefusal(RuntimeError): pass

def git_blob_sha1(path: Path)->str:
    raw=path.read_bytes(); return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise AggregateRefusal(f"cannot load {path}")
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def _configured(repository_root: Path, authorization_path: Path):
    if not BASE_PATH.is_file() or git_blob_sha1(BASE_PATH)!=BASE_BLOB: raise AggregateRefusal("base aggregator byte drift")
    b=load("avps_recovery3_base_aggregator",BASE_PATH); a=load("avps_recovery3_aggregate_adapter",ADAPTER_PATH)
    b.STAGE=STAGE; b.EXPECTED_ORDINAL=ORDINAL; b.EXPECTED_EXECUTION_KEY=EXECUTION_KEY; b.EXPECTED_AUTH_HEAD=AUTH_HEAD; b.EXPECTED_SEED_CANONICAL=SEED_CANONICAL; b.EXPECTED_FOUR_ALIAS_TREE=FOUR_ALIAS
    def state(root):
        c=json.loads((root/CONTRACT_PATH.relative_to(ROOT)).read_text()); auth=json.loads(authorization_path.read_text())
        if c.get("scientificOrdinal")!=ORDINAL or c.get("executionKey")!=EXECUTION_KEY: raise AggregateRefusal("contract identity drift")
        try: a.validate_authorization(auth); cases=a.authorized_case_universe(auth)
        except Exception as e: raise AggregateRefusal(str(e)) from e
        if len(cases)!=360 or len({r["groupId"] for r in cases})!=72: raise AggregateRefusal("authorized universe drift")
        d=load("avps_recovery3_aggregate_derived",root/"experiments/aerosol-family-challenge-v2-r8/derived_channels.py")
        return c,auth,a,d
    b.load_and_validate_bound_state=state
    return b,a

def aggregate(repository_root: Path, artifact_root: Path, artifact_metadata_path: Path, authorization_path: Path, *, workflow_run_id: int):
    b,_=_configured(repository_root,authorization_path); return b.aggregate(repository_root,artifact_root,artifact_metadata_path,workflow_run_id=workflow_run_id)

def structural_closed_aggregate_fixture(repository_root: Path, authorization_path: Path) -> dict:
    b,a=_configured(repository_root,authorization_path); auth=json.loads(authorization_path.read_text()); cases=a.authorized_case_universe(auth)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); artifacts=root/"artifacts"; artifacts.mkdir(); meta=[]
        for i,case in enumerate(cases,1):
            name="avps-v2-case-"+case["caseId"]; d=artifacts/name; d.mkdir(); (d/"case-result.json").write_text("{}\n")
            meta.append({"id":i,"name":name,"digest":"sha256:synthetic","size_in_bytes":3})
        mp=root/"metadata.json"; mp.write_text(json.dumps({"artifacts":meta}))
        original=b.validate_case_result; b.validate_case_result=lambda result,expected,**kwargs: {"fixture":True}
        try:
            acquisition,verified=b.aggregate(repository_root,artifacts,mp,workflow_run_id=1)
            if acquisition.get("status")!="COMPLETE_EXACT_360_CASE_ARTIFACT_UNIVERSE_RESULTS_STILL_CLOSED" or verified.get("status")!="COMPLETE_EXACT_360_ANALYSIS_INPUT_RESULTS_STILL_CLOSED": raise AggregateRefusal("closed status drift")
            if (acquisition.get("caseCount"),acquisition.get("groupCount"),acquisition.get("analysisCellCount"))!=(360,72,24): raise AggregateRefusal("closed aggregate cardinality drift")
            mp.write_text(json.dumps({"artifacts":meta[:-1]})); refused=False
            try: b.aggregate(repository_root,artifacts,mp,workflow_run_id=1)
            except Exception: refused=True
            if not refused: raise AggregateRefusal("359-case fixture did not refuse")
        finally: b.validate_case_result=original
    return {"exact360ClosedAggregateCompatible":True,"missingCaseRefused":True,"caseCount":360,"groupCount":72,"analysisCellCount":24,"statesPerGroup":5,"resultOpeningAuthorized":False}
'''


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    check_sources(); OUT.mkdir(parents=True, exist_ok=True)
    write("runtime_adapter.py", ADAPTER); write("executor.py", EXECUTOR); write("aggregator.py", AGGREGATOR)
    outputs={p.name:{"sha256":sha256(p.read_bytes()),"size":p.stat().st_size} for p in sorted(OUT.glob("*.py"))}
    manifest={"schemaVersion":1,"status":"GENERATED_AVPS_V2_RECOVERY3_ORDINAL44_RUNTIME_IDENTITY_ZERO_RUNTIME","sourceMain":"e9f79772f07e2a90974979f187be137606c3dfea","controllingDefectComment":5470658421,"failedPublisherRun":33329476520,"scientificOrdinal":44,"authorizationHead":"dd3a4c692af505389e9feb1e5f5480fa389110a3","authorizationPr":718,"candidateSeedCanonicalSha256":"d2817b1ea4f2bdc8cb1842e565b099b015e4e28c5874482629fadc450069d9bf","caseCount":360,"groupCount":72,"statesPerGroup":5,"photonHistoriesPerCase":20_000_000,"frozenScienceChanged":False,"dispatchCreated":False,"scientificRuntime":False,"solverExecution":False,"resultsOpened":False,"levelB":False,"holdout":False,"taylorOrJerusalemUsed":False,"newMappingAuthorized":False,"outputs":outputs}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps(manifest,sort_keys=True))

if __name__=="__main__": main()
