from __future__ import annotations
import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'review' / 'lunar-scattered-light-source-contract-v1'

def load_model():
    spec = importlib.util.spec_from_file_location('rolo311g_lunar_source_contract_v1', ROOT / 'rolo311g.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load ROLO source contract')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class LunarScatteredLightSourceContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = load_model()

    def test_original_source_constants_and_rows(self):
        r = self.r
        rows = r.load_coefficients()
        self.assertEqual(len(rows), 19)
        self.assertEqual(rows[0]['wavelength_nm'], 350.0)
        self.assertEqual(rows[-1]['wavelength_nm'], 865.3)
        self.assertEqual(r.P4_DEG, 16.7498)
        self.assertEqual(r.P3_DEG, -30.5858)
        self.assertEqual(r.C2, -0.0013425)

    def test_unit_sensitive_known_values(self):
        r = self.r
        row553 = next(x for x in r.load_coefficients() if x['wavelength_nm'] == 553.8)
        g1 = r.RoloGeometry(7.0, 0.0, 0.0, 7.0)
        self.assertAlmostEqual(r.disk_equivalent_reflectance(row553, g1), 0.09869856650046396, places=14)
        g2 = r.RoloGeometry(16.0, 1.0, -2.0, 10.0)
        self.assertAlmostEqual(r.disk_equivalent_reflectance(row553, g2), 0.07577298460473274, places=14)

    def test_exact_band_nodes_and_distance_law(self):
        r = self.r
        g = r.RoloGeometry(7, 0, 0, 7)
        for wavelength, reflectance in r.band_reflectances(g):
            self.assertAlmostEqual(r.log_reflectance_interpolated(wavelength, g), reflectance, places=14)
        far = r.RoloGeometry(7, 0, 0, 7, 1.0, 2 * 384400.0)
        i0 = r.actual_lunar_irradiance_w_m2_nm(553.8, 1.85, g)
        i2 = r.actual_lunar_irradiance_w_m2_nm(553.8, 1.85, far)
        self.assertAlmostEqual(i2 / i0, 0.25, places=14)

    def test_fail_closed_support_and_research_labels(self):
        r = self.r
        for bad_phase in [0.0, 1.54, 97.01, 120.0]:
            with self.assertRaises(r.RoloSupportError):
                r.band_reflectances(r.RoloGeometry(bad_phase, 0, 0, 0))
        g = r.RoloGeometry(7, 0, 0, 7)
        for bad_wavelength in [350.0, 355.0, 865.31, 900.0]:
            with self.assertRaises(r.RoloSupportError):
                r.reconstruct_spectrum([bad_wavelength], [1.0], g)
        spectrum = r.reconstruct_spectrum([380.0, 553.8, 780.0], [1.7, 1.85, 1.4], g)
        self.assertFalse(spectrum['operationalRoloOrGiroClaim'])
        self.assertFalse(spectrum['validatedForAtmosphericScatteredMoonlight'])
        self.assertFalse(spectrum['productionAuthorized'])
        self.assertTrue(all(math.isfinite(x) and x > 0 for x in spectrum['lunarToaIrradianceWm2Nm']))

if __name__ == '__main__':
    unittest.main()
