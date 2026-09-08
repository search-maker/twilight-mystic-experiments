#!/usr/bin/env python3
"""Fail-closed source-file/datastream binding for ARM Stage-A continuity handoff.

This is control-plane/result-blind only. It validates that each source filename named by
the timing-only continuity handoff belongs to the datastream declared by that row. It
never opens native files, reads radiance values, performs network access, or grants any
science/Stage-B/production authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from tools.arm_stagea_time_continuity_contract_v1 import verify as continuity

EXPECTED_DATASTREAM_PREFIX = {
    "sasze_filterbands": "sgpsaszefilterbandsC1.a1.",
    "hsrl": "sgphsrlC1.a1.",
    "rlprofbe": "sgprlprofbeC1.c1.",
    "arscl": "sgparsclkazr1kolliasC1.c0.",
    "ceil": "sgpceilC1.b1.",
}


class SourceBindingError(ValueError):
    pass


def _canonical_stream(value: str, row_number: int) -> str:
    stream = continuity.STREAM_ALIASES.get((value or "").strip())
    if stream is None or stream not in EXPECTED_DATASTREAM_PREFIX:
        raise SourceBindingError(f"row {row_number}: unsupported stream {value!r}")
    return stream


def _validate_source_filename(name: str, stream: str, row_number: int) -> None:
    if not name or name != name.strip():
        raise SourceBindingError(f"row {row_number}: source filename must be nonempty canonical text")
    if "/" in name or "\\" in name or Path(name).name != name:
        raise SourceBindingError(f"row {row_number}: source_files must contain basenames only")
    prefix = EXPECTED_DATASTREAM_PREFIX[stream]
    if not name.startswith(prefix):
        raise SourceBindingError(
            f"row {row_number}: source filename {name!r} is not bound to declared stream {stream!r}"
        )
    if not name.endswith(".nc"):
        raise SourceBindingError(f"row {row_number}: source filename must be an ARM native .nc basename")
    tail = name[len(prefix) : -3]
    if not tail:
        raise SourceBindingError(f"row {row_number}: source filename lacks native timestamp/member suffix")


def verify_source_file_bindings(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != continuity.EXPECTED_PRIORITY_ROWS * len(continuity.EXPECTED_STREAMS):
        raise SourceBindingError("continuity handoff must contain exactly 100 rows (20 cases x 5 streams)")

    seen: set[tuple[str, str]] = set()
    checked_files = 0
    for row_number, raw in enumerate(rows, start=2):
        if not isinstance(raw, dict):
            raise SourceBindingError(f"row {row_number}: expected object row")
        case_id = str(raw.get("case_id", "")).strip()
        if not case_id:
            raise SourceBindingError(f"row {row_number}: missing case_id")
        stream = _canonical_stream(str(raw.get("stream", "")), row_number)
        key = (case_id, stream)
        if key in seen:
            raise SourceBindingError(f"row {row_number}: duplicate case/stream {key}")
        seen.add(key)
        try:
            files = continuity.parse_list(str(raw.get("source_files", "")), f"row {row_number}.source_files")
        except continuity.ContractError as exc:
            raise SourceBindingError(str(exc)) from exc
        for name in files:
            _validate_source_filename(name, stream, row_number)
            checked_files += 1

    expected_streams = set(continuity.EXPECTED_STREAMS)
    streams_by_case: dict[str, set[str]] = {}
    for case_id, stream in seen:
        streams_by_case.setdefault(case_id, set()).add(stream)
    if len(streams_by_case) != continuity.EXPECTED_PRIORITY_ROWS:
        raise SourceBindingError("continuity handoff must contain exactly 20 distinct cases")
    bad_cases = sorted(case_id for case_id, streams in streams_by_case.items() if streams != expected_streams)
    if bad_cases:
        raise SourceBindingError(f"case stream coverage mismatch for {bad_cases}")

    return {
        "schema": 1,
        "source_file_binding_valid": True,
        "row_count": len(rows),
        "case_count": len(streams_by_case),
        "checked_source_file_count": checked_files,
        "expected_datastream_prefixes": dict(EXPECTED_DATASTREAM_PREFIX),
        "upstream_continuity_contract_pass_inferred": False,
        "scientific_pass_inferred": False,
        "missing_native_data_counts_as_pass": False,
        "protected_results_opened": False,
        "heldout_sws_sasze_radiance_opened": False,
        "heldout_radiance_opening_authorized": False,
        "stage_b_authorized": False,
        "science_execution_authorized": False,
        "production_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("continuity_csv", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        rows = continuity.load_csv_rows(args.continuity_csv)
        receipt = verify_source_file_bindings(rows)
    except (SourceBindingError, continuity.ContractError, OSError) as exc:
        print(f"ARM_STAGEA_SOURCE_FILE_BINDING_FAIL: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
