from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExploratoryRoleMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module = load(
            cls.root / "modeling/surrogate-training-v2/exploratory_noisy_label_training_exact.py",
            "exploratory_role_map_test_module",
        )
        cls.exhausted = [
            "train-0003", "train-0007", "train-0011", "train-0013", "train-0015",
            "train-0019", "train-0023", "train-0027", "train-0029", "train-0031",
            "train-0035", "train-0039", "train-0041", "train-0043", "train-0047",
        ]

    def binding(self):
        value = {
            "schemaVersion": 1,
            "stageId": "surrogate-training-v2-wave3-terminal-source-binding-v1",
            "status": "AUDITED_THREE_WAVE_SOURCE_BOUND",
            "runId": 31070968611,
            "runAttempt": 1,
            "authorizationRef": "6c22de3578b1b0dcbc640779baa66be8d1051fe1",
            "executionSourceMainSha": "ae81798f538899b09b6c03c3d6e90ab93458427c",
            "executionManifestSha256": "822fc607d4418835074d53b5990163a46a3d7969d499dcbe5d601c9952aa0958",
            "sourceOrdinal12AnalysisRawSha256": "c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237",
            "sourceOrdinal12AnalysisSha256": "8e87fd440d15233dc66543a9ca011535a857b12b5602fd506f6466a900bfafc2",
            "artifactCount": 35,
            "caseArtifactCount": 30,
            "geometryCount": 15,
            "nextWaveGeometryIds": [],
            "scientificallyEligible": False,
            "exhaustedGeometryIds": self.exhausted,
            "aggregateRawSha256": "1" * 64,
            "auditRawSha256": "2" * 64,
            "analysisRawSha256": "3" * 64,
            "terminalReportRawSha256": "4" * 64,
            "terminalReportSha256": "5" * 64,
            "additionalExecutionAutomaticallyAuthorized": False,
            "internalHoldoutOpened": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        }
        value["bindingSha256"] = self.module.canonical_sha256(value)
        return value

    def dataset(self):
        training_exhausted = set(self.exhausted) & set(self.module.TRAINING_GEOMETRY_IDS)
        rows = []
        for index, geometry_id in enumerate(self.module.TRAINING_GEOMETRY_IDS):
            exhausted = geometry_id in training_exhausted
            rows.append({
                "geometryId": geometry_id,
                "role": "surrogate-training",
                "geometry": {
                    "sunDepressionDeg": 1.0 + index * 0.1,
                    "targetAltitudeDeg": 2.0 + (index % 8),
                    "relativeAzimuthDeg": 5.0 + index * 3.0,
                    "observerElevationM": 10.0 + index * 20.0,
                    "aod550": 0.05 + (index % 5) * 0.02,
                },
                "statistics": {
                    "meanCdM2": math.exp(-9.0 + index * 0.04),
                    "relativeStandardErrorOfMean": 0.32 if exhausted else 0.04,
                    "zeroHitBlockCount": 0,
                },
                "classification": "PRECISION_CONTINUATION_EXHAUSTED" if exhausted else "PRECISION_TARGET_MET",
                "scientificallyEligible": not exhausted,
            })
        value = {
            "schemaVersion": 1,
            "stageId": self.module.TRAINING_DATASET_STAGE,
            "status": self.module.TRAINING_DATASET_STATUS,
            "sourceBindingSha256": self.binding()["bindingSha256"],
            "trainingGeometryIds": list(self.module.TRAINING_GEOMETRY_IDS),
            "internalHoldoutGeometryIdsExcludedAndUnopened": list(self.module.HOLDOUT_GEOMETRY_IDS),
            "holdoutRecordCount": 0,
            "holdoutValuesIncluded": False,
            "records": rows,
        }
        value["datasetSha256"] = self.module.canonical_sha256(value)
        return value

    def test_frozen_role_map_matches_every_fifth_holdout(self):
        self.assertEqual(
            list(self.module.HOLDOUT_GEOMETRY_IDS),
            ["train-0005", "train-0010", "train-0015", "train-0020", "train-0025", "train-0030", "train-0035", "train-0040", "train-0045"],
        )
        self.assertEqual(len(self.module.TRAINING_GEOMETRY_IDS), 39)
        self.assertIn("train-0047", self.module.TRAINING_GEOMETRY_IDS)
        self.assertNotIn("train-0035", self.module.TRAINING_GEOMETRY_IDS)

    def test_freezes_model_on_correct_39_training_records(self):
        artifact = self.module.run(self.dataset(), self.binding())
        self.assertEqual(artifact["trainingGeometryIds"], list(self.module.TRAINING_GEOMETRY_IDS))
        self.assertEqual(artifact["internalHoldoutGeometryIdsExcludedAndUnopened"], list(self.module.HOLDOUT_GEOMETRY_IDS))
        self.assertEqual(artifact["holdoutRecordCount"], 0)
        self.assertFalse(artifact["holdoutValuesRead"])
        self.assertFalse(artifact["scientificallyEligibleModelClaimed"])
        self.assertIn("train-0047", artifact["ineligibleTrainingGeometryIds"])
        self.assertNotIn("train-0035", artifact["trainingGeometryIds"])

    def test_refuses_holdout_record_injection(self):
        dataset = self.dataset()
        dataset["records"].append({"geometryId": "train-0005", "role": "internal-holdout"})
        dataset["datasetSha256"] = self.module.canonical_sha256(
            {key: value for key, value in dataset.items() if key != "datasetSha256"}
        )
        with self.assertRaisesRegex(Exception, "exactly 39 records"):
            self.module.run(dataset, self.binding())


if __name__ == "__main__":
    unittest.main()
