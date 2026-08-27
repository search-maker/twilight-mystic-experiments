import importlib.util
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/native_stellar_zenith_v31.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v31_limit", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load native stellar zenith v3.1 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeStellarZenithV31LimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_scientific_universe_and_acceptance_gates_are_unchanged(self):
        m = self.m
        m.validate_frozen_case_universe()
        self.assertEqual(m.NEW_TRAINING_ALTITUDE_DEG, (82.5, 85.0, 87.5, 90.0))
        self.assertEqual(m.VALIDATION_ALTITUDE_DEG, (80.9375, 83.4375, 85.9375, 88.4375))
        self.assertEqual(len(m.build_training_cases()), 100)
        self.assertEqual(len(m.build_validation_cases()), 64)
        self.assertEqual(m.MAX_ABS_ERROR_MAG_LIMIT, 0.025)
        self.assertEqual(m.RMS_ERROR_MAG_LIMIT, 0.010)
        self.assertEqual(m.REPRESENTATIVE_LIBRARY_NUMBERS, (1, 26, 45))

    def test_exact_physical_zenith_maps_only_solver_to_fixed_limit(self):
        m = self.m
        self.assertEqual(m.solver_source_zenith_angle_deg(90.0), 0.001)
        self.assertEqual(m.solver_target_altitude_deg(90.0), 89.999)
        self.assertTrue(m.zenith_limit_applied(90.0))
        self.assertAlmostEqual(m.solver_mu0(90.0), math.cos(math.radians(0.001)), places=15)
        excess = m.zenith_limit_relative_airmass_excess()
        self.assertGreater(excess, 0.0)
        self.assertLess(excess, 2e-10)

    def test_nonzenith_solver_geometry_is_identical_to_physical_geometry(self):
        m = self.m
        for altitude in (80.0, 82.5, 85.0, 87.5, 88.4375):
            self.assertFalse(m.zenith_limit_applied(altitude))
            self.assertAlmostEqual(m.solver_source_zenith_angle_deg(altitude), 90.0 - altitude, places=14)
            self.assertAlmostEqual(m.solver_target_altitude_deg(altitude), altitude, places=14)
            self.assertAlmostEqual(m.solver_mu0(altitude), math.sin(math.radians(altitude)), places=14)

    def test_exact_zenith_renderer_never_sends_umu0_equal_one(self):
        m = self.m
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = root / "afglus.dat"
            atmosphere.write_text("10 1\n5 1\n0 1\n", encoding="utf-8")
            grid = root / "wavelength.dat"
            grid.write_text("\n".join(str(x) for x in range(380, 781)) + "\n", encoding="utf-8")
            text = m.render_uvspec_input(
                data_dir=root,
                atmosphere_file=atmosphere,
                wavelength_grid_file=grid,
                target_altitude_deg=90.0,
                observer_elevation_m=0.0,
                aod550=0.20,
            )
        self.assertIn("sza 0.00100000", text)
        self.assertNotIn("sza 0.00000000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertIn("output_user lambda edir", text)
        self.assertNotIn("rte_solver mystic", text.lower())

    def test_parser_uses_solver_mu0_but_reports_exact_physical_zenith(self):
        m = self.m
        mu0 = math.cos(math.radians(0.001))
        rows = "\n".join(f"{w} {0.5 * mu0:.16g}" for w in range(380, 781)) + "\n"
        parsed = m.parse_direct_transmission(rows, target_altitude_deg=90.0)
        self.assertEqual(parsed["physicalTargetAltitudeDeg"], 90.0)
        self.assertEqual(parsed["physicalSourceZenithAngleDeg"], 0.0)
        self.assertEqual(parsed["solverSourceZenithAngleDeg"], 0.001)
        self.assertTrue(parsed["zenithLimitRegularizationApplied"])
        self.assertAlmostEqual(parsed["solverMu0"], mu0, places=15)
        self.assertTrue(all(abs(x - 0.5) < 2e-15 for x in parsed["lineOfSightDirectTransmission"]))
        self.assertLess(parsed["relativePlaneParallelAirmassExcessVsExactVertical"], 2e-10)

    def test_parser_nonzenith_is_unchanged(self):
        m = self.m
        altitude = 85.0
        mu0 = math.sin(math.radians(altitude))
        rows = "\n".join(f"{w} {0.75 * mu0:.16g}" for w in range(380, 781)) + "\n"
        parsed = m.parse_direct_transmission(rows, target_altitude_deg=altitude)
        self.assertFalse(parsed["zenithLimitRegularizationApplied"])
        self.assertEqual(parsed["physicalTargetAltitudeDeg"], altitude)
        self.assertAlmostEqual(parsed["solverSourceZenithAngleDeg"], 5.0, places=14)
        self.assertTrue(all(abs(x - 0.75) < 2e-15 for x in parsed["lineOfSightDirectTransmission"]))

    def test_execution_stays_inert_without_explicit_authorization(self):
        m = self.m
        with self.assertRaisesRegex(m.ZenithV31Refusal, "allow_execution=True"):
            m.execute_campaign(
                root=Path("."), source_runtime_path=Path("missing"), uvspec=Path("missing"),
                data_dir=Path("missing"), atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"), sed_bundle_path=Path("missing"),
                johnson_v_path=Path("missing"), output_dir=Path("missing"),
                allow_execution=False,
            )

    def test_training_and_holdout_remain_disjoint(self):
        m = self.m
        train = {m._coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in m.build_training_cases()}
        holdout = {m._coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in m.build_validation_cases()}
        self.assertFalse(train & holdout)


if __name__ == "__main__":
    unittest.main()
