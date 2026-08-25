import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v4"
CONTROL = REC / "RECOVERY_CONTROL_CONTRACT.review.json"
ACTIVATION = REC / "WORKFLOW_ACTIVATION_CONTRACT.review.json"
AUTH_CANDIDATE = REC / "authorization-review-workflow-v4.yml.review"
SCIENCE_CANDIDATE = REC / "science-workflow-v4.yml.review"
HELPER = REC / "read_only_gh_api_retry_v4.py"
EVIDENCE = REC / "HISTORICAL_PRE_SOLVER_EVIDENCE.review.json"
AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v4.yml"
SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v4.yml"
V3_AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v3.yml"
V3_SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v3.yml"
ACTIVATION_REVIEW = ROOT / ".github/workflows/asiv-matched-stellar-recovery-workflow-activation-review-v4.yml"

EXPECTED_CONTROL_BLOB = "775f65ee5f6ca8ec847829bc9ea73c08f0744f96"
EXPECTED_ACTIVATION_BLOB = "d080814b874337a7e2ade96aa0d4b8d0f5efe5d0"
EXPECTED_AUTH_BLOB = "b4d7f489be60a98c6bc6a9af48fce70dcd40d6e9"
EXPECTED_SCIENCE_BLOB = "1d36adb676cae115b141c8c085afb9e22e2142c3"
EXPECTED_HELPER_BLOB = "7b9a0698135f60c56cb8a212a724079cda054cc3"
EXPECTED_EVIDENCE_BLOB = "b779f3dc46773fb4819fea6999ddd2fd68904aa1"
EXPECTED_V3_AUTH_BLOB = "86564ecd4d33c6c5f94d657214c3aa98f09c211a"
EXPECTED_V3_SCIENCE_BLOB = "fd844e53da4d4433a3a5322a40af2dd734238376"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class RecoveryV4WorkflowActivationTests(unittest.TestCase):
    def test_v4_active_authorization_review_matches_compact_candidate_and_science_is_unchanged(self):
        self.assertEqual(git_blob_sha1(AUTH_CANDIDATE), EXPECTED_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_ACTIVE), EXPECTED_AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_CANDIDATE.read_bytes())
        self.assertEqual(git_blob_sha1(SCIENCE_CANDIDATE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE_ACTIVE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE_CANDIDATE.read_bytes())

    def test_activation_contract_binds_compact_history_control_and_exact_science(self):
        control = json.loads(CONTROL.read_text(encoding="utf-8"))
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        self.assertEqual(git_blob_sha1(CONTROL), EXPECTED_CONTROL_BLOB)
        self.assertEqual(git_blob_sha1(ACTIVATION), EXPECTED_ACTIVATION_BLOB)
        self.assertEqual(git_blob_sha1(HELPER), EXPECTED_HELPER_BLOB)
        self.assertEqual(git_blob_sha1(EVIDENCE), EXPECTED_EVIDENCE_BLOB)
        self.assertEqual(activation["sourceRecoveryControlContract"]["gitBlobSha1"], EXPECTED_CONTROL_BLOB)
        roles = {row["role"]: row for row in activation["exactActivations"]}
        self.assertEqual(roles["authorization-review"]["candidateGitBlobSha1"], EXPECTED_AUTH_BLOB)
        self.assertEqual(roles["authorization-review"]["activeGitBlobSha1Required"], EXPECTED_AUTH_BLOB)
        self.assertEqual(roles["science"]["candidateGitBlobSha1"], EXPECTED_SCIENCE_BLOB)
        self.assertEqual(roles["science"]["activeGitBlobSha1Required"], EXPECTED_SCIENCE_BLOB)
        history = activation["historicalEvidenceAlignment"]
        self.assertEqual(history["historicalEvidenceGitBlobSha1"], EXPECTED_EVIDENCE_BLOB)
        self.assertEqual(history["priorRunIds"], [32848973816, 32868735547, 32874586374])
        self.assertFalse(history["fullHistoricalJobsEnumerationInAuthorizationReviewPermitted"])
        self.assertEqual(history["exactFailedJobIdsForCompactLiveCheck"], [97805508810, 97870360724, 97889371107])
        self.assertTrue(history["immutableEvidenceRemainsAuthorityForPreviouslyReviewedFullJobEnumeration"])
        retired = activation["retiredAuthorizationReview"]
        self.assertEqual(retired["pullRequestNumber"], 383)
        self.assertEqual(retired["runId"], 32876439701)
        self.assertEqual(retired["failedJobId"], 97895352566)
        self.assertFalse(retired["receiptProduced"])
        self.assertFalse(retired["scienceDispatchOccurred"])
        preserved = activation["preservedScience"]
        self.assertEqual(preserved["scienceWorkflowGitBlobSha1"], EXPECTED_SCIENCE_BLOB)
        self.assertFalse(preserved["scienceWorkflowChangedByThisControlFix"])
        self.assertEqual(preserved["caseCount"], 3468)
        self.assertEqual(preserved["shardCount"], 99)
        self.assertEqual(preserved["johnsonVComparisonCount"], 2304)
        self.assertEqual(preserved["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(preserved["perFamilyRmsDeltaAvMag"], 0.01)

    def test_activation_itself_grants_no_scientific_or_production_authority(self):
        activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))
        for key in (
            "scientificExecutionAuthorized", "solverExecutionAuthorized", "authorizationFileCreated",
            "dispatchBranchCreated", "workflowDispatchPerformed", "resultOpeningAuthorized",
            "productionActivationAuthorized", "pandoraHoldoutAccessAllowed", "starsvisibilityMutationAuthorized",
            "nativeRebuildAuthorized", "retryPermitted", "resumePermitted", "githubRerunPermitted",
        ):
            self.assertIs(activation[key], False, key)
        boundary = activation["activationBoundary"]
        self.assertTrue(boundary["authorizationMayNotBeCreatedByThisReview"])
        self.assertTrue(boundary["scienceMayNotBeDispatchedByThisReview"])
        self.assertTrue(boundary["historicalEvidenceMustBeCompactLiveVerifiedBySeparateAuthorizationReview"])
        self.assertTrue(boundary["scienceMayConsumeOnlyVerifiedHistoricalReceipt"])
        self.assertTrue(boundary["authorizationMustBeSeparateFreshOneFileDraftPr"])

    def test_v3_active_workflows_remain_unchanged(self):
        self.assertEqual(git_blob_sha1(V3_AUTH_ACTIVE), EXPECTED_V3_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(V3_SCIENCE_ACTIVE), EXPECTED_V3_SCIENCE_BLOB)

    def test_active_v4_auth_is_compact_and_active_science_semantics_are_frozen(self):
        auth = AUTH_ACTIVE.read_text(encoding="utf-8")
        science = SCIENCE_ACTIVE.read_text(encoding="utf-8")
        self.assertIn("pull_request:", auth)
        self.assertNotIn("workflow_dispatch:", auth)
        self.assertNotIn("/jobs?per_page=100", auth)
        self.assertNotIn("--paginate --slurp", auth)
        for jid in (97805508810, 97870360724, 97889371107):
            self.assertIn(f"actions/jobs/{jid}", auth)
        self.assertIn("gate.validate_strict_authorization(auth)", auth)
        self.assertIn("batch.validate_batch_authorization(auth)", auth)
        self.assertIn("HISTORICAL_PRE_SOLVER_EVIDENCE_LIVE_VERIFIED", auth)
        self.assertIn("workflow_dispatch:", science)
        self.assertIn("dispatch/asiv-matched-stellar-transport-recovery-v4", science)
        self.assertIn("GITHUB_RUN_NUMBER", science)
        self.assertIn("actions/download-artifact@v4", science)
        self.assertIn("max-parallel: 8", science)
        self.assertIn("fail-fast: true", science)
        self.assertIn("Execute exactly one frozen shard with no retry or resume", science)
        self.assertIn("execute_shard_strict", science)
        self.assertIn("allow_execution=True", science)
        self.assertIn("scientificCaseCount']=3468", science)
        self.assertIn("validationJohnsonVComparisonsTotal')!=2304", science)
        self.assertIn("exactly 99 unique complete Recovery v4 shard artifact directories required", science)

    def test_activation_review_is_zero_solver_and_fresh_authorization_is_separate(self):
        text = ACTIVATION_REVIEW.read_text(encoding="utf-8")
        header = text.split("\njobs:\n", 1)[0]
        self.assertIn("pull_request:", header)
        self.assertNotIn("workflow_dispatch:", header)
        self.assertIn("contents: read", header)
        self.assertNotIn("contents: write", header)
        self.assertNotIn("actions: write", header)
        self.assertNotIn("mamba-org/setup-micromamba@", text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertNotIn("allow_execution=True", text)
        self.assertIn("test ! -e review/asiv-matched-stellar-transport-v1/authorization-recovery-v4.json", text)


if __name__ == "__main__":
    unittest.main()
