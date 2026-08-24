import hashlib, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"experiments/aerosol-scenario-interpolation-validation-v1"
PROTOCOL=ROOT/"review/aerosol-scenario-interpolation-validation-v1/protocol.review.json"
SELECTED=ROOT/"review/aerosol-scenario-interpolation-validation-v1/selected-model-v1.json"
EVALUATOR=ROOT/"review/aerosol-scenario-interpolation-validation-v1/evaluate_selected_model_v1.py"
WORKFLOW=ROOT/".github/workflows/asiv-v1-preauthorization-audit.yml"

def blob(p):
    b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_module(name,p):
    s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_asiv_preauthorization_binds_frozen_science_without_allocating_ordinal39():
    assert blob(PROTOCOL)=="27923f9d40d35b001c15b20b7909e3fcd12fd833"
    assert blob(SELECTED)=="cacb4889c47c718333ac885664ecb243a0fc9d75"
    assert blob(EVALUATOR)=="063c49dbdd6626a3e67440c53508260ac7d23f70"
    p=json.loads(PROTOCOL.read_text()); s=json.loads(SELECTED.read_text())
    assert p["authorization"]["ordinal39Allocated"] is False and p["authorization"]["solverExecutionAuthorized"] is False
    assert s["scientificBoundary"]["ordinal39Allocated"] is False and s["scientificBoundary"]["freshHoldoutValuesOpened"] is False
    assert p["frozenExecutionEnvelopeIfLaterAuthorized"]["freshSeedCountRequired"]==24
    assert p["frozenExecutionEnvelopeIfLaterAuthorized"]["caseCount"]==120

def test_asiv_candidate_seed_ledger_is_exact_deterministic_24_group_candidate_only():
    mod=load_module("asiv_seed_ledger_test",STAGE/"seed_ledger.py"); x=mod.validate()
    assert x["candidateSeedCount"]==24 and len(set(x["candidateSeeds"]))==24
    assert x["candidateSeedFreshnessProven"] is False and x["scientificOrdinalAllocated"] is False
    assert x["authorizationPermitted"] is False and x["allCollisionCountersZero"] is True

def test_asiv_seed_scanners_and_geometry_audit_are_fail_closed_and_zero_science():
    tracked=(STAGE/"tracked_tree_seed_scan.py").read_text(); global_scan=(STAGE/"repository_global_seed_scan.py").read_text(); geom=(STAGE/"geometry_collision_audit.py").read_text(); proof=(STAGE/"build_freshness_proof.py").read_text()
    assert "exactly 24" in tracked and 'candidateSeedCount":24' in tracked
    assert 'candidateSeedCount":24' in global_scan
    assert "FAIL_HOLDOUT_GEOMETRY_COLLISION_PROTOCOL_MUST_RETIRE" in geom
    assert 'individualPointReplacementAllowed":False' in geom
    for text in (tracked,global_scan,geom,proof):
        low=text.lower(); assert "setup-micromamba" not in low and "uvspec" not in low and "libradtran" not in low

def test_asiv_preauthorization_surface_reuses_bound_global_control_and_is_stage_specific():
    text=(STAGE/"preauthorization_surface.py").read_text()
    assert 'STAGE="aerosol-scenario-interpolation-validation-v1"' in text and 'TOKEN="ASIV_V1"' in text
    assert 'AOPS_CONTROL_BLOB="bc6d5a565b2b98f496793b35b226a334ba6b87f4"' in text
    assert 'AOPS_GLOBAL_BLOB="27f8ac62bc8a520ab22b0215e847ef878db5aa5f"' in text
    assert 'AFPF_FRESHNESS_BLOB="eca41233f3e91b06dd08172d74ef990d18d9ef7d"' in text
    assert "candidateGeometryAuthorizationRecheckPassed" in text

def test_asiv_preauthorization_workflow_is_push_main_zero_runtime_not_allocation():
    text=WORKFLOW.read_text()
    assert "branches: [main]" in text and "ASIV-V1-PREAUTHORIZATION-RUN" in text
    assert "candidate_seeds=" in text and "geometry_collisions=" in text
    assert "latest != 38" in text and "candidate != 39" in text
    forbidden=("setup-micromamba","rubin-libradtran","command -v uvspec","git push ","workflow_dispatch:","repository_dispatch:","schedule:")
    assert not [x for x in forbidden if x in text]
    assert "scientific_identity_allocated=false" in text and "solver_execution=false" in text and "holdout_opened=false" in text
