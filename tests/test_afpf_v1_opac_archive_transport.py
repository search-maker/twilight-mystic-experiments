from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/afpf-v1-execution.yml"
ARCHIVE_SHA256 = "11daa1f1f4be0fd4ddf7e881ec2005498049674a1540d37b4b1e8f5e16052c7e"
ARCHIVE_SIZE = "743391266"
SOURCE_URL = "https://www.libradtran.org/lib/exe/fetch.php?media=download%3Aoptprop_v2.1.tar.gz"


class AfpfOpacArchiveTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text()
        cls.preflight, cls.case_surface = cls.text.split("steps: &case_steps", 1)

    def test_official_source_is_acquired_once_before_case_matrix(self):
        self.assertEqual(self.text.count(SOURCE_URL), 1)
        self.assertIn(SOURCE_URL, self.preflight)
        self.assertEqual(self.text.count("curl --location"), 1)
        self.assertNotIn("curl --location", self.case_surface)

    def test_same_run_preflight_artifact_carries_exact_archive(self):
        expected_path = "execution-preflight/optprop_v2.1.tar.gz"
        case_path = "preflight/execution-preflight/optprop_v2.1.tar.gz"
        self.assertIn(expected_path, self.preflight)
        self.assertIn(case_path, self.case_surface)
        self.assertIn(ARCHIVE_SHA256, self.preflight)
        self.assertIn(ARCHIVE_SHA256, self.case_surface)
        self.assertIn(ARCHIVE_SIZE, self.preflight)
        self.assertIn(ARCHIVE_SIZE, self.case_surface)

    def test_case_jobs_reconstruct_overlay_from_preflight_bytes(self):
        self.assertIn("stage_frozen_overlay(base,archive,Path('libradtran-overlay'))", self.case_surface)
        self.assertIn("FROZEN_OPAC_RUNTIME_OVERLAY_STAGED", self.case_surface)
        self.assertIn("5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80", self.case_surface)


if __name__ == "__main__":
    unittest.main()
