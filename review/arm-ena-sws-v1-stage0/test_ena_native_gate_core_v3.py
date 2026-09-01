#!/usr/bin/env python3
"""Synthetic result-blind contracts for the prospective E4 MFRSR v3 fix."""
from __future__ import annotations
import datetime as dt
import tempfile
from pathlib import Path

import netCDF4
import numpy as np

import ena_native_gate_core_v3 as G

UTC = dt.timezone.utc
BASE = dt.datetime(2019, 1, 1, tzinfo=UTC).timestamp()


def make_mfrsr(path: Path, *, peak_nm: float = 500.0, include_response: bool = True, ambiguous: bool = False, wavelength_units: str = "nm") -> None:
    n = 20
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", n)
        t = ds.createVariable("time", "f8", ("time",))
        t.units = "seconds since 1970-01-01 00:00:00 UTC"
        t[:] = BASE + np.arange(n) * 20.0
        a = ds.createVariable("aerosol_optical_depth_filter2", "f4", ("time",), fill_value=-9999.0)
        a[:] = 0.08
        q = ds.createVariable("qc_aerosol_optical_depth_filter2", "i4", ("time",))
        q[:] = 0
        c = ds.createVariable("filter2_CWL_measured", "f4")
        c.long_name = "measured center wavelength filter2"
        c.assignValue(500.0)
        if include_response:
            ds.createDimension("filter2_wavelength", 9)
            w = ds.createVariable("filter2_wavelength", "f4", ("filter2_wavelength",))
            w.long_name = "measured wavelength for filter2 spectral response"
            w.units = wavelength_units
            wn = np.arange(480.0, 525.0, 5.0)
            w[:] = wn if wavelength_units == "nm" else wn / 1000.0
            r = ds.createVariable("filter2_measured_spectral_response", "f4", ("filter2_wavelength",))
            r.long_name = "measured filter2 spectral response"
            r.coordinates = "filter2_wavelength"
            r[:] = np.exp(-0.5 * ((wn - peak_nm) / 4.0) ** 2)
            if ambiguous:
                r2 = ds.createVariable("filter2_measured_filter_response", "f4", ("filter2_wavelength",))
                r2.long_name = "measured filter2 filter response"
                r2.coordinates = "filter2_wavelength"
                r2[:] = r[:]


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        good = root / "good.nc"
        make_mfrsr(good, peak_nm=500.0)
        g = G.analyze_mfrsr(good, BASE, BASE + 1000.0, 0.07)
        assert g["pass"], g
        proof = g["filter2_measured_response_proof"]
        assert proof["verified"] and 495.0 <= proof["peak_wavelength_median_nm"] <= 505.0, proof

        wrong = root / "wrong.nc"
        make_mfrsr(wrong, peak_nm=510.0)
        w = G.analyze_mfrsr(wrong, BASE, BASE + 1000.0, 0.07)
        assert not w["pass"] and w["reason"] == "FILTER2_RESPONSE_PEAK_OUT_OF_FROZEN_500NM_RANGE", w
        # Scalar CWL=500 must not rescue an actual measured response that peaks at 510.
        assert w.get("filter2_cwl_measured_nm_corroborative") is None or w.get("filter2_cwl_measured_nm_corroborative") == 500.0

        missing = root / "missing.nc"
        make_mfrsr(missing, include_response=False)
        m = G.analyze_mfrsr(missing, BASE, BASE + 1000.0, 0.07)
        assert not m["pass"] and m["reason"] == "FILTER2_MEASURED_RESPONSE_UNVERIFIED", m

        amb = root / "ambiguous.nc"
        make_mfrsr(amb, ambiguous=True)
        a = G.analyze_mfrsr(amb, BASE, BASE + 1000.0, 0.07)
        assert not a["pass"] and a["reason"] == "FILTER2_MEASURED_RESPONSE_AMBIGUOUS", a

        micron = root / "micron.nc"
        make_mfrsr(micron, peak_nm=500.0, wavelength_units="um")
        u = G.analyze_mfrsr(micron, BASE, BASE + 1000.0, 0.07)
        assert u["pass"], u

    print("PASS ENA native E4 v3 measured-response frozen-contract synthetic tests")


if __name__ == "__main__":
    main()
