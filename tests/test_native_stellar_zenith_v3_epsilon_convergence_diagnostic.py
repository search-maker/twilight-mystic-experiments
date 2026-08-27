import importlib.util
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

    def test_frozen_epsilon_sequence_and_case_count(self):
        m = self.m
        m.validate_case_universe()
        self.assertEqual(m.SZA_EPSILON_DEG, (1.0, 0.5, 0.1, 0.01, 0.001, 0.0001))
        self.assertEqual(m.ATMOSPHERE_CORNERS, ((0.0, 0.05), (0.0, 0.40), (2500.0, 0.05), (2500.0, 0.40)))
        self.assertEqual(len(m.cases()), 24)

    def test_no_exact_zero_and_no_protected_holdout_altitude(self):
        m = self.m
        for row in m.cases():
            self.assertGreater(row["sourceZenithAngleDeg"], 0.0)
            self.assertLess(row["targetAltitudeDeg"], 90.0)
            self.assertNotIn(row["targetAltitudeDeg"], m.PROTECTED_HOLDOUT_ALTITUDES)

    def test_sequence_approaches_exact_zenith_monotonically(self):
        m = self.m
        self.assertTrue(all(m.SZA_EPSILON_DEG[i] > m.SZA_EPSILON_DEG[i + 1] for i in range(len(m.SZA_EPSILON_DEG) - 1)))
        altitudes = [90.0 - x for x in m.SZA_EPSILON_DEG]
        self.assertTrue(all(altitudes[i] < altitudes[i + 1] for i in range(len(altitudes) - 1)))
        self.assertEqual(altitudes[-1], 89.9999)

    def test_diagnostic_does_not_preselect_canonical_epsilon_or_acceptance_gate(self):
        m = self.m
        self.assertFalse(hasattr(m, "CANONICAL_EPSILON_DEG"))
        self.assertFalse(hasattr(m, "EPSILON_ACCEPTANCE_GATE"))
        self.assertEqual(m.REPRESENTATIVE_LIBRARY_NUMBERS, (1, 26, 45))

    def test_case_universe_is_unique(self):
        m = self.m
        rows = m.cases()
        keys = {(r["sourceZenithAngleDeg"], r["observerElevationM"], r["aod550"]) for r in rows}
        self.assertEqual(len(keys), len(rows))


if __name__ == "__main__":
    unittest.main()
