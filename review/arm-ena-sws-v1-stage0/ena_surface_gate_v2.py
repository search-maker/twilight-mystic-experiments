#!/usr/bin/env python3
"""Prospective result-blind E6 measured-wavelength ambiguity correction.

Governance: Issue #60 comments 5488714659 and 5488750527.
No ENA native E6 outcome had been opened when this correction was made.

The historical v1 E6 implementation is retained for provenance.  This layer
preserves every frozen v1 E6 threshold and calculation, but corrects one
schema-disposition defect in measured wavelength evidence:

* a wavelength-coordinate variable that mentions a spectral response is never
  itself a response function;
* conflicting same-hierarchy measured wavelength proofs are ambiguous and fail
  closed instead of silently accepting the first NetCDF variable encountered.

No SWS datastream is queried or read here.
"""
from __future__ import annotations

from typing import Any
import numpy as np

import ena_surface_gate_v1 as V1
from ena_surface_gate_v1 import *  # re-export frozen E6 public API

CENTER_TOL_NM = 1.0e-6


def _is_response_candidate(name: str, var: Any, token: str) -> bool:
    s = V1._semantic(name, var)
    low = name.lower()
    if token not in s or "nominal" in s:
        return False
    if low.startswith("qc_") or low.endswith("_qc"):
        return False
    # A spectral-response wavelength coordinate can contain the phrase
    # "spectral response" in metadata. It is a coordinate, not T(lambda).
    if "wavelength" in low or "lambda" in low:
        return False
    return any(x in s for x in (
        "normalized_transmittance", "normalized transmittance",
        "filter_response", "filter response", "spectral response",
        "relative response", "response function", "filter function",
        "transmission",
    ))


def _is_wavelength_candidate(name: str, var: Any, token: str) -> bool:
    s = V1._semantic(name, var)
    low = name.lower()
    if token not in s or "nominal" in s:
        return False
    if low.startswith("qc_") or low.endswith("_qc"):
        return False
    return "wavelength" in s or "lambda" in s


def _consistent_proof(candidates: list[dict[str, Any]], ambiguous_reason: str) -> dict[str, Any] | None:
    if not candidates:
        return None
    centers = np.asarray([float(x["center_nm"]) for x in candidates], dtype=float)
    if not np.all(np.isfinite(centers)):
        return {"ok": False, "reason": ambiguous_reason, "proof_candidates": candidates}
    if float(np.max(centers) - np.min(centers)) > CENTER_TOL_NM:
        return {"ok": False, "reason": ambiguous_reason, "proof_candidates": candidates}
    first = dict(candidates[0])
    first["center_nm"] = float(np.median(centers))
    first["proof_candidates"] = candidates
    if len(candidates) > 1:
        first["corroborating_proof_count"] = len(candidates)
    return first


def measured_center_from_dataset(ds: Any, filter_n: int, irradiance_var_name: str) -> dict[str, Any]:
    """Frozen E6 hierarchy with ambiguity fail-closed disposition.

    Hierarchy remains exactly #60 5488750527:
      1) measured response wavelength + response/transmittance;
      2) explicit native measured-CWL scalar;
      3) explicit measured-centroid attribute on the irradiance variable.

    Multiple usable proofs at one hierarchy level may corroborate only when
    their derived centers agree to numerical identity; conflicting proofs are
    schema-ambiguous and fail closed.  Lower hierarchy levels never rescue an
    ambiguous higher-level proof.
    """
    token = f"filter{filter_n}"

    waves = [(n, v) for n, v in ds.variables.items() if _is_wavelength_candidate(n, v, token)]
    responses = [(n, v) for n, v in ds.variables.items() if _is_response_candidate(n, v, token)]
    response_proofs: list[dict[str, Any]] = []
    for wn, wv in waves:
        for rn, rv in responses:
            try:
                wa = np.ma.asarray(wv[:]).reshape(-1)
                ra = np.ma.asarray(rv[:]).reshape(-1)
                if wa.size != ra.size:
                    continue
                if np.any(np.ma.getmaskarray(wa)) or np.any(np.ma.getmaskarray(ra)):
                    continue
                center = V1.response_weighted_center_nm(
                    np.ma.getdata(wa), np.ma.getdata(ra), getattr(wv, "units", "")
                )
            except Exception:
                continue
            if center is not None:
                response_proofs.append({
                    "ok": True,
                    "center_nm": float(center),
                    "evidence_type": "MEASURED_RESPONSE_WEIGHTED",
                    "evidence": [wn, rn],
                })
    proof = _consistent_proof(response_proofs, "MEASURED_RESPONSE_SCHEMA_AMBIGUOUS")
    if proof is not None:
        return proof

    cwl_proofs: list[dict[str, Any]] = []
    for name, var in ds.variables.items():
        s = V1._semantic(name, var)
        low = name.lower()
        if token not in s or "nominal" in s or low.startswith("qc_") or low.endswith("_qc"):
            continue
        if not (("cwl" in s and "measured" in s) or
                ("centroid" in s and ("wavelength" in s or "measured" in s))):
            continue
        try:
            raw = np.ma.asarray(var[:]).reshape(-1)
            data = np.asarray(np.ma.getdata(raw), dtype=float)
            mask = np.ma.getmaskarray(raw) | ~np.isfinite(data)
            vals = data[~mask]
            scale = V1._unit_scale_to_nm(getattr(var, "units", ""))
            if vals.size and scale is not None:
                centers = vals * scale
                if np.all(np.isfinite(centers)) and np.all(centers > 0):
                    cwl_proofs.append({
                        "ok": True,
                        "center_nm": float(np.median(centers)),
                        "evidence_type": "MEASURED_CWL_VARIABLE",
                        "evidence": [name],
                        "center_sample_count": int(centers.size),
                    })
        except Exception:
            continue
    proof = _consistent_proof(cwl_proofs, "MEASURED_CWL_SCHEMA_AMBIGUOUS")
    if proof is not None:
        return proof

    attr_proofs: list[dict[str, Any]] = []
    if irradiance_var_name in ds.variables:
        var = ds.variables[irradiance_var_name]
        for attr in ("centroid_wavelength", "measured_centroid_wavelength", "measured_CWL", "measured_cwl"):
            if not hasattr(var, attr):
                continue
            units = getattr(var, attr + "_units", None) or getattr(var, "wavelength_units", None)
            center = V1.parse_centroid_attribute(getattr(var, attr), units)
            if center is not None:
                attr_proofs.append({
                    "ok": True,
                    "center_nm": float(center),
                    "evidence_type": "MEASURED_CENTROID_ATTRIBUTE",
                    "evidence": [f"{irradiance_var_name}:{attr}"],
                })
    proof = _consistent_proof(attr_proofs, "MEASURED_CENTROID_ATTRIBUTE_AMBIGUOUS")
    if proof is not None:
        return proof

    return {"ok": False, "reason": "MEASURED_WAVELENGTH_EVIDENCE_MISSING_OR_AMBIGUOUS"}


# The frozen v1 computations call this function through their own module global.
# Patch only that schema-resolution primitive; thresholds/math remain v1.
V1.measured_center_from_dataset = measured_center_from_dataset

# Explicit public aliases make the prospective layer's intent obvious.
collect_narrowband = V1.collect_narrowband
evaluate_spectral_surface = V1.evaluate_spectral_surface
evaluate_surface_gate = V1.evaluate_surface_gate
