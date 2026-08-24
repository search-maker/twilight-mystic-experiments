import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "review"
    / "empirical-twilight-radiance-source-admission-v1"
    / "pgn_metadata_only_client_v1.py"
)
SPEC = importlib.util.spec_from_file_location("pgn_metadata_only_client_live_v1", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


@unittest.skipUnless(
    os.environ.get("CI", "").lower() == "true",
    "live PGN OpenAPI discovery is CI-only; ordinary local unit runs remain offline",
)
class PgnLiveOpenapiMetadataContractTests(unittest.TestCase):
    def test_live_openapi_exposes_only_described_metadata_contract(self):
        openapi = module.fetch_openapi(timeout_s=20.0)
        described = module.describe_contract(openapi)
        print("PGN_METADATA_OPENAPI_CONTRACT_BEGIN")
        print(json.dumps(described, indent=2, sort_keys=True))
        print("PGN_METADATA_OPENAPI_CONTRACT_END")

        prefixes_seen = set()
        for path in described:
            self.assertFalse(path == "/v1/download" or path.startswith("/v1/download/"))
            matching = [
                prefix
                for prefix in module.ALLOWED_PATH_PREFIXES
                if path == prefix or path.startswith(prefix + "/")
            ]
            self.assertEqual(len(matching), 1, path)
            prefixes_seen.add(matching[0])
        self.assertEqual(prefixes_seen, set(module.ALLOWED_PATH_PREFIXES))

        with self.assertRaises(module.MetadataOnlyViolation):
            module.assert_metadata_only_path("/v1/download")


if __name__ == "__main__":
    unittest.main()
