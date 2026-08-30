from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v2" / "state_0002_refinement_protocol.py"
SPEC = importlib.util.spec_from_file_location("state_0002_refinement_protocol", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class State0002RefinementProtocolTests(unittest.TestCase):
    def test_protocol_validates_and_has_expected_nested_counts(self):
        m.validate_protocol()
        self.assertEqual(m.SCIENTIFIC_STATE, "LOWALT-STELLAR-STATE-0002")
        self.assertEqual(m.expected_training_spectra("L1"), 550)
        self.assertEqual(m.expected_training_spectra("L2"), 1980)
        self.assertEqual(m.expected_training_spectra("L3"), 7480)
        self.assertEqual(len(m.model_selection_cases()), 1408)
        self.assertEqual(len(m.final_protected_cases()), 176)

    def test_nested_axes_preserve_domain_and_only_add_dyadic_knots(self):
        l1 = m.training_axes("L1")
        l2 = m.training_axes("L2")
        l3 = m.training_axes("L3")
        self.assertEqual(l1["targetGeometricAltitudeDeg"][0], 0.25)
        self.assertEqual(l3["targetGeometricAltitudeDeg"][-1], 5.0)
        self.assertTrue(set(l1["targetGeometricAltitudeDeg"]).issubset(set(l2["targetGeometricAltitudeDeg"])))
        self.assertTrue(set(l2["targetGeometricAltitudeDeg"]).issubset(set(l3["targetGeometricAltitudeDeg"])))
        self.assertTrue(set(l1["observerElevationM"]).issubset(set(l2["observerElevationM"])))
        self.assertTrue(set(l2["observerElevationM"]).issubset(set(l3["observerElevationM"])))
        self.assertEqual(l1["aod550"], l2["aod550"])
        self.assertEqual(l2["aod550"], l3["aod550"])
        self.assertNotIn(0.0, l3["targetGeometricAltitudeDeg"])

    def test_model_selection_is_disjoint_from_all_training_and_final_holdout(self):
        model = m._keys(m.model_selection_cases())
        final = m._keys(m.final_protected_cases())
        self.assertFalse(model & final)
        for level in ("L1", "L2", "L3"):
            train = m._keys(m.training_cases(level))
            self.assertFalse(train & model)
            self.assertFalse(train & final)

    def test_final_holdout_is_fresh_against_both_opened_state1_matrices(self):
        final = m._keys(m.final_protected_cases())
        old_v1 = m._opened_keys(m.OPENED_STATE1_V1_ALTITUDE, m.OPENED_STATE1_V1_ELEVATION, m.OPENED_STATE1_V1_AOD)
        old_v2 = m._opened_keys(m.OPENED_STATE1_V2_ALTITUDE, m.OPENED_STATE1_V2_ELEVATION, m.OPENED_STATE1_V2_AOD)
        self.assertFalse(final & old_v1)
        self.assertFalse(final & old_v2)
        axes = m.final_protected_axes()
        self.assertFalse(set(axes["targetGeometricAltitudeDeg"]) & (set(m.OPENED_STATE1_V1_ALTITUDE) | set(m.OPENED_STATE1_V2_ALTITUDE)))
        self.assertFalse(set(axes["observerElevationM"]) & (set(m.OPENED_STATE1_V1_ELEVATION) | set(m.OPENED_STATE1_V2_ELEVATION)))
        self.assertFalse(set(axes["aod550"]) & (set(m.OPENED_STATE1_V1_AOD) | set(m.OPENED_STATE1_V2_AOD)))

    @staticmethod
    def _metrics(max_abs: float, rms: float):
        row = {"maxAbsDeltaAvMag": max_abs, "rmsDeltaAvMag": rms}
        return {
            "comparisonCount": m.EXPECTED_MODEL_SELECTION_COMPARISONS,
            "overall": dict(row),
            "byBaseAltitudeInterval": {str(i): dict(row) for i in range(len(m.BASE_ALTITUDE_DEG) - 1)},
        }

    def test_selection_rule_is_coarsest_complete_passing_level(self):
        passed = self._metrics(0.01, 0.004)
        failed = self._metrics(0.02, 0.004)
        self.assertEqual(m.select_level_from_model_selection({"L1": passed}), "L1")
        self.assertEqual(m.select_level_from_model_selection({"L1": failed, "L2": passed}), "L2")
        self.assertEqual(m.select_level_from_model_selection({"L1": failed, "L2": failed, "L3": passed}), "L3")
        self.assertIsNone(m.select_level_from_model_selection({"L1": failed, "L2": failed, "L3": failed}))
        self.assertIsNone(m.select_level_from_model_selection({"L1": failed}))

    def test_ledger_keeps_protected_closed_and_predecessor_residuals_out(self):
        ledger = m.ledger()
        self.assertFalse(ledger["predecessorProtectedResidualsUsedForDesign"])
        self.assertFalse(ledger["predecessorProtectedPerAltitudePassPatternUsedForDesign"])
        self.assertFalse(ledger["mysticState0077ResidualsUsedForDesign"])
        self.assertFalse(ledger["taylorOrJerusalemUsed"])
        self.assertFalse(ledger["finalProtected"]["opened"])
        self.assertFalse(ledger["solverExecutionAuthorizedByThisModule"])
        self.assertEqual(ledger["modelSelection"]["selectionRule"], "first/coarsest nested level L1->L2->L3 satisfying the complete frozen model-selection gate")
        self.assertEqual(ledger["claimBoundary"]["minimumSupportedGeometricAltitudeBeforeFinalProtectedPassDeg"], 5.0)
        self.assertFalse(ledger["claimBoundary"]["exactHorizonSupported"])
        self.assertFalse(ledger["claimBoundary"]["applicationSupportChanged"])
        self.assertFalse(ledger["claimBoundary"]["productionAuthorized"])

    def test_source_contains_no_opened_protected_error_values_or_execution_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("0.20750414925067062", source)
        self.assertNotIn("0.044561710921862445", source)
        self.assertNotIn("0.010802886158554112", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("--execute", source)
        self.assertNotIn("uvspec", source)
        self.assertNotIn("first-seeing", source.lower())
        self.assertIn("predecessorProtectedResidualsUsedForDesign", source)
        self.assertIn("TERMINATE_STATE_0002_WITHOUT_OPENING_FINAL_PROTECTED", source)


if __name__ == "__main__":
    unittest.main()
