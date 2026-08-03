from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "mystic-batch-v1"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_module("cross_geometry_validate", PACKAGE / "cross_geometry_validate.py")
adapter = load_module("cross_geometry_adapter", PACKAGE / "cross_geometry_adapter.py")
analyzer = load_module("cross_geometry_analysis", PACKAGE / "cross_geometry_analysis.py")


class CrossGeometryProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = self.root / "manifest.json"
        self.contract = self.root / "contract.json"
        self.authorization = self.root / "authorization.json"
        shutil.copy2(PACKAGE / "manifest.cross-geometry-pilot.proposal.json", self.manifest)
        shutil.copy2(PACKAGE / "cross-geometry-contract.json", self.contract)
        shutil.copy2(PACKAGE / "authorization.cross-geometry-template.json", self.authorization)
        self.data = self.root / "data"
        self.repo = self.root / "repo"
        (self.data / "solar_flux").mkdir(parents=True)
        (self.data / "atmmod").mkdir(parents=True)
        (self.repo / "experiments/reference-vroom-v1").mkdir(parents=True)
        (self.data / "solar_flux/atlas_plus_modtran").write_text("solar\n")
        (self.data / "atmmod/afglus.dat").write_text("atmosphere\n")
        (self.repo / "experiments/reference-vroom-v1/wavelength-grid.dat").write_text("380\n470\n780\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_exact_proposal_contract(self) -> None:
        result = validator.validate(self.manifest, self.contract, self.authorization, PACKAGE / "cross_geometry_adapter.py")
        self.assertEqual(result["status"], "PROPOSAL_VALIDATED_NO_EXECUTION")
        self.assertEqual(result["caseCount"], 24)
        self.assertEqual(result["configuredMcPhotonsSum"], 480_000_000)

    def test_duplicate_seed_is_refused(self) -> None:
        manifest = json.loads(self.manifest.read_text())
        manifest["cases"][1]["seed"] = manifest["cases"][0]["seed"]
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(validator.ValidationFailure):
            validator.validate(self.manifest, self.contract, self.authorization, PACKAGE / "cross_geometry_adapter.py")

    def test_missing_method_block_is_refused(self) -> None:
        manifest = json.loads(self.manifest.read_text())
        manifest["cases"][-1]["method"] = "reference-vroom"
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(validator.ValidationFailure):
            validator.validate(self.manifest, self.contract, self.authorization, PACKAGE / "cross_geometry_adapter.py")

    def test_reference_and_alis_render_different_frozen_modes(self) -> None:
        out = self.root / "out"
        reference = adapter.prepare_case(self.manifest, "cg-g01-vroom-b1", self.data, self.repo, out)
        alis = adapter.prepare_case(self.manifest, "cg-g01-alis-b1", self.data, self.repo, out)
        reference_text = (out / reference["caseId"] / "input-resolved.txt").read_text()
        alis_text = (out / alis["caseId"] / "input-resolved.txt").read_text()
        self.assertIn("mc_vroom on", reference_text)
        self.assertIn("wavelength_grid_file", reference_text)
        self.assertNotIn("mc_spectral_is", reference_text)
        self.assertIn("mc_vroom off", alis_text)
        self.assertIn("mc_spectral_is 405.0", alis_text)
        self.assertNotIn("wavelength_grid_file", alis_text)

    def _synthetic_records(self, noisy: bool = False, disagree: bool = False):
        manifest = json.loads(self.manifest.read_text())
        records = []
        for case in manifest["cases"]:
            base = 10.0
            if case["method"] == "alis":
                base *= 3.0 if disagree else 1.1
            factor = 1.5 if noisy and case["block"] == 2 else (1.02 if case["block"] == 2 else 1.0)
            value = base * factor
            records.append({
                "caseId": case["caseId"],
                "status": "COMPLETED",
                "selectedPhotopicContributionCdM2": value,
                "selectedNodeRadiance": [value] * 15,
                "selectedNodeStdRadiance": [value * (0.15 if noisy else 0.02)] * 15
            })
        return {"records": records}

    def test_screening_agreement(self) -> None:
        records = self.root / "records.json"
        records.write_text(json.dumps(self._synthetic_records()))
        result = analyzer.analyze(self.manifest, self.contract, records)
        self.assertEqual(result["classificationCounts"]["SCREENING_AGREEMENT"], 6)

    def test_noisy_geometry_requires_more_blocks(self) -> None:
        records = self.root / "records.json"
        records.write_text(json.dumps(self._synthetic_records(noisy=True)))
        result = analyzer.analyze(self.manifest, self.contract, records)
        self.assertEqual(result["classificationCounts"]["NEEDS_MORE_BLOCKS"], 6)

    def test_stable_discrepancy_is_not_accepted(self) -> None:
        records = self.root / "records.json"
        records.write_text(json.dumps(self._synthetic_records(disagree=True)))
        result = analyzer.analyze(self.manifest, self.contract, records)
        self.assertEqual(result["classificationCounts"]["SCREENING_DISCREPANCY"], 6)


if __name__ == "__main__":
    unittest.main()
