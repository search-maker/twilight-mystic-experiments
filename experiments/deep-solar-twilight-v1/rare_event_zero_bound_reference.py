#!/usr/bin/env python3
"""POST_V1/NONBLOCKING exact-zero rare-event reference certificate.

Scope
-----
This module is deliberately result-blind and solver-free.  It does not open or
reinterpret protected MYSTIC results, does not replace an observed zero by an
epsilon, and does not alter Level-B.  It implements only deterministic
reference mathematics for a future post-release stopping rule.

Key facts
---------
For independent nonnegative scores X_i, observing X_1=...=X_n=0 gives exact
one-sided information about q=P(X>0):

    q <= 1 - alpha**(1/n)

with confidence 1-alpha.  By itself this is not a finite mean bound.  A finite
mean upper bound requires an independently certified finite score envelope B,
or a finite-order envelope B_m plus a deterministic upper bound U_tail on the
unresolved higher-order transport.

Along the all-zero path, repeated inspection does *not* require alpha spending:
the events {first n observations are all zero} are nested.  For any false q,
the first exclusion time n* has probability (1-q)**n* < alpha.  Thus the same
fixed-alpha zero-only boundary is anytime-valid while every observed score
remains exactly zero and all envelope/tail inputs were frozen independently of
the scores.  If a positive score appears, this zero-only path is terminated.

The binary64 formulas in this file remain useful for reporting/reference
values, but integer stopping decisions are certified against exact decimal
inputs by the sibling exact-rational oracle.  A rounded binary64 endpoint must
never be allowed to decide that a campaign has crossed a one-sample boundary.
"""

from __future__ import annotations

import argparse
import json
import math
import unittest
from fractions import Fraction

from assumption_tier_budget_reference import required_independent_units
from negligibility_amplification_reference import magnitude_ratio_budget_lower

MAG_TOL_DEFAULT = 0.0100
_MAX_CERTIFIABLE_INTEGER_COUNT = (1 << 53) - 1
_LN10_OVER_2P5 = math.log(10.0) / 2.5


def _require_probability(name: str, value: float) -> None:
    if not (math.isfinite(value) and 0.0 < value < 1.0):
        raise ValueError(f"{name} must be finite and strictly between 0 and 1")


def _require_positive(name: str, value: float) -> None:
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"{name} must be finite and > 0")


def _require_nonnegative(name: str, value: float) -> None:
    if not (math.isfinite(value) and value >= 0.0):
        raise ValueError(f"{name} must be finite and >= 0")


def _require_certifiable_integer_boundary(name: str, raw_count: float) -> None:
    """Fail closed when binary64 cannot certify one-sample integer minimality."""
    if not math.isfinite(raw_count) or raw_count >= _MAX_CERTIFIABLE_INTEGER_COUNT:
        raise ValueError(
            f"{name} exceeds the binary64 exact-integer audit range; "
            "use a separately reviewed higher-precision reference"
        )


def _decimal_fraction(value: float) -> Fraction:
    """Interpret the caller-visible decimal value exactly for certification.

    Python's shortest round-trip ``str(float)`` is used deliberately.  The
    public reference API historically accepts binary64 values such as ``0.05``;
    stopping certification must therefore use the decimal value the API exposes
    rather than a rounded transcendental endpoint computed from that binary64.
    """
    return Fraction(str(value))


def _required_all_zero_count_exact(alpha: Fraction, q_target: Fraction) -> int:
    try:
        return required_independent_units(alpha, q_target)
    except ValueError as exc:
        if "bounded reference range" in str(exc):
            raise ValueError(
                "required all-zero count exceeds the bounded exact-reference range; "
                "use a separately reviewed higher-precision reference"
            ) from exc
        raise


