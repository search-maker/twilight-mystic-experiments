#!/usr/bin/env python3
"""Fail-closed verifier for the frozen ARM Stage-A decoded-time continuity artifact.

This module is control-plane/result-blind. It never opens radiance values, performs
network access, or authorizes Stage B/science. A zero exit code means only that the
supplied continuity artifact is internally consistent with the frozen Stage-A timing
contract; rows/cases may still be FAIL.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_PRIORITY_SHA256 = "345d7023bb4e29e0cc7bb47f1eaaef33636e0bd1719d05e796e3d30cba310ae0"
EXPECTED_PRIORITY_ROWS = 20
EXPECTED_STREAMS = (
    "sasze_filterbands",
    "hsrl",
    "rlprofbe",
    "arscl",
    "ceil",
)
REQUIRED_COLUMNS = (
    "case_id",
    "stream",
    "core_start_utc",
    "core_end_utc",
    "source_files",
    "source_sha256s",
    "decoded_time_basis",
    "code_version",
    "sample_count_core",
    "left_bracket_utc",
    "right_bracket_utc",
    "left_bracket_delta_s",
    "right_bracket_delta_s",
    "median_positive_cadence_s",
    "max_gap_s",
    "duplicate_count",
    "nonfinite_or_masked_count",
    "continuity_pass",
    "failure_reason",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STREAM_ALIASES = {
    "sasze_filterbands": "sasze_filterbands",
    "sgpsaszefilterbandsC1.a1": "sasze_filterbands",
    "hsrl": "hsrl",
    "sgphsrlC1.a1": "hsrl",
    "rlprofbe": "rlprofbe",
    "sgprlprofbeC1.c1": "rlprofbe",
    "arscl": "arscl",
    "sgparsclkazr1kolliasC1.c0": "arscl",
    "ceil": "ceil",
    "sgpceilC1.b1": "ceil",
}


class ContractError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_utc(value: str, field: str) -> datetime:
    if not value or not value.endswith("Z"):
        raise ContractError(f"{field}: timestamp must be nonempty UTC Z form")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError(f"{field}: invalid timestamp {value!r}") from exc
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ContractError(f"{field}: timestamp is not UTC")
    return dt


def parse_float(value: str, field: str, *, strictly_positive: bool = False) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field}: expected finite number") from exc
    if not math.isfinite(x):
        raise ContractError(f"{field}: expected finite number")
    if strictly_positive and x <= 0:
        raise ContractError(f"{field}: expected > 0")
    if not strictly_positive and x < 0:
        raise ContractError(f"{field}: expected >= 0")
    return x


def parse_int(value: str, field: str) -> int:
    try:
        x = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field}: expected integer") from exc
    if str(x) != str(value).strip() and not (str(value).strip().startswith("+") and str(x) == str(value).strip()[1:]):
        raise ContractError(f"{field}: non-canonical integer")
    if x < 0:
        raise ContractError(f"{field}: expected >= 0")
    return x


def parse_list(value: str, field: str) -> list[str]:
    text = (value or "").strip()
    if not text:
        raise ContractError(f"{field}: empty list")
    if text.startswith("["):
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{field}: invalid JSON list") from exc
        if not isinstance(obj, list) or not obj or not all(isinstance(x, str) and x for x in obj):
            raise ContractError(f"{field}: expected nonempty list of nonempty strings")
        return obj
    vals = [x.strip() for x in text.split(";")]
    if not vals or any(not x for x in vals):
        raise ContractError(f"{field}: malformed semicolon list")
    return vals


def normalize_pass(value: str, field: str) -> str:
    v = (value or "").strip().upper()
    if v not in {"PASS", "FAIL"}:
        raise ContractError(f"{field}: expected PASS or FAIL")
    return v


def load_priority_cases(path: Path) -> dict[str, dict[str, str]]:
    digest = sha256(path)
    if digest != EXPECTED_PRIORITY_SHA256:
        raise ContractError(f"priority CSV sha256 mismatch: {digest}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_PRIORITY_ROWS:
        raise ContractError(f"priority CSV must have exactly {EXPECTED_PRIORITY_ROWS} rows")
    required = {"local_civil_date", "event", "t_minus6_utc", "t_minus8_utc"}
    if not rows or not required.issubset(rows[0]):
        raise ContractError("priority CSV missing required identity/time columns")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        event = row["event"].strip().lower()
        date = row["local_civil_date"].strip()
        if event not in {"dawn", "dusk"}:
            raise ContractError(f"priority row has unsupported event {event!r}")
        case_id = f"{date}_{event}"
        if case_id in out:
            raise ContractError(f"duplicate priority case {case_id}")
        t6 = parse_utc(row["t_minus6_utc"], f"{case_id}.t_minus6_utc")
        t8 = parse_utc(row["t_minus8_utc"], f"{case_id}.t_minus8_utc")
        out[case_id] = {
            "core_start_utc": min(t6, t8).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "core_end_utc": max(t6, t8).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        }
    return out


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ContractError("continuity CSV has no header")
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ContractError(f"continuity CSV missing columns: {missing}")
        extra = [c for c in reader.fieldnames if c not in REQUIRED_COLUMNS]
        if extra:
            raise ContractError(f"continuity CSV has unexpected columns: {extra}")
        rows = list(reader)
    if len(rows) != EXPECTED_PRIORITY_ROWS * len(EXPECTED_STREAMS):
        raise ContractError("continuity CSV must contain exactly 100 rows (20 cases x 5 streams)")
    return rows


def load_json_rows(path: Path) -> list[dict[str, Any]]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError("continuity JSON is invalid") from exc
    if isinstance(obj, dict):
        if set(obj) != {"rows"}:
            raise ContractError("continuity JSON object form may contain only 'rows'")
        obj = obj["rows"]
    if not isinstance(obj, list):
        raise ContractError("continuity JSON must be a row array or {'rows': [...]} object")
    if len(obj) != EXPECTED_PRIORITY_ROWS * len(EXPECTED_STREAMS):
        raise ContractError("continuity JSON must contain exactly 100 rows")
    if not all(isinstance(row, dict) for row in obj):
        raise ContractError("continuity JSON rows must be objects")
    return obj


def canonical_row(row: dict[str, Any]) -> dict[str, str]:
    if set(row) != set(REQUIRED_COLUMNS):
        missing = sorted(set(REQUIRED_COLUMNS) - set(row))
        extra = sorted(set(row) - set(REQUIRED_COLUMNS))
        raise ContractError(f"JSON/CSV row field mismatch missing={missing} extra={extra}")
    out: dict[str, str] = {}
    for key in REQUIRED_COLUMNS:
        value = row[key]
        if isinstance(value, (dict, list)) and key in {"source_files", "source_sha256s"}:
            out[key] = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        elif value is None:
            out[key] = ""
        elif isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = str(value)
    return out


def verify_rows(rows: list[dict[str, str]], cases: dict[str, dict[str, str]]) -> dict[str, Any]:
    seen: set[tuple[str, str]] = set()
    case_results: dict[str, list[str]] = {case_id: [] for case_id in cases}
    normalized_rows: list[dict[str, str]] = []

    for idx, raw in enumerate(rows, start=2):
        row = canonical_row(raw)
        case_id = row["case_id"].strip()
        if case_id not in cases:
            raise ContractError(f"row {idx}: unknown case_id {case_id!r}")
        stream_raw = row["stream"].strip()
        stream = STREAM_ALIASES.get(stream_raw)
        if stream is None:
            raise ContractError(f"row {idx}: unsupported stream {stream_raw!r}")
        key = (case_id, stream)
        if key in seen:
            raise ContractError(f"row {idx}: duplicate case/stream {key}")
        seen.add(key)

        expected = cases[case_id]
        if row["core_start_utc"] != expected["core_start_utc"]:
            raise ContractError(f"row {idx}: core_start_utc does not match frozen priority t_minus6/t_minus8 core")
        if row["core_end_utc"] != expected["core_end_utc"]:
            raise ContractError(f"row {idx}: core_end_utc does not match frozen priority t_minus6/t_minus8 core")
        core_start = parse_utc(row["core_start_utc"], f"row {idx}.core_start_utc")
        core_end = parse_utc(row["core_end_utc"], f"row {idx}.core_end_utc")
        left = parse_utc(row["left_bracket_utc"], f"row {idx}.left_bracket_utc")
        right = parse_utc(row["right_bracket_utc"], f"row {idx}.right_bracket_utc")
        if not core_start < core_end:
            raise ContractError(f"row {idx}: core interval is not positive")

        files = parse_list(row["source_files"], f"row {idx}.source_files")
        hashes = parse_list(row["source_sha256s"], f"row {idx}.source_sha256s")
        if len(files) != len(hashes):
            raise ContractError(f"row {idx}: source_files/source_sha256s length mismatch")
        if any(not HEX64.fullmatch(h) for h in hashes):
            raise ContractError(f"row {idx}: source_sha256s must be lowercase SHA-256 hex")

        basis = row["decoded_time_basis"].strip().lower()
        if not basis:
            raise ContractError(f"row {idx}: decoded_time_basis is empty")
        if "time_coverage" in basis or "filename" in basis:
            raise ContractError(f"row {idx}: diagnostic metadata/filename cannot satisfy decoded-time gate")
        if not ("time" in basis or "base_time" in basis or "time_offset" in basis):
            raise ContractError(f"row {idx}: decoded_time_basis does not identify a decoded sample-time coordinate")

        sample_count = parse_int(row["sample_count_core"], f"row {idx}.sample_count_core")
        duplicate_count = parse_int(row["duplicate_count"], f"row {idx}.duplicate_count")
        masked_count = parse_int(row["nonfinite_or_masked_count"], f"row {idx}.nonfinite_or_masked_count")
        del sample_count, duplicate_count, masked_count  # presence/count integrity is the contract here
        left_delta = parse_float(row["left_bracket_delta_s"], f"row {idx}.left_bracket_delta_s")
        right_delta = parse_float(row["right_bracket_delta_s"], f"row {idx}.right_bracket_delta_s")
        median = parse_float(row["median_positive_cadence_s"], f"row {idx}.median_positive_cadence_s", strictly_positive=True)
        max_gap = parse_float(row["max_gap_s"], f"row {idx}.max_gap_s")
        status = normalize_pass(row["continuity_pass"], f"row {idx}.continuity_pass")
        reason = row["failure_reason"].strip()

        derived_conditions = []
        derived_conditions.append(left <= core_start)
        derived_conditions.append(right >= core_end)
        derived_conditions.append(abs((core_start - left).total_seconds() - left_delta) <= 0.001)
        derived_conditions.append(abs((right - core_end).total_seconds() - right_delta) <= 0.001)
        derived_conditions.append(max_gap <= 2.0 * median + 1e-9)
        if stream == "hsrl":
            derived_conditions.append(row["code_version"].strip() == "2.6.7")
        derived_pass = all(derived_conditions)
        if status == "PASS" and not derived_pass:
            raise ContractError(f"row {idx}: declared PASS violates frozen decoded-time continuity conditions")
        if status == "PASS" and reason:
            raise ContractError(f"row {idx}: PASS row must have empty failure_reason")
        if status == "FAIL" and not reason:
            raise ContractError(f"row {idx}: FAIL row must preserve a failure_reason")

        case_results[case_id].append(status)
        row["stream"] = stream
        normalized_rows.append(row)

    expected_keys = {(case_id, stream) for case_id in cases for stream in EXPECTED_STREAMS}
    if seen != expected_keys:
        missing = sorted(expected_keys - seen)
        extra = sorted(seen - expected_keys)
        raise ContractError(f"case/stream coverage mismatch missing={missing} extra={extra}")

    case_continuity = {
        case_id: ("PASS" if len(statuses) == len(EXPECTED_STREAMS) and all(x == "PASS" for x in statuses) else "FAIL")
        for case_id, statuses in case_results.items()
    }
    return {
        "schema": 1,
        "artifact_contract_valid": True,
        "row_count": len(normalized_rows),
        "case_count": len(cases),
        "stream_count": len(EXPECTED_STREAMS),
        "stream_names": list(EXPECTED_STREAMS),
        "case_continuity": case_continuity,
        "case_pass_count": sum(v == "PASS" for v in case_continuity.values()),
        "case_fail_count": sum(v == "FAIL" for v in case_continuity.values()),
        "scientific_pass_inferred": False,
        "missing_native_data_counts_as_pass": False,
        "protected_results_opened": False,
        "heldout_sws_sasze_radiance_opened": False,
        "heldout_radiance_opening_authorized": False,
        "stage_b_authorized": False,
        "science_execution_authorized": False,
        "production_authorized": False,
    }


def verify_json_equivalence(csv_rows: list[dict[str, str]], json_rows: list[dict[str, Any]]) -> None:
    csv_map = {}
    for row in csv_rows:
        c = canonical_row(row)
        stream = STREAM_ALIASES.get(c["stream"].strip(), c["stream"].strip())
        c["stream"] = stream
        csv_map[(c["case_id"].strip(), stream)] = c
    json_map = {}
    for raw in json_rows:
        c = canonical_row(raw)
        stream = STREAM_ALIASES.get(c["stream"].strip(), c["stream"].strip())
        c["stream"] = stream
        json_map[(c["case_id"].strip(), stream)] = c
    if csv_map != json_map:
        raise ContractError("continuity CSV and JSON are not semantically byte-field equivalent")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--priority-csv", required=True, type=Path)
    p.add_argument("--continuity-csv", required=True, type=Path)
    p.add_argument("--continuity-json", required=True, type=Path)
    p.add_argument("--receipt-json", type=Path)
    args = p.parse_args(argv)

    try:
        cases = load_priority_cases(args.priority_csv)
        csv_rows = load_csv_rows(args.continuity_csv)
        json_rows = load_json_rows(args.continuity_json)
        verify_json_equivalence(csv_rows, json_rows)
        receipt = verify_rows(csv_rows, cases)
        receipt.update(
            {
                "priority_csv_sha256": sha256(args.priority_csv),
                "continuity_csv_sha256": sha256(args.continuity_csv),
                "continuity_json_sha256": sha256(args.continuity_json),
            }
        )
    except (ContractError, OSError) as exc:
        print(f"ARM_STAGEA_TIME_CONTINUITY_CONTRACT_FAIL: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt_json:
        args.receipt_json.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
