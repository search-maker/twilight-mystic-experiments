#!/usr/bin/env python3
"""Synthetic local self-test for the Phase-0 ARM SASZE native-time gate."""

from __future__ import annotations

import tempfile
from pathlib import Path

import netCDF4
import numpy as np

from audit_sasze_native_time import PRIMARY_STREAM, STREAMS, audit_case, parse_utc

CASE = {
    "priority": "0",
    "case_id": "2024-04-08_dawn",
    "event": "dawn",
    "source_date_utc": "20240408",
    "t_minus8_utc": "2024-04-08T11:29:18.545002Z",
    "t_minus7_utc": "2024-04-08T11:34:27.589304Z",
    "t_minus6_utc": "2024-04-08T11:39:35.526412Z",
}


def write_file(root: Path, stream: str, times_epoch: np.ndarray, suffix: str = "000000") -> Path:
    path = root / f"{stream}.20240408.{suffix}.nc"
    if path.exists():
        path.unlink()
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", len(times_epoch))
        t = ds.createVariable("time", "f8", ("time",))
        t.units = "seconds since 1970-01-01 00:00:00 UTC"
        t[:] = times_epoch
        it = ds.createVariable("integration_time_vis", "f4", ("time",))
        it[:] = np.full(len(times_epoch), 0.1, dtype=np.float32)
        scans = ds.createVariable("number_of_scans_vis", "i4", ("time",))
        scans[:] = np.full(len(times_epoch), 1, dtype=np.int32)
        qc = ds.createVariable("qc_instrument_health", "i4", ("time",))
        qc.flag_values = np.asarray([0, 1], dtype=np.int32)
        qc.flag_meanings = "good bad"
        qc[:] = np.zeros(len(times_epoch), dtype=np.int32)
    return path


def run() -> None:
    t0 = parse_utc(CASE["t_minus8_utc"]).timestamp()
    t1 = parse_utc(CASE["t_minus6_utc"]).timestamp()
    with tempfile.TemporaryDirectory(prefix="arm-sgp-selftest-") as tmp:
        root = Path(tmp)

        # Continuous 1 Hz source-day series for all three SASZE products.
        times = np.arange(np.floor(t0) - 5, np.ceil(t1) + 6, 1.0)
        paths = {}
        for stream, _, _ in STREAMS:
            paths[stream] = write_file(root, stream, times)
            row = audit_case(root, CASE, stream)
            assert row["disposition"] == "TWILIGHT_CONTIGUOUS", row
            assert row["median_positive_cadence_s"] == "1.000000", row
            assert float(row["max_internal_gap_s"]) == 1.0, row

        # The product roles are frozen independently of sampled values.
        vis = audit_case(root, CASE, PRIMARY_STREAM)
        assert vis["product_role"] == "PRIMARY_HELDOUT_SUPPORT", vis
        filter_row = audit_case(root, CASE, "sgpsaszefilterbandsC1.a1")
        assert filter_row["product_role"] == "DAYLIGHT_DERIVED_DIAGNOSTIC", filter_row
        assert "NOT_TWILIGHT_GATE" in filter_row["product_semantics"], filter_row

        # A broken same-day VIS companion fails the PRIMARY gate closed.
        broken = root / f"{PRIMARY_STREAM}.20240408.010000.nc"
        broken.write_bytes(b"not-a-netcdf-file")
        row = audit_case(root, CASE, PRIMARY_STREAM)
        assert row["disposition"] == "UNREADABLE", row
        assert "010000.nc" in row["read_errors"], row
        broken.unlink()

        # An openable VIS file lacking native-time semantics is unresolved.
        no_time = root / f"{PRIMARY_STREAM}.20240408.020000.nc"
        with netCDF4.Dataset(no_time, "w") as ds:
            ds.createDimension("record", 1)
            x = ds.createVariable("housekeeping_only", "f4", ("record",))
            x[:] = [1.0]
        row = audit_case(root, CASE, PRIMARY_STREAM)
        assert row["disposition"] == "UNREADABLE", row
        assert "NO_DECODABLE_NATIVE_TIME_COORDINATE" in row["read_errors"], row
        no_time.unlink()

        # Introduce a large hole only in VIS. Filterband continuity must not
        # rescue the primary held-out-observable gate.
        hole_start = t0 + 120.0
        hole_end = hole_start + 120.0
        times_gap = times[(times < hole_start) | (times > hole_end)]
        write_file(root, PRIMARY_STREAM, times_gap)
        row = audit_case(root, CASE, PRIMARY_STREAM)
        assert row["disposition"] == "TWILIGHT_DISCONTINUOUS", row
        assert float(row["max_internal_gap_s"]) > 2.0 * float(row["median_positive_cadence_s"]), row
        filter_row = audit_case(root, CASE, "sgpsaszefilterbandsC1.a1")
        assert filter_row["disposition"] == "TWILIGHT_CONTIGUOUS", filter_row

        # Readable VIS source-day data but no primary twilight samples.
        times_absent = np.asarray([t0 - 100.0, t0 - 50.0, t1 + 50.0, t1 + 100.0])
        write_file(root, PRIMARY_STREAM, times_absent)
        row = audit_case(root, CASE, PRIMARY_STREAM)
        assert row["disposition"] == "TWILIGHT_SAMPLES_ABSENT", row

        # Removing VIS is distinct from observational absence even when the
        # filterband diagnostic file remains present.
        paths[PRIMARY_STREAM].unlink()
        row = audit_case(root, CASE, PRIMARY_STREAM)
        assert row["disposition"] == "SOURCE_FILE_MISSING", row
        filter_row = audit_case(root, CASE, "sgpsaszefilterbandsC1.a1")
        assert filter_row["disposition"] == "TWILIGHT_CONTIGUOUS", filter_row

    print("PASS selftest_arm_compact_handoff")


if __name__ == "__main__":
    run()
