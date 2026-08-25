from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v2/authorization_builder_recovery_v2.py"
AUTHORIZATION = ROOT / "review/asiv-matched-stellar-transport-v1/authorization-recovery-v2.json"
PARENT_MAIN = "f04c1714be998ca62954fd7704dabcdeca4f29a2"


def load_builder():
    spec = importlib.util.spec_from_file_location("recovery_v2_derivation_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecoveryV2AuthorizationDerivationTests(unittest.TestCase):
    def test_print_exact_canonical_builder_output_without_writing_authorization(self):
        self.assertFalse(AUTHORIZATION.exists())
        builder = load_builder()
        auth = builder.build_authorization(ROOT, PARENT_MAIN)
        builder.validate_authorization(ROOT, auth, PARENT_MAIN)
        self.assertFalse(AUTHORIZATION.exists())
        self.assertEqual(auth["authorizationBranch"], "authorization/asiv-matched-stellar-transport-recovery-v2")
        self.assertEqual(auth["dispatchBranch"], "dispatch/asiv-matched-stellar-transport-recovery-v2")
        self.assertEqual(auth["executionKey"], "asiv-matched-stellar-transport-recovery-v2-one-shot")
        self.assertEqual(auth["recoveryPriorRunId"], 32848973816)
        self.assertTrue(auth["recoveryPriorRunWasPreSolverFailure"])
        self.assertFalse(auth["dispatchAuthorized"])
        self.assertFalse(auth["automaticDispatch"])
        self.assertFalse(auth["consumed"])
        canonical = json.dumps(auth, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        print("MATCHED_STELLAR_RECOVERY_V2_AUTHORIZATION_DERIVATION=" + canonical)


if __name__ == "__main__":
    unittest.main()
