#!/usr/bin/env python3
"""Verify result-blind Stage-A decoded-time continuity evidence for ARM SGP C1.

This verifier intentionally does not read any scientific measurement values. It
binds a future continuity summary to the frozen priority-20 extraction ledger and
requires proof that native sample times, rather than global time_coverage
metadata, were decoded. A successful verification is only control-plane
readiness evidence; it never authorizes case selection, Stage B, radiance opening,
or scientific execution.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRIORITY_LEDGER_SHA256 = "345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0"
EXTRACT_REQUEST_SHA256 = "96ba04ad1e5f8c7f6c8f3ffd2bbf2116fb5137de9e88d716de3d73c8e75c5996"
EXPECTED_CASE_COUNT = 20
PROTOCOL = "ARM_SGP_C1_STAGEA_DECODED_TIME_CONTINUITY_EVIDENCE_V1"
STATUS = "ARM_SGP_STAGEA_DECODED_TIME_CONTINUITY_EVIDENCE_VERIFIED_RESULT_BLIND"

STREAM_TO_PRIORITY_COLUMN = {
    "sasze_vis": "sasze_vis_file",
    "hsrl": "hsrl_file",
    "rlprofbe": "rlprofbe_file",
    "arscl": "arscl_file",
    "ceil": "ceil_file",
}
REQUIRED_STREAMS = tuple(STREAM_TO_PRIORITY_COLUMN)
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
CASE_ID_RE = re.compile(r"\d{4}-\d{2}-\d{2}_(?:dawn|dusk)\Z")

PRIORITY_COLUMNS = (
    "local_civil_date", "event", "window_start_utc", "window_end_utc",
    "t_minus6_utc", "t_minus7_utc", "t_minus8_utc", "t_minus12_utc",
    "nearest_sonde_file", "nearest_sonde_delta_min", "moon_alt_deg_screen",
    "moon_illum_frac_screen", "moon_elong_deg_screen", "priority_reason",
    "sasze_vis_file", "hsrl_file", "rlprofbe_file", "arscl_file", "ceil_file",
)

CONTINUITY_COLUMNS = (
    "case_id", "stream", "source_filename", "source_sha256",
    "native_time_decode_status", "decoded_time_vector_sha256",
    "decoded_sample_count", "window_overlap_sample_count",
    "first_overlap_sample_utc", "last_overlap_sample_utc",
    "max_gap_seconds_within_window", "metadata_time_coverage_used_as_substitute",
    "protected_values_read", "science_values_read", "hsrl_code_version",
)


class Refusal(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256_bytes(raw)


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise Refusal(f"{field} must be UTC Z timestamp")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Refusal(f"invalid {field}: {value}") from exc
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise Refusal(f"{field} must be UTC")
    return dt


def parse_nonnegative_int(value: str, field: str, *, positive: bool = False) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"\d+", value):
        raise Refusal(f"{field} must be a decimal integer")
    n = int(value)
    if positive and n <= 0:
        raise Refusal(f"{field} must be positive")
    return n


def parse_nonnegative_float(value: str, field: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise Refusal(f"{field} must be numeric") from exc
    if not math.isfinite(x) or x < 0:
        raise Refusal(f"{field} must be finite and nonnegative")
    return x


def parse_false(value: str, field: str) -> None:
    if value != "false":
        raise Refusal(f"{field} must be literal false")


def read_csv_exact(path: Path, expected_columns: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise Refusal(f"cannot read {path}") from exc
    if b"\x00" in raw:
        raise Refusal(f"NUL byte refused: {path}")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Refusal(f"CSV must be UTF-8: {path}") from exc
    reader = csv.DictReader(text.splitlines())
    if tuple(reader.fieldnames or ()) != expected_columns:
        raise Refusal(f"unexpected columns in {path.name}: {reader.fieldnames}")
    rows = list(reader)
    if any(None in row for row in rows):
        raise Refusal(f"ragged CSV row in {path.name}")
    return rows


def load_priority(path: Path) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != PRIORITY_LEDGER_SHA256:
        raise Refusal(f"priority ledger SHA-256 mismatch: {digest}")
    rows = read_csv_exact(path, PRIORITY_COLUMNS)
    if len(rows) != EXPECTED_CASE_COUNT:
        raise Refusal(f"priority ledger must contain exactly {EXPECTED_CASE_COUNT} cases")
    by_case: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["event"] not in {"dawn", "dusk"}:
            raise Refusal("priority event must be dawn/dusk")
        case_id = f'{row["local_civil_date"]}_{row["event"]}'
        if not CASE_ID_RE.fullmatch(case_id) or case_id in by_case:
            raise Refusal(f"invalid or duplicate priority case: {case_id}")
        start = parse_utc(row["window_start_utc"], "window_start_utc")
        end = parse_utc(row["window_end_utc"], "window_end_utc")
        if start >= end:
            raise Refusal(f"non-positive priority window: {case_id}")
        for stream, column in STREAM_TO_PRIORITY_COLUMN.items():
            filename = row[column]
            if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
                raise Refusal(f"unsafe/missing priority filename {stream}: {case_id}")
        by_case[case_id] = row
    return rows, by_case


def verify(priority_path: Path, continuity_path: Path) -> dict[str, Any]:
    priority_rows, priority = load_priority(priority_path)
    continuity_raw = continuity_path.read_bytes()
    rows = read_csv_exact(continuity_path, CONTINUITY_COLUMNS)
    expected_rows = EXPECTED_CASE_COUNT * len(REQUIRED_STREAMS)
    if len(rows) != expected_rows:
        raise Refusal(f"continuity evidence must contain exactly {expected_rows} rows")

    seen: set[tuple[str, str]] = set()
    records: list[dict[str, Any]] = []
    for row in rows:
        case_id = row["case_id"]
        stream = row["stream"]
        key = (case_id, stream)
        if case_id not in priority:
            raise Refusal(f"unknown case_id: {case_id}")
        if stream not in STREAM_TO_PRIORITY_COLUMN:
            raise Refusal(f"unknown stream: {stream}")
        if key in seen:
            raise Refusal(f"duplicate continuity row: {case_id}/{stream}")
        seen.add(key)

        expected_filename = priority[case_id][STREAM_TO_PRIORITY_COLUMN[stream]]
        if row["source_filename"] != expected_filename:
            raise Refusal(f"source filename mismatch: {case_id}/{stream}")
        if not SHA_RE.fullmatch(row["source_sha256"]):
            raise Refusal(f"invalid source SHA-256: {case_id}/{stream}")
        if row["native_time_decode_status"] != "DECODED_NATIVE_TIME":
            raise Refusal(f"native time was not decoded: {case_id}/{stream}")
        if not SHA_RE.fullmatch(row["decoded_time_vector_sha256"]):
            raise Refusal(f"invalid decoded-time-vector SHA-256: {case_id}/{stream}")
        decoded_count = parse_nonnegative_int(row["decoded_sample_count"], "decoded_sample_count", positive=True)
        overlap_count = parse_nonnegative_int(row["window_overlap_sample_count"], "window_overlap_sample_count", positive=True)
        if overlap_count > decoded_count:
            raise Refusal(f"overlap count exceeds decoded count: {case_id}/{stream}")
        first = parse_utc(row["first_overlap_sample_utc"], "first_overlap_sample_utc")
        last = parse_utc(row["last_overlap_sample_utc"], "last_overlap_sample_utc")
        if first > last:
            raise Refusal(f"overlap timestamps reversed: {case_id}/{stream}")
        window_start = parse_utc(priority[case_id]["window_start_utc"], "window_start_utc")
        window_end = parse_utc(priority[case_id]["window_end_utc"], "window_end_utc")
        if first < window_start or first > window_end or last < window_start or last > window_end:
            raise Refusal(f"overlap endpoint outside frozen window: {case_id}/{stream}")
        max_gap = parse_nonnegative_float(row["max_gap_seconds_within_window"], "max_gap_seconds_within_window")
        parse_false(row["metadata_time_coverage_used_as_substitute"], "metadata_time_coverage_used_as_substitute")
        parse_false(row["protected_values_read"], "protected_values_read")
        parse_false(row["science_values_read"], "science_values_read")
        if stream == "hsrl":
            if row["hsrl_code_version"] != "2.6.7":
                raise Refusal(f"HSRL code_version is not frozen corrected 2.6.7: {case_id}")
        elif row["hsrl_code_version"] != "":
            raise Refusal(f"hsrl_code_version must be blank for {stream}: {case_id}")

        records.append({
            "case_id": case_id,
            "stream": stream,
            "source_filename": expected_filename,
            "source_sha256": row["source_sha256"],
            "decoded_time_vector_sha256": row["decoded_time_vector_sha256"],
            "decoded_sample_count": decoded_count,
            "window_overlap_sample_count": overlap_count,
            "first_overlap_sample_utc": row["first_overlap_sample_utc"],
            "last_overlap_sample_utc": row["last_overlap_sample_utc"],
            "max_gap_seconds_within_window": max_gap,
            "hsrl_code_version": row["hsrl_code_version"] or None,
        })

    expected_keys = {(case_id, stream) for case_id in priority for stream in REQUIRED_STREAMS}
    if seen != expected_keys:
        raise Refusal("continuity evidence does not cover the exact priority-case/stream product")
    records.sort(key=lambda item: (item["case_id"], item["stream"]))

    receipt: dict[str, Any] = {
        "schema": 1,
        "protocol": PROTOCOL,
        "status": STATUS,
        "priority_ledger_sha256": PRIORITY_LEDGER_SHA256,
        "extract_request_sha256": EXTRACT_REQUEST_SHA256,
        "continuity_evidence_sha256": sha256_bytes(continuity_raw),
        "priority_case_count": len(priority_rows),
        "required_streams": list(REQUIRED_STREAMS),
        "verified_case_stream_row_count": len(records),
        "records_sha256": canonical_sha256(records),
        "decoded_native_times_required": True,
        "metadata_time_coverage_substitution_allowed": False,
        "scientific_values_read": False,
        "protected_values_read": False,
        "case_selection_performed": False,
        "case_selection_authorized": False,
        "stage_b_authorized": False,
        "heldout_radiance_opening_authorized": False,
        "science_execution_authorized": False,
        "production_authorized": False,
        "continuity_threshold_classification_performed": False,
        "note": "Structural/provenance verification only; recorded max gaps are not scientifically classified by this gate.",
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority-ledger", type=Path, required=True)
    parser.add_argument("--continuity-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = verify(args.priority_ledger, args.continuity_evidence)
    except (OSError, Refusal, ValueError) as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt_sha256": receipt["receipt_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
