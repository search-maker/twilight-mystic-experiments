import hashlib
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = ROOT / "tools" / "arm_ena_sws_e0_postartifact_v1"
sys.path.insert(0, str(TOOL_DIR))
spec = importlib.util.spec_from_file_location("bundle", TOOL_DIR / "verify_downloaded_e0_bundle_v1.py")
bundle = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bundle)


def envelope(digest):
    return {
        "schema": 1,
        "status": bundle.ENVELOPE_STATUS,
        "authority_comment": bundle.AUTHORITY_COMMENT,
        "run_id": 123,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": bundle.FROZEN_BRANCH,
        "execution_head": bundle.FROZEN_HEAD,
        "workflow_path": bundle.WORKFLOW_PATH,
        "artifact_id": 456,
        "artifact_name": bundle.ARTIFACT_NAME,
        "artifact_digest": digest,
        "duplicate_e0_dispatches": 0,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def make_zip(path, names=None):
    names = names or sorted(bundle.REQUIRED_FILES)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.writestr(name, "{}\n")
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def safe_content(_root):
    return {
        "status": "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED",
        "e0_disposition": "E0_PASS_BLIND_CANDIDATE",
        "e0_blind_candidate_pass": True,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
    }


class DownloadedBundleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def assert_refused(self, func, contains):
        with self.assertRaises(bundle.BundleVerificationError) as ctx:
            func()
        self.assertIn(contains, str(ctx.exception))

    def test_accepts_exact_digest_and_exact_sanitized_file_set(self):
        path = self.root / "artifact.zip"
        digest = make_zip(path)
        result = bundle.verify_bundle(path, envelope(digest), artifact_verifier=safe_content)
        self.assertEqual(result["status"], "ARM_E0_DOWNLOADED_ZIP_AND_SANITIZED_CONTENT_VERIFIED")
        self.assertEqual(result["artifact_digest"], digest)
        self.assertFalse(result["stage_b_authorized"])
        self.assertFalse(result["science_execution_authorized"])

    def test_refuses_digest_mismatch(self):
        path = self.root / "artifact.zip"
        make_zip(path)
        bad = "sha256:" + "0" * 64
        self.assert_refused(
            lambda: bundle.verify_bundle(path, envelope(bad), artifact_verifier=safe_content),
            "SHA-256",
        )

    def test_refuses_path_traversal_even_when_digest_matches(self):
        path = self.root / "artifact.zip"
        names = sorted(bundle.REQUIRED_FILES - {"probe_receipt.json"}) + ["../probe_receipt.json"]
        digest = make_zip(path, names)
        self.assert_refused(
            lambda: bundle.verify_bundle(path, envelope(digest), artifact_verifier=safe_content),
            "unsafe ZIP member path",
        )

    def test_refuses_extra_file(self):
        path = self.root / "artifact.zip"
        digest = make_zip(path, sorted(bundle.REQUIRED_FILES) + ["extra.txt"])
        self.assert_refused(
            lambda: bundle.verify_bundle(path, envelope(digest), artifact_verifier=safe_content),
            "file set mismatch",
        )

    def test_refuses_case_collision(self):
        path = self.root / "artifact.zip"
        names = sorted(bundle.REQUIRED_FILES) + ["PROBE_RECEIPT.JSON"]
        digest = make_zip(path, names)
        self.assert_refused(
            lambda: bundle.verify_bundle(path, envelope(digest), artifact_verifier=safe_content),
            "case-colliding",
        )

    def test_refuses_wrong_frozen_head_before_opening_zip(self):
        path = self.root / "artifact.zip"
        digest = make_zip(path)
        receipt = envelope(digest)
        receipt["execution_head"] = "0" * 40
        self.assert_refused(
            lambda: bundle.verify_bundle(path, receipt, artifact_verifier=safe_content),
            "execution_head mismatch",
        )

    def test_refuses_symlink_member(self):
        path = self.root / "artifact.zip"
        with zipfile.ZipFile(path, "w") as zf:
            for name in sorted(bundle.REQUIRED_FILES - {"probe_receipt.json"}):
                zf.writestr(name, "{}\n")
            info = zipfile.ZipInfo("probe_receipt.json")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            zf.writestr(info, "target")
        digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        self.assert_refused(
            lambda: bundle.verify_bundle(path, envelope(digest), artifact_verifier=safe_content),
            "non-regular",
        )

    def test_wraps_existing_content_verifier_refusal(self):
        path = self.root / "artifact.zip"
        digest = make_zip(path)

        def refuse(_root):
            raise bundle.ArtifactVerificationError("unsafe sanitized content")

        self.assert_refused(
            lambda: bundle.verify_bundle(path, envelope(digest), artifact_verifier=refuse),
            "sanitized content verifier refused",
        )


if __name__ == "__main__":
    unittest.main()
