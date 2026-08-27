from __future__ import annotations

import copy
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "experiments/aerosol-vertical-profile-sensitivity-v1"
ADAPTER_PATH = STAGE / "adapter.py"
ANALYSIS_PATH = STAGE / "analysis.py"

TAU = {
    "opac-profile-continental-average": "e6c296951dfae376bf77948aa92828062ba95d7b1e9c28703befa9cffb5bf198",
    "opac-profile-maritime-clean": "5cbaf5f81f3f36bfcf9b365eaa5d892889da83453c18d58e705b3de9273adc8c",
    "opac-profile-desert": "3d8891b3b67fa8c8c6fd66861d49e9bfad8c937a176b7001c6c47a5571de21ad",
    "opac-profile-arctic": "61eed1e73ac8cc6f044b89870a6874f1d21500008c7747830a2a812bbd87919a",
    "opac-profile-antarctic": "a14460a04afd5154d931b77e55b7adce2ab41aae2e8e4c13afaa0de459aff164",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def authorization() -> dict:
    return {
        "stageId": "aerosol-vertical-profile-sensitivity-v1",
        "status": "AUTHORIZED_PENDING_SEPARATE_DISPATCH",
        "scientificOrdinal": 40,
        "disabledExecutionPackageBlobSha1": "4b588e5eb289e9074935bf4ca22a4e2c6185bdb9",
        "disabledExecutionPackageCanonicalSha256": "ecf7052454e47a9e047cb944f22b031473c0986e9d8b9cec1aa010d425b39cc1",
        "candidateSeedCanonicalSha256": "a2e22b526dfad84d4f23c0ca8b143d028fddc7e55f78deb93a43e194ebd6c35e",
        "candidateRowsCanonicalSha256": "f22de8a9e30ba106759effb1170a5ca1d1e747cb2ac68293fa232dc7ed6ca683",
        "caseCount": 360,
        "commonRandomNumberGroupCount": 72,
        "statesPerGroup": 5,
        "photonHistoriesPerCase": 20_000_000,
        "scientificExecutionAuthorized": True,
        "solverExecutionAuthorized": True,
        "dispatchAuthorized": False,
        "resultOpeningAuthorized": False,
        "automaticDispatch": False,
        "productionAuthorized": False,
        "taylorOrJerusalemFitAuthorized": False,
        "exactAfglProfileTauSha256": dict(TAU),
    }


class AerosolVerticalProfileExecutionControlV1Tests(unittest.TestCase):
    def test_authorized_universe_reconstructs_exact_metadata_and_crn_pairing(self) -> None:
        adapter = load("avps_adapter_universe_test", ADAPTER_PATH)
        cases = adapter.authorized_case_universe(authorization())
        self.assertEqual(len(cases), 360)
        self.assertEqual(len({row["caseId"] for row in cases}), 360)
        groups = {}
        for row in cases:
            groups.setdefault(row["groupId"], []).append(row)
            self.assertEqual(row["photonHistories"], 20_000_000)
            self.assertIn(row["replicate"], (1, 2, 3))
            self.assertIn(row["sunDepressionDeg"], (2.0, 4.0, 6.0, 8.0))
            self.assertIn(row["aod550"], (0.10, 0.30))
            self.assertTrue(row["renderable"])
            self.assertTrue(row["executionAuthorized"])
            self.assertFalse(row["resultOpeningAuthorized"])
            self.assertEqual(row["scientificOrdinal"], 40)
        self.assertEqual(len(groups), 72)
        self.assertTrue(all(len(rows) == 5 for rows in groups.values()))
        self.assertTrue(all(len({r["stateId"] for r in rows}) == 5 for rows in groups.values()))
        self.assertTrue(all(len({r["seed"] for r in rows}) == 1 for rows in groups.values()))
        self.assertEqual(len({rows[0]["seed"] for rows in groups.values()}), 72)

    def test_render_uses_exact_frozen_surface_with_only_path_and_seed_substitution(self) -> None:
        adapter = load("avps_adapter_render_test", ADAPTER_PATH)
        auth = authorization()
        case = adapter.authorized_case(
            "dep20-aod10-g02-early-near-low-rep1--opac-profile-desert", auth
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            text = adapter.render_case_input(case, auth, root / "data", ROOT, root / "out")
        lines = text.splitlines()
        self.assertEqual(lines.count("rte_solver mystic"), 1)
        self.assertEqual(lines.count("mc_spherical 1D"), 1)
        self.assertEqual(lines.count("mc_vroom on"), 1)
        self.assertEqual(lines.count("mc_std"), 1)
        self.assertEqual(lines.count("mc_photons 20000000"), 1)
        self.assertEqual(lines.count("aerosol_species_file continental_average"), 1)
        self.assertEqual(lines.count("aerosol_file tau profiles/opac-profile-desert.tau"), 1)
        self.assertEqual(lines.count("aerosol_set_tau_at_wvl 550 0.100000"), 1)
        self.assertEqual(lines.count(f"mc_randomseed {case['seed']}"), 1)
        self.assertFalse(any(line.startswith("aerosol_modify ") for line in lines))
        self.assertFalse(any("<UNALLOCATED" in line or "<EXACT_" in line or "<REPOSITORY>" in line for line in lines))

    def test_adapter_refuses_frozen_source_or_authorization_drift(self) -> None:
        adapter = load("avps_adapter_refusal_test", ADAPTER_PATH)
        auth = authorization()
        bad = copy.deepcopy(auth)
        bad["photonHistoriesPerCase"] = 1
        with self.assertRaises(adapter.AdapterRefusal):
            adapter.authorized_case_universe(bad)
        original = adapter.EXPECTED_EXECUTION_CANDIDATE_BLOB
        adapter.EXPECTED_EXECUTION_CANDIDATE_BLOB = "0" * 40
        try:
            with self.assertRaises(adapter.AdapterRefusal):
                adapter.authorized_case_universe(auth)
        finally:
            adapter.EXPECTED_EXECUTION_CANDIDATE_BLOB = original

    def test_primary_analysis_is_only_four_alt_vs_reference_log_contrasts(self) -> None:
        analysis = load("avps_analysis_test", ANALYSIS_PATH)
        records = {
            "opac-profile-continental-average": {"photopicLuminanceCdM2": 10.0},
            "opac-profile-maritime-clean": {"photopicLuminanceCdM2": 20.0},
            "opac-profile-desert": {"photopicLuminanceCdM2": 5.0},
            "opac-profile-arctic": {"photopicLuminanceCdM2": 10.0},
            "opac-profile-antarctic": {"photopicLuminanceCdM2": 40.0},
        }
        out = analysis.scalar_replicate_contrasts(records, "photopicLuminanceCdM2")
        self.assertEqual(len(out), 4)
        self.assertAlmostEqual(out[analysis.contrast_name("opac-profile-maritime-clean")], math.log(2.0))
        self.assertAlmostEqual(out[analysis.contrast_name("opac-profile-desert")], math.log(0.5))
        self.assertAlmostEqual(out[analysis.contrast_name("opac-profile-arctic")], 0.0)
        self.assertAlmostEqual(out[analysis.contrast_name("opac-profile-antarctic")], math.log(4.0))

    def test_three_replicate_statistics_and_unresolved_policy_are_frozen(self) -> None:
        analysis = load("avps_analysis_stats_test", ANALYSIS_PATH)
        finite = analysis.summarize_three([1.0, 2.0, 3.0])
        self.assertEqual(finite["status"], "FINITE_THREE_REPLICATES")
        self.assertAlmostEqual(finite["mean"], 2.0)
        self.assertAlmostEqual(finite["sampleStd"], 1.0)
        self.assertAlmostEqual(finite["standardError"], 1.0 / math.sqrt(3.0))
        unresolved = analysis.summarize_three([1.0, None, 3.0])
        self.assertEqual(unresolved["status"], "NUMERICALLY_UNRESOLVED")
        self.assertIsNone(unresolved["mean"])
        self.assertIsNone(unresolved["sampleStd"])
        self.assertIsNone(unresolved["standardError"])


if __name__ == "__main__":
    unittest.main()
