import importlib.util
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
SPEC = importlib.util.spec_from_file_location("pgn_metadata_only_client_v1", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


FAKE_OPENAPI = {
    "openapi": "3.1.0",
    "paths": {
        "/v1/calibrationfiles": {
            "get": {
                "parameters": [
                    {"name": "instrument", "in": "query", "required": True, "schema": {"type": "integer"}},
                    {"name": "spectrometer", "in": "query", "required": False, "schema": {"type": "integer"}},
                ]
            }
        },
        "/v1/operationfiles": {
            "get": {
                "parameters": [
                    {"name": "instrument", "in": "query", "required": True, "schema": {"type": "integer"}},
                ]
            }
        },
        "/v1/metadata": {
            "get": {
                "parameters": [
                    {"name": "file", "in": "query", "required": True, "schema": {"type": "string"}},
                ]
            }
        },
        "/v1/files": {
            "get": {
                "parameters": [
                    {"name": "location", "in": "query", "required": False, "schema": {"type": "string"}},
                ]
            }
        },
        "/v1/download": {"get": {"parameters": []}},
    },
}


class PgnMetadataOnlyClientTests(unittest.TestCase):
    def test_download_endpoint_is_always_forbidden(self):
        with self.assertRaises(module.MetadataOnlyViolation):
            module.assert_metadata_only_path("/v1/download")
        with self.assertRaises(module.MetadataOnlyViolation):
            module.assert_metadata_only_path("/v1/download/file.txt")

    def test_unknown_endpoint_is_forbidden(self):
        with self.assertRaises(module.MetadataOnlyViolation):
            module.assert_metadata_only_path("/v1/secret-data")

    def test_live_contract_drives_query_parameter_names(self):
        names = module.query_parameter_names(FAKE_OPENAPI, "/v1/calibrationfiles")
        self.assertEqual(names, frozenset({"instrument", "spectrometer"}))

    def test_query_cannot_guess_parameter_not_in_openapi(self):
        with self.assertRaises(module.MetadataOnlyViolation):
            module.validate_query_against_openapi(
                FAKE_OPENAPI,
                "/v1/calibrationfiles",
                {"panid": 209},
            )

    def test_required_parameter_must_be_present(self):
        with self.assertRaises(module.MetadataOnlyViolation):
            module.validate_query_against_openapi(
                FAKE_OPENAPI,
                "/v1/calibrationfiles",
                {"spectrometer": 2},
            )

    def test_metadata_url_is_built_only_after_contract_validation(self):
        url = module.build_metadata_url(
            FAKE_OPENAPI,
            "/v1/calibrationfiles",
            {"instrument": 209, "spectrometer": 2},
        )
        self.assertEqual(
            url,
            "https://api.pandonia-global-network.org/v1/calibrationfiles?instrument=209&spectrometer=2",
        )

    def test_exact_openapi_key_is_preserved_when_normalization_removes_trailing_slash(self):
        spec = {
            "paths": {
                "/v1/calibrationfiles/": {
                    "get": {
                        "parameters": [
                            {"name": "instrument", "in": "query", "required": True, "schema": {"type": "integer"}}
                        ]
                    }
                }
            }
        }
        self.assertEqual(module.discover_metadata_paths(spec), ("/v1/calibrationfiles/",))
        self.assertEqual(
            module.query_parameter_names(spec, "/v1/calibrationfiles/"),
            frozenset({"instrument"}),
        )
        # A normalized caller is safe only because the mapping is unique.
        self.assertEqual(
            module.query_parameter_names(spec, "/v1/calibrationfiles"),
            frozenset({"instrument"}),
        )

    def test_unresolved_parameter_refs_fail_closed(self):
        spec = {
            "paths": {
                "/v1/metadata": {
                    "get": {"parameters": [{"$ref": "#/components/parameters/File"}]}
                }
            }
        }
        with self.assertRaises(RuntimeError):
            module.endpoint_parameters(spec, "/v1/metadata")

    def test_contract_description_never_includes_download(self):
        described = module.describe_contract(FAKE_OPENAPI)
        self.assertNotIn("/v1/download", described)
        self.assertEqual(
            set(described),
            {
                "/v1/calibrationfiles",
                "/v1/files",
                "/v1/metadata",
                "/v1/operationfiles",
            },
        )


if __name__ == "__main__":
    unittest.main()
