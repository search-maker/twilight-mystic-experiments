from __future__ import annotations
import hashlib, importlib.util, json, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE_PATH=ROOT/"review/aerosol-vertical-profile-sensitivity-v2-aggregator-parity-v1/aggregator.py"
ADAPTER_PATH=Path(__file__).with_name("runtime_adapter.py")
CONTRACT_PATH=Path(__file__).with_name("runtime_contract.json")
BASE_BLOB="ef24a0d30af3dfb46a6b764f3e426465da870fbe"
STAGE="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4"
ORDINAL=45
EXECUTION_KEY="aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4:numerical:45"
AUTH_HEAD="6e095b4b1603c90dcee0943295909b30cd1b374d"
SEED_CANONICAL="ddded6b2d170ca2fac8d498bdba2887446c16995df0880d948fb2be00870b3de"
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
    b=load("avps_recovery4_base_aggregator",BASE_PATH); a=load("avps_recovery4_aggregate_adapter",ADAPTER_PATH)
    b.STAGE=STAGE; b.EXPECTED_ORDINAL=ORDINAL; b.EXPECTED_EXECUTION_KEY=EXECUTION_KEY; b.EXPECTED_AUTH_HEAD=AUTH_HEAD; b.EXPECTED_SEED_CANONICAL=SEED_CANONICAL; b.EXPECTED_FOUR_ALIAS_TREE=FOUR_ALIAS
    def state(root):
        c=json.loads(CONTRACT_PATH.read_text()); auth=json.loads(authorization_path.read_text())
        if c.get("scientificOrdinal")!=ORDINAL or c.get("executionKey")!=EXECUTION_KEY: raise AggregateRefusal("contract identity drift")
        try: a.validate_authorization(auth); cases=a.authorized_case_universe(auth)
        except Exception as e: raise AggregateRefusal(str(e)) from e
        if len(cases)!=360 or len({r["groupId"] for r in cases})!=72: raise AggregateRefusal("authorized universe drift")
        d=load("avps_recovery4_aggregate_derived",root/"experiments/aerosol-family-challenge-v2-r8/derived_channels.py")
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
