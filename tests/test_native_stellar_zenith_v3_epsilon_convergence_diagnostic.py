import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/diagnose_zenith_epsilon_convergence_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_epsdiag_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load epsilon convergence diagnostic")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ZenithEpsilonConvergenceDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.native = cls.m.load_native()

    def test_frozen_epsilon_sequence_and_case_count(self):
        m = self.m
        m.validate_case_universe()
        self.assertEqual(
            m.SZA_EPSILON_DEG,
            (1.0, 0.5, 0.1, 0.05, 0.03, 0.025, 0.0225, 0.021, 0.0205,
             0.0200, 0.0198, 0.01975, 0.0195, 0.0190, 0.018, 0.015,
             0.010, 0.001, 0.0001),
        )
        self.assertEqual(m.ATMOSPHERE_CORNERS, ((0.0, 0.05), (0.0, 0.40), (2500.0, 0.05), (2500.0, 0.40)))
        self.assertEqual(m.EXPECTED_CASE_COUNT, 76)
        self.assertEqual(len(m.cases()), 76)

    def test_no_exact_zero_and_no_protected_holdout_altitude(self):
        m = self.m
        for row in m.cases():
            self.assertGreater(row["sourceZenithAngleDeg"], 0.0)
            self.assertLess(row["targetAltitudeDeg"], 90.0)
            self.assertNotIn(row["targetAltitudeDeg"], m.PROTECTED_HOLDOUT_ALTITUDES)

    def test_sequence_approaches_exact_zenith_monotonically_and_brackets_transition(self):
        m = self.m
        self.assertTrue(all(m.SZA_EPSILON_DEG[i] > m.SZA_EPSILON_DEG[i + 1] for i in range(len(m.SZA_EPSILON_DEG) - 1)))
        altitudes = [90.0 - x for x in m.SZA_EPSILON_DEG]
        self.assertTrue(all(altitudes[i] < altitudes[i + 1] for i in range(len(altitudes) - 1)))
        self.assertIn(0.0200, m.SZA_EPSILON_DEG)
        self.assertIn(0.01975, m.SZA_EPSILON_DEG)
        self.assertEqual(altitudes[-1], 89.9999)

    def test_diagnostic_does_not_preselect_canonical_epsilon_or_acceptance_gate(self):
        m = self.m
        self.assertFalse(hasattr(m, "CANONICAL_EPSILON_DEG"))
        self.assertFalse(hasattr(m, "EPSILON_ACCEPTANCE_GATE"))
        self.assertEqual(m.REPRESENTATIVE_LIBRARY_NUMBERS, (1, 26, 45))

    def test_known_umu0_endpoint_refusal_is_recorded_not_raised(self):
        m = self.m
        result = m.classify_solver_output(
            native=self.native,
            stdout_text="",
            stderr_text="\nError,  Does not work for umu0=1.0\n",
            return_code=0,
            target_altitude_deg=89.999,
        )
        self.assertFalse(result["solverUsable"])
        self.assertEqual(result["failureKind"], "STRICT_SPECTRUM_PARSE_REFUSAL")
        self.assertTrue(result["knownUmu0EqualsOneRefusal"])
        self.assertEqual(result["dataRowCount"], 0)

    def test_strict_401_node_spectrum_is_classified_usable(self):
        m = self.m
        altitude = 89.95
        mu0 = math.sin(math.radians(altitude))
        stdout = "\n".join(f"{w} {0.5 * mu0:.16g}" for w in range(380, 781)) + "\n"
        result = m.classify_solver_output(
            native=self.native,
            stdout_text=stdout,
            stderr_text="",
            return_code=0,
            target_altitude_deg=altitude,
        )
        self.assertTrue(result["solverUsable"])
        self.assertIsNone(result["failureKind"])
        self.assertEqual(result["dataRowCount"], 401)
        self.assertEqual(result["firstWavelengthNm"], 380.0)
        self.assertEqual(result["lastWavelengthNm"], 780.0)
        self.assertTrue(all(abs(x - 0.5) < 2e-15 for x in result["lineOfSightDirectTransmission"]))

    def test_nonzero_solver_return_is_recorded_not_raised(self):
        m = self.m
        result = m.classify_solver_output(
            native=self.native,
            stdout_text="",
            stderr_text="synthetic failure",
            return_code=9,
            target_altitude_deg=89.95,
        )
        self.assertFalse(result["solverUsable"])
        self.assertEqual(result["failureKind"], "NONZERO_RETURN_CODE")

    def test_usability_monotonicity_helper_detects_reentry(self):
        m = self.m
        self.assertTrue(m._usability_monotonic([
            {"solverUsable": True}, {"solverUsable": True}, {"solverUsable": False}, {"solverUsable": False}
        ]))
        self.assertFalse(m._usability_monotonic([
            {"solverUsable": True}, {"solverUsable": False}, {"solverUsable": True}
        ]))

    def test_case_universe_is_unique(self):
        m = self.m
        rows = m.cases()
        keys = {(r["sourceZenithAngleDeg"], r["observerElevationM"], r["aod550"]) for r in rows}
        self.assertEqual(len(keys), len(rows))


if __name__ == "__main__":
    unittest.main()
