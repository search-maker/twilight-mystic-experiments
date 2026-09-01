#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import tempfile

import run_ena_surface_live25_v3 as V3


def reset() -> None:
    V3._PENDING_ACQUISITION_ERRORS.clear()


def test_discover_tracks_errors_without_changing_return() -> None:
    old = V3._ORIGINAL_DISCOVER
    try:
        reset()
        expected_errors = [{"datastream": "x", "date": "2018-01-01", "error_type": "TimeoutError"}]
        V3._ORIGINAL_DISCOVER = lambda pair, ds, days: (["x.nc"], expected_errors)
        names, errors = V3.discover_tracking("u:t", "x", ["2018-01-01"])
        assert names == ["x.nc"]
        assert errors == expected_errors
        assert V3._PENDING_ACQUISITION_ERRORS == expected_errors
    finally:
        V3._ORIGINAL_DISCOVER = old
        reset()


def test_fail_plus_acquisition_error_becomes_unresolved() -> None:
    old = V3._ORIGINAL_EVALUATE
    try:
        reset()
        V3._PENDING_ACQUISITION_ERRORS.append({"datastream": "mfr", "error_type": "TimeoutError"})
        V3._ORIGINAL_EVALUATE = lambda *a, **k: {"pass": False, "disposition": "SURFACE_EVIDENCE_INSUFFICIENT"}
        out = V3.evaluate_surface_gate_acquisition_safe()
        assert out["pass"] is False
        assert out["disposition"] == "E6_ACQUISITION_UNRESOLVED"
        assert out["underlying_e6_disposition"] == "SURFACE_EVIDENCE_INSUFFICIENT"
        assert out["acquisition_error_count"] == 1
        assert out["sws_values_opened"] is False
        assert out["stage_b_authorized"] is False
        assert V3._PENDING_ACQUISITION_ERRORS == []
    finally:
        V3._ORIGINAL_EVALUATE = old
        reset()


def test_complete_pass_survives_unrelated_optional_acquisition_error() -> None:
    old = V3._ORIGINAL_EVALUATE
    try:
        reset()
        V3._PENDING_ACQUISITION_ERRORS.append({"datastream": "sebs", "error_type": "TimeoutError"})
        expected = {"pass": True, "disposition": "PASS_SURFACE_RETRIEVED_WITH_BROADBAND_CORROBORATION"}
        V3._ORIGINAL_EVALUATE = lambda *a, **k: dict(expected)
        assert V3.evaluate_surface_gate_acquisition_safe() == expected
        assert V3._PENDING_ACQUISITION_ERRORS == []
    finally:
        V3._ORIGINAL_EVALUATE = old
        reset()


def test_fail_without_transport_error_remains_scientific_fail() -> None:
    old = V3._ORIGINAL_EVALUATE
    try:
        reset()
        expected = {"pass": False, "disposition": "SURFACE_CORROBORATION_INSUFFICIENT"}
        V3._ORIGINAL_EVALUATE = lambda *a, **k: dict(expected)
        assert V3.evaluate_surface_gate_acquisition_safe() == expected
    finally:
        V3._ORIGINAL_EVALUATE = old
        reset()


def test_analysis_exception_plus_transport_error_is_unresolved() -> None:
    old = V3._ORIGINAL_EVALUATE
    try:
        reset()
        V3._PENDING_ACQUISITION_ERRORS.append({"filename": "x.nc", "error_type": "URLError"})
        def boom(*a, **k):
            raise ValueError("synthetic")
        V3._ORIGINAL_EVALUATE = boom
        out = V3.evaluate_surface_gate_acquisition_safe()
        assert out["disposition"] == "E6_ACQUISITION_UNRESOLVED"
        assert out["underlying_e6_disposition"] == "E6_ANALYSIS_ERROR_FAIL_CLOSED"
        assert out["analysis_error_type"] == "ValueError"
    finally:
        V3._ORIGINAL_EVALUATE = old
        reset()


def test_analysis_exception_without_transport_error_remains_fail_closed_path() -> None:
    old = V3._ORIGINAL_EVALUATE
    try:
        reset()
        def boom(*a, **k):
            raise ValueError("synthetic")
        V3._ORIGINAL_EVALUATE = boom
        try:
            V3.evaluate_surface_gate_acquisition_safe()
        except ValueError:
            pass
        else:
            raise AssertionError("science analysis exception must remain visible to historical fail-closed handler")
    finally:
        V3._ORIGINAL_EVALUATE = old
        reset()


def test_download_failure_is_tracked_and_reraised() -> None:
    old = V3._ORIGINAL_DOWNLOAD
    try:
        reset()
        def fail(pair, name, path):
            raise TimeoutError("synthetic")
        V3._ORIGINAL_DOWNLOAD = fail
        with tempfile.TemporaryDirectory() as td:
            try:
                V3.download_tracking("u:t", "safe_non_sws.nc", Path(td) / "safe_non_sws.nc")
            except TimeoutError:
                pass
            else:
                raise AssertionError("download exception must preserve historical catch path")
        assert len(V3._PENDING_ACQUISITION_ERRORS) == 1
        assert V3._PENDING_ACQUISITION_ERRORS[0]["error_type"] == "TimeoutError"
    finally:
        V3._ORIGINAL_DOWNLOAD = old
        reset()


def test_wrapper_preserves_surface_gate_v2_binding() -> None:
    assert V3.BASE.E6.__name__ == "ena_surface_gate_v2"


if __name__ == "__main__":
    test_discover_tracks_errors_without_changing_return()
    test_fail_plus_acquisition_error_becomes_unresolved()
    test_complete_pass_survives_unrelated_optional_acquisition_error()
    test_fail_without_transport_error_remains_scientific_fail()
    test_analysis_exception_plus_transport_error_is_unresolved()
    test_analysis_exception_without_transport_error_remains_fail_closed_path()
    test_download_failure_is_tracked_and_reraised()
    test_wrapper_preserves_surface_gate_v2_binding()
    print("PASS ENA E6 v3 unresolved-acquisition contracts")
