#!/usr/bin/env python3
"""Safely extract the digest-bound sanitized ARM E0 artifact ZIP.

This gate runs only after the outer archive bytes have been bound to GitHub's
canonical artifact digest.  It validates ZIP structure and extracts the exact
closed seven-file sanitized package without parsing any file content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

AUTHORITY_COMMENT = 5575796491
FROZEN_BRANCH = "review/arm-ena-sws-v1-stage0"
FROZEN_HEAD = "b8671665a2bf8fe9972b8cb48492abcfa6765140"
WORKFLOW_PATH = ".github/workflows/arm-ena-sws-e0-oneevent-auth-runtime-v1.yml"
ARTIFACT_NAME = "arm-ena-sws-e0-oneevent-auth-v1"
DIGEST_STATUS = "ARM_E0_DOWNLOADED_ARTIFACT_ZIP_DIGEST_VERIFIED"
STATUS = "ARM_E0_SANITIZED_ARTIFACT_ZIP_SAFELY_EXTRACTED"
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
ALLOWED_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
REQUIRED_FILES = {
    "ena_sws_e0_event_universe.csv",
    "ena_sws_e0_query_manifest.jsonl",
    "ena_sws_e0_stream_ledger.jsonl",
    "ena_sws_e0_stream_provenance.jsonl",
    "ena_sws_e0_stream_schema.jsonl",
    "ena_sws_e0_stream_summary.json",
    "probe_receipt.json",
}
DIGEST_RECEIPT_KEYS = {
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
    "github_artifact_digest",
    "downloaded_zip_size_bytes",
    "downloaded_zip_sha256",
    "zip_contents_inspected",
    "zip_extracted",
    "protected_results_opened",
    "stage_b_authorized",
    "heldout_radiance_opening_authorized",
    "science_execution_authorized",
}


class SafeExtractionError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise SafeExtractionError(message)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {type(exc).__name__}")


def _positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        fail(f"{where} must be a positive integer")
    return value


def verify_digest_receipt(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        fail("ZIP-digest receipt must be a JSON object")
    unknown = set(payload) - DIGEST_RECEIPT_KEYS
    missing = DIGEST_RECEIPT_KEYS - set(payload)
    if unknown:
        fail(f"ZIP-digest receipt has unregistered keys {sorted(unknown)}")
    if missing:
        fail(f"ZIP-digest receipt is missing required keys {sorted(missing)}")

    exact = {
        "schema": 1,
        "status": DIGEST_STATUS,
        "authority_comment": AUTHORITY_COMMENT,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": FROZEN_BRANCH,
        "execution_head": FROZEN_HEAD,
        "workflow_path": WORKFLOW_PATH,
        "artifact_name": ARTIFACT_NAME,
        "zip_contents_inspected": False,
        "zip_extracted": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }
    for key, expected in exact.items():
        if payload.get(key) != expected:
            fail(f"ZIP-digest receipt {key} mismatch: expected {expected!r}, got {payload.get(key)!r}")

    _positive_int(payload.get("run_id"), "ZIP-digest receipt run_id")
    _positive_int(payload.get("artifact_id"), "ZIP-digest receipt artifact_id")
    size = _positive_int(payload.get("downloaded_zip_size_bytes"), "ZIP-digest receipt downloaded_zip_size_bytes")
    digest = payload.get("downloaded_zip_sha256")
    github_digest = payload.get("github_artifact_digest")
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        fail("ZIP-digest receipt downloaded_zip_sha256 is not canonical")
    if not isinstance(github_digest, str) or DIGEST_RE.fullmatch(github_digest) is None:
        fail("ZIP-digest receipt github_artifact_digest is not canonical")
    if digest != github_digest:
        fail("ZIP-digest receipt does not preserve GitHub digest equality")
    if size > MAX_TOTAL_BYTES * 4:
        # Outer archive may be compressed, but an unexpectedly enormous download
        # is not accepted by this narrow one-event control-plane package.
        fail("ZIP-digest receipt archive size exceeds bounded one-event envelope")
    return payload


def sha256_file(path: Path) -> tuple[int, str]:
    if path.is_symlink() or not path.is_file():
        fail("artifact ZIP must remain a non-symlink regular file")
    size = path.stat().st_size
    if size <= 0:
        fail("artifact ZIP must contain positive bytes")
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(block)
    except Exception as exc:
        fail(f"cannot re-read artifact ZIP bytes: {type(exc).__name__}")
    return size, "sha256:" + h.hexdigest()


def canonical_member_name(info: zipfile.ZipInfo) -> str:
    name = info.filename
    if not isinstance(name, str) or not name or "\\" in name or name.endswith("/"):
        fail(f"ZIP contains a directory or non-canonical member: {name!r}")
    p = PurePosixPath(name)
    if p.is_absolute() or len(p.parts) != 1 or p.name != name or "." in p.parts or ".." in p.parts:
        fail(f"ZIP member path is not a canonical root filename: {name!r}")
    if name not in REQUIRED_FILES:
        fail(f"ZIP contains unexpected sanitized member: {name!r}")
    if info.flag_bits & 0x1:
        fail(f"encrypted ZIP member is forbidden: {name!r}")
    if info.compress_type not in ALLOWED_COMPRESSION:
        fail(f"unsupported ZIP compression method for {name!r}: {info.compress_type}")
    mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(mode)
    if file_type and file_type != stat.S_IFREG:
        fail(f"non-regular ZIP member is forbidden: {name!r}")
    if info.file_size < 0 or info.file_size > MAX_FILE_BYTES:
        fail(f"ZIP member exceeds bounded uncompressed size: {name!r}")
    if info.compress_size < 0:
        fail(f"ZIP member has invalid compressed size: {name!r}")
    return name


def validate_archive_structure(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) != len(REQUIRED_FILES):
        fail(f"ZIP must contain exactly {len(REQUIRED_FILES)} members, found {len(infos)}")
    names: list[str] = []
    total = 0
    for info in infos:
        name = canonical_member_name(info)
        if name in names:
            fail(f"duplicate ZIP member is forbidden: {name!r}")
        names.append(name)
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            fail("ZIP total uncompressed size exceeds bounded one-event package limit")
    if set(names) != REQUIRED_FILES:
        fail(f"ZIP closed member set mismatch: missing={sorted(REQUIRED_FILES - set(names))}")
    return infos


def extract_safely(digest_receipt: Any, artifact_zip: Path, output_dir: Path) -> dict[str, Any]:
    receipt = verify_digest_receipt(digest_receipt)
    size, digest = sha256_file(artifact_zip)
    if size != receipt["downloaded_zip_size_bytes"] or digest != receipt["downloaded_zip_sha256"]:
        fail("artifact ZIP changed after outer-byte digest verification")

    if output_dir.is_symlink() or output_dir.exists():
        fail("output directory must be a new, non-existent path")
    parent = output_dir.parent
    if parent.is_symlink() or not parent.exists() or not parent.is_dir():
        fail("output directory parent must be an existing non-symlink directory")

    created = False
    try:
        with zipfile.ZipFile(artifact_zip, "r") as archive:
            infos = validate_archive_structure(archive)
            output_dir.mkdir(mode=0o700)
            created = True
            for info in infos:
                name = info.filename
                target = output_dir / name
                written = 0
                with archive.open(info, "r") as src, target.open("xb") as dst:
                    while True:
                        block = src.read(1024 * 1024)
                        if not block:
                            break
                        written += len(block)
                        if written > info.file_size or written > MAX_FILE_BYTES:
                            fail(f"ZIP member expanded beyond declared/bounded size: {name!r}")
                        dst.write(block)
                if written != info.file_size:
                    fail(f"ZIP member extracted size mismatch: {name!r}")
        extracted = sorted(path.name for path in output_dir.iterdir())
        if extracted != sorted(REQUIRED_FILES) or any(not path.is_file() or path.is_symlink() for path in output_dir.iterdir()):
            fail("post-extraction filesystem is not the exact closed regular-file set")
    except SafeExtractionError:
        if created:
            shutil.rmtree(output_dir, ignore_errors=True)
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        if created:
            shutil.rmtree(output_dir, ignore_errors=True)
        fail(f"safe ZIP extraction failed closed: {type(exc).__name__}")

    return {
        "schema": 1,
        "status": STATUS,
        "authority_comment": AUTHORITY_COMMENT,
        "run_id": receipt["run_id"],
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "execution_branch": FROZEN_BRANCH,
        "execution_head": FROZEN_HEAD,
        "workflow_path": WORKFLOW_PATH,
        "artifact_id": receipt["artifact_id"],
        "artifact_name": ARTIFACT_NAME,
        "downloaded_zip_sha256": digest,
        "archive_member_count": len(REQUIRED_FILES),
        "extracted_file_names": sorted(REQUIRED_FILES),
        "zip_contents_inspected": True,
        "zip_extracted": True,
        "artifact_content_values_parsed": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip-digest-receipt-json", type=Path, required=True)
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path)
    args = parser.parse_args()
    result = extract_safely(read_json(args.zip_digest_receipt_json), args.artifact_zip, args.output_dir)
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.receipt_output is not None:
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
