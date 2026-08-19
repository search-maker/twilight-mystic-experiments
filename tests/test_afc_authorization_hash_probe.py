from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = {
    "manifestRawSha256": "evidence/aerosol-family-challenge-v2/manifest.frozen.json",
    "freezeRecordRawSha256": "evidence/aerosol-family-challenge-v2/freeze-record.json",
    "transportContractRawSha256": "experiments/aerosol-family-challenge-v2/execution-candidate/transport-contract.v3.json",
    "adapterRawSha256": "experiments/aerosol-family-challenge-v2/adapter.py",
    "executorRawSha256": "experiments/aerosol-family-challenge-v2/execution-candidate/executor.py",
    "workflowRawSha256": ".github/workflows/aerosol-family-v2-execution.yml",
    "authorizationGuardRawSha256": "experiments/aerosol-family-challenge-v2/execution-candidate/authorization_guard.py",
    "dispatchGuardRawSha256": "experiments/aerosol-family-challenge-v2/execution-candidate/dispatch_guard.py",
    "freshnessGuardRawSha256": "experiments/aerosol-family-challenge-v2/execution-candidate/freshness.py",
    "authorizationReviewWorkflowRawSha256": ".github/workflows/aerosol-family-v2-authorization-review.yml",
}


class AuthorizationHashProbe(unittest.TestCase):
    def test_print_exact_raw_sha256_bindings(self):
        print("AFC_AUTH_HASH_PROBE_BEGIN")
        for field, rel in PATHS.items():
            path = ROOT / rel
            self.assertTrue(path.is_file(), rel)
            print(f"AFC_AUTH_HASH {field}={hashlib.sha256(path.read_bytes()).hexdigest()}")
        print("AFC_AUTH_HASH_PROBE_END")


if __name__ == "__main__":
    unittest.main()
