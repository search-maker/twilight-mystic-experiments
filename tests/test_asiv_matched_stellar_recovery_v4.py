import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v4"
HELPER = BASE / "read_only_gh_api_retry_v4.py"
EVIDENCE = BASE / "HISTORICAL_PRE_SOLVER_EVIDENCE.review.json"
CONTRACT = BASE / "RECOVERY_CONTROL_CONTRACT.review.json"
SCIENCE = BASE / "science-workflow-v4.yml.review"
AUTH_REVIEW = BASE / "authorization-review-workflow-v4.yml.review"
AUTH_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-authorization-review-recovery-v4.yml"
SCIENCE_ACTIVE = ROOT / ".github/workflows/asiv-matched-stellar-science-recovery-v4.yml"

EXPECTED_HELPER_BLOB = "7b9a0698135f60c56cb8a212a724079cda054cc3"
EXPECTED_EVIDENCE_BLOB = "b779f3dc46773fb4819fea6999ddd2fd68904aa1"
EXPECTED_AUTH_BLOB = "b4d7f489be60a98c6bc6a9af48fce70dcd40d6e9"
EXPECTED_SCIENCE_BLOB = "1d36adb676cae115b141c8c085afb9e22e2142c3"
EXPECTED_CONTROL_BLOB = "775f65ee5f6ca8ec847829bc9ea73c08f0744f96"


