from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


execution = load("verify_execution", "verify_full_spectrum_estimator_pilot_execution_manifest_v4.py")
acquisition = load("verify_acquisition", "verify_full_spectrum_estimator_pilot_acquisition_contract_v4.py")
seed = load("verify_seed", "verify_full_spectrum_estimator_pilot_seed_collision_audit_v4.py")
identity = load("verify_identity", "verify_full_spectrum_estimator_pilot_identity_collision_audit_v4.py")


class T(unittest.TestCase):
    def test_execution_manifest_frozen_evidence(self):
        result = execution.verify(ROOT)
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["caseCount"], 44)
        self.assertEqual(result["configuredPhotonHistoriesSum"], 5_600_000_000)

    def test_acquisition_contract_frozen_evidence(self):
        result = acquisition.verify(ROOT)
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["artifactCount"], 44)

    def test_seed_audit_frozen_evidence(self):
        result = seed.verify(ROOT)
        self.assertEqual(result["status"], "PASSED_FROZEN_EVIDENCE_ONLY")
        self.assertEqual(result["historicalSeedCount"], 166)
        self.assertEqual(result["candidateSeedCount"], 44)
        self.assertEqual(result["intersectionCount"], 0)

    def test_identity_audit_is_review_time_only(self):
        result = identity.verify(ROOT)
        self.assertEqual(result["status"], "PASSED_REVIEW_TIME_ONLY_RECHECK_REQUIRED")
        self.assertEqual(result["candidateOrdinal"], 14)
        self.assertFalse(result["reserved"])
        self.assertFalse(result["authorized"])


if __name__ == "__main__":
    unittest.main()
