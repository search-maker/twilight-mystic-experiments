from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Wave3AuthorizationReviewV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.review = load(
            cls.root / "experiments/tier1-precision-continuation-wave3-v1/authorization_review.py",
            "wave3_authorization_review_test",
        )

    def metadata(self, *, exists: bool = False):
        return {
            "authorizationBranch": self.review.AUTHORIZATION_BRANCH,
            "authorizationBranchExists": exists,
            "authorizationHead": "2" * 40,
            "authorizationParent": "1" * 40,
            "liveMain": "1" * 40,
            "parentCount": 1,
            "changedFiles": [self.review.AUTHORIZATION_PATH],
            "dispatchBranchExists": False,
        }

    def artifact(self):
        return {
            "id": self.review.SOURCE_ARTIFACT_ID,
            "name": self.review.SOURCE_ARTIFACT_NAME,
            "expired": False,
            "digest": self.review.SOURCE_ARTIFACT_DIGEST,
            "workflow_run": {
                "id": self.review.SOURCE_RUN_ID,
                "head_branch": "dispatch/tier1-precision-continuation-wave2-ordinal12-v1",
                "head_sha": self.review.SOURCE_HEAD_SHA,
            },
        }

    def test_dry_and_actual_commit_identity_are_accepted(self):
        self.review.validate_commit_metadata(self.metadata(exists=False), "dry-review")
        self.review.validate_commit_metadata(self.metadata(exists=True), "actual-authorization")

    def test_refuses_parent_not_equal_live_main(self):
        value = self.metadata()
        value["liveMain"] = "3" * 40
        with self.assertRaisesRegex(Exception, "commit identity changed"):
            self.review.validate_commit_metadata(value, "dry-review")

    def test_refuses_more_than_one_changed_file(self):
        value = self.metadata()
        value["changedFiles"].append("README.md")
        with self.assertRaisesRegex(Exception, "commit identity changed"):
            self.review.validate_commit_metadata(value, "dry-review")

    def test_refuses_dispatch_or_wrong_authorization_branch_state(self):
        value = self.metadata()
        value["dispatchBranchExists"] = True
        with self.assertRaisesRegex(Exception, "commit identity changed"):
            self.review.validate_commit_metadata(value, "dry-review")
        value = self.metadata(exists=False)
        with self.assertRaisesRegex(Exception, "authorizationBranchExists"):
            self.review.validate_commit_metadata(value, "actual-authorization")

    def test_exact_source_artifact_metadata_is_accepted(self):
        self.review.validate_artifact_metadata(self.artifact())

    def test_refuses_source_artifact_or_run_drift(self):
        value = self.artifact()
        value["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(Exception, "source artifact metadata changed"):
            self.review.validate_artifact_metadata(value)
        value = self.artifact()
        value["workflow_run"]["id"] += 1
        with self.assertRaisesRegex(Exception, "source artifact metadata changed"):
            self.review.validate_artifact_metadata(value)

    def test_repository_history_must_not_contain_title_or_dispatch_branch(self):
        report = self.review.validate_no_prior_identity(
            [{"id": 1, "display_title": "Unrelated contract", "head_branch": "main"}]
        )
        self.assertEqual(report["matchingRunCount"], 0)
        with self.assertRaisesRegex(Exception, "scientific identity already exists"):
            self.review.validate_no_prior_identity(
                [{"id": 2, "display_title": self.review.RUN_TITLE, "head_branch": "main"}]
            )
        with self.assertRaisesRegex(Exception, "scientific identity already exists"):
            self.review.validate_no_prior_identity(
                [{"id": 3, "display_title": "Other", "head_branch": self.review.DISPATCH_BRANCH}]
            )

    def test_live_scientific_workflow_is_exact_push_only_transport(self):
        digest = self.review.validate_scientific_workflow(self.root)
        self.assertEqual(len(digest), 64)

    def test_sha_shape_is_strict(self):
        self.assertTrue(self.review.valid_sha("a" * 40))
        self.assertFalse(self.review.valid_sha("A" * 40))
        self.assertFalse(self.review.valid_sha("a" * 39))


if __name__ == "__main__":
    unittest.main()
