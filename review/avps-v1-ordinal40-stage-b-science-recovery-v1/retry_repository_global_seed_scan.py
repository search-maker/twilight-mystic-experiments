#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

EXPECTED_SCANNER_BLOB_SHA1 = "1cfb54e3ed96ff57f84739b4e4393544c49e2d32"
MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (60, 120)
RETRY_NEEDLE = "HTTP Error 429: Too Many Requests"


class SeedScanRetryRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _validate_scanner(scanner: Path, expected_blob_sha1: str) -> None:
    if not scanner.is_file():
        raise SeedScanRetryRefusal(f"frozen repository-global seed scanner missing: {scanner}")
    got = git_blob_sha1(scanner)
    if got != expected_blob_sha1:
        raise SeedScanRetryRefusal(
            f"frozen repository-global seed scanner byte drift: expected={expected_blob_sha1} observed={got}"
        )


def _validate_args(scanner_args: Sequence[str]) -> None:
    if "--output" in scanner_args:
        raise SeedScanRetryRefusal("caller must not supply --output; retry wrapper owns output identity")


def run_seed_scan_with_429_retry(
    scanner: Path,
    output_path: Path,
    scanner_args: Sequence[str],
    *,
    expected_blob_sha1: str = EXPECTED_SCANNER_BLOB_SHA1,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict:
    """Run the frozen read-only seed scanner, retrying only exact HTTP 429 acquisition failures.

    This is orchestration-only metadata acquisition recovery. It never relaxes scanner semantics,
    never retries a successful/semantic scanner refusal, and never executes scientific code.
    """
    _validate_scanner(scanner, expected_blob_sha1)
    _validate_args(scanner_args)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path = output_path.with_name(output_path.name + ".retry-audit.json")
    attempts: list[dict] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        for stale in (output_path, audit_path):
            try:
                stale.unlink()
            except FileNotFoundError:
                pass

        cmd = [sys.executable, str(scanner), *scanner_args, "--output", str(output_path)]
        proc = runner(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        stdout_text = (proc.stdout or b"").decode("utf-8", errors="replace")
        stderr_text = (proc.stderr or b"").decode("utf-8", errors="replace")
        is_429 = RETRY_NEEDLE in stderr_text
        attempts.append(
            {
                "attempt": attempt,
                "returnCode": int(proc.returncode),
                "exact429Observed": bool(is_429),
                "outputPresentAfterAttempt": output_path.exists(),
            }
        )

        if proc.returncode == 0:
            if not output_path.is_file():
                raise SeedScanRetryRefusal("seed scanner exited success without required output")
            audit = {
                "schemaVersion": 1,
                "status": "FROZEN_REPOSITORY_GLOBAL_SEED_SCAN_SUCCESS_WITH_429_ONLY_ACQUISITION_RETRY",
                "scannerGitBlobSha1": expected_blob_sha1,
                "maximumAttempts": MAX_ATTEMPTS,
                "retryNeedle": RETRY_NEEDLE,
                "retryDelaysSeconds": list(RETRY_DELAYS_SECONDS),
                "attempts": attempts,
                "non429FailuresRetryable": False,
                "scientificExecutionPerformed": False,
                "solverExecutionPerformed": False,
            }
            audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if stdout_text:
                sys.stdout.write(stdout_text)
            return audit

        try:
            output_path.unlink()
        except FileNotFoundError:
            pass

        if not is_429:
            if stdout_text:
                sys.stdout.write(stdout_text)
            if stderr_text:
                sys.stderr.write(stderr_text)
            raise SeedScanRetryRefusal(
                f"repository-global seed scan failed with non-retryable non-429 status on attempt {attempt}"
            )

        if attempt == MAX_ATTEMPTS:
            if stdout_text:
                sys.stdout.write(stdout_text)
            if stderr_text:
                sys.stderr.write(stderr_text)
            raise SeedScanRetryRefusal(
                f"repository-global seed scan still returned exact HTTP 429 after {MAX_ATTEMPTS} attempts"
            )

        delay = RETRY_DELAYS_SECONDS[attempt - 1]
        print(
            f"AVPS_READ_ONLY_SEED_METADATA_429_RETRY attempt={attempt} next_delay_seconds={delay}",
            file=sys.stderr,
        )
        sleep_fn(delay)

    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scanner", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("scanner_args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()
    args = list(ns.scanner_args)
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        raise SystemExit("repository-global seed scanner arguments are required")
    try:
        run_seed_scan_with_429_retry(Path(ns.scanner), Path(ns.output), args)
    except SeedScanRetryRefusal as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
