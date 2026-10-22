import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "exact_aod_interval_support_v1.py"
SPEC = importlib.util.spec_from_file_location("exact_aod_interval_support_v1", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def synthetic_support():
    # Exactly 58 five-dimensional rows, matching the production cardinality.
    rows = []
    for i in range(58):
        rows.append([
            (i % 7) / 6.0,
            (i % 11) / 10.0,
            (i % 13) / 12.0,
            (i % 17) / 16.0,
            (i % 19) / 18.0,
        ])
    return rows


class ExactAodIntervalSupportV1Tests(unittest.TestCase):
    def test_coordinate_mapping_matches_frozen_provider_convention(self):
        fixed = MOD.v1_idw_cos_fixed_coordinates(
            sun_depression_deg=2.0,
            target_altitude_deg=5.0,
            relative_azimuth_deg=0.0,
            observer_elevation_m=0.0,
        )
        self.assertEqual(fixed, (0.0, 0.0, 1.0, 0.0))
        self.assertAlmostEqual(MOD.normalized_aod(0.05), 0.0)
        self.assertAlmostEqual(MOD.normalized_aod(0.40), 1.0)

    def test_exact_candidate_method_dominates_dense_grid_and_matches_to_resolution(self):
        support = synthetic_support()
        kwargs = dict(
            support_coordinates=support,
            sun_depression_deg=5.7,
            target_altitude_deg=42.0,
            relative_azimuth_deg=73.0,
            observer_elevation_m=1240.0,
            aod550_min=0.071,
            aod550_max=0.367,
        )
        exact = MOD.exact_max_nearest_support_distance(**kwargs)
        fixed = MOD.v1_idw_cos_fixed_coordinates(
            sun_depression_deg=kwargs["sun_depression_deg"],
            target_altitude_deg=kwargs["target_altitude_deg"],
            relative_azimuth_deg=kwargs["relative_azimuth_deg"],
            observer_elevation_m=kwargs["observer_elevation_m"],
        )
        lo = MOD.normalized_aod(kwargs["aod550_min"])
        hi = MOD.normalized_aod(kwargs["aod550_max"])
        grid_max = max(
            MOD.nearest_distance_at_x(fixed, support, lo + (hi - lo) * k / 20000)
            for k in range(20001)
        )
        self.assertGreaterEqual(exact["maximumNearestFrozenTrainingDistance"] + 1e-12, grid_max)
        self.assertLessEqual(exact["maximumNearestFrozenTrainingDistance"] - grid_max, 2e-4)
        self.assertFalse(exact["gridApproximationUsed"])
        self.assertFalse(exact["targetRadianceUsed"])

    def test_pairwise_crossing_can_be_worst_point_not_aod_endpoint(self):
        # Pad two controlling rows to production cardinality with distant rows.
        fixed = MOD.v1_idw_cos_fixed_coordinates(
            sun_depression_deg=6.25,
            target_altitude_deg=42.5,
            relative_azimuth_deg=90.0,
            observer_elevation_m=1250.0,
        )
        rows = [
            [*fixed, 0.25],
            [*fixed, 0.75],
        ]
        rows.extend([[9.0, 9.0, 9.0, 9.0, (i % 10) / 10.0] for i in range(56)])
        result = MOD.exact_max_nearest_support_distance(
            support_coordinates=rows,
            sun_depression_deg=6.25,
            target_altitude_deg=42.5,
            relative_azimuth_deg=90.0,
            observer_elevation_m=1250.0,
            aod550_min=0.05 + 0.20 * 0.35,
            aod550_max=0.05 + 0.80 * 0.35,
        )
        # Endpoints are 0.05 from a support node; the midpoint crossing is 0.25 away.
        self.assertAlmostEqual(result["maximumNearestFrozenTrainingDistance"], 0.25, places=12)
        self.assertAlmostEqual(MOD.normalized_aod(result["worstAod550"]), 0.5, places=12)

    def test_fails_closed_outside_frozen_physical_box(self):
        support = synthetic_support()
        with self.assertRaises(ValueError):
            MOD.exact_max_nearest_support_distance(
                support_coordinates=support,
                sun_depression_deg=1.99,
                target_altitude_deg=40.0,
                relative_azimuth_deg=90.0,
                observer_elevation_m=1000.0,
                aod550_min=0.10,
                aod550_max=0.20,
            )
        with self.assertRaises(ValueError):
            MOD.exact_max_nearest_support_distance(
                support_coordinates=support,
                sun_depression_deg=6.0,
                target_altitude_deg=40.0,
                relative_azimuth_deg=90.0,
                observer_elevation_m=1000.0,
                aod550_min=0.04,
                aod550_max=0.20,
            )

    def test_rejects_wrong_support_cardinality(self):
        with self.assertRaises(ValueError):
            MOD.exact_max_nearest_support_distance(
                support_coordinates=[[0, 0, 0, 0, 0]],
                sun_depression_deg=6.0,
                target_altitude_deg=40.0,
                relative_azimuth_deg=90.0,
                observer_elevation_m=1000.0,
                aod550_min=0.10,
                aod550_max=0.20,
            )


if __name__ == "__main__":
    unittest.main()
