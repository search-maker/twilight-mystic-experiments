import importlib.machinery
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "review/asiv-matched-stellar-transport-v2"
CANDIDATE = V2 / "interpolation_candidate_v2.py.review"
CONTRACT = V2 / "METHOD_AND_FRESH_VALIDATION_CONTRACT.review.json"
DIAGNOSTIC = V2 / "V1_OPEN_DEVELOPMENT_DIAGNOSTIC.review.json"


def load_candidate():
    loader = importlib.machinery.SourceFileLoader("matched_stellar_v2_candidate", str(CANDIDATE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class MatchedStellarV2ReviewTest(unittest.TestCase):
    def test_review_surface_has_no_solver_or_network_execution(self):
        text = CANDIDATE.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("from subprocess", text)
        self.assertNotIn("import requests", text)
        self.assertNotIn("import urllib", text)
        self.assertNotIn("Popen(", text)
        self.assertNotIn("subprocess.run", text)
        self.assertNotIn("solverExecutionAuthorized\": True", text)

    def test_contract_freezes_only_altitude_interpolation_change(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        method = contract["method"]
        self.assertEqual(method["version"], 2)
        self.assertEqual(method["quantity"], "direct-optical-depth")
        self.assertEqual(method["targetAltitudeCoordinate"], "cosecant-altitude-1-over-sin-h")
        self.assertEqual(method["targetAltitudeInterpolation"], "shape-preserving-piecewise-cubic-hermite-PCHIP")
        self.assertEqual(method["observerElevationInterpolation"], "piecewise-linear")
        self.assertEqual(method["aod550Interpolation"], "piecewise-linear")
        self.assertFalse(method["trainingAxesChangedFromV1"])
        self.assertFalse(method["trainingSpectraChangedFromV1"])
        self.assertFalse(contract["trainingReuse"]["newTrainingSolverExecutionRequired"])
        self.assertEqual(contract["trainingReuse"]["trainingSpectrumCount"], 2700)
        self.assertFalse(contract["scientificBoundaries"]["solverExecutionAuthorizedByThisContract"])
        self.assertFalse(contract["scientificBoundaries"]["pandoraHoldoutAccessAllowed"])
        self.assertFalse(contract["scientificBoundaries"]["starsvisibilityMutationAuthorized"])
        self.assertFalse(contract["scientificBoundaries"]["productionActivationAuthorized"])

    def test_pchip_formula_matches_frozen_reference_numbers(self):
        m = load_candidate()
        x = [0.0, 1.0, 2.0, 3.0]
        y = [0.0, 1.0, 1.5, 1.8]
        self.assertAlmostEqual(m.pchip_interpolate(x, y, 0.25), 0.30078125000000006, places=15)
        self.assertAlmostEqual(m.pchip_interpolate(x, y, 1.4), 1.236, places=15)
        self.assertAlmostEqual(m.pchip_interpolate(x, y, 2.6), 1.7016, places=15)
        for xx, yy in zip(x, y):
            self.assertEqual(m.pchip_interpolate(x, y, xx), yy)

    def test_fresh_holdout_is_exact_768_and_disjoint(self):
        m = load_candidate()
        manifest = m.build_new_validation_manifest()
        self.assertEqual(manifest["status"], "FROZEN_UNEXECUTED_NEW_VALIDATION_HOLDOUT")
        self.assertEqual(manifest["caseCount"], 768)
        self.assertEqual(len(manifest["targetAltitudeDeg"]), 12)
        self.assertEqual(len(manifest["observerElevationM"]), 4)
        self.assertEqual(len(manifest["aod550"]), 4)
        self.assertTrue(all(row["solverExecutionAuthorized"] is False for row in manifest["cases"]))

        new_coords = {
            (row["family"], row["targetAltitudeDeg"], row["observerElevationM"], row["aod550"])
            for row in manifest["cases"]
        }
        training = {
            (family, float(h), float(e), float(a))
            for family in m.NON_NATIVE_FAMILIES
            for h in m.ALTITUDE_KNOTS
            for e in m.ELEVATION_KNOTS_M
            for a in m.AOD_KNOTS
        }
        old_validation = {
            (family, float(h), float(e), float(a))
            for family in m.NON_NATIVE_FAMILIES
            for h in m.OLD_V1_VALIDATION_ALTITUDE_DEG
            for e in m.OLD_V1_VALIDATION_ELEVATION_M
            for a in m.OLD_V1_VALIDATION_AOD550
        }
        self.assertFalse(new_coords & training)
        self.assertFalse(new_coords & old_validation)

    def test_fresh_coordinates_match_contract_and_three_eighths_rule(self):
        m = load_candidate()
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        fresh = contract["freshValidation"]
        self.assertEqual(fresh["fractionWithinSelectedInterval"], 0.375)
        self.assertEqual(list(m.VALIDATION_ALTITUDE_DEG), fresh["targetAltitudeDeg"])
        self.assertEqual(list(m.VALIDATION_ELEVATION_M), fresh["observerElevationM"])
        self.assertEqual(list(m.VALIDATION_AOD550), fresh["aod550"])
        self.assertEqual(fresh["atmosphericCaseCount"], 768)
        self.assertEqual(fresh["johnsonVComparisonCount"], 2304)

    def test_opened_v5_diagnostic_is_development_only(self):
        evidence = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
        self.assertTrue(evidence["baselineReproduced"])
        self.assertFalse(evidence["solverExecutedByDiagnostic"])
        self.assertFalse(evidence["openedV5SetReusableAsFutureValidationHoldout"])
        self.assertFalse(evidence["newValidationClaim"])
        self.assertEqual(evidence["selectedGenericDevelopmentCandidate"]["methodId"], "pchip-alt-csc")
        for family, metrics in evidence["selectedGenericDevelopmentCandidate"]["openedDevelopmentMetrics"].items():
            self.assertEqual(metrics["comparisonCount"], 576, family)
            self.assertLess(metrics["maxAbsDeltaAvMag"], 0.025, family)
            self.assertLess(metrics["rmsDeltaAvMag"], 0.010, family)
            self.assertEqual(metrics["countAbove025"], 0, family)

    def test_gates_are_unchanged_and_cannot_be_relaxed_post_result(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        gates = contract["acceptanceGates"]
        self.assertEqual(gates["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(gates["perFamilyRmsDeltaAvMag"], 0.010)
        self.assertTrue(gates["everyFamilyMustPassSeparately"])
        self.assertTrue(gates["aggregatePassCannotHideFamilyFailure"])
        self.assertFalse(gates["postResultThresholdRelaxationAuthorized"])
        self.assertFalse(gates["postResultMethodChangeAuthorized"])


if __name__ == "__main__":
    unittest.main()
