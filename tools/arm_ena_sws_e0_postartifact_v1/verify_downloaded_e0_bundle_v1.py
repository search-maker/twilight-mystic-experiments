#!/usr/bin/env python3
"""Bind a downloaded ARM E0 artifact ZIP to its authorized GitHub digest.

This is result-blind control-plane ingest only. It verifies the run-envelope
receipt, hashes the downloaded ZIP before extraction, rejects unsafe archive
members, extracts only the exact sanitized E0 file set, and then delegates to
the existing sanitized artifact verifier. It never contacts ARM Live and never
authorizes Stage B, protected-result opening, MYSTIC, or science execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from verify_oneevent_e0_artifact_v1 import (
    REQUIRED_FILES,
    VerificationError as ArtifactVerificationError,
    verify as verify_artifact_dir,
)

AUTHORITY_COMMENT = 5575796491
FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"
FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
WORKFLOW_PATH = ".github/workflows/arm-ena-sws-e0-oneevent-auth-runtime-v1.yml"
ARTIFACT_NAME = "arm-ena-sws-e0-oneevent-auth-v1"
ENVELOPE_STATUS = "ARM_E0_AUTHORIZED_RUN_ENVELOPE_VERIFIED"
DIGEST_RE = re.compile(r"sha256:([0-9a-f]{64})\Z")
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 32 * 1024 * 1024


class BundleVerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise BundleVerificationError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {type(exc).__name__}")


def verify_envelope_receipt(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        fail("run-envelope receipt must be a JSON object")
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
        if payload.get(key) != expected:
            fail(f"run-envelope {key} mismatch: expected {expected!r}, got {payload.get(key)!r}")
    for key in ("run_id", "artifact_id"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            fail(f"run-envelope {key} must be a positive integer")
    digest = payload.get("artifact_digest")
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        fail("run-envelope artifact_digest is not canonical sha256:<64-hex>")
    return payload


def _canonical_member_name(name: str) -> str:
    if not name or "\\" in name:
        fail(f"non-canonical ZIP member name: {name!r}")
    p = PurePosixPath(name)
    if p.is_absolute() or "." in p.parts or ".." in p.parts:
        fail(f"unsafe ZIP member path: {name!r}")
    canonical = p.as_posix()
    if canonical != name or len(p.parts) != 1:
        fail(f"ZIP member must be a root-level canonical filename: {name!r}")
    return canonical


def validate_zip_members(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = zf.infolist()
    if not infos:
        fail("artifact ZIP is empty")
    names: list[str] = []
    casefolded: set[str] = set()
    total = 0
    for info in infos:
        if info.is_dir():
            fail(f"directory entry is forbidden in sanitized artifact ZIP: {info.filename!r}")
        name = _canonical_member_name(info.filename)
        if name in names:
            fail(f"duplicate ZIP member: {name}")
        folded = name.casefold()
        if folded in casefolded:
            fail(f"case-colliding ZIP member: {name}")
        names.append(name)
        casefolded.add(folded)
        if info.flag_bits & 0x1:
            fail(f"encrypted ZIP member is forbidden: {name}")
        mode = (info.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if file_type not in (0, stat.S_IFREG):
            fail(f"non-regular ZIP member is forbidden: {name}")
        if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
            fail(f"ZIP member exceeds sanitized size bound: {name}")
        total += info.file_size
        if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
            fail("artifact ZIP exceeds sanitized total uncompressed size bound")
    if set(names) != REQUIRED_FILES:
        missing = sorted(REQUIRED_FILES - set(names))
        extra = sorted(set(names) - REQUIRED_FILES)
        fail(f"artifact ZIP file set mismatch missing={missing} extra={extra}")
    return infos


def extract_validated_zip(zf: zipfile.ZipFile, infos: list[zipfile.ZipInfo], root: Path) -> None:
    for info in infos:
        target = root / info.filename
        with zf.open(info, "r") as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
        if target.stat().st_size != info.file_size:
            fail(f"extracted size mismatch for {info.filename}")


def verify_bundle(
    artifact_zip: Path,
    envelope_payload: Any,
    *,
    artifact_verifier: Callable[[Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    envelope = verify_envelope_receipt(envelope_payload)
    artifact_zip = artifact_zip.resolve()
    if not artifact_zip.is_file():
        fail(f"artifact ZIP does not exist: {artifact_zip}")
    digest_match = DIGEST_RE.fullmatch(str(envelope["artifact_digest"]))
    assert digest_match is not None
    expected_hex = digest_match.group(1)
    actual_hex = sha256_file(artifact_zip)
    if actual_hex != expected_hex:
        fail("downloaded artifact ZIP SHA-256 does not match authorized GitHub artifact digest")

    verifier = artifact_verifier if artifact_verifier is not None else verify_artifact_dir
    try:
        with zipfile.ZipFile(artifact_zip, "r") as zf:
            infos = validate_zip_members(zf)
            with tempfile.TemporaryDirectory(prefix="arm-e0-sanitized-") as tmp:
                root = Path(tmp)
                extract_validated_zip(zf, infos, root)
                try:
                    content = verifier(root)
                except ArtifactVerificationError as exc:
                    fail(f"sanitized content verifier refused artifact: {exc}")
    except zipfile.BadZipFile as exc:
        fail(f"invalid artifact ZIP: {exc}")

    if not isinstance(content, dict) or content.get("status") != "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED":
        fail("sanitized content verifier did not return its exact PASS receipt")
    for key in ("protected_variable_values_read", "raw_sws_files_retained", "stage_b_authorized", "heldout_radiance_opening_authorized"):
        if content.get(key) is not False:
            fail(f"sanitized content receipt {key} must remain false")

    return {
        "schema": 1,
        "status": "ARM_E0_DOWNLOADED_ZIP_AND_SANITIZED_CONTENT_VERIFIED",
        "authority_comment": AUTHORITY_COMMENT,
        "run_id": envelope["run_id"],
        "artifact_id": envelope["artifact_id"],
        "artifact_name": ARTIFACT_NAME,
        "artifact_digest": envelope["artifact_digest"],
        "downloaded_zip_sha256": actual_hex,
        "archive_file_count": len(REQUIRED_FILES),
        "content_status": content["status"],
        "e0_disposition": content.get("e0_disposition"),
        "e0_blind_candidate_pass": content.get("e0_blind_candidate_pass"),
        "protected_results_opened": False,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact-zip", type=Path, required=True)
    ap.add_argument("--run-envelope-receipt", type=Path, required=True)
    ap.add_argument("--receipt-out", type=Path)
    args = ap.parse_args()
    try:
        result = verify_bundle(args.artifact_zip, read_json(args.run_envelope_receipt))
    except BundleVerificationError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True, indent=2))
        return 2
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.receipt_out is not None:
        args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
