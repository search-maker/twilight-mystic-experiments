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


def _bind_extraction_to_digest(digest: dict[str, Any], extraction: dict[str, Any]) -> None:
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
    for key in (
        "protected_results_opened",
        "stage_b_authorized",
        "heldout_radiance_opening_authorized",
        "science_execution_authorized",
    ):
        _require_false(extraction, key, "safe-extraction receipt")


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
    _bind_extraction_to_digest(digest, extraction)
    write_receipt(work_dir / "03-safe-extraction-receipt.json", extraction)

    content = content_gate.verify_strict(extracted_dir)
    _validate_content_receipt(content)
    write_receipt(work_dir / "04-strict-content-receipt.json", content)

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
