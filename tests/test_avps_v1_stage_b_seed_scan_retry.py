from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "review/avps-v1-ordinal40-stage-b-science-recovery-v1/retry_repository_global_seed_scan.py"

spec = importlib.util.spec_from_file_location("avps_stage_b_seed_retry_tested", HELPER)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot import Stage-B seed retry helper")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class AvpsStageBSeedScanRetry(unittest.TestCase):
    def make_scanner(self, root: Path) -> Path:
        p = root / "scanner.py"
        p.write_text("print('fake scanner')\n", encoding="utf-8")
        return p

    def test_frozen_policy_constants(self):
        self.assertEqual(mod.MAX_ATTEMPTS, 3)
        self.assertEqual(mod.RETRY_DELAYS_SECONDS, (60, 120))
        self.assertEqual(mod.RETRY_NEEDLE, "HTTP Error 429: Too Many Requests")
        self.assertEqual(mod.EXPECTED_SCANNER_BLOB_SHA1, "1cfb54e3ed96ff57f84739b4e4393544c49e2d32")

    def test_one_429_then_success_retries_once_and_removes_partial_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"
            calls = []; sleeps = []
            expected = blob_sha1(scanner)

            def runner(cmd, **kwargs):
                calls.append(list(cmd))
                output = Path(cmd[cmd.index("--output") + 1])
                if len(calls) == 1:
                    output.write_text("partial", encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 1, b"", b"urllib.error.HTTPError: HTTP Error 429: Too Many Requests\n")
                self.assertFalse(output.exists(), "partial output must be deleted before retry")
                output.write_text('{"status":"PASS"}\n', encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, b"ok\n", b"")

            audit = mod.run_seed_scan_with_429_retry(scanner, out, ["--repository", "o/r"], expected_blob_sha1=expected, runner=runner, sleep_fn=sleeps.append)
            self.assertEqual(len(calls), 2)
            self.assertEqual(sleeps, [60])
            self.assertEqual([r["exact429Observed"] for r in audit["attempts"]], [True, False])
            self.assertTrue(out.is_file())
            self.assertTrue(out.with_name(out.name + ".retry-audit.json").is_file())

    def test_two_429s_then_success_uses_60_then_120_seconds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"
            calls = []; sleeps = []; expected = blob_sha1(scanner)

            def runner(cmd, **kwargs):
                calls.append(1)
                output = Path(cmd[cmd.index("--output") + 1])
                if len(calls) < 3:
                    output.write_text("partial", encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 1, b"", b"HTTP Error 429: Too Many Requests")
                self.assertFalse(output.exists())
                output.write_text('{}\n', encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, b"", b"")

            mod.run_seed_scan_with_429_retry(scanner, out, ["--repository", "o/r"], expected_blob_sha1=expected, runner=runner, sleep_fn=sleeps.append)
            self.assertEqual(len(calls), 3)
            self.assertEqual(sleeps, [60, 120])

    def test_non_429_failure_is_never_retried(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"; calls = []; sleeps = []
            expected = blob_sha1(scanner)

            def runner(cmd, **kwargs):
                calls.append(1)
                return subprocess.CompletedProcess(cmd, 2, b"", b"seed collision detected")

            with self.assertRaisesRegex(mod.SeedScanRetryRefusal, "non-retryable non-429"):
                mod.run_seed_scan_with_429_retry(scanner, out, ["--repository", "o/r"], expected_blob_sha1=expected, runner=runner, sleep_fn=sleeps.append)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sleeps, [])

    def test_other_http_status_is_never_retried(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"; calls = []; sleeps = []
            expected = blob_sha1(scanner)

            def runner(cmd, **kwargs):
                calls.append(1)
                return subprocess.CompletedProcess(cmd, 1, b"", b"HTTP Error 503: Service Unavailable")

            with self.assertRaises(mod.SeedScanRetryRefusal):
                mod.run_seed_scan_with_429_retry(scanner, out, ["--repository", "o/r"], expected_blob_sha1=expected, runner=runner, sleep_fn=sleeps.append)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sleeps, [])

    def test_third_429_is_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"; calls = []; sleeps = []
            expected = blob_sha1(scanner)

            def runner(cmd, **kwargs):
                calls.append(1)
                return subprocess.CompletedProcess(cmd, 1, b"", b"HTTP Error 429: Too Many Requests")

            with self.assertRaisesRegex(mod.SeedScanRetryRefusal, "after 3 attempts"):
                mod.run_seed_scan_with_429_retry(scanner, out, ["--repository", "o/r"], expected_blob_sha1=expected, runner=runner, sleep_fn=sleeps.append)
            self.assertEqual(len(calls), 3)
            self.assertEqual(sleeps, [60, 120])

    def test_caller_cannot_override_output_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"; expected = blob_sha1(scanner)
            with self.assertRaisesRegex(mod.SeedScanRetryRefusal, "must not supply --output"):
                mod.run_seed_scan_with_429_retry(scanner, out, ["--output", "evil.json"], expected_blob_sha1=expected)

    def test_scanner_byte_drift_fails_before_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); scanner = self.make_scanner(root); out = root / "out.json"
            with self.assertRaisesRegex(mod.SeedScanRetryRefusal, "scanner byte drift"):
                mod.run_seed_scan_with_429_retry(scanner, out, ["--repository", "o/r"], expected_blob_sha1="0" * 40)


if __name__ == "__main__":
    unittest.main()
