from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "experiments" / "aerosol-vertical-profile-sensitivity-v1" / "execution_candidate.py"
spec = importlib.util.spec_from_file_location("vertical_profile_execution_candidate", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class VerticalProfileExecutionCandidateTests(unittest.TestCase):
    def test_exact_review_bindings(self):
        self.assertEqual(mod.validate_review_bindings(), mod.EXPECTED_GIT_BLOBS)

    def test_exact_360_case_72_group_unseeded_unrenderable_universe(self):
        d = mod.build_review_execution_skeleton()
        self.assertEqual(d["status"], "REVIEW_ONLY_EXECUTION_SKELETON_SEEDS_UNALLOCATED")
        self.assertEqual(d["caseCount"], 360)
        self.assertEqual(d["groupCount"], 72)
        self.assertEqual(d["statesPerGroup"], 5)
        self.assertEqual(d["seedCount"], 0)
        self.assertIsNone(d["scientificOrdinal"])
        self.assertFalse(d["scientificExecutionAuthorized"])
        self.assertFalse(d["solverExecutionAuthorized"])
        self.assertFalse(d["resultOpeningAuthorized"])
        self.assertFalse(d["productionAuthorized"])
        self.assertEqual(len({row["caseId"] for row in d["cases"]}), 360)
        self.assertEqual(len({row["groupId"] for row in d["groups"]}), 72)
        self.assertTrue(all(row["seed"] is None for row in d["cases"]))
        self.assertTrue(all(row["seedStatus"] == "UNALLOCATED_REVIEW_ONLY" for row in d["cases"]))
        self.assertTrue(all(row["renderable"] is False for row in d["cases"]))
        self.assertTrue(all(row["executionAuthorized"] is False for row in d["cases"]))
        self.assertTrue(all(row["resultOpeningAuthorized"] is False for row in d["cases"]))

    def test_each_group_contains_exactly_all_five_states_with_identical_pairing(self):
        d = mod.build_review_execution_skeleton()
        expected_states = {
            "opac-profile-continental-average",
            "opac-profile-maritime-clean",
            "opac-profile-desert",
            "opac-profile-arctic",
            "opac-profile-antarctic",
        }
        cases = {row["caseId"]: row for row in d["cases"]}
        for group in d["groups"]:
            self.assertEqual(set(group["stateIds"]), expected_states)
            self.assertEqual(len(group["caseIds"]), 5)
            self.assertIsNone(group["candidateSeed"])
            self.assertEqual(group["seedStatus"], "UNALLOCATED_REVIEW_ONLY")
            for case_id in group["caseIds"]:
                case = cases[case_id]
                self.assertEqual(case["groupId"], group["groupId"])
                for key, value in group["pairing"].items():
                    self.assertEqual(case[key], value)

    def test_frozen_design_cross_product_counts(self):
        d = mod.build_review_execution_skeleton()
        self.assertEqual(Counter(row["sunDepressionDeg"] for row in d["cases"]), {2.0: 90, 4.0: 90, 6.0: 90, 8.0: 90})
        self.assertEqual(Counter(row["aod550"] for row in d["cases"]), {0.1: 180, 0.3: 180})
        self.assertEqual(Counter(row["geometryId"] for row in d["cases"]), {
            "g02-early-near-low": 120,
            "g04-mid-perpendicular": 120,
            "g06-late-opposite-high-aerosol": 120,
        })
        self.assertEqual(Counter(row["replicate"] for row in d["cases"]), {1: 120, 2: 120, 3: 120})
        self.assertEqual(Counter(row["stateId"] for row in d["cases"]), {
            "opac-profile-continental-average": 72,
            "opac-profile-maritime-clean": 72,
            "opac-profile-desert": 72,
            "opac-profile-arctic": 72,
            "opac-profile-antarctic": 72,
        })

    def test_aerosol_surface_changes_only_tau_file_by_state_and_aod_by_group(self):
        d = mod.build_review_execution_skeleton()
        for row in d["cases"]:
            aerosol = row["aerosolDirectives"]
            self.assertEqual(aerosol[:3], [
                "aerosol_default",
                "aerosol_species_library OPAC",
                "aerosol_species_file continental_average",
            ])
            self.assertEqual(aerosol[3], f"aerosol_file tau profiles/{row['stateId']}.tau")
            self.assertEqual(aerosol[4], f"aerosol_set_tau_at_wvl 550 {row['aod550']:.6f}")
            self.assertFalse(any(line.startswith("aerosol_modify ") for line in aerosol))
            self.assertEqual(sum(line.startswith("aerosol_file tau ") for line in aerosol), 1)
            self.assertEqual(sum(line.startswith("aerosol_set_tau_at_wvl ") for line in aerosol), 1)

    def test_deterministic_canonical_skeleton(self):
        a = mod.build_review_execution_skeleton()
        b = mod.build_review_execution_skeleton()
        self.assertEqual(a["canonicalSkeletonSha256"], b["canonicalSkeletonSha256"])
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_refuses_byte_drift(self):
        original = dict(mod.EXPECTED_GIT_BLOBS)
        try:
            mod.EXPECTED_GIT_BLOBS["protocol.review.json"] = "0" * 40
            with self.assertRaises(mod.ExecutionCandidateError):
                mod.validate_review_bindings()
        finally:
            mod.EXPECTED_GIT_BLOBS.clear()
            mod.EXPECTED_GIT_BLOBS.update(original)


if __name__ == "__main__":
    unittest.main()
