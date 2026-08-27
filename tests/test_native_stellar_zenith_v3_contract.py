import importlib.util
import math
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/native_stellar_zenith_v3.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_stellar_zenith_v3_contract", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load native stellar zenith v3 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeStellarZenithV3ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_frozen_case_universe_and_gates(self):
        m = self.m
        m.validate_frozen_case_universe()
        self.assertEqual(m.NEW_TRAINING_ALTITUDE_DEG, (82.5, 85.0, 87.5, 90.0))
        self.assertEqual(m.VALIDATION_ALTITUDE_DEG, (80.9375, 83.4375, 85.9375, 88.4375))
        self.assertEqual(len(m.build_training_cases()), 100)
        self.assertEqual(len(m.build_validation_cases()), 64)
        self.assertEqual(m.REPRESENTATIVE_LIBRARY_NUMBERS, (1, 26, 45))
        self.assertEqual(m.MAX_ABS_ERROR_MAG_LIMIT, 0.025)
        self.assertEqual(m.RMS_ERROR_MAG_LIMIT, 0.010)
        self.assertEqual(m.OLD_ALTITUDE_KNOTS[-1], 80)
        self.assertEqual(m.EXTENDED_ALTITUDE_KNOTS[-1], 90.0)

    def test_renderer_at_exact_zenith_preserves_native_physics(self):
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
        self.assertIn("sza 0.00000000", text)
        self.assertIn("zout 0.000000", text)
        self.assertIn("aerosol_default", text)
        self.assertIn("aerosol_set_tau_at_wvl 550 0.20000000", text)
        self.assertIn("rte_solver sdisort", text)
        self.assertIn("sdisort nscat 1", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertIn("output_user lambda edir", text)
        self.assertNotIn("rte_solver mystic", text.lower())
        self.assertNotIn("aerosol_species_file", text.lower())
        self.assertNotIn("angstrom", text.lower())

    def test_parser_uses_exact_line_of_sight_conversion_at_zenith(self):
        m = self.m
        rows = "\n".join(f"{w} 0.5" for w in range(380, 781)) + "\n"
        parsed = m.parse_direct_transmission(rows, target_altitude_deg=90.0)
        self.assertEqual(parsed["wavelengthNm"], list(range(380, 781)))
        self.assertAlmostEqual(parsed["mu0"], 1.0, places=15)
        self.assertTrue(all(abs(x - 0.5) < 1e-15 for x in parsed["lineOfSightDirectTransmission"]))
        self.assertTrue(all(abs(x - math.log(2.0)) < 1e-12 for x in parsed["directOpticalDepth"]))

    def test_parser_divides_edir_by_sine_altitude(self):
        m = self.m
        h = 85.0
        mu0 = math.sin(math.radians(h))
        rows = "\n".join(f"{w} {0.75 * mu0:.16g}" for w in range(380, 781)) + "\n"
        parsed = m.parse_direct_transmission(rows, target_altitude_deg=h)
        self.assertTrue(all(abs(x - 0.75) < 2e-15 for x in parsed["lineOfSightDirectTransmission"]))

    def test_execution_is_inert_without_explicit_authorization(self):
        m = self.m
        with self.assertRaisesRegex(m.ZenithV3Refusal, "allow_execution=True"):
            m.execute_campaign(
                root=Path("."), source_runtime_path=Path("missing"), uvspec=Path("missing"),
                data_dir=Path("missing"), atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"), sed_bundle_path=Path("missing"),
                johnson_v_path=Path("missing"), output_dir=Path("missing"),
                allow_execution=False,
            )

    def test_no_training_holdout_overlap(self):
        m = self.m
        train = {m._coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in m.build_training_cases()}
        holdout = {m._coord_key(r["targetAltitudeDeg"], r["observerElevationM"], r["aod550"]) for r in m.build_validation_cases()}
        self.assertFalse(train & holdout)


if __name__ == "__main__":
    unittest.main()
