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
"""

from __future__ import annotations

import argparse
import json
import math
import unittest

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


def zero_event_probability_upper(alpha: float, n: int) -> float:
    """Exact upper bound for q=P(X>0) after n independent exact zeros."""
    _require_probability("alpha", alpha)
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    # Stable evaluation of 1 - alpha**(1/n) for very large n.
    return -math.expm1(math.log(alpha) / n)


def bounded_zero_mean_upper(alpha: float, n: int, envelope: float) -> float:
    """Mean upper bound when 0 <= X <= envelope and all n scores are zero."""
    _require_nonnegative("envelope", envelope)
    return envelope * zero_event_probability_upper(alpha, n)


def hybrid_zero_upper(
    alpha: float,
    n: int,
    finite_order_envelope: float,
    deterministic_tail_upper: float,
) -> float:
    """Finite-order exact-zero cap plus deterministic unresolved-tail cap."""
    _require_nonnegative("finite_order_envelope", finite_order_envelope)
    _require_nonnegative("deterministic_tail_upper", deterministic_tail_upper)
    return (
        bounded_zero_mean_upper(alpha, n, finite_order_envelope)
        + deterministic_tail_upper
    )


def radiance_ratio_budget(magnitude_tolerance: float = MAG_TOL_DEFAULT) -> float:
    """Largest additive radiance ratio compatible with a magnitude tolerance."""
    _require_positive("magnitude_tolerance", magnitude_tolerance)
    # expm1 avoids cancellation when the requested magnitude budget is tiny.
    return math.expm1(_LN10_OVER_2P5 * magnitude_tolerance)


def required_all_zero_count(alpha: float, q_target: float) -> int:
    """Smallest n such that the exact all-zero upper bound is <= q_target."""
    _require_probability("alpha", alpha)
    _require_probability("q_target", q_target)
    raw = math.log(alpha) / math.log1p(-q_target)
    _require_certifiable_integer_boundary("required all-zero count", raw)
    n = max(1, math.ceil(raw))
    # Guard the exact integer contract against floating-point boundary rounding.
    while zero_event_probability_upper(alpha, n) > q_target:
        if n >= _MAX_CERTIFIABLE_INTEGER_COUNT:
            raise ValueError(
                "required all-zero count crossed the binary64 exact-integer audit range"
            )
        n += 1
    while n > 1 and zero_event_probability_upper(alpha, n - 1) <= q_target:
        n -= 1
    return n


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
    """
    _require_nonnegative("finite_order_envelope", finite_order_envelope)
    _require_nonnegative("deterministic_tail_upper", deterministic_tail_upper)
    _require_positive("non_solar_lower", non_solar_lower)
    budget = radiance_ratio_budget(magnitude_tolerance) * non_solar_lower
    residual = budget - deterministic_tail_upper
    if residual <= 0.0:
        raise ValueError("deterministic tail already exhausts the materiality budget")
    if finite_order_envelope == 0.0:
        return 1
    q_target = residual / finite_order_envelope
    if q_target >= 1.0:
        return 1
    return required_all_zero_count(alpha, q_target)


def all_zero_crossing_probability(q: float, alpha: float) -> tuple[int, float]:
    """Return first false-q exclusion time and its all-zero crossing probability."""
    _require_probability("q", q)
    _require_probability("alpha", alpha)
    log_alpha = math.log(alpha)
    log_survival = math.log1p(-q)
    raw = log_alpha / log_survival
    _require_certifiable_integer_boundary("all-zero crossing count", raw)
    n = max(1, math.floor(raw) + 1)

    def log_crossing_probability(count: int) -> float:
        return count * log_survival

    # Compare in log space: forming (1-q) first can round to exactly 1 for tiny q.
    while log_crossing_probability(n) >= log_alpha:
        if n >= _MAX_CERTIFIABLE_INTEGER_COUNT:
            raise ValueError(
                "all-zero crossing count crossed the binary64 exact-integer audit range"
            )
        n += 1
    while n > 1 and log_crossing_probability(n - 1) < log_alpha:
        n -= 1
    return n, math.exp(log_crossing_probability(n))


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
        self.assertLessEqual(zero_event_probability_upper(0.05, n), target)
        self.assertGreater(zero_event_probability_upper(0.05, n - 1), target)

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

    def test_materiality_stopping_count_is_minimal(self) -> None:
        n = stopping_count_for_materiality(
            alpha=0.05,
            finite_order_envelope=10.0,
            deterministic_tail_upper=0.001,
            non_solar_lower=100.0,
        )
        upper = hybrid_zero_upper(0.05, n, 10.0, 0.001)
        budget = radiance_ratio_budget() * 100.0
        self.assertLessEqual(upper, budget)
        if n > 1:
            previous = hybrid_zero_upper(0.05, n - 1, 10.0, 0.001)
            self.assertGreater(previous, budget)

    def test_all_zero_sequential_boundary_is_anytime_valid(self) -> None:
        for q in (1e-2, 1e-4, 1e-8, 1e-12):
            n, crossing_probability = all_zero_crossing_probability(q, 0.05)
            self.assertLess(crossing_probability, 0.05)
            if n > 1:
                previous_log_probability = (n - 1) * math.log1p(-q)
                self.assertGreaterEqual(previous_log_probability, math.log(0.05))

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
