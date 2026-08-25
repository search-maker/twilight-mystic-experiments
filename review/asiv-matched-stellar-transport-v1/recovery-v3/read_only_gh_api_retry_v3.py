#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TRANSIENT_HTTP_STATUSES = {502, 503, 504}
FORBIDDEN_EXACT = {
    "-X",
    "--method",
    "-f",
    "-F",
    "--field",
    "--raw-field",
    "--input",
}
FORBIDDEN_PREFIXES = (
    "-X",
    "--method=",
    "-f",
    "-F",
    "--field=",
    "--raw-field=",
    "--input=",
)
HTTP_RE = re.compile(r"HTTP\s+(\d{3})")


def _reject_non_read_only_args(args: list[str]) -> None:
    for token in args:
        if token in FORBIDDEN_EXACT:
            raise SystemExit(f"non-read-only gh api option forbidden: {token}")
        if any(token.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            raise SystemExit(f"non-read-only gh api option forbidden: {token}")


def _extract_http_status(stderr_text: str) -> int | None:
    matches = HTTP_RE.findall(stderr_text)
    return int(matches[-1]) if matches else None


def run_read_only_gh_api(
    gh_api_args: list[str],
    output_path: Path,
    *,
    max_attempts: int = 3,
    sleep_seconds: tuple[int, ...] = (2, 4),
) -> dict:
    if max_attempts != 3:
        raise SystemExit("Recovery v3 freezes max_attempts=3")
    _reject_non_read_only_args(gh_api_args)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    attempts: list[dict] = []

    for attempt in range(1, max_attempts + 1):
        tmp = output_path.with_name(output_path.name + f".attempt-{attempt}.tmp")
        with tmp.open("wb") as stdout:
            proc = subprocess.run(
                ["gh", "api", *gh_api_args],
                stdout=stdout,
                stderr=subprocess.PIPE,
                check=False,
            )
        stderr_text = proc.stderr.decode("utf-8", errors="replace")
        status = _extract_http_status(stderr_text)
        attempts.append(
            {
                "attempt": attempt,
                "returnCode": proc.returncode,
                "httpStatus": status,
            }
        )
        if proc.returncode == 0:
            os.replace(tmp, output_path)
            audit = {
                "schemaVersion": 1,
                "status": "READ_ONLY_GITHUB_API_SUCCESS",
                "maxAttempts": 3,
                "transientRetryStatuses": sorted(TRANSIENT_HTTP_STATUSES),
                "attempts": attempts,
                "writeMethodsPermitted": False,
            }
            output_path.with_name(output_path.name + ".read-audit.json").write_text(
                json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            return audit

        try:
            tmp.unlink()
        except FileNotFoundError:
            pass

        retryable = status in TRANSIENT_HTTP_STATUSES
        if not retryable or attempt == max_attempts:
            sys.stderr.write(stderr_text)
            raise SystemExit(proc.returncode or 1)

        delay = sleep_seconds[attempt - 1]
        print(
            f"READ_ONLY_GITHUB_API_RETRY attempt={attempt} http={status} next_delay_seconds={delay}",
            file=sys.stderr,
        )
        time.sleep(delay)

    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("gh_api_args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()
    args = list(ns.gh_api_args)
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        raise SystemExit("gh api arguments are required")
    run_read_only_gh_api(args, Path(ns.output))


if __name__ == "__main__":
    main()
