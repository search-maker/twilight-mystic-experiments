import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v5"
HISTORY = BASE / "HISTORICAL_PRE_SOLVER_EVIDENCE.review.json"
V4_FAILURE = BASE / "RUN_32879766880_PRE_SOLVER_FAILURE.review.json"
DIAGNOSTIC = BASE / "UVSPEC_HELP_FLAG_DIAGNOSTIC.review.json"
CONTRACT = BASE / "RECOVERY_CONTROL_CONTRACT.review.json"
SCIENCE = BASE / "science-workflow-v5.yml.review"
AUTH_REVIEW = BASE / "authorization-review-workflow-v5.yml.review"

EXPECTED_HISTORY_BLOB = "1b96747b5e865f049a2c839d5adf077a2949d6fd"
EXPECTED_V4_FAILURE_BLOB = "5bd2a61b19dd601b6c755fcc2173dee6eab7966a"
EXPECTED_DIAGNOSTIC_BLOB = "e9c9ff71a9414e17403e96c2537d4724dabda3e4"
EXPECTED_SCIENCE_BLOB = "d6cced250cc3fdbdb914f3c643e419c6b931c8c6"
EXPECTED_AUTH_REVIEW_BLOB = "1a9a5258f9980467ff1f5504a79ec9d5f78495b9"
EXPECTED_CONTRACT_BLOB = "bed640935666add4e78d394d4b10d0894ad68f03"
FROZEN_HELP_SHA = "868aea5af762d968f6f62c4e1472916d25232ed9cab5be112d753b0823d20548"
FROZEN_UVSPEC_SHA = "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3"


