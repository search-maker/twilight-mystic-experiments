from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "modeling" / "surrogate-training-v2"
MAIN_SHA = "e7c7b0e1bef4f8b3e3989e7ed445a008846ac914"


def module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / filename)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


adapter = module("surrogate_training_v2_adapter", "adapter.py")
fixture = module("surrogate_training_v2_fixture", "synthetic_fixture.py")
training = module("surrogate_training_v2_training", "training.py")


class SurrogateTrainingV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = fixture.build(self.root)
        self.protocol = json.loads((PACKAGE / "candidate-protocol.json").read_text())

    def tearDown(self):
        self.temp.cleanup()

    def rebind_dataset_hash(self):
        envelope = json.loads(self.paths["envelope"].read_text())
        envelope["datasetRawSha256"] = hashlib.sha256(self.paths["dataset"].read_bytes()).hexdigest()
        self.paths["envelope"].write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")

    def make_adapter_eligible(self):
        envelope = json.loads(self.paths["envelope"].read_text())
        envelope["syntheticOnly"] = False
        envelope["scientificExecution"] = True
        self.paths["envelope"].write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")

    def read(self):
        return adapter.read_tier1_dataset(
            self.paths["dataset"], self.paths["envelope"], self.paths["design"],
            expected_main_sha=MAIN_SHA,
        )

    def test_synthetic_artifacts_carry_all_boundaries(self):
        for path in self.paths.values():
            value = json.loads(path.read_text())
            self.assertTrue(value["syntheticOnly"])
            self.assertFalse(value["scientificExecution"])
            self.assertFalse(value["observationallyValidated"])
            self.assertFalse(value["productionModelReady"])
            self.assertTrue(value["successDoesNotAuthorizeProduction"])

    def test_adapter_accepts_complete_partition_and_refuses_hash_tamper(self):
        self.make_adapter_eligible()
        partitioned = self.read()
        self.assertEqual(len(partitioned.training), 39)
        self.assertEqual(len(partitioned.internal_holdout), 9)
        envelope = json.loads(self.paths["envelope"].read_text())
        envelope["datasetRawSha256"] = "0" * 64
        self.paths["envelope"].write_text(json.dumps(envelope))
        with self.assertRaisesRegex(adapter.DatasetRefusal, "dataset hash mismatch"):
            self.read()

    def test_adapter_refuses_overlap_with_valid_hash(self):
        self.make_adapter_eligible()
        dataset = json.loads(self.paths["dataset"].read_text())
        dataset["internalHoldoutGeometryIds"][0] = dataset["trainingGeometryIds"][0]
        self.paths["dataset"].write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n")
        self.rebind_dataset_hash()
        with self.assertRaisesRegex(adapter.DatasetRefusal, "partitions overlap"):
            self.read()

    def test_adapter_refuses_role_change_and_adaptive_geometry(self):
        self.make_adapter_eligible()
        dataset = json.loads(self.paths["dataset"].read_text())
        dataset["records"][0]["role"] = "internal-holdout"
        self.paths["dataset"].write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n")
        self.rebind_dataset_hash()
        with self.assertRaisesRegex(adapter.DatasetRefusal, "role changed"):
            self.read()
        self.paths = fixture.build(self.root)
        self.make_adapter_eligible()
        dataset = json.loads(self.paths["dataset"].read_text())
        dataset["records"][0]["classification"] = "ADAPTIVE_CONTINUATION_REQUIRED"
        self.paths["dataset"].write_text(json.dumps(dataset, indent=2, sort_keys=True) + "\n")
        self.rebind_dataset_hash()
        with self.assertRaisesRegex(adapter.DatasetRefusal, "adaptive continuation"):
            self.read()

    def test_candidate_protocol_is_frozen_and_small(self):
        self.assertTrue(self.protocol["frozenBeforeInternalHoldout"])
        self.assertEqual(
            [item["candidateId"] for item in self.protocol["candidates"]],
            ["transparent-log-mean-baseline", "fixed-basis-log-ridge", "local-log-idw"],
        )
        self.assertEqual(self.protocol["evaluationOrder"][0], "training-cross-validation")
        self.assertFalse(self.protocol["productionBoundary"]["productionPromotionAuthorized"])

    def test_selection_is_training_only_and_deterministic(self):
        self.make_adapter_eligible()
        partitioned = self.read()
        selected1, results1 = training.cross_validate(self.protocol, list(partitioned.training))
        selected2, results2 = training.cross_validate(self.protocol, list(reversed(partitioned.training)))
        self.assertEqual(selected1, selected2)
        self.assertEqual(results1, results2)
        holdout_ids = {item["geometryId"] for item in partitioned.internal_holdout}
        self.assertFalse(holdout_ids & {item["geometryId"] for item in partitioned.training})

    def test_model_freezes_before_holdout_and_reports_anchors_separately(self):
        self.make_adapter_eligible()
        partitioned = self.read()
        model, artifact = training.freeze_artifact(
            self.protocol,
            partitioned,
            {"adapter.py": "a" * 64, "training.py": "b" * 64, "candidate-protocol.json": "c" * 64},
        )
        self.assertEqual(artifact["status"], "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT")
        self.assertFalse(artifact["internalHoldoutOpened"])
        self.assertFalse(artifact["productionBoundary"]["productionPromotionAuthorized"])
        holdout = training.open_internal_holdout_once(model, artifact, list(partitioned.internal_holdout))
        self.assertTrue(holdout["selectionForbidden"])
        external = training.evaluate_external(
            model, artifact, list(partitioned.hard_anchors), list(partitioned.soft_diagnostics)
        )
        self.assertEqual(len(external["hardAnchors"]), 5)
        self.assertEqual(len(external["softDiagnostics"]), 1)
        self.assertTrue(external["softDiagnosticsReportOnly"])
        self.assertTrue(external["softDiagnosticCannotAlonePassOrFail"])


if __name__ == "__main__":
    unittest.main()
