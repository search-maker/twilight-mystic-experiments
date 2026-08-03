from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments" / "mystic-batch-v1"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def load(path: Path):
    return json.loads(path.read_text())


adapter = module("stage2_adapter_test", PKG / "cross_geometry_stage_two_execution_adapter.py")
plan = module("stage2_plan_test", PKG / "cross_geometry_stage_two_execution_plan.py")
driver = module("stage2_driver_test", PKG / "cross_geometry_stage_two_execution_analysis_driver.py")
analysis = module("stage2_analysis_test", PKG / "cross_geometry_analysis.py")


class StageTwoExecutionContractTests(unittest.TestCase):
    def setUp(self):
        self.proposal_path = PKG / "manifest.cross-geometry-stage-two.proposal.json"
        self.source_manifest_path = PKG / "manifest.cross-geometry-pilot.proposal.json"
        self.contract_path = PKG / "cross-geometry-contract.json"
        self.source_analysis_path = PKG / "results" / "screening-analysis.cross-geometry-pilot-screening-2.json"

    def test_active_authorization_is_exact_disabled_template(self):
        active = load(PKG / "authorization.cross-geometry-stage-two.json")
        template = load(PKG / "authorization.cross-geometry-stage-two-execution-template.json")
        self.assertEqual(active, template)
        self.assertIs(active["authorized"], False)
        self.assertIs(active["scientificExecution"], False)
        self.assertEqual(active["authorizationOrdinal"], 0)

    def test_adapter_renders_exact_vroom_and_alis_modes(self):
        proposal = load(self.proposal_path)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            repo = root / "repo"
            (data / "solar_flux").mkdir(parents=True)
            (data / "atmmod").mkdir(parents=True)
            (repo / "experiments/reference-vroom-v1").mkdir(parents=True)
            (data / "solar_flux/atlas_plus_modtran").write_text("solar\n")
            (data / "atmod/afglus.dat").write_text("atmosphere\n")
            (repo / "experiments/reference-vroom-v1/wavelength-grid.dat").write_text("380\n470\n780\n")
            runtime = root / "runtime.json"
            runtime.write_text(json.dumps({
                "schemaVersion": 1,
                "stageId": "mystic-batch-v1",
                "scientificSolverExecuted": False,
                "syntaxCheckExecuted": False,
                **{ey: proposal["runtime"][key] for key in (
                    "uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256",
                    "atmosphereSha256", "runtimeLockRawSha256",
                )},
            }))
            output = root / "out"
            vroom = adapter.prepare_case(self.proposal_path, runtime, "cg2-g01-vroom-b3", data, repo, output)
            alis = adapter.prepare_case(self.proposal_path, runtime, "cg2-g01-alis-b3", data, repo, output)
            vroom_text = Path(vroom["inputPath"]).read_text()
            alis_text = Path(alis["inputPath"]).read_text()
            self.assertIn("mc_vroom on", vroom_text)
            self.assertIn("wavelength_grid_file", vroom_text)
            self.assertNotIn("mc_spectral_is", vroom_text)
            self.assertIn("mc_vroom off", alis_text)
            self.assertIn("mc_spectral_is 405.0", alis_text)
            self.assertNotIn("wavelength_grid_file", alis_text)

    def test_plan_freezes_exact_16_cases_and_320m_photons(self):
        guard_path = Path(tempfile.mkstemp(suffix=".json")[1])
        try:
            guard_path.write_text(json.dumps({
                "status": "AUTHORIZED",
                "stageId": "cross-geometry-stage-two-v1",
                "batchId": "cross-geometry-stage-two-screening-v1",
                "proposalRawSha256": "1" * 64,
                "executionAdapterRawSha256": "2" * 64,
                "runtimeLockRawSha256": "3" * 64,
                "executionWorkflowRawSha256": "4" * 64,
                "authorizationRef": "5" * 40,
                "authorizationOrdinal": 3,
                "executionKey": "cross-geometry-stage-two-v1:screening:3",
                "sourceManifestRawSha256": "6" * 64,
                "sourceAnalysisRawSha256": "7" * 64,
                "sourceProvenanceRawSha256": "8" * 64,
                "sourceScientificRunId": 30856116586,
                "sourcePostprocessRunId": 30858046820,
            }))
            frozen = plan.build_plan(self.proposal_path, guard_path)
            self.assertEqual(frozen["caseCount"], 16)
            self.assertEqual(frozen["configuredMcPhotonsSum"], 320_000_000)
            self.assertEqual(len(frozen["matrix"]["include"]), 16)
            self.assertEqual({case["block"] for case in frozen["cases"]}, {3, 4})
            self.assertEqual(frozen["scientificAdapterRawSha256"], "2" * 64)
        finally:
            guard_path.unlink(missing_ok=True)

    def test_combined_analysis_uses_four_blocks_for_selected_groups(self):
        source = load(self.source_manifest_path)
        stage2 = load(self.proposal_path)
        contract = load(self.contract_path)
        source_screening = load(self.source_analysis_path)

        def record(manifest, case, value):
            return {
                "caseId": case["caseId"], "groupId": case["groupId"], "method": case["method"],
                "block": case["block"], "selectedPhotopicContributionCdM2": value,
                "selectedNodeRadiance": [value] * 15, "selectedNodeStdRadiance": [value * 0.01] * 15,
            }

        source_records = [record(source, case, 1.0 + case["block"] * 0.001) for case in source["cases"]]
        stage2_records = [record(stage2, case, 1.0 + case["block"] * 0.001) for case in stage2["cases"]]
        result = driver.analyze_combined(
            source, stage2, contract, source_screening, source_records, stage2_records, analysis
        )
        self.assertEqual(result["status"], "STAGE_TWO_SCREENING_ANALYZED")
        self.assertEqual(result["classificationCounts"]["SCREENING_AGREEMENT"], 6)
        selected = [item for item in result["geometryResults"] if not item["carriedForwardFromPilot"]]
        self.assertEqual(len(selected), 4)
        self.assertEqual({item["blocksPerMethodAnalyzed"] for item in selected}, {4})


if __name__ == "__main__":
    unittest.main()
