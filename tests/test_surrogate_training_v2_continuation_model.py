from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_surrogate_training_v2_continuation_handoff import ContinuationHandoffTests


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ContinuationModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "modeling/surrogate-training-v2"
        cls.model_run = load(
            cls.directory / "continuation_training.py",
            "surrogate_training_v2_continuation_model_test",
        )
        cls.training = load(
            cls.directory / "training.py",
            "surrogate_training_v2_continuation_model_training_test",
        )
        ContinuationHandoffTests.setUpClass()
        cls.handoff_test = ContinuationHandoffTests()

    def fixture(self, root: Path):
        _, _, handoff = self.handoff_test.build(root / "handoff-source")
        return handoff

    def run_model(self, root: Path, output_name: str = "model"):
        handoff = self.fixture(root)
        return self.model_run.run(
            repository_root=self.root,
            dataset_path=handoff["dataset"],
            envelope_path=handoff["envelope"],
            design_path=handoff["design"],
            protocol_path=self.directory / "candidate-protocol.json",
            exact_main_sha="0" * 40,
            output_dir=root / output_name,
        )

    def test_end_to_end_model_is_frozen_serialized_and_evaluated_in_order(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.run_model(Path(raw))
            artifact = json.loads(result["model"].read_text())
            selection = json.loads(result["selection"].read_text())
            holdout = json.loads(result["holdout"].read_text())
            external = json.loads(result["external"].read_text())
            report = json.loads(result["report"].read_text())
            self.assertEqual(artifact["status"], "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT")
            self.assertIn("modelState", artifact)
            self.assertIn("residualRmseLog", artifact)
            self.assertEqual(len(artifact["trainingIds"]), 39)
            self.assertEqual(len(artifact["holdoutIds"]), 9)
            self.assertFalse(artifact["internalHoldoutOpened"])
            self.assertEqual(selection["status"], "TRAINING_ONLY_SELECTION_COMPLETE_MODEL_FROZEN")
            self.assertEqual(len(selection["trainingGeometryIds"]), 39)
            self.assertEqual(len(selection["internalHoldoutGeometryIdsExcludedFromSelection"]), 9)
            self.assertFalse(selection["internalHoldoutOpened"])
            self.assertEqual(holdout["count"], 9)
            self.assertTrue(holdout["selectionForbidden"])
            self.assertTrue(holdout["thresholdTuningForbidden"])
            self.assertTrue(holdout["internalHoldoutOpenedExactlyOnceByThisRun"])
            self.assertEqual(len(external["hardAnchors"]), 5)
            self.assertEqual(len(external["softDiagnostics"]), 1)
            self.assertTrue(external["softDiagnosticsReportOnly"])
            self.assertFalse(external["productionPromotionAuthorized"])
            self.assertEqual(
                report["status"],
                "MODEL_TRAINED_FROZEN_AND_EVALUATED_NOT_PRODUCTION_READY",
            )
            self.assertTrue(report["modelStateSerialized"])
            self.assertTrue(report["modelRestorationVerified"])
            self.assertTrue(report["internalHoldoutOpenedExactlyOnce"])
            self.assertFalse(report["holdoutUsedForSelection"])
            self.assertFalse(report["anchorsUsedForSelection"])
            self.assertFalse(report["productionModelReady"])
            self.assertFalse(report["productionPromotionAuthorized"])

    def test_model_run_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            handoff = self.fixture(root)
            outputs = []
            for name in ("first", "second"):
                output = self.model_run.run(
                    repository_root=self.root,
                    dataset_path=handoff["dataset"],
                    envelope_path=handoff["envelope"],
                    design_path=handoff["design"],
                    protocol_path=self.directory / "candidate-protocol.json",
                    exact_main_sha="0" * 40,
                    output_dir=root / name,
                )
                outputs.append({key: path.read_bytes() for key, path in output.items()})
            self.assertEqual(outputs[0], outputs[1])

    def test_serialized_model_restores_exact_predictions(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            handoff = self.fixture(root)
            result = self.model_run.run(
                repository_root=self.root,
                dataset_path=handoff["dataset"],
                envelope_path=handoff["envelope"],
                design_path=handoff["design"],
                protocol_path=self.directory / "candidate-protocol.json",
                exact_main_sha="0" * 40,
                output_dir=root / "model",
            )
            artifact = json.loads(result["model"].read_text())
            restored = self.model_run.restore_model(self.training, artifact)
            adapter = load(
                self.directory / "adapter.py",
                "surrogate_training_v2_continuation_model_adapter_restore_test",
            )
            partitioned = adapter.read_tier1_dataset(
                handoff["dataset"],
                handoff["envelope"],
                handoff["design"],
                expected_main_sha="0" * 40,
            )
            predictions = [restored.predict(record) for record in partitioned.training]
            self.assertEqual(len(predictions), 39)
            self.assertTrue(all(prediction["predictionCdM2"] > 0 for prediction in predictions))

    def test_refuses_protocol_drift_before_training(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            handoff = self.fixture(root)
            protocol = json.loads((self.directory / "candidate-protocol.json").read_text())
            protocol["frozenBeforeInternalHoldout"] = False
            protocol_path = root / "protocol.json"
            protocol_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n")
            with self.assertRaisesRegex(Exception, "candidate protocol changed"):
                self.model_run.run(
                    repository_root=self.root,
                    dataset_path=handoff["dataset"],
                    envelope_path=handoff["envelope"],
                    design_path=handoff["design"],
                    protocol_path=protocol_path,
                    exact_main_sha="0" * 40,
                    output_dir=root / "model",
                )

    def test_refuses_serialized_model_hash_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.run_model(Path(raw))
            artifact = json.loads(result["model"].read_text())
            artifact["generatedModelHash"] = "f" * 64
            with self.assertRaisesRegex(Exception, "serialized model artifact hash changed"):
                self.model_run.restore_model(self.training, artifact)


if __name__ == "__main__":
    unittest.main()
