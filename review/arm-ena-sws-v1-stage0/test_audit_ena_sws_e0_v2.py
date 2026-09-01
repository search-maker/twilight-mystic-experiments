#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path

import netCDF4
import numpy as np

import audit_ena_sws_e0_v2 as E0

UTC = dt.timezone.utc
DAY = dt.date(2018, 5, 6)
BASE = dt.datetime(2018, 5, 6, 20, 0, 0, tzinfo=UTC).timestamp()
CENTERS = [BASE + 0, BASE + 600, BASE + 1200]  # -8, -7, -6
OFFSETS = np.asarray([-30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30], dtype=float)


def iso(x: float) -> str:
    return dt.datetime.fromtimestamp(x, UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def event() -> E0.Event:
    return E0.Event(
        case_id="2018-05-06_dusk",
        local_civil_date="2018-05-06",
        event="dusk",
        t_minus8_utc=iso(CENTERS[0]),
        t_minus7_utc=iso(CENTERS[1]),
        t_minus6_utc=iso(CENTERS[2]),
    )


def write_file(path: Path, bad_offsets: set[int]) -> None:
    times = np.concatenate([c + OFFSETS for c in CENTERS])
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", times.size)
        ds.createDimension("wavelength", 2)

        t = ds.createVariable("time", "f8", ("time",))
        t.standard_name = "time"
        t.units = "seconds since 1970-01-01 00:00:00 UTC"
        t[:] = times

        w = ds.createVariable("wavelength", "f8", ("wavelength",))
        w.standard_name = "radiation_wavelength"
        w.units = "nm"
        w[:] = [550.0, 870.0]

        # This protected field exists to model the real file.  The E0 auditor
        # is not permitted to access its values; the test deliberately makes
        # eligibility decidable entirely from time/wavelength/QC.
        rad = ds.createVariable("zenith_radiance", "f4", ("time", "wavelength"), fill_value=-9999.0)
        rad.units = "W m-2 nm-1 sr-1"
        rad[:] = 123.456

        qc = ds.createVariable("qc_sample", "i4", ("time", "wavelength"))
        qc.long_name = "Data quality flag for native spectral sample"
        q = np.zeros((times.size, 2), dtype=np.int32)
        pos = 0
        for _center in CENTERS:
            for off in OFFSETS.astype(int).tolist():
                if off in bad_offsets:
                    q[pos, 0] = 1
                pos += 1
        qc[:] = q


def run_case(root: Path, filename: str, bad_offsets: set[int]) -> dict:
    path = root / filename
    write_file(path, bad_offsets)
    return E0.audit(event(), root, {DAY.strftime("%Y%m%d"): [path]})


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        good = run_case(root, "enaswsC1.b1.20180506.000000.cdf", set())
        assert good["timing_pass"], good
        assert good["validity_pass"], good
        assert good["primary_holdout_eligible_after_e0"], good
        for a in ("minus8", "minus7", "minus6"):
            assert good[f"safe_qc_valid_samples_within_5s_{a}"] == 3, good
            assert good[f"safe_qc_valid_samples_within_30s_{a}"] == 13, good

        # Historical v1's >=5-good-in-30 rule could pass this configuration,
        # despite every native sample inside +/-5 s being bad.  Frozen Stage-0
        # requires a structurally usable member of the required +/-5-s set.
        no_good_near = run_case(
            root, "enaswsC1.b1.20180506.000001.cdf", {-5, 0, 5}
        )
        assert no_good_near["timing_pass"], no_good_near
        assert not no_good_near["validity_pass"], no_good_near
        assert no_good_near["disposition"] == "E0_SAFE_QC_VALIDITY_FAIL", no_good_near
        for a in ("minus8", "minus7", "minus6"):
            assert no_good_near[f"safe_qc_valid_samples_within_5s_{a}"] == 0, no_good_near
            assert no_good_near[f"safe_qc_valid_samples_within_30s_{a}"] == 10, no_good_near

        # Also lock the frozen >=10 usable samples within +/-30 s.  Nine good
        # native rows are insufficient even though the raw timestamp density
        # itself is 13 and the old implementation's arbitrary threshold was 5.
        only_nine = run_case(
            root, "enaswsC1.b1.20180506.000002.cdf", {-30, -25, 25, 30}
        )
        assert only_nine["timing_pass"], only_nine
        assert not only_nine["validity_pass"], only_nine
        assert only_nine["disposition"] == "E0_SAFE_QC_VALIDITY_FAIL", only_nine
        for a in ("minus8", "minus7", "minus6"):
            assert only_nine[f"safe_qc_valid_samples_within_5s_{a}"] == 3, only_nine
            assert only_nine[f"safe_qc_valid_samples_within_30s_{a}"] == 9, only_nine

        print("PASS ENA SWS E0 v2 frozen usable-anchor 1/10 synthetic contracts")


if __name__ == "__main__":
    main()
