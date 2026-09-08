import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.arm_stagea_package_chain_v1 import verify as v


class StageAPackageChainV1Tests(unittest.TestCase):
    REPO_LOCK = Path("tools/arm_stagea_input_lock_v1/input_lock.json")

    def test_current_component_implementation_pins_are_exact(self):
        receipt = v.verify_component_implementation_pins()
        self.assertEqual(
            receipt["continuity_verify_git_blob_sha1"],
            v.EXPECTED_CONTINUITY_IMPL_GIT_BLOB_SHA1,
        )
        self.assertEqual(
            receipt["source_binding_verify_git_blob_sha1"],
            v.EXPECTED_SOURCE_BINDING_IMPL_GIT_BLOB_SHA1,
        )

    def test_repository_input_lock_is_exact_and_fail_closed(self):
        receipt = v.verify_input_lock(self.REPO_LOCK)
        self.assertEqual(receipt["input_lock_git_blob_sha1"], v.EXPECTED_INPUT_LOCK_GIT_BLOB_SHA1)
        self.assertEqual(receipt["priority_csv_sha256"], v.continuity.EXPECTED_PRIORITY_SHA256)
        self.assertFalse(receipt["historical_extract_request_active_execution_contract"])
        self.assertTrue(receipt["protected_sasze_radiance_must_remain_sealed"])

    def test_input_lock_byte_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            drift = Path(td) / "input_lock.json"
            drift.write_bytes(self.REPO_LOCK.read_bytes() + b"\n")
            with self.assertRaises(v.PackageChainError):
                v.verify_input_lock(drift)

    def test_composite_receipt_binds_both_components_to_same_csv_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock = root / "lock.json"
            priority = root / "priority.csv"
            continuity_csv = root / "continuity.csv"
            continuity_json = root / "continuity.json"
            lock.write_text("{}", encoding="utf-8")
            priority.write_text("priority\n", encoding="utf-8")
            continuity_csv.write_text("same-continuity-bytes\n", encoding="utf-8")
            continuity_json.write_text("[]\n", encoding="utf-8")

            rows = [{"case_id": "sentinel", "stream": "hsrl"}]
            cases = {"sentinel": {}}
            case_continuity = {f"case-{i:02d}": "FAIL" for i in range(20)}
            false_boundary = {
                "scientific_pass_inferred": False,
                "missing_native_data_counts_as_pass": False,
                "protected_results_opened": False,
                "heldout_sws_sasze_radiance_opened": False,
                "heldout_radiance_opening_authorized": False,
                "stage_b_authorized": False,
                "science_execution_authorized": False,
                "production_authorized": False,
            }
            continuity_receipt = {
                "schema": 1,
                "artifact_contract_valid": True,
                "case_continuity": case_continuity,
                "case_pass_count": 0,
                "case_fail_count": 20,
                **false_boundary,
            }
            source_receipt = {
                "schema": 1,
                "source_file_binding_valid": True,
                "upstream_continuity_contract_pass_inferred": False,
                **false_boundary,
            }
            lock_receipt = {
                "input_lock_git_blob_sha1": "a" * 40,
                "priority_csv_sha256": hashlib.sha256(priority.read_bytes()).hexdigest(),
                "priority_data_row_count": 20,
                "historical_extract_request_active_execution_contract": False,
                "protected_sasze_radiance_must_remain_sealed": True,
            }

            with (
                mock.patch.object(v, "verify_component_implementation_pins", return_value={"pinned": "yes"}),
                mock.patch.object(v, "verify_input_lock", return_value=lock_receipt),
                mock.patch.object(v.continuity, "load_priority_cases", return_value=cases),
                mock.patch.object(v.continuity, "load_csv_rows", return_value=rows),
                mock.patch.object(v.continuity, "load_json_rows", return_value=[{"json": "rows"}]),
                mock.patch.object(v.continuity, "verify_json_equivalence") as eq,
                mock.patch.object(v.continuity, "verify_rows", return_value=dict(continuity_receipt)) as cv,
                mock.patch.object(v.source_binding, "verify_source_file_bindings", return_value=dict(source_receipt)) as sv,
                mock.patch.object(v.continuity, "sha256", side_effect=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()),
            ):
                receipt = v.build_package_receipt(
                    input_lock_json=lock,
                    priority_csv=priority,
                    continuity_csv=continuity_csv,
                    continuity_json=continuity_json,
                )

            eq.assert_called_once()
            cv.assert_called_once_with(rows, cases)
            sv.assert_called_once_with(rows)
            expected_csv_sha = hashlib.sha256(continuity_csv.read_bytes()).hexdigest()
            self.assertEqual(receipt["inputs"]["continuity_csv_sha256"], expected_csv_sha)
            self.assertTrue(receipt["same_continuity_csv_bound_across_components"])
            self.assertTrue(receipt["stagea_timing_package_contract_valid"])
            self.assertEqual(receipt["case_fail_count"], 20)
            self.assertFalse(receipt["scientific_pass_inferred"])
            self.assertFalse(receipt["heldout_sws_sasze_radiance_opened"])
            self.assertFalse(receipt["stage_b_authorized"])

    def test_source_binding_failure_prevents_package_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            paths = [root / name for name in ("lock.json", "priority.csv", "continuity.csv", "continuity.json")]
            for path in paths:
                path.write_text("x", encoding="utf-8")
            lock, priority, continuity_csv, continuity_json = paths
            lock_receipt = {
                "input_lock_git_blob_sha1": "a" * 40,
                "priority_csv_sha256": hashlib.sha256(priority.read_bytes()).hexdigest(),
                "priority_data_row_count": 20,
                "historical_extract_request_active_execution_contract": False,
                "protected_sasze_radiance_must_remain_sealed": True,
            }
            cont_receipt = {
                "artifact_contract_valid": True,
                "case_continuity": {f"case-{i:02d}": "FAIL" for i in range(20)},
                "case_pass_count": 0,
                "case_fail_count": 20,
                "scientific_pass_inferred": False,
                "missing_native_data_counts_as_pass": False,
                "protected_results_opened": False,
                "heldout_sws_sasze_radiance_opened": False,
                "heldout_radiance_opening_authorized": False,
                "stage_b_authorized": False,
                "science_execution_authorized": False,
                "production_authorized": False,
            }
            with (
                mock.patch.object(v, "verify_component_implementation_pins", return_value={}),
                mock.patch.object(v, "verify_input_lock", return_value=lock_receipt),
                mock.patch.object(v.continuity, "load_priority_cases", return_value={}),
                mock.patch.object(v.continuity, "load_csv_rows", return_value=[]),
                mock.patch.object(v.continuity, "load_json_rows", return_value=[]),
                mock.patch.object(v.continuity, "verify_json_equivalence"),
                mock.patch.object(v.continuity, "verify_rows", return_value=cont_receipt),
                mock.patch.object(v.continuity, "sha256", side_effect=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()),
                mock.patch.object(
                    v.source_binding,
                    "verify_source_file_bindings",
                    side_effect=v.source_binding.SourceBindingError("wrong datastream"),
                ),
            ):
                with self.assertRaises(v.source_binding.SourceBindingError):
                    v.build_package_receipt(
                        input_lock_json=lock,
                        priority_csv=priority,
                        continuity_csv=continuity_csv,
                        continuity_json=continuity_json,
                    )


if __name__ == "__main__":
    unittest.main()
