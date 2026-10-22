#!/usr/bin/env python3
"""POST_V1/NONBLOCKING exact species-coupled optical-property reference.

This module is solver-free and result-blind. It captures a deterministic
preprocessing invariant for a future deep-twilight upper-bound certificate:
keep Rayleigh and aerosol scattering strengths coupled to their own normalized
phase distributions for as long as possible instead of independently bounding
a total scattering strength and a normalized mixed phase function.

For nonnegative species strengths s_R and s_A and normalized discrete phase
masses P_R and P_A, the unnormalized continuation kernel is

    K_j = s_R P_R,j + s_A P_A,j.

The corresponding normalized aerosol mixture weight is

    w = s_A / (s_R + s_A),

and after multiplying aerosol scattering by an exact positive scale rho,

    w' = rho*w / (1 - w + rho*w).

All arithmetic here uses fractions.Fraction. Binary floats are rejected.
No protected MYSTIC result is read, no zero is replaced by epsilon, and Level-B
is not modified.
"""

from __future__ import annotations

import argparse
import json
import unittest
from fractions import Fraction
from typing import Iterable, Sequence

Exact = Fraction
ExactLike = int | str | Fraction


def as_exact(value: ExactLike) -> Exact:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("use int, Fraction, or exact decimal/rational string; floats are forbidden")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    raise TypeError(f"unsupported exact value type: {type(value).__name__}")


def _vec(values: Iterable[ExactLike]) -> tuple[Exact, ...]:
    return tuple(as_exact(v) for v in values)


def _require_nonnegative(name: str, values: Sequence[Exact]) -> None:
    if any(v < 0 for v in values):
        raise ValueError(f"{name} must be componentwise nonnegative")


def _normalized_phase(name: str, phase: Iterable[ExactLike]) -> tuple[Exact, ...]:
    p = _vec(phase)
    if not p:
        raise ValueError(f"{name} must be nonempty")
    _require_nonnegative(name, p)
    if sum(p, Fraction(0)) != 1:
        raise ValueError(f"{name} must sum exactly to one")
    return p


def aerosol_mixture_weight(rayleigh_strength: ExactLike, aerosol_strength: ExactLike) -> Exact:
    s_r = as_exact(rayleigh_strength)
    s_a = as_exact(aerosol_strength)
    if s_r < 0 or s_a < 0:
        raise ValueError("species strengths must be nonnegative")
    total = s_r + s_a
    if total <= 0:
        raise ValueError("at least one species strength must be positive")
    return s_a / total


def scaled_aerosol_mixture_weight(weight: ExactLike, aerosol_scale: ExactLike) -> Exact:
    """Return exact logistic reweighting after s_A -> aerosol_scale * s_A."""
    w = as_exact(weight)
    rho = as_exact(aerosol_scale)
    if not 0 <= w <= 1:
        raise ValueError("weight must lie in [0, 1]")
    if rho <= 0:
        raise ValueError("aerosol_scale must be positive")
    denominator = 1 - w + rho * w
    if denominator <= 0:
        raise AssertionError("positive scale produced nonpositive mixture denominator")
    return rho * w / denominator


def species_coupled_kernel_expectation(
    rayleigh_strength: ExactLike,
    aerosol_strength: ExactLike,
    rayleigh_phase: Iterable[ExactLike],
    aerosol_phase: Iterable[ExactLike],
    importance: Iterable[ExactLike],
) -> Exact:
    """Return sum_j (s_R P_R,j + s_A P_A,j) y_j exactly."""
    s_r = as_exact(rayleigh_strength)
    s_a = as_exact(aerosol_strength)
    if s_r < 0 or s_a < 0:
        raise ValueError("species strengths must be nonnegative")
    p_r = _normalized_phase("rayleigh_phase", rayleigh_phase)
    p_a = _normalized_phase("aerosol_phase", aerosol_phase)
    y = _vec(importance)
    if not (len(p_r) == len(p_a) == len(y)):
        raise ValueError("phase and importance vectors must have equal length")
    _require_nonnegative("importance", y)
    return sum(
        ((s_r * p_r[j] + s_a * p_a[j]) * y[j] for j in range(len(y))),
        Fraction(0),
    )


def normalized_species_mixture_expectation(
    rayleigh_strength: ExactLike,
    aerosol_strength: ExactLike,
    rayleigh_phase: Iterable[ExactLike],
    aerosol_phase: Iterable[ExactLike],
    importance: Iterable[ExactLike],
) -> Exact:
    """Return the normalized mixed-phase expectation of importance exactly."""
    s_r = as_exact(rayleigh_strength)
    s_a = as_exact(aerosol_strength)
    total = s_r + s_a
    if s_r < 0 or s_a < 0 or total <= 0:
        raise ValueError("species strengths must be nonnegative with positive total")
    return species_coupled_kernel_expectation(
        s_r, s_a, rayleigh_phase, aerosol_phase, importance
    ) / total