def _integer_power_equals(base: int, exponent: int, target: int) -> bool:
    """Exact bounded equality test for base**exponent == target.

    Exponents can be as large as the bounded stopping oracle permits.  Avoid
    constructing an integer with O(exponent) digits: exponentiation by squaring
    caps an intermediate as soon as it exceeds the fixed target.  Runtime and
    intermediate size are therefore bounded by O(log(exponent)) and the size of
    ``target`` rather than by the mathematical power itself.
    """
    if exponent < 0 or base < 0 or target < 0:
        raise ValueError("power-equality inputs must be nonnegative")
    if exponent == 0:
        return target == 1
    if base == 0:
        return target == 0
    if base == 1:
        return target == 1
    if target <= 0:
        return False

    result = 1
    factor = base
    remaining = exponent
    while remaining:
        if remaining & 1:
            if factor > target // result:
                return False
            result *= factor
        remaining >>= 1
        if remaining:
            if factor > target // factor:
                factor = target + 1
            else:
                factor *= factor
    return result == target


def _fraction_power_equals(base: Fraction, exponent: int, target: Fraction) -> bool:
    """Exact equality test for reduced positive rational powers."""
    if not (Fraction(0) < base <= Fraction(1)):
        raise ValueError("base must lie in (0, 1]")
    if not (Fraction(0) < target <= Fraction(1)):
        raise ValueError("target must lie in (0, 1]")
    if not isinstance(exponent, int) or isinstance(exponent, bool) or exponent <= 0:
        raise ValueError("exponent must be a positive integer")

    # Fractions are stored reduced.  Since gcd(num, den)=1, base**m is also
    # reduced, so rational equality is equivalent to equality of the two
    # numerator powers and denominator powers separately.
    return _integer_power_equals(
        base.numerator, exponent, target.numerator
    ) and _integer_power_equals(base.denominator, exponent, target.denominator)


def zero_event_probability_upper(alpha: float, n: int) -> float:
    """Stable binary64 report value for 1-alpha**(1/n).

    This return value is not used to certify an integer stopping boundary.
    ``required_all_zero_count`` uses exact-rational certification instead.
    """
    _require_probability("alpha", alpha)
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    # Stable evaluation of 1 - alpha**(1/n) for very large n.
    return -math.expm1(math.log(alpha) / n)


def bounded_zero_mean_upper(alpha: float, n: int, envelope: float) -> float:
    """Binary64 report value when 0 <= X <= envelope and all n scores are zero."""
    _require_nonnegative("envelope", envelope)
    return envelope * zero_event_probability_upper(alpha, n)


def hybrid_zero_upper(
    alpha: float,
    n: int,
    finite_order_envelope: float,
    deterministic_tail_upper: float,
) -> float:
    """Binary64 finite-order report value plus deterministic unresolved-tail cap."""
    _require_nonnegative("finite_order_envelope", finite_order_envelope)
    _require_nonnegative("deterministic_tail_upper", deterministic_tail_upper)
    return (
        bounded_zero_mean_upper(alpha, n, finite_order_envelope)
        + deterministic_tail_upper
    )


def radiance_ratio_budget(magnitude_tolerance: float = MAG_TOL_DEFAULT) -> float:
    """Binary64 report value for the magnitude-to-radiance materiality budget."""
    _require_positive("magnitude_tolerance", magnitude_tolerance)
    # expm1 avoids cancellation when the requested magnitude budget is tiny.
    return math.expm1(_LN10_OVER_2P5 * magnitude_tolerance)


def required_all_zero_count(alpha: float, q_target: float) -> int:
    """Smallest n with 1-alpha**(1/n) <= q_target, exactly certified.

    Candidate/stopping decisions do not compare the rounded binary64 value from
    ``zero_event_probability_upper`` against ``q_target``.  Such a comparison
    can be fail-open at a one-sample boundary when the transcendental endpoint
    rounds downward.  Instead the caller-visible decimal values are converted
    to exact Fractions and the sibling outward-certified oracle proves both
    sufficiency and minimality.
    """
    _require_probability("alpha", alpha)
    _require_probability("q_target", q_target)
    return _required_all_zero_count_exact(
        _decimal_fraction(alpha),
        _decimal_fraction(q_target),
    )


