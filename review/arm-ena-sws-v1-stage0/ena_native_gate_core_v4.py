#!/usr/bin/env python3
"""Prospective result-blind E5 common-vertical-range correction layer.

Governance: Issue #60 comment 5488569132 freezes E5 raw-sonde semantics.
No ENA native E5 science outcome had been opened when this correction was made.

This layer preserves E2-v2, E4-v3, E3, and all other reviewed primitives.  It
only makes the frozen E5 phrase "common vertical range supported by both
bracketing measured profiles" explicit and fail-closed.  Historical v1
`choose_sonde_pair()` recorded min(top_before, top_after) but did not calculate
the corresponding max(bottom_before, bottom_after), so it could theoretically
PASS two individually usable profiles with no measured vertical overlap.
"""
from __future__ import annotations
from typing import Any
import math

import ena_native_gate_core_v3 as V3
from ena_native_gate_core_v3 import *


def choose_sonde_pair(records: list[dict[str, Any]], reference_epoch: float, max_hours: float = 6.0) -> dict[str, Any]:
    usable = [
        r for r in records
        if r.get("usable") and math.isfinite(float(r.get("launch_epoch", math.nan)))
    ]
    before = [
        r for r in usable
        if r["launch_epoch"] < reference_epoch
        and reference_epoch - r["launch_epoch"] <= max_hours * 3600 + 1e-6
    ]
    after = [
        r for r in usable
        if r["launch_epoch"] > reference_epoch
        and r["launch_epoch"] - reference_epoch <= max_hours * 3600 + 1e-6
    ]
    if not before or not after:
        return {"pass": False, "reason": "NO_TWO_SIDED_SONDE_WITHIN_6H"}

    b = max(before, key=lambda r: r["launch_epoch"])
    a = min(after, key=lambda r: r["launch_epoch"])

    required = ("measured_bottom_alt", "measured_top_alt")
    if any(k not in b or k not in a for k in required):
        return {"pass": False, "reason": "SONDE_COMMON_VERTICAL_RANGE_UNRESOLVED"}
    try:
        b_bottom = float(b["measured_bottom_alt"])
        b_top = float(b["measured_top_alt"])
        a_bottom = float(a["measured_bottom_alt"])
        a_top = float(a["measured_top_alt"])
    except Exception:
        return {"pass": False, "reason": "SONDE_COMMON_VERTICAL_RANGE_UNRESOLVED"}
    if not all(math.isfinite(x) for x in (b_bottom, b_top, a_bottom, a_top)):
        return {"pass": False, "reason": "SONDE_COMMON_VERTICAL_RANGE_UNRESOLVED"}

    common_bottom = max(b_bottom, a_bottom)
    common_top = min(b_top, a_top)
    if not common_top > common_bottom:
        return {
            "pass": False,
            "reason": "NO_COMMON_MEASURED_VERTICAL_RANGE",
            "before_file": b.get("source_file"),
            "after_file": a.get("source_file"),
            "common_measured_bottom_alt": common_bottom,
            "common_measured_top_alt": common_top,
        }

    return {
        "pass": True,
        "reason": "THERMO_TWO_SIDED_SUPPORTED",
        "before_file": b["source_file"],
        "after_file": a["source_file"],
        "before_offset_hours": (reference_epoch - b["launch_epoch"]) / 3600.0,
        "after_offset_hours": (a["launch_epoch"] - reference_epoch) / 3600.0,
        "common_measured_bottom_alt": common_bottom,
        "common_measured_top_alt": common_top,
        "above_common_top_label": "ASSUMED_STANDARD_EXTENSION_SENSITIVITY",
    }
