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


class FinalModelPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.directory = cls.root / "modeling/surrogate-training-v2"
        cls.pipeline = load(
            cls.directory / "final_model_pipeline.py",
            "surrogate_training_v2_final_model_pipeline_test",
        )
        cls.runtime = load(
            cls.directory / "model_runtime.py",
            "surrogate_training_v2_model_runtime_test",
        )
        ContinuationHandoffTests.setUpClass()

    def handoff(self, root: Path):
        helper = ContinuationHandoffTests()
        _, _, outputs = helper.build(root)
        return outputs

    def train(self, root: Path, output_name: str = "model"):
        handoff = self.handoff(root / "handoff")
        outputs = self.pipeline.run_pipeline(
            handoff["dataset"],
            handoff["envelope"],
            handoff["design"],
            self.directory / "candidate-protocol.json",
            root / output_name,
            expected_main_sha="0" * 40,
            repository_root=self.root,
        )
        return handoff, outputs

    def test_trains_freezes_evaluates_and_predicts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            handoff, outputs = self.train(root)
            package = json.loads(outputs["package"].read_text())
            artifact = json.loads(outputs["artifact"].read_text())
            state = json.loads(outputs["state"].read_text())
            holdout = json.loads(outputs["holdout"].read_text())
            external = json.loads(outputs["external"].read_text())
            dataset = json.loads(handoff["dataset"].read_text())

            self.assertEqual(package["status"], "MODEL_TRAINED_AND_EVALUATED")
            self.assertEqual(package["trainingGeometryCount"], 39)
            self.assertEqual(package["internalHoldoutGeometryCount"], 9)
            self.assertEqual(package["hardAnchorCount"], 5)
            self.assertEqual(package["softDiagnosticCount"], 1)
            self.assertEqual(artifact["status"], "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT")
            self.assertFalse(artifact["internalHoldoutOpened"])
            self.assertEqual(state["status"], "MODEL_STATE_FROZEN")
            self.assertEqual(holdout["count"], 9)
            self.assertTrue(holdout["selectionForbidden"])
            self.assertTrue(holdout["thresholdTuningForbidden"])
            self.assertEqual(len(external["hardAnchors"]), 5)
            self.assertEqual(len(external["softDiagnostics"]), 1)
            self.assertTrue(external["softDiagnosticsReportOnly"])
            self.assertFalse(package["holdoutUsedForSelection"])
            self.assertFalse(package["externalAnchorsUsedForSelection"])
            self.assertTrue(package["modelUsableForPrediction"])
            self.assertFalse(package["observationallyValidated"])
            self.assertFalse(package["productionModelReady"])
            self.assertFalse(package["productionPromotionAuthorized"])

            training_id = package["trainingIds"][0]
            record = next(
                item for item in dataset["records"] if item["geometryId"] == training_id
            )
            prediction = self.runtime.predict(
                outputs["package"],
                outputs["artifact"],
                outputs["state"],
                {"geometryId": training_id, "geometry": record["geometry"]},
                repository_root=self.root,
            )
            self.assertEqual(prediction["status"], "PREDICTION_COMPLETE")
            self.assertGreater(prediction["predictionCdM2"], 0.0)
            self.assertGreaterEqual(prediction["uncertaintyLog"], 0.0)
            self.assertFalse(prediction["productionModelReady"])

    def test_regeneration_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            handoff = self.handoff(root / "handoff")
            first = self.pipeline.run_pipeline(
                handoff["dataset"], handoff["envelope"], handoff["design"],
                self.directory / "candidate-protocol.json", root / "first",
                expected_main_sha="0" * 40, repository_root=self.root,
            )
            second = self.pipeline.run_pipeline(
                handoff["dataset"], handoff["envelope"], handoff["design"],
                self.directory / "candidate-protocol.json", root / "second",
                expected_main_sha="0" * 40, repository_root=self.root,
            )
            self.assertEqual(
                {name: path.read_bytes() for name, path in first.items()},
                {name: path.read_bytes() for name, path in second.items()},
            )

    def test_runtime_refuses_state_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, outputs = self.train(root)
            state = json.loads(outputs["state"].read_text())
            state["residualRmse"] = float(state["residualRmse"]) + 1.0
            outputs["state"].write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
            with self.assertRaisesRegex(Exception, "model state hash changed"):
                self.runtime.load_model(
                    outputs["package"], outputs["artifact"], outputs["state"],
                    repository_root=self.root,
                )

    def test_pipeline_refuses_wrong_scientific_source_main(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            handoff = self.handoff(root / "handoff")
            with self.assertRaisesRegex(Exception, "main SHA"):
                self.pipeline.run_pipeline(
                    handoff["dataset"], handoff["envelope"], handoff["design"],
                    self.directory / "candidate-protocol.json", root / "model",
                    expected_main_sha="1" * 40, repository_root=self.root,
                )


if __name__ == "__main__":
    unittest.main()
