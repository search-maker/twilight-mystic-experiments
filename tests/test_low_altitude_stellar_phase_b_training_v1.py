from __future__ import annotations

import importlib.util
import math
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "low-altitude-stellar-transport-v1" / "run_phase_b_training_v1.py"
SPEC = importlib.util.spec_from_file_location("run_phase_b_training_v1", MODULE_PATH)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PhaseBTrainingV1ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = pathlib.Path(self.tmp.name)
        self.atmosphere = base / "afglus.dat"
        self.atmosphere.write_text("120 1\n80 1\n50 1\n20 1\n10 1\n5 1\n2.5 1\n0 1\n", encoding="utf-8")
        self.wavelength = base / "wavelength-grid.dat"
        self.wavelength.write_text("380\n780\n", encoding="utf-8")
        self.data_dir = base / "data"

    def test_training_universe_is_exactly_275_and_excludes_seam(self):
        cases = m.phase_b.build_training_cases()
        self.assertEqual(len(cases), 275)
        self.assertEqual(sorted({r["targetGeometricAltitudeDeg"] for r in cases}), list(m.phase_b.TRAINING_ALTITUDE_DEG))
        self.assertTrue(all(r["targetGeometricAltitudeDeg"] < 5.0 for r in cases))
        self.assertEqual(m.EXPECTED_INVOCATIONS, 275)

    def test_renderer_matches_phase_a_semantics_on_shared_coordinates(self):
        for altitude in (0.25, 0.5, 1.0, 2.0, 3.0, 4.0):
            for elevation in (0.0, 2500.0):
                for aod in (0.05, 0.40):
                    expected = m.phase_a.render_uvspec_input(
                        data_dir=self.data_dir,
                        atmosphere_file=self.atmosphere,
                        wavelength_grid_file=self.wavelength,
                        target_altitude_deg=altitude,
                        observer_elevation_m=elevation,
                        aod550=aod,
                    )
                    actual = m.render_training_input(
                        data_dir=self.data_dir,
                        atmosphere_file=self.atmosphere,
                        wavelength_grid_file=self.wavelength,
                        target_altitude_deg=altitude,
                        observer_elevation_m=elevation,
                        aod550=aod,
                    )
                    self.assertEqual(actual, expected)

    def test_renderer_allows_new_preregistered_knots_only(self):
        text = m.render_training_input(
            data_dir=self.data_dir,
            atmosphere_file=self.atmosphere,
            wavelength_grid_file=self.wavelength,
            target_altitude_deg=0.75,
            observer_elevation_m=500.0,
            aod550=0.10,
        )
        self.assertIn("sza 89.25000000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertNotIn("refraction", text.lower())
        with self.assertRaises(m.TrainingExecutionRefusal):
            m.render_training_input(
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                target_altitude_deg=5.0,
                observer_elevation_m=500.0,
                aod550=0.10,
            )

    def test_parser_accepts_positive_401_point_spectrum_and_refuses_zero(self):
        altitude = 0.75
        mu0 = math.sin(math.radians(altitude))
        stdout = "\n".join(f"{w} {mu0 * 0.2:.17g}" for w in range(380, 781)) + "\n"
        parsed = m.parse_training_transmission(stdout, target_altitude_deg=altitude)
        self.assertEqual(len(parsed["directOpticalDepth"]), 401)
        self.assertFalse(parsed["positiveEpsilonSubstitutionUsed"])
        self.assertAlmostEqual(parsed["sourceZenithAngleDeg"], 89.25)
        zero = "\n".join(f"{w} {0.0 if w == 550 else mu0 * 0.2:.17g}" for w in range(380, 781)) + "\n"
        with self.assertRaisesRegex(m.TrainingExecutionRefusal, "NUMERICALLY_UNRESOLVED"):
            m.parse_training_transmission(zero, target_altitude_deg=altitude)

    def test_execution_is_explicit_and_nonresumable(self):
        with self.assertRaisesRegex(m.TrainingExecutionRefusal, "allow_execution"):
            m.execute_campaign(
                uvspec=pathlib.Path('/does/not/matter'),
                data_dir=self.data_dir,
                atmosphere_file=self.atmosphere,
                wavelength_grid_file=self.wavelength,
                output_dir=pathlib.Path(self.tmp.name) / 'out',
                allow_execution=False,
            )

    def test_control_contains_no_protected_execution_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('protectedValidationOpened', source)
        self.assertIn('protectedSolverInvocationCount', source)
        self.assertNotIn('build_protected_cases()', source)
        self.assertNotIn('evaluate_protected_deltas(', source)
        self.assertNotIn('Taylor', source)
        self.assertNotIn('Jerusalem', source)
        self.assertNotIn('MYSTIC Monte Carlo', source)


if __name__ == "__main__":
    unittest.main()
