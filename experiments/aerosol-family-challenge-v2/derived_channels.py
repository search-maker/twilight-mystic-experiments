from __future__ import annotations

import math
from typing import Any, Callable

KM_PHOTOPIC = 683.002
KM_SCOTOPIC = 1700.06
RAW_START_NM = 380.0
RAW_STOP_NM = 780.0
RAW_STEP_NM = 0.05
RAW_NODE_COUNT = 8001
RAW_POINT_TOLERANCE_NM = 0.00005
CIE_WL = tuple(float(w) for w in range(380, 781, 10))
V_PHOT = (
    0.00004, 0.00012, 0.0004, 0.0012, 0.0040, 0.0116, 0.023, 0.038,
    0.060, 0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.710, 0.862,
    0.954, 0.99495, 0.995, 0.952, 0.870, 0.757, 0.631, 0.503, 0.381,
    0.265, 0.175, 0.107, 0.061, 0.032, 0.017, 0.00821, 0.004102,
    0.002091, 0.001047, 0.00052, 0.000249, 0.00012, 0.00006, 0.00003,
    0.000015,
)
V_SCOT = (
    0.000589, 0.002209, 0.00929, 0.03484, 0.0966, 0.1998, 0.3281,
    0.455, 0.567, 0.676, 0.793, 0.904, 0.982, 0.997, 0.935, 0.811,
    0.650, 0.481, 0.3288, 0.2076, 0.1212, 0.0655, 0.03315, 0.01593,
    0.00737, 0.003335, 0.001497, 0.000677, 0.0003129, 0.000148,
    0.0000715, 0.00003533, 0.0000178, 0.00000914, 0.00000478,
    0.000002546, 0.000001379, 0.00000076, 0.000000425, 0.000000241,
    0.000000139,
)
BESSELL_V = (
    (470.0, 0.0), (480.0, 0.03), (490.0, 0.163), (500.0, 0.458),
    (510.0, 0.78), (520.0, 0.967), (530.0, 1.0), (540.0, 0.973),
    (550.0, 0.898), (560.0, 0.792), (570.0, 0.684), (580.0, 0.574),
    (590.0, 0.461), (600.0, 0.359), (610.0, 0.27), (620.0, 0.197),
    (630.0, 0.135), (640.0, 0.081), (650.0, 0.045), (660.0, 0.025),
    (670.0, 0.017), (680.0, 0.013), (690.0, 0.009), (700.0, 0.0),
)
GRID_ERROR_UPPER_BOUND_RELATIVE = {
    "photopicLuminanceCdM2": 0.0011168248714839013,
    "scotopicLuminanceScotCdM2": 0.0020320382260645697,
    "johnsonVEffectiveRadiance_mW_m2_nm_sr": 0.0018607417688334404,
}


def validate_raw_grid(wavelengths: list[float], radiance: list[float]) -> None:
    if len(wavelengths) != RAW_NODE_COUNT or len(radiance) != RAW_NODE_COUNT:
        raise ValueError("expected exact 8001-node 380..780 nm serialized spectrum")
    for i, (w, r) in enumerate(zip(wavelengths, radiance)):
        expected = RAW_START_NM + i * RAW_STEP_NM
        if not math.isfinite(w) or abs(w - expected) > RAW_POINT_TOLERANCE_NM:
            raise ValueError(f"serialized wavelength grid mismatch at {i}: got {w}, expected {expected}")
        if not math.isfinite(r) or r < 0:
            raise ValueError(f"invalid radiance at {i}")
        if i and not wavelengths[i - 1] < w:
            raise ValueError(f"serialized wavelength grid not strictly increasing at {i}")


def _interp(table: tuple[float, ...], wavelength: float) -> float:
    if wavelength < 380.0 or wavelength > 780.0:
        return 0.0
    if wavelength == 780.0:
        return table[-1]
    x = (wavelength - 380.0) / 10.0
    i = int(math.floor(x))
    f = x - i
    return table[i] * (1.0 - f) + table[i + 1] * f


def _bessell_response(wavelength: float) -> float:
    if wavelength < 470.0 or wavelength > 700.0:
        return 0.0
    if wavelength == 700.0:
        return BESSELL_V[-1][1]
    x = (wavelength - 470.0) / 10.0
    i = int(math.floor(x))
    f = x - i
    return BESSELL_V[i][1] * (1.0 - f) + BESSELL_V[i + 1][1] * f


def _trap_weighted(wl: list[float], rad: list[float], weight_at: Callable[[float], float], km: float) -> float:
    total = 0.0
    for i in range(len(wl) - 1):
        dl = wl[i + 1] - wl[i]
        total += 0.5 * (weight_at(wl[i]) * rad[i] + weight_at(wl[i + 1]) * rad[i + 1]) * dl
    return km * total * 1e-3


def _johnson_effective(wl: list[float], rad: list[float]) -> float:
    num = 0.0
    den = 0.0
    for i in range(len(wl) - 1):
        dl = wl[i + 1] - wl[i]
        a = _bessell_response(wl[i]) * wl[i]
        b = _bessell_response(wl[i + 1]) * wl[i + 1]
        num += 0.5 * (a * rad[i] + b * rad[i + 1]) * dl
        den += 0.5 * (a + b) * dl
    if den <= 0:
        raise ValueError("Johnson V passband has zero support")
    return num / den


def derive_channels(wavelengths: list[float], radiance: list[float]) -> dict[str, Any]:
    validate_raw_grid(wavelengths, radiance)
    photopic = _trap_weighted(wavelengths, radiance, lambda x: _interp(V_PHOT, x), KM_PHOTOPIC)
    scotopic = _trap_weighted(wavelengths, radiance, lambda x: _interp(V_SCOT, x), KM_SCOTOPIC)
    johnson = _johnson_effective(wavelengths, radiance)
    return {
        "photopicLuminanceCdM2": photopic,
        "scotopicLuminanceScotCdM2": scotopic,
        "scotopicPhotopicRatio": None if photopic <= 0 else scotopic / photopic,
        "johnsonVEffectiveRadiance_mW_m2_nm_sr": johnson,
    }


def marginal_mc_std_diagnostics(wavelengths: list[float], radiance: list[float], std_radiance: list[float]) -> dict[str, Any]:
    validate_raw_grid(wavelengths, radiance)
    validate_raw_grid(wavelengths, std_radiance)
    relative = [float(s) / float(r) for r, s in zip(radiance, std_radiance) if r > 0.0]
    zero_count = sum(1 for r in radiance if r == 0.0)
    if not relative:
        return {
            "status": "NO_POSITIVE_RADIANCE_NODES",
            "positiveRadianceNodeCount": 0,
            "zeroRadianceNodeCount": zero_count,
            "medianRelativeStd": None,
            "maximumRelativeStd": None,
            "pairedContrastUncertaintyUsePermitted": False,
        }
    ordered = sorted(relative)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else 0.5 * (ordered[n // 2 - 1] + ordered[n // 2])
    return {
        "status": "MARGINAL_MC_STD_DIAGNOSTIC_ONLY",
        "positiveRadianceNodeCount": len(relative),
        "zeroRadianceNodeCount": zero_count,
        "medianRelativeStd": median,
        "maximumRelativeStd": max(relative),
        "pairedContrastUncertaintyUsePermitted": False,
    }
