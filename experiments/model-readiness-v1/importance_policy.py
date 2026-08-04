#!/usr/bin/env python3
from __future__ import annotations


def alis_importance_nm(geometry: dict[str, float]) -> float:
    """Variance-reduction policy only; ALIS remains unbiased under every branch."""
    sun = float(geometry["sunDepressionDeg"])
    altitude = float(geometry["targetAltitudeDeg"])
    aod = float(geometry["aod550"])
    if sun >= 10.0 and altitude <= 20.0:
        return 600.0
    if sun >= 10.0 and altitude >= 35.0 and aod >= 0.25:
        return 500.0
    return 550.0
