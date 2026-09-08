#!/usr/bin/env python3
"""Bind downloaded ARM E0 artifact ZIP bytes to GitHub's canonical digest.

This is a result-blind, pre-extraction control-plane gate. It never opens the ZIP,
contacts ARM Live, reads credentials, or authorizes protected/science work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

AUTHORITY_COMMENT = 5575796491
FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"
FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
WORKFLOW_PATH = ".github/workflows/arm-ena-sws-e0-oneevent-auth-runtime-v1.yml"
ARTIFACT_NAME = "arm-ena-sws-e0-oneevent-auth-v1"
ENVELOPE_STATUS = "ARM_E0_AUTHORIZED_RUN_ENVELOPE_VERIFIED"
STATUS = "ARM_E0_DOWNLOADED_ARTIFACT_ZIP_DIGEST_VERIFIED"
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
ENVELOPE_ALLOWED_KEYS = {
    "schema",
    "status",
    "authority_comment",
    "run_id",
    "run_attempt",
    "event",
    "execution_branch",
    "execution_head",
    "workflow_path",
    "artifact_id",
    "artifact_name",
    "artifact_digest",
    "duplicate_e0_dispatches",
    "protected_results_opened",
    "stage_b_authorized",
    "heldout_radiance_opening_authorized",
    "science_execution_authorized",
}


class ZipDigestVerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ZipDigestVerificationError(message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {type(exc).__name__}")


def _require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{where} must be a JSON object")
    return value


def _positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        fail(f"{where} must be a positive integer")
    return value


def verify_envelope_receipt(payload: Any) -> dict[str, Any]:
    receipt = _require_object(payload, "run-envelope receipt")
    unknown = set(receipt) - ENVELOPE_ALLOWED_KEYS
    missing = ENVELOPE_ALLOWED_KEYS - set(receipt)
    if unknown:
        fail(f"run-envelope receipt has unregistered keys {sorted(unknown)}")
    if missing:
        fail(f"run-envelope receipt is missing required keys {sorted(missing)}")

    exact = {
        "schema": 1,
        "status": ENVELOPE_STATUS,
        "authority_comment": AUTHORITY_COMMENT,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": FROZEN_BRANCH,
        "execution_head": FROZEN_HEAD,
        "workflow_path": WORKFLOW_PATH,
        "artifact_name": ARTIFACT_NAME,
        "duplicate_e0_dispatches": 0,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }
    for key, expected in exact.items():
        if receipt.get(key) != expected:
            fail(f"run-envelope {key} mismatch: expected {expected!r}, got {receipt.get(key)!r}")

    _positive_int(receipt.get("run_id"), "run-envelope run_id")
    _positive_int(receipt.get("artifact_id"), "run-envelope artifact_id")
    digest = receipt.get("artifact_digest")
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        fail("run-envelope artifact_digest must be canonical lowercase sha256:<64hex>")
    return receipt


def sha256_file_bytes(path: Path) -> tuple[int, str]:
    if path.is_symlink():
        fail("artifact ZIP path must not be a symlink")
    try:
        if not path.is_file():
            fail("artifact ZIP path must be a regular file")
        size = path.stat().st_size
    except ZipDigestVerificationError:
        raise
    except Exception as exc:
        fail(f"cannot stat artifact ZIP: {type(exc).__name__}")
    if size <= 0:
        fail("artifact ZIP must contain positive bytes")

    digest = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except Exception as exc:
        fail(f"cannot read artifact ZIP bytes: {type(exc).__name__}")
    return size, "sha256:" + digest.hexdigest()


def verify_downloaded_zip(envelope_payload: Any, artifact_zip: Path) -> dict[str, Any]:
    envelope = verify_envelope_receipt(envelope_payload)
    size, actual_digest = sha256_file_bytes(artifact_zip)
    expected_digest = str(envelope["artifact_digest"])
    if actual_digest != expected_digest:
        fail(
            "downloaded artifact ZIP SHA-256 does not match GitHub canonical digest: "
            f"expected {expected_digest}, got {actual_digest}"
        )

    return {
        "schema": 1,
        "status": STATUS,
        "authority_comment": AUTHORITY_COMMENT,
        "run_id": envelope["run_id"],
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": FROZEN_BRANCH,
        "execution_head": FROZEN_HEAD,
        "workflow_path": WORKFLOW_PATH,
        "artifact_id": envelope["artifact_id"],
        "artifact_name": ARTIFACT_NAME,
        "github_artifact_digest": expected_digest,
        "downloaded_zip_size_bytes": size,
        "downloaded_zip_sha256": actual_digest,
        "zip_contents_inspected": False,
        "zip_extracted": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-envelope-json", type=Path, required=True)
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_downloaded_zip(read_json(args.run_envelope_json), args.artifact_zip)
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
