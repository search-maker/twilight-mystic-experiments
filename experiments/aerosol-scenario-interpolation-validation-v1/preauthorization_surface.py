from __future__ import annotations
import hashlib, importlib.util, re
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
AOPS=ROOT/"experiments/aerosol-optical-property-sensitivity-v1/execution-candidate"
AFPF=ROOT/"experiments/aerosol-full-phase-function-sensitivity-v1/execution-candidate"
AOPS_CONTROL_BLOB="bc6d5a565b2b98f496793b35b226a334ba6b87f4"
AOPS_GLOBAL_BLOB="27f8ac62bc8a520ab22b0215e847ef878db5aa5f"
AFPF_FRESHNESS_BLOB="eca41233f3e91b06dd08172d74ef990d18d9ef7d"
STAGE="aerosol-scenario-interpolation-validation-v1"
TOKEN="ASIV_V1"
AUTHORIZATION_PATH=f"experiments/{STAGE}/authorization.json"
CASE_ARTIFACT_PREFIX="asiv-v1-case-"

class Refusal(RuntimeError): pass

def blob(p:Path)->str:
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(name:str,path:Path,want:str):
    if blob(path)!=want: raise Refusal(f"bound source byte drift: {path}")
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def failed_history(payload:dict[str,Any],ordinal:int)->dict[str,Any]:
    pat=re.compile(rf"^history/{re.escape(STAGE)}-ordinal-{ordinal}-auth-review-failed-([1-9][0-9]*)$",re.I)
    found=[str(r.get("name") or "") for r in payload.get("branches",[]) if pat.fullmatch(str(r.get("name") or ""))]
    if found: raise Refusal("ASIV failed-authorization history exists; separately reviewed recovery required")
    return {"heads":[],"prNumbers":[],"reviewRunIds":[]}

def modules():
    freshness=load("asiv_bound_freshness",AFPF/"freshness.py",AFPF_FRESHNESS_BLOB); freshness.STAGE_ID=STAGE; freshness.STAGE_TOKEN=TOKEN
    control=load("asiv_bound_control",AOPS/"control_surface.py",AOPS_CONTROL_BLOB); ordinal=load("asiv_bound_global_ordinal",AOPS/"global_ordinal.py",AOPS_GLOBAL_BLOB)
    control.authorization_branch=freshness.authorization_branch; control.dispatch_branch=freshness.dispatch_branch; control.execution_key=freshness.execution_key
    control.matching_marker=freshness.matching_marker; control.positive_candidate_claims=freshness.positive_candidate_claims; control.consumed_marker=freshness.consumed_marker
    control.AUTHORIZATION_PATH=AUTHORIZATION_PATH; control.CASE_ARTIFACT_PREFIX=CASE_ARTIFACT_PREFIX; control.failed_authorization_history=failed_history
    return freshness,control,ordinal

def collect(repository:str,token:str)->dict[str,Any]:
    _,c,_=modules(); return c.collect(repository,token)

def latest_consumed(payload:dict[str,Any])->int|None:
    _,c,_=modules(); return c.latest_consumed_or_dispatched_ordinal(payload)

def derive_next(payload:dict[str,Any],latest:int,current_run_id:int|None=None):
    _,_,o=modules(); return o.derive_next_global_ordinal(payload,latest,current_run_id=current_run_id)

def build(payload:dict[str,Any],ordinal:int,current_run_id:int|None,seed_ok:bool,geometry_ok:bool)->dict[str,Any]:
    f,c,_=modules()
    if not geometry_ok: raise Refusal("repository-wide holdout geometry freshness did not pass")
    surface=c.build_surface(payload,ordinal,current_run_id=current_run_id,active_authorization_path_on_main_exists=False,candidate_code_paths_on_main_inspected=True,candidate_seed_authorization_recheck_passed=seed_ok,allow_authorization_branch=False,allow_dispatch_branch=False)
    surface["nextAvailableScientificOrdinal"]=ordinal; f.validate_preauthorization(surface,ordinal); surface["candidateGeometryAuthorizationRecheckPassed"]=True; return surface

def identity(ordinal:int)->dict[str,str]:
    f,_,_=modules(); return {"authorizationBranch":f.authorization_branch(ordinal),"dispatchBranch":f.dispatch_branch(ordinal),"executionKey":f.execution_key(ordinal)}
