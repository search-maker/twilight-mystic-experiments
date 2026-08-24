#!/usr/bin/env python3
"""Exact pre-value Level-B v3 support test over a continuous AOD550 interval.

This module deliberately consumes metadata/model-runtime bytes only.  It never
reads measured sky radiance.  For fixed geometry and observer elevation the
frozen V1_IDW_COS support coordinate varies only in its AOD coordinate.  The
nearest-support distance is therefore the lower envelope of equal-curvature
quadratics.  Its maximum over a closed AOD interval occurs at an interval
endpoint or at a pairwise distance-equality crossing, so no AOD grid or
outcome-adaptive search is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

EXPECTED_MODEL_SHA256 = "c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9"
EXPECTED_RUNTIME_SHA256 = "6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4"
EXPECTED_SUPPORT_COUNT = 58
MAX_SUPPORT_DISTANCE = 0.60
AOD_MIN = 0.05
AOD_MAX = 0.40


def _finite(name: str, value: float) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def v1_idw_cos_fixed_coordinates(
    *,
    sun_depression_deg: float,
    target_altitude_deg: float,
    relative_azimuth_deg: float,
    observer_elevation_m: float,
) -> tuple[float, float, float, float]:
    """Return the four V1_IDW_COS coordinates that do not depend on AOD."""
    d = _finite("sun_depression_deg", sun_depression_deg)
    h = _finite("target_altitude_deg", target_altitude_deg)
    az = _finite("relative_azimuth_deg", relative_azimuth_deg)
    elev = _finite("observer_elevation_m", observer_elevation_m)
    if not 2.0 <= d <= 10.5:
        raise ValueError("sun_depression_deg outside frozen [2, 10.5] domain")
    if not 5.0 <= h <= 80.0:
        raise ValueError("target_altitude_deg outside frozen [5, 80] domain")
    if not 0.0 <= az <= 180.0:
        raise ValueError("relative_azimuth_deg outside frozen [0, 180] domain")
    if not 0.0 <= elev <= 2500.0:
        raise ValueError("observer_elevation_m outside frozen [0, 2500] domain")
    return (
        (d - 2.0) / 8.5,
        (h - 5.0) / 75.0,
        (math.cos(math.radians(az)) + 1.0) / 2.0,
        elev / 2500.0,
    )


def normalized_aod(aod550: float) -> float:
    aod = _finite("aod550", aod550)
    if not AOD_MIN <= aod <= AOD_MAX:
        raise ValueError("aod550 outside frozen [0.05, 0.40] domain")
    return (aod - AOD_MIN) / (AOD_MAX - AOD_MIN)


def _validate_support_coordinates(support_coordinates: Sequence[Sequence[float]]) -> list[tuple[float, ...]]:
    if len(support_coordinates) != EXPECTED_SUPPORT_COUNT:
        raise ValueError(f"expected {EXPECTED_SUPPORT_COUNT} support coordinates")
    out: list[tuple[float, ...]] = []
    for index, row in enumerate(support_coordinates):
        if len(row) != 5:
            raise ValueError(f"support coordinate {index} must have length 5")
        values = tuple(_finite(f"support[{index}]", value) for value in row)
        out.append(values)
    return out


def load_bound_runtime(path: Path, *, require_raw_sha256: bool = True) -> dict:
    raw = path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest()
    if require_raw_sha256 and raw_sha != EXPECTED_RUNTIME_SHA256:
        raise ValueError(f"runtime raw SHA-256 drift: {raw_sha}")
    data = json.loads(raw)
    if data.get("sourceModelCanonicalSha256") != EXPECTED_MODEL_SHA256:
        raise ValueError("runtime source model identity drift")
    _validate_support_coordinates(data.get("supportCoordinates", []))
    return data


def _candidate_x_values(
    fixed: Sequence[float],
    support_coordinates: Sequence[Sequence[float]],
    x_lo: float,
    x_hi: float,
) -> list[float]:
    """Endpoints plus every pairwise support-distance equality crossing."""
    rows = _validate_support_coordinates(support_coordinates)
    constants: list[float] = []
    aods: list[float] = []
    for row in rows:
        constants.append(sum((fixed[j] - row[j]) ** 2 for j in range(4)))
        aods.append(row[4])

    candidates = {float(x_lo), float(x_hi)}
    eps = 1e-15
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            ai, aj = aods[i], aods[j]
            denominator = 2.0 * (aj - ai)
            if abs(denominator) <= eps:
                continue
            numerator = constants[i] - constants[j] + ai * ai - aj * aj
            x = -numerator / denominator
            if x_lo - eps <= x <= x_hi + eps:
                candidates.add(min(x_hi, max(x_lo, x)))
    return sorted(candidates)


def nearest_distance_at_x(
    fixed: Sequence[float],
    support_coordinates: Sequence[Sequence[float]],
    x: float,
) -> float:
    rows = _validate_support_coordinates(support_coordinates)
    best_sq = math.inf
    for row in rows:
        distance_sq = sum((fixed[j] - row[j]) ** 2 for j in range(4)) + (x - row[4]) ** 2
        best_sq = min(best_sq, distance_sq)
    return math.sqrt(best_sq)


def exact_max_nearest_support_distance(
    *,
    support_coordinates: Sequence[Sequence[float]],
    sun_depression_deg: float,
    target_altitude_deg: float,
    relative_azimuth_deg: float,
    observer_elevation_m: float,
    aod550_min: float,
    aod550_max: float,
) -> dict:
    aod_lo = _finite("aod550_min", aod550_min)
    aod_hi = _finite("aod550_max", aod550_max)
    if aod_lo > aod_hi:
        raise ValueError("aod550_min must be <= aod550_max")
    x_lo = normalized_aod(aod_lo)
    x_hi = normalized_aod(aod_hi)
    fixed = v1_idw_cos_fixed_coordinates(
        sun_depression_deg=sun_depression_deg,
        target_altitude_deg=target_altitude_deg,
        relative_azimuth_deg=relative_azimuth_deg,
        observer_elevation_m=observer_elevation_m,
    )
    candidates = _candidate_x_values(fixed, support_coordinates, x_lo, x_hi)
    evaluated = [(x, nearest_distance_at_x(fixed, support_coordinates, x)) for x in candidates]
    x_worst, max_distance = max(evaluated, key=lambda pair: (pair[1], pair[0]))
    worst_aod = AOD_MIN + x_worst * (AOD_MAX - AOD_MIN)
    return {
        "algorithmId": "EXACT_PAIRWISE_LOWER_ENVELOPE_V1",
        "candidateCount": len(candidates),
        "aod550Interval": [aod_lo, aod_hi],
        "maximumNearestFrozenTrainingDistance": max_distance,
        "worstAod550": worst_aod,
        "maximumAllowedDistance": MAX_SUPPORT_DISTANCE,
        "supportedAcrossEntireInterval": max_distance <= MAX_SUPPORT_DISTANCE + 1e-12,
        "gridApproximationUsed": False,
        "targetRadianceUsed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-json", type=Path, required=True)
    parser.add_argument("--sun-depression-deg", type=float, required=True)
    parser.add_argument("--target-altitude-deg", type=float, required=True)
    parser.add_argument("--relative-azimuth-deg", type=float, required=True)
    parser.add_argument("--observer-elevation-m", type=float, required=True)
    parser.add_argument("--aod550-min", type=float, required=True)
    parser.add_argument("--aod550-max", type=float, required=True)
    parser.add_argument("--allow-unbound-runtime-for-test", action="store_true")
    args = parser.parse_args()
    runtime = load_bound_runtime(
        args.runtime_json,
        require_raw_sha256=not args.allow_unbound_runtime_for_test,
    )
    result = exact_max_nearest_support_distance(
        support_coordinates=runtime["supportCoordinates"],
        sun_depression_deg=args.sun_depression_deg,
        target_altitude_deg=args.target_altitude_deg,
        relative_azimuth_deg=args.relative_azimuth_deg,
        observer_elevation_m=args.observer_elevation_m,
        aod550_min=args.aod550_min,
        aod550_max=args.aod550_max,
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["supportedAcrossEntireInterval"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