def stopping_count_for_materiality(
    *,
    alpha: float,
    finite_order_envelope: float,
    deterministic_tail_upper: float,
    non_solar_lower: float,
    magnitude_tolerance: float = MAG_TOL_DEFAULT,
) -> int:
    """Predeclare the all-zero sample count for the hybrid materiality gate.

    All non-score inputs must be frozen independently before protected results
    are opened.  If any positive score occurs, this zero-only stopping rule no
    longer applies and must fail closed or hand off to a separately frozen
    nonzero-score protocol.

    The integer decision is made from exact decimal Fractions and the directed
    lower enclosure of the magnitude budget.  Binary64 report values therefore
    cannot round the allowed budget upward or the q target outward into a false
    PASS.
    """
    _require_probability("alpha", alpha)
    _require_nonnegative("finite_order_envelope", finite_order_envelope)
    _require_nonnegative("deterministic_tail_upper", deterministic_tail_upper)
    _require_positive("non_solar_lower", non_solar_lower)
    _require_positive("magnitude_tolerance", magnitude_tolerance)

    alpha_exact = _decimal_fraction(alpha)
    envelope_exact = _decimal_fraction(finite_order_envelope)
    tail_exact = _decimal_fraction(deterministic_tail_upper)
    non_solar_exact = _decimal_fraction(non_solar_lower)
    tolerance_exact = _decimal_fraction(magnitude_tolerance)

    ratio_budget_lower = magnitude_ratio_budget_lower(tolerance_exact)
    residual = ratio_budget_lower * non_solar_exact - tail_exact
    if residual <= 0:
        raise ValueError("deterministic tail already exhausts the materiality budget")
    if envelope_exact == 0:
        return 1
    q_target = residual / envelope_exact
    if q_target >= 1:
        return 1
    if q_target <= 0:
        raise ValueError("nonpositive q target is not certifiable by finite zero sampling")
    return _required_all_zero_count_exact(alpha_exact, q_target)


def all_zero_crossing_probability(q: float, alpha: float) -> tuple[int, float]:
    """Return first strict false-q exclusion time and report probability.

    The anytime-valid proof needs the *strict* event ``(1-q)**n < alpha``.
    First obtain the outward-certified non-strict crossing ``m`` satisfying
    ``(1-q)**m <= alpha``.  If equality holds exactly at ``m``, advance to
    ``m+1``; otherwise ``m`` is already the first strict crossing.  Exact
    rational equality is checked without forming enormous rational powers.

    The returned probability is binary64 reporting only and is never used to
    choose the certified integer crossing count.
    """
    _require_probability("q", q)
    _require_probability("alpha", alpha)

    q_exact = _decimal_fraction(q)
    alpha_exact = _decimal_fraction(alpha)
    survival_exact = Fraction(1) - q_exact
    non_strict = _required_all_zero_count_exact(alpha_exact, q_exact)
    crossing = non_strict + int(
        _fraction_power_equals(survival_exact, non_strict, alpha_exact)
    )

    log_survival = math.log1p(-q)
    return crossing, math.exp(crossing * log_survival)


