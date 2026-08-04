from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "experiments/mystic-batch-v1"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class StageThreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.convergence = module("convergence_v2", PKG / "cross_geometry_convergence_v2.py")
        cls.stage3 = module("stage3", PKG / "cross_geometry_stage_three.py")
        cls.adapter = module("stage3_adapter", PKG / "cross_geometry_stage_three_execution_adapter.py")
        cls.screening_path = PKG / "results/stage-two-screening-analysis.json"
        cls.convergence_path = PKG / "results/convergence-v2.stage-two.json"
        cls.provenance_path = PKG / "results/stage-three-source-provenance.json"
        cls.proposal_path = PKG / "manifest.cross-geometry-stage-three.proposal.json"

    def test_corrected_convergence_is_reproducible(self):
        source = json.loads(self.screening_path.read_text())
        expected = json.loads(self.convergence_path.read_text())
        actual = self.convergence.analyze(source)
        self.assertEqual(actual, expected)
        by_group = {item["groupId"]: item for item in actual["geometryResults"]}
        self.assertEqual(by_group["g04-mid-perpendicular"]["classification"], "CONVERGED_SCREENING_AGREEMENT")
        self.assertAlmostEqual(by_group["g04-mid-perpendicular"]["ratioRelativeStandardError"], 0.06463023239621378)
        self.assertFalse(by_group["g01-reference-bridge"]["reportedStdDiagnostics"]["alisReportedStdUsable"])

    def test_stage_three_proposal_is_reproducible_and_bounded(self):
        expected = json.loads(self.proposal_path.read_text())
        actual = self.stage3.build(self.convergence_path, self.provenance_path)
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual["cases"]), 24)
        self.assertEqual(sum(case["photonHistories"] for case in actual["cases"]), 480_000_000)
        self.assertEqual(len({case["seed"] for case in actual["cases"]}), 24)
        self.assertNotIn("g04-mid-perpendicular", {case["groupId"] for case in actual["cases"]})
        candidates = {
            float(case["alisSpectralImportanceSamplingNm"])
            for case in actual["cases"]
            if case["groupId"] in {"g01-reference-bridge", "g06-late-opposite-high-aerosol"} and case["method"] == "alis"
        }
        self.assertEqual(candidates, {500.0, 550.0, 600.0})

    def test_adapter_renders_per_case_importance_wavelength(self):
        proposal = json.loads(self.proposal_path.read_text())
        self.adapter.validate_manifest(proposal)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            repo = root / "repo"
            for path in (
                data / "atmmod/afglus.dat",
                data / "solar_flux/atlas_plus_modtran",
                repo / "experiments/reference-vroom-v1/wavelength-grid.dat",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n")
            runtime = {
                "schemaVersion": 1,
                "stageId": "mystic-batch-v1",
                "scientificSolverExecuted": False,
                "syntaxCheckExecuted": False,
                **{field: proposal["runtime"][field] for field in (
                    "uvspecSha256", "uvspecHelpSha256", "libRadtranDataTreeSha256", "atmosphereSha256", "runtimeLockRawSha256"
                )},
            }
            runtime_path = root / "runtime.json"
            runtime_path.write_text(json.dumps(runtime))
            prepared = self.adapter.prepare_case(
                self.proposal_path,
                runtime_path,
                "cg3-g01-alis-is550-r1",
                data,
                repo,
                root / "output",
            )
            text = Path(prepared["inputPath"]).read_text()
            self.assertIn("mc_spectral_is 550.0", text)
            self.assertIn("mc_vroom off", text)
            self.assertEqual(prepared["alisSpectralImportanceSamplingNm"], 550.0)

    def test_all_numbers_are_finite(self):
        values = json.loads(self.convergence_path.read_text())
        for result in values["geometryResults"]:
            self.assertTrue(math.isfinite(result["ratioRelativeStandardError"]))
            self.assertGreaterEqual(result["ratioRelativeStandardError"], 0.0)


if __name__ == "__main__":
    unittest.main()
