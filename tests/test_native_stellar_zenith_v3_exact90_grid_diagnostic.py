import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/diagnose_exact90_grid_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_exact90_diag", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load exact90 diagnostic")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Exact90GridDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_case_is_exact_first_90_degree_training_coordinate(self):
        self.assertEqual(self.m.CASE, {
            "targetAltitudeDeg": 90.0,
            "observerElevationM": 0.0,
            "aod550": 0.05,
        })

    def test_exact_grid_is_reported_exact(self):
        text = "\n".join(f"{w} 0.5" for w in range(380, 781)) + "\n"
        report = self.m.summarize_stdout_grid(text)
        self.assertEqual(report["status"], "EXACT_380_780_1NM")
        self.assertTrue(report["orderedGridEqualsExactExpected"])
        self.assertEqual(report["nonCommentDataRowCount"], 401)
        self.assertEqual(report["missingExpectedWavelengthNm"], [])
        self.assertEqual(report["duplicateIntegralWavelengthRows"], {})
        self.assertFalse(report["protectedHoldoutOpened"])
        self.assertFalse(report["radiometricAcceptanceEvaluated"])

    def test_missing_row_is_structurally_visible_without_relaxing_parser(self):
        text = "\n".join(f"{w} 0.5" for w in range(380, 781) if w != 557) + "\n"
        report = self.m.summarize_stdout_grid(text)
        self.assertEqual(report["status"], "OUTPUT_GRID_MISMATCH_OBSERVED")
        self.assertFalse(report["orderedGridEqualsExactExpected"])
        self.assertEqual(report["missingExpectedWavelengthNm"], [557])
        self.assertEqual(report["nonCommentDataRowCount"], 400)

    def test_duplicate_row_is_structurally_visible_without_relaxing_parser(self):
        rows = [f"{w} 0.5" for w in range(380, 781)]
        rows.insert(100, "479 0.5")
        report = self.m.summarize_stdout_grid("\n".join(rows) + "\n")
        self.assertEqual(report["status"], "OUTPUT_GRID_MISMATCH_OBSERVED")
        self.assertEqual(report["duplicateIntegralWavelengthRows"], {"479": 2})

    def test_review_mode_does_not_execute_solver(self):
        native = self.m.load_native()
        native.validate_frozen_case_universe()
        self.assertEqual(self.m.CASE["targetAltitudeDeg"], 90.0)


if __name__ == "__main__":
    unittest.main()
