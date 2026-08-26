import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "certified_aod_scenario_extrema_v1.py"
SPEC = importlib.util.spec_from_file_location("certified_aod_scenario_extrema_v1", MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def base_fixture():
    coefficients = [[0.0, 0.0, 0.0] for _ in range(16)]
    coefficients[5] = [0.001, 0.002, 0.003]  # linear in frozen log-AOD coordinate o
    coordinates = []
    targets = []
    for i in range(58):
        coordinates.append([
            (i % 17) / 16.0,
            ((i * 3) % 19) / 18.0,
            ((i * 7) % 23) / 22.0,
            ((i * 11) % 29) / 28.0,
            0.20,
        ])
        targets.append([0.0, 0.0, 0.0])
    return {
        "sourceModelCanonicalSha256": MOD.BASE_MODEL_SHA256,
        "primaryBasis": "PHYSICAL_COMPACT_16_TERMS",
        "residualCoordinateSystem": "V1_IDW_COS_COORDINATES",
        "residualNeighbors": 6,
        "residualPower": 1,
        "residualShrinkage": 1,
        "primaryCoefficients": coefficients,
        "residualCoordinates": coordinates,
        "residualTargets": targets,
    }


def asiv_fixture():
    rows = []
    for i in range(24):
        rows.append({
            "cellId": f"fixture-{i:02d}",
            "coord": [
                (i % 7) / 6.0,
                ((i * 3) % 11) / 10.0,
                ((i * 5) % 13) / 12.0,
                0.80,
            ],
            "target": [0.0] * 12,
        })
    return {
        "sourceSelectedModelCanonicalSha256": MOD.ASIV_MODEL_SHA256,
        "candidateSpec": {
            "candidateId": "IDW_COS_4D-k8-p2",
            "neighbors": 8,
            "power": 2.0,
        },
        "holdoutValuesIncluded": False,
        "training": rows,
    }


class CertifiedAodScenarioExtremaV1Tests(unittest.TestCase):
    def test_pairwise_crossing_is_explicit_partition_boundary(self):
        rows = [
            {"coord": [0.0, 0.0], "target": [0.0], "id": 0},
            {"coord": [0.0, 1.0], "target": [1.0], "id": 1},
        ]
        cuts = MOD._pairwise_crossings((0.0,), rows, "coord", 1, 0.0, 1.0)
        self.assertIn(0.5, cuts)

    def test_exact_hit_is_bounded_without_epsilon_substitution(self):
        rows = [
            {"coord": [0.0, 0.0], "target": [2.0], "id": 0},
            {"coord": [1.0, 0.5], "target": [7.0], "id": 1},
        ]
        bound = MOD._idw_bound(
            rows,
            "coord",
            "target",
            (0.0,),
            1,
            (0, 1),
            0.0,
            0.1,
            1,
            0,
        )
        self.assertLessEqual(bound.lo, 2.0)
        self.assertGreaterEqual(bound.hi, 2.0)
        self.assertTrue(bound.hi < 7.0)

    def test_full_aod_extrema_are_value_free_and_certified(self):
        out = MOD.certified_extrema(
            base_fixture(),
            asiv_fixture(),
            sun=6.0,
            alt=30.0,
            raz=90.0,
            elev=1000.0,
            aod_lo=0.05,
            aod_hi=0.40,
            log_tolerance=1e-4,
            max_depth=30,
            max_nodes=10000,
        )
        self.assertTrue(out["certified"])
        self.assertFalse(out["targetRadianceUsed"])
        self.assertFalse(out["adaptiveSearchUsingMeasuredRadiance"])
        self.assertEqual(out["algorithmId"], "CERTIFIED_AOD_SCENARIO_EXTREMA_INTERVAL_BNB_V1")
        self.assertLess(out["branchNodes"], 10000)

        expected_max = {"photopic": 0.001, "scotopic": 0.002, "johnsonV": 0.003}
        for scenario in MOD.SCENARIOS:
            for channel in MOD.CHANNELS:
                row = out["scenarios"][scenario][channel]
                self.assertAlmostEqual(row["innerMin"], 0.0, places=14)
                self.assertAlmostEqual(row["innerMax"], expected_max[channel], places=14)
                self.assertLessEqual(row["minCertificationGap"], 1.0001e-4)
                self.assertLessEqual(row["maxCertificationGap"], 1.0001e-4)

    def test_runtime_hashes_are_pinned(self):
        self.assertEqual(MOD.BASE_RUNTIME_SHA256, "6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4")
        self.assertEqual(MOD.ASIV_RUNTIME_SHA256, "a324408e87fd1ffa5f3fc386e77e54fe046eb3e749f2b39a699712ba355eb060")
        self.assertEqual(MOD.DEFAULT_LOG_TOLERANCE, 1e-4)


if __name__ == "__main__":
    unittest.main()
