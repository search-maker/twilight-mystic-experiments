from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Any


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_process_group(
    command: list[str],
    text: str,
    cwd: Path,
    timeout: int,
    *,
    sigterm_grace_seconds: int = 5,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if sigterm_grace_seconds <= 0:
        raise ValueError("sigterm grace must be positive")

    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(input=text, timeout=timeout)
        return {
            "exitCode": proc.returncode,
            "timedOut": False,
            "stdout": stdout,
            "stderr": stderr,
            "processGroupIsolated": True,
            "processGroupTerminationAttempted": False,
            "sigkillFallbackUsed": False,
        }
    except subprocess.TimeoutExpired as exc:
        partial_stdout = _text(exc.stdout)
        partial_stderr = _text(exc.stderr)
        sigkill_used = False
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=sigterm_grace_seconds)
        except subprocess.TimeoutExpired as exc2:
            partial_stdout += _text(exc2.stdout)
            partial_stderr += _text(exc2.stderr)
            sigkill_used = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        return {
            "exitCode": None,
            "timedOut": True,
            "stdout": partial_stdout + _text(stdout),
            "stderr": partial_stderr + _text(stderr),
            "processGroupIsolated": True,
            "processGroupTerminationAttempted": True,
            "sigkillFallbackUsed": sigkill_used,
        }
