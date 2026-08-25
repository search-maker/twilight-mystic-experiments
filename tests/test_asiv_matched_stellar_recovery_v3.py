import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v3"
HELPER = BASE / "read_only_gh_api_retry_v3.py"
EVIDENCE = BASE / "RUN_32868735547_PRE_SOLVER_FAILURE.review.json"
CONTRACT = BASE / "RECOVERY_CONTROL_CONTRACT.review.json"
SCIENCE = BASE / "science-workflow-v3.yml.review"
AUTH_REVIEW = BASE / "authorization-review-workflow-v3.yml.review"


def load_helper():
    spec = importlib.util.spec_from_file_location("matched_stellar_read_retry_v3", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RecoveryV3ReadOnlyApiTests(unittest.TestCase):
    def test_v2_failure_evidence_is_pre_solver_and_zero_artifact(self):
        row = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(row["runId"], 32868735547)
        self.assertEqual(row["runAttempt"], 1)
        self.assertEqual(row["failureClass"], "READ_ONLY_GITHUB_API_TRANSIENT_502")
        self.assertEqual(row["artifactCount"], 0)
        self.assertEqual(row["scientificShardArtifactCount"], 0)
        self.assertEqual(row["finalValidationArtifactCount"], 0)
        self.assertFalse(row["solverExecutionObserved"])
        self.assertFalse(row["matrixBuilt"])
        self.assertFalse(row["micromambaParserReached"])
        self.assertEqual(row["allowedReadOnlyRetryHttpStatuses"], [502, 503, 504])

    def test_502_then_success_retries_once_and_writes_audit(self):
        mod = load_helper()
        responses = [
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
            self.assertEqual(out.read_text(encoding="utf-8"), '{"ok":true}\n')
            self.assertEqual([x["httpStatus"] for x in audit["attempts"]], [502, None])
            sleep.assert_called_once_with(2)
            stored = json.loads(Path(str(out) + ".read-audit.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["maxAttempts"], 3)
            self.assertFalse(stored["writeMethodsPermitted"])

    def test_non_transient_500_fails_without_retry(self):
        mod = load_helper()
        row = subprocess.CompletedProcess(["gh"], 1, b"", b"gh: Server Error (HTTP 500)\n")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(mod.subprocess, "run", return_value=row), \
             mock.patch.object(mod.time, "sleep") as sleep:
            with self.assertRaises(SystemExit):
                mod.run_read_only_gh_api(["repos/x/y/actions/runs/1"], Path(td) / "out.json")
            sleep.assert_not_called()

    def test_mutating_gh_api_options_are_rejected_before_subprocess(self):
        mod = load_helper()
        forbidden = [
            ["-X", "POST", "repos/x/y"],
            ["--method=PATCH", "repos/x/y"],
            ["-f", "state=open", "repos/x/y"],
            ["--field=name=value", "repos/x/y"],
            ["--input", "payload.json", "repos/x/y"],
        ]
        for args in forbidden:
            with self.subTest(args=args), mock.patch.object(mod.subprocess, "run") as run:
                with self.assertRaises(SystemExit):
                    mod.run_read_only_gh_api(args, Path("unused"))
                run.assert_not_called()

    def test_transient_status_set_is_frozen(self):
        mod = load_helper()
        self.assertEqual(mod.TRANSIENT_HTTP_STATUSES, {502, 503, 504})

    def test_control_contract_preserves_science_universe_and_gates(self):
        row = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(row["recoveryVersion"], 3)
        self.assertEqual([x["runId"] for x in row["priorFailedRuns"]], [32848973816, 32868735547])
        retry = row["readOnlyApiRetryPolicy"]
        self.assertTrue(retry["readOnlyGetOnly"])
        self.assertEqual(retry["maxAttempts"], 3)
        self.assertEqual(retry["retryHttpStatuses"], [502, 503, 504])
        self.assertFalse(retry["githubJobRerunPermitted"])
        self.assertFalse(retry["solverRetryPermitted"])
        self.assertFalse(retry["solverResumePermitted"])
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

    def test_science_candidate_routes_github_api_reads_only_through_helper(self):
        text = SCIENCE.read_text(encoding="utf-8")
        self.assertNotIn("gh api ", text)
        self.assertIn("read_only_gh_api_retry_v3.py", text)
        self.assertIn("Build exact frozen 99-shard matrix", text)
        self.assertIn("Execute exactly one frozen shard with no retry or resume", text)
        self.assertIn("batch.get('totalCaseCount')!=3468", text)
        self.assertIn("universe.get('validationJohnsonVComparisonsTotal')!=2304", text)
        self.assertIn("exactly 99 unique complete Recovery v3 shard artifacts required", text)
        self.assertIn("artifact digest mismatch", text)
        self.assertIn("micromamba_list_parser_v2.py", text)
        self.assertNotIn("rerun-failed-jobs", text)
        self.assertNotIn("rerun_workflow", text)

    def test_authorization_review_candidate_is_nonexecuting_and_runs_strict_gates(self):
        text = AUTH_REVIEW.read_text(encoding="utf-8")
        self.assertIn("AUTHORIZATION_REVIEW_PASS_NO_DISPATCH", text)
        self.assertIn("scientificExecutionPerformed':False", text)
        self.assertIn("solverExecutionPerformed':False", text)
        self.assertIn("dispatchPerformed':False", text)
        self.assertIn("asiv-matched-stellar-transport-v1-execution-authorization", text)
        self.assertIn("asiv-matched-stellar-transport-recovery-v3-authorization", text)
        self.assertIn("gate.validate_strict_authorization(auth)", text)
        self.assertIn("batch.validate_batch_authorization(auth)", text)
        self.assertNotIn("uvspec", text)
        self.assertNotIn("execute_shard_strict", text)
        self.assertNotIn("workflow_dispatch", text)


if __name__ == "__main__":
    unittest.main()