def _oscillation(values: Iterable[ExactLike]) -> Exact:
    y = _vec(values)
    if not y:
        raise ValueError("importance must be nonempty")
    return max(y) - min(y)


class ReferenceTests(unittest.TestCase):
    def test_exact_logistic_reweighting_matches_strength_scaling(self) -> None:
        s_r = Fraction(2)
        s_a = Fraction(3)
        rho = Fraction(5, 2)
        w = aerosol_mixture_weight(s_r, s_a)
        expected = aerosol_mixture_weight(s_r, rho * s_a)
        self.assertEqual(scaled_aerosol_mixture_weight(w, rho), expected)

    def test_mixture_constant_shift_invariance(self) -> None:
        p_r = ["3/4", "1/4"]
        p_a = ["1/4", "3/4"]
        y = [2, 5]
        shifted = [9, 12]
        before = normalized_species_mixture_expectation(2, 1, p_r, p_a, y)
        after = normalized_species_mixture_expectation(2, 3, p_r, p_a, y)
        before_shift = normalized_species_mixture_expectation(2, 1, p_r, p_a, shifted)
        after_shift = normalized_species_mixture_expectation(2, 3, p_r, p_a, shifted)
        self.assertEqual(after - before, after_shift - before_shift)

    def test_exact_mixture_perturbation_identity_and_oscillation_bound(self) -> None:
        p_r = _normalized_phase("rayleigh_phase", ["4/5", "1/5"])
        p_a = _normalized_phase("aerosol_phase", ["1/5", "4/5"])
        y = _vec([1, 7])
        e_r = sum((p_r[j] * y[j] for j in range(2)), Fraction(0))
        e_a = sum((p_a[j] * y[j] for j in range(2)), Fraction(0))
        w0 = aerosol_mixture_weight(3, 1)
        w1 = aerosol_mixture_weight(3, 5)
        m0 = normalized_species_mixture_expectation(3, 1, p_r, p_a, y)
        m1 = normalized_species_mixture_expectation(3, 5, p_r, p_a, y)
        self.assertEqual(m1 - m0, (w1 - w0) * (e_a - e_r))
        self.assertLessEqual(abs(e_a - e_r), _oscillation(y))

    def test_species_coupling_is_strictly_tighter_than_independent_product_fixture(self) -> None:
        # True one-bin unnormalized kernel K = s_R*p_R + s_A*p_A with
        # s_A in [0, 1]. Independently maximizing total strength and normalized
        # mixed-bin mass combines incompatible endpoints and is strictly looser.
        s_r = Fraction(1)
        s_a_lo = Fraction(0)
        s_a_hi = Fraction(1)
        p_r = Fraction(9, 10)
        p_a = Fraction(1, 10)

        species_coupled_upper = s_r * p_r + s_a_hi * p_a
        total_upper = s_r + s_a_hi
        mixed_bin_at_lo = (s_r * p_r + s_a_lo * p_a) / (s_r + s_a_lo)
        mixed_bin_at_hi = (s_r * p_r + s_a_hi * p_a) / (s_r + s_a_hi)
        independent_product_upper = total_upper * max(mixed_bin_at_lo, mixed_bin_at_hi)

        self.assertEqual(species_coupled_upper, 1)
        self.assertEqual(independent_product_upper, Fraction(9, 5))
        self.assertLess(species_coupled_upper, independent_product_upper)

    def test_kernel_constant_importance_conserves_total_scattering_strength(self) -> None:
        value = species_coupled_kernel_expectation(
            "2/5", "3/5", ["1/3", "2/3"], ["3/4", "1/4"], [7, 7]
        )
        self.assertEqual(value, 7)

    def test_fail_closed_normalization_and_float_guards(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum exactly to one"):
            normalized_species_mixture_expectation(
                1, 1, ["1/2", "1/3"], ["1/2", "1/2"], [1, 2]
            )
        with self.assertRaisesRegex(TypeError, "floats are forbidden"):
            aerosol_mixture_weight(1.0, 1)
        with self.assertRaisesRegex(ValueError, "aerosol_scale must be positive"):
            scaled_aerosol_mixture_weight("1/2", 0)


def _s(value: Exact) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _summary() -> dict[str, object]:
    p_r = ["3/4", "1/4"]
    p_a = ["1/4", "3/4"]
    y = [2, 5]
    before = normalized_species_mixture_expectation(2, 1, p_r, p_a, y)
    after = normalized_species_mixture_expectation(2, 3, p_r, p_a, y)
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "species_coupled": True,
        "mixture_shift_example": _s(after - before),
        "arithmetic": "exact Fraction; binary floats forbidden",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    print(json.dumps(_summary(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
