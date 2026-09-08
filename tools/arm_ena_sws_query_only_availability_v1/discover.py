#!/usr/bin/env python3
"""Authenticated metadata/query-only SWS native-file availability discovery.

This executable is result-blind and deliberately incapable of downloading or
opening a native ARM file. It queries only ARM Live ``/query`` metadata for the
already-frozen ordered 25-case ENA/SWS set and stops at the first case/day whose
exact expected ``enaswsC1.b1`` native basename is returned.

Credential values are accepted only through ARM_USER_ID and ARM_ACCESS_TOKEN;
they are never persisted, printed, or accepted on the command line.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

BASE_URL = "https://adc.arm.gov/armlive"
DATASTREAM = "enaswsC1.b1"
MANIFEST_NAME = "ordered_25_cases.json"
EXPECTED_MANIFEST_SHA256 = "8a0756be59dac59cd8ad4fab77e499ec19069e24d2d2a636fa4352713b550def"
EXPECTED_CASE_COUNT = 25
EXPECTED_PURPOSE = "ARM_ENA_SWS_V1_E0_SUCCESSOR_QUERY_ONLY_AVAILABILITY_DISCOVERY"
FILE_RE = re.compile(r"^enaswsC1\.b1\.(\d{8})\..*\.(?:nc|cdf)$", re.I)
OUTPUT_ALLOWED_KEYS = {
    "schema",
    "purpose",
    "status",
    "datastream",
    "ordered_case_manifest_sha256",
    "ordered_case_count",
    "checked_case_count",
    "checked_cases",
    "first_match",
    "query_error",
    "credentials_persisted",
    "native_file_download_performed",
    "native_file_open_performed",
    "protected_sws_sasze_values_read",
    "stage_b_authorized",
    "mystic_science_authorized",
    "production_authorized",
}


class QueryOnlyError(RuntimeError):
    """Sanitized query-only transport/contract error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != EXPECTED_MANIFEST_SHA256:
        raise QueryOnlyError("ordered-case manifest digest mismatch")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception:
        raise QueryOnlyError("ordered-case manifest is not valid UTF-8 JSON") from None
    if not isinstance(obj, dict):
        raise QueryOnlyError("ordered-case manifest root must be an object")
    if obj.get("schema") != 1 or obj.get("purpose") != EXPECTED_PURPOSE:
        raise QueryOnlyError("ordered-case manifest identity mismatch")
    if obj.get("datastream") != DATASTREAM:
        raise QueryOnlyError("ordered-case manifest datastream mismatch")
    cases = obj.get("ordered_case_ids")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASE_COUNT:
        raise QueryOnlyError("ordered-case manifest cardinality mismatch")
    if len(set(cases)) != len(cases):
        raise QueryOnlyError("ordered-case manifest contains duplicate case IDs")
    for case_id in cases:
        if not isinstance(case_id, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}_dusk", case_id):
            raise QueryOnlyError("ordered-case manifest contains malformed case ID")
    return obj


def _next_day(day: str) -> str:
    d = dt.date.fromisoformat(day)
    return (d + dt.timedelta(days=1)).isoformat()


def _json_filenames(obj: Any) -> list[str]:
    out: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            name = os.path.basename(value)
            if name.lower().endswith((".nc", ".cdf")):
                out.add(name)

    walk(obj)
    return sorted(out)


