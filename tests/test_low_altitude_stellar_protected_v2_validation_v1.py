import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "review/low-altitude-stellar-transport-v1/run_protected_v2_validation_v1.py"
SPEC = importlib.util.spec_from_file_location("protected_v2_controller_test", P)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class ProtectedV2ControllerTests(unittest.TestCase):
    def test_review_ledger_is_fresh_exec003_only(self):
        d = m.review_ledger()
        self.assertEqual(d["scientificState"], "LOWALT-STELLAR-STATE-0001")
        self.assertEqual(d["protocolId"], "low-altitude-stellar-protected-v2-fresh-cell-centers")
        self.assertEqual(d["candidateTrainingExecutionId"], "low-altitude-stellar-phase-b-training-v1-exec003")
        self.assertEqual(d["candidateAssemblyId"], "low-altitude-stellar-phase-b-training-candidate-v1-exec003")
        self.assertEqual(d["candidateRuntimeSha256"], "4730c4404ef4ee93c07930f5fe8eb391f117cdc84f2c9eff49c5e7ee9f73b72e")
        self.assertEqual(d["candidateSourceRunId"], 33313239384)
        self.assertEqual(d["candidateArtifactId"], 9732635873)
        self.assertEqual(d["protectedAtmosphericSpectrumCount"], 176)
        self.assertEqual(d["protectedJohnsonVComparisonCount"], 528)
        self.assertEqual(d["protectedAltitudeDeg"], [0.375,0.625,0.875,1.25,1.75,2.25,2.75,3.25,3.75,4.25,4.75])
        self.assertEqual(d["protectedElevationM"], [250.0,875.0,1625.0,2250.0])
        self.assertEqual(d["protectedAod550"], [0.075,0.15,0.25,0.35])
        self.assertFalse(d["inadmissibleExec001NumericalResultsUsed"])
        self.assertFalse(d["mysticState0077ResidualsUsed"])
        self.assertFalse(d["taylorOrJerusalemUsed"])
        self.assertFalse(d["protectedResultsOpenedByReview"])
        self.assertFalse(d["applicationSupportChanged"])
        self.assertFalse(d["productionAuthorized"])
        self.assertFalse(d["githubRerunPermitted"])
        self.assertFalse(d["solverRetryPermitted"])
        self.assertFalse(d["positiveEpsilonSubstitutionAllowed"])
        self.assertEqual(d["minimumSupportedGeometricAltitudeIfPassDeg"], 0.25)
        self.assertFalse(d["exactHorizonSupported"])

    def test_renderer_uses_geometric_sza_and_no_refraction(self):
        with tempfile.TemporaryDirectory() as td:
            atmosphere = Path(td) / "afglus.dat"
            atmosphere.write_text("120 1\n10 1\n0 1\n", encoding="utf-8")
            grid = Path(td) / "wavelength_grid.dat"
            grid.write_text("380\n", encoding="utf-8")
            text = m.render_protected_input(
                data_dir=Path(td), atmosphere_file=atmosphere, wavelength_grid_file=grid,
                target_geometric_altitude_deg=0.375, observer_elevation_m=250.0, aod550=0.075,
            )
        self.assertIn("sza 89.62500000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertNotIn("refraction", text.lower())
        self.assertNotIn("rte_solver mystic", text.lower())
        self.assertNotIn("mc_", text.lower())

    def test_zero_or_underflow_direct_transmission_refuses(self):
        rows = []
        mu = __import__("math").sin(__import__("math").radians(0.375))
        for w in range(380, 781):
            edir = 0.0 if w == 550 else 0.5 * mu
            rows.append(f"{w} {edir:.17g}")
        with self.assertRaises(m.ProtectedV2Refusal):
            m.parse_protected_transmission("\n".join(rows), target_geometric_altitude_deg=0.375)

    def test_exact_positive_transmission_parses_without_epsilon(self):
        import math
        mu = math.sin(math.radians(4.75))
        text = "\n".join(f"{w} {0.25 * mu:.17g}" for w in range(380, 781))
        d = m.parse_protected_transmission(text, target_geometric_altitude_deg=4.75)
        self.assertEqual(d["wavelengthNm"], list(range(380, 781)))
        self.assertTrue(all(abs(x - 0.25) < 1e-12 for x in d["lineOfSightDirectTransmission"]))
        self.assertFalse(d["positiveEpsilonSubstitutionUsed"])

    def test_fresh_metric_has_no_post_result_floor_selection(self):
        rows = []
        for c in m.fresh.build_protected_cases():
            for lib in m.fresh.REPRESENTATIVE_LIBRARY_NUMBERS:
                rows.append({**c, "libraryNumber": lib, "deltaAvMag": 0.0})
        d = m.fresh.evaluate_deltas(rows)
        self.assertEqual(d["status"], "PROTECTED_VALIDATION_PASS")
        self.assertEqual(d["minimumSupportedGeometricAltitudeIfPassDeg"], 0.25)
        self.assertFalse(d["postResultFloorBackSelectionAuthorized"])

    def test_source_has_no_old_exec001_candidate_or_protected_values(self):
        text = P.read_text(encoding="utf-8")
        self.assertNotIn("33311205702", text)
        self.assertNotIn("9732025874", text)
        self.assertNotIn("2ab71a13dee10374d7ebba854bd46cedb61e77d293d0d24804ea75dcd2a33ea3", text)
        self.assertNotIn("0.34375", text)
        self.assertNotIn("Taylor residual", text)
        self.assertNotIn("Jerusalem residual", text)


if __name__ == "__main__":
    unittest.main()
