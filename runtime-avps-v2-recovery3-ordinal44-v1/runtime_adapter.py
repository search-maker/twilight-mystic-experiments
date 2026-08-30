from __future__ import annotations
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
