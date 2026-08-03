from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "experiment/runner.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_module("corrected_runner", RUNNER_PATH)


class ContractTests(unittest.TestCase):
    def test_frozen_contract_is_valid_and_authorization_is_disabled(self):
        manifest, contract, baseline = runner.load_frozen()
        self.assertEqual(manifest["stageId"], runner.STAGE_ID)
        self.assertTrue(contract["successDoesNotAuthorizeProduction"])
        self.assertEqual(len(baseline["cases"]), 12)
        auth = runner.load_json(runner.AUTH_PATH)
        self.assertIs(auth["authorized"], False)
        self.assertIs(auth["runMystic"], False)
        self.assertIs(auth["runUvspec"], False)

    def test_grid_exactly_covers_requested_domain_and_nodes(self):
        grid = runner.parse_grid()
        self.assertEqual([grid[0], grid[-1]], [380, 780])
        self.assertTrue(set(runner.SELECTED_NODES).issubset(grid))
        self.assertIn(405, range(grid[0], grid[-1] + 1))

    def test_mismatched_grid_is_rejected_before_solver(self):
        manifest = runner.load_json(runner.MANIFEST_PATH)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-grid.dat"
            path.write_text("470\n480\n660\n", encoding="utf-8")
            with self.assertRaises(runner.Refusal) as raised:
                runner.validate_manifest(manifest, path)
        self.assertEqual(raised.exception.code, "grid-domain-mismatch")

    def test_fresh_case_set_and_photon_ceiling(self):
        manifest = runner.load_json(runner.MANIFEST_PATH)
        cases = runner.cases_from_manifest(manifest)
        self.assertEqual(len(cases), 12)
        self.assertEqual(sum(case["photonHistories"] for case in cases), 1_200_000_000)
        used = set(range(76701, 77007))
        fresh = {case["seed"] for case in cases}
        self.assertTrue(used.isdisjoint(fresh))

    def test_reference_input_contains_corrected_grid_and_domain(self):
        manifest = runner.load_json(runner.MANIFEST_PATH)
        reference = runner.cases_from_manifest(manifest)[6]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = runner.render_input(reference, root / "data", root / "atm.dat", root / "case", runner.GRID_PATH)
        self.assertIn(f"wavelength_grid_file {runner.GRID_PATH}", text)
        self.assertIn("wavelength 380 780", text)
        self.assertNotIn("mc_spectral_is", text)

    def test_alis_input_keeps_importance_wavelength_inside_domain(self):
        manifest = runner.load_json(runner.MANIFEST_PATH)
        alis = runner.cases_from_manifest(manifest)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = runner.render_input(alis, root / "data", root / "atm.dat", root / "case", runner.GRID_PATH)
        self.assertIn("mc_spectral_is 405.0", text)
        self.assertNotIn("wavelength_grid_file", text)

    def test_analysis_recomputes_complete_classification(self):
        baseline = runner.load_json(runner.BASELINE_PATH)
        contract = runner.load_json(runner.CONTRACT_PATH)
        alis_cases = [case for case in baseline["cases"] if case["method"] == "alis"]
        reference_cases = [case for case in baseline["cases"] if case["method"] == "reference"]
        alis_means = [sum(case["selectedNodeRadiance"][i] for case in alis_cases) / 6 for i in range(15)]
        reference_means = [sum(case["selectedNodeRadiance"][i] for case in reference_cases) / 6 for i in range(15)]
        common = [(a ** 0.35) * (r ** 0.65) for a, r in zip(alis_means, reference_means)]
        factors = [0.98, 1.01, 0.99, 1.02, 0.97, 1.03]
        records = []
        for method, seeds, photons in (("alis", range(77101, 77107), 40_000_000), ("reference", range(77201, 77207), 160_000_000)):
            for seed, factor in zip(seeds, factors):
                values = [value * factor for value in common]
                records.append({
                    "method": method,
                    "seed": seed,
                    "photonHistories": photons,
                    "selectedNodeRadiance": values,
                    "selectedPhotopicContributionCdM2": runner.selected_contribution(values),
                })
        result = runner.analyze(records, baseline, contract)
        self.assertEqual(result["classification"], "BOTH_CONVERGE_AND_AGREE")

    def test_proposal_never_authorizes_execution(self):
        proposal = runner.proposal()
        self.assertTrue(proposal["authorizationRequired"])
        self.assertFalse(proposal["executionAuthorizedByProposal"])
        self.assertEqual(proposal["requiredAuthorizationBranch"], runner.AUTH_BRANCH)
        self.assertEqual(proposal["expectedHashes"]["maximumSolverExecutionCount"], 12)


if __name__ == "__main__":
    unittest.main()