def git_blob_sha1(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def load_helper():
    spec = importlib.util.spec_from_file_location("matched_stellar_read_retry_v4", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RecoveryV4CompactHistoryTests(unittest.TestCase):
    def test_exact_control_blobs_and_unchanged_science(self):
        self.assertEqual(git_blob_sha1(HELPER), EXPECTED_HELPER_BLOB)
        self.assertEqual(git_blob_sha1(EVIDENCE), EXPECTED_EVIDENCE_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_REVIEW), EXPECTED_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_ACTIVE), EXPECTED_AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_REVIEW.read_bytes())
        self.assertEqual(git_blob_sha1(SCIENCE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE_ACTIVE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE.read_bytes())
        self.assertEqual(git_blob_sha1(CONTRACT), EXPECTED_CONTROL_BLOB)

    def test_immutable_evidence_remains_exact_three_pre_solver_failures(self):
        row = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        prior = row["priorRuns"]
        self.assertEqual([x["runId"] for x in prior], [32848973816, 32868735547, 32874586374])
        self.assertEqual([x["failedJobId"] for x in prior], [97805508810, 97870360724, 97889371107])
        for item in prior:
            self.assertFalse(item["solverExecutionObserved"])
            self.assertEqual(item["scientificShardArtifactCount"], 0)
            self.assertEqual(item["finalValidationArtifactCount"], 0)
        common = row["commonBoundary"]
        self.assertFalse(common["scientificSolverExecutionObserved"])
        self.assertFalse(common["scientificShardArtifactsObserved"])
        self.assertFalse(common["finalValidationArtifactsObserved"])
        self.assertFalse(common["githubJobRerunPermitted"])
        self.assertFalse(common["solverRetryPermitted"])
        self.assertFalse(common["solverResumePermitted"])
        self.assertFalse(common["pandoraHoldoutOpened"])
        self.assertFalse(common["productionAuthorized"])

    def test_helper_policy_is_still_fail_closed_and_does_not_authorize_solver_retry(self):
        mod = load_helper()
        self.assertEqual(mod.TRANSIENT_HTTP_STATUSES, {502, 503, 504})
        self.assertEqual(mod.MAX_ATTEMPTS, 8)
        self.assertEqual(mod.BACKOFF_SECONDS, (2, 4, 8, 16, 30, 30, 30))
        for args in (["-X", "POST", "repos/x/y"], ["--method=PATCH", "repos/x/y"], ["-f", "state=open", "repos/x/y"], ["--input", "payload.json", "repos/x/y"]):
            with self.subTest(args=args), mock.patch.object(mod.subprocess, "run") as run:
                with self.assertRaises(SystemExit):
                    mod.run_read_only_gh_api(list(args), Path("unused"))
                run.assert_not_called()
        responses = [
            subprocess.CompletedProcess(["gh"], 1, b"", b"gh: Server Error (HTTP 502)\n"),
            subprocess.CompletedProcess(["gh"], 0, b"", b""),
        ]
        def fake_run(cmd, stdout, stderr, check):
            row = responses.pop(0)
            if row.returncode == 0:
                stdout.write(b'{"ok":true}\n')
            return row
        with tempfile.TemporaryDirectory() as td, mock.patch.object(mod.subprocess, "run", side_effect=fake_run), mock.patch.object(mod.time, "sleep"):
            audit = mod.run_read_only_gh_api(["repos/x/y/actions/runs/1"], Path(td) / "result.json")
            self.assertFalse(audit["writeMethodsPermitted"])
            self.assertFalse(audit["solverRetryPermitted"])
            self.assertFalse(audit["solverResumePermitted"])

    def test_contract_preserves_science_and_freezes_compact_history_fix(self):
        row = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(row["recoveryVersion"], 4)
        self.assertEqual(row["baseMainSha"], "bea05fcbd99858b9667ad1c444b2db542006db0f")
        retired = row["retiredAuthorizationReview"]
        self.assertEqual(retired["pullRequestNumber"], 383)
        self.assertEqual(retired["workflowRunId"], 32876439701)
        self.assertEqual(retired["failedJobId"], 97895352566)
        self.assertFalse(retired["authorizationReceiptProduced"])
        self.assertFalse(retired["scienceRunCreated"])
        history = row["historicalEvidenceHandoff"]
        self.assertEqual(history["gitBlobSha1"], EXPECTED_EVIDENCE_BLOB)
        compact = history["compactLiveVerification"]
        self.assertFalse(compact["fullHistoricalJobsEnumerationPermitted"])
        self.assertFalse(compact["paginatedHistoricalJobsListPermitted"])
        self.assertEqual(compact["exactFailedJobReads"], [97805508810, 97870360724, 97889371107])
        self.assertTrue(compact["frozenEvidenceRemainsAuthorityForFullNoSolverEnumeration"])
        self.assertEqual(row["authorizationReviewWorkflowCandidateGitBlobSha1"], EXPECTED_AUTH_BLOB)
        self.assertEqual(row["scienceWorkflowCandidateGitBlobSha1"], EXPECTED_SCIENCE_BLOB)
        self.assertFalse(row["scienceWorkflowBytesChangedByCompactHistoryFix"])
        self.assertEqual(row["caseUniverse"]["trainingSpectraTotal"], 2700)
        self.assertEqual(row["caseUniverse"]["validationAtmosphericSpectraTotal"], 768)
        self.assertEqual(row["caseUniverse"]["validationJohnsonVComparisonsTotal"], 2304)
        self.assertEqual(row["caseUniverse"]["totalCaseCount"], 3468)
        self.assertEqual(row["caseUniverse"]["totalShardCount"], 99)
        self.assertEqual(row["acceptanceGates"]["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(row["acceptanceGates"]["perFamilyRmsDeltaAvMag"], 0.01)
        self.assertFalse(row["productionAuthorized"])
        self.assertFalse(row["pandoraHoldoutAccessAllowed"])
        self.assertFalse(row["scientificExecutionAuthorizedByThisReview"])

    def test_authorization_review_uses_compact_live_proof_and_both_strict_gates(self):
        text = AUTH_REVIEW.read_text(encoding="utf-8")
        for rid in (32848973816, 32868735547, 32874586374):
            self.assertIn(f'actions/runs/${{RID}}', text)
            self.assertIn(f'actions/runs/${{RID}}/artifacts?per_page=100', text)
        for jid in (97805508810, 97870360724, 97889371107):
            self.assertIn(f"actions/jobs/{jid}", text)
        self.assertNotIn("/jobs?per_page=100", text)
        self.assertNotIn("--paginate --slurp", text)
        self.assertIn("IMMUTABLE_FULL_ENUMERATION_EVIDENCE_PLUS_COMPACT_LIVE_IDENTITY_JOB_ARTIFACT_CHECK", text)
        self.assertIn("fullHistoricalJobsEnumerationPerformedInThisReview':False", text)
        self.assertIn("gate.validate_strict_authorization(auth)", text)
        self.assertIn("batch.validate_batch_authorization(auth)", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertNotIn("workflow_dispatch:", text)

    def test_science_workflow_is_byte_unchanged_and_consumes_receipt_only(self):
        text = SCIENCE.read_text(encoding="utf-8")
        for rid in (32848973816, 32868735547, 32874586374):
            self.assertNotIn(f"actions/runs/{rid}", text)
        self.assertIn('test "$GITHUB_RUN_NUMBER" = 1', text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn("historicalPreSolverEvidenceVerified", text)
        self.assertIn("actions/download-artifact@v4", text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("execute_shard_strict", text)
        self.assertIn("allow_execution=True", text)
        self.assertIn("scientificCaseCount']=3468", text)
        self.assertIn("recoveryVersion']=4", text)
        self.assertNotIn("rerun-failed-jobs", text)


if __name__ == "__main__":
    unittest.main()
