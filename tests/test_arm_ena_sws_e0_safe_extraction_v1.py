from __future__ import annotations

import hashlib
import importlib.util
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1" / "extract_sanitized_artifact_zip_v1.py"
SPEC = importlib.util.spec_from_file_location("arm_e0_safe_extract", SOURCE)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)

RUN_ID = 424242
ARTIFACT_ID = 515151


def make_zip(path: Path, *, members: dict[str, bytes] | None = None) -> tuple[int, str]:
    if members is None:
        members = {name: (f"sanitized fixture {name}\n").encode() for name in V.REQUIRED_FILES}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    data = path.read_bytes()
    return len(data), "sha256:" + hashlib.sha256(data).hexdigest()


def digest_receipt(size: int, digest: str) -> dict:
    return {
        "schema": 1,
        "status": V.DIGEST_STATUS,
        "authority_comment": V.AUTHORITY_COMMENT,
        "run_id": RUN_ID,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": V.FROZEN_BRANCH,
        "execution_head": V.FROZEN_HEAD,
        "workflow_path": V.WORKFLOW_PATH,
        "artifact_id": ARTIFACT_ID,
        "artifact_name": V.ARTIFACT_NAME,
        "github_artifact_digest": digest,
        "downloaded_zip_size_bytes": size,
        "downloaded_zip_sha256": digest,
        "zip_contents_inspected": False,
        "zip_extracted": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


class SafeExtractionTests(unittest.TestCase):
    def test_exact_closed_zip_extracts_without_parsing_values_or_authorizing_science(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive_path = root / "artifact.zip"
            size, digest = make_zip(archive_path)
            output = root / "out"
            result = V.extract_safely(digest_receipt(size, digest), archive_path, output)
            self.assertEqual(set(path.name for path in output.iterdir()), V.REQUIRED_FILES)
        self.assertEqual(result["status"], V.STATUS)
        self.assertTrue(result["zip_contents_inspected"])
        self.assertTrue(result["zip_extracted"])
        self.assertFalse(result["artifact_content_values_parsed"])
        self.assertFalse(result["protected_results_opened"])
        self.assertFalse(result["stage_b_authorized"])
        self.assertFalse(result["heldout_radiance_opening_authorized"])
        self.assertFalse(result["science_execution_authorized"])

    def test_archive_substitution_after_digest_gate_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive_path = root / "artifact.zip"
            size, digest = make_zip(archive_path)
            receipt = digest_receipt(size, digest)
            archive_path.write_bytes(archive_path.read_bytes() + b"tamper")
            with self.assertRaisesRegex(V.SafeExtractionError, "changed after"):
                V.extract_safely(receipt, archive_path, root / "out")

    def test_closed_receipt_surface_and_fail_closed_flags_are_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive_path = root / "artifact.zip"
            size, digest = make_zip(archive_path)
            base = digest_receipt(size, digest)
            cases = {
                "status": "other",
                "authority_comment": V.AUTHORITY_COMMENT + 1,
                "run_attempt": 2,
                "event": "push",
                "execution_branch": "main",
                "execution_head": "0" * 40,
                "workflow_path": ".github/workflows/other.yml",
                "artifact_name": "other",
                "zip_contents_inspected": True,
                "zip_extracted": True,
                "protected_results_opened": True,
                "stage_b_authorized": True,
                "heldout_radiance_opening_authorized": True,
                "science_execution_authorized": True,
            }
            for key, value in cases.items():
                with self.subTest(key=key):
                    receipt = dict(base)
                    receipt[key] = value
                    with self.assertRaises(V.SafeExtractionError):
                        V.extract_safely(receipt, archive_path, root / f"out-{key}")

            extra = dict(base)
            extra["unexpected"] = False
            with self.assertRaisesRegex(V.SafeExtractionError, "unregistered"):
                V.extract_safely(extra, archive_path, root / "out-extra")

    def test_missing_extra_nested_and_duplicate_members_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            base_members = {name: b"x\n" for name in V.REQUIRED_FILES}

            missing_members = dict(base_members)
            missing_members.pop(next(iter(V.REQUIRED_FILES)))
            missing = root / "missing.zip"
            size, digest = make_zip(missing, members=missing_members)
            with self.assertRaises(V.SafeExtractionError):
                V.extract_safely(digest_receipt(size, digest), missing, root / "out-missing")

            extra_members = dict(base_members)
            extra_members["unexpected.txt"] = b"x"
            extra = root / "extra.zip"
            size, digest = make_zip(extra, members=extra_members)
            with self.assertRaises(V.SafeExtractionError):
                V.extract_safely(digest_receipt(size, digest), extra, root / "out-extra")

            nested_members = dict(base_members)
            victim = next(iter(V.REQUIRED_FILES))
            payload = nested_members.pop(victim)
            nested_members[f"nested/{victim}"] = payload
            nested = root / "nested.zip"
            size, digest = make_zip(nested, members=nested_members)
            with self.assertRaises(V.SafeExtractionError):
                V.extract_safely(digest_receipt(size, digest), nested, root / "out-nested")

            duplicate = root / "duplicate.zip"
            with zipfile.ZipFile(duplicate, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, payload in base_members.items():
                    archive.writestr(name, payload)
                archive.writestr(next(iter(V.REQUIRED_FILES)), b"duplicate")
            data = duplicate.read_bytes()
            receipt = digest_receipt(len(data), "sha256:" + hashlib.sha256(data).hexdigest())
            with self.assertRaises(V.SafeExtractionError):
                V.extract_safely(receipt, duplicate, root / "out-duplicate")

    def test_symlink_member_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive_path = root / "symlink.zip"
            victim = next(iter(V.REQUIRED_FILES))
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name in V.REQUIRED_FILES:
                    if name == victim:
                        info = zipfile.ZipInfo(name)
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(info, b"target")
                    else:
                        archive.writestr(name, b"x\n")
            data = archive_path.read_bytes()
            receipt = digest_receipt(len(data), "sha256:" + hashlib.sha256(data).hexdigest())
            with self.assertRaisesRegex(V.SafeExtractionError, "non-regular"):
                V.extract_safely(receipt, archive_path, root / "out")

    def test_uncompressed_size_bounds_and_preexisting_output_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive_path = root / "artifact.zip"
            size, digest = make_zip(archive_path)
            output = root / "out"
            output.mkdir()
            with self.assertRaisesRegex(V.SafeExtractionError, "new, non-existent"):
                V.extract_safely(digest_receipt(size, digest), archive_path, output)

            old_limit = V.MAX_FILE_BYTES
            try:
                V.MAX_FILE_BYTES = 4
                with self.assertRaisesRegex(V.SafeExtractionError, "bounded uncompressed size"):
                    V.extract_safely(digest_receipt(size, digest), archive_path, root / "out-size")
            finally:
                V.MAX_FILE_BYTES = old_limit


if __name__ == "__main__":
    unittest.main()
