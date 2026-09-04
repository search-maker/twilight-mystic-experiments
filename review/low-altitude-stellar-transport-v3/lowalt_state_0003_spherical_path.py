#!/usr/bin/env python3
"""Solver-free geometry primitive for LOWALT-STELLAR-STATE-0003.

This module intentionally does NOT claim libRadtran/sdisort source equivalence.
It evaluates a straight outward ray through concentric piecewise-constant
extinction shells. It contains no uvspec/subprocess execution and no fitted
parameters. h<=0 is refused because exact horizon support is not established.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


class DirectPathRefusal(ValueError):
    """Fail-closed refusal for geometry/numeric states outside the prototype contract."""


@dataclass(frozen=True)
class RadialLayer:
    """One retained radial shell above the observer.

    z_lo_km/z_hi_km are geometric heights above the same reference sea-level
    sphere. vertical_tau is the extinction optical depth normal to the shell.
    """

    z_lo_km: float
    z_hi_km: float
    vertical_tau: float


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise DirectPathRefusal(f"{name} must be finite")
    return value


def _validate_layers(layers: Sequence[RadialLayer], observer_altitude_km: float) -> None:
    if not layers:
        raise DirectPathRefusal("at least one retained layer is required")
    previous_hi = None
    for index, layer in enumerate(layers):
        lo = _finite(f"layers[{index}].z_lo_km", layer.z_lo_km)
        hi = _finite(f"layers[{index}].z_hi_km", layer.z_hi_km)
        tau = _finite(f"layers[{index}].vertical_tau", layer.vertical_tau)
        if hi <= lo:
            raise DirectPathRefusal("layer heights must be strictly increasing")
        if tau < 0.0:
            raise DirectPathRefusal("vertical optical depth must be nonnegative")
        if previous_hi is not None and not math.isclose(lo, previous_hi, rel_tol=0.0, abs_tol=1e-12):
            raise DirectPathRefusal("retained layers must be contiguous")
        previous_hi = hi
    if not math.isclose(layers[0].z_lo_km, observer_altitude_km, rel_tol=0.0, abs_tol=1e-12):
        raise DirectPathRefusal("first retained layer must start exactly at observer altitude")


def shell_path_length_km(
    *,
    earth_radius_km: float,
    observer_altitude_km: float,
    geometric_altitude_deg: float,
    z_lo_km: float,
    z_hi_km: float,
) -> float:
    """Exact Euclidean path length through one concentric shell for h>0.

    For r0=R+z_obs and impact parameter b=r0*cos(h), the exact outward-ray
    distance is sqrt(r_hi^2-b^2)-sqrt(r_lo^2-b^2). Direct evaluation of that
    identity loses precision twice near the horizon/thin-shell limit: first in
    r^2-b^2 and then in the difference of nearby square roots.

    Use the algebraically identical observer-relative radicand

      A(z) = (z-z_obs)*(2R+z+z_obs) + (R+z_obs)^2*sin(h)^2

    and rationalize the root difference:

      ds = (z_hi-z_lo)*(2R+z_hi+z_lo) / (sqrt(A_hi)+sqrt(A_lo)).

    This changes only floating-point conditioning; it does not choose an Earth
    radius, extinction rule, refraction model, or sdisort-equivalence mapping.
    """

    radius = _finite("earth_radius_km", earth_radius_km)
    observer = _finite("observer_altitude_km", observer_altitude_km)
    h_deg = _finite("geometric_altitude_deg", geometric_altitude_deg)
    lo = _finite("z_lo_km", z_lo_km)
    hi = _finite("z_hi_km", z_hi_km)

    if radius <= 0.0:
        raise DirectPathRefusal("earth radius must be positive")
    if observer < 0.0:
        raise DirectPathRefusal("negative observer altitude is outside this prototype")
    if not (0.0 < h_deg <= 90.0):
        raise DirectPathRefusal("geometric altitude must satisfy 0 < h <= 90 deg")
    if lo < observer - 1e-12 or hi <= lo:
        raise DirectPathRefusal("shell must be above observer and have positive thickness")

    r0 = radius + observer
    h_rad = math.radians(h_deg)
    sin_term = r0 * math.sin(h_rad)
    sin_term_sq = sin_term * sin_term

    def radial_root(z_km: float) -> float:
        dz = z_km - observer
        shell_term = dz * (2.0 * radius + z_km + observer)
        arg = shell_term + sin_term_sq
        r = radius + z_km
        scale = max(r * r, 1.0)
        if not math.isfinite(arg):
            raise DirectPathRefusal("ray/shell geometry produced a nonfinite radicand")
        if arg < -1e-13 * scale:
            raise DirectPathRefusal("ray/shell geometry produced a negative radicand")
        return math.sqrt(max(0.0, arg))

    lo_root = radial_root(lo)
    hi_root = radial_root(hi)
    denominator = hi_root + lo_root
    numerator = (hi - lo) * (2.0 * radius + hi + lo)
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator <= 0.0:
        raise DirectPathRefusal("nonfinite shell path rationalization")
    ds = numerator / denominator
    if not math.isfinite(ds) or ds <= 0.0:
        raise DirectPathRefusal("nonfinite or nonpositive shell path length")
    return ds


def slant_optical_depth(
    *,
    earth_radius_km: float,
    observer_altitude_km: float,
    geometric_altitude_deg: float,
    layers: Iterable[RadialLayer],
) -> float:
    """Integrate piecewise-constant extinction through retained spherical shells."""

    layer_seq = tuple(layers)
    observer = _finite("observer_altitude_km", observer_altitude_km)
    _validate_layers(layer_seq, observer)

    total = 0.0
    for layer in layer_seq:
        dz = layer.z_hi_km - layer.z_lo_km
        ds = shell_path_length_km(
            earth_radius_km=earth_radius_km,
            observer_altitude_km=observer,
            geometric_altitude_deg=geometric_altitude_deg,
            z_lo_km=layer.z_lo_km,
            z_hi_km=layer.z_hi_km,
        )
        contribution = layer.vertical_tau * (ds / dz)
        if not math.isfinite(contribution) or contribution < 0.0:
            raise DirectPathRefusal("nonfinite or negative optical-depth contribution")
        total += contribution
    if not math.isfinite(total) or total < 0.0:
        raise DirectPathRefusal("nonfinite or negative total optical depth")
    return total


def direct_transmission_from_tau(slant_tau: float) -> float:
    """Return exp(-tau), refusing numerical zero rather than manufacturing epsilon."""

    tau = _finite("slant_tau", slant_tau)
    if tau < 0.0:
        raise DirectPathRefusal("slant optical depth must be nonnegative")
    transmission = math.exp(-tau)
    if not math.isfinite(transmission) or transmission <= 0.0:
        raise DirectPathRefusal("direct transmission is unresolved/underflowed")
    return transmission


def direct_transmission(
    *,
    earth_radius_km: float,
    observer_altitude_km: float,
    geometric_altitude_deg: float,
    layers: Iterable[RadialLayer],
) -> float:
    return direct_transmission_from_tau(
        slant_optical_depth(
            earth_radius_km=earth_radius_km,
            observer_altitude_km=observer_altitude_km,
            geometric_altitude_deg=geometric_altitude_deg,
            layers=layers,
        )
    )


def _high_precision_shell_reference_km(
    *,
    earth_radius_km: float,
    observer_altitude_km: float,
    geometric_altitude_deg: float,
    z_lo_km: float,
    z_hi_km: float,
) -> float:
    """100-digit arithmetic oracle for the shell-arithmetic self-test only.

    The sine is intentionally computed once in binary64 and converted exactly
    to Decimal. This isolates the cancellation/conditioning question from any
    separate high-precision trigonometric convention. It is not science input
    and is not a libRadtran source-equivalence claim.
    """

    from decimal import Decimal, localcontext

    with localcontext() as context:
        context.prec = 100
        radius = Decimal.from_float(float(earth_radius_km))
        observer = Decimal.from_float(float(observer_altitude_km))
        lo = Decimal.from_float(float(z_lo_km))
        hi = Decimal.from_float(float(z_hi_km))
        sin_h = Decimal.from_float(math.sin(math.radians(float(geometric_altitude_deg))))
        r0 = radius + observer
        sin_term_sq = (r0 * sin_h) * (r0 * sin_h)

        def arg(z_km: Decimal) -> Decimal:
            return (z_km - observer) * (2 * radius + z_km + observer) + sin_term_sq

        return float(arg(hi).sqrt() - arg(lo).sqrt())


def _self_test() -> None:
    R = 6371.0  # synthetic test constant only; NOT a frozen sdisort source-equivalence claim
    layers = (
        RadialLayer(0.0, 1.0, 0.10),
        RadialLayer(1.0, 3.0, 0.20),
        RadialLayer(3.0, 8.0, 0.30),
    )

    # Vertical-ray identity for piecewise-constant shells.
    vertical = slant_optical_depth(
        earth_radius_km=R,
        observer_altitude_km=0.0,
        geometric_altitude_deg=90.0,
        layers=layers,
    )
    assert math.isclose(vertical, 0.60, rel_tol=0.0, abs_tol=2e-12), vertical

    # Splitting a constant-extinction layer must not change the integral.
    unsplit = (RadialLayer(0.0, 10.0, 0.50),)
    split = (RadialLayer(0.0, 2.0, 0.10), RadialLayer(2.0, 10.0, 0.40))
    for h in (0.25, 0.5, 1.0, 5.0, 30.0, 90.0):
        a = slant_optical_depth(
            earth_radius_km=R,
            observer_altitude_km=0.0,
            geometric_altitude_deg=h,
            layers=unsplit,
        )
        b = slant_optical_depth(
            earth_radius_km=R,
            observer_altitude_km=0.0,
            geometric_altitude_deg=h,
            layers=split,
        )
        assert math.isclose(a, b, rel_tol=5e-12, abs_tol=5e-12), (h, a, b)
        assert a > 0.0 and math.isfinite(a)

    # Cancellation regression: compare the binary64 implementation to a
    # 100-digit oracle over thin-shell / near-horizon stress cases. These
    # coordinates are synthetic arithmetic tests, not an equivalence matrix.
    cancellation_cases = (
        (5.0, 0.0, 0.0, 0.1),
        (1.0, 0.0, 0.0, 0.01),
        (0.0001, 0.0, 0.0, 0.0001),
        (1e-7, 0.0, 0.0, 1e-6),
        (0.3, 2.5, 2.5, 2.500001),
        (90.0, 0.0, 0.0, 1e-6),
    )
    for h, observer, lo, hi in cancellation_cases:
        got = shell_path_length_km(
            earth_radius_km=R,
            observer_altitude_km=observer,
            geometric_altitude_deg=h,
            z_lo_km=lo,
            z_hi_km=hi,
        )
        reference = _high_precision_shell_reference_km(
            earth_radius_km=R,
            observer_altitude_km=observer,
            geometric_altitude_deg=h,
            z_lo_km=lo,
            z_hi_km=hi,
        )
        relative_error = abs(got - reference) / reference
        assert relative_error <= 8e-15, (h, observer, lo, hi, got, reference, relative_error)

    # Observer-elevation truncation is explicit in the retained layers.
    elevated = (
        RadialLayer(2.5, 4.0, 0.12),
        RadialLayer(4.0, 9.0, 0.18),
    )
    tau_elev = slant_optical_depth(
        earth_radius_km=R,
        observer_altitude_km=2.5,
        geometric_altitude_deg=1.0,
        layers=elevated,
    )
    assert tau_elev > sum(x.vertical_tau for x in elevated)

    # Horizon and below remain fail closed under this identity.
    for h in (0.0, -0.01):
        try:
            shell_path_length_km(
                earth_radius_km=R,
                observer_altitude_km=0.0,
                geometric_altitude_deg=h,
                z_lo_km=0.0,
                z_hi_km=1.0,
            )
        except DirectPathRefusal:
            pass
        else:
            raise AssertionError("h<=0 must refuse")

    # Numerical underflow is a refusal, never epsilon substitution.
    try:
        direct_transmission_from_tau(1000.0)
    except DirectPathRefusal:
        pass
    else:
        raise AssertionError("underflowed transmission must refuse")

    assert 0.0 < direct_transmission_from_tau(1.0) < 1.0


if __name__ == "__main__":
    _self_test()
    print("LOWALT-STELLAR-STATE-0003 spherical-path solver-free self-test: PASS")
