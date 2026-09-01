#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import run_one_ena_sws_schema_probe_v2 as P


def safe_summary() -> dict:
    return {
        "protocol": P.EXPECTED_PROTOCOL,
        "processed_event_count": 1,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "stage_b_authorized": False,
    }


def write_summary(root: Path, obj: dict | None = None) -> None:
    (root / "ena_sws_e0_stream_summary.json").write_text(
        json.dumps(obj or safe_summary()) + "\n", encoding="utf-8"
    )


def write_safe_sws_schema(root: Path) -> None:
    record = {
        "kind": "sws",
        "source_file": "enaswsC1.b1.synthetic.nc",
        "source_sha256": "0" * 64,
        "protected_variable_values_read": False,
        "variables": [
            {"name": "time", "dimensions": ["time"], "protected_photometric_values": False},
            {"name": "radiance", "dimensions": ["time", "wavelength"], "protected_photometric_values": True},
        ],
    }
    (root / "ena_sws_e0_stream_schema.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")


def test_safe_output_with_actual_sws_schema_validates() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_summary(root); write_safe_sws_schema(root)
        out = P.validate_safe_probe_output(root)
        assert out["protocol"] == P.EXPECTED_PROTOCOL


def test_summary_only_is_not_a_firewall_proof() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_summary(root)
        try:
            P.validate_safe_probe_output(root)
        except RuntimeError as exc:
            assert "actual SWS native schema" in str(exc)
        else:
            raise AssertionError("SOURCE_FILE_MISSING-style summary must not prove firewall")


def test_raw_native_payload_fails_firewall() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_summary(root); write_safe_sws_schema(root)
        (root / "forbidden.nc").write_bytes(b"synthetic")
        try:
            P.validate_safe_probe_output(root)
        except RuntimeError as exc:
            assert "HOLDOUT FIREWALL" in str(exc)
        else:
            raise AssertionError("raw NetCDF must fail portable probe firewall")


def test_wrong_protocol_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        obj = safe_summary(); obj["protocol"] = "HISTORICAL_V1"
        write_summary(root, obj); write_safe_sws_schema(root)
        try:
            P.validate_safe_probe_output(root)
        except RuntimeError as exc:
            assert "E0-v2 protocol" in str(exc)
        else:
            raise AssertionError("historical protocol must fail")


def test_false_firewall_attestation_required() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for key in ("protected_variable_values_read", "raw_sws_files_retained", "stage_b_authorized"):
            obj = safe_summary(); obj[key] = True
            write_summary(root, obj); write_safe_sws_schema(root)
            try:
                P.validate_safe_probe_output(root)
            except RuntimeError:
                pass
            else:
                raise AssertionError(f"{key}=true must fail")


def test_bad_schema_attestation_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); write_summary(root)
        record = {"kind":"sws","source_sha256":"0"*64,"protected_variable_values_read":True,"variables":[{"name":"time"}]}
        (root / "ena_sws_e0_stream_schema.jsonl").write_text(json.dumps(record)+"\n",encoding="utf-8")
        try:
            P.validate_safe_probe_output(root)
        except RuntimeError as exc:
            assert "protected-values=false" in str(exc)
        else:
            raise AssertionError("unsafe schema attestation must fail")


def test_manifest_is_hash_bound_and_excludes_receipt() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.json").write_text("a\n", encoding="utf-8")
        (root / "probe_receipt.json").write_text("ignore\n", encoding="utf-8")
        rows = P.build_manifest(root)
        assert len(rows) == 1
        assert rows[0]["relative_path"] == "a.json"
        assert len(str(rows[0]["sha256"])) == 64


def test_source_has_no_cli_credential_flags_and_is_live25_pinned() -> None:
    text = Path(P.__file__).read_text(encoding="utf-8")
    assert '"--user-id"' not in text
    assert '"--access-token"' not in text
    assert P.PROBE_CASE_ID == "2017-06-16_dusk"
    assert '"--start-case", PROBE_CASE_ID' in text


if __name__ == "__main__":
    test_safe_output_with_actual_sws_schema_validates()
    test_summary_only_is_not_a_firewall_proof()
    test_raw_native_payload_fails_firewall()
    test_wrong_protocol_fails()
    test_false_firewall_attestation_required()
    test_bad_schema_attestation_fails()
    test_manifest_is_hash_bound_and_excludes_receipt()
    test_source_has_no_cli_credential_flags_and_is_live25_pinned()
    print("PASS portable ENA/SWS one-event E0-v2 firewall probe contracts")
