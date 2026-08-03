from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "twilight-surrogate-v1"
sys.path.insert(0, str(PACKAGE))

import harness  # noqa: E402
import run_harness as runner  # noqa: E402
import synthetic_data as synthetic  # noqa: E402


class TwilightSurrogateV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        synthetic.generate(self.data)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dataset_splits_are_disjoint(self) -> None:
        groups = [harness.load_jsonl(self.data / f"{name}.jsonl") for name in ("train", "validation", "withheld")]
        id_sets = [{row["id"] for row in group} for group in groups]
        self.assertFalse(id_sets[0] & id_sets[1])
        self.assertFalse(id_sets[0] & id_sets[2])
        self.assertFalse(id_sets[1] & id_sets[2])

    def test_exact_training_point_is_reproduced(self) -> None:
        train = harness.load_jsonl(self.data / "train.jsonl")
        model = harness.LogIdwSurrogate(train, neighbors=8)
        prediction = model.predict(train[0])
        self.assertAlmostEqual(prediction.value, train[0]["targetRadiance"], places=12)
        self.assertFalse(prediction.out_of_domain)

    def test_distance_weights_prevent_elevation_domination(self) -> None:
        base = {
            "sunDepressionDeg": 10.0,
            "targetAltitudeDeg": 30.0,
            "relativeAzimuthDeg": 90.0,
            "aod550": 0.15,
            "observerElevationM": 0.0,
        }
        elevation = {**base, "observerElevationM": 2000.0}
        depression = {**base, "sunDepressionDeg": 16.0}
        base_vector = harness.normalized_vector(base)
        self.assertLess(
            harness.euclidean(base_vector, harness.normalized_vector(elevation)),
            harness.euclidean(base_vector, harness.normalized_vector(depression)),
        )

    def test_withheld_harness_passes_frozen_gates(self) -> None:
        report = runner.run(self.data, self.root / "output")
        self.assertTrue(report["gates"]["passed"])
        self.assertLessEqual(report["withheld"]["meanAbsoluteLogError"], 0.09)
        self.assertGreaterEqual(report["withheld"]["twoSigmaCoverage"], 0.75)
        self.assertTrue(report["syntheticOnly"])

    def test_adaptive_selection_is_deterministic_and_unique(self) -> None:
        train = harness.load_jsonl(self.data / "train.jsonl")
        candidates = harness.load_jsonl(self.data / "candidates.jsonl")
        model = harness.LogIdwSurrogate(train, neighbors=10, distance_power=2.6)
        left = harness.select_adaptive_cases(model, candidates, limit=20)
        right = harness.select_adaptive_cases(model, candidates, limit=20)
        self.assertEqual([row["id"] for row in left], [row["id"] for row in right])
        self.assertEqual(len({row["id"] for row in left}), 20)

    def test_two_stage_allocation_uses_independent_block_bands(self) -> None:
        allocation = harness.allocate_two_stage(
            [
                {"caseId": "low", "value": 100.0, "sigma": 2.0},
                {"caseId": "medium", "value": 100.0, "sigma": 5.0},
                {"caseId": "high", "value": 100.0, "sigma": 10.0},
            ]
        )
        self.assertEqual([row["additionalIndependentBlocks"] for row in allocation], [0, 2, 4])
        self.assertEqual([row["allocationBand"] for row in allocation], ["sufficient", "moderate", "high"])


if __name__ == "__main__":
    unittest.main()
