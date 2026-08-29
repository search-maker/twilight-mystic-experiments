from __future__ import annotations
import importlib.util
import math
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

    def test_finite_disk_sensitivity_geometry_is_exactly_frozen_33_direction_plan(self):
        m = self.m
        samples = m.finite_disk_direction_samples(
            moon_zenith_deg=48.25,
            target_altitude_deg=63.0,
            target_relative_azimuth_to_moon_deg=137.0,
            lunar_angular_radius_deg=0.258,
        )
        self.assertEqual(len(samples), 33)
        self.assertEqual(len({s['sampleId'] for s in samples}), 33)
        self.assertEqual(samples[0]['sampleId'], 'center')
        self.assertAlmostEqual(samples[0]['angularOffsetDeg'], 0.0, places=8)
        self.assertAlmostEqual(samples[0]['sourceZenithDeg'], 48.25, places=8)
        self.assertAlmostEqual(samples[0]['sourceAzimuthInCenterFrameDeg'], 0.0, places=8)
        self.assertAlmostEqual(samples[0]['targetRelativeAzimuthToSampleSourceDeg'], 137.0, places=8)
        self.assertTrue(all(s['sameFullDiskIntegratedRoloIrradianceRequired'] for s in samples))
        self.assertTrue(all(s['physicalResolvedDiskWeight'] is None for s in samples))

        inner = [s for s in samples if s['radiusFraction'] == 0.5]
        limb = [s for s in samples if s['radiusFraction'] == 1.0]
        self.assertEqual(len(inner), 16)
        self.assertEqual(len(limb), 16)
        for s in inner:
            self.assertAlmostEqual(s['angularOffsetDeg'], 0.129, places=8)
        for s in limb:
            self.assertAlmostEqual(s['angularOffsetDeg'], 0.258, places=8)
        self.assertEqual([s['positionAngleDeg'] for s in inner], [22.5 * i for i in range(16)])
        self.assertEqual([s['positionAngleDeg'] for s in limb], [22.5 * i for i in range(16)])

    def test_finite_disk_position_angle_orientation_and_fixed_target_direction(self):
        m = self.m
        samples = m.finite_disk_direction_samples(
            moon_zenith_deg=48.25,
            target_altitude_deg=63.0,
            target_relative_azimuth_to_moon_deg=137.0,
            lunar_angular_radius_deg=0.258,
        )
        zenithward = next(s for s in samples if s['sampleId'] == 'r100-pa00')
        azimuthward = next(s for s in samples if s['sampleId'] == 'r100-pa04')
        nadirward = next(s for s in samples if s['sampleId'] == 'r100-pa08')
        opposite_az = next(s for s in samples if s['sampleId'] == 'r100-pa12')
        self.assertLess(zenithward['sourceZenithDeg'], 48.25)
        self.assertGreater(nadirward['sourceZenithDeg'], 48.25)
        self.assertGreater(azimuthward['sourceAzimuthInCenterFrameDeg'], 0.0)
        self.assertGreater(opposite_az['sourceAzimuthInCenterFrameDeg'], 180.0)
        self.assertAlmostEqual(
            (azimuthward['targetRelativeAzimuthToSampleSourceDeg'] + azimuthward['sourceAzimuthInCenterFrameDeg']) % 360.0,
            137.0,
            places=8,
        )
        self.assertAlmostEqual(
            (opposite_az['targetRelativeAzimuthToSampleSourceDeg'] + opposite_az['sourceAzimuthInCenterFrameDeg']) % 360.0,
            137.0,
            places=8,
        )

    def test_finite_disk_sampling_rejects_nonphysical_radius(self):
        m = self.m
        for radius in (0.0, -0.1, 1.1, float('nan')):
            with self.subTest(radius=radius):
                with self.assertRaises(m.LunarMysticInputError):
                    m.finite_disk_direction_samples(
                        moon_zenith_deg=48.25,
                        target_altitude_deg=63.0,
                        target_relative_azimuth_to_moon_deg=137.0,
                        lunar_angular_radius_deg=radius,
                    )

    def test_sample_geometry_can_feed_collimated_mystic_renderer_without_claiming_disk_modeled(self):
        m = self.m
        sample = next(s for s in m.finite_disk_direction_samples(
            moon_zenith_deg=48.25,
            target_altitude_deg=63.0,
            target_relative_azimuth_to_moon_deg=137.0,
            lunar_angular_radius_deg=0.258,
        ) if s['sampleId'] == 'r100-pa04')
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            atmosphere = d / 'afglus-test.dat'
            atmosphere.write_text('100 1\n50 1\n10 1\n2 1\n0 1\n', encoding='utf-8')
            source = d / 'lunar-source.dat'
            m.write_lunar_source_file(source, [380.0, 553.8, 780.0], [1e-5, 2e-5, 1.5e-5])
            case_dir = d / 'case'
            case_dir.mkdir()
            text, provenance = m.render_lunar_mystic_input(
                data_dir=d,
                atmosphere_file=atmosphere,
                lunar_source_file=source,
                moon_zenith_deg=sample['sourceZenithDeg'],
                target_altitude_deg=sample['targetAltitudeDeg'],
                target_relative_azimuth_to_moon_deg=sample['targetRelativeAzimuthToSampleSourceDeg'],
                observer_elevation_m=1500.0,
                aod550=0.18,
                albedo=0.15,
                photon_histories=1000000,
                random_seed=12346,
                case_dir=case_dir,
            )
            self.assertIn(f"sza {sample['sourceZenithDeg']:.6f}", text)
            self.assertIn(f"phi {sample['targetRelativeAzimuthToSampleSourceDeg']:.6f}", text)
            self.assertFalse(provenance['finiteMoonDiskModeled'])
            self.assertFalse(provenance['validatedForAtmosphericScatteredMoonlight'])

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
