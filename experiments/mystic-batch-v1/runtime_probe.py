#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "mystic-batch-v1"


class RuntimeProbeFailure(RuntimeError):
    pass


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(root: Path) -> tuple[str, int, int]:
    if not root.is_dir():
        raise RuntimeProbeFailure(f"data directory not found: {root}")
    digest = hashlib.sha256()
    file_count = 0
    byte_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content_hash = raw_sha256(path).encode("ascii")
        size = path.stat().st_size
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        digest.update(content_hash)
        file_count += 1
        byte_count += size
    if file_count == 0:
        raise RuntimeProbeFailure(f"data directory contains no files: {root}")
    return digest.hexdigest(), file_count, byte_count


def command_output_sha256(command: list[str]) -> tuple[str, str]:
    process = subprocess.run(command, check=False, capture_output=True)
    combined = process.stdout + process.stderr
    if process.returncode != 0:
        raise RuntimeProbeFailure(
            f"identity command failed with exit code {process.returncode}: {command!r}: {combined[:500]!r}"
        )
    return hashlib.sha256(combined).hexdigest(), combined.decode("utf-8", errors="replace").splitlines()[0:5].__repr__()


def build_report(
    uvspec: Path,
    data_dir: Path,
    atmosphere: Path,
    runtime_lock: Path,
    skip_help: bool = False,
) -> dict[str, Any]:
    for path, label in ((uvspec, "uvspec"), (atmosphere, "atmosphere"), (runtime_lock, "runtime lock")):
        if not path.is_file():
            raise RuntimeProbeFailure(f"{label} file not found: {path}")
    data_hash, file_count, byte_count = tree_sha256(data_dir)
    if skip_help:
        help_hash = "0" * 64
        help_preview = "skipped"
    else:
        help_hash, help_preview = command_output_sha256([str(uvspec.resolve()), "-h"])
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "RUNTIME_IDENTITY_CAPTURED",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
        "uvspecPath": str(uvspec.resolve()),
        "uvspecSha256": raw_sha256(uvspec),
        "uvspecHelpSha256": help_hash,
        "uvspecHelpPreview": help_preview,
        "libRadtranDataPath": str(data_dir.resolve()),
        "libRadtranDataTreeSha256": data_hash,
        "libRadtranDataFileCount": file_count,
        "libRadtranDataByteCount": byte_count,
        "atmospherePath": str(atmosphere.resolve()),
        "atmosphereSha256": raw_sha256(atmosphere),
        "runtimeLockPath": str(runtime_lock.resolve()),
        "runtimeLockRawSha256": raw_sha256(runtime_lock),
        "python": sys.version.split()[0],
        "pythonImplementation": platform.python_implementation(),
        "os": platform.system(),
        "osRelease": platform.release(),
        "architecture": platform.machine(),
        "runnerImage": os.environ.get("ImageOS"),
        "runnerArch": os.environ.get("RUNNER_ARCH"),
        "boundary": "runtime identity only; uvspec help may run, but no syntax check or scientific solver executes",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uvspec", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--runtime-lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-help", action="store_true")
    args = parser.parse_args()
    try:
        report = build_report(args.uvspec, args.data_dir, args.atmosphere, args.runtime_lock, args.skip_help)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump_json(report))
        print(dump_json(report), end="")
        return 0
    except Exception as exc:
        failure = {
            "schemaVersion": 1,
            "stageId": STAGE_ID,
            "status": "RUNTIME_IDENTITY_FAILURE",
            "scientificSolverExecuted": False,
            "reason": str(exc),
        }
        print(dump_json(failure), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
