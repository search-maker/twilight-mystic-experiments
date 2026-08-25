import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v3/read_only_gh_api_retry_v3.py"
EVIDENCE = ROOT / "review/asiv-matched-stellar-transport-v1/recovery-v3/RUN_32868735547_PRE_SOLVER_FAILURE.review.json"


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


if __name__ == "__main__":
    unittest.main()
