from __future__ import annotations

import importlib.util
import math
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v1" / "low_altitude_phase_b.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_phase_b", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class LowAltitudePhaseBV1Tests(unittest.TestCase):
    def test_frozen_counts_and_disjointness(self):
        m.validate_frozen_universe()
        self.assertEqual(len(m.build_training_cases()), 275)
        self.assertEqual(len(m.build_seam_cases()), 25)
        self.assertEqual(len(m.build_protected_cases()), 176)
        self.assertEqual(176 * len(m.REPRESENTATIVE_LIBRARY_NUMBERS), 528)
        self.assertLess(max(m.PROTECTED_ALTITUDE_DEG), 5.0)

    def test_geometry_and_representation_are_frozen(self):
        ledger = m.review_ledger()
        self.assertEqual(ledger["targetAltitudeBasis"], "topocentric-vacuum-geometric")
        self.assertFalse(ledger["refractionAppliedInRadiativeTransfer"])
        self.assertEqual(ledger["representation"]["interpolatedQuantity"], "direct-optical-depth")
        self.assertEqual(ledger["representation"]["targetAltitudeCoordinate"], "identity-geometric-altitude-deg")
        self.assertFalse(ledger["representation"]["cscExtrapolationBelow5Deg"])
        self.assertFalse(ledger["failureSemantics"]["epsilonSubstitutionAllowed"])
        self.assertFalse(ledger["failureSemantics"]["sameIdentityRetryAllowed"])
        self.assertFalse(ledger["solverExecutionAuthorized"])
        self.assertFalse(ledger["protectedResultsOpened"])
        self.assertFalse(ledger["productionAuthorized"])

    def test_routing_keeps_exact_5_on_v32(self):
        self.assertEqual(m.route_provider(0.249999), "STELLAR_SPECTRAL_RUNTIME_OOD")
        self.assertEqual(m.route_provider(0.25), "LOWALT_STELLAR_V1_CANDIDATE")
        self.assertEqual(m.route_provider(4.999999), "LOWALT_STELLAR_V1_CANDIDATE")
        self.assertEqual(m.route_provider(5.0), "AUTHORITATIVE_STELLAR_V32")
        self.assertEqual(m.route_provider(90.0), "AUTHORITATIVE_STELLAR_V32")
        self.assertEqual(m.route_provider(90.000001), "STELLAR_SPECTRAL_RUNTIME_OOD")
        self.assertEqual(m.route_provider(0.0), "STELLAR_SPECTRAL_RUNTIME_OOD")

    def test_training_refuses_zero_underflow_or_wrong_universe(self):
        rows = []
        for c in m.build_training_cases():
            rows.append({**c, "directOpticalDepth": [1.0] * 401})
        validated = m.validate_training_results(rows)
        self.assertEqual(len(validated), 275)
        bad = [dict(row) for row in rows]
        bad[0] = dict(bad[0])
        bad[0]["directOpticalDepth"] = [1000.0] * 401
        with self.assertRaisesRegex(m.PhaseBRefusal, "epsilon substitution"):
            m.validate_training_results(bad)
        with self.assertRaises(m.PhaseBRefusal):
            m.validate_training_results(rows[:-1])

    def test_protected_gate_requires_global_and_each_altitude(self):
        rows = []
        for c in m.build_protected_cases():
            for lib in m.REPRESENTATIVE_LIBRARY_NUMBERS:
                rows.append({**c, "libraryNumber": lib, "deltaAvMag": 0.001})
        result = m.evaluate_protected_deltas(rows)
        self.assertEqual(result["status"], "PROTECTED_VALIDATION_PASS")
        self.assertEqual(result["overall"]["comparisonCount"], 528)
        self.assertFalse(result["exactHorizonSupported"])
        self.assertFalse(result["productionAuthorized"])
        fail = [dict(row) for row in rows]
        for row in fail:
            if math.isclose(row["targetGeometricAltitudeDeg"], m.PROTECTED_ALTITUDE_DEG[0]):
                row["deltaAvMag"] = 0.026
                break
        failed = m.evaluate_protected_deltas(fail)
        self.assertEqual(failed["status"], "PROTECTED_VALIDATION_FAIL")

    def test_no_solver_execution_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("Popen(", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("--execute", source)
        self.assertNotIn("allow_execution", source)
        self.assertNotIn("Taylor", source)
        self.assertNotIn("Jerusalem", source)


if __name__ == "__main__":
    unittest.main()
