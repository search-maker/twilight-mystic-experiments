from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "review/asiv-matched-stellar-transport-v1/science-control/SCIENCE_CONTROL_CONTRACT.review.json"
ACTIVATION = ROOT / "review/asiv-matched-stellar-transport-v1/science-control/WORKFLOW_ACTIVATION_CONTRACT.review.json"
AUTH_CANDIDATE = ROOT / "review/asiv-matched-stellar-transport-v1/science-control/authorization-review-workflow.yml.review"
SCIENCE_CANDIDATE = ROOT / "review/asiv-matched-stellar-transport-v1/science-control/science-workflow.yml.review"
AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-v1.yml"
SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-v1.yml"
ACTIVATION_REVIEW = ROOT / ".github/workflows/asiv-matched-stellar-workflow-activation-review-v1.yml"
AUTHORIZATION = ROOT / "review/asiv-matched-stellar-transport-v1/authorization.json"

EXPECTED_AUTH_BLOB = "6ed68a90f2614dd762b5484e740a146e2cb636cc"
EXPECTED_SCIENCE_BLOB = "396bb79f0f00b36888f809f7f3bff40d62646632"
EXPECTED_CONTROL_BLOB = "97e4ee84def3ffc620328646effbf6fdfbeb8394"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class AsivMatchedStellarWorkflowActivationV1Tests(unittest.TestCase):
    def test_active_workflows_are_exact_candidate_blobs(self):
        self.assertEqual(git_blob_sha1(AUTH_CANDIDATE), EXPECTED_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_ACTIVE), EXPECTED_AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_CANDIDATE.read_bytes())
        self.assertEqual(git_blob_sha1(SCIENCE_CANDIDATE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE_ACTIVE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE_CANDIDATE.read_bytes())

    def test_activation_contract_matches_frozen_science_control(self):
        control = json.loads(CONTROL.read_text(encoding="utf-8"))
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        self.assertEqual(git_blob_sha1(CONTROL), EXPECTED_CONTROL_BLOB)
        self.assertEqual(activation["sourceScienceControlContract"]["gitBlobSha1"], EXPECTED_CONTROL_BLOB)
        roles = {row["role"]: row for row in activation["exactActivations"]}
        self.assertEqual(roles["authorization-review"]["candidateGitBlobSha1"], control["workflowCandidates"]["authorizationReview"]["gitBlobSha1"])
        self.assertEqual(roles["authorization-review"]["activeGitBlobSha1Required"], EXPECTED_AUTH_BLOB)
        self.assertEqual(roles["science"]["candidateGitBlobSha1"], control["workflowCandidates"]["science"]["gitBlobSha1"])
        self.assertEqual(roles["science"]["activeGitBlobSha1Required"], EXPECTED_SCIENCE_BLOB)
        self.assertEqual(roles["authorization-review"]["activePath"], control["workflowCandidates"]["authorizationReview"]["futureActivePath"])
        self.assertEqual(roles["science"]["activePath"], control["workflowCandidates"]["science"]["futureActivePath"])

    def test_activation_review_does_not_create_authorization_or_cross_boundary(self):
        self.assertFalse(AUTHORIZATION.exists())
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        for key in (
            "scientificExecutionAuthorized", "solverExecutionAuthorized", "authorizationFileCreated",
            "authorizationBranchCreated", "dispatchBranchCreated", "workflowDispatchPerformed",
            "resultOpeningAuthorized", "productionActivationAuthorized", "pandoraHoldoutAccessAllowed",
            "starsvisibilityMutationAuthorized", "nativeRebuildAuthorized", "retryPermitted",
            "resumePermitted", "githubRerunPermitted",
        ):
            self.assertIs(activation[key], False, key)
        boundary = activation["activationBoundary"]
        self.assertIs(boundary["authorizationMayNotBeCreatedByThisReview"], True)
        self.assertIs(boundary["scienceMayNotBeDispatchedByThisReview"], True)
        self.assertIs(boundary["activeScienceWorkflowAloneIsInsufficientForExecution"], True)
        self.assertIs(boundary["strictAuthorizationGateStillRequired"], True)
        self.assertIs(boundary["batchAuthorizationStillRequired"], True)

    def test_active_workflow_control_semantics_remain_frozen(self):
        auth = AUTH_ACTIVE.read_text(encoding="utf-8")
        science = SCIENCE_ACTIVE.read_text(encoding="utf-8")
        self.assertIn("pull_request:", auth)
        self.assertIn("review/asiv-matched-stellar-transport-v1/authorization.json", auth)
        self.assertNotIn("workflow_dispatch:", auth)
        self.assertNotIn("uvspec", auth)
        self.assertIn("workflow_dispatch:", science)
        self.assertIn("dispatch/asiv-matched-stellar-transport-v1", science)
        self.assertIn("GITHUB_RUN_ATTEMPT", science)
        self.assertIn("max-parallel: 8", science)
        self.assertIn("fail-fast: true", science)
        self.assertIn("execute_shard_strict", science)
        self.assertIn("allow_execution=True", science)
        self.assertIn("3468", science)
        self.assertIn("99", science)
        self.assertNotIn("pandora", science.lower())
        self.assertNotIn("starsvisibility", science.lower())

    def test_activation_review_workflow_itself_is_zero_runtime(self):
        text = ACTIVATION_REVIEW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("setup-micromamba", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("--allow-execution", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("actions: write", text)


if __name__ == "__main__":
    unittest.main()
