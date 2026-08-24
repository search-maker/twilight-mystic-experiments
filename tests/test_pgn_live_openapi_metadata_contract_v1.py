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

        self.assertEqual(
            set(described),
            {
                "/v1/calibrationfiles",
                "/v1/files",
                "/v1/metadata",
                "/v1/operationfiles",
            },
        )
        for path in described:
            self.assertNotEqual(path, "/v1/download")
        with self.assertRaises(module.MetadataOnlyViolation):
            module.assert_metadata_only_path("/v1/download")


if __name__ == "__main__":
    unittest.main()
