import importlib.util
import math
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "review/low-altitude-stellar-transport-v1/run_phase_b_protected_validation_v2.py"
SPEC = importlib.util.spec_from_file_location("low_altitude_protected_v2_controller_test", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ProtectedV2ControllerTests(unittest.TestCase):
    def test_review_ledger_binds_fresh_protocol_candidate_and_acceptance(self):
        d = mod.review_ledger()
        self.assertEqual(d["executionId"], "low-altitude-stellar-phase-b-protected-validation-v2-exec001")
        self.assertEqual(d["protocolId"], "low-altitude-stellar-protected-v2-fresh-cell-centers")
        self.assertEqual(d["protocolFreezeIssue60CommentId"], 5468889581)
        self.assertEqual(d["candidateRuntimeSha256"], "4730c4404ef4ee93c07930f5fe8eb391f117cdc84f2c9eff49c5e7ee9f73b72e")
        self.assertEqual(d["candidateAssemblyId"], "low-altitude-stellar-phase-b-training-candidate-v1-exec003")
        self.assertEqual(d["candidateArtifactId"], 9732635873)
        self.assertEqual(d["trainingExecutionId"], "low-altitude-stellar-phase-b-training-v1-exec003")
        self.assertEqual(d["protectedAtmosphericSpectrumCount"], 176)
        self.assertEqual(d["protectedJohnsonVComparisonCount"], 528)
        self.assertEqual(d["protectedAltitudeDeg"], [0.375,0.625,0.875,1.25,1.75,2.25,2.75,3.25,3.75,4.25,4.75])
        self.assertEqual(d["protectedElevationM"], [250.0,875.0,1625.0,2250.0])
        self.assertEqual(d["protectedAod550"], [0.075,0.15,0.25,0.35])
        self.assertEqual(d["representativeLibraryNumbers"], [1,26,45])
        self.assertEqual(d["maxAbsDeltaAvMagLimit"], 0.025)
        self.assertEqual(d["rmsDeltaAvMagLimit"], 0.010)
        self.assertTrue(d["globalAndEveryAltitudeIntervalMustPass"])
        self.assertFalse(d["protectedV1NumericalResultsUsed"])
        self.assertFalse(d["mysticState0077ResidualsUsed"])
        self.assertFalse(d["taylorOrJerusalemUsed"])
        self.assertFalse(d["scientificExecutionAuthorizedByModule"])
        self.assertFalse(d["postResultFloorBackSelectionAuthorized"])
        self.assertFalse(d["postResultRetuningAuthorized"])
        self.assertFalse(d["positiveEpsilonSubstitutionAllowed"])
        self.assertFalse(d["sameIdentityRetryAllowed"])
        self.assertFalse(d["githubRerunAllowed"])
        self.assertEqual(d["minimumSupportedGeometricAltitudeIfPassDeg"], 0.25)
        self.assertFalse(d["exactHorizonSupported"])
        self.assertEqual(d["exactFiveDegreeProvider"], "authoritative-v3.2")
        self.assertFalse(d["productionAuthorized"])
        self.assertFalse(d["applicationSupportChanged"])

    def test_protected_universe_is_exact_fresh_176_and_not_v1(self):
        rows = mod.protected_cases()
        keys = mod.protected_keys()
        self.assertEqual(len(rows), 176)
        self.assertEqual(len(keys), 176)
        old = mod.phase_b.coord(0.34375, 187.5, 0.06875)
        self.assertNotIn(old, keys)
        self.assertIn(mod.phase_b.coord(0.375, 250.0, 0.075), keys)

    def _atmosphere_file(self, root):
        path = pathlib.Path(root) / "afglus-mini.dat"
        path.write_text("100 1\n10 1\n2.5 1\n1.0 1\n0 1\n", encoding="utf-8")
        return path

    def test_renderer_uses_geometric_altitude_pseudospherical_sdisort_and_no_refraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            atm = self._atmosphere_file(tmp)
            text = mod.render_protected_input(
                data_dir=pathlib.Path(tmp), atmosphere_file=atm,
                wavelength_grid_file=pathlib.Path(tmp) / "grid.dat",
                target_geometric_altitude_deg=0.375,
                observer_elevation_m=250.0, aod550=0.075,
            )
        self.assertIn("sza 89.62500000", text)
        self.assertIn("atm_z_grid 0.250000 1.000000 2.500000 10.000000 100.000000", text)
        self.assertIn("aerosol_set_tau_at_wvl 550 0.07500000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertNotIn("refraction", text.lower())
        self.assertNotIn("nrefrac", text.lower())
        self.assertNotIn("mystic", text.lower())

    def test_renderer_refuses_old_opened_v1_coordinate(self):
        with tempfile.TemporaryDirectory() as tmp:
            atm = self._atmosphere_file(tmp)
            with self.assertRaises(mod.ProtectedV2Refusal):
                mod.render_protected_input(
                    data_dir=pathlib.Path(tmp), atmosphere_file=atm,
                    wavelength_grid_file=pathlib.Path(tmp) / "grid.dat",
                    target_geometric_altitude_deg=0.34375,
                    observer_elevation_m=187.5, aod550=0.06875,
                )

    def test_parser_recovers_line_of_sight_transmission_and_refuses_zero(self):
        h = 0.375
        mu0 = math.sin(math.radians(h))
        good = "\n".join(f"{w} {mu0 * 0.5:.17g}" for w in range(380, 781)) + "\n"
        parsed = mod.parse_protected_transmission(good, target_geometric_altitude_deg=h)
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertTrue(all(abs(x - 0.5) < 1e-12 for x in parsed["lineOfSightDirectTransmission"]))
        self.assertTrue(all(abs(x - math.log(2.0)) < 1e-12 for x in parsed["directOpticalDepth"]))
        self.assertFalse(parsed["positiveEpsilonSubstitutionUsed"])

        bad = []
        for w in range(380, 781):
            edir = 0.0 if w == 550 else mu0 * 0.5
            bad.append(f"{w} {edir:.17g}")
        with self.assertRaisesRegex(mod.ProtectedV2Refusal, "NUMERICALLY_UNRESOLVED"):
            mod.parse_protected_transmission("\n".join(bad) + "\n", target_geometric_altitude_deg=h)

    def test_parser_refuses_nonfresh_altitude(self):
        with self.assertRaises(mod.ProtectedV2Refusal):
            mod.parse_protected_transmission("", target_geometric_altitude_deg=0.34375)

    def test_fresh_metric_pass_and_fail_have_no_floor_back_selection(self):
        zero_rows = []
        for case in mod.protected_cases():
            for library_number in mod.fresh_v2.REPRESENTATIVE_LIBRARY_NUMBERS:
                zero_rows.append({**case, "libraryNumber": library_number, "deltaAvMag": 0.0})
        passed = mod.fresh_v2.evaluate_deltas(zero_rows)
        self.assertEqual(passed["status"], "PROTECTED_VALIDATION_PASS")
        self.assertEqual(passed["minimumSupportedGeometricAltitudeIfPassDeg"], 0.25)
        self.assertFalse(passed["postResultFloorBackSelectionAuthorized"])

        fail_rows = [dict(row) for row in zero_rows]
        fail_rows[0]["deltaAvMag"] = 0.026
        failed = mod.fresh_v2.evaluate_deltas(fail_rows)
        self.assertEqual(failed["status"], "PROTECTED_VALIDATION_FAIL")
        self.assertIsNone(failed["minimumSupportedGeometricAltitudeIfPassDeg"])
        self.assertFalse(failed["postResultFloorBackSelectionAuthorized"])

    def test_controller_source_has_no_old_evaluator_or_result_tuning(self):
        source = PATH.read_text(encoding="utf-8")
        self.assertNotIn("phase_b.build_protected_cases()", source)
        self.assertNotIn("phase_b.evaluate_protected_deltas", source)
        self.assertNotIn("low-altitude-stellar-phase-b-training-v1-exec001", source)
        self.assertNotIn("MYSTIC-STATE-0077", source)
        self.assertNotIn("Taylor", source)
        self.assertNotIn("Jerusalem", source)
        self.assertIn("fresh_v2.build_protected_cases()", source)
        self.assertIn("fresh_v2.evaluate_deltas", source)
        self.assertIn("expected candidate SHA is not the frozen protected-v2 candidate", source)
        self.assertIn("retry/resume is forbidden", source)


if __name__ == "__main__":
    unittest.main()
