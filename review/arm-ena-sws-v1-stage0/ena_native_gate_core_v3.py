#!/usr/bin/env python3
"""Result-blind E4 MFRSR correction layer for ARM ENA/SWS V1.

Governance: Issue #60 comments 5488569132, 5489705401, 5490157179.
This prospective layer is frozen before any ENA native E4 outcome is opened.
It preserves E2-v2 plus reviewed E3/E5 primitives and corrects only the MFRSR
side of E4: native filter-2 identity must be proven by a measured spectral
response in the same native file whose response peak lies in 495..505 nm.
A scalar nominal/measured CWL alone is never sufficient.  This module never
reads SWS files or protected photometric values.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import re

import netCDF4
import numpy as np

import ena_native_gate_core_v2 as V2
from ena_native_gate_core_v2 import *  # preserve corrected E2 + public v1 primitives


def _var_text(name: str, var: netCDF4.Variable) -> str:
    return " ".join([
        name,
        str(getattr(var, "long_name", "")),
        str(getattr(var, "standard_name", "")),
        str(getattr(var, "description", "")),
        str(getattr(var, "comment", "")),
    ]).lower()


def _is_filter2_text(text: str) -> bool:
    compact = re.sub(r"[^a-z0-9]+", "", text.lower())
    return any(x in compact for x in ("filter2", "band2", "channel2"))


def _is_response_var(name: str, var: netCDF4.Variable) -> bool:
    text = _var_text(name, var)
    low = name.lower()
    if low.startswith("qc_") or low.endswith("_qc"):
        return False
    # A wavelength coordinate can legitimately mention the spectral response in
    # its metadata; it is still a coordinate, never the response function itself.
    if "wavelength" in low or "lambda" in low:
        return False
    if "aerosol_optical_depth" in text or "optical depth" in text:
        return False
    if "cwl" in text or "center wavelength" in text or "centre wavelength" in text:
        return False
    if not _is_filter2_text(text):
        return False
    return any(x in text for x in (
        "spectral response", "filter response", "relative response",
        "response function", "filter function", "transmission",
    ))


def _is_wavelength_var(name: str, var: netCDF4.Variable) -> bool:
    text = _var_text(name, var)
    low = name.lower()
    if low.startswith("qc_") or low.endswith("_qc"):
        return False
    return any(x in text for x in ("wavelength", "lambda"))


def _wavelength_nm(var: netCDF4.Variable) -> tuple[np.ndarray, np.ndarray] | None:
    raw = np.ma.asarray(var[:])
    data = np.asarray(np.ma.getdata(raw), dtype=float)
    mask = np.ma.getmaskarray(raw) | ~np.isfinite(data)
    units = str(getattr(var, "units", "")).strip().lower().replace("µ", "u").replace("μ", "u")
    name_text = _var_text(getattr(var, "name", ""), var)
    factor = None
    if units in ("nm", "nanometer", "nanometers", "nanometre", "nanometres"):
        factor = 1.0
    elif units in ("um", "micron", "microns", "micrometer", "micrometers", "micrometre", "micrometres"):
        factor = 1000.0
    elif units in ("m", "meter", "meters", "metre", "metres"):
        factor = 1.0e9
    elif units in ("angstrom", "angstroms", "a"):
        factor = 0.1
    elif not units and ("_nm" in str(getattr(var, "name", "")).lower() or " nanometer" in name_text or " nanometre" in name_text):
        factor = 1.0
    if factor is None:
        return None
    return data * factor, mask


def _associated_wavelength_names(ds: netCDF4.Dataset, response_name: str) -> list[str]:
    rv = ds.variables[response_name]
    names: list[str] = []
    for tok in str(getattr(rv, "coordinates", "")).replace(",", " ").split():
        if tok in ds.variables and _is_wavelength_var(tok, ds.variables[tok]):
            names.append(tok)
    for dim in rv.dimensions:
        if dim in ds.variables and _is_wavelength_var(dim, ds.variables[dim]):
            names.append(dim)
    for name, var in ds.variables.items():
        if not _is_wavelength_var(name, var):
            continue
        if name in rv.dimensions:
            names.append(name)
            continue
        if var.ndim == 1 and len(var) in rv.shape and (_is_filter2_text(_var_text(name, var)) or _is_filter2_text(_var_text(response_name, rv))):
            names.append(name)
    return sorted(set(names))


def _response_peak_proof(ds: netCDF4.Dataset) -> dict[str, Any]:
    response_names = sorted(n for n, v in ds.variables.items() if _is_response_var(n, v))
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for rname in response_names:
        rv = ds.variables[rname]
        rraw = np.ma.asarray(rv[:])
        rdata = np.asarray(np.ma.getdata(rraw), dtype=float)
        rmask = np.ma.getmaskarray(rraw) | ~np.isfinite(rdata)
        for wname in _associated_wavelength_names(ds, rname):
            wv = ds.variables[wname]
            converted = _wavelength_nm(wv)
            if converted is None:
                rejected.append({"response_variable": rname, "wavelength_variable": wname, "reason": "WAVELENGTH_UNITS_UNVERIFIED"})
                continue
            wdata, wmask = converted
            if wdata.ndim != 1 or wdata.size < 3:
                rejected.append({"response_variable": rname, "wavelength_variable": wname, "reason": "WAVELENGTH_AXIS_NOT_1D"})
                continue
            matching_axes = [i for i, n in enumerate(rv.shape) if n == wdata.size]
            named_axes = [i for i, d in enumerate(rv.dimensions) if d == wname]
            axes = named_axes if named_axes else matching_axes
            if len(axes) != 1:
                rejected.append({"response_variable": rname, "wavelength_variable": wname, "reason": "WAVELENGTH_AXIS_AMBIGUOUS"})
                continue
            ax = axes[0]
            moved = np.moveaxis(rdata, ax, -1).reshape(-1, wdata.size)
            mmoved = np.moveaxis(rmask, ax, -1).reshape(-1, wdata.size)
            w = wdata.reshape(-1)
            wm = wmask.reshape(-1)
            peaks: list[float] = []
            usable_rows = 0
            bad_row = False
            for row, rmaskrow in zip(moved, mmoved):
                valid = ~rmaskrow & ~wm & np.isfinite(row) & np.isfinite(w)
                if np.count_nonzero(valid) < 3:
                    continue
                usable_rows += 1
                rr = row[valid]
                ww = w[valid]
                mx = float(np.max(rr))
                peak_mask = np.isclose(rr, mx, rtol=1e-10, atol=max(1e-15, abs(mx) * 1e-12))
                pws = ww[peak_mask]
                if pws.size == 0:
                    bad_row = True
                    break
                peaks.extend(float(x) for x in pws)
            if bad_row or usable_rows == 0 or not peaks:
                rejected.append({"response_variable": rname, "wavelength_variable": wname, "reason": "NO_USABLE_MEASURED_RESPONSE_PROFILE"})
                continue
            candidates.append({
                "response_variable": rname,
                "wavelength_variable": wname,
                "usable_response_profiles": usable_rows,
                "peak_wavelength_min_nm": float(np.min(peaks)),
                "peak_wavelength_max_nm": float(np.max(peaks)),
                "peak_wavelength_median_nm": float(np.median(peaks)),
                "all_peaks_in_frozen_500nm_range": bool(np.all((np.asarray(peaks) >= 495.0) & (np.asarray(peaks) <= 505.0))),
            })
    if len(candidates) != 1:
        return {
            "verified": False,
            "reason": "FILTER2_MEASURED_RESPONSE_UNVERIFIED" if not candidates else "FILTER2_MEASURED_RESPONSE_AMBIGUOUS",
            "response_candidates": response_names,
            "pair_candidates": candidates,
            "rejected_pairs": rejected,
        }
    proof = dict(candidates[0])
    proof["verified"] = bool(proof["all_peaks_in_frozen_500NM_RANGE"] if "all_peaks_in_frozen_500NM_RANGE" in proof else proof["all_peaks_in_frozen_500nm_range"])
    proof["reason"] = "PASS" if proof["verified"] else "FILTER2_RESPONSE_PEAK_OUT_OF_FROZEN_500NM_RANGE"
    proof["response_candidates"] = response_names
    proof["rejected_pairs"] = rejected
    return proof


def analyze_mfrsr(path: Path, start: float, end: float, aeronet_median: float) -> dict[str, Any]:
    """Frozen E4 MFRSR analyzer with measured-response peak proof."""
    out: dict[str, Any] = {
        "stream": "MFRSR_AOD",
        "source_file": path.name,
        "sha256": sha256_file(path),
        "pass": False,
        "schema_ok": False,
        "e4_contract_version": "MFRSR_MEASURED_RESPONSE_PEAK_V3",
    }
    with netCDF4.Dataset(path) as ds:
        times = decode_times(ds)
        idx = in_window(times, start, end)
        name = "aerosol_optical_depth_filter2" if "aerosol_optical_depth_filter2" in ds.variables else None
        if idx.size == 0 or not name:
            out["reason"] = "NO_NATIVE_FILTER2_AOD_OR_SAMPLES"
            return out
        qc_name = "qc_" + name if "qc_" + name in ds.variables else (name + "_qc" if name + "_qc" in ds.variables else None)
        if not qc_name:
            out["reason"] = "NO_NATIVE_FILTER2_QC"
            return out

        proof = _response_peak_proof(ds)
        out["filter2_measured_response_proof"] = proof
        if not proof.get("verified"):
            out["reason"] = str(proof.get("reason", "FILTER2_MEASURED_RESPONSE_UNVERIFIED"))
            return out

        # Scalar measured CWL is recorded only as corroborative metadata.  It is
        # deliberately never used to establish the frozen 500-nm identity.
        if "filter2_CWL_measured" in ds.variables:
            craw = np.ma.asarray(ds.variables["filter2_CWL_measured"][:])
            cd = np.asarray(np.ma.getdata(craw), dtype=float).reshape(-1)
            cm = np.ma.getmaskarray(craw).reshape(-1) | ~np.isfinite(cd)
            vals_cwl = cd[~cm]
            if vals_cwl.size:
                out["filter2_cwl_measured_nm_corroborative"] = float(np.median(vals_cwl))

        a = np.ma.asarray(ds.variables[name][idx]).reshape(-1)
        q = np.ma.asarray(ds.variables[qc_name][idx]).reshape(-1)
        d = np.asarray(np.ma.getdata(a), dtype=float)
        qd = np.asarray(np.ma.getdata(q), dtype=float)
        mask = np.ma.getmaskarray(a) | np.ma.getmaskarray(q) | ~np.isfinite(d) | ~np.isfinite(qd) | (qd != 0)
        vals = d[~mask]
        out["schema_ok"] = True
        out["valid_count"] = int(vals.size)
        if not vals.size:
            out["reason"] = "NO_VALID_QC0_RETRIEVALS"
            return out
        med = float(np.median(vals))
        p10 = float(np.percentile(vals, 10))
        p90 = float(np.percentile(vals, 90))
        spread = p90 - p10
        diff = abs(med - float(aeronet_median))
        out.update({
            "median_aod500": med,
            "p10_aod500": p10,
            "p90_aod500": p90,
            "p90_minus_p10": spread,
            "abs_median_diff_vs_aeronet": diff,
        })
        out["pass"] = bool(vals.size >= 15 and spread <= 0.015 + 1e-12 and diff <= 0.020 + 1e-12)
        out["reason"] = "PASS" if out["pass"] else ("MIN_COUNT" if vals.size < 15 else ("STABILITY" if spread > 0.015 + 1e-12 else "CROSS_SOURCE_DISAGREEMENT"))
        return out
