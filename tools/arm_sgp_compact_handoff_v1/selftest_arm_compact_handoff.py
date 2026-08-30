#!/usr/bin/env python3
"""Synthetic local self-test for the Phase-0 ARM SASZE native-time gate."""

from __future__ import annotations

import tempfile
from pathlib import Path

import netCDF4
import numpy as np

from audit_sasze_native_time import STREAM, audit_case, parse_utc

CASE = {
    "priority": "0",
    "case_id": "2024-04-08_dawn",
    "event": "dawn",
    "source_date_utc": "20240408",
    "t_minus8_utc": "2024-04-08T11:29:18.545002Z",
    "t_minus7_utc": "2024-04-08T11:34:27.589304Z",
    "t_minus6_utc": "2024-04-08T11:39:35.526412Z",
}


def write_file(root: Path, times_epoch: np.ndarray, suffix: str = "000000") -> Path:
    path = root / f"{STREAM}.20240408.{suffix}.nc"
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

        # Continuous 1 Hz source-day series bracketing both sub-second crossings.
        times = np.arange(np.floor(t0) - 5, np.ceil(t1) + 6, 1.0)
        good = write_file(root, times)
        row = audit_case(root, CASE)
        assert row["disposition"] == "TWILIGHT_CONTIGUOUS", row
        assert row["median_positive_cadence_s"] == "1.000000", row
        assert float(row["max_internal_gap_s"]) == 1.0, row

        # Any additional same-day source file that cannot be opened must force
        # UNREADABLE, even though another file by itself proves continuity. This
        # prevents a partially unreadable archive from contributing to an
        # observational-absence/HALT conclusion.
        broken = root / f"{STREAM}.20240408.010000.nc"
        broken.write_bytes(b"not-a-netcdf-file")
        row = audit_case(root, CASE)
        assert row["disposition"] == "UNREADABLE", row
        assert "010000.nc" in row["read_errors"], row
        broken.unlink()

        # A NetCDF file that opens but has no decodable native-time coordinate
        # is also unresolved rather than observationally absent.
        no_time = root / f"{STREAM}.20240408.020000.nc"
        with netCDF4.Dataset(no_time, "w") as ds:
            ds.createDimension("record", 1)
            x = ds.createVariable("housekeeping_only", "f4", ("record",))
            x[:] = [1.0]
        row = audit_case(root, CASE)
        assert row["disposition"] == "UNREADABLE", row
        assert "NO_DECODABLE_NATIVE_TIME_COORDINATE" in row["read_errors"], row
        no_time.unlink()

        # Introduce a 120-second hole inside the core; median source cadence remains 1 s.
        hole_start = t0 + 120.0
        hole_end = hole_start + 120.0
        times_gap = times[(times < hole_start) | (times > hole_end)]
        write_file(root, times_gap)
        row = audit_case(root, CASE)
        assert row["disposition"] == "TWILIGHT_DISCONTINUOUS", row
        assert float(row["max_internal_gap_s"]) > 2.0 * float(row["median_positive_cadence_s"]), row

        # Samples on the source day but none in the core => observational absence, not missing file.
        times_absent = np.asarray([t0 - 100.0, t0 - 50.0, t1 + 50.0, t1 + 100.0])
        write_file(root, times_absent)
        row = audit_case(root, CASE)
        assert row["disposition"] == "TWILIGHT_SAMPLES_ABSENT", row

        # Removing the source file must remain distinct from observational absence.
        good.unlink()
        row = audit_case(root, CASE)
        assert row["disposition"] == "SOURCE_FILE_MISSING", row

    print("PASS selftest_arm_compact_handoff")


if __name__ == "__main__":
    run()
