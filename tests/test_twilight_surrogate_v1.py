from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "modeling" / "twilight-surrogate-v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


allocator = load("allocator", PACKAGE / "two_stage_allocator.py")
splitter = load("splitter", PACKAGE / "split.py")
surrogate = load("surrogate", PACKAGE / "surrogate.py")
selector = load("selector", PACKAGE / "adaptive_baseline.py")


class TwilightSurrogateV1Tests(unittest.TestCase):
    def test_two_stage_allocation_adds_blocks_for_noisy_case(self) -> None:
        payload = {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-v1",
            "policy": {
                "pilotBlocks": 2,
                "maximumTotalBlocks": 6,
                "targetRelativeStandardError": 0.03,
                "targetTimeUncertaintyMinutes": 0.5,
            },
            "cases": [
                {
                    "caseId": "noisy",
                    "blockSeeds": [1, 2],
                    "independentBlockLuminance": [1.0, 1.5],
                    "absoluteLogLuminanceSlopePerMinute": 0.1,
                }
            ],
        }
        result = allocator.allocate(payload)
        recommendation = result["recommendations"][0]
        self.assertGreater(recommendation["additionalIndependentBlocks"], 0)
        self.assertLessEqual(recommendation["recommendedTotalBlocks"], 6)

    def test_two_stage_allocation_requires_unique_seeds(self) -> None:
        payload = {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-v1",
            "policy": {
                "pilotBlocks": 2,
                "maximumTotalBlocks": 4,
                "targetRelativeStandardError": 0.1,
                "targetTimeUncertaintyMinutes": 1.0,
            },
            "cases": [
                {
                    "caseId": "bad",
                    "blockSeeds": [1, 1],
                    "independentBlockLuminance": [1.0, 1.1],
                    "absoluteLogLuminanceSlopePerMinute": 0.1,
                }
            ],
        }
        with self.assertRaises(allocator.AllocationRefusal):
            allocator.allocate(payload)

    def test_split_keeps_groups_together(self) -> None:
        rows = [{"groupId": f"g{index // 2}", "seed": index} for index in range(30)]
        assigned = splitter.assign_groups(rows, "frozen-salt", 0.2, 0.2)
        mapping: dict[str, set[str]] = {}
        for row in assigned:
            mapping.setdefault(row["groupId"], set()).add(row["split"])
        self.assertTrue(all(len(value) == 1 for value in mapping.values()))
        self.assertFalse(splitter.summarize(assigned)["groupLeakage"])

    def test_split_is_deterministic(self) -> None:
        rows = [{"groupId": f"g{index}"} for index in range(20)]
        first = splitter.assign_groups(rows, "salt", 0.2, 0.2)
        second = splitter.assign_groups(list(reversed(rows)), "salt", 0.2, 0.2)
        self.assertEqual(
            {row["groupId"]: row["split"] for row in first},
            {row["groupId"]: row["split"] for row in second},
        )

    def synthetic_rows(self):
        rows = []
        for depth in range(3, 16):
            for altitude in (10.0, 30.0):
                group = f"d{depth}-a{altitude}"
                luminance = math.exp(
                    5.0 - 0.45 * depth + 0.01 * altitude + 0.02 * depth * 0.15
                )
                rows.append(
                    {
                        "groupId": group,
                        "sunDepressionDeg": float(depth),
                        "targetAltitudeDeg": altitude,
                        "relativeAzimuthDeg": 90.0,
                        "observerElevationM": 0.0,
                        "aod550": 0.15,
                        "albedo": 0.15,
                        "photopicLuminanceCdM2": luminance,
                        "logStandardError": 0.02,
                    }
                )
        return splitter.assign_groups(rows, "model-salt", 0.2, 0.2)

    def test_surrogate_trains_and_scores_withheld(self) -> None:
        rows = self.synthetic_rows()
        result = surrogate.train_and_evaluate(
            {
                "schemaVersion": 1,
                "stageId": "twilight-surrogate-v1",
                "rows": rows,
                "ridge": 1e-5,
            }
        )
        self.assertEqual(result["status"], "TRAINED_SYNTHETIC_OR_IMPORTED_DATA")
        self.assertTrue(result["withheld"]["available"])
        self.assertLess(result["withheld"]["rootMeanSquaredLogError"], 0.2)

    def test_surrogate_flags_out_of_domain(self) -> None:
        model = surrogate.fit(self.synthetic_rows(), 1e-5)
        result = surrogate.predict(
            model,
            {
                "sunDepressionDeg": 25.0,
                "targetAltitudeDeg": 80.0,
                "relativeAzimuthDeg": 250.0,
                "observerElevationM": 5000.0,
                "aod550": 1.5,
                "albedo": 0.8,
            },
        )
        self.assertTrue(result["outOfDomain"])
        self.assertTrue(result["outsideFeatureRanges"])

    def test_adaptive_selector_prioritizes_wide_or_curved_interval(self) -> None:
        payload = {
            "schemaVersion": 1,
            "stageId": "twilight-surrogate-v1",
            "policy": {
                "maximumNewPoints": 2,
                "maximumSunDepressionIntervalDeg": 2.0,
                "targetInterpolationLogError": 0.05,
            },
            "points": [
                {
                    "sunDepressionDeg": 3.0,
                    "photopicLuminanceCdM2": 100.0,
                    "logStandardError": 0.01,
                },
                {
                    "sunDepressionDeg": 5.0,
                    "photopicLuminanceCdM2": 60.0,
                    "logStandardError": 0.01,
                },
                {
                    "sunDepressionDeg": 10.0,
                    "photopicLuminanceCdM2": 5.0,
                    "logStandardError": 0.02,
                },
                {
                    "sunDepressionDeg": 12.0,
                    "photopicLuminanceCdM2": 2.5,
                    "logStandardError": 0.02,
                },
            ],
        }
        result = selector.select(payload)
        self.assertTrue(result["selectedPoints"])
        self.assertIn(
            7.5,
            [point["sunDepressionDeg"] for point in result["selectedPoints"]],
        )


if __name__ == "__main__":
    unittest.main()
