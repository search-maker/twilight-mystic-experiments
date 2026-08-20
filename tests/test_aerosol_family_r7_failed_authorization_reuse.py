from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "experiments/aerosol-family-challenge-v2-r7/execution-candidate"
AUTH_BRANCH = "authorization/aerosol-family-challenge-v2-r7-ordinal-31"
AUTH_HEAD = "b" * 40


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class FailedAuthorizationReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freshness = load_module("afc2_r7_failed_reuse_freshness", CANDIDATE / "freshness.py")
        sys.modules["freshness"] = cls.freshness
        cls.surface = load_module("afc2_r7_failed_reuse_surface", CANDIDATE / "authorization_surface.py")

    def payload(self):
        return {
            "branches": [
                {"name": "main", "commit": {"sha": "a" * 40}},
                {"name": AUTH_BRANCH, "commit": {"sha": AUTH_HEAD}},
                {"name": "dispatch/aerosol-family-challenge-v2-ordinal-30", "commit": {"sha": "c" * 40}},
            ],
            "runs": [
                {
                    "id": 123,
                    "head_branch": AUTH_BRANCH,
                    "head_sha": AUTH_HEAD,
                    "path": ".github/workflows/aerosol-family-v2-r7-authorization-review.yml",
                    "event": "pull_request",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "failure",
                }
            ],
            "artifacts": [],
            "pulls": [
                {
                    "number": 264,
                    "state": "closed",
                    "merged_at": None,
                    "title": "Failed review preserved",
                    "body": "No scientific dispatch occurred.",
                    "head": {"ref": AUTH_BRANCH, "sha": AUTH_HEAD},
                }
            ],
            "issues": [],
            "issueComments": [],
            "pullReviewComments": [],
            "commitComments": [],
            "issue60Comments": [],
        }

    def test_one_closed_unmerged_pr_and_one_failed_attempt1_review_is_reusable(self):
        out = self.surface.build_surface(self.payload(), 31)
        self.assertTrue(out["authorizationBranchExists"])
        self.assertEqual(out["authorizationBranchHeadSha"], AUTH_HEAD)
        self.assertTrue(out["authorizationBranchReusableAfterFailedReview"])
        self.assertEqual(out["latestPriorConsumedScientificOrdinal"], 30)
        self.assertEqual(out["nextAvailableScientificOrdinal"], 31)
        self.assertEqual(out["candidatePriorScientificRunCount"], 0)

    def test_successful_review_is_never_reusable(self):
        payload = self.payload()
        payload["runs"][0]["conclusion"] = "success"
        self.assertFalse(self.surface.build_surface(payload, 31)["authorizationBranchReusableAfterFailedReview"])

    def test_rerun_attempt_or_open_pr_is_never_reusable(self):
        payload = self.payload()
        payload["runs"][0]["run_attempt"] = 2
        self.assertFalse(self.surface.build_surface(payload, 31)["authorizationBranchReusableAfterFailedReview"])
        payload = self.payload()
        payload["pulls"][0]["state"] = "open"
        self.assertFalse(self.surface.build_surface(payload, 31)["authorizationBranchReusableAfterFailedReview"])


if __name__ == "__main__":
    unittest.main()
