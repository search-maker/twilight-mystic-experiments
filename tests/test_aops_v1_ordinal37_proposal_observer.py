from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MAIN_SHA = "139c070aebd7cf9ebee4282a4b0995eb3fe418b4"
PROOF = ROOT / "tests/fixtures/aops-v1-seed-authorization-proof-main-139c070.json"
BUILDER = ROOT / "experiments/aerosol-optical-property-sensitivity-v1/execution-candidate/build_authorization.py"
EXPECTED_PROOF_SHA256 = "f7605a204bc434bee1d86aa2b797770fa85aa80840c80f29e5ee94107ffb3ef5"


def load_builder():
    spec = importlib.util.spec_from_file_location("aops_v1_ordinal37_observer_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AopsV1Ordinal37ProposalObserverTest(unittest.TestCase):
    def test_exact_main_ordinal37_proposal_without_allocation(self) -> None:
        self.assertEqual(hashlib.sha256(PROOF.read_bytes()).hexdigest(), EXPECTED_PROOF_SHA256)
        builder = load_builder()
        doc = builder.build(ROOT, PROOF, MAIN_SHA, 37)
        self.assertEqual(doc["status"], "AUTHORIZED_PENDING_SEPARATE_DISPATCH")
        self.assertEqual(doc["scientificOrdinal"], 37)
        self.assertEqual(doc["executionKey"], "aerosol-optical-property-sensitivity-v1:numerical:37")
        self.assertEqual(doc["authorizationBranch"], "authorization/aerosol-optical-property-sensitivity-v1-ordinal-37")
        self.assertEqual(doc["dispatchBranch"], "dispatch/aerosol-optical-property-sensitivity-v1-ordinal-37")
        self.assertEqual(doc["exactAuthorizationParentCommit"], MAIN_SHA)
        self.assertEqual(doc["reviewPackageMainSha"], MAIN_SHA)
        self.assertIsNone(doc["exactAuthorizationCommit"])
        self.assertFalse(doc["dispatchAuthorized"])
        self.assertFalse(doc["resultOpeningAuthorized"])
        self.assertFalse(doc["automaticDispatch"])
        self.assertFalse(doc["consumed"])
        self.assertFalse(doc["githubRerunAllowed"])
        self.assertFalse(doc["retryAllowed"])
        self.assertFalse(doc["resumeAllowed"])
        payload = json.dumps(doc, indent=2, sort_keys=True) + "\n"
        payload_bytes = payload.encode()
        print("AOPS37_PROPOSAL_SHA256=" + hashlib.sha256(payload_bytes).hexdigest())
        print("AOPS37_PROPOSAL_JSON_B64=" + base64.b64encode(payload_bytes).decode())


if __name__ == "__main__":
    unittest.main()