def _query_payload(
    userpair: str,
    day: str,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> Any:
    params = urllib.parse.urlencode(
        {
            "user": userpair,
            "ds": DATASTREAM,
            "start": day,
            "end": _next_day(day),
            "wt": "json",
        }
    )
    request = urllib.request.Request(
        BASE_URL + "/query?" + params,
        headers={"User-Agent": "arm-ena-sws-query-only-availability-v1/1"},
    )
    try:
        with opener(request, timeout=120) as response:
            body = response.read()
    except Exception as exc:
        raise QueryOnlyError(type(exc).__name__) from None
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        raise QueryOnlyError("invalid_json_response") from None


def _matching_names(payload: Any, yyyymmdd: str) -> list[str]:
    matches: list[str] = []
    for name in _json_filenames(payload):
        m = FILE_RE.fullmatch(name)
        if m and m.group(1) == yyyymmdd:
            matches.append(name)
    return sorted(set(matches))


def _base_receipt(manifest_sha256: str, ordered_count: int) -> dict[str, Any]:
    return {
        "schema": 1,
        "purpose": EXPECTED_PURPOSE,
        "status": "UNSET",
        "datastream": DATASTREAM,
        "ordered_case_manifest_sha256": manifest_sha256,
        "ordered_case_count": ordered_count,
        "checked_case_count": 0,
        "checked_cases": [],
        "first_match": None,
        "query_error": None,
        "credentials_persisted": False,
        "native_file_download_performed": False,
        "native_file_open_performed": False,
        "protected_sws_sasze_values_read": False,
        "stage_b_authorized": False,
        "mystic_science_authorized": False,
        "production_authorized": False,
    }


def discover(
    userpair: str,
    manifest: dict[str, Any],
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    cases = list(manifest["ordered_case_ids"])
    receipt = _base_receipt(EXPECTED_MANIFEST_SHA256, len(cases))

    for ordinal, case_id in enumerate(cases, start=1):
        day = case_id[:10]
        yyyymmdd = day.replace("-", "")
        try:
            payload = _query_payload(userpair, day, opener=opener)
            matches = _matching_names(payload, yyyymmdd)
        except QueryOnlyError as exc:
            receipt["status"] = "QUERY_ERROR_FAIL_CLOSED"
            receipt["checked_case_count"] = len(receipt["checked_cases"])
            receipt["query_error"] = {
                "ordinal": ordinal,
                "case_id": case_id,
                "date": day,
                "error_type": str(exc),
            }
            _validate_receipt(receipt, cases)
            return receipt

        receipt["checked_cases"].append(
            {
                "ordinal": ordinal,
                "case_id": case_id,
                "date": day,
                "match_count": len(matches),
            }
        )
        receipt["checked_case_count"] = len(receipt["checked_cases"])
        if matches:
            receipt["status"] = "FIRST_NATIVE_FILENAME_RESOLVED"
            receipt["first_match"] = {
                "ordinal": ordinal,
                "case_id": case_id,
                "date": day,
                "filenames": matches,
            }
            _validate_receipt(receipt, cases)
            return receipt

    receipt["status"] = "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED"
    _validate_receipt(receipt, cases)
    return receipt


def _validate_receipt(receipt: dict[str, Any], expected_cases: list[str] | None = None) -> None:
    if set(receipt) != OUTPUT_ALLOWED_KEYS:
        raise QueryOnlyError("receipt key universe drift")
    if receipt["ordered_case_count"] != EXPECTED_CASE_COUNT:
        raise QueryOnlyError("receipt ordered-case count drift")
    if receipt["ordered_case_manifest_sha256"] != EXPECTED_MANIFEST_SHA256:
        raise QueryOnlyError("receipt manifest identity drift")
    if receipt.get("schema") != 1 or receipt.get("purpose") != EXPECTED_PURPOSE or receipt.get("datastream") != DATASTREAM:
        raise QueryOnlyError("receipt identity drift")
    if receipt.get("status") not in {
        "FIRST_NATIVE_FILENAME_RESOLVED",
        "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED",
        "QUERY_ERROR_FAIL_CLOSED",
    }:
        raise QueryOnlyError("receipt status drift")
    for key in (
        "credentials_persisted",
        "native_file_download_performed",
        "native_file_open_performed",
        "protected_sws_sasze_values_read",
        "stage_b_authorized",
        "mystic_science_authorized",
        "production_authorized",
    ):
        if receipt.get(key) is not False:
            raise QueryOnlyError(f"forbidden authority/activity flag drift: {key}")
    checked = receipt["checked_cases"]
    if not isinstance(checked, list) or receipt["checked_case_count"] != len(checked):
        raise QueryOnlyError("receipt checked-case count mismatch")
    if not isinstance(receipt["checked_case_count"], int) or not (0 <= receipt["checked_case_count"] <= EXPECTED_CASE_COUNT):
        raise QueryOnlyError("receipt checked-case count out of range")
    if expected_cases is not None and len(expected_cases) != EXPECTED_CASE_COUNT:
        raise QueryOnlyError("expected-case validation cardinality drift")
    for i, row in enumerate(checked, start=1):
        if not isinstance(row, dict) or set(row) != {"ordinal", "case_id", "date", "match_count"}:
            raise QueryOnlyError("checked-case schema drift")
        if row["ordinal"] != i or not isinstance(row["match_count"], int) or row["match_count"] < 0:
            raise QueryOnlyError("checked-case ordering/count drift")
        if not isinstance(row["case_id"], str) or row["date"] != row["case_id"][:10]:
            raise QueryOnlyError("checked-case date binding drift")
        if expected_cases is not None and row["case_id"] != expected_cases[i - 1]:
            raise QueryOnlyError("checked-case order drift from frozen manifest")

    match = receipt["first_match"]
    query_error = receipt["query_error"]
    status = receipt["status"]
    if status == "FIRST_NATIVE_FILENAME_RESOLVED":
        if query_error is not None or match is None or not checked:
            raise QueryOnlyError("first-match status relationship drift")
        if any(row["match_count"] != 0 for row in checked[:-1]) or checked[-1]["match_count"] <= 0:
            raise QueryOnlyError("first-match must be first positive checked case")
    elif status == "EXHAUSTED_25_NO_NATIVE_FILENAME_RESOLVED":
        if match is not None or query_error is not None or len(checked) != EXPECTED_CASE_COUNT:
            raise QueryOnlyError("exhausted status relationship drift")
        if any(row["match_count"] != 0 for row in checked):
            raise QueryOnlyError("exhausted receipt cannot contain positive matches")
    elif status == "QUERY_ERROR_FAIL_CLOSED":
        if match is not None or not isinstance(query_error, dict):
            raise QueryOnlyError("query-error status relationship drift")
        if any(row["match_count"] != 0 for row in checked):
            raise QueryOnlyError("query-error receipt cannot skip an earlier resolved match")
        if set(query_error) != {"ordinal", "case_id", "date", "error_type"}:
            raise QueryOnlyError("query-error schema drift")
        expected_ordinal = len(checked) + 1
        if query_error["ordinal"] != expected_ordinal or not (1 <= expected_ordinal <= EXPECTED_CASE_COUNT):
            raise QueryOnlyError("query-error ordinal drift")
        if query_error["date"] != str(query_error["case_id"])[:10]:
            raise QueryOnlyError("query-error date binding drift")
        if expected_cases is not None and query_error["case_id"] != expected_cases[expected_ordinal - 1]:
            raise QueryOnlyError("query-error order drift from frozen manifest")
        if not isinstance(query_error["error_type"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", query_error["error_type"]):
            raise QueryOnlyError("query-error type is not sanitized")

    if match is not None:
        if not isinstance(match, dict) or set(match) != {"ordinal", "case_id", "date", "filenames"}:
            raise QueryOnlyError("first-match schema drift")
        if match["ordinal"] != receipt["checked_case_count"]:
            raise QueryOnlyError("first-match must be final checked case")
        if match["case_id"] != checked[-1]["case_id"] or match["date"] != checked[-1]["date"]:
            raise QueryOnlyError("first-match identity drift from checked case")
        names = match["filenames"]
        if not isinstance(names, list) or not names or len(names) != checked[-1]["match_count"]:
            raise QueryOnlyError("first-match filename count drift")
        yyyymmdd = match["date"].replace("-", "")
        if names != sorted(set(names)):
            raise QueryOnlyError("first-match filenames must be unique sorted basenames")
        for name in names:
            m = FILE_RE.fullmatch(name) if isinstance(name, str) else None
            if not m or os.path.basename(name) != name or m.group(1) != yyyymmdd:
                raise QueryOnlyError("unsafe first-match filename")


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _reject_explicit_credentials(argv: list[str]) -> None:
    for arg in argv:
        if arg == "--user-id" or arg.startswith("--user-id=") or arg == "--access-token" or arg.startswith("--access-token="):
            raise SystemExit("credentials are accepted from inherited environment only")


def main(argv: list[str] | None = None) -> int:
    argsv = list(sys.argv[1:] if argv is None else argv)
    _reject_explicit_credentials(argsv)
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name(MANIFEST_NAME))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argsv)

    uid = os.environ.get("ARM_USER_ID", "").strip()
    token = os.environ.get("ARM_ACCESS_TOKEN", "").strip()
    if not uid or not token:
        raise SystemExit("ARM_USER_ID and ARM_ACCESS_TOKEN are required; values are never printed or persisted")

    manifest = load_manifest(args.manifest)
    receipt = discover(uid + ":" + token, manifest)
    _write_receipt(args.output, receipt)
    print(receipt["status"])
    return 0 if receipt["status"] != "QUERY_ERROR_FAIL_CLOSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
