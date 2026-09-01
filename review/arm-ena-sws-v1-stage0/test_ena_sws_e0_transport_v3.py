#!/usr/bin/env python3
"""Synthetic/result-blind contracts for ENA/SWS E0 transport-v3 hardening."""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def expect_system_exit(fn, *args) -> None:
    try:
        fn(*args)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit")


def test_query_error_is_sanitized() -> None:
    tr = importlib.import_module("stream_ena_sws_e0_from_arm_live_v2")
    original = tr.BASE.query_day
    secret = "SECRET_TOKEN_SHOULD_NEVER_PERSIST"
    try:
        def boom(*_args, **_kwargs):
            raise RuntimeError(f"https://adc.arm.gov/armlive/query?user=id:{secret}&ds=enaswsC1.b1")
        tr.BASE.query_day = boom
        try:
            tr.query_day("id:" + secret, tr.DATASTREAM, "20170616", tr.FILE_RE)
        except Exception as exc:
            text = str(exc)
            assert type(exc).__name__ == "ARMTransportError"
            assert secret not in text
            assert "https://" not in text
            assert text == "RuntimeError"
        else:
            raise AssertionError("expected sanitized query error")
    finally:
        tr.BASE.query_day = original


def test_download_error_is_sanitized() -> None:
    tr = importlib.import_module("stream_ena_sws_e0_from_arm_live_v2")
    original = tr.BASE.download_native
    secret = "SECRET_DOWNLOAD_TOKEN"
    try:
        def boom(*_args, **_kwargs):
            raise OSError(f"saveData?user=id:{secret}&file=enaswsC1.b1.20170616.test.nc")
        tr.BASE.download_native = boom
        with tempfile.TemporaryDirectory() as td:
            try:
                tr.download_native("id:" + secret, "enaswsC1.b1.20170616.test.nc", Path(td) / "x.nc")
            except Exception as exc:
                text = str(exc)
                assert type(exc).__name__ == "ARMTransportError"
                assert secret not in text
                assert "saveData" not in text
                assert text == "OSError"
            else:
                raise AssertionError("expected sanitized download error")
    finally:
        tr.BASE.download_native = original


def test_explicit_credentials_are_rejected() -> None:
    tr = importlib.import_module("stream_ena_sws_e0_from_arm_live_v2")
    for argv in (["--user-id", "abc"], ["--user-id=abc"], ["--access-token", "xyz"], ["--access-token=xyz"]):
        expect_system_exit(tr._reject_explicit_credentials, argv)


def test_live25_v3_rejects_execution_overrides() -> None:
    live = importlib.import_module("stream_ena_sws_e0_live25_v3")
    for argv in (["--e0-script", "old.py"], ["--e0-script=old.py"], ["--transport-script", "old.py"], ["--transport-script=old.py"]):
        expect_system_exit(live._reject_overrides, argv)
    assert live.E0_V2.name == "audit_ena_sws_e0_v2.py"
    assert live.TRANSPORT_V2.name == "stream_ena_sws_e0_from_arm_live_v2.py"


def test_portable_probe_v3_is_pinned_and_requires_actual_native_schema() -> None:
    probe = importlib.import_module("run_one_ena_sws_schema_probe_v3")
    assert probe.PROBE_CASE_ID == "2017-06-16_dusk"
    src = Path(probe.__file__).read_text(encoding="utf-8")
    assert 'runner = here / "run_ena_sws_e0_frozen_v3.py"' in src
    assert 'if not sws_schema:' in src
    assert 'protected_variable_values_read") is not False' in src
    assert 'raw_sws_files_retained") is not False' in src
    assert '"transport_errors_sanitized": True' in src


def test_frozen_v3_keeps_e0_v2_and_sanitized_transport() -> None:
    src = (HERE / "run_ena_sws_e0_frozen_v3.py").read_text(encoding="utf-8")
    assert 'e0_path = here / "audit_ena_sws_e0_v2.py"' in src
    assert 'collector_path = here / "stream_ena_sws_e0_from_arm_live_v2.py"' in src
    assert "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41" in src
    assert '"--user-id"' in src and '"--access-token"' in src


def main() -> int:
    test_query_error_is_sanitized()
    test_download_error_is_sanitized()
    test_explicit_credentials_are_rejected()
    test_live25_v3_rejects_execution_overrides()
    test_portable_probe_v3_is_pinned_and_requires_actual_native_schema()
    test_frozen_v3_keeps_e0_v2_and_sanitized_transport()
    print("PASS ENA SWS E0 sanitized-transport v3 synthetic contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
