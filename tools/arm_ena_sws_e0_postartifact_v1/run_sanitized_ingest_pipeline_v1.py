#!/usr/bin/env python3
"""Run the complete result-blind ARM E0 post-artifact ingest chain.

This orchestration layer performs no network access and reads no credentials. It
only composes the already-reviewed gates in their required order:

  authorized GitHub run envelope -> downloaded ZIP digest -> safe extraction ->
  strict sanitized-content verification.

A successful pipeline receipt is an ingest/audit result only. It never grants
Stage B, held-out radiance opening, scientific execution, or production authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import extract_sanitized_artifact_zip_v1 as extraction_gate
import verify_authorized_run_envelope_v1 as envelope_gate
import verify_downloaded_artifact_zip_v1 as digest_gate
import verify_oneevent_e0_artifact_strict_v1 as content_gate

STATUS = "ARM_E0_SANITIZED_POSTARTIFACT_PIPELINE_VERIFIED"
CONTENT_STATUS = "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED"


class PipelineVerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise PipelineVerificationError(message)


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


def receipt_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def write_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(payload))


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON in {path}: {type(exc).__name__}")


def require_new_work_dir(work_dir: Path) -> None:
    if work_dir.is_symlink() or work_dir.exists():
        fail("pipeline work directory must be a new, non-existent path")
    parent = work_dir.parent
    if parent.is_symlink() or not parent.exists() or not parent.is_dir():
        fail("pipeline work directory parent must be an existing non-symlink directory")


def _same(left: dict[str, Any], right: dict[str, Any], key: str, where: str) -> None:
    if left.get(key) != right.get(key):
        fail(f"{where} {key} drift between chained receipts")


def _require_false(payload: dict[str, Any], key: str, where: str) -> None:
    if payload.get(key) is not False:
        fail(f"{where} {key} must remain exactly false")


def _canonical_sha256(value: object, where: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        fail(f"{where} must be a lowercase SHA-256")
    return value


def _bind_digest_to_envelope(envelope: dict[str, Any], digest: dict[str, Any]) -> None:
    for key in (
        "authority_comment",
        "run_id",
        "run_attempt",
        "event",
        "execution_branch",
        "execution_head",
        "workflow_path",
        "artifact_id",
        "artifact_name",
    ):
        _same(envelope, digest, key, "ZIP-digest receipt")
    if digest.get("github_artifact_digest") != envelope.get("artifact_digest"):
        fail("ZIP-digest receipt GitHub digest drift from run envelope")
    if digest.get("downloaded_zip_sha256") != envelope.get("artifact_digest"):
        fail("downloaded ZIP digest is not the authorized GitHub artifact digest")
    for key in (
        "protected_results_opened",
        "stage_b_authorized",
        "heldout_radiance_opening_authorized",
        "science_execution_authorized",
    ):
        _require_false(digest, key, "ZIP-digest receipt")


def _validate_extracted_file_manifest(payload: object) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, dict) or set(payload) != extraction_gate.REQUIRED_FILES:
        fail("safe-extraction receipt extracted_files must cover the exact seven-file set")
    normalized: dict[str, dict[str, Any]] = {}
    for name in sorted(payload):
        row = payload[name]
        if not isinstance(row, dict) or set(row) != {"size_bytes", "sha256"}:
            fail(f"safe-extraction receipt extracted_files[{name!r}] has invalid shape")
        size = row.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            fail(f"safe-extraction receipt extracted_files[{name!r}].size_bytes is invalid")
        normalized[name] = {
            "size_bytes": size,
            "sha256": _canonical_sha256(
                row.get("sha256"),
                f"safe-extraction receipt extracted_files[{name!r}].sha256",
            ),
        }
    return normalized


def _bind_extraction_to_digest(digest: dict[str, Any], extraction: dict[str, Any]) -> dict[str, dict[str, Any]]:
    for key in (
        "authority_comment",
        "run_id",
        "run_attempt",
        "event",
        "execution_branch",
        "execution_head",
        "workflow_path",
        "artifact_id",
        "artifact_name",
        "downloaded_zip_sha256",
    ):
        _same(digest, extraction, key, "safe-extraction receipt")
    if extraction.get("zip_contents_inspected") is not True or extraction.get("zip_extracted") is not True:
        fail("safe-extraction receipt does not attest completed bounded extraction")
    if extraction.get("artifact_content_values_parsed") is not False:
        fail("safe-extraction gate parsed artifact values")
    if extraction.get("archive_member_count") != len(extraction_gate.REQUIRED_FILES):
        fail("safe-extraction receipt archive_member_count drifted")
    if extraction.get("extracted_file_names") != sorted(extraction_gate.REQUIRED_FILES):
        fail("safe-extraction receipt extracted_file_names drifted")
    extracted_files = _validate_extracted_file_manifest(extraction.get("extracted_files"))
    for key in (
        "protected_results_opened",
        "stage_b_authorized",
        "heldout_radiance_opening_authorized",
        "science_execution_authorized",
    ):
        _require_false(extraction, key, "safe-extraction receipt")
    return extracted_files


def _hash_regular_file_stably(path: Path) -> dict[str, Any]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        fail(f"cannot open extracted file safely {path.name!r}: {type(exc).__name__}")
    try:
        with os.fdopen(fd, "rb", closefd=True) as fh:
            before = os.fstat(fh.fileno())
            if not stat.S_ISREG(before.st_mode):
                fail(f"extracted file is not regular: {path.name!r}")
            h = hashlib.sha256()
            size = 0
            for block in iter(lambda: fh.read(1024 * 1024), b""):
                size += len(block)
                h.update(block)
            after = os.fstat(fh.fileno())
    except PipelineVerificationError:
        raise
    except OSError as exc:
        fail(f"cannot hash extracted file {path.name!r}: {type(exc).__name__}")

    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after or size != before.st_size:
        fail(f"extracted file changed while hashing: {path.name!r}")
    try:
        path_state = path.lstat()
    except OSError as exc:
        fail(f"cannot restat extracted file {path.name!r}: {type(exc).__name__}")
    if (
        not stat.S_ISREG(path_state.st_mode)
        or path_state.st_dev != after.st_dev
        or path_state.st_ino != after.st_ino
        or path_state.st_size != after.st_size
        or path_state.st_mtime_ns != after.st_mtime_ns
    ):
        fail(f"extracted file path changed while hashing: {path.name!r}")
    return {"size_bytes": size, "sha256": h.hexdigest()}


def snapshot_extracted_tree(root: Path) -> dict[str, dict[str, Any]]:
    if root.is_symlink() or not root.is_dir():
        fail("sanitized artifact root must remain a non-symlink directory")
    try:
        names_before = {path.name for path in root.iterdir()}
    except OSError as exc:
        fail(f"cannot enumerate sanitized artifact root: {type(exc).__name__}")
    if names_before != extraction_gate.REQUIRED_FILES:
        fail("sanitized artifact root no longer has the exact seven-file set")
    snapshot = {
        name: _hash_regular_file_stably(root / name)
        for name in sorted(extraction_gate.REQUIRED_FILES)
    }
    try:
        names_after = {path.name for path in root.iterdir()}
    except OSError as exc:
        fail(f"cannot re-enumerate sanitized artifact root: {type(exc).__name__}")
    if names_after != names_before:
        fail("sanitized artifact file set changed during byte snapshot")
    return snapshot


def _validate_content_receipt(content: dict[str, Any]) -> None:
    if content.get("status") != CONTENT_STATUS:
        fail(f"strict content verifier status mismatch: {content.get('status')!r}")
    if content.get("probe_case_id") != "2017-06-16_dusk":
        fail("strict content verifier probe case drift")
    if content.get("frozen_event_universe_sha256") != "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41":
        fail("strict content verifier event-universe drift")
    disposition = content.get("e0_disposition")
    if not isinstance(disposition, str) or not disposition:
        fail("strict content verifier lacks bounded E0 disposition identity")
    if not isinstance(content.get("e0_blind_candidate_pass"), bool):
        fail("strict content verifier e0_blind_candidate_pass must be boolean")
    for key in (
        "protected_variable_values_read",
        "raw_sws_files_retained",
        "credentials_persisted",
        "stage_b_authorized",
        "heldout_radiance_opening_authorized",
    ):
        _require_false(content, key, "strict content receipt")


def run_pipeline(
    run_payload: Any,
    artifacts_payload: Any,
    dispatch_inventory_payload: Any,
    artifact_zip: Path,
    work_dir: Path,
) -> dict[str, Any]:
    """Run the offline fail-closed ingest chain and return its success receipt."""

    envelope = envelope_gate.verify_envelope(run_payload, artifacts_payload, dispatch_inventory_payload)
    digest = digest_gate.verify_downloaded_zip(envelope, artifact_zip)
    _bind_digest_to_envelope(envelope, digest)

    require_new_work_dir(work_dir)
    work_dir.mkdir(mode=0o700)
    write_receipt(work_dir / "01-run-envelope-receipt.json", envelope)
    write_receipt(work_dir / "02-zip-digest-receipt.json", digest)

    extracted_dir = work_dir / "sanitized-artifact"
    extraction = extraction_gate.extract_safely(digest, artifact_zip, extracted_dir)
    extraction_manifest = _bind_extraction_to_digest(digest, extraction)
    extracted_before_content = snapshot_extracted_tree(extracted_dir)
    if extracted_before_content != extraction_manifest:
        fail("safe-extraction file manifest does not match extracted bytes")
    write_receipt(work_dir / "03-safe-extraction-receipt.json", extraction)

    content = content_gate.verify_strict(extracted_dir)
    _validate_content_receipt(content)
    extracted_after_content = snapshot_extracted_tree(extracted_dir)
    if extracted_after_content != extracted_before_content:
        fail("sanitized artifact bytes changed during strict content verification")
    write_receipt(work_dir / "04-strict-content-receipt.json", content)

    sanitized_manifest_sha256 = receipt_sha256(extracted_before_content)
    final = {
        "schema": 1,
        "status": STATUS,
        "authority_comment": envelope["authority_comment"],
        "run_id": envelope["run_id"],
        "run_attempt": envelope["run_attempt"],
        "event": envelope["event"],
        "execution_branch": envelope["execution_branch"],
        "execution_head": envelope["execution_head"],
        "workflow_path": envelope["workflow_path"],
        "artifact_id": envelope["artifact_id"],
        "artifact_name": envelope["artifact_name"],
        "artifact_digest": envelope["artifact_digest"],
        "downloaded_zip_sha256": digest["downloaded_zip_sha256"],
        "sanitized_file_manifest_sha256": sanitized_manifest_sha256,
        "same_extracted_bytes_verified_before_and_after_content_check": True,
        "probe_case_id": content["probe_case_id"],
        "frozen_event_universe_sha256": content["frozen_event_universe_sha256"],
        "e0_disposition": content["e0_disposition"],
        "e0_blind_candidate_pass": content["e0_blind_candidate_pass"],
        "receipt_sha256": {
            "01-run-envelope-receipt.json": receipt_sha256(envelope),
            "02-zip-digest-receipt.json": receipt_sha256(digest),
            "03-safe-extraction-receipt.json": receipt_sha256(extraction),
            "04-strict-content-receipt.json": receipt_sha256(content),
        },
        "network_access_performed_by_pipeline": False,
        "credential_values_read_by_pipeline": False,
        "protected_results_opened": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
        "production_authorized": False,
    }
    write_receipt(work_dir / "05-pipeline-success-receipt.json", final)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", type=Path, required=True)
    parser.add_argument("--artifacts-json", type=Path, required=True)
    parser.add_argument("--dispatch-inventory-json", type=Path, required=True)
    parser.add_argument("--artifact-zip", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = run_pipeline(
            read_json(args.run_json),
            read_json(args.artifacts_json),
            read_json(args.dispatch_inventory_json),
            args.artifact_zip,
            args.work_dir,
        )
    except (
        PipelineVerificationError,
        envelope_gate.EnvelopeVerificationError,
        digest_gate.ZipDigestVerificationError,
        extraction_gate.SafeExtractionError,
        content_gate.StrictVerificationError,
    ) as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True, indent=2))
        return 2

    print(canonical_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
