import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review/native-stellar-zenith-v3/diagnose_exact_vertical_optical_column_v1.py"
spec = importlib.util.spec_from_file_location("exact_vertical_optical_column_v1", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ExactVerticalOpticalColumnTests(unittest.TestCase):
    def _atmosphere(self, root: Path) -> Path:
        path = root / "afglus-test.dat"
        path.write_text(
            "120 1\n10 1\n2 1\n1 1\n0 1\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _table_block(iv: int, wavelength: int, *, aerosol_scat: float = 0.02,
                     aerosol_abs: float = 0.003, water_scat: float = 0.0) -> str:
        return f"""*** wavelength: iv = {iv}, {float(wavelength):.6f} nm, albedo = 0.150000
*** optical_properties()
  0 |   0.5000 | 1.000000e-01 | {aerosol_scat:.6f} {aerosol_abs:.6f} 0.650 | {water_scat:.6f} 0.000000 0.000 | 0.000000 0.000000 0.000 0.000 0.000 0.000 0.000 | 4.000000e-02
 sum |     -nan | 1.000000e-01 | 0.000000 0.000000 -nan | 0.000000 0.000000 -nan | 0.000000 0.000000 -nan -nan -nan -nan -nan | 4.000000e-02
"""

    def test_frozen_case_universe_and_gates(self):
        module.validate_case_universe()
        self.assertEqual(module.EXPECTED_SOLVER_CALLS, 4)
        self.assertEqual(
            module.CASE_UNIVERSE,
            ((500.0, 0.30), (1250.0, 0.10), (1250.0, 0.30), (2000.0, 0.20)),
        )
        self.assertEqual(module.MAX_ABS_DELTA_TAU, 1.0e-5)
        self.assertEqual(module.MAX_ABS_DELTA_AV_MAG, 1.0e-4)

    def test_renderer_is_exact_vertical_disort_verbose_without_netcdf_or_mystic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            text = module.render_uvspec_input(
                observer_elevation_m=500.0,
                aod550=0.30,
                data_dir=root / "data",
                atmosphere_file=atmosphere,
                wavelength_grid_file=root / "grid.dat",
            )
        self.assertIn("source solar ", text)
        self.assertIn("solar_flux/atlas_plus_modtran", text)
        self.assertIn("sza 0.00000000", text)
        self.assertIn("rte_solver disort", text)
        self.assertIn("number_of_streams 16", text)
        self.assertIn("output_quantity transmittance", text)
        self.assertIn("output_user lambda edir", text)
        self.assertIn("verbose", text)
        self.assertIn("atm_z_grid 0.500000", text)
        self.assertIn("zout 0.000000", text)
        for forbidden in (
            "write_optical_properties", "rte_solver sdisort", "sdisort nscat",
            "rte_solver mystic", "mc_", "altitude ", "mc_elevation_file",
        ):
            self.assertNotIn(forbidden, text.lower())

    def test_renderer_refuses_nonfrozen_case(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atmosphere = self._atmosphere(root)
            with self.assertRaises(module.OpticalColumnRefusal):
                module.render_uvspec_input(
                    observer_elevation_m=500.0,
                    aod550=0.20,
                    data_dir=root,
                    atmosphere_file=atmosphere,
                    wavelength_grid_file=root / "grid.dat",
                )

    def test_direct_transmission_parser_exact_vertical(self):
        parsed = module.parse_direct_transmission(
            "380 9.000000e-01\n381 8.000000e-01\n",
            expected_grid=(380, 381),
        )
        self.assertEqual(parsed["wavelengthNm"], [380, 381])
        self.assertAlmostEqual(parsed["directOpticalDepth"][0], -math.log(0.9), places=14)
        self.assertAlmostEqual(parsed["directOpticalDepth"][1], -math.log(0.8), places=14)

    def test_verbose_wrapper_reuses_tier1_parser_and_sums_layers(self):
        stderr = self._table_block(0, 380) + self._table_block(1, 381, aerosol_scat=0.021)
        parsed = module.parse_verbose_optical_columns(
            stderr,
            expected_grid=(380, 381),
            expected_layer_count=1,
        )
        self.assertEqual(parsed["wavelengthNm"], [380, 381])
        self.assertEqual(parsed["layerCountByWavelength"], [1, 1])
        self.assertAlmostEqual(parsed["verboseColumnOpticalDepth"][0], 0.163, places=12)
        self.assertAlmostEqual(parsed["verboseColumnOpticalDepth"][1], 0.164, places=12)

    def test_verbose_wrapper_refuses_nonzero_cloud(self):
        stderr = self._table_block(0, 380, water_scat=0.001)
        with self.assertRaises(module.OpticalColumnRefusal):
            module.parse_verbose_optical_columns(
                stderr,
                expected_grid=(380,),
                expected_layer_count=1,
            )

    def test_verbose_wrapper_refuses_index_or_count_drift(self):
        stderr = self._table_block(1, 380)
        with self.assertRaises(module.OpticalColumnRefusal):
            module.parse_verbose_optical_columns(
                stderr,
                expected_grid=(380,),
                expected_layer_count=1,
            )
        with self.assertRaises(module.OpticalColumnRefusal):
            module.parse_verbose_optical_columns(
                self._table_block(0, 380),
                expected_grid=(380, 381),
                expected_layer_count=1,
            )

    def test_identical_spectral_columns_have_zero_photometric_consequence(self):
        tau = [0.1 + 0.0001 * i for i in range(len(module.WAVELENGTH_NM))]
        direct = {
            "wavelengthNm": list(module.WAVELENGTH_NM),
            "directOpticalDepth": tau,
        }
        verbose = {
            "wavelengthNm": list(module.WAVELENGTH_NM),
            "verboseColumnOpticalDepth": list(tau),
        }
        result = module.evaluate_case(
            root=ROOT,
            parsed_direct=direct,
            parsed_verbose=verbose,
            sed_bundle_path=ROOT / "review/asiv-matched-stellar-transport-v1/frozen-assets/pickles-sed-1nm.json",
            johnson_v_path=ROOT / "review/asiv-matched-stellar-transport-v1/frozen-assets/johnson-v-1nm.json",
        )
        self.assertEqual(result["maxAbsDeltaOpticalDepth"], 0.0)
        self.assertEqual(result["maxAbsDeltaAvMag"], 0.0)
        self.assertTrue(result["spectralOpticalColumnPassed"])
        self.assertTrue(result["johnsonVConsequencePassed"])

    def test_execution_fails_closed_without_explicit_authorization(self):
        with self.assertRaises(module.OpticalColumnRefusal):
            module.execute_campaign(
                root=ROOT,
                uvspec=Path("missing"),
                data_dir=Path("missing"),
                atmosphere_file=Path("missing"),
                wavelength_grid_file=Path("missing"),
                sed_bundle_path=Path("missing"),
                johnson_v_path=Path("missing"),
                output_dir=Path("missing"),
                allow_execution=False,
            )


if __name__ == "__main__":
    unittest.main()
