#!/usr/bin/env python3
"""Result-blind E2 correction layer for ARM ENA/SWS V1.

Governance: Issue #60 comment 5488569132 froze these semantics before any ENA
native outcome was opened.  This module preserves the reviewed v1 primitives for
E3/E4/E5 and overrides only the two E2 parsers whose implementation did not
fully match that frozen contract.  It never reads SWS files.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np

import ena_native_gate_core_v1 as V1
from ena_native_gate_core_v1 import *  # re-export frozen public primitives


def _cloud_base_names(ds: netCDF4.Dataset) -> list[str]:
    """Return science cloud/hydrometeor-base fields, never their QC variables."""
    out: list[str] = []
    needles = (
        "cloud_base", "cloud base", "cloud_layer_base", "cloud layer base",
        "hydrometeor_layer_base", "hydrometeor layer base",
    )
    for name, var in ds.variables.items():
        low = name.lower()
        if low.startswith("qc_") or low.endswith("_qc"):
            continue
        text = " ".join([
            name,
            str(getattr(var, "long_name", "")),
            str(getattr(var, "standard_name", "")),
            str(getattr(var, "description", "")),
        ]).lower()
        if any(x in text for x in needles):
            out.append(name)
    return sorted(set(out))


def _finite_nonnegative_count(ds: netCDF4.Dataset, names: list[str], idx: np.ndarray, ntime: int) -> int:
    total = 0
    for name in names:
        arr = V1._take_time(ds.variables[name], idx, ntime)
        if arr is None:
            continue
        data = np.asarray(np.ma.getdata(arr), dtype=float)
        mask = np.ma.getmaskarray(arr) | ~np.isfinite(data)
        total += int(np.count_nonzero((data >= 0.0) & ~mask))
    return total


def analyze_arscl(path: Path, start: float, end: float) -> dict[str, Any]:
    """Apply the prospectively frozen ARSCL cloud veto exactly/fail-closed.

    cloud_source_flag 2..6 is cloud-positive.  Flags 3 and 5 are radar-reliant,
    so they are usable as a veto only where the corresponding source
    reflectivity is finite and its native QC is explicitly 0.  Flags 2, 4 and 6
    have independent lidar support and remain positive without relying on radar.
    Flag 0, masked cells, unknown flags, or radar-reliant detections without good
    source QC prevent a clear disposition.
    """
    out = {
        "stream": "ARSCL", "source_file": path.name,
        "sha256": V1.sha256_file(path), "positive": False,
        "clear_evidence": False, "schema_ok": False,
    }
    with netCDF4.Dataset(path) as ds:
        times = V1.decode_times(ds)
        idx = V1.in_window(times, start, end)
        cont = V1.continuity(times, start, end)
        out["continuity"] = cont
        if idx.size == 0:
            out["reason"] = "NO_GUARD_SAMPLES"
            return out

        src = V1._candidate(ds, ["cloud_source_flag"])
        mpl = V1._candidate(ds, ["cloud_mask_mplzwang"])
        bases = _cloud_base_names(ds)
        if not src:
            out["reason"] = "NO_CLOUD_SOURCE_FLAG"
            return out

        arr = V1._take_time(ds.variables[src], idx, times.size)
        if arr is None:
            out["reason"] = "CLOUD_SOURCE_LAYOUT_UNSUPPORTED"
            return out
        data = np.asarray(np.ma.getdata(arr), dtype=float)
        mask = np.ma.getmaskarray(arr) | ~np.isfinite(data)
        flags = np.where(mask, -999999, data).astype(int)
        out["schema_ok"] = True

        missing_mask = mask | ((flags == 0) & ~mask)
        clear_mask = (flags == 1) & ~mask
        lidar_supported = np.isin(flags, [2, 4, 6]) & ~mask
        radar_reliant = np.isin(flags, [3, 5]) & ~mask
        unknown_flag = (~mask) & ~np.isin(flags, [0, 1, 2, 3, 4, 5, 6])

        radar_valid = np.zeros(flags.shape, dtype=bool)
        radar_schema = None
        for refl_name, qc_name in (
            ("reflectivity_best_estimate", "qc_reflectivity_best_estimate"),
            ("reflectivity", "qc_reflectivity"),
        ):
            if refl_name not in ds.variables or qc_name not in ds.variables:
                continue
            rpair = V1._same_shape_data(V1._take_time(ds.variables[refl_name], idx, times.size), flags.shape)
            qpair = V1._same_shape_data(V1._take_time(ds.variables[qc_name], idx, times.size), flags.shape)
            if rpair is None or qpair is None:
                continue
            _, rmask = rpair
            qdata, qmask = qpair
            radar_valid = radar_reliant & ~rmask & ~qmask & (qdata == 0)
            radar_schema = f"{refl_name}+{qc_name}"
            break

        radar_unresolved = radar_reliant & ~radar_valid
        supported_positive = lidar_supported | radar_valid
        out.update({
            "cloud_source_supported_positive_cells": int(np.count_nonzero(supported_positive)),
            "cloud_source_lidar_supported_positive_cells": int(np.count_nonzero(lidar_supported)),
            "cloud_source_radar_reliant_qc0_positive_cells": int(np.count_nonzero(radar_valid)),
            "cloud_source_radar_reliant_unresolved_cells": int(np.count_nonzero(radar_unresolved)),
            # Back-compatible keys consumed by existing audit/report code.
            "cloud_source_radar_only_qc0_positive_cells": int(np.count_nonzero(radar_valid)),
            "cloud_source_radar_only_unresolved_cells": int(np.count_nonzero(radar_unresolved)),
            "cloud_source_unsupported_flag5_6_cells": 0,
            "cloud_source_missing_cells": int(np.count_nonzero(missing_mask)),
            "cloud_source_unknown_flag_cells": int(np.count_nonzero(unknown_flag)),
            "cloud_source_clear_cells": int(np.count_nonzero(clear_mask)),
            "radar_qc_schema": radar_schema,
        })

        positive = bool(np.any(supported_positive))
        mplpos = 0
        if mpl:
            marr = V1._take_time(ds.variables[mpl], idx, times.size)
            if marr is not None:
                md = np.asarray(np.ma.getdata(marr), dtype=float)
                mm = np.ma.getmaskarray(marr) | ~np.isfinite(md)
                mplpos = int(np.count_nonzero((md == 1) & ~mm))
                positive |= mplpos > 0
        out["mpl_cloud_cells"] = mplpos

        basepos = _finite_nonnegative_count(ds, bases, idx, times.size)
        out["cloud_base_variables"] = bases
        out["cloud_base_positive_cells"] = basepos
        positive |= basepos > 0

        unresolved = bool(
            np.any(missing_mask) or np.any(radar_unresolved) or np.any(unknown_flag)
        )
        out["positive"] = positive
        out["clear_evidence"] = bool(
            not positive and not unresolved and np.any(clear_mask) and cont["pass"]
        )
        out["reason"] = (
            "CLOUD_OR_HYDROMETEOR_PRESENT" if positive
            else ("CLEAR" if out["clear_evidence"] else "EVIDENCE_INSUFFICIENT")
        )
        return out


def analyze_raman(path: Path, start: float, end: float) -> dict[str, Any]:
    """Apply frozen Raman E2 veto, including independent cloud-base fields."""
    out = {
        "stream": "RAMAN", "source_file": path.name,
        "sha256": V1.sha256_file(path), "cloud_positive": False,
        "cloud_clear_evidence": False, "e3_profile_usable": False,
        "schema_ok": False,
    }
    with netCDF4.Dataset(path) as ds:
        times = V1.decode_times(ds)
        idx = V1.in_window(times, start, end)
        cont = V1.continuity(times, start, end)
        out["continuity"] = cont
        if idx.size == 0:
            out["reason"] = "NO_GUARD_SAMPLES"
            return out

        bases = _cloud_base_names(ds)
        basepos = _finite_nonnegative_count(ds, bases, idx, times.size)
        out["cloud_base_variables"] = bases
        out["cloud_base_positive_cells"] = basepos

        feat = V1._feature_var(ds)
        if not feat:
            out["schema_ok"] = bool(bases)
            out["cloud_positive"] = basepos > 0
            out["reason"] = (
                "CLOUD_OR_HYDROMETEOR_PRESENT" if out["cloud_positive"]
                else "NO_FEATURE_MASK_OR_CLEAR_EVIDENCE"
            )
            return out

        arr = V1._take_time(ds.variables[feat], idx, times.size)
        if arr is None:
            out["schema_ok"] = bool(bases)
            out["cloud_positive"] = basepos > 0
            out["reason"] = (
                "CLOUD_OR_HYDROMETEOR_PRESENT" if out["cloud_positive"]
                else "FEATURE_MASK_LAYOUT_UNSUPPORTED"
            )
            return out

        raw = np.asarray(np.ma.getdata(arr), dtype=float)
        mask = np.ma.getmaskarray(arr) | ~np.isfinite(raw)
        data = np.where(mask, 0, raw).astype(np.int64)
        valid = data[~mask]
        cloud = int(np.count_nonzero((valid & V1.CLOUD_BITS) != 0))
        aerosol = int(np.count_nonzero((valid & V1.AEROSOL_BIT) != 0))
        out["schema_ok"] = True
        out.update({"cloud_feature_cells": cloud, "aerosol_feature_cells": aerosol})
        out["cloud_positive"] = bool(cloud > 0 or basepos > 0)
        out["cloud_clear_evidence"] = bool(
            not out["cloud_positive"] and valid.size > 0 and cont["pass"]
        )

        usable = []
        for name in ("extinction", "particulate_backscatter", "backscatter", "depolarization_ratio"):
            if name not in ds.variables:
                continue
            aval = V1._take_time(ds.variables[name], idx, times.size)
            if aval is None:
                continue
            vals = np.asarray(np.ma.getdata(aval), dtype=float)
            vmask = np.ma.getmaskarray(aval) | ~np.isfinite(vals)
            qc = V1._qc_for(ds, name)
            if qc is not None:
                qa = V1._take_time(qc, idx, times.size)
                if qa is not None and qa.shape == vals.shape:
                    qd = np.asarray(np.ma.getdata(qa), dtype=float)
                    qm = np.ma.getmaskarray(qa) | ~np.isfinite(qd)
                    vmask |= qm | (qd != 0)
                else:
                    vmask |= True
            else:
                vmask |= True
            if vals.shape == data.shape:
                aerosol_mask = (
                    ((data & V1.AEROSOL_BIT) != 0)
                    & ((data & V1.CLOUD_BITS) == 0)
                    & ~mask
                )
                count = int(np.count_nonzero(aerosol_mask & ~vmask))
                usable.append((name, count))
                out[name + "_usable_aerosol_cells"] = count

        out["e3_profile_usable"] = bool(
            cont["pass"] and aerosol > 0 and any(c > 0 for _, c in usable)
        )
        out["reason"] = (
            "CLOUD_OR_HYDROMETEOR_PRESENT" if out["cloud_positive"]
            else ("PROFILE_USABLE" if out["e3_profile_usable"] else "PROFILE_EVIDENCE_INSUFFICIENT")
        )
        return out
