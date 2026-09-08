from __future__ import annotations

import copy
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1" / "verify_downloaded_artifact_zip_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_downloaded_zip_digest", SOURCE)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)

RUN_ID = 424242
ARTIFACT_ID = 515151
PAYLOAD = b"opaque github artifact zip bytes for digest binding only\n"
DIGEST = "sha256:" + hashlib.sha256(PAYLOAD).hexdigest()


def valid_envelope() -> dict:
    return {
        "schema": 1,
        "status": V.ENVELOPE_STATUS,
        "authority_comment": V.AUTHORITY_COMMENT,
        "run_id": RUN_ID,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": V.FROZEN_BRANCH,
        "execution_head": V.FROZEN_HEAD,
        "workflow_path": V.WORKFLOW_PATH,
        "artifact_id": ARTIFACT_ID,
        "artifact_name": V.ARTIFACT_NAME,
        "artifact_digest": DIGEST,
        "duplicate_e0_dispatches": 0,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


class DownloadedZipDigestTests(unittest.TestCase):
    def _write(self, root: Path, data: bytes = PAYLOAD) -> Path:
        path = root / "artifact.zip"
        path.write_bytes(data)
        return path

    def test_exact_downloaded_bytes_pass_without_content_inspection_or_authority(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td))
            result = V.verify_downloaded_zip(valid_envelope(), path)
        self.assertEqual(result["status"], V.STATUS)
        self.assertEqual(result["github_artifact_digest"], DIGEST)
        self.assertEqual(result["downloaded_zip_sha256"], DIGEST)
        self.assertEqual(result["downloaded_zip_size_bytes"], len(PAYLOAD))
        self.assertFalse(result["zip_contents_inspected"])
        self.assertFalse(result["zip_extracted"])
        self.assertFalse(result["protected_results_opened"])
        self.assertFalse(result["stage_b_authorized"])
        self.assertFalse(result["heldout_radiance_opening_authorized"])
        self.assertFalse(result["science_execution_authorized"])

    def test_digest_mismatch_fails_closed_before_any_content_verification(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td), PAYLOAD + b"tamper")
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "does not match"):
                V.verify_downloaded_zip(valid_envelope(), path)

    def test_run_envelope_surface_is_closed_and_exact(self):
        extra = valid_envelope()
        extra["future_field"] = "not allowed"
        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td))
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "unregistered keys"):
                V.verify_downloaded_zip(extra, path)

        missing = valid_envelope()
        del missing["artifact_id"]
        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td))
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "missing required keys"):
                V.verify_downloaded_zip(missing, path)

    def test_identity_attempt_and_fail_closed_flags_cannot_drift(self):
        mutations = {
            "status": "other",
            "authority_comment": V.AUTHORITY_COMMENT + 1,
            "run_attempt": 2,
            "event": "push",
            "execution_branch": "main",
            "execution_head": "0" * 40,
            "workflow_path": ".github/workflows/other.yml",
            "artifact_name": "other-artifact",
            "duplicate_e0_dispatches": 1,
            "protected_results_opened": True,
            "stage_b_authorized": True,
            "heldout_radiance_opening_authorized": True,
            "science_execution_authorized": True,
        }
        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td))
            for key, value in mutations.items():
                with self.subTest(key=key):
                    envelope = valid_envelope()
                    envelope[key] = value
                    with self.assertRaises(V.ZipDigestVerificationError):
                        V.verify_downloaded_zip(envelope, path)

    def test_ids_and_canonical_digest_must_be_well_formed(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write(Path(td))
            cases = (
                ("run_id", 0),
                ("run_id", True),
                ("artifact_id", -1),
                ("artifact_digest", hashlib.sha256(PAYLOAD).hexdigest()),
                ("artifact_digest", "sha256:" + "A" * 64),
            )
            for key, value in cases:
                with self.subTest(key=key, value=value):
                    envelope = valid_envelope()
                    envelope[key] = value
                    with self.assertRaises(V.ZipDigestVerificationError):
                        V.verify_downloaded_zip(envelope, path)

    def test_missing_empty_directory_and_symlink_inputs_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "missing.zip"
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "regular file"):
                V.verify_downloaded_zip(valid_envelope(), missing)

            empty = root / "empty.zip"
            empty.write_bytes(b"")
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "positive bytes"):
                V.verify_downloaded_zip(valid_envelope(), empty)

            directory = root / "dir.zip"
            directory.mkdir()
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "regular file"):
                V.verify_downloaded_zip(valid_envelope(), directory)

            target = self._write(root)
            link = root / "link.zip"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaisesRegex(V.ZipDigestVerificationError, "symlink"):
                V.verify_downloaded_zip(valid_envelope(), link)


if __name__ == "__main__":
    unittest.main()
