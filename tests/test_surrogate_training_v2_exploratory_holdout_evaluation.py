from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "modeling/surrogate-training-v2/exploratory_holdout_evaluation.py"
MODEL_PATH = ROOT / "modeling/surrogate-training-v2/evidence/exploratory-training-only-model.json"
PROTOCOL_PATH = ROOT / "modeling/surrogate-training-v2/exploratory_holdout_protocol.json"

spec = importlib.util.spec_from_file_location("exploratory_holdout_evaluation", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExploratoryHoldoutEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        cls.protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    def record(self, geometry_id: str, fraction: float, target_multiplier: float = 1.0) -> dict:
        lows = self.model["normalizationConstants"]["minimums"]
        highs = self.model["normalizationConstants"]["maximums"]
        geometry = {
            key: float(low) + fraction * (float(high) - float(low))
            for key, low, high in zip(module.FEATURES, lows, highs, strict=True)
        }
        provisional = {
            "geometryId": geometry_id,
            "role": "internal-holdout",
            "geometry": geometry,
            "statistics": {"meanCdM2": 1.0},
        }
        predicted = module.predict(self.model, provisional)["predictionCdM2"]
        provisional["statistics"]["meanCdM2"] = float(predicted) * target_multiplier
        return provisional

    def dataset(self, multipliers: list[float] | None = None) -> dict:
        if multipliers is None:
            multipliers = [1.0, 1.05, 0.95, 1.2, 0.8, 1.3, 0.77, 1.1, 0.9]
        records = [
            self.record(geometry_id, 0.1 + index * 0.1, multipliers[index])
            for index, geometry_id in enumerate(module.EXPECTED_HOLDOUT_IDS)
        ]
        value = {
            "schemaVersion": 1,
            "stageId": module.EXPECTED_DATASET_STAGE,
            "status": module.EXPECTED_DATASET_STATUS,
            "protocolSha256": self.protocol["protocolSha256"],
            "sourceModelHash": module.EXPECTED_MODEL_HASH,
            "sourceTrainingDatasetSha256": module.EXPECTED_TRAINING_DATASET_SHA256,
            "holdoutGeometryIds": list(module.EXPECTED_HOLDOUT_IDS),
            "holdoutRecordCount": 9,
            "holdoutValuesIncluded": True,
            "internalHoldoutOpenedExactlyOnce": True,
            "selectionFromHoldoutForbidden": True,
            "thresholdTuningFromHoldoutForbidden": True,
            "records": records,
        }
        value["holdoutDatasetSha256"] = module.canonical_sha256(value)
        return value

    def write_dataset(self, directory: Path, value: dict) -> Path:
        path = directory / "holdout.json"
        path.write_text(module.dump(value), encoding="utf-8", newline="\n")
        return path

    def test_protocol_and_model_are_exactly_frozen(self) -> None:
        module.validate_protocol(copy.deepcopy(self.protocol))
        module.validate_model(copy.deepcopy(self.model), MODEL_PATH)
        self.assertEqual(module.raw_sha256(MODEL_PATH), module.EXPECTED_MODEL_RAW_SHA256)
        self.assertEqual(self.model["modelHash"], module.EXPECTED_MODEL_HASH)
        self.assertEqual(self.protocol["holdoutGeometryIds"], list(module.EXPECTED_HOLDOUT_IDS))

    def test_passes_synthetic_holdout_with_frozen_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_dataset(Path(temporary), self.dataset())
            result = module.evaluate(
                model_path=MODEL_PATH,
                protocol_path=PROTOCOL_PATH,
                holdout_dataset_path=path,
            )
        self.assertEqual(result["status"], "INTERNAL_HOLDOUT_GENERALIZATION_PASSED")
        self.assertTrue(result["generalizationValidated"])
        self.assertTrue(all(result["acceptanceChecks"].values()))
        self.assertEqual(result["count"], 9)
        self.assertGreaterEqual(result["withinFactorTwoCount"], 7)
        self.assertEqual(result["outOfDomainCount"], 0)
        self.assertFalse(result["productionModelReady"])
        self.assertFalse(result["tier2Authorized"])
        supplied = result["resultSha256"]
        payload = {key: value for key, value in result.items() if key != "resultSha256"}
        self.assertEqual(supplied, module.canonical_sha256(payload))

    def test_fails_without_tuning_when_generalization_is_poor(self) -> None:
        bad = self.dataset([10.0] * 9)
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_dataset(Path(temporary), bad)
            result = module.evaluate(
                model_path=MODEL_PATH,
                protocol_path=PROTOCOL_PATH,
                holdout_dataset_path=path,
            )
        self.assertEqual(result["status"], "INTERNAL_HOLDOUT_GENERALIZATION_FAILED")
        self.assertFalse(result["generalizationValidated"])
        self.assertFalse(result["acceptanceChecks"]["meanAbsoluteLogError"])
        self.assertTrue(result["thresholdTuningFromHoldoutForbidden"])
        self.assertTrue(result["modelOrPreprocessingChangeAfterOpeningForbidden"])

    def test_refuses_protocol_threshold_tampering(self) -> None:
        changed = copy.deepcopy(self.protocol)
        changed["acceptanceCriteria"]["meanAbsoluteLogErrorMaximum"] = 99.0
        changed["protocolSha256"] = module.canonical_sha256(
            {key: value for key, value in changed.items() if key != "protocolSha256"}
        )
        with self.assertRaisesRegex(module.HoldoutRefusal, "acceptance criteria changed"):
            module.validate_protocol(changed)

    def test_refuses_model_artifact_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            changed = copy.deepcopy(self.model)
            changed["modelState"]["coefficients"][0] += 1e-6
            changed["modelHash"] = module.canonical_sha256(
                {key: value for key, value in changed.items() if key != "modelHash"}
            )
            path.write_text(module.dump(changed), encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(module.HoldoutRefusal, "raw hash changed"):
                module.validate_model(changed, path)

    def test_refuses_holdout_identity_drift(self) -> None:
        changed = self.dataset()
        changed["records"][0]["geometryId"] = "train-0006"
        changed["holdoutDatasetSha256"] = module.canonical_sha256(
            {key: value for key, value in changed.items() if key != "holdoutDatasetSha256"}
        )
        with self.assertRaisesRegex(module.HoldoutRefusal, "geometry order or identities changed"):
            module.validate_holdout_dataset(changed, self.protocol)

    def test_refuses_holdout_self_hash_drift(self) -> None:
        changed = self.dataset()
        changed["records"][0]["statistics"]["meanCdM2"] *= 1.01
        with self.assertRaisesRegex(module.HoldoutRefusal, "self-hash changed"):
            module.validate_holdout_dataset(changed, self.protocol)

    def test_refuses_out_of_domain_as_a_passing_result(self) -> None:
        changed = self.dataset()
        changed["records"][0]["geometry"][module.FEATURES[0]] = (
            float(self.model["normalizationConstants"]["maximums"][0]) + 1.0
        )
        prediction = module.predict(self.model, changed["records"][0])
        changed["records"][0]["statistics"]["meanCdM2"] = prediction["predictionCdM2"]
        changed["holdoutDatasetSha256"] = module.canonical_sha256(
            {key: value for key, value in changed.items() if key != "holdoutDatasetSha256"}
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_dataset(Path(temporary), changed)
            result = module.evaluate(
                model_path=MODEL_PATH,
                protocol_path=PROTOCOL_PATH,
                holdout_dataset_path=path,
            )
        self.assertFalse(result["generalizationValidated"])
        self.assertEqual(result["outOfDomainCount"], 1)
        self.assertFalse(result["acceptanceChecks"]["outOfDomainCount"])


if __name__ == "__main__":
    unittest.main()
