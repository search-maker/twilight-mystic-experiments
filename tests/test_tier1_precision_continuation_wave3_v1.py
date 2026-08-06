from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Wave3V1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.package = load(
            cls.root / "experiments/tier1-precision-continuation-wave3-v1/package.py",
            "wave3_v1_test_package",
        )
        cls.wave2 = load(
            cls.root / "experiments/tier1-precision-continuation-wave2-v1/core.py",
            "wave3_v1_test_wave2_core",
        )
        cls.active = ["train-0003", "train-0015"]

    def analysis(self, active=None):
        active = list(self.active if active is None else active)
        points = []
        for geometry_id in self.wave2.ACTIVE_GEOMETRY_IDS:
            is_active = geometry_id in active
            points.append(
                {
                    "geometryId": geometry_id,
                    "role": "internal-holdout" if geometry_id in {"train-0015", "train-0035"} else "surrogate-training",
                    "blockCount": 6,
                    "valuesCdM2": [1.0] * 6,
                    "relativeStandardErrorOfMean": 0.2 if is_active else 0.04,
                    "zeroHitBlockCount": 0,
                    "classification": "ADAPTIVE_CONTINUATION_REQUIRED" if is_active else "PRECISION_TARGET_MET",
                    "numericalStatus": "NUMERICAL_PRECISION_INSUFFICIENT" if is_active else "NUMERICALLY_CONVERGED_TARGET",
                    "capReached": False,
                    "scientificallyEligible": not is_active,
                }
            )
        for geometry_id in set(self.wave2.proposal(self.root)["base"].CONTINUATION_GEOMETRY_IDS) - set(self.wave2.ACTIVE_GEOMETRY_IDS):
            points.append(
                {
                    "geometryId": geometry_id,
                    "role": "internal-holdout" if geometry_id == "train-0045" else "surrogate-training",
                    "blockCount": 4,
                    "valuesCdM2": [1.0] * 4,
                    "relativeStandardErrorOfMean": 0.04,
                    "zeroHitBlockCount": 0,
                    "classification": "PRECISION_TARGET_MET",
                    "numericalStatus": "NUMERICALLY_CONVERGED_TARGET",
                    "capReached": False,
                    "scientificallyEligible": True,
                }
            )
        value = {
            "schemaVersion": 1,
            "stageId": self.package.SOURCE_STAGE_ID,
            "sourceWave1AggregateSha256": "1" * 64,
            "sourceWave1AuditSha256": "2" * 64,
            "wave2AggregateSha256": "3" * 64,
            "wave2AuditSha256": "4" * 64,
            "analysis": {
                "schemaVersion": 2,
                "stageId": "tier1-precision-continuation-analysis-v2",
                "status": "CONTINUATION_ANALYZED",
                "points": sorted(points, key=lambda item: item["geometryId"]),
                "nextWaveGeometryIds": active,
                "exhaustedGeometryIds": [],
                "scientificallyEligible": not active,
                "additionalExecutionAutomaticallyAuthorized": False,
                "surrogateFitAuthorized": False,
                "productionPromotionAuthorized": False,
            },
            "additionalExecutionAutomaticallyAuthorized": False,
            "surrogateFitAuthorized": False,
            "internalHoldoutOpened": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        value["analysisSha256"] = self.package.canonical_sha256(value)
        return value

    def write_source(self, root: Path, value=None):
        path = root / "analysis.json"
        path.write_text(
            json.dumps(value or self.analysis(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def test_dynamic_preregistration_uses_only_original_b7_b8_subset(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_path = self.write_source(root)
            value = self.package.build_preregistration(
                self.package.load_json(source_path), source_path, self.root
            )
            self.assertEqual(value["status"], "PREPARATION_ONLY_NOT_AUTHORIZED")
            self.assertEqual(value["wave"], 3)
            self.assertEqual(value["blocks"], [7, 8])
            self.assertEqual(value["geometryIds"], self.active)
            self.assertEqual(value["geometryCount"], 2)
            self.assertEqual(value["caseCount"], 4)
            self.assertEqual(value["trainingGeometryIds"], ["train-0003"])
            self.assertEqual(value["internalHoldoutGeometryIds"], ["train-0015"])
            state = self.wave2.proposal(self.root)
            expected = [
                state["base"].PRECOMPUTED_SEEDS[geometry_id][block - 3]
                for geometry_id in self.active
                for block in (7, 8)
            ]
            observed = [row["seed"] for row in value["cases"]]
            self.assertEqual(observed, expected)
            self.assertEqual(value["seedProof"]["wave3SeedsSha256"], self.package.canonical_sha256(expected))
            self.assertEqual(value["seedProof"]["consumedOverlap"], [])
            self.assertTrue(value["seedProof"]["wave3SubsetOfOriginalPreregisteredB7B8"])
            self.assertEqual(value["candidateIdentity"]["authorizationOrdinal"], 13)
            self.assertFalse(value["candidateIdentity"]["allocated"])
            self.assertFalse(value["authorizationEnabled"])
            self.assertFalse(value["dispatchEnabled"])
            self.assertFalse(value["surrogateTrainingAuthorized"])
            self.assertFalse(value["internalHoldoutOpeningAuthorized"])

    def test_generation_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self.write_source(root)
            first, second = root / "a", root / "b"
            self.package.write_generated(source, first, self.root)
            self.package.write_generated(source, second, self.root)
            self.assertEqual(
                {path.name: path.read_bytes() for path in first.iterdir()},
                {path.name: path.read_bytes() for path in second.iterdir()},
            )

    def test_refuses_when_no_wave_three_is_required(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = self.write_source(root, self.analysis([]))
            with self.assertRaisesRegex(Exception, "no wave three required"):
                self.package.build_preregistration(
                    self.package.load_json(source), source, self.root
                )

    def test_refuses_analysis_hash_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            value = self.analysis()
            value["analysisSha256"] = "f" * 64
            source = self.write_source(root, value)
            with self.assertRaisesRegex(Exception, "self-hash changed"):
                self.package.build_preregistration(
                    self.package.load_json(source), source, self.root
                )

    def test_refuses_active_set_outside_reviewed_wave_two(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            value = self.analysis()
            value["analysis"]["nextWaveGeometryIds"] = ["train-0017"]
            value["analysisSha256"] = self.package.canonical_sha256(
                {key: item for key, item in value.items() if key != "analysisSha256"}
            )
            source = self.write_source(root, value)
            with self.assertRaisesRegex(Exception, "outside the reviewed wave-two universe"):
                self.package.build_preregistration(
                    self.package.load_json(source), source, self.root
                )

    def test_refuses_active_point_that_is_not_b1_b6_adaptive(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            value = self.analysis()
            point = next(item for item in value["analysis"]["points"] if item["geometryId"] == "train-0003")
            point["blockCount"] = 4
            value["analysisSha256"] = self.package.canonical_sha256(
                {key: item for key, item in value.items() if key != "analysisSha256"}
            )
            source = self.write_source(root, value)
            with self.assertRaisesRegex(Exception, "not an active b1-b6 continuation"):
                self.package.build_preregistration(
                    self.package.load_json(source), source, self.root
                )


if __name__ == "__main__":
    unittest.main()
