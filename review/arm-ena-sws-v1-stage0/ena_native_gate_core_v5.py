#!/usr/bin/env python3
"""Prospective result-blind E3 vertical-shape support correction layer.

Governance: Issue #60 comments 5487647692 and 5488569132 freeze E3 before any
ENA native E3 outcome.  This layer preserves E2-v2, E4-v3, E5-v4 and all other
reviewed primitives.  It only makes the already-frozen E3 requirement for a
QC-valid *vertical aerosol shape* with native common vertical support explicit.

Historical E3 could set `e3_profile_usable` from any one QC-good aerosol cell
of extinction, backscatter, or even depolarization without proving a native
vertical coordinate.  Depolarization alone is not a vertical extinction/
backscatter shape that can be normalized to independent column AOD.  V5 fails
closed on that schema ambiguity; no new scientific threshold is introduced.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import netCDF4
import numpy as np

import ena_native_gate_core_v1 as V1
import ena_native_gate_core_v2 as V2
import ena_native_gate_core_v4 as V4
from ena_native_gate_core_v4 import *

SHAPE_VARIABLES = ("extinction", "particulate_backscatter", "backscatter")
AUXILIARY_OPTICAL_VARIABLES = ("depolarization_ratio",)


def _vertical_semantic(name: str, var: netCDF4.Variable) -> bool:
    text = " ".join([
        name,
        str(getattr(var, "long_name", "")),
        str(getattr(var, "standard_name", "")),
        str(getattr(var, "description", "")),
        str(getattr(var, "axis", "")),
        str(getattr(var, "positive", "")),
    ]).lower()
    return any(tok in text for tok in (
        "height", "altitude", "range", "distance above", "distance from",
        "vertical coordinate", "above sea level", "above ground",
    )) or str(getattr(var, "axis", "")).strip().upper() == "Z"


def _vertical_dimension_info(ds: netCDF4.Dataset, science_name: str) -> dict[str, Any]:
    """Prove one native vertical dimension/coordinate for a science variable.

    We do not infer height from array ordinal.  A non-time dimension must be
    explicitly tied to at least one 1-D native coordinate variable with
    vertical semantics and finite coordinate values.  Multiple coordinate
    variables on the same dimension are harmless corroboration; multiple
    distinct vertical dimensions are ambiguous and fail closed.
    """
    var = ds.variables[science_name]
    dims = tuple(var.dimensions)
    dim_candidates: dict[str, list[str]] = {}

    for dim in dims:
        if dim == "time":
            continue
        names: list[str] = []
        if dim in ds.variables:
            cv = ds.variables[dim]
            if tuple(cv.dimensions) == (dim,) and _vertical_semantic(dim, cv):
                names.append(dim)
        for cname, cv in ds.variables.items():
            if cname == dim:
                continue
            if tuple(cv.dimensions) != (dim,):
                continue
            if _vertical_semantic(cname, cv):
                names.append(cname)
        if names:
            dim_candidates[dim] = sorted(set(names), key=lambda n: (n != dim, n))

    if len(dim_candidates) != 1:
        return {
            "ok": False,
            "reason": "VERTICAL_DIMENSION_MISSING_OR_AMBIGUOUS",
            "vertical_dimension_candidates": sorted(dim_candidates),
        }

    dim, coord_names = next(iter(dim_candidates.items()))
    axis = dims.index(dim)
    usable_coords: list[dict[str, Any]] = []
    for cname in coord_names:
        cv = ds.variables[cname]
        try:
            raw = np.ma.asarray(cv[:]).reshape(-1)
            data = np.asarray(np.ma.getdata(raw), dtype=float)
            mask = np.ma.getmaskarray(raw) | ~np.isfinite(data)
        except Exception:
            continue
        if data.size != len(ds.dimensions[dim]):
            continue
        if not np.any(~mask):
            continue
        usable_coords.append({
            "name": cname,
            "finite_count": int(np.count_nonzero(~mask)),
            "data": data,
            "mask": mask,
        })
    if not usable_coords:
        return {
            "ok": False,
            "reason": "VERTICAL_COORDINATE_NO_FINITE_VALUES",
            "vertical_dimension": dim,
            "coordinate_candidates": coord_names,
        }
    return {
        "ok": True,
        "vertical_dimension": dim,
        "vertical_axis": axis,
        "coordinate_candidates": [x["name"] for x in usable_coords],
        "coordinates": usable_coords,
    }


def _support_levels(mask: np.ndarray, axis: int) -> np.ndarray:
    """Return a boolean vector of vertical indices with any supported cell."""
    if mask.ndim == 0 or axis < 0 or axis >= mask.ndim:
        return np.zeros(0, dtype=bool)
    reduce_axes = tuple(i for i in range(mask.ndim) if i != axis)
    if not reduce_axes:
        return mask.astype(bool)
    return np.any(mask, axis=reduce_axes)


def _vertical_support_for_variable(
    ds: netCDF4.Dataset,
    name: str,
    idx: np.ndarray,
    ntime: int,
    aerosol_mask: np.ndarray,
) -> dict[str, Any]:
    aval = V1._take_time(ds.variables[name], idx, ntime)
    if aval is None:
        return {"ok": False, "reason": "SCIENCE_TIME_LAYOUT_UNSUPPORTED", "variable": name}
    vals = np.asarray(np.ma.getdata(aval), dtype=float)
    vmask = np.ma.getmaskarray(aval) | ~np.isfinite(vals)
    if vals.shape != aerosol_mask.shape:
        return {"ok": False, "reason": "SCIENCE_FEATURE_MASK_SHAPE_MISMATCH", "variable": name}

    qc = V1._qc_for(ds, name)
    if qc is None:
        return {"ok": False, "reason": "SCIENCE_NATIVE_QC_MISSING", "variable": name}
    qa = V1._take_time(qc, idx, ntime)
    if qa is None or qa.shape != vals.shape:
        return {"ok": False, "reason": "SCIENCE_NATIVE_QC_LAYOUT_UNSUPPORTED", "variable": name}
    qd = np.asarray(np.ma.getdata(qa), dtype=float)
    qmask = np.ma.getmaskarray(qa) | ~np.isfinite(qd)
    usable_cells = aerosol_mask & ~vmask & ~qmask & (qd == 0)
    cell_count = int(np.count_nonzero(usable_cells))
    if cell_count == 0:
        return {"ok": False, "reason": "NO_QC0_AEROSOL_CELLS", "variable": name, "usable_cell_count": 0}

    vinfo = _vertical_dimension_info(ds, name)
    if not vinfo.get("ok"):
        return {
            "ok": False,
            "reason": vinfo.get("reason", "VERTICAL_SUPPORT_UNRESOLVED"),
            "variable": name,
            "usable_cell_count": cell_count,
            "vertical_evidence": vinfo,
        }

    levels = _support_levels(usable_cells, int(vinfo["vertical_axis"]))
    if levels.size == 0:
        return {"ok": False, "reason": "VERTICAL_SUPPORT_UNRESOLVED", "variable": name, "usable_cell_count": cell_count}

    chosen = None
    for c in vinfo["coordinates"]:
        coord_valid = ~np.asarray(c["mask"], dtype=bool)
        if coord_valid.shape == levels.shape and np.any(levels & coord_valid):
            chosen = c
            break
    if chosen is None:
        return {
            "ok": False,
            "reason": "NO_FINITE_VERTICAL_COORDINATE_AT_USABLE_AEROSOL_LEVEL",
            "variable": name,
            "usable_cell_count": cell_count,
        }

    supported = levels & ~np.asarray(chosen["mask"], dtype=bool)
    return {
        "ok": True,
        "variable": name,
        "usable_cell_count": cell_count,
        "usable_vertical_level_count": int(np.count_nonzero(supported)),
        "vertical_dimension": vinfo["vertical_dimension"],
        "vertical_coordinate": chosen["name"],
        "vertical_coordinate_candidates": vinfo["coordinate_candidates"],
    }


def analyze_raman(path: Path, start: float, end: float) -> dict[str, Any]:
    """Preserve corrected E2 Raman veto and fail-close E3 vertical-shape proof."""
    # Use the already-reviewed E2-v2 implementation directly. It determines
    # cloud veto/clear evidence and historical optical QC counts without SWS.
    base = V2.analyze_raman(path, start, end)
    base["e3_profile_usable"] = False
    base["e3_shape_basis"] = None
    base["e3_vertical_support"] = []

    if base.get("cloud_positive"):
        base["reason"] = "CLOUD_OR_HYDROMETEOR_PRESENT"
        return base
    if not base.get("continuity", {}).get("pass"):
        base["reason"] = "PROFILE_EVIDENCE_INSUFFICIENT"
        return base

    with netCDF4.Dataset(path) as ds:
        times = V1.decode_times(ds)
        idx = V1.in_window(times, start, end)
        feat = V1._feature_var(ds)
        if idx.size == 0 or not feat:
            base["reason"] = "PROFILE_EVIDENCE_INSUFFICIENT"
            return base
        arr = V1._take_time(ds.variables[feat], idx, times.size)
        if arr is None:
            base["reason"] = "PROFILE_EVIDENCE_INSUFFICIENT"
            return base
        raw = np.asarray(np.ma.getdata(arr), dtype=float)
        fmask = np.ma.getmaskarray(arr) | ~np.isfinite(raw)
        data = np.where(fmask, 0, raw).astype(np.int64)
        aerosol_mask = (
            ((data & V1.AEROSOL_BIT) != 0)
            & ((data & V1.CLOUD_BITS) == 0)
            & ~fmask
        )
        if not np.any(aerosol_mask):
            base["reason"] = "PROFILE_EVIDENCE_INSUFFICIENT"
            return base

        support: list[dict[str, Any]] = []
        for name in SHAPE_VARIABLES:
            if name not in ds.variables:
                continue
            support.append(_vertical_support_for_variable(ds, name, idx, times.size, aerosol_mask))
        base["e3_vertical_support"] = support

        usable = [x for x in support if x.get("ok")]
        if usable:
            # Deterministic pre-value semantic preference follows SHAPE_VARIABLES.
            chosen = usable[0]
            base["e3_profile_usable"] = True
            base["e3_shape_basis"] = chosen["variable"]
            base["e3_vertical_coordinate"] = chosen["vertical_coordinate"]
            base["e3_usable_vertical_level_count"] = chosen["usable_vertical_level_count"]
            base["reason"] = "PROFILE_USABLE"
        else:
            # Depolarization remains useful auxiliary optical information but can
            # never be the sole normalized vertical shape basis.
            base["e3_profile_usable"] = False
            base["reason"] = "PROFILE_EVIDENCE_INSUFFICIENT"
    return base
