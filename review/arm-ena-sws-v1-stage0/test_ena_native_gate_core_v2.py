#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt
import tempfile
from pathlib import Path

import netCDF4
import numpy as np

import ena_native_gate_core_v2 as G

UTC = dt.timezone.utc
BASE = dt.datetime(2019, 1, 1, tzinfo=UTC).timestamp()
START, END = BASE + 100, BASE + 200


def add_time(ds, n=31, step=10):
    ds.createDimension("time", n)
    t = ds.createVariable("time", "f8", ("time",))
    t.units = "seconds since 1970-01-01 00:00:00 UTC"
    t[:] = BASE + np.arange(n) * step


def make_arscl(path: Path, flag: int, radar_qc: int = 0):
    with netCDF4.Dataset(path, "w") as ds:
        add_time(ds)
        ds.createDimension("height", 2)
        src = ds.createVariable("cloud_source_flag", "i4", ("time", "height"), fill_value=-9999)
        src[:] = 1
        src[15, 0] = flag
        mpl = ds.createVariable("cloud_mask_mplzwang", "i4", ("time", "height"), fill_value=-9999)
        mpl[:] = 0
        base = ds.createVariable("cloud_base_best_estimate", "f4", ("time",), fill_value=-9999.0)
        base[:] = -9999.0
        refl = ds.createVariable("reflectivity_best_estimate", "f4", ("time", "height"), fill_value=-9999.0)
        refl[:] = -30.0
        qc = ds.createVariable("qc_reflectivity_best_estimate", "i4", ("time", "height"))
        qc[:] = 0
        qc[15, 0] = radar_qc


def make_raman(path: Path, cloud_base_value=None):
    with netCDF4.Dataset(path, "w") as ds:
        add_time(ds)
        ds.createDimension("height", 2)
        feat = ds.createVariable("feature_mask", "i4", ("time", "height"))
        feat[:] = 2  # aerosol only; no cloud bits
        base = ds.createVariable("cloud_base", "f4", ("time",), fill_value=-9999.0)
        base[:] = -9999.0
        if cloud_base_value is not None:
            base[15] = cloud_base_value
        ext = ds.createVariable("extinction", "f4", ("time", "height"), fill_value=-9999.0)
        ext[:] = 0.02
        qext = ds.createVariable("qc_extinction", "i4", ("time", "height"))
        qext[:] = 0


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        make_arscl(root / "flag5_good.nc", 5, radar_qc=0)
        f5 = G.analyze_arscl(root / "flag5_good.nc", START, END)
        assert f5["positive"], f5
        assert f5["cloud_source_radar_reliant_qc0_positive_cells"] == 1, f5

        make_arscl(root / "flag6.nc", 6, radar_qc=1)
        f6 = G.analyze_arscl(root / "flag6.nc", START, END)
        assert f6["positive"], f6
        assert f6["cloud_source_lidar_supported_positive_cells"] == 1, f6

        make_arscl(root / "flag5_badqc.nc", 5, radar_qc=1)
        f5bad = G.analyze_arscl(root / "flag5_badqc.nc", START, END)
        assert not f5bad["positive"], f5bad
        assert not f5bad["clear_evidence"], f5bad
        assert f5bad["cloud_source_radar_reliant_unresolved_cells"] == 1, f5bad
        assert f5bad["reason"] == "EVIDENCE_INSUFFICIENT", f5bad

        make_raman(root / "raman_base_cloud.nc", cloud_base_value=1200.0)
        rb = G.analyze_raman(root / "raman_base_cloud.nc", START, END)
        assert rb["cloud_positive"], rb
        assert rb["cloud_base_positive_cells"] == 1, rb
        assert rb["reason"] == "CLOUD_OR_HYDROMETEOR_PRESENT", rb

        make_raman(root / "raman_clear.nc")
        rc = G.analyze_raman(root / "raman_clear.nc", START, END)
        assert not rc["cloud_positive"], rc
        assert rc["cloud_clear_evidence"], rc
        assert rc["e3_profile_usable"], rc

        print("PASS ENA native E2 v2 frozen-contract synthetic tests")


if __name__ == "__main__":
    main()
