from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ordinal13TerminalBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.model = load(
            cls.root / "modeling/surrogate-training-v2/exploratory_noisy_label_training_exact.py",
            "ordinal13_terminal_binding_model",
        )
        cls.path = cls.root / "modeling/surrogate-training-v2/evidence/ordinal13-terminal-source-binding.json"
        cls.raw = cls.path.read_bytes()
        cls.value = json.loads(cls.raw)

    def test_exact_terminal_source_binding_is_valid(self):
        self.model.validate_source_binding(self.value)
        self.assertEqual(
            hashlib.sha256(self.raw).hexdigest(),
            "6f5fea9e1690d72cd9701c69a85da925505200d20a71d1ec08823f299590cce4",
        )
        self.assertEqual(
            self.value["bindingSha256"],
            "fccdf0d31301b2aa3fe11b5523516070600650f234435ed7a870690296dab004",
        )

    def test_exact_terminal_identity_and_artifact_universe(self):
        self.assertEqual(self.value["runId"], 31070968611)
        self.assertEqual(self.value["runAttempt"], 1)
        self.assertEqual(
            self.value["authorizationRef"],
            "6c22de3578b1b0dcbc640779baa66be8d1051fe1",
        )
        self.assertEqual(
            self.value["executionSourceMainSha"],
            "ae81798f538899b09b6c03c3d6e90ab93458427c",
        )
        self.assertEqual(self.value["artifactCount"], 35)
        self.assertEqual(self.value["caseArtifactCount"], 30)
        self.assertEqual(self.value["geometryCount"], 15)
        self.assertEqual(
            self.value["executionManifestSha256"],
            "822fc607d4418835074d53b5990163a46a3d7969d499dcbe5d601c9952aa0958",
        )

    def test_terminal_path_is_ineligible_exhausted_and_closed(self):
        expected = [
            "train-0003", "train-0007", "train-0011", "train-0013", "train-0015",
            "train-0019", "train-0023", "train-0027", "train-0029", "train-0031",
            "train-0035", "train-0039", "train-0041", "train-0043", "train-0047",
        ]
        self.assertEqual(self.value["exhaustedGeometryIds"], expected)
        self.assertEqual(self.value["nextWaveGeometryIds"], [])
        self.assertFalse(self.value["scientificallyEligible"])
        self.assertFalse(self.value["additionalExecutionAutomaticallyAuthorized"])
        self.assertFalse(self.value["internalHoldoutOpened"])
        self.assertFalse(self.value["tier2Authorized"])
        self.assertFalse(self.value["productionPromotionAuthorized"])

    def test_frozen_role_map_excludes_every_fifth_geometry(self):
        self.assertEqual(
            list(self.model.HOLDOUT_GEOMETRY_IDS),
            ["train-0005", "train-0010", "train-0015", "train-0020", "train-0025", "train-0030", "train-0035", "train-0040", "train-0045"],
        )
        self.assertEqual(len(self.model.TRAINING_GEOMETRY_IDS), 39)
        self.assertIn("train-0047", self.model.TRAINING_GEOMETRY_IDS)
        self.assertNotIn("train-0035", self.model.TRAINING_GEOMETRY_IDS)


if __name__ == "__main__":
    unittest.main()
