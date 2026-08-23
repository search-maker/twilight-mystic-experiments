from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_protocol_is_exact_review_only_five_state_universe() -> None:
    p = json.loads((STAGE / "protocol.review.json").read_text())
    assert p["stageId"] == "aerosol-full-phase-function-sensitivity-v1"
    assert p["status"] == "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED"
    for key in (
        "scientificExecutionAuthorized",
        "solverExecutionAuthorized",
        "resultOpeningAuthorized",
        "candidateSeedsAllocated",
        "scientificOrdinalAllocated",
    ):
        assert p[key] is False
    assert [s["stateId"] for s in p["aerosolStates"]] == [
        "native-rural-ss",
        "opac-continental-average",
        "opac-maritime-clean",
        "opac-desert",
        "opac-desert-spheroids",
    ]
    assert p["caseCardinality"] == {
        "analysisCells": 24,
        "replicatesPerCell": 3,
        "statesPerGroup": 5,
        "commonRandomNumberGroups": 72,
        "expectedCases": 360,
        "configuredPhotonHistories": 7_200_000_000,
    }
    assert p["runtimeAndOpticalPropertyBinding"]["augmentedStagedDataTreeSha256"] == (
        "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80"
    )
    assert p["commonRandomNumbers"]["candidateSeedsAllocatedInThisReview"] is False
    assert p["commonRandomNumbers"]["freshNamespaceRequired"] == (
        "aerosol-full-phase-function-sensitivity-v1|group-seed|sha256-v1"
    )


def test_review_manifest_has_24_cells_72_seedless_groups_360_nonrenderable_cases() -> None:
    core = load("afpf_review_core_test", STAGE / "review_core.py")
    manifest = core.review_manifest()
    assert manifest["status"] == "REVIEW_ONLY_CASE_SKELETONS_NON_RENDERABLE_NO_SEEDS"
    assert manifest["analysisCellCount"] == 24
    assert manifest["groupCount"] == 72
    assert manifest["caseCount"] == 360
    assert manifest["statesPerGroup"] == 5
    assert manifest["configuredPhotonHistories"] == 7_200_000_000
    assert manifest["candidateSeedsAllocated"] is False
    assert manifest["scientificOrdinalAllocated"] is False
    assert manifest["scientificExecutionAuthorized"] is False
    assert manifest["resultOpeningAuthorized"] is False
    groups = manifest["groups"]
    cases = manifest["cases"]
    assert all(g["seed"] is None and g["seedStatus"] == "UNALLOCATED_REVIEW_ONLY" for g in groups)
    assert all(c["seed"] is None and c["renderable"] is False and c["executionAuthorized"] is False for c in cases)
    by_group: dict[str, list[dict]] = {}
    for case in cases:
        by_group.setdefault(case["groupId"], []).append(case)
    expected_states = {
        "native-rural-ss",
        "opac-continental-average",
        "opac-maritime-clean",
        "opac-desert",
        "opac-desert-spheroids",
    }
    assert len(by_group) == 72
    for members in by_group.values():
        assert len(members) == 5
        assert {m["stateId"] for m in members} == expected_states
        assert {m["seed"] for m in members} == {None}


def test_exact_native_and_opac_aerosol_surfaces() -> None:
    adapter = load("afpf_adapter_surface_test", STAGE / "adapter.py")
    assert adapter.aerosol_block("native-rural-ss", 0.10) == [
        "aerosol_default",
        "aerosol_haze 1",
        "aerosol_vulcan 1",
        "aerosol_season 1",
        "aerosol_set_tau_at_wvl 550 0.100000",
    ]
    expected = {
        "opac-continental-average": "continental_average",
        "opac-maritime-clean": "maritime_clean",
        "opac-desert": "desert",
        "opac-desert-spheroids": "desert_spheroids",
    }
    for state, mixture in expected.items():
        assert adapter.aerosol_block(state, 0.30) == [
            "aerosol_default",
            "aerosol_species_library OPAC",
            f"aerosol_species_file {mixture}",
            "aerosol_set_tau_at_wvl 550 0.300000",
        ]


def test_adapter_refuses_review_case_before_fresh_seed_and_authorization(tmp_path: Path) -> None:
    core = load("afpf_review_core_render_refusal_test", STAGE / "review_core.py")
    adapter = load("afpf_adapter_render_refusal_test", STAGE / "adapter.py")
    case = core.review_manifest()["cases"][0]
    with pytest.raises(adapter.Refusal, match="non-renderable"):
        adapter.render_case_input(case, tmp_path / "data", ROOT, tmp_path / "out")


def test_adapter_rejects_mixed_or_modified_aerosol_surfaces() -> None:
    adapter = load("afpf_adapter_mixed_surface_test", STAGE / "adapter.py")
    native = "\n".join(adapter.aerosol_block("native-rural-ss", 0.10) + ["aerosol_species_library OPAC"]) + "\n"
    with pytest.raises(adapter.Refusal, match="surface drift"):
        adapter.assert_exact_aerosol_surface(native, "native-rural-ss", 0.10)
    opac = "\n".join(adapter.aerosol_block("opac-desert", 0.10) + ["aerosol_modify gg set 0.70"]) + "\n"
    with pytest.raises(adapter.Refusal, match="surface drift"):
        adapter.assert_exact_aerosol_surface(opac, "opac-desert", 0.10)


def test_analysis_contract_is_exact_seven_contrast_no_inference_contract() -> None:
    c = json.loads((STAGE / "analysis-contract.v1.json").read_text())
    assert c["status"] == "FROZEN_REVIEW_ONLY_ANALYSIS_CONTRACT_RESULTS_NOT_OPENED"
    assert c["caseUniverse"]["caseCount"] == 360
    assert c["caseUniverse"]["commonRandomNumberGroupCount"] == 72
    ids = [row["contrastId"] for row in c["contrasts"]]
    assert ids == [
        "continental_vs_native",
        "maritime_vs_native",
        "desert_vs_native",
        "desert_spheroids_vs_native",
        "maritime_vs_continental",
        "desert_vs_continental",
        "desert_spheroids_vs_desert",
    ]
    assert c["replicateSummary"]["independentErrorQuadraturePermitted"] is False
    assert c["replicateSummary"]["pValuesPermitted"] is False
    assert c["replicateSummary"]["confidenceIntervalsPermitted"] is False
    assert c["numericRules"]["epsilonSubstitutionPermitted"] is False
    assert c["numericRules"]["dropUnresolvedReplicateAndUseRemainingReplicatesPermitted"] is False
    assert c["implementationBoundary"]["analysisImplementationPresentInThisReview"] is False
    assert c["implementationBoundary"]["analysisImplementationMustBeReviewedAndGitBlobBoundBeforeScience"] is True
