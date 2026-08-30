from __future__ import annotations

import importlib.util
import math
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v1" / "run_phase_b_protected_validation_v1.py"
SPEC = importlib.util.spec_from_file_location("run_phase_b_protected_validation_v1", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class ProtectedValidationContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)
        self.atmosphere = root / "afglus.dat"
        self.atmosphere.write_text("120 1\n80 1\n50 1\n20 1\n10 1\n5 1\n2.5 1\n0 1\n", encoding="utf-8")
        self.grid = root / "wavelength.dat"
        self.grid.write_text("\n".join(str(x) for x in range(380, 781)) + "\n", encoding="utf-8")
        self.data_dir = root / "data"

    def _stdout(self, altitude, transmission=0.25):
        mu0 = math.sin(math.radians(altitude))
        return "\n".join(f"{w} {mu0 * transmission:.17g}" for w in range(380, 781)) + "\n"

    def _candidate(self):
        spectra = []
        for h in m.phase_b.LOWER_ASSET_ALTITUDE_DEG:
            for e in m.phase_b.ELEVATION_KNOTS_M:
                for a in m.phase_b.AOD_KNOTS:
                    tau = 0.2 + 0.01 * (5.0 - h) + 0.00001 * e + 0.01 * a
                    spectra.append([tau] * len(m.phase_b.WAVELENGTH_NM))
        return {
            "schemaVersion": 1,
            "quantity": "level-b-stellar-direct-optical-depth-lut-lower-extension",
            "scientificState": m.phase_b.SCIENTIFIC_STATE,
            "axes": {
                "targetAltitudeDeg": list(m.phase_b.LOWER_ASSET_ALTITUDE_DEG),
                "observerElevationM": list(m.phase_b.ELEVATION_KNOTS_M),
                "aod550": list(m.phase_b.AOD_KNOTS),
            },
            "wavelengthNm": list(m.phase_b.WAVELENGTH_NM),
            "directOpticalDepth": spectra,
            "representation": {
                "interpolatedQuantity": "direct-optical-depth",
                "targetAltitudeCoordinate": "identity-geometric-altitude-deg",
                "targetAltitudeInterpolation": "linear",
                "observerElevationInterpolation": "linear",
                "aod550Interpolation": "linear",
                "cscExtrapolationBelow5Deg": False,
            },
            "routing": {
                "lowerProviderMinInclusiveDeg": 0.25,
                "lowerProviderMaxExclusiveDeg": 5.0,
                "exactFiveAndAboveProvider": "authoritative-v3.2",
                "outsideSupport": "STELLAR_SPECTRAL_RUNTIME_OOD",
                "exactHorizonSupported": False,
            },
            "provenance": {
                "trainingExecutionId": "low-altitude-stellar-phase-b-training-v1-exec001",
                "protectedValidationOpened": False,
                "scientificallyValidatedBelow5Deg": False,
                "productionAuthorized": False,
                "applicationSupportChanged": False,
            },
        }

    def test_ledger_exact_fresh_matrix_and_gates(self):
        d = m.review_ledger()
        self.assertEqual(d["protectedAtmosphericSpectrumCount"], 176)
        self.assertEqual(d["protectedJohnsonVComparisonCount"], 528)
        self.assertEqual(d["protectedAltitudeDeg"], list(m.phase_b.PROTECTED_ALTITUDE_DEG))
        self.assertEqual(d["protectedElevationM"], list(m.phase_b.PROTECTED_ELEVATION_M))
        self.assertEqual(d["protectedAod550"], list(m.phase_b.PROTECTED_AOD550))
        self.assertEqual(d["maxAbsDeltaAvMagLimit"], 0.025)
        self.assertEqual(d["rmsDeltaAvMagLimit"], 0.010)
        self.assertTrue(d["globalAndEveryAltitudeIntervalMustPass"])
        self.assertFalse(d["postResultFloorBackSelectionAuthorized"])
        self.assertFalse(d["positiveEpsilonSubstitutionAllowed"])
        self.assertFalse(d["scientificExecutionAuthorizedByModule"])

    def test_renderer_is_restricted_to_protected_coordinates_and_no_refraction(self):
        row = m.phase_b.build_protected_cases()[0]
        text = m.render_protected_input(
            data_dir=self.data_dir, atmosphere_file=self.atmosphere,
            wavelength_grid_file=self.grid,
            target_geometric_altitude_deg=row["targetGeometricAltitudeDeg"],
            observer_elevation_m=row["observerElevationM"], aod550=row["aod550"],
        )
        self.assertIn(f"sza {90.0 - row['targetGeometricAltitudeDeg']:.8f}", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertNotIn("refraction", text.lower())
        with self.assertRaises(m.ProtectedValidationRefusal):
            m.render_protected_input(
                data_dir=self.data_dir, atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.grid,
                target_geometric_altitude_deg=0.25,
                observer_elevation_m=row["observerElevationM"], aod550=row["aod550"],
            )

    def test_parser_rejects_zero_and_accepts_positive(self):
        h = m.phase_b.PROTECTED_ALTITUDE_DEG[0]
        parsed = m.parse_protected_transmission(self._stdout(h), target_geometric_altitude_deg=h)
        self.assertEqual(len(parsed["directOpticalDepth"]), 401)
        self.assertFalse(parsed["positiveEpsilonSubstitutionUsed"])
        mu0 = math.sin(math.radians(h))
        bad = "\n".join(f"{w} {0.0 if w == 550 else mu0 * 0.25:.17g}" for w in range(380, 781)) + "\n"
        with self.assertRaisesRegex(m.ProtectedValidationRefusal, "NUMERICALLY_UNRESOLVED"):
            m.parse_protected_transmission(bad, target_geometric_altitude_deg=h)

    def test_candidate_claim_boundary(self):
        c = self._candidate()
        m.validate_candidate(c)
        c["provenance"]["scientificallyValidatedBelow5Deg"] = True
        with self.assertRaises(m.ProtectedValidationRefusal):
            m.validate_candidate(c)

    def test_matrix_has_no_collision_with_training_or_historical_domains(self):
        protected = m.protected_keys()
        training = {
            m.phase_b.coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
            for r in m.phase_b.build_training_cases()
        }
        seam = {
            m.phase_b.coord(r["targetGeometricAltitudeDeg"], r["observerElevationM"], r["aod550"])
            for r in m.phase_b.build_seam_cases()
        }
        self.assertFalse(protected & training)
        self.assertFalse(protected & seam)
        self.assertLess(max(k[0] for k in protected), 5.0)

    def test_no_floor_back_selection_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("MYSTIC-STATE-0077", source)
        self.assertNotIn("Taylor", source)
        self.assertNotIn("Jerusalem", source)
        self.assertNotIn("back_select", source.lower())
        self.assertIn("postResultFloorBackSelectionAuthorized", source)
        self.assertIn("candidateShaMustBeBoundBeforeExecution", source)


if __name__ == "__main__":
    unittest.main()
