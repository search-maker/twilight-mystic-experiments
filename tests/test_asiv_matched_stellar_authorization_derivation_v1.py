from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "review/asiv-matched-stellar-transport-v1/science-control/authorization_builder_review.py"
PARENT_MAIN = "04f83beff361a001892fd14150a189dd80fe37ed"
AUTHORIZATION = ROOT / "review/asiv-matched-stellar-transport-v1/authorization.json"


class AsivMatchedStellarAuthorizationDerivationV1Tests(unittest.TestCase):
    def test_print_exact_in_memory_authorization_without_creating_file(self):
        self.assertFalse(AUTHORIZATION.exists())
        spec = importlib.util.spec_from_file_location("matched_stellar_authorization_derivation_builder", BUILDER)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        auth = mod.build_authorization(ROOT, PARENT_MAIN)
        mod.validate_authorization(ROOT, auth, PARENT_MAIN)
        self.assertFalse(AUTHORIZATION.exists())
        self.assertEqual(auth["exactAuthorizationParentCommit"], PARENT_MAIN)
        self.assertFalse(auth["dispatchAuthorized"])
        self.assertFalse(auth["automaticDispatch"])
        self.assertFalse(auth["consumed"])
        self.assertFalse(auth["pandoraHoldoutAccessAllowed"])
        print("MATCHED_STELLAR_AUTHORIZATION_DERIVATION=" + json.dumps(auth, sort_keys=True, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    unittest.main()
