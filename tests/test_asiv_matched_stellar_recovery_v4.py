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
EXPECTED_AUTH_BLOB = "d2c82687e558f16a5e23da5f67921e1282952eec"
EXPECTED_SCIENCE_BLOB = "1d36adb676cae115b141c8c085afb9e22e2142c3"
EXPECTED_CONTROL_BLOB = "5351b7000a7fb282520113dfababfa173f2beb00"


def git_blob_sha1(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], text=True).strip()


def load_helper():
    spec = importlib.util.spec_from_file_location("matched_stellar_read_retry_v4", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RecoveryV4EvidenceHandoffTests(unittest.TestCase):
    def test_exact_review_blobs_are_frozen_and_active_workflows_match_candidates(self):
        self.assertEqual(git_blob_sha1(HELPER), EXPECTED_HELPER_BLOB)
        self.assertEqual(git_blob_sha1(EVIDENCE), EXPECTED_EVIDENCE_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_REVIEW), EXPECTED_AUTH_BLOB)
        self.assertEqual(git_blob_sha1(AUTH_ACTIVE), EXPECTED_AUTH_BLOB)
        self.assertEqual(AUTH_ACTIVE.read_bytes(), AUTH_REVIEW.read_bytes())
        self.assertEqual(git_blob_sha1(SCIENCE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(git_blob_sha1(SCIENCE_ACTIVE), EXPECTED_SCIENCE_BLOB)
        self.assertEqual(SCIENCE_ACTIVE.read_bytes(), SCIENCE.read_bytes())
        self.assertEqual(git_blob_sha1(CONTRACT), EXPECTED_CONTROL_BLOB)

    def test_historical_evidence_is_exact_three_pre_solver_failures(self):
        row = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        prior = row["priorRuns"]
        self.assertEqual([x["runId"] for x in prior], [32848973816, 32868735547, 32874586374])
        self.assertEqual([x["runAttempt"] for x in prior], [1, 1, 1])
        self.assertEqual(prior[0]["failureClass"], "PRE_SOLVER_MICROMAMBA_JSON_SHAPE")
        self.assertTrue(prior[0]["matrixBuilt"])
        self.assertEqual(prior[0]["preflightArtifactId"], 9563491205)
        self.assertEqual(prior[1]["failureClass"], "READ_ONLY_GITHUB_API_TRANSIENT_502")
        self.assertFalse(prior[1]["matrixBuilt"])
        self.assertEqual(prior[1]["artifactCount"], 0)
        self.assertEqual(prior[2]["failureClass"], "READ_ONLY_GITHUB_API_TRANSIENT_502_EXHAUSTED_THREE_ATTEMPTS")
        self.assertEqual(prior[2]["readOnlyApiObservedHttpStatuses"], [502, 502, 502])
        self.assertEqual(prior[2]["readOnlyApiObservedBackoffSeconds"], [2, 4])
        self.assertTrue(prior[2]["authorizationIdentityGatePassed"])
        self.assertFalse(prior[2]["matrixBuilt"])
        self.assertFalse(prior[2]["opacArchiveFetchReached"])
        self.assertEqual(prior[2]["artifactCount"], 0)
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

    def test_helper_retries_three_consecutive_502s_without_mutation_then_succeeds(self):
        mod = load_helper()
        responses = [
            subprocess.CompletedProcess(["gh"], 1, b"", b"gh: Server Error (HTTP 502)\n"),
            subprocess.CompletedProcess(["gh"], 1, b"", b"gh: Server Error (HTTP 502)\n"),
            subprocess.CompletedProcess(["gh"], 1, b"", b"gh: Server Error (HTTP 502)\n"),
            subprocess.CompletedProcess(["gh"], 0, b"", b""),
        ]

        def fake_run(cmd, stdout, stderr, check):
            row = responses.pop(0)
            if row.returncode == 0:
                stdout.write(b'{"ok":true}\n')
            return row

        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(mod.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(mod.time, "sleep") as sleep:
            out = Path(td) / "result.json"
            audit = mod.run_read_only_gh_api(["repos/x/y/actions/runs/1"], out)
            self.assertEqual([x["httpStatus"] for x in audit["attempts"]], [502, 502, 502, None])
            self.assertEqual(audit["maxAttempts"], 8)
            self.assertEqual(audit["backoffSeconds"], [2, 4, 8, 16, 30, 30, 30])
            self.assertFalse(audit["writeMethodsPermitted"])
            self.assertFalse(audit["solverRetryPermitted"])
            self.assertFalse(audit["solverResumePermitted"])
            self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4, 8])

    def test_helper_policy_and_mutating_args_are_fail_closed(self):
        mod = load_helper()
        self.assertEqual(mod.TRANSIENT_HTTP_STATUSES, {502, 503, 504})
        self.assertEqual(mod.MAX_ATTEMPTS, 8)
        self.assertEqual(mod.BACKOFF_SECONDS, (2, 4, 8, 16, 30, 30, 30))
        for args in (["-X", "POST", "repos/x/y"], ["--method=PATCH", "repos/x/y"], ["-f", "state=open", "repos/x/y"], ["--input", "payload.json", "repos/x/y"]):
            with self.subTest(args=args), mock.patch.object(mod.subprocess, "run") as run:
                with self.assertRaises(SystemExit):
                    mod.run_read_only_gh_api(list(args), Path("unused"))
                run.assert_not_called()

    def test_control_contract_preserves_science_runtime_universe_and_gates(self):
        row = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(row["recoveryVersion"], 4)
        self.assertEqual(row["baseMainSha"], "fa43b87647bf59704f6e6fa99eed248655fe8bc3")
        self.assertEqual([x["runId"] for x in row["priorFailedRuns"]], [32848973816, 32868735547, 32874586374])
        self.assertEqual(row["historicalEvidenceHandoff"]["gitBlobSha1"], EXPECTED_EVIDENCE_BLOB)
        self.assertTrue(row["historicalEvidenceHandoff"]["liveVerificationOccursOnlyInAuthorizationReview"])
        self.assertTrue(row["historicalEvidenceHandoff"]["sciencePreflightMayNotRequeryHistoricalRunJobsOrArtifacts"])
        retry = row["readOnlyApiRetryPolicy"]
        self.assertEqual(retry["maxAttempts"], 8)
        self.assertEqual(retry["retryHttpStatuses"], [502, 503, 504])
        self.assertEqual(retry["backoffSeconds"], [2, 4, 8, 16, 30, 30, 30])
        self.assertFalse(retry["githubJobRerunPermitted"])
        self.assertFalse(retry["solverRetryPermitted"])
        self.assertFalse(retry["solverResumePermitted"])
        science = row["scienceBindings"]
        self.assertEqual(science["strictAuthorizationGateGitBlobSha1"], "9bbe4f8fe64f7f32dd3e3e69469a15b30f658dde")
        self.assertEqual(science["executionCandidateGitBlobSha1"], "ec433aa3a594311738a6f6aa2b339a7e33d43447")
        self.assertEqual(science["executionContractGitBlobSha1"], "f152befc00a8d7a098b210d1f1173d5bdeeb65e9")
        self.assertEqual(science["executionTransportGitBlobSha1"], "2bfb94758e048868aa0a6009a654e0805af35f0a")
        self.assertEqual(science["validationAssemblerGitBlobSha1"], "9492ca0297136654bdacc81bf0fa2c90d63108b9")
        self.assertEqual(science["batchOrchestrationGitBlobSha1"], "d1c4f156967e592ee41f4c1a829e7d551a4f7ea7")
        universe = row["caseUniverse"]
        self.assertEqual(universe["trainingSpectraTotal"], 2700)
        self.assertEqual(universe["validationAtmosphericSpectraTotal"], 768)
        self.assertEqual(universe["validationJohnsonVComparisonsTotal"], 2304)
        self.assertEqual(universe["totalCaseCount"], 3468)
        self.assertEqual(universe["totalShardCount"], 99)
        gates = row["acceptanceGates"]
        self.assertEqual(gates["perFamilyMaxAbsDeltaAvMag"], 0.025)
        self.assertEqual(gates["perFamilyRmsDeltaAvMag"], 0.01)
        self.assertTrue(gates["everyFamilyMustPassSeparately"])
        self.assertFalse(gates["postResultThresholdRelaxationPermitted"])
        self.assertFalse(gates["postResultKnotRetuningPermitted"])
        self.assertFalse(gates["postResultInterpolationRetuningPermitted"])
        runtime = row["runtimeIdentity"]
        self.assertEqual(runtime["packageSpec"], "rubin-libradtran=2.0.6=py312pl5321he9373c2_1")
        self.assertEqual(runtime["uvspecSha256"], "2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3")
        self.assertFalse(row["pandoraHoldoutAccessAllowed"])
        self.assertFalse(row["productionAuthorized"])
        self.assertFalse(row["scientificExecutionAuthorizedByThisReview"])

    def test_authorization_review_live_verifies_history_and_runs_both_strict_gates_without_solver(self):
        text = AUTH_REVIEW.read_text(encoding="utf-8")
        for rid in (32848973816, 32868735547, 32874586374):
            self.assertIn(f"actions/runs/${{RID}}", text)
        self.assertIn("HISTORICAL_PRE_SOLVER_EVIDENCE_LIVE_VERIFIED", text)
        self.assertIn("historicalPreSolverEvidenceVerified':True", text)
        self.assertIn("gate.validate_strict_authorization(auth)", text)
        self.assertIn("batch.validate_batch_authorization(auth)", text)
        self.assertIn("read_only_gh_api_retry_v4.py", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertNotIn("workflow_dispatch:", text)

    def test_science_consumes_receipt_without_historical_actions_api_requeries(self):
        text = SCIENCE.read_text(encoding="utf-8")
        for rid in (32848973816, 32868735547, 32874586374):
            self.assertNotIn(f"actions/runs/{rid}", text)
        self.assertIn('test "$GITHUB_RUN_NUMBER" = 1', text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn("historicalPreSolverEvidenceVerified", text)
        self.assertIn("actions/download-artifact@v4", text)
        self.assertIn("asiv-matched-stellar-authorization-review-recovery-v4", text)
        self.assertIn("asiv-matched-stellar-preflight-recovery-v4", text)
        self.assertIn("pattern: asiv-matched-stellar-shard-recovery-v4-*", text)
        self.assertIn("exactly 99 unique complete Recovery v4 shard artifact directories required", text)
        self.assertIn("execute_shard_strict", text)
        self.assertIn("allow_execution=True", text)
        self.assertIn("max-parallel: 8", text)
        self.assertIn("scientificCaseCount']=3468", text)
        self.assertIn("recoveryVersion']=4", text)
        self.assertNotIn("rerun-failed-jobs", text)
        self.assertNotIn("solverResumePerformed']=True", text)

    def test_shards_and_aggregate_have_no_manual_gh_api_artifact_transport(self):
        text = SCIENCE.read_text(encoding="utf-8")
        shards = text.split("\n  shards:\n", 1)[1].split("\n  aggregate:\n", 1)[0]
        aggregate = text.split("\n  aggregate:\n", 1)[1]
        self.assertNotIn("read_only_gh_api_retry_v4.py", shards)
        self.assertNotIn("gh api", shards)
        self.assertIn("actions/download-artifact@v4", shards)
        self.assertNotIn("read_only_gh_api_retry_v4.py", aggregate)
        self.assertNotIn("gh api", aggregate)
        self.assertIn("actions/download-artifact@v4", aggregate)
        self.assertIn("merge-multiple: false", aggregate)
        self.assertTrue(json.loads(CONTRACT.read_text(encoding="utf-8"))["artifactTransport"]["completeUniverseValidatorStillRequired"])


if __name__ == "__main__":
    unittest.main()
