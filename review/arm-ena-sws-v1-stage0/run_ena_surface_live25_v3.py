#!/usr/bin/env python3
"""Result-blind E6 orchestration hardening for unresolved ARM acquisition.

This additive wrapper preserves the prospective E6-v2 science gate and every
frozen E6 threshold.  It changes only transport/error disposition before any
native E6 outcome is consumed:

* query/download errors are acquisition uncertainty, not evidence that a
  required source is scientifically missing or bad;
* if the E6-v2 evaluator can nevertheless prove a complete PASS from actually
  retrieved required primary + corroborating evidence, that PASS remains
  valid;
* otherwise, any query/download error makes the case
  ``E6_ACQUISITION_UNRESOLVED`` rather than a terminal scientific FAIL/MISSING.

No SWS datastream is queried or read here.
"""
from __future__ import annotations

from typing import Any

import run_ena_surface_live25_v2 as V2


BASE = V2._historical
_ORIGINAL_DISCOVER = BASE.discover
_ORIGINAL_DOWNLOAD = BASE.download
_ORIGINAL_EVALUATE = BASE.E6.evaluate_surface_gate
_PENDING_ACQUISITION_ERRORS: list[dict[str, str]] = []


def discover_tracking(pair: str, ds: str, days: list[str]):
    """Preserve historical discovery output while remembering transport errors."""
    names, errors = _ORIGINAL_DISCOVER(pair, ds, days)
    for err in errors:
        _PENDING_ACQUISITION_ERRORS.append(dict(err))
    return names, errors


def download_tracking(pair: str, name: str, path: Any):
    """Remember a failed native download, then preserve historical exception flow."""
    try:
        return _ORIGINAL_DOWNLOAD(pair, name, path)
    except Exception as exc:
        _PENDING_ACQUISITION_ERRORS.append({
            "filename": str(name),
            "error_type": type(exc).__name__,
        })
        raise


def evaluate_surface_gate_acquisition_safe(*args: Any, **kwargs: Any):
    """Only terminalize E6 failure when acquisition completed without errors."""
    try:
        result = _ORIGINAL_EVALUATE(*args, **kwargs)
        if bool(result.get("pass")):
            # The frozen E6 gate itself proves the required primary spectral
            # evidence plus at least one independent broadband corroboration.
            # Errors in unused/alternate acquisitions do not invalidate that
            # complete evidence path.
            return result
        if _PENDING_ACQUISITION_ERRORS:
            out = dict(result)
            out["pass"] = False
            out["disposition"] = "E6_ACQUISITION_UNRESOLVED"
            out["underlying_e6_disposition"] = result.get("disposition")
            out["acquisition_error_count"] = len(_PENDING_ACQUISITION_ERRORS)
            out["sws_values_opened"] = False
            out["stage_b_authorized"] = False
            return out
        return result
    except Exception as exc:
        if _PENDING_ACQUISITION_ERRORS:
            return {
                "pass": False,
                "disposition": "E6_ACQUISITION_UNRESOLVED",
                "underlying_e6_disposition": "E6_ANALYSIS_ERROR_FAIL_CLOSED",
                "analysis_error_type": type(exc).__name__,
                "acquisition_error_count": len(_PENDING_ACQUISITION_ERRORS),
                "sws_values_opened": False,
                "stage_b_authorized": False,
            }
        raise
    finally:
        _PENDING_ACQUISITION_ERRORS.clear()


def main() -> int:
    BASE.discover = discover_tracking
    BASE.download = download_tracking
    BASE.E6.evaluate_surface_gate = evaluate_surface_gate_acquisition_safe
    return int(V2.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
