"""Refusal tests for the closed sanitized one-event E0 artifact universe."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1"

base_spec = importlib.util.spec_from_file_location(
    "arm_e0_fixture_tests_strict", TOOLS / "test_verify_oneevent_e0_artifact_v1.py"
)
assert base_spec is not None and base_spec.loader is not None
fixture_module = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(fixture_module)

strict_spec = importlib.util.spec_from_file_location(
    "arm_e0_strict", TOOLS / "verify_oneevent_e0_artifact_strict_v1.py"
)
assert strict_spec is not None and strict_spec.loader is not None
strict = importlib.util.module_from_spec(strict_spec)
strict_spec.loader.exec_module(strict)


class StrictClosedArtifactTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.original_strict_hash = strict.base.FROZEN_UNIVERSE_SHA256
        self.original_fixture_hash = fixture_module.V.FROZEN_UNIVERSE_SHA256
        self.fx = fixture_module.ArtifactFixture(self.root)
        strict.base.FROZEN_UNIVERSE_SHA256 = self.fx.fixture_universe_sha
        fixture_module.V.FROZEN_UNIVERSE_SHA256 = self.fx.fixture_universe_sha
        self.fx.refresh_receipt()

    def tearDown(self):
        strict.base.FROZEN_UNIVERSE_SHA256 = self.original_strict_hash
        fixture_module.V.FROZEN_UNIVERSE_SHA256 = self.original_fixture_hash
        self.td.cleanup()

    def test_strict_clean_fixture_passes(self):
        result = strict.verify_strict(self.root)
        self.assertEqual(result["status"], "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED")
        self.assertFalse(result["stage_b_authorized"])
        self.assertFalse(result["heldout_radiance_opening_authorized"])

    def test_strict_refuses_unexpected_text_file(self):
        (self.root / "unexpected-notes.txt").write_text("unexpected payload\n", encoding="utf-8")
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("unexpected=['unexpected-notes.txt']", str(ctx.exception))

    def test_strict_refuses_broken_symlink(self):
        (self.root / "broken-link").symlink_to(self.root / "does-not-exist")
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("symlink is forbidden", str(ctx.exception))

    def test_strict_refuses_unexpected_directory(self):
        (self.root / "unexpected-dir").mkdir()
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("unexpected directory", str(ctx.exception))

    def test_strict_refuses_unregistered_receipt_key(self):
        path = self.root / "probe_receipt.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["protected_radiance"] = 1.23
        path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("receipt has unregistered keys", str(ctx.exception))

    def test_strict_refuses_unregistered_ledger_key(self):
        path = self.root / "ena_sws_e0_stream_ledger.jsonl"
        row = strict.base.read_jsonl(path)[0]
        row["radiance"] = 1.23
        fixture_module.write_jsonl(path, [row])
        self.fx.refresh_receipt()
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("ledger row 1 has unregistered keys", str(ctx.exception))

    def test_strict_refuses_unregistered_aux_schema_variable_key(self):
        path = self.root / "ena_sws_e0_stream_schema.jsonl"
        rows = strict.base.read_jsonl(path)
        aux = dict(rows[0])
        aux["kind"] = "swsaux"
        aux["source_file"] = "enaswsauxC1.b1.20170616.000000.cdf"
        aux["source_sha256"] = "4" * 64
        aux["variables"] = [dict(rows[0]["variables"][0])]
        aux["variables"][0]["values"] = [1, 2, 3]
        fixture_module.write_jsonl(path, rows + [aux])
        self.fx.refresh_receipt()
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("schema row 2 variable 1 has unregistered keys", str(ctx.exception))

    def test_strict_refuses_query_provenance_filename_mismatch(self):
        path = self.root / "ena_sws_e0_query_manifest.jsonl"
        row = strict.base.read_jsonl(path)[0]
        row["filenames"] = ["enaswsC1.b1.20170616.other.cdf"]
        fixture_module.write_jsonl(path, [row])
        self.fx.refresh_receipt()
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("query-manifest filename set does not exactly match provenance sources", str(ctx.exception))

    def test_strict_refuses_extra_summary_disposition(self):
        path = self.root / "ena_sws_e0_stream_summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))
        summary["disposition_counts"]["UNREGISTERED"] = "ignored-by-base"
        path.write_text(json.dumps(summary), encoding="utf-8")
        self.fx.refresh_receipt()
        with self.assertRaises(strict.StrictVerificationError) as ctx:
            strict.verify_strict(self.root)
        self.assertIn("summary disposition_counts must be exactly", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
