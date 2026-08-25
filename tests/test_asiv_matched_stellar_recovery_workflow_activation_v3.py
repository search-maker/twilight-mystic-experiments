from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v3"
CONTROL = REC / "RECOVERY_CONTROL_CONTRACT.review.json"
ACTIVATION = REC / "WORKFLOW_ACTIVATION_CONTRACT.review.json"
AUTH_CANDIDATE = REC / "authorization-review-workflow-v3.yml.review"
SCIENCE_CANDIDATE = REC / "science-workflow-v3.yml.review"
HELPER = REC / "read_only_gh_api_retry_v3.py"
EVIDENCE = REC / "RUN_32868735547_PRE_SOLVER_FAILURE.review.json"
AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v3.yml"
SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v3.yml"
V2_AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v2.yml"
V2_SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v2.yml"
V1_AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-v1.yml"
V1_SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-v1.yml"
AUTHORIZATION = ROOT / "review/asiv-matched-stellar-transport-v1/authorization-recovery-v3.json"
ACTIVATION_REVIEW = ROOT / ".github/workflows/asiv-matched-stellar-recovery-workflow-activation-review-v3.yml"

EXPECTED_CONTROL_BLOB = "1c9ba7e3f30388835bd87d24e3e2c7d03c050126"
EXPECTED_AUTH_BLOB = "86564ecd4d33c6c5f94d657214c3aa98f09c211a"
EXPECTED_SCIENCE_BLOB = "fd844e53da4d4433a3a5322a40af2dd734238376"
EXPECTED_HELPER_BLOB = "ce2ebe14f5128308fb8d138d38b064f8387feb29"
EXPECTED_EVIDENCE_BLOB = "2caae4d121e13eced92cfb7b362c29502d2a25f4"
EXPECTED_V2_AUTH_BLOB = "a334c8d4537f4503a502978f106daf83c87a1c9e"
EXPECTED_V2_SCIENCE_BLOB = "91fc9bc11102cc30db9c3ed46a2ee9290747c986"
EXPECTED_V1_AUTH_BLOB = "6ed68a90f2614dd762b5484e740a146e2cb636cc"
EXPECTED_V1_SCIENCE_BLOB = "396bb79f0f00b36888f809f7f3bff40d62646632"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class RecoveryV3WorkflowActivationTests(unittest.TestCase):
    def test_v3_active_workflows_are_exact_candidate_bytes(self):
        self.assertEqual(git_blob_sha1(AUTH_CANDIDATE), EXPECTED_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_ACTIVE), EXPECTED_AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_CANDIDATE.read_bytes())
        self.assertEqual(git_blob_sha1(SCIENCE_CANDIDATE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE_ACTIVE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE_CANDIDATE.read_bytes())

    def test_activation_contract_binds_exact_control_retry_and_strict_gate_alignment(self):
        control = json.loads(CONTROL.read_text(encoding="utf-8"))
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        self.assertEqual(git_blob_sha1(CONTROL), EXPECTED_CONTROL_BLOB)
        self.assertEqual(git_blob_sha1(HELPER), EXPECTED_HELPER_BLOB)
        self.assertEqual(git_blob_sha1(EVIDENCE), EXPECTED_EVIDENCE_BLOB)
        self.assertEqual(activation["sourceRecoveryControlContract"]["gitBlobSha1"], EXPECTED_CONTROL_BLOB)
        roles = {row["role"]: row for row in activation["exactActivations"]}
        self.assertEqual(roles["authorization-review"]["candidateGitBlobSha1"], EXPECTED_AUTH_BLOB)
        self.assertEqual(roles["authorization-review"]["activeGitBlobSha1Required"], EXPECTED_AUTH_BLOB)
        self.assertEqual(roles["science"]["candidateGitBlobSha1"], EXPECTED_SCIENCE_BLOB)
        self.assertEqual(roles["science"]["activeGitBlobSha1Required"], EXPECTED_SCIENCE_BLOB)
        alignment = activation["strictGateAlignment"]
        self.assertEqual(alignment["immutableStrictGateGitBlobSha1"], "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde")
        self.assertEqual(alignment["requiredScientificAuthorizationStageId"], "asiv-matched-stellar-transport-v1-execution-authorization")
        self.assertEqual(alignment["recoveryControlStageId"], "asiv-matched-stellar-transport-recovery-v3-authorization")
        self.assertTrue(alignment["strictCaseUniverseMustEqualExecutionContractExactly"])
        self.assertTrue(alignment["batchCardinalityMustRemainInBatchBindings"])
        self.assertTrue(alignment["authorizationReviewMustExecuteStrictGateValidation"])
        self.assertTrue(alignment["authorizationReviewMustExecuteBatchGateValidation"])
        self.assertEqual(control["readOnlyApiRetryPolicy"]["retryHttpStatuses"], [502, 503, 504])
        self.assertEqual(control["readOnlyApiRetryPolicy"]["maxAttempts"], 3)
        self.assertFalse(control["readOnlyApiRetryPolicy"]["solverRetryPermitted"])
        self.assertFalse(control["readOnlyApiRetryPolicy"]["solverResumePermitted"])

    def test_v1_and_v2_active_workflows_remain_unchanged(self):
        self.assertEqual(git_blob_sha1(V2_AUTH_ACTIVE), EXPECTED_V2_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(V2_SCIENCE_ACTIVE), EXPECTED_V2_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(V1_AUTH_ACTIVE), EXPECTED_V1_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(V1_SCIENCE_ACTIVE), EXPECTED_V1_SCIENCE_BLOB)

    def test_alignment_creates_no_authorization_or_dispatch(self):
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
        self.assertTrue(boundary["authorizationMayNotBeCreatedByThisReview"])
        self.assertTrue(boundary["scienceMayNotBeDispatchedByThisReview"])
        self.assertTrue(boundary["bothPriorPreSolverFailuresMustStillBeReverifiedAtDispatch"])
        self.assertTrue(boundary["readOnlyApiTransportRetryDoesNotAuthorizeSolverRetry"])

    def test_active_v3_control_and_science_semantics_remain_frozen(self):
        auth = AUTH_ACTIVE.read_text(encoding="utf-8")
        science = SCIENCE_ACTIVE.read_text(encoding="utf-8")
        self.assertIn("pull_request:", auth)
        self.assertIn("authorization-recovery-v3.json", auth)
        self.assertNotIn("workflow_dispatch:", auth)
        self.assertNotIn("uvspec", auth)
        self.assertIn("asiv-matched-stellar-transport-v1-execution-authorization", auth)
        self.assertIn("asiv-matched-stellar-transport-recovery-v3-authorization", auth)
        self.assertIn("gate.validate_strict_authorization(auth)", auth)
        self.assertIn("batch.validate_batch_authorization(auth)", auth)
        self.assertIn("workflow_dispatch:", science)
        self.assertIn("dispatch/asiv-matched-stellar-transport-recovery-v3", science)
        self.assertIn("32848973816", science)
        self.assertIn("32868735547", science)
        self.assertIn("read_only_gh_api_retry_v3.py", science)
        self.assertIn("micromamba_list_parser_v2.py", science)
        self.assertIn("max-parallel: 8", science)
        self.assertIn("fail-fast: true", science)
        self.assertIn("Execute exactly one frozen shard with no retry or resume", science)
        self.assertIn("execute_shard_strict", science)
        self.assertIn("allow_execution=True", science)
        self.assertIn("batch.get('totalCaseCount')!=3468", science)
        self.assertIn("universe.get('validationJohnsonVComparisonsTotal')!=2304", science)
        self.assertIn("exactly 99 unique complete Recovery v3 shard artifacts required", science)
        self.assertIn("artifact digest mismatch", science)
        self.assertNotIn("gh api ", science)

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
