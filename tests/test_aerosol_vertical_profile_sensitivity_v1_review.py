from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments" / "aerosol-vertical-profile-sensitivity-v1"
MODULE = BASE / "opac_vertical_templates.py"
PROTOCOL = BASE / "protocol.review.json"

spec = importlib.util.spec_from_file_location("opac_vertical_templates", MODULE)
vt = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = vt
spec.loader.exec_module(vt)

TARGET_GRID_KM = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 35, 40, 50, 70, 100, 120]


class VerticalProfileSensitivityReviewTests(unittest.TestCase):
    def test_source_table_values_and_first_layer_tau(self):
        expected = {
            "opac-profile-continental-average": (0.151, 2.0, 8.0, 0.133),
            "opac-profile-maritime-clean": (0.096, 2.0, 1.0, 0.078),
            "opac-profile-desert": (0.286, 6.0, 2.0, 0.268),
            "opac-profile-arctic": (0.063, 2.0, 99.0, 0.045),
            "opac-profile-antarctic": (0.072, 10.0, 8.0, 0.054),
        }
        self.assertEqual(set(vt.PROFILE_STATES), set(expected))
        for state_id, (total, h, z, first) in expected.items():
            with self.subTest(state_id=state_id):
                state = vt.PROFILE_STATES[state_id]
                self.assertAlmostEqual(state["totalTau550"], total, places=15)
                self.assertAlmostEqual(state["firstLayerTopKm"], h, places=15)
                self.assertAlmostEqual(state["firstLayerScaleHeightKm"], z, places=15)
                tau = vt.state_component_tau550(state_id)
                self.assertAlmostEqual(tau["firstLayer"], first, places=15)
                self.assertAlmostEqual(tau["freeTroposphere"], 0.013, places=15)
                self.assertAlmostEqual(tau["stratosphere"], 0.005, places=15)
                self.assertAlmostEqual(tau["total"], total, places=15)

    def test_each_template_reproduces_frozen_component_shares(self):
        for state_id, state in vt.PROFILE_STATES.items():
            with self.subTest(state_id=state_id):
                fractions = vt.layer_tau_fractions(TARGET_GRID_KM, state_id)
                self.assertAlmostEqual(math.fsum(fractions), 1.0, places=14)
                self.assertTrue(all(value >= 0 for value in fractions))
                h = state["firstLayerTopKm"]
                total = state["totalTau550"]
                first = free = strat = above = 0.0
                for lo, hi, value in zip(TARGET_GRID_KM, TARGET_GRID_KM[1:], fractions):
                    if hi <= h:
                        first += value
                    elif lo >= h and hi <= 12:
                        free += value
                    elif lo >= 12 and hi <= 35:
                        strat += value
                    elif lo >= 35:
                        above += value
                    else:
                        self.fail(f"test grid unexpectedly straddles frozen boundary: {lo}-{hi} for {state_id}")
                self.assertAlmostEqual(first, vt.state_component_tau550(state_id)["firstLayer"] / total, places=13)
                self.assertAlmostEqual(free, 0.013 / total, places=13)
                self.assertAlmostEqual(strat, 0.005 / total, places=13)
                self.assertAlmostEqual(above, 0.0, places=15)

    def test_renderer_reuses_merged_lower_bound_tau_contract(self):
        for state_id in vt.PROFILE_STATES:
            with self.subTest(state_id=state_id):
                text = vt.render_libradtran_tau(TARGET_GRID_KM, state_id)
                rows = [line for line in text.splitlines() if line and not line.startswith("#")]
                self.assertEqual(rows[0].split()[0], "120.000000000")
                self.assertEqual(float(rows[0].split()[1]), 0.0)
                self.assertEqual(rows[-1].split()[0], "0.000000000")
                self.assertAlmostEqual(math.fsum(float(row.split()[1]) for row in rows), 1.0, places=14)

    def test_v1_rejects_non_sea_level_or_too_low_top_grid(self):
        with self.assertRaises(vt.VerticalTemplateError):
            vt.layer_tau_fractions([0.8, 2, 12, 35, 120], vt.REFERENCE_STATE_ID)
        with self.assertRaises(vt.VerticalTemplateError):
            vt.layer_tau_fractions([0, 2, 12, 30], vt.REFERENCE_STATE_ID)

    def test_protocol_is_execution_disabled_and_exact_cardinality(self):
        p = json.loads(PROTOCOL.read_text())
        self.assertEqual(p["stageId"], vt.STAGE_ID)
        self.assertEqual(p["status"], "REVIEW_ONLY_PREREGISTRATION_EXECUTION_DISABLED_RESULTS_NOT_OPENED")
        for key in (
            "scientificExecutionAuthorized",
            "solverExecutionAuthorized",
            "resultOpeningAuthorized",
            "candidateSeedsAllocated",
            "scientificOrdinalAllocated",
            "productionAuthorized",
        ):
            self.assertIs(p[key], False, key)
        d = p["fixedNumericalAndPhysicalDesign"]
        count = len(d["sunDepressionDeg"]) * len(d["aod550"]) * len(d["geometries"]) * len(d["replicates"]) * len(p["verticalProfileStates"])
        self.assertEqual(count, 360)
        self.assertEqual(p["caseCardinality"]["expectedCases"], 360)
        self.assertEqual(p["caseCardinality"]["commonRandomNumberGroups"], 72)

    def test_protocol_profile_values_match_generator(self):
        p = json.loads(PROTOCOL.read_text())
        rows = {row["stateId"]: row for row in p["verticalProfileStates"]}
        self.assertEqual(set(rows), set(vt.PROFILE_STATES))
        for state_id, source in vt.PROFILE_STATES.items():
            row = rows[state_id]
            tau = vt.state_component_tau550(state_id)
            self.assertEqual(row["sourceAerosolType"], source["sourceAerosolType"])
            self.assertAlmostEqual(row["sourceTotalTau550"], source["totalTau550"], places=15)
            self.assertAlmostEqual(row["firstLayerTopKm"], source["firstLayerTopKm"], places=15)
            self.assertAlmostEqual(row["firstLayerScaleHeightKm"], source["firstLayerScaleHeightKm"], places=15)
            self.assertAlmostEqual(row["derivedFirstLayerTau550"], tau["firstLayer"], places=15)

    def test_fixed_optics_and_antifitting_boundary(self):
        p = json.loads(PROTOCOL.read_text())
        optics = p["fixedOpticalFamily"]
        self.assertEqual(optics["library"], "OPAC")
        self.assertEqual(optics["mixture"], "continental_average")
        self.assertFalse(optics["climatologicalTruthClaim"])
        self.assertEqual(p["secondaryLevelBEndpoint"]["fieldFactor"], 3.14)
        anti = p["antiFittingBoundary"]
        self.assertFalse(anti["taylorResidualsUsedToSelectProfiles"])
        self.assertFalse(anti["jerusalemEventTimesUsedToSelectProfiles"])
        self.assertTrue(anti["profileStatesSelectedFromIndependentOPACTables"])
        self.assertFalse(anti["aodOrOpticalFamilyMayBeRetunedAfterResults"])


if __name__ == "__main__":
    unittest.main()
