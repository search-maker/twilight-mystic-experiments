from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-full-phase-function-sensitivity-v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load test module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AerosolFullPhaseFunctionSensitivityV1ReviewTests(unittest.TestCase):
    def test_protocol_is_exact_review_only_five_state_universe(self) -> None:
        p = json.loads((STAGE / "protocol.review.json").read_text())
        self.assertEqual(p["stageId"], "aerosol-full-phase-function-sensitivity-v1")
        self.assertEqual(p["status"], "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED")
        for key in (
            "scientificExecutionAuthorized",
            "solverExecutionAuthorized",
            "resultOpeningAuthorized",
            "candidateSeedsAllocated",
            "scientificOrdinalAllocated",
        ):
            self.assertIs(p[key], False)
        self.assertEqual(
            [s["stateId"] for s in p["aerosolStates"]],
            [
                "native-rural-ss",
                "opac-continental-average",
                "opac-maritime-clean",
                "opac-desert",
                "opac-desert-spheroids",
            ],
        )
        self.assertEqual(
            p["caseCardinality"],
            {
                "analysisCells": 24,
                "replicatesPerCell": 3,
                "statesPerGroup": 5,
                "commonRandomNumberGroups": 72,
                "expectedCases": 360,
                "configuredPhotonHistories": 7_200_000_000,
            },
        )
        self.assertEqual(
            p["runtimeAndOpticalPropertyBinding"]["augmentedStagedDataTreeSha256"],
            "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80",
        )
        self.assertIs(p["commonRandomNumbers"]["candidateSeedsAllocatedInThisReview"], False)
        self.assertEqual(
            p["commonRandomNumbers"]["freshNamespaceRequired"],
            "aerosol-full-phase-function-sensitivity-v1|group-seed|sha256-v1",
        )

    def test_review_manifest_has_24_cells_72_seedless_groups_360_nonrenderable_cases(self) -> None:
        core = load("afpf_review_core_test", STAGE / "review_core.py")
        manifest = core.review_manifest()
        self.assertEqual(manifest["status"], "REVIEW_ONLY_CASE_SKELETONS_NON_RENDERABLE_NO_SEEDS")
        self.assertEqual(manifest["analysisCellCount"], 24)
        self.assertEqual(manifest["groupCount"], 72)
        self.assertEqual(manifest["caseCount"], 360)
        self.assertEqual(manifest["statesPerGroup"], 5)
        self.assertEqual(manifest["configuredPhotonHistories"], 7_200_000_000)
        self.assertIs(manifest["candidateSeedsAllocated"], False)
        self.assertIs(manifest["scientificOrdinalAllocated"], False)
        self.assertIs(manifest["scientificExecutionAuthorized"], False)
        self.assertIs(manifest["resultOpeningAuthorized"], False)
        groups = manifest["groups"]
        cases = manifest["cases"]
        self.assertTrue(all(g["seed"] is None and g["seedStatus"] == "UNALLOCATED_REVIEW_ONLY" for g in groups))
        self.assertTrue(all(c["seed"] is None and c["renderable"] is False and c["executionAuthorized"] is False for c in cases))
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
        self.assertEqual(len(by_group), 72)
        for members in by_group.values():
            self.assertEqual(len(members), 5)
            self.assertEqual({m["stateId"] for m in members}, expected_states)
            self.assertEqual({m["seed"] for m in members}, {None})

    def test_exact_native_and_opac_aerosol_surfaces(self) -> None:
        adapter = load("afpf_adapter_surface_test", STAGE / "adapter.py")
        self.assertEqual(
            adapter.aerosol_block("native-rural-ss", 0.10),
            [
                "aerosol_default",
                "aerosol_haze 1",
                "aerosol_vulcan 1",
                "aerosol_season 1",
                "aerosol_set_tau_at_wvl 550 0.100000",
            ],
        )
        expected = {
            "opac-continental-average": "continental_average",
            "opac-maritime-clean": "maritime_clean",
            "opac-desert": "desert",
            "opac-desert-spheroids": "desert_spheroids",
        }
        for state, mixture in expected.items():
            self.assertEqual(
                adapter.aerosol_block(state, 0.30),
                [
                    "aerosol_default",
                    "aerosol_species_library OPAC",
                    f"aerosol_species_file {mixture}",
                    "aerosol_set_tau_at_wvl 550 0.300000",
                ],
            )

    def test_adapter_refuses_review_case_before_fresh_seed_and_authorization(self) -> None:
        core = load("afpf_review_core_render_refusal_test", STAGE / "review_core.py")
        adapter = load("afpf_adapter_render_refusal_test", STAGE / "adapter.py")
        case = core.review_manifest()["cases"][0]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with self.assertRaisesRegex(adapter.Refusal, "non-renderable"):
                adapter.render_case_input(case, tmp_path / "data", ROOT, tmp_path / "out")

    def test_adapter_rejects_mixed_or_modified_aerosol_surfaces(self) -> None:
        adapter = load("afpf_adapter_mixed_surface_test", STAGE / "adapter.py")
        native = "\n".join(adapter.aerosol_block("native-rural-ss", 0.10) + ["aerosol_species_library OPAC"]) + "\n"
        with self.assertRaisesRegex(adapter.Refusal, "surface drift"):
            adapter.assert_exact_aerosol_surface(native, "native-rural-ss", 0.10)
        opac = "\n".join(adapter.aerosol_block("opac-desert", 0.10) + ["aerosol_modify gg set 0.70"]) + "\n"
        with self.assertRaisesRegex(adapter.Refusal, "surface drift"):
            adapter.assert_exact_aerosol_surface(opac, "opac-desert", 0.10)

    def test_analysis_contract_is_exact_seven_contrast_no_inference_contract(self) -> None:
        c = json.loads((STAGE / "analysis-contract.v1.json").read_text())
        self.assertEqual(c["status"], "FROZEN_REVIEW_ONLY_ANALYSIS_CONTRACT_RESULTS_NOT_OPENED")
        self.assertEqual(c["caseUniverse"]["caseCount"], 360)
        self.assertEqual(c["caseUniverse"]["commonRandomNumberGroupCount"], 72)
        self.assertEqual(
            [row["contrastId"] for row in c["contrasts"]],
            [
                "continental_vs_native",
                "maritime_vs_native",
                "desert_vs_native",
                "desert_spheroids_vs_native",
                "maritime_vs_continental",
                "desert_vs_continental",
                "desert_spheroids_vs_desert",
            ],
        )
        self.assertIs(c["replicateSummary"]["independentErrorQuadraturePermitted"], False)
        self.assertIs(c["replicateSummary"]["pValuesPermitted"], False)
        self.assertIs(c["replicateSummary"]["confidenceIntervalsPermitted"], False)
        self.assertIs(c["numericRules"]["epsilonSubstitutionPermitted"], False)
        self.assertIs(c["numericRules"]["dropUnresolvedReplicateAndUseRemainingReplicatesPermitted"], False)
        self.assertIs(c["implementationBoundary"]["analysisImplementationPresentInThisReview"], False)
        self.assertIs(c["implementationBoundary"]["analysisImplementationMustBeReviewedAndGitBlobBoundBeforeScience"], True)


if __name__ == "__main__":
    unittest.main()
