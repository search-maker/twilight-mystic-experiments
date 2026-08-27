from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence


class ProfileTransportError(ValueError):
    pass


@dataclass(frozen=True)
class RemappedProfile:
    target_edges_m: tuple[float, ...]
    layer_tau_fractions: tuple[float, ...]
    transported_integral: float
    outside_below_policy: str
    outside_above_policy: str
    source_fingerprint_sha256: str

    def as_dict(self) -> dict:
        return {
            "schemaVersion": 1,
            "targetEdgesM": list(self.target_edges_m),
            "layerTauFractions": list(self.layer_tau_fractions),
            "transportedIntegral": self.transported_integral,
            "outsideBelowPolicy": self.outside_below_policy,
            "outsideAbovePolicy": self.outside_above_policy,
            "sourceFingerprintSha256": self.source_fingerprint_sha256,
        }


def _finite_float(value, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ProfileTransportError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise ProfileTransportError(f"{name} must be finite")
    return out


def _strictly_increasing(values: Sequence[float]) -> bool:
    return all(b > a for a, b in zip(values, values[1:]))


def validate_source_profile(
    altitude_m: Iterable[float],
    values: Iterable[float],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    z = tuple(_finite_float(v, "altitude_m") for v in altitude_m)
    y = tuple(_finite_float(v, "profile value") for v in values)
    if len(z) < 2 or len(z) != len(y):
        raise ProfileTransportError("source profile needs >=2 altitude nodes and matching values")
    if not _strictly_increasing(z):
        raise ProfileTransportError("source altitude grid must be strictly increasing")
    if any(v < 0 for v in y):
        raise ProfileTransportError("source profile values must be nonnegative")
    if not any(v > 0 for v in y):
        raise ProfileTransportError("all-zero source profile is not a usable aerosol shape")
    return z, y


def validate_target_edges(target_edges_m: Iterable[float]) -> tuple[float, ...]:
    edges = tuple(_finite_float(v, "target edge") for v in target_edges_m)
    if len(edges) < 2 or not _strictly_increasing(edges):
        raise ProfileTransportError("target edges must be a strictly increasing grid with >=2 nodes")
    return edges


def _outside_value(policy: str, edge_value: float, side: str) -> float:
    if policy == "zero":
        return 0.0
    if policy == "edge":
        return edge_value
    if policy == "reject":
        raise ProfileTransportError(f"target interval extends {side} source profile support")
    raise ProfileTransportError(f"unsupported outside-{side} policy: {policy}")


def _value_at(z: Sequence[float], y: Sequence[float], x: float, below: str, above: str) -> float:
    if x < z[0]:
        return _outside_value(below, y[0], "below")
    if x > z[-1]:
        return _outside_value(above, y[-1], "above")
    if x == z[0]:
        return y[0]
    if x == z[-1]:
        return y[-1]
    lo = 0
    hi = len(z) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if z[mid] <= x:
            lo = mid
        else:
            hi = mid
    w = (x - z[lo]) / (z[hi] - z[lo])
    return y[lo] * (1.0 - w) + y[hi] * w


def _integrate_supported_piecewise_linear(
    altitude_m: Sequence[float], values: Sequence[float], lo_m: float, hi_m: float
) -> float:
    if not hi_m > lo_m:
        return 0.0
    points = [lo_m]
    points.extend(v for v in altitude_m if lo_m < v < hi_m)
    points.append(hi_m)
    samples = [_value_at(altitude_m, values, x, "reject", "reject") for x in points]
    return math.fsum(
        0.5 * (samples[i] + samples[i + 1]) * (points[i + 1] - points[i])
        for i in range(len(points) - 1)
    )


def integrate_piecewise_linear(
    altitude_m: Sequence[float],
    values: Sequence[float],
    lo_m: float,
    hi_m: float,
    *,
    outside_below_policy: str,
    outside_above_policy: str,
) -> float:
    if not hi_m > lo_m:
        raise ProfileTransportError("integration interval must have positive width")

    z0, z1 = altitude_m[0], altitude_m[-1]
    pieces = []

    below_hi = min(hi_m, z0)
    if lo_m < below_hi:
        if outside_below_policy == "reject":
            raise ProfileTransportError("target interval extends below source profile support")
        if outside_below_policy not in {"zero", "edge"}:
            raise ProfileTransportError(f"unsupported outside-below policy: {outside_below_policy}")
        value = 0.0 if outside_below_policy == "zero" else values[0]
        pieces.append(value * (below_hi - lo_m))

    inside_lo = max(lo_m, z0)
    inside_hi = min(hi_m, z1)
    if inside_lo < inside_hi:
        pieces.append(_integrate_supported_piecewise_linear(altitude_m, values, inside_lo, inside_hi))

    above_lo = max(lo_m, z1)
    if above_lo < hi_m:
        if outside_above_policy == "reject":
            raise ProfileTransportError("target interval extends above source profile support")
        if outside_above_policy not in {"zero", "edge"}:
            raise ProfileTransportError(f"unsupported outside-above policy: {outside_above_policy}")
        value = 0.0 if outside_above_policy == "zero" else values[-1]
        pieces.append(value * (hi_m - above_lo))

    integral = math.fsum(pieces)
    if integral < 0 or not math.isfinite(integral):
        raise ProfileTransportError("integrated profile is invalid")
    return integral


def canonical_source_fingerprint(
    altitude_m: Sequence[float],
    values: Sequence[float],
    *,
    source_identity: object | None = None,
) -> str:
    payload = {
        "schemaVersion": 1,
        "altitudeM": list(altitude_m),
        "values": list(values),
        "sourceIdentity": source_identity,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def remap_normalized_vertical_shape(
    altitude_m: Iterable[float],
    values: Iterable[float],
    target_edges_m: Iterable[float],
    *,
    outside_below_policy: str,
    outside_above_policy: str,
    source_identity: object | None = None,
) -> RemappedProfile:
    """Map a supplied nonnegative vertical *shape* to target layers.

    The returned fractions sum to one over the requested target domain. This function
    deliberately does not accept or choose a column AOD: column optical depth remains
    a separate atmospheric quantity and must be supplied independently downstream.

    Outside-profile behavior is mandatory and explicit; there is no hidden physical
    extrapolation default.
    """
    z, y = validate_source_profile(altitude_m, values)
    edges = validate_target_edges(target_edges_m)
    allowed = {"reject", "zero", "edge"}
    if outside_below_policy not in allowed or outside_above_policy not in allowed:
        raise ProfileTransportError("outside policies must be one of reject/zero/edge")

    layer_integrals = tuple(
        integrate_piecewise_linear(
            z,
            y,
            edges[i],
            edges[i + 1],
            outside_below_policy=outside_below_policy,
            outside_above_policy=outside_above_policy,
        )
        for i in range(len(edges) - 1)
    )
    total = math.fsum(layer_integrals)
    if not total > 0:
        raise ProfileTransportError("source profile has zero integrated weight over target domain")
    fractions = tuple(v / total for v in layer_integrals)
    if abs(math.fsum(fractions) - 1.0) > 1e-12:
        raise ProfileTransportError("normalized layer fractions do not sum to one")

    return RemappedProfile(
        target_edges_m=edges,
        layer_tau_fractions=fractions,
        transported_integral=total,
        outside_below_policy=outside_below_policy,
        outside_above_policy=outside_above_policy,
        source_fingerprint_sha256=canonical_source_fingerprint(z, y, source_identity=source_identity),
    )


def render_libradtran_aerosol_tau(profile: RemappedProfile, *, header: str | None = None) -> str:
    """Render libRadtran `aerosol_file tau` lower-bound layer convention.

    Each layer optical-depth fraction is associated with its lower boundary; the top
    boundary is emitted with zero. Lines are descending in altitude, matching the
    convention already proven in the Taylor HRRR vertical-shape implementation.
    """
    tau_by_edge = {
        profile.target_edges_m[i]: profile.layer_tau_fractions[i]
        for i in range(len(profile.layer_tau_fractions))
    }
    tau_by_edge[profile.target_edges_m[-1]] = 0.0
    lines = []
    if header:
        lines.append(f"# {header}")
    lines.append("# normalized vertical optical-depth shape only; column AOD is external")
    for altitude_m in reversed(profile.target_edges_m):
        lines.append(f"{altitude_m / 1000.0:.9f} {tau_by_edge[altitude_m]:.17e}")
    return "\n".join(lines) + "\n"