from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v2"
CONTROL = REC / "RECOVERY_CONTROL_CONTRACT.review.json"
ACTIVATION = REC / "WORKFLOW_ACTIVATION_CONTRACT.review.json"
AUTH_CANDIDATE = REC / "authorization-review-workflow-v2.yml.review"
SCIENCE_CANDIDATE = REC / "science-workflow-v2.yml.review"
AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v2.yml"
SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v2.yml"
V1_AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-v1.yml"
V1_SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-v1.yml"
AUTHORIZATION = ROOT / "review/asiv-matched-stellar-transport-v1/authorization-recovery-v2.json"
ACTIVATION_REVIEW = ROOT / ".github/workflows/asiv-matched-stellar-recovery-workflow-activation-review-v2.yml"

EXPECTED_CONTROL_BLOB = "28ec19fdc218e6230cf1aec7a52e69b5771363e6"
EXPECTED_AUTH_BLOB = "a334c8d4537f4503a502978f106daf83c87a1c9e"
EXPECTED_SCIENCE_BLOB = "91fc9bc11102cc30db9c3ed46a2ee9290747c986"
EXPECTED_V1_AUTH_BLOB = "6ed68a90f2614dd762b5484e740a146e2cb636cc"
EXPECTED_V1_SCIENCE_BLOB = "396bb79f0f00b36888f809f7f3bff40d62646632"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class RecoveryV2WorkflowActivationTests(unittest.TestCase):
    def test_recovery_active_workflows_are_exact_candidate_bytes(self):
        self.assertEqual(git_blob_sha1(AUTH_CANDIDATE), EXPECTED_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_ACTIVE), EXPECTED_AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_CANDIDATE.read_bytes())
        self.assertEqual(git_blob_sha1(SCIENCE_CANDIDATE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE_ACTIVE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE_CANDIDATE.read_bytes())

    def test_activation_contract_binds_exact_recovery_control(self):
        control = json.loads(CONTROL.read_text(encoding="utf-8"))
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        self.assertEqual(git_blob_sha1(CONTROL), EXPECTED_CONTROL_BLOB)
        self.assertEqual(activation["sourceRecoveryControlContract"]["gitBlobSha1"], EXPECTED_CONTROL_BLOB)
        roles = {row["role"]: row for row in activation["exactActivations"]}
        self.assertEqual(roles["authorization-review"]["candidateGitBlobSha1"], control["workflowCandidates"]["authorizationReview"]["gitBlobSha1"])
        self.assertEqual(roles["authorization-review"]["activeGitBlobSha1Required"], EXPECTED_AUTH_BLOB)
        self.assertEqual(roles["science"]["candidateGitBlobSha1"], control["workflowCandidates"]["science"]["gitBlobSha1"])
        self.assertEqual(roles["science"]["activeGitBlobSha1Required"], EXPECTED_SCIENCE_BLOB)
        self.assertEqual(roles["authorization-review"]["activePath"], control["workflowCandidates"]["authorizationReview"]["futureActivePath"])
        self.assertEqual(roles["science"]["activePath"], control["workflowCandidates"]["science"]["futureActivePath"])

    def test_v1_active_workflows_remain_unchanged(self):
        self.assertEqual(git_blob_sha1(V1_AUTH_ACTIVE), EXPECTED_V1_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(V1_SCIENCE_ACTIVE), EXPECTED_V1_SCIENCE_BLOB)

    def test_activation_creates_no_authorization_or_dispatch(self):
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
        self.assertIs(boundary["activeRecoveryScienceWorkflowAloneIsInsufficientForExecution"], True)
        self.assertIs(boundary["priorV1PreSolverFailureReverificationStillRequired"], True)

    def test_active_recovery_science_semantics_remain_frozen(self):
        auth = AUTH_ACTIVE.read_text(encoding="utf-8")
        science = SCIENCE_ACTIVE.read_text(encoding="utf-8")
        self.assertIn("pull_request:", auth)
        self.assertIn("authorization-recovery-v2.json", auth)
        self.assertNotIn("workflow_dispatch:", auth)
        self.assertNotIn("uvspec", auth)
        self.assertIn("workflow_dispatch:", science)
        self.assertIn("dispatch/asiv-matched-stellar-transport-recovery-v2", science)
        self.assertIn("32848973816", science)
        self.assertIn("micromamba_list_parser_v2.py", science)
        self.assertIn("GITHUB_RUN_ATTEMPT", science)
        self.assertIn("max-parallel: 8", science)
        self.assertIn("fail-fast: true", science)
        self.assertIn("execute_shard_strict", science)
        self.assertIn("allow_execution=True", science)
        self.assertIn("3468", science)
        self.assertIn("exactly 99 unique complete recovery shard artifacts required", science)

    def test_activation_review_itself_is_zero_solver(self):
        text = ACTIVATION_REVIEW.read_text(encoding="utf-8")
        header = text.split("\njobs:\n", 1)[0]
        self.assertIn("pull_request:", header)
        self.assertNotIn("workflow_dispatch:", header)
        self.assertIn("contents: read", header)
        self.assertNotIn("contents: write", header)
        self.assertNotIn("actions: write", header)
        self.assertNotIn("mamba-org/setup-micromamba@", text)
        self.assertNotIn("shell: micromamba-shell", text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertNotIn("allow_execution=True", text)


if __name__ == "__main__":
    unittest.main()
