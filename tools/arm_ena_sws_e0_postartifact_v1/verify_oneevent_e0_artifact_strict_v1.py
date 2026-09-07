#!/usr/bin/env python3
"""Strict entrypoint for the sanitized ARM ENA/SWS one-event E0 artifact.

The frozen producer has a closed seven-file output universe. Refuse every extra
filesystem object and every unregistered semantic field before delegating to the
deeper result-blind verifier, so future producer widening cannot silently carry
protected data or bypass provenance cross-binding.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verify_oneevent_e0_artifact_v1 as base


class StrictVerificationError(RuntimeError):
    pass


RECEIPT_ALLOWED_KEYS = {
    "schema", "purpose", "created_utc", "frozen_event_universe_sha256",
    "probe_case_id", "processed_event_count", "actual_sws_native_schema_inspected",
    "protected_variable_values_read", "raw_sws_files_retained", "credentials_persisted",
    "credentials_source", "transport_errors_sanitized", "stage_b_authorized", "files",
}
RECEIPT_FILE_ALLOWED_KEYS = {"relative_path", "size_bytes", "sha256"}
SUMMARY_ALLOWED_KEYS = {
    "schema", "protocol", "control_comment", "candidate_event_count",
    "processed_event_count", "remaining_event_count", "disposition_counts",
    "e0_auditor_sha256", "collector_sha256", "raw_sws_files_retained",
    "protected_variable_values_read", "stage_b_authorized",
}
SCHEMA_ROW_ALLOWED_KEYS = {
    "kind", "source_file", "source_sha256", "dod_version", "process_version",
    "variables", "protected_variable_values_read",
}
PROVENANCE_ALLOWED_KEYS = {
    "case_id", "source_files", "e0_auditor_sha256", "collector_sha256",
    "protected_variable_values_read", "raw_sws_files_retained",
}
PROVENANCE_SOURCE_ALLOWED_KEYS = {"filename", "size_bytes", "sha256"}
QUERY_ALLOWED_KEYS = {
    "case_id", "datastream", "date", "start", "end_exclusive", "filenames",
    "credentials_persisted",
}
LEDGER_ALLOWED_KEYS = {
    "case_id", "local_civil_date", "event", "t_minus8_utc", "t_minus7_utc", "t_minus6_utc",
    "source_file_count", "source_files", "source_sha256", "target_wavelength_nm_requested",
    "target_pixel_map", "qc_variables_used", "timing_pass",
    "validity_resolved_without_photometric_values", "validity_pass",
    "primary_holdout_eligible_after_e0", "disposition", "read_errors", "e0_semantics",
    "protected_variable_values_read", "raw_sws_files_retained",
}
for _anchor in ("minus8", "minus7", "minus6"):
    LEDGER_ALLOWED_KEYS.update({
        f"nearest_{_anchor}_s",
        f"samples_within_5s_{_anchor}",
        f"samples_within_30s_{_anchor}",
        f"safe_qc_valid_samples_within_5s_{_anchor}",
        f"safe_qc_valid_samples_within_30s_{_anchor}",
    })


def _reject_unknown(obj: dict, allowed: set[str], where: str) -> None:
    unknown = set(obj) - allowed
    if unknown:
        raise StrictVerificationError(f"{where} has unregistered keys {sorted(unknown)}")


def _basename(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or Path(value).name != value:
        raise StrictVerificationError(f"{where} must be a basename")
    return value


def _sha(value: object, where: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise StrictVerificationError(f"{where} must be a lowercase SHA-256")
    return value


def _closed_semantic_preflight(root: Path) -> None:
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if path.is_symlink():
            raise StrictVerificationError(f"symlink is forbidden in sanitized artifact: {rel}")
        if path.is_dir():
            raise StrictVerificationError(f"unexpected directory in closed sanitized artifact: {rel}")
        if not path.is_file():
            raise StrictVerificationError(f"unexpected filesystem object in sanitized artifact: {rel}")

    receipt = base.read_json(root / "probe_receipt.json")
    if not isinstance(receipt, dict):
        raise StrictVerificationError("probe_receipt.json must contain an object")
    _reject_unknown(receipt, RECEIPT_ALLOWED_KEYS, "receipt")
    manifest = receipt.get("files")
    if not isinstance(manifest, list):
        raise StrictVerificationError("receipt files must be a list")
    for i, row in enumerate(manifest, 1):
        if not isinstance(row, dict):
            raise StrictVerificationError(f"receipt files row {i} must be an object")
        _reject_unknown(row, RECEIPT_FILE_ALLOWED_KEYS, f"receipt files row {i}")

    summary = base.read_json(root / "ena_sws_e0_stream_summary.json")
    if not isinstance(summary, dict):
        raise StrictVerificationError("summary must contain an object")
    _reject_unknown(summary, SUMMARY_ALLOWED_KEYS, "summary")

    schema_rows = base.read_jsonl(root / "ena_sws_e0_stream_schema.jsonl")
    sws_sources: dict[str, str] = {}
    for i, row in enumerate(schema_rows, 1):
        _reject_unknown(row, SCHEMA_ROW_ALLOWED_KEYS, f"schema row {i}")
        kind = row.get("kind")
        if kind not in {"sws", "swsaux"}:
            raise StrictVerificationError(f"schema row {i} has unregistered kind {kind!r}")
        if row.get("protected_variable_values_read") is not False:
            raise StrictVerificationError(f"schema row {i} lacks protected-values=false attestation")
        filename = _basename(row.get("source_file"), f"schema row {i} source_file")
        digest = _sha(row.get("source_sha256"), f"schema row {i} source_sha256")
        variables = row.get("variables")
        if not isinstance(variables, list) or not variables:
            raise StrictVerificationError(f"schema row {i} lacks variable metadata")
        for j, var in enumerate(variables, 1):
            if not isinstance(var, dict):
                raise StrictVerificationError(f"schema row {i} variable {j} must be an object")
            _reject_unknown(var, base.SCHEMA_VARIABLE_ALLOWED_KEYS, f"schema row {i} variable {j}")
        if kind == "sws":
            if filename in sws_sources:
                raise StrictVerificationError(f"duplicate SWS schema source filename: {filename}")
            sws_sources[filename] = digest

    ledger_rows = base.read_jsonl(root / "ena_sws_e0_stream_ledger.jsonl")
    for i, row in enumerate(ledger_rows, 1):
        _reject_unknown(row, LEDGER_ALLOWED_KEYS, f"ledger row {i}")

    provenance_rows = base.read_jsonl(root / "ena_sws_e0_stream_provenance.jsonl")
    provenance_sources: dict[str, str] = {}
    for i, row in enumerate(provenance_rows, 1):
        _reject_unknown(row, PROVENANCE_ALLOWED_KEYS, f"provenance row {i}")
        sources = row.get("source_files")
        if not isinstance(sources, list):
            raise StrictVerificationError(f"provenance row {i} source_files must be a list")
        for j, src in enumerate(sources, 1):
            if not isinstance(src, dict):
                raise StrictVerificationError(f"provenance row {i} source {j} must be an object")
            _reject_unknown(src, PROVENANCE_SOURCE_ALLOWED_KEYS, f"provenance row {i} source {j}")
            filename = _basename(src.get("filename"), f"provenance row {i} source {j} filename")
            digest = _sha(src.get("sha256"), f"provenance row {i} source {j} sha256")
            if filename in provenance_sources:
                raise StrictVerificationError(f"duplicate provenance source filename: {filename}")
            provenance_sources[filename] = digest

    query_rows = base.read_jsonl(root / "ena_sws_e0_query_manifest.jsonl")
    query_filenames: set[str] = set()
    for i, row in enumerate(query_rows, 1):
        _reject_unknown(row, QUERY_ALLOWED_KEYS, f"query manifest row {i}")
        names = row.get("filenames")
        if not isinstance(names, list):
            raise StrictVerificationError(f"query manifest row {i} filenames must be a list")
        for j, name in enumerate(names, 1):
            query_filenames.add(_basename(name, f"query manifest row {i} filename {j}"))

    if provenance_sources != sws_sources:
        raise StrictVerificationError("SWS provenance filename/SHA set does not exactly match SWS schema sources")
    if query_filenames != set(provenance_sources):
        raise StrictVerificationError("query-manifest filename set does not exactly match provenance sources")

    if len(ledger_rows) == 1:
        disposition = ledger_rows[0].get("disposition")
        if summary.get("disposition_counts") != {disposition: 1}:
            raise StrictVerificationError("summary disposition_counts must be exactly the one ledger disposition")


def verify_strict(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise StrictVerificationError(f"artifact directory does not exist: {root}")
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
    }
    if actual != base.REQUIRED_FILES:
        missing = sorted(base.REQUIRED_FILES - actual)
        unexpected = sorted(actual - base.REQUIRED_FILES)
        raise StrictVerificationError(
            f"closed sanitized artifact file-set mismatch missing={missing} unexpected={unexpected}"
        )
    try:
        _closed_semantic_preflight(root)
        return base.verify(root)
    except base.VerificationError as exc:
        raise StrictVerificationError(str(exc)) from exc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact_dir", type=Path)
    ap.add_argument("--receipt-out", type=Path, default=None)
    args = ap.parse_args()
    try:
        result = verify_strict(args.artifact_dir)
    except StrictVerificationError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.receipt_out is not None:
        args.receipt_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
