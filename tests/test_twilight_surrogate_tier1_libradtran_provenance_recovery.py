from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "experiments"
    / "mystic-batch-v1"
    / "twilight_surrogate_tier1_libradtran_provenance_recovery.py"
)
spec = importlib.util.spec_from_file_location("tier1_provenance_recovery", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {MODULE_PATH}")
MOD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MOD)


class ProvenanceRecoveryTests(unittest.TestCase):
    def test_feedstock_binding_keeps_original_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "meta.yaml"
            path.write_text(
                '{% set version = "2.0.6" %}\n'
                'url: http://www.libradtran.org/download/'
                'libRadtran-{{ version }}.tar.gz\n'
                f'sha256: {MOD.EXPECTED_SOURCE_SHA256}\n',
                encoding="utf-8",
            )
            original = MOD.FEEDSTOCK_RECIPE_BLOB_SHA
            try:
                MOD.FEEDSTOCK_RECIPE_BLOB_SHA = MOD.git_blob_sha1(path)
                evidence = MOD.validate_feedstock(path)
            finally:
                MOD.FEEDSTOCK_RECIPE_BLOB_SHA = original
            self.assertEqual(evidence["sourceSha256"], MOD.EXPECTED_SOURCE_SHA256)
            self.assertNotEqual(
                MOD.EXPECTED_SOURCE_SHA256,
                MOD.CURRENT_OFFICIAL_OBSERVED_SHA256,
            )

    def test_wayback_rows_are_deduplicated_and_sorted(self) -> None:
        rows = [
            {"timestamp": "20240101000000", "digest": "B", "length": "20"},
            {"timestamp": "20180101000000", "digest": "A", "length": "10"},
            {"timestamp": "20190101000000", "digest": "A", "length": "10"},
        ]
        selected = MOD.select_wayback_rows(rows)
        self.assertEqual(
            [row["timestamp"] for row in selected],
            ["20180101000000", "20240101000000"],
        )

    def test_exact_source_is_required_for_green_gate(self) -> None:
        self.assertEqual(
            MOD.classify_decision(True, False, False),
            (
                "PACKAGE_PROVENANCE_BOUND_EXACT_HISTORICAL_SOURCE_NOT_RECOVERED",
                False,
            ),
        )
        self.assertEqual(
            MOD.classify_decision(True, True, True),
            (
                "EXACT_HISTORICAL_SOURCE_RECOVERED_PACKAGE_PROVENANCE_BOUND",
                True,
            ),
        )
        self.assertEqual(
            MOD.classify_decision(False, True, True),
            ("PACKAGE_PROVENANCE_FAILED", False),
        )

    def test_governance_boundary_always_refuses_scientific_actions(self) -> None:
        boundary = MOD.governance_boundary()
        self.assertFalse(boundary["scientificExecution"])
        self.assertFalse(boundary["scientificDatasetProduced"])
        self.assertEqual(boundary["solverExecutionCount"], 0)
        self.assertFalse(boundary["authorizationPermitted"])
        self.assertFalse(boundary["ordinal2ScientificDispatchPermitted"])
        self.assertFalse(boundary["githubRerunPermitted"])
        self.assertFalse(boundary["sourceHashChangePermitted"])

    def test_static_candidates_do_not_replace_expected_hash(self) -> None:
        candidates = MOD.static_candidates()
        self.assertTrue(any(row["kind"].startswith("feedstock") for row in candidates))
        self.assertEqual(
            MOD.EXPECTED_SOURCE_SHA256,
            "999e47f4af4b5df6f85a6887fc105fc8f6e1a7cee89a3124f69ac8d8912c8e85",
        )


if __name__ == "__main__":
    unittest.main()
