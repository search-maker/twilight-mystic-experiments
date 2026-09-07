#!/usr/bin/env python3
"""Fail-closed verifier for a sanitized ARM ENA/SWS one-event E0 artifact.

This verifier is deliberately result-blind with respect to protected photometric
values. It accepts only the sanitized evidence package emitted by the frozen
one-event E0 workflow, verifies file coverage/hashes and firewall attestations,
and reports the non-photometric E0 disposition without authorizing Stage B or
any protected-result opening.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

FROZEN_UNIVERSE_SHA256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
PROBE_CASE_ID = "2017-06-16_dusk"
EXPECTED_PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2"
EXPECTED_PURPOSE = "ARM_ENA_SWS_V1_E0_V2_ONE_EVENT_SCHEMA_PROBE_PORTABLE_SANITIZED_TRANSPORT"
EXPECTED_DATASTREAM = "enaswsC1.b1"

REQUIRED_FILES = {
    "ena_sws_e0_event_universe.csv",
    "ena_sws_e0_query_manifest.jsonl",
    "ena_sws_e0_stream_ledger.jsonl",
    "ena_sws_e0_stream_provenance.jsonl",
    "ena_sws_e0_stream_schema.jsonl",
    "ena_sws_e0_stream_summary.json",
    "probe_receipt.json",
}

SAFE_TERMINAL_DISPOSITIONS = {
    "E0_PASS_BLIND_CANDIDATE",
    "E0_TIMING_FAIL",
    "E0_SAFE_QC_VALIDITY_FAIL",
    "E0_VALIDITY_UNRESOLVED_NO_SAFE_QC",
}

UNSAFE_OR_INCOMPLETE_DISPOSITIONS = {
    "SOURCE_FILE_MISSING",
    "ARM_LIVE_QUERY_ERROR",
    "STREAM_AUDIT_ERROR",
    "UNREADABLE_OR_UNDECODABLE",
    "E0_VALIDITY_UNREADABLE",
}

SCHEMA_VARIABLE_ALLOWED_KEYS = {
    "name", "dtype", "dimensions", "shape",
    "protected_photometric_values", "safe_qc_values_allowed",
    "long_name", "standard_name", "units",
}

SECRET_LEAK_PATTERNS = (
    re.compile(r"(?i)(?:^|[?&])user=[^\s]+"),
    re.compile(r"(?i)access[_-]?token\s*[:=]"),
    re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+"),
    re.compile(r"(?i)https?://[^\s]*?/armlive/(?:query|saveData)\?[^\s]*user="),
)


class VerificationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise VerificationError(message)


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
        fail(f"invalid JSON in {path.name}: {type(exc).__name__}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        fail(f"unreadable JSONL {path.name}: {type(exc).__name__}")
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:
            fail(f"invalid JSONL {path.name}:{lineno}: {type(exc).__name__}")
        if not isinstance(obj, dict):
            fail(f"non-object JSONL record in {path.name}:{lineno}")
        rows.append(obj)
    return rows


def require_bool_false(obj: dict[str, Any], key: str, where: str) -> None:
    if obj.get(key) is not False:
        fail(f"{where}: {key} must be false")


def check_no_raw_or_secret_leak(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".nc", ".cdf"}:
            fail(f"raw native payload is forbidden: {path.relative_to(root)}")
        if path.is_symlink():
            fail(f"symlink is forbidden in sanitized artifact: {path.relative_to(root)}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(f"unexpected non-text file in sanitized artifact: {path.relative_to(root)}")
        for pattern in SECRET_LEAK_PATTERNS:
            if pattern.search(text):
                fail(f"possible credential-bearing transport text in {path.relative_to(root)}")


def normalized_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        fail("receipt manifest contains empty/non-string relative_path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        fail(f"unsafe receipt manifest path: {value!r}")
    normalized = p.as_posix()
    if normalized != value or normalized == "probe_receipt.json":
        fail(f"non-canonical receipt manifest path: {value!r}")
    return normalized


def verify_receipt_and_coverage(root: Path) -> dict[str, Any]:
    receipt = read_json(root / "probe_receipt.json")
    if not isinstance(receipt, dict):
        fail("probe_receipt.json must contain an object")
    expected_scalars = {
        "schema": 4,
        "purpose": EXPECTED_PURPOSE,
        "frozen_event_universe_sha256": FROZEN_UNIVERSE_SHA256,
        "probe_case_id": PROBE_CASE_ID,
        "processed_event_count": 1,
        "actual_sws_native_schema_inspected": True,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "credentials_persisted": False,
        "credentials_source": "environment_presence_only",
        "transport_errors_sanitized": True,
        "stage_b_authorized": False,
    }
    for key, expected in expected_scalars.items():
        if receipt.get(key) != expected:
            fail(f"receipt {key} mismatch: expected {expected!r}, got {receipt.get(key)!r}")

    files = receipt.get("files")
    if not isinstance(files, list) or not files:
        fail("receipt files manifest missing/empty")
    manifest: dict[str, tuple[int, str]] = {}
    for item in files:
        if not isinstance(item, dict):
            fail("receipt manifest row must be an object")
        path = normalized_relative_path(item.get("relative_path"))
        if path in manifest:
            fail(f"duplicate receipt manifest path: {path}")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        if not isinstance(size, int) or size < 0:
            fail(f"invalid manifest size for {path}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"invalid manifest sha256 for {path}")
        manifest[path] = (size, digest)

    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name != "probe_receipt.json"
    }
    if set(manifest) != actual:
        missing = sorted(actual - set(manifest))
        extra = sorted(set(manifest) - actual)
        fail(f"receipt manifest coverage mismatch missing={missing} extra={extra}")

    for rel, (size, digest) in manifest.items():
        path = root / rel
        if path.stat().st_size != size:
            fail(f"size mismatch for {rel}")
        if sha256_file(path) != digest:
            fail(f"sha256 mismatch for {rel}")
    return receipt


def verify_universe(root: Path) -> None:
    path = root / "ena_sws_e0_event_universe.csv"
    if sha256_file(path) != FROZEN_UNIVERSE_SHA256:
        fail("frozen event-universe SHA-256 mismatch")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except Exception as exc:
        fail(f"unreadable event universe: {type(exc).__name__}")
    if len(rows) != 906:
        fail(f"expected 906 frozen events, got {len(rows)}")
    matches = [r for r in rows if r.get("case_id") == PROBE_CASE_ID]
    if len(matches) != 1 or matches[0].get("event") != "dusk":
        fail("pinned probe event is missing/duplicated/not dusk in frozen universe")


def verify_summary(root: Path) -> dict[str, Any]:
    summary = read_json(root / "ena_sws_e0_stream_summary.json")
    if not isinstance(summary, dict):
        fail("summary must be an object")
    if summary.get("protocol") != EXPECTED_PROTOCOL:
        fail("summary protocol mismatch")
    if int(summary.get("candidate_event_count", -1)) != 906:
        fail("summary candidate_event_count must be 906")
    if int(summary.get("processed_event_count", -1)) != 1:
        fail("summary processed_event_count must be 1")
    if int(summary.get("remaining_event_count", -1)) != 905:
        fail("summary remaining_event_count must be 905")
    require_bool_false(summary, "protected_variable_values_read", "summary")
    require_bool_false(summary, "raw_sws_files_retained", "summary")
    require_bool_false(summary, "stage_b_authorized", "summary")
    return summary


def verify_schema(root: Path) -> tuple[int, set[str]]:
    rows = read_jsonl(root / "ena_sws_e0_stream_schema.jsonl")
    sws = [r for r in rows if r.get("kind") == "sws"]
    if not sws:
        fail("sanitized artifact contains no native SWS schema record")
    source_hashes: set[str] = set()
    for i, row in enumerate(sws, 1):
        require_bool_false(row, "protected_variable_values_read", f"sws schema row {i}")
        digest = row.get("source_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"sws schema row {i} lacks valid source_sha256")
        source_hashes.add(digest)
        variables = row.get("variables")
        if not isinstance(variables, list) or not variables:
            fail(f"sws schema row {i} lacks variable metadata")
        for j, var in enumerate(variables, 1):
            if not isinstance(var, dict):
                fail(f"sws schema row {i} variable {j} is not an object")
            unknown = set(var) - SCHEMA_VARIABLE_ALLOWED_KEYS
            if unknown:
                fail(f"sws schema row {i} variable {j} has unexpected keys {sorted(unknown)}")
            if not isinstance(var.get("name"), str) or not var["name"]:
                fail(f"sws schema row {i} variable {j} lacks name")
            if not isinstance(var.get("dimensions"), list) or not isinstance(var.get("shape"), list):
                fail(f"sws schema row {i} variable {j} lacks dimensions/shape metadata")
    return len(sws), source_hashes


def verify_ledger(root: Path) -> str:
    rows = read_jsonl(root / "ena_sws_e0_stream_ledger.jsonl")
    if len(rows) != 1:
        fail(f"expected exactly one ledger row, got {len(rows)}")
    row = rows[0]
    if row.get("case_id") != PROBE_CASE_ID:
        fail("ledger case_id mismatch")
    require_bool_false(row, "protected_variable_values_read", "ledger")
    require_bool_false(row, "raw_sws_files_retained", "ledger")
    disposition = str(row.get("disposition", ""))
    if disposition in UNSAFE_OR_INCOMPLETE_DISPOSITIONS or disposition not in SAFE_TERMINAL_DISPOSITIONS:
        fail(f"one-event E0 disposition is incomplete/unsafe/unrecognized: {disposition!r}")
    return disposition


def verify_provenance(root: Path, schema_hashes: set[str]) -> int:
    rows = read_jsonl(root / "ena_sws_e0_stream_provenance.jsonl")
    if len(rows) != 1:
        fail(f"expected exactly one provenance row, got {len(rows)}")
    row = rows[0]
    if row.get("case_id") != PROBE_CASE_ID:
        fail("provenance case_id mismatch")
    require_bool_false(row, "protected_variable_values_read", "provenance")
    require_bool_false(row, "raw_sws_files_retained", "provenance")
    sources = row.get("source_files")
    if not isinstance(sources, list) or not sources:
        fail("provenance source_files missing/empty")
    hashes: set[str] = set()
    for src in sources:
        if not isinstance(src, dict):
            fail("provenance source row is not an object")
        filename = src.get("filename")
        digest = src.get("sha256")
        size = src.get("size_bytes")
        if not isinstance(filename, str) or Path(filename).name != filename:
            fail("provenance source filename must be a basename")
        if not isinstance(size, int) or size <= 0:
            fail(f"invalid provenance size for {filename}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"invalid provenance sha256 for {filename}")
        hashes.add(digest)
    if not hashes.issubset(schema_hashes):
        fail("provenance source hash is not represented by a sanitized SWS schema record")
    return len(sources)


def verify_query_manifest(root: Path) -> int:
    rows = read_jsonl(root / "ena_sws_e0_query_manifest.jsonl")
    if not rows:
        fail("query manifest missing/empty")
    for i, row in enumerate(rows, 1):
        if row.get("case_id") != PROBE_CASE_ID:
            fail(f"query manifest row {i} case_id mismatch")
        if row.get("datastream") != EXPECTED_DATASTREAM:
            fail(f"query manifest row {i} datastream mismatch")
        require_bool_false(row, "credentials_persisted", f"query manifest row {i}")
        names = row.get("filenames")
        if not isinstance(names, list):
            fail(f"query manifest row {i} filenames must be a list")
        for name in names:
            if not isinstance(name, str) or Path(name).name != name:
                fail(f"query manifest row {i} contains unsafe filename")
    return len(rows)


def verify(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        fail(f"artifact directory does not exist: {root}")

    files = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    missing = REQUIRED_FILES - files
    if missing:
        fail(f"required sanitized files missing: {sorted(missing)}")

    check_no_raw_or_secret_leak(root)
    receipt = verify_receipt_and_coverage(root)
    verify_universe(root)
    summary = verify_summary(root)
    sws_schema_records, schema_hashes = verify_schema(root)
    disposition = verify_ledger(root)
    source_file_count = verify_provenance(root, schema_hashes)
    query_rows = verify_query_manifest(root)

    dispositions = summary.get("disposition_counts")
    if not isinstance(dispositions, dict) or dispositions.get(disposition) != 1 or sum(
        int(v) for v in dispositions.values() if isinstance(v, int)
    ) != 1:
        fail("summary disposition_counts do not bind exactly to the one ledger disposition")

    return {
        "schema": 1,
        "status": "SAFE_E0_ONEEVENT_SANITIZED_ARTIFACT_VERIFIED",
        "probe_case_id": PROBE_CASE_ID,
        "frozen_event_universe_sha256": FROZEN_UNIVERSE_SHA256,
        "e0_disposition": disposition,
        "e0_blind_candidate_pass": disposition == "E0_PASS_BLIND_CANDIDATE",
        "sws_schema_record_count": sws_schema_records,
        "source_file_count": source_file_count,
        "query_manifest_row_count": query_rows,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "credentials_persisted": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "receipt_schema": receipt.get("schema"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact_dir", type=Path)
    ap.add_argument("--receipt-out", type=Path, default=None)
    args = ap.parse_args()
    try:
        result = verify(args.artifact_dir)
    except VerificationError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.receipt_out is not None:
        args.receipt_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
