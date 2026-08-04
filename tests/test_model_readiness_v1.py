from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments/model-readiness-v1"


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


contract = module("reference_contract", PACKAGE / "reference_dataset_contract.py")
design = module("training_design", PACKAGE / "training_design.py")
policy = module("importance_policy", PACKAGE / "importance_policy.py")


def stats(mean: float):
    return {
        "blockCount": 4,
        "meanCdM2": mean,
        "relativeStandardErrorOfMean": 0.04,
        "nodeMeanRadiance": [mean] * 15,
    }


class ModelReadinessTests(unittest.TestCase):
    def test_reference_anchor_contract(self):
        groups = sorted(contract.EXPECTED_GROUPS)
        records = []
        for index, group in enumerate(groups):
            geometry = {
                "geometryId": group,
                "sunDepressionDeg": 4.0 + index,
                "targetAltitudeDeg": 10.0 + index,
                "relativeAzimuthDeg": 30.0 + index,
                "observerElevationM": 0.0,
                "aod550": 0.15,
            }
            records.append({
                "groupId": group,
                "geometry": geometry,
                "methodStatistics": {"reference-vroom": stats(1.0), "alis": stats(0.9)},
                "methodOrigins": {"reference-vroom": "frozen", "alis": "held-out"},
                "meanRatioAlisToVroom": 0.9,
                "nodeAgreementFraction": 1.0,
            })
        dataset = {
            "schemaVersion": 1,
            "status": "AUDITED_COMPUTATIONAL_REFERENCE_DATASET",
            "sourceStageId": "cross-geometry-held-out-confirmation-timeout-continuation-v1",
            "screeningOnly": True,
            "observationValidationRequired": True,
            "records": records,
        }
        readiness = {
            "schemaVersion": 1,
            "status": "COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE",
            "computationalReferenceScreeningComplete": True,
            "acceptedReferenceGeometryCount": 6,
            "heldOutConfirmationFailureCount": 0,
            "technicalDiagnosisRequiredGeometryIds": [],
            "productionModelReady": False,
            "observationValidationRequired": True,
            "surrogateTrainingAutomaticallyAuthorized": False,
        }
        result = contract.validate(dataset, readiness)
        self.assertEqual(result["anchorCount"], 6)
        self.assertTrue(all(not row["eligibleForTraining"] for row in result["anchors"]))

    def test_reference_anchor_rejects_training_leakage_or_noise(self):
        with self.assertRaises(contract.ContractError):
            contract.validate({"schemaVersion": 1}, {})

    def test_importance_policy(self):
        self.assertEqual(policy.alis_importance_nm({"sunDepressionDeg": 12, "targetAltitudeDeg": 10, "aod550": 0.15}), 600.0)
        self.assertEqual(policy.alis_importance_nm({"sunDepressionDeg": 12, "targetAltitudeDeg": 45, "aod550": 0.30}), 500.0)
        self.assertEqual(policy.alis_importance_nm({"sunDepressionDeg": 6, "targetAltitudeDeg": 30, "aod550": 0.15}), 550.0)

    def test_training_design_is_deterministic_and_disjoint(self):
        spec = json.loads((PACKAGE / "training-design.proposal.json").read_text())
        first = design.build(spec, PACKAGE / "importance_policy.py")
        second = design.build(spec, PACKAGE / "importance_policy.py")
        self.assertEqual(first, second)
        self.assertEqual(first["geometryCount"], 96)
        self.assertEqual(first["caseCount"], 192)
        self.assertEqual([tier["geometryCount"] for tier in first["executionTiers"]], [48, 48])
        self.assertEqual([tier["caseCount"] for tier in first["executionTiers"]], [96, 96])
        self.assertEqual(sum(tier["configuredMcPhotonsSum"] for tier in first["executionTiers"]), first["configuredMcPhotonsSum"])
        self.assertFalse(set(first["trainingGeometryIds"]) & set(first["internalHoldoutGeometryIds"]))
        self.assertFalse(set(first["externalValidationAnchorIds"]) & set(first["trainingGeometryIds"]))
        self.assertEqual(len({case["seed"] for case in first["cases"]}), 192)
        self.assertTrue(all(case["method"] == "alis" for case in first["cases"]))
        self.assertFalse(first["scientificExecution"])

    def test_training_design_covers_all_importance_centers_and_depth_bands(self):
        spec = json.loads((PACKAGE / "training-design.proposal.json").read_text())
        result = design.build(spec, PACKAGE / "importance_policy.py")
        centers = {row["alisSpectralImportanceSamplingNm"] for row in result["geometries"]}
        photons = {row["photonHistoriesPerBlock"] for row in result["geometries"]}
        self.assertEqual(centers, {500.0, 550.0, 600.0})
        self.assertEqual(photons, {20_000_000, 50_000_000, 100_000_000, 200_000_000})


if __name__ == "__main__":
    unittest.main()