class ReferenceTests(unittest.TestCase):
    def test_reference_200m(self) -> None:
        # High-precision reference values from direct Decimal evaluation.
        self.assertAlmostEqual(
            zero_event_probability_upper(0.05, 200_000_000),
            1.4978661255589807e-8,
            places=20,
        )
        self.assertAlmostEqual(
            zero_event_probability_upper(0.01, 200_000_000),
            2.3025850664845553e-8,
            places=20,
        )

    def test_zero_cap_requires_finite_envelope(self) -> None:
        with self.assertRaises(ValueError):
            bounded_zero_mean_upper(0.05, 10, float("inf"))

    def test_n_monotonic(self) -> None:
        self.assertLess(
            zero_event_probability_upper(0.05, 1001),
            zero_event_probability_upper(0.05, 1000),
        )

    def test_required_count_is_minimal(self) -> None:
        target = 1e-8
        n = required_all_zero_count(0.05, target)
        self.assertEqual(
            n,
            required_independent_units(Fraction("0.05"), Fraction("1e-8")),
        )
        self.assertTrue(
            n == 1 or not required_independent_units(
                Fraction("0.05"), Fraction("1e-8")
            ) < n
        )

    def test_binary64_endpoint_cannot_create_one_sample_false_pass(self) -> None:
        # For exact decimal alpha=0.05 and n=3, the true endpoint is
        # 0.6315968501359613394... . The historical binary64 report rounds it
        # down to 0.6315968501359613. Reusing that rounded value as q_target
        # would let a binary64 endpoint comparison accept n=3, even though the
        # exact decimal target is below the true boundary and requires n=4.
        target = 0.6315968501359613
        self.assertLessEqual(zero_event_probability_upper(0.05, 3), target)
        self.assertEqual(required_all_zero_count(0.05, target), 4)

    def test_hybrid_m_order(self) -> None:
        expected = 7.0 * zero_event_probability_upper(0.05, 12345) + 0.25
        self.assertEqual(hybrid_zero_upper(0.05, 12345, 7.0, 0.25), expected)

    def test_materiality_ratio(self) -> None:
        self.assertAlmostEqual(
            radiance_ratio_budget(0.0100),
            0.009252886076684491,
            places=15,
        )

    def test_tiny_materiality_ratio_does_not_cancel_to_zero(self) -> None:
        tiny = radiance_ratio_budget(1e-16)
        self.assertGreater(tiny, 0.0)
        self.assertTrue(
            math.isclose(
                tiny,
                _LN10_OVER_2P5 * 1e-16,
                rel_tol=2e-16,
                abs_tol=0.0,
            )
        )

    def test_tail_exhaustion_fails_closed(self) -> None:
        budget = radiance_ratio_budget() * 10.0
        with self.assertRaisesRegex(ValueError, "tail already exhausts"):
            stopping_count_for_materiality(
                alpha=0.05,
                finite_order_envelope=1.0,
                deterministic_tail_upper=budget,
                non_solar_lower=10.0,
            )

    def test_materiality_stopping_count_uses_exact_composed_budget(self) -> None:
        n = stopping_count_for_materiality(
            alpha=0.05,
            finite_order_envelope=10.0,
            deterministic_tail_upper=0.001,
            non_solar_lower=100.0,
        )
        budget_lower = magnitude_ratio_budget_lower(Fraction("0.0100"))
        q_target = (
            budget_lower * Fraction(100) - Fraction("0.001")
        ) / Fraction(10)
        self.assertEqual(
            n,
            required_independent_units(Fraction("0.05"), q_target),
        )

    def test_all_zero_sequential_boundary_is_anytime_valid(self) -> None:
        for q in (1e-2, 1e-4, 1e-8, 1e-12):
            n, crossing_probability = all_zero_crossing_probability(q, 0.05)
            self.assertLess(crossing_probability, 0.05)
            if n > 1:
                previous_log_probability = (n - 1) * math.log1p(-q)
                self.assertGreaterEqual(previous_log_probability, math.log(0.05))

    def test_strict_crossing_rejects_binary64_three_sample_false_pass(self) -> None:
        # Exact decimal q gives survival^3 slightly above 0.05.  The old
        # binary64 log quotient was 2.9999999999999996 and could return 3.
        q = 0.6315968501359613
        n, _report_probability = all_zero_crossing_probability(q, 0.05)
        survival = Fraction(1) - Fraction("0.6315968501359613")
        alpha = Fraction("0.05")
        self.assertGreater(survival**3, alpha)
        self.assertLess(survival**4, alpha)
        self.assertEqual(n, 4)

    def test_strict_crossing_advances_exact_equality_boundary(self) -> None:
        # Non-strict crossing is m=2 because (1-0.5)^2 == 0.25 exactly, but
        # anytime exclusion requires strict probability < alpha, so n*=3.
        n, crossing_probability = all_zero_crossing_probability(0.5, 0.25)
        self.assertEqual(n, 3)
        self.assertEqual(
            _fraction_power_equals(Fraction(1, 2), 2, Fraction(1, 4)),
            True,
        )
        self.assertLess(crossing_probability, 0.25)

    def test_unverifiable_huge_count_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "higher-precision reference"):
            required_all_zero_count(0.05, 1e-16)
        with self.assertRaisesRegex(ValueError, "higher-precision reference"):
            all_zero_crossing_probability(1e-16, 0.05)


def _summary() -> dict[str, float | int | str]:
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "q_upper_95_n_200m": zero_event_probability_upper(0.05, 200_000_000),
        "q_upper_99_n_200m": zero_event_probability_upper(0.01, 200_000_000),
        "ratio_budget_0p0100_mag": radiance_ratio_budget(0.0100),
        "integer_stopping_certification": "EXACT_RATIONAL_OUTWARD_CERTIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    print(json.dumps(_summary(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
