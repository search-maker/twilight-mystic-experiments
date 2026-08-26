from __future__ import annotations
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_mystic_input.py'

def load_module():
    name = 'lunar_mystic_input_contract_v1'
    spec = importlib.util.spec_from_file_location(name, MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load lunar MYSTIC input contract')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module

class LunarMysticInputContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_custom_source_units_geometry_and_level_b_elevation_semantics(self):
        m = self.m
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            atmosphere = d / 'afglus-test.dat'
            atmosphere.write_text('100 1\n50 1\n10 1\n2 1\n0 1\n', encoding='utf-8')
            source = d / 'lunar-source.dat'
            meta = m.write_lunar_source_file(source, [380.0, 553.8, 780.0], [1e-5, 2e-5, 1.5e-5])
            self.assertEqual(meta['unit'], 'mW m-2 nm-1')
            self.assertTrue(meta['exactRequestedWavelengthCoverage'])
            self.assertEqual(meta['startNm'], 380.0)
            self.assertEqual(meta['stopNm'], 780.0)
            self.assertEqual(source.read_text().splitlines()[0], '380.000000 1.000000000000e-02')
            case_dir = d / 'case'
            case_dir.mkdir()
            text, provenance = m.render_lunar_mystic_input(
                data_dir=d,
                atmosphere_file=atmosphere,
                lunar_source_file=source,
                moon_zenith_deg=48.25,
                target_altitude_deg=90.0,
                target_relative_azimuth_to_moon_deg=137.0,
                observer_elevation_m=1500.0,
                aod550=0.18,
                albedo=0.15,
                photon_histories=1000000,
                random_seed=12345,
                case_dir=case_dir,
            )
            self.assertIn(f'source solar {source.resolve()}', text)
            self.assertIn('sza 48.250000', text)
            self.assertIn('phi0 0.000000', text)
            self.assertIn('phi 137.000000', text)
            self.assertIn('umu -1.00000000', text)
            self.assertIn('atm_z_grid 1.500000 2.000000 10.000000 50.000000 100.000000', text)
            self.assertEqual(text.count('zout 0.000000'), 1)
            self.assertNotIn('day_of_year ', text)
            self.assertNotIn('\naltitude ', '\n' + text)
            self.assertNotIn('mc_elevation_file ', text)
            self.assertFalse(provenance['dayOfYearDistanceScalingApplied'])
            self.assertFalse(provenance['finiteMoonDiskModeled'])
            self.assertFalse(provenance['validatedForAtmosphericScatteredMoonlight'])
            self.assertFalse(provenance['productionAuthorized'])

    def test_fail_closed_source_and_input_validation(self):
        m = self.m
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            invalid_sources = [
                ([380, 379, 780], [1e-5, 1e-5, 1e-5]),
                ([380], [1e-5]),
                ([379, 780], [1e-5, 1e-5]),
                ([380, 779], [1e-5, 1e-5]),
                ([380, 780], [-1e-5, 1e-5]),
            ]
            for wavelengths, irradiance in invalid_sources:
                with self.subTest(wavelengths=wavelengths, irradiance=irradiance):
                    with self.assertRaises(m.LunarMysticInputError):
                        m.write_lunar_source_file(d / 'bad.dat', wavelengths, irradiance)

if __name__ == '__main__':
    unittest.main()