def git_blob_sha1(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


class RecoveryV5HelpCorrectionTests(unittest.TestCase):
    def test_exact_review_blobs(self):
        self.assertEqual(git_blob_sha1(HISTORY), EXPECTED_HISTORY_BLOB)
        self.assertEqual(git_blob_sha1(V4_FAILURE), EXPECTED_V4_FAILURE_BLOB)
        self.assertEqual(git_blob_sha1(DIAGNOSTIC), EXPECTED_DIAGNOSTIC_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_REVIEW), EXPECTED_AUTH_REVIEW_BLOB)
        self.assertEqual(git_blob_sha1(CONTRACT), EXPECTED_CONTRACT_BLOB)

    def test_four_prior_runs_are_frozen_pre_solver(self):
        row = json.loads(HISTORY.read_text(encoding="utf-8"))
        prior = row["priorRuns"]
        self.assertEqual(
            [x["runId"] for x in prior],
            [32848973816, 32868735547, 32874586374, 32879766880],
        )
        self.assertEqual(
            [x["failedJobId"] for x in prior],
            [97805508810, 97870360724, 97889371107, 97906508551],
        )
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

    def test_v4_full_job_universe_remains_pre_solver(self):
        row = json.loads(V4_FAILURE.read_text(encoding="utf-8"))
        self.assertEqual(row["run"]["runId"], 32879766880)
        self.assertTrue(row["preflight"]["authorizationReceiptVerified"])
        self.assertEqual(row["preflight"]["exactShardCount"], 99)
        self.assertEqual(row["preflight"]["exactCaseCount"], 3468)
        self.assertTrue(row["failure"]["uvspecBinarySha256Passed"])
        self.assertTrue(row["failure"]["helpFingerprintCheckFailedBeforeSolver"])
        full = row["fullJobUniverseInspection"]
        self.assertEqual(full["totalJobCount"], 101)
        self.assertEqual(full["solverStepSuccessCount"], 0)
        self.assertEqual(full["solverStepFailureCount"], 0)
        self.assertEqual(full["aggregateConclusion"], "skipped")
        self.assertFalse(full["solverExecutionObserved"])
        self.assertFalse(row["boundaries"]["scientificSolverExecuted"])

    def test_zero_solver_diagnostic_proves_short_help_flag_and_preserves_hash(self):
        row = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
        self.assertEqual(row["status"], "ZERO_SOLVER_DIAGNOSTIC_PASS")
        self.assertEqual(row["uvspecBinarySha256"], FROZEN_UVSPEC_SHA)
        self.assertEqual(row["frozenHelpSha256"], FROZEN_HELP_SHA)
        self.assertEqual(row["replication"]["independentRunnerCount"], 2)
        self.assertEqual(row["replication"]["repetitionsPerFlagPerRunner"], 3)
        long_flag = row["observations"]["longFlag"]
        short_flag = row["observations"]["shortFlag"]
        self.assertFalse(long_flag["supported"])
        self.assertFalse(long_flag["matchesFrozenHash"])
        self.assertTrue(short_flag["supported"])
        self.assertTrue(short_flag["matchesFrozenHash"])
        self.assertEqual(short_flag["combinedSha256"], FROZEN_HELP_SHA)
        correction = row["requiredCorrection"]
        self.assertEqual(correction["oldInvocation"], "uvspec --help")
        self.assertEqual(correction["newInvocation"], "uvspec -h")
        self.assertEqual(correction["expectedHelpSha256Remains"], FROZEN_HELP_SHA)
        self.assertFalse(row["boundaries"]["scientificSolverExecuted"])
        self.assertFalse(row["boundaries"]["runtimeBinaryChanged"])
        self.assertFalse(row["boundaries"]["frozenHelpHashChanged"])
        self.assertFalse(row["boundaries"]["expectedHashRelaxed"])

    def test_science_candidate_changes_invocation_not_frozen_identity_or_science(self):
        text = SCIENCE.read_text(encoding="utf-8")
        self.assertIn("subprocess.run([str(uvspec),'-h'],capture_output=True,check=True)", text)
        self.assertNotIn("subprocess.run([str(uvspec),'--help']", text)
        self.assertIn(FROZEN_HELP_SHA, text)
        self.assertIn("runtimeHelpInvocation']='-h'", text)
        self.assertIn('test "$GITHUB_RUN_NUMBER" = 1', text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("execute_shard_strict", text)
        self.assertIn("allow_execution=True", text)
        self.assertIn("scientificCaseCount']=3468", text)
        self.assertIn("recoveryVersion']=5", text)
        self.assertIn("result['recoveryPriorRunIds']=[32848973816,32868735547,32874586374,32879766880]", text)
        self.assertNotIn("rerun-failed-jobs", text)
        self.assertNotIn("solverRetryPerformed']=True", text)
        self.assertNotIn("solverResumePerformed']=True", text)

    def test_authorization_review_uses_compact_four_run_proof_and_strict_gates(self):
        text = AUTH_REVIEW.read_text(encoding="utf-8")
        for rid in (32848973816, 32868735547, 32874586374, 32879766880):
            self.assertIn(str(rid), text)
        for jid in (97805508810, 97870360724, 97889371107, 97906508551):
            self.assertIn(f"actions/jobs/{jid}", text)
        self.assertNotIn("/jobs?per_page=100", text)
        self.assertIn("gate.validate_strict_authorization(auth)", text)
        self.assertIn("batch.validate_batch_authorization(auth)", text)
        self.assertIn("uvspecRuntimeHelpInvocation':'-h'", text)
        self.assertIn(FROZEN_HELP_SHA, text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertNotIn("workflow_dispatch:", text)

    def test_contract_freezes_only_control_plane_correction(self):
        row = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(row["recoveryVersion"], 5)
        self.assertEqual(row["baseMainSha"], "02944d569ea879f8f0fd7c4263b8912ef8b7dccf")
        corr = row["runtimeHelpCorrection"]
        self.assertEqual(corr["oldInvocation"], "uvspec --help")
        self.assertEqual(corr["newInvocation"], "uvspec -h")
        self.assertEqual(corr["frozenHelpSha256"], FROZEN_HELP_SHA)
        self.assertFalse(corr["frozenHashChanged"])
        self.assertFalse(corr["expectedHashRelaxed"])
        self.assertFalse(corr["uvspecBinaryChanged"])
        self.assertEqual(row["scienceWorkflowCandidateGitBlobSha1"], EXPECTED_SCIENCE_BLOB)
        self.assertEqual(row["authorizationReviewWorkflowCandidateGitBlobSha1"], EXPECTED_AUTH_REVIEW_BLOB)
        universe = row["caseUniverse"]
        self.assertEqual(universe["trainingSpectraTotal"], 2700)
        self.assertEqual(universe["validationAtmosphericSpectraTotal"], 768)
        self.assertEqual(universe["validationJohnsonVComparisonsTotal"], 2304)
        self.assertEqual(universe["totalCaseCount"], 3468)
        self.assertEqual(universe["totalShardCount"], 99)
        gates = row["acceptanceGates"]
        self.assertEqual(gates["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(gates["perFamilyRmsDeltaAvMag"], 0.01)
        self.assertFalse(row["scientificExecutionAuthorizedByThisReview"])
        self.assertFalse(row["authorizationCreatedByThisReview"])
        self.assertFalse(row["dispatchCreatedByThisReview"])
        self.assertFalse(row["githubRerunPermitted"])
        self.assertFalse(row["solverRetryPermitted"])
        self.assertFalse(row["solverResumePermitted"])
        self.assertFalse(row["pandoraHoldoutAccessAllowed"])
        self.assertFalse(row["productionAuthorized"])


if __name__ == "__main__":
    unittest.main()
