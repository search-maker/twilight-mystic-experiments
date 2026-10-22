#!/usr/bin/env python3
"""Certified pre-value full-AOD extrema for frozen Level-B v3 + ASIV scenarios.

Consumes only frozen model/runtime bytes plus metadata-derived geometry and an
external AOD550 interval. It never reads measured sky radiance. The evaluator
partitions the one-dimensional AOD axis wherever either frozen k-nearest set can
change, then uses outward-enlarged interval bounds plus deterministic bisection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

BASE_MODEL_SHA256 = "c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9"
BASE_RUNTIME_SHA256 = "6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4"
ASIV_MODEL_SHA256 = "0b11a1691bfd2d9e3f073c786044bacedd3e9210bcb0660c76f21c34128a61af"
ASIV_RUNTIME_SHA256 = "a324408e87fd1ffa5f3fc386e77e54fe046eb3e749f2b39a699712ba355eb060"
AOD_MIN, AOD_MAX = 0.05, 0.40
SCENARIOS = ("native", "continental", "maritime", "desert", "desert_spheroids")
CHANNELS = ("photopic", "scotopic", "johnsonV")
CONTRASTS = ("continental", "maritime", "desert", "desert_spheroids")
DEFAULT_LOG_TOLERANCE = 1e-4


def _down(x: float) -> float:
    return math.nextafter(x, -math.inf) if math.isfinite(x) else x


def _up(x: float) -> float:
    return math.nextafter(x, math.inf) if math.isfinite(x) else x


@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float

    def __post_init__(self):
        if self.lo > self.hi or math.isnan(self.lo) or math.isnan(self.hi):
            raise ValueError("invalid interval")

    def add(self, other: "Interval") -> "Interval":
        return Interval(_down(self.lo + other.lo), _up(self.hi + other.hi))

    def mul_const(self, c: float) -> "Interval":
        a, b = self.lo * c, self.hi * c
        return Interval(_down(min(a, b)), _up(max(a, b)))

    def div_pos(self, other: "Interval") -> "Interval":
        if other.lo <= 0:
            raise ValueError("positive denominator required")
        vals = (
            self.lo / other.lo,
            self.lo / other.hi,
            self.hi / other.lo,
            self.hi / other.hi,
        )
        return Interval(_down(min(vals)), _up(max(vals)))

    @property
    def width(self) -> float:
        return self.hi - self.lo


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_base_runtime(path: Path, *, require_sha: bool = True) -> dict:
    if require_sha and _sha(path) != BASE_RUNTIME_SHA256:
        raise ValueError("base runtime raw SHA-256 drift")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("sourceModelCanonicalSha256") != BASE_MODEL_SHA256:
        raise ValueError("base model identity drift")
    if data.get("primaryBasis") != "PHYSICAL_COMPACT_16_TERMS":
        raise ValueError("base basis drift")
    if data.get("residualCoordinateSystem") != "V1_IDW_COS_COORDINATES":
        raise ValueError("base residual coordinate drift")
    if (
        data.get("residualNeighbors"),
        data.get("residualPower"),
        data.get("residualShrinkage"),
    ) != (6, 1, 1):
        raise ValueError("base residual hyperparameter drift")
    if len(data.get("primaryCoefficients", [])) != 16 or any(
        len(row) != 3 for row in data["primaryCoefficients"]
    ):
        raise ValueError("base coefficients drift")
    if len(data.get("residualCoordinates", [])) != 58 or any(
        len(row) != 5 for row in data["residualCoordinates"]
    ):
        raise ValueError("base residual coordinates drift")
    if len(data.get("residualTargets", [])) != 58 or any(
        len(row) != 3 for row in data["residualTargets"]
    ):
        raise ValueError("base residual targets drift")
    return data


def load_asiv_runtime(path: Path, *, require_sha: bool = True) -> dict:
    if require_sha and _sha(path) != ASIV_RUNTIME_SHA256:
        raise ValueError("ASIV runtime raw SHA-256 drift")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("sourceSelectedModelCanonicalSha256") != ASIV_MODEL_SHA256:
        raise ValueError("ASIV model identity drift")
    spec = data.get("candidateSpec", {})
    if (
        spec.get("candidateId"),
        spec.get("neighbors"),
        spec.get("power"),
    ) != ("IDW_COS_4D-k8-p2", 8, 2.0):
        raise ValueError("ASIV candidate drift")
    if data.get("holdoutValuesIncluded") is not False:
        raise ValueError("ASIV holdout boundary drift")
    if len(data.get("training", [])) != 24:
        raise ValueError("ASIV training cardinality drift")
    for row in data["training"]:
        if len(row.get("coord", [])) != 4 or len(row.get("target", [])) != 12:
            raise ValueError("ASIV training shape drift")
    return data


def _x_aod(aod: float) -> float:
    aod = float(aod)
    if not AOD_MIN <= aod <= AOD_MAX:
        raise ValueError("AOD outside frozen domain")
    return (aod - AOD_MIN) / (AOD_MAX - AOD_MIN)


def _geometry_fixed(sun: float, alt: float, raz: float, elev: float):
    sun, alt, raz, elev = map(float, (sun, alt, raz, elev))
    if (
        not 2.0 <= sun <= 10.5
        or not 5.0 <= alt <= 80.0
        or not 0.0 <= raz <= 180.0
        or not 0.0 <= elev <= 2500.0
    ):
        raise ValueError("geometry outside frozen domain")
    return (
        (sun - 2.0) / 8.5,
        (alt - 5.0) / 75.0,
        (math.cos(math.radians(raz)) + 1.0) / 2.0,
        elev / 2500.0,
    )


def _base_query(fixed, x):
    return (fixed[0], fixed[1], fixed[2], fixed[3], x)


def _asiv_query(fixed, x):
    return (fixed[0], fixed[1], fixed[2], x)


def _sqdist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _neighbors(query, rows, k, coord_key, tie_key):
    values = []
    for index, row in enumerate(rows):
        values.append((_sqdist(query, row[coord_key]), row.get(tie_key, index), index))
    values.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in values[:k])


def _pairwise_crossings(fixed_coords: Sequence[float], rows, coord_key, x_index, lo, hi):
    params = []
    for row in rows:
        coord = row[coord_key]
        constant = sum((fixed_coords[j] - coord[j]) ** 2 for j in range(len(fixed_coords)))
        params.append((constant, coord[x_index]))
    out = {lo, hi}
    eps = 1e-15
    for i in range(len(params)):
        ci, ai = params[i]
        for j in range(i + 1, len(params)):
            cj, aj = params[j]
            denominator = 2.0 * (aj - ai)
            if abs(denominator) <= eps:
                continue
            x = -(ci - cj + ai * ai - aj * aj) / denominator
            if lo < x < hi:
                out.add(x)
    return out


def _q_range(constant, center, lo, hi):
    nearest_x = min(max(center, lo), hi)
    qlo = constant + (nearest_x - center) ** 2
    qhi = constant + max((lo - center) ** 2, (hi - center) ** 2)
    return _down(qlo), _up(qhi)


def _weight_interval(constant, center, lo, hi, power):
    qlo, qhi = _q_range(constant, center, lo, hi)
    if qlo <= 0:
        return None
    if power == 1:
        return Interval(_down(1.0 / math.sqrt(qhi)), _up(1.0 / math.sqrt(qlo)))
    if power == 2:
        return Interval(_down(1.0 / qhi), _up(1.0 / qlo))
    raise ValueError("unsupported IDW power")


def _idw_bound(rows, coord_key, target_key, fixed, x_index, selected, lo, hi, power, target_index):
    params = []
    singular = []
    for index in selected:
        row = rows[index]
        coord = row[coord_key]
        constant = sum((fixed[j] - coord[j]) ** 2 for j in range(len(fixed)))
        center = coord[x_index]
        target = float(row[target_key][target_index])
        params.append((index, constant, center, target))
        if constant == 0.0 and lo <= center <= hi:
            singular.append((index, constant, center, target))

    if len(singular) > 1:
        raise ArithmeticError("multiple exact-hit IDW singularities in selected set")

    if singular:
        singular_index, _, singular_center, singular_target = singular[0]
        # The atomic partition places an exact hit at an endpoint. Multiplying
        # numerator and denominator by |x-x0|^power removes the divergent
        # common factor and provides a finite one-sided enclosure.
        u_max = max(abs(lo - singular_center), abs(hi - singular_center))
        numerator = Interval(singular_target, singular_target)
        denominator = Interval(1.0, 1.0)
        for index, constant, center, target in params:
            if index == singular_index:
                continue
            qlo, _ = _q_range(constant, center, lo, hi)
            if qlo <= 0:
                raise ArithmeticError("secondary singularity")
            if power == 1:
                ratio_hi = u_max / math.sqrt(qlo)
            else:
                ratio_hi = (u_max * u_max) / qlo
            ratio = Interval(0.0, _up(ratio_hi))
            numerator = numerator.add(ratio.mul_const(target))
            denominator = denominator.add(ratio)
        return numerator.div_pos(denominator)

    numerator = Interval(0.0, 0.0)
    denominator = Interval(0.0, 0.0)
    for _, constant, center, target in params:
        weight = _weight_interval(constant, center, lo, hi, power)
        if weight is None:
            raise ArithmeticError("unhandled singularity")
        numerator = numerator.add(weight.mul_const(target))
        denominator = denominator.add(weight)
    return numerator.div_pos(denominator)


def _quadratic_range(c2, c1, c0, lo, hi):
    values = [c2 * lo * lo + c1 * lo + c0, c2 * hi * hi + c1 * hi + c0]
    if c2 != 0:
        vertex = -c1 / (2.0 * c2)
        if lo <= vertex <= hi:
            values.append(c2 * vertex * vertex + c1 * vertex + c0)
    return Interval(_down(min(values)), _up(max(values)))


def _primary_poly_bound(base, sun, alt, raz, elev, aod_lo, aod_hi, channel):
    s = (sun - 2.0) / 8.5
    a = math.sin(math.radians(alt))
    c = math.cos(math.radians(raz))
    e = elev / 2500.0
    co = base["primaryCoefficients"]
    j = channel
    c0 = (
        co[0][j]
        + s * co[1][j]
        + a * co[2][j]
        + c * co[3][j]
        + e * co[4][j]
        + s * s * co[6][j]
        + a * a * co[7][j]
        + c * c * co[8][j]
        + s * a * co[10][j]
        + s * c * co[11][j]
        + a * c * co[13][j]
    )
    c1 = co[5][j] + s * co[12][j] + a * co[14][j] + c * co[15][j]
    c2 = co[9][j]
    o_lo = math.log(aod_lo / AOD_MIN) / math.log(8.0)
    o_hi = math.log(aod_hi / AOD_MIN) / math.log(8.0)
    return _quadratic_range(c2, c1, c0, o_lo, o_hi)


def _point_prediction(base, asiv, sun, alt, raz, elev, aod):
    fixed = _geometry_fixed(sun, alt, raz, elev)
    x = _x_aod(aod)
    s = (sun - 2.0) / 8.5
    a = math.sin(math.radians(alt))
    c = math.cos(math.radians(raz))
    e = elev / 2500.0
    o = math.log(aod / AOD_MIN) / math.log(8.0)
    basis = [1, s, a, c, e, o, s * s, a * a, c * c, o * o, s * a, s * c, s * o, a * c, a * o, c * o]
    base_logs = [
        sum(basis[i] * base["primaryCoefficients"][i][j] for i in range(16))
        for j in range(3)
    ]

    query = _base_query(fixed, x)
    ordered = sorted(
        ((_sqdist(query, coord), index) for index, coord in enumerate(base["residualCoordinates"])),
        key=lambda item: (item[0], item[1]),
    )
    if ordered[0][0] == 0:
        correction = list(base["residualTargets"][ordered[0][1]])
    else:
        chosen = ordered[:6]
        weights = [1.0 / math.sqrt(distance_sq) for distance_sq, _ in chosen]
        total_weight = sum(weights)
        correction = [
            sum(weight * base["residualTargets"][index][j] for weight, (_, index) in zip(weights, chosen))
            / total_weight
            for j in range(3)
        ]
    base_logs = [base_logs[j] + correction[j] for j in range(3)]

    asiv_query = _asiv_query(fixed, x)
    rows = asiv["training"]
    ordered = sorted(
        ((_sqdist(asiv_query, row["coord"]), row["cellId"], index) for index, row in enumerate(rows)),
        key=lambda item: (item[0], item[1]),
    )
    if math.sqrt(ordered[0][0]) <= 1e-15:
        vector = list(rows[ordered[0][2]]["target"])
    else:
        chosen = ordered[:8]
        weights = [1.0 / distance_sq for distance_sq, _, _ in chosen]
        total_weight = sum(weights)
        vector = [
            sum(weight * rows[index]["target"][j] for weight, (_, _, index) in zip(weights, chosen))
            / total_weight
            for j in range(12)
        ]

    out = {"native": base_logs}
    for contrast_index, name in enumerate(CONTRASTS):
        out[name] = [base_logs[j] + vector[contrast_index * 3 + j] for j in range(3)]
    return out


def certified_extrema(
    base,
    asiv,
    *,
    sun,
    alt,
    raz,
    elev,
    aod_lo,
    aod_hi,
    log_tolerance=DEFAULT_LOG_TOLERANCE,
    max_depth=50,
    max_nodes=250000,
):
    if aod_lo > aod_hi:
        raise ValueError("AOD min > max")
    if not (0 < log_tolerance <= 0.01):
        raise ValueError("log_tolerance must be in (0, 0.01]")

    fixed = _geometry_fixed(sun, alt, raz, elev)
    x_lo, x_hi = _x_aod(aod_lo), _x_aod(aod_hi)
    base_rows = [
        {"coord": coord, "target": target, "id": index}
        for index, (coord, target) in enumerate(zip(base["residualCoordinates"], base["residualTargets"]))
    ]

    cuts = set(_pairwise_crossings(fixed, base_rows, "coord", 4, x_lo, x_hi))
    cuts.update(_pairwise_crossings(fixed[:3], asiv["training"], "coord", 3, x_lo, x_hi))

    # Exact-hit points are explicit boundaries, never epsilon-substituted.
    for row in base_rows:
        if all(fixed[j] == row["coord"][j] for j in range(4)) and x_lo < row["coord"][4] < x_hi:
            cuts.add(row["coord"][4])
    for row in asiv["training"]:
        if all(fixed[j] == row["coord"][j] for j in range(3)) and x_lo < row["coord"][3] < x_hi:
            cuts.add(row["coord"][3])
    cuts = sorted(cuts)

    result = {
        scenario: {
            channel: {
                "outerMin": math.inf,
                "innerMin": math.inf,
                "innerMax": -math.inf,
                "outerMax": -math.inf,
            }
            for channel in CHANNELS
        }
        for scenario in SCENARIOS
    }
    nodes = 0
    maximum_depth_seen = 0
    failures = []

    def aod_from_x(x):
        return AOD_MIN + x * (AOD_MAX - AOD_MIN)

    def absorb_point(x):
        prediction = _point_prediction(base, asiv, sun, alt, raz, elev, aod_from_x(x))
        for scenario in SCENARIOS:
            for j, channel in enumerate(CHANNELS):
                value = prediction[scenario][j]
                row = result[scenario][channel]
                row["innerMin"] = min(row["innerMin"], value)
                row["innerMax"] = max(row["innerMax"], value)
                row["outerMin"] = min(row["outerMin"], value)
                row["outerMax"] = max(row["outerMax"], value)

    for x in cuts:
        absorb_point(x)

    def recurse(lo, hi, depth):
        nonlocal nodes, maximum_depth_seen
        nodes += 1
        maximum_depth_seen = max(maximum_depth_seen, depth)
        if nodes > max_nodes:
            failures.append("MAX_NODES")
            return

        midpoint = (lo + hi) / 2.0
        base_selected = _neighbors(_base_query(fixed, midpoint), base_rows, 6, "coord", "id")
        asiv_selected = _neighbors(_asiv_query(fixed, midpoint), asiv["training"], 8, "coord", "cellId")
        aod_segment_lo, aod_segment_hi = aod_from_x(lo), aod_from_x(hi)
        bounds = {}
        maximum_width = 0.0

        for j, channel in enumerate(CHANNELS):
            polynomial = _primary_poly_bound(
                base, sun, alt, raz, elev, aod_segment_lo, aod_segment_hi, j
            )
            residual = _idw_bound(
                base_rows, "coord", "target", fixed, 4, base_selected, lo, hi, 1, j
            )
            native = polynomial.add(residual)
            bounds[("native", channel)] = native
            maximum_width = max(maximum_width, native.width)

            for contrast_index, scenario in enumerate(CONTRASTS):
                contrast = _idw_bound(
                    asiv["training"],
                    "coord",
                    "target",
                    fixed[:3],
                    3,
                    asiv_selected,
                    lo,
                    hi,
                    2,
                    contrast_index * 3 + j,
                )
                total = native.add(contrast)
                bounds[(scenario, channel)] = total
                maximum_width = max(maximum_width, total.width)

        if maximum_width <= log_tolerance:
            absorb_point(midpoint)
            for (scenario, channel), interval in bounds.items():
                row = result[scenario][channel]
                row["outerMin"] = min(row["outerMin"], interval.lo)
                row["outerMax"] = max(row["outerMax"], interval.hi)
            return

        if depth >= max_depth:
            failures.append(f"MAX_DEPTH:{lo:.17g}:{hi:.17g}")
            absorb_point(midpoint)
            for (scenario, channel), interval in bounds.items():
                row = result[scenario][channel]
                row["outerMin"] = min(row["outerMin"], interval.lo)
                row["outerMax"] = max(row["outerMax"], interval.hi)
            return

        recurse(lo, midpoint, depth + 1)
        recurse(midpoint, hi, depth + 1)

    for lo, hi in zip(cuts, cuts[1:]):
        if hi > lo:
            recurse(lo, hi, 0)

    certified = not failures
    for scenario in SCENARIOS:
        for channel in CHANNELS:
            row = result[scenario][channel]
            if math.isinf(row["outerMin"]):
                row["outerMin"] = row["innerMin"]
                row["outerMax"] = row["innerMax"]
            row["minCertificationGap"] = row["innerMin"] - row["outerMin"]
            row["maxCertificationGap"] = row["outerMax"] - row["innerMax"]
            if (
                row["minCertificationGap"] > log_tolerance * 1.0001
                or row["maxCertificationGap"] > log_tolerance * 1.0001
            ):
                certified = False

    return {
        "algorithmId": "CERTIFIED_AOD_SCENARIO_EXTREMA_INTERVAL_BNB_V1",
        "targetRadianceUsed": False,
        "adaptiveSearchUsingMeasuredRadiance": False,
        "aod550Interval": [aod_lo, aod_hi],
        "logTolerance": log_tolerance,
        "partitionBreakpoints": len(cuts),
        "branchNodes": nodes,
        "maximumDepth": maximum_depth_seen,
        "certified": certified,
        "failures": failures,
        "scenarios": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime-json", type=Path, required=True)
    parser.add_argument("--asiv-runtime-json", type=Path, required=True)
    parser.add_argument("--sun-depression-deg", type=float, required=True)
    parser.add_argument("--target-altitude-deg", type=float, required=True)
    parser.add_argument("--relative-azimuth-deg", type=float, required=True)
    parser.add_argument("--observer-elevation-m", type=float, required=True)
    parser.add_argument("--aod550-min", type=float, required=True)
    parser.add_argument("--aod550-max", type=float, required=True)
    parser.add_argument("--log-tolerance", type=float, default=DEFAULT_LOG_TOLERANCE)
    parser.add_argument("--max-depth", type=int, default=50)
    parser.add_argument("--max-nodes", type=int, default=250000)
    parser.add_argument("--allow-unbound-runtime-for-test", action="store_true")
    args = parser.parse_args()

    base = load_base_runtime(
        args.base_runtime_json,
        require_sha=not args.allow_unbound_runtime_for_test,
    )
    asiv = load_asiv_runtime(
        args.asiv_runtime_json,
        require_sha=not args.allow_unbound_runtime_for_test,
    )
    result = certified_extrema(
        base,
        asiv,
        sun=args.sun_depression_deg,
        alt=args.target_altitude_deg,
        raz=args.relative_azimuth_deg,
        elev=args.observer_elevation_m,
        aod_lo=args.aod550_min,
        aod_hi=args.aod550_max,
        log_tolerance=args.log_tolerance,
        max_depth=args.max_depth,
        max_nodes=args.max_nodes,
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["certified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
