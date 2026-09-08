from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1" / "run_sanitized_ingest_pipeline_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_ingest_pipeline", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"
FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
WORKFLOW_PATH = ".github/workflows/arm-ena-sws-e0-oneevent-auth-runtime-v1.yml"
ARTIFACT_DIGEST = "sha256:" + "a" * 64


def envelope_receipt() -> dict:
    return {
        "schema": 1,
        "status": "ARM_E0_AUTHORIZED_RUN_ENVELOPE_VERIFIED",
        "authority_comment": 5575796491,
        "run_id": 123456,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": FROZEN_BRANCH,
        "execution_head": FROZEN_HEAD,
        "workflow_path": WORKFLOW_PATH,
        "artifact_id": 654321,
        "artifact_name": "arm-ena-sws-e0-oneevent-auth-v1",
        "artifact_digest": ARTIFACT_DIGEST,
        "duplicate_e0_dispatches": 0,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def digest_receipt() -> dict:
    envelope = envelope_receipt()
    return {
        "schema": 1,
        "status": "ARM_E0_DOWNLOADED_ARTIFACT_ZIP_DIGEST_VERIFIED",
        "authority_comment": envelope["authority_comment"],
        "run_id": envelope["run_id"],
        "run_attempt": envelope["run_attempt"],
        "event": envelope["event"],
        "execution_branch": envelope["execution_branch"],
        "execution_head": envelope["execution_head"],
        "workflow_path": envelope["workflow_path"],
        "artifact_id": envelope["artifact_id"],
        "artifact_name": envelope["artifact_name"],
        "github_artifact_digest": ARTIFACT_DIGEST,
        "downloaded_zip_size_bytes": 4,
        "downloaded_zip_sha256": ARTIFACT_DIGEST,
        "zip_contents_inspected": False,
        "zip_extracted": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def extraction_receipt() -> dict:
    digest = digest_receipt()
    return {
        "schema": 1,
        "status": "ARM_E0_SANITIZED_ARTIFACT_ZIP_SAFELY_EXTRACTED",
        "authority_comment": digest["authority_comment"],
        "run_id": digest["run_id"],
        "run_attempt": digest["run_attempt"],
        "event": digest["event"],
        "execution_branch": digest["execution_branch"],
        "execution_head": digest["execution_head"],
        "workflow_path": digest["workflow_path"],
        "artifact_id": digest["artifact_id"],
        "artifact_name": digest["artifact_name"],
        "downloaded_zip_sha256": digest["downloaded_zip_sha256"],
        "archive_member_count": 7,
        "extracted_file_names": ["dummy"] * 7,
        "zip_contents_inspected": True,
        "zip_extracted": True,
        "artifact_content_values_parsed": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def content_receipt() -> dict:
    return {
        "schema": 1,
        "status": "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED",
        "probe_case_id": "2017-06-16_dusk",
        "frozen_event_universe_sha256": "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41",
        "e0_disposition": "E0_PASS_BLIND_CANDIDATE",
        "e0_blind_candidate_pass": True,
        "sws_schema_record_count": 2,
        "source_file_count": 2,
        "query_manifest_row_count": 1,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "credentials_persisted": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "receipt_schema": 4,
    }


class SanitizedIngestPipelineTests(unittest.TestCase):
    def test_success_chains_gates_and_keeps_every_authority_false(self) -> None:
        calls: list[str] = []
        env = envelope_receipt()
        dig = digest_receipt()
        ext = extraction_receipt()
        content = content_receipt()

        def envelope_side_effect(*_args):
            calls.append("envelope")
            return env

        def digest_side_effect(*_args):
            calls.append("digest")
            return dig

        def extraction_side_effect(_digest, _zip, output_dir):
            calls.append("extraction")
            output_dir.mkdir()
            return ext

        def content_side_effect(_root):
            calls.append("content")
            return content

        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            artifact_zip = parent / "artifact.zip"
            artifact_zip.write_bytes(b"test")
            work_dir = parent / "work"
            with (
                mock.patch.object(MOD.envelope_gate, "verify_envelope", side_effect=envelope_side_effect),
                mock.patch.object(MOD.digest_gate, "verify_downloaded_zip", side_effect=digest_side_effect),
                mock.patch.object(MOD.extraction_gate, "extract_safely", side_effect=extraction_side_effect),
                mock.patch.object(MOD.content_gate, "verify_strict", side_effect=content_side_effect),
            ):
                result = MOD.run_pipeline({}, {}, {}, artifact_zip, work_dir)

            self.assertEqual(calls, ["envelope", "digest", "extraction", "content"])
            self.assertEqual(result["status"], MOD.STATUS)
            self.assertEqual(result["execution_branch"], FROZEN_BRANCH)
            self.assertEqual(result["execution_head"], FROZEN_HEAD)
            self.assertEqual(result["artifact_digest"], ARTIFACT_DIGEST)
            self.assertTrue(result["e0_blind_candidate_pass"])
            for key in (
                "network_access_performed_by_pipeline",
                "credential_values_read_by_pipeline",
                "protected_results_opened",
                "stage_b_authorized",
                "heldout_radiance_opening_authorized",
                "science_execution_authorized",
                "production_authorized",
            ):
                self.assertIs(result[key], False)
            self.assertEqual(set(result["receipt_sha256"]), {
                "01-run-envelope-receipt.json",
                "02-zip-digest-receipt.json",
                "03-safe-extraction-receipt.json",
                "04-strict-content-receipt.json",
            })
            for digest in result["receipt_sha256"].values():
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
            persisted = json.loads((work_dir / "05-pipeline-success-receipt.json").read_text())
            self.assertEqual(persisted, result)

    def test_digest_failure_never_creates_workdir_or_calls_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            artifact_zip = parent / "artifact.zip"
            artifact_zip.write_bytes(b"test")
            work_dir = parent / "work"
            with (
                mock.patch.object(MOD.envelope_gate, "verify_envelope", return_value=envelope_receipt()),
                mock.patch.object(
                    MOD.digest_gate,
                    "verify_downloaded_zip",
                    side_effect=MOD.digest_gate.ZipDigestVerificationError("digest mismatch"),
                ),
                mock.patch.object(MOD.extraction_gate, "extract_safely") as extraction,
            ):
                with self.assertRaises(MOD.digest_gate.ZipDigestVerificationError):
                    MOD.run_pipeline({}, {}, {}, artifact_zip, work_dir)
            self.assertFalse(work_dir.exists())
            extraction.assert_not_called()

    def test_existing_workdir_is_refused_before_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            artifact_zip = parent / "artifact.zip"
            artifact_zip.write_bytes(b"test")
            work_dir = parent / "work"
            work_dir.mkdir()
            with (
                mock.patch.object(MOD.envelope_gate, "verify_envelope", return_value=envelope_receipt()),
                mock.patch.object(MOD.digest_gate, "verify_downloaded_zip", return_value=digest_receipt()),
                mock.patch.object(MOD.extraction_gate, "extract_safely") as extraction,
            ):
                with self.assertRaisesRegex(MOD.PipelineVerificationError, "new, non-existent"):
                    MOD.run_pipeline({}, {}, {}, artifact_zip, work_dir)
            extraction.assert_not_called()

    def test_digest_identity_drift_is_refused_before_workdir_creation(self) -> None:
        bad_digest = digest_receipt()
        bad_digest["run_id"] += 1
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            artifact_zip = parent / "artifact.zip"
            artifact_zip.write_bytes(b"test")
            work_dir = parent / "work"
            with (
                mock.patch.object(MOD.envelope_gate, "verify_envelope", return_value=envelope_receipt()),
                mock.patch.object(MOD.digest_gate, "verify_downloaded_zip", return_value=bad_digest),
                mock.patch.object(MOD.extraction_gate, "extract_safely") as extraction,
            ):
                with self.assertRaisesRegex(MOD.PipelineVerificationError, "run_id drift"):
                    MOD.run_pipeline({}, {}, {}, artifact_zip, work_dir)
            self.assertFalse(work_dir.exists())
            extraction.assert_not_called()

    def test_content_authority_drift_blocks_final_success_receipt(self) -> None:
        content = content_receipt()
        content["stage_b_authorized"] = True
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            artifact_zip = parent / "artifact.zip"
            artifact_zip.write_bytes(b"test")
            work_dir = parent / "work"

            def extraction_side_effect(_digest, _zip, output_dir):
                output_dir.mkdir()
                return extraction_receipt()

            with (
                mock.patch.object(MOD.envelope_gate, "verify_envelope", return_value=envelope_receipt()),
                mock.patch.object(MOD.digest_gate, "verify_downloaded_zip", return_value=digest_receipt()),
                mock.patch.object(MOD.extraction_gate, "extract_safely", side_effect=extraction_side_effect),
                mock.patch.object(MOD.content_gate, "verify_strict", return_value=content),
            ):
                with self.assertRaisesRegex(MOD.PipelineVerificationError, "stage_b_authorized"):
                    MOD.run_pipeline({}, {}, {}, artifact_zip, work_dir)
            self.assertFalse((work_dir / "05-pipeline-success-receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
