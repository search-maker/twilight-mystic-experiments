from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-scenario-interpolation-validation-v1"
EXECD = STAGE / "execution-candidate"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def proof(head: str = "a" * 40) -> dict:
    return {
        "schemaVersion": 1,
        "stageId": "aerosol-scenario-interpolation-validation-v1-preauthorization-freshness-proof",
        "status": "PASS_ASIV_SEED_AND_GEOMETRY_AUTHORIZATION_RECHECK_NOT_ALLOCATED",
        "auditedMainHead": head,
        "candidateSeedCount": 24,
        "candidateSeedCanonicalSha256": "cd04e0f7a206ca7fd49f3b00eae8de6d49ba8dc1427c21e5c7530adf03837040",
        "candidateRowsCanonicalSha256": "d88da58b6fe896b8324df224c5e849399b770783d4d63bb2bc4a7b01aa844e8b",
        "allCollisionCountersZero": True,
        "trackedTreeExternalCollisionCount": 0,
        "repositoryGlobalCollisionCount": 0,
        "repositoryGlobalDoubleEnumerationStable": True,
        "repositoryGlobalStableContextSha256": "1" * 64,
        "holdoutGeometryCount": 8,
        "trackedGeometryCollisionCount": 0,
        "metadataGeometryCollisionCount": 0,
        "geometryMetadataStableContextSha256": "2" * 64,
        "scientificOrdinalAllocated": False,
        "authorizationCreated": False,
        "dispatchCreated": False,
        "scientificExecutionAuthorized": False,
        "solverExecutionAuthorized": False,
        "resultOpeningAuthorized": False,
    }


def test_seeded_review_design_is_exact_24_group_120_case_crn_universe():
    design_mod = load("asiv_design_test", STAGE / "execution_design.py")
    transport = load("asiv_transport_test", STAGE / "execution_transport.py")
    d = design_mod.build_review_execution_design(proof(), "a" * 40)
    transport.validate_authorized_design(ROOT, d)
    assert d["status"] == "CANDIDATE_SEEDED_DESIGN_FRESHNESS_PROVEN_REVIEW_ONLY"
    assert d["groupCount"] == 24 and d["caseCount"] == 120 and d["holdoutGeometryCount"] == 8
    assert d["candidateSeedsAllocated"] is True and d["candidateSeedFreshnessProven"] is True
    assert d["scientificOrdinalAllocated"] is False and d["authorizationCreated"] is False and d["dispatchCreated"] is False
    seeds = {g["groupId"]: g["seed"] for g in d["groups"]}
    assert len(seeds) == 24 and len(set(seeds.values())) == 24
    for gid, seed in seeds.items():
        rows = [c for c in d["cases"] if c["groupId"] == gid]
        assert len(rows) == 5 and {c["seed"] for c in rows} == {seed}
        assert all(c["renderable"] is False and c["executionAuthorized"] is False for c in rows)


def test_geometry_recheck_is_mandatory_for_every_control_transition():
    freshness = load("asiv_freshness_test", EXECD / "freshness.py")
    with pytest.raises(Exception, match="geometry"):
        freshness._geometry({"candidateGeometryAuthorizationRecheckPassed": False})
    freshness._geometry({"candidateGeometryAuthorizationRecheckPassed": True})


def test_authorization_builder_is_deterministic_closed_dispatch_document():
    builder = load("asiv_builder_test", EXECD / "build_authorization.py")
    guard = load("asiv_guard_test", EXECD / "authorization_guard.py")
    a = builder.build(ROOT, "a" * 40, 39, proof())
    b = builder.build(ROOT, "a" * 40, 39, proof())
    assert a == b
    assert a["status"] == "AUTHORIZED_PENDING_SEPARATE_DISPATCH"
    assert a["scientificOrdinal"] == 39
    assert a["authorizationBranch"] == "authorization/aerosol-scenario-interpolation-validation-v1-ordinal-39"
    assert a["dispatchBranch"] == "dispatch/aerosol-scenario-interpolation-validation-v1-ordinal-39"
    assert a["caseCount"] == 120 and a["groupCount"] == 24 and a["holdoutGeometryCount"] == 8
    assert a["scientificExecutionAuthorized"] is True and a["solverExecutionAuthorized"] is True
    for key in ("dispatchAuthorized", "resultOpeningAuthorized", "automaticDispatch", "consumed", "githubRerunAllowed", "retryAllowed", "resumeAllowed", "postHoldoutRetuningAllowed", "productionAuthorized"):
        assert a[key] is False
    assert a["selectedModelCanonicalSha256"] == "0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af"
    guard.validate_enabled_document(ROOT, a, "a" * 40, proof())
    assert {"authorizationReviewWorkflow", "dispatchPublisherWorkflow", "scientificExecutionWorkflow", "boundHumanThreshold", "runtimeOverlay"} <= set(a["byteBindings"])


def test_workflow_boundaries_are_separate_and_fail_closed():
    auth = (ROOT / ".github/workflows/asiv-v1-authorization-review.yml").read_text()
    publisher = (ROOT / ".github/workflows/asiv-v1-dispatch-publisher.yml").read_text()
    science = (ROOT / ".github/workflows/asiv-v1-execution.yml").read_text()
    assert "pull_request:" in auth and "setup-micromamba" not in auth and "command -v uvspec" not in auth
    assert "DISPATCH_PUBLISHED_ZERO_RUNTIME" in publisher and "setup-micromamba" not in publisher and "command -v uvspec" not in publisher
    assert "workflow_dispatch:" in science and "max-parallel: 8" in science
    assert "asiv-v1-case-${{ matrix.caseId }}" in science and "exact 120 unique current-run case artifacts" in science
    assert "bound-human-threshold.mjs" in science
    assert "production=false" in science and "starsvisibility_mutation=false" in science
    assert ".github/dispatch-requests/asiv-v1.json" not in [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("asiv-v1.json")]
