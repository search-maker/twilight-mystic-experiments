#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import run_ena_native_live25_v6 as V6


def test_preferred_absent_allows_fallback() -> None:
    calls = []

    def fake_query(pair, ds, day):
        calls.append((ds, day))
        if ds == "preferred":
            return []
        return [f"{ds}.20180101.000000.nc"]

    old = V6.BASE.query_day
    try:
        V6.BASE.query_day = fake_query
        ds, names, errors = V6.discover_strict("x:y", ["preferred", "fallback"], ["2018-01-01"])
        assert ds == "fallback"
        assert names == ["fallback.20180101.000000.nc"]
        assert errors == []
        assert calls == [("preferred", "2018-01-01"), ("fallback", "2018-01-01")]
    finally:
        V6.BASE.query_day = old


def test_preferred_query_error_is_unresolved_not_fallback() -> None:
    calls = []

    def fake_query(pair, ds, day):
        calls.append((ds, day))
        if ds == "preferred":
            raise TimeoutError("synthetic")
        return [f"{ds}.20180101.000000.nc"]

    old = V6.BASE.query_day
    try:
        V6.BASE.query_day = fake_query
        try:
            V6.discover_strict("x:y", ["preferred", "fallback"], ["2018-01-01"])
        except V6.AcquisitionUnresolved as exc:
            text = str(exc)
            assert "datastream=preferred" in text
            assert "error_type=TimeoutError" in text
        else:
            raise AssertionError("query error must remain unresolved")
        assert calls == [("preferred", "2018-01-01")]
    finally:
        V6.BASE.query_day = old


def test_all_successful_empty_is_genuine_missing() -> None:
    old = V6.BASE.query_day
    try:
        V6.BASE.query_day = lambda pair, ds, day: []
        assert V6.discover_strict("x:y", ["a", "b"], ["2018-01-01"]) == (None, [], [])
    finally:
        V6.BASE.query_day = old


def write_e0(rows: list[dict[str, str]]) -> Path:
    td = tempfile.TemporaryDirectory()
    path = Path(td.name) / "e0.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["case_id", "disposition"])
        wr.writeheader()
        wr.writerows(rows)
    path._test_tmpdir = td  # type: ignore[attr-defined]
    return path


def test_e0_query_error_is_unresolved() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "e0.csv"
        with p.open("w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["case_id", "disposition"])
            wr.writeheader()
            wr.writerow({"case_id": "2018-01-01_dusk", "disposition": "ARM_LIVE_QUERY_ERROR"})
        try:
            V6.e0_pass_set_strict(p)
        except V6.AcquisitionUnresolved as exc:
            assert "2018-01-01_dusk:ARM_LIVE_QUERY_ERROR" in str(exc)
        else:
            raise AssertionError("E0 transport error must remain unresolved")


def test_e0_science_nonpass_remains_nonpass_and_pass_set_is_exact() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "e0.csv"
        with p.open("w", encoding="utf-8", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=["case_id", "disposition"])
            wr.writeheader()
            wr.writerow({"case_id": "pass", "disposition": "E0_PASS_BLIND_CANDIDATE"})
            wr.writerow({"case_id": "missing", "disposition": "SOURCE_FILE_MISSING"})
            wr.writerow({"case_id": "fail", "disposition": "E0_FAIL_STRUCTURAL"})
        assert V6.e0_pass_set_strict(p) == {"pass"}


def test_wrapper_preserves_v5_science_core_binding() -> None:
    assert V6.BASE.G.__name__ == "ena_native_gate_core_v5"


if __name__ == "__main__":
    test_preferred_absent_allows_fallback()
    test_preferred_query_error_is_unresolved_not_fallback()
    test_all_successful_empty_is_genuine_missing()
    test_e0_query_error_is_unresolved()
    test_e0_science_nonpass_remains_nonpass_and_pass_set_is_exact()
    test_wrapper_preserves_v5_science_core_binding()
    print("PASS ENA native live25 v6 unresolved-acquisition contracts")
