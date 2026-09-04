#!/usr/bin/env python3
"""POST_V1/NONBLOCKING bounded exact finite-hit confidence reference.

This module closes the methodological gap between an all-zero rare-event path
and a finite-but-small hit count without changing any historical estimator
outcome.  It is solver-free, result-blind, and never substitutes epsilon for
zero.

Statistical scope
-----------------
For a preregistered fixed horizon of ``n`` independent Bernoulli hit
indicators with common hit probability ``q``, observing ``k`` hits gives the
one-sided Clopper-Pearson upper endpoint ``q_U`` defined by

    P_{q_U}[Binomial(n, q_U) <= k] = alpha,      k < n.

For ``k=0`` this reduces exactly to

    q_U = 1 - alpha**(1/n).

If each nonnegative score is independently bounded by a frozen envelope ``B``,
then ``E[X] <= B*q_U``.  A separately certified deterministic tail may be
added.  Without such an envelope this module refuses to turn hit counts into a
finite mean/radiance cap.

Repeated finite-hit looks are *not* granted the special nested-path anytime
property of the all-zero event.  Multiple preregistered looks must therefore
carry an explicit familywise alpha allocation; a union bound then preserves
coverage.  This module enforces that budget rather than silently reusing the
same alpha at every look.

Implementation scope
--------------------
The inversion below is an exact-rational, dyadic bisection oracle intended for
bounded reference/QA cases, not for 200M-photon production arithmetic.  It
returns a bracket ``(lo, hi)`` around the exact endpoint and the conservative
certificate uses ``hi``.  Larger production runs must use a separately
validated scalable implementation against this bounded oracle.
"""

from __future__ import annotations

import argparse
import json
import math
import unittest
from dataclasses import dataclass
from fractions import Fraction

_MAX_EXACT_N = 512
_DEFAULT_BITS = 80


def _fraction(value: Fraction | int | str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("probabilities/envelopes must be exact Fraction/int/decimal-string values")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    raise TypeError("unsupported exact scalar type")


def _require_probability(name: str, value: Fraction) -> None:
    if not (Fraction(0) < value < Fraction(1)):
        raise ValueError(f"{name} must be strictly between 0 and 1")


def _require_n_k(n: int, k: int) -> None:
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError("n must be a positive integer")
    if n > _MAX_EXACT_N:
        raise ValueError(f"bounded exact oracle supports n <= {_MAX_EXACT_N}")
    if not isinstance(k, int) or isinstance(k, bool) or not (0 <= k <= n):
        raise ValueError("k must be an integer in [0,n]")


def binomial_cdf_exact(n: int, k: int, q: Fraction | int | str) -> Fraction:
    """Exact P[Binomial(n,q) <= k] for the bounded oracle domain."""
    _require_n_k(n, k)
    qf = _fraction(q)
    if not (Fraction(0) <= qf <= Fraction(1)):
        raise ValueError("q must lie in [0,1]")
    one_minus = 1 - qf
    total = Fraction(0)
    for j in range(k + 1):
        total += math.comb(n, j) * (qf**j) * (one_minus ** (n - j))
    return total


def clopper_pearson_upper_bracket(
    n: int,
    k: int,
    alpha: Fraction | int | str,
    *,
    bits: int = _DEFAULT_BITS,
) -> tuple[Fraction, Fraction]:
    """Exact-rational bracket for the one-sided fixed-horizon upper endpoint.

    For k<n, invariants on return are

        CDF(lo) > alpha >= CDF(hi)

    so the true endpoint lies in (lo, hi] and ``hi`` is conservative.
    For k=n the exact endpoint is one.
    """
    _require_n_k(n, k)
    af = _fraction(alpha)
    _require_probability("alpha", af)
    if not isinstance(bits, int) or isinstance(bits, bool) or bits <= 0:
        raise ValueError("bits must be a positive integer")
    if k == n:
        return Fraction(1), Fraction(1)

    lo = Fraction(0)
    hi = Fraction(1)
    # CDF(0)=1>alpha and CDF(1)=0<=alpha for k<n.
    for _ in range(bits):
        mid = (lo + hi) / 2
        if binomial_cdf_exact(n, k, mid) > af:
            lo = mid
        else:
            hi = mid

    if not (binomial_cdf_exact(n, k, lo) > af):
        raise ArithmeticError("lower bracket lost strict CDF>alpha invariant")
    if not (binomial_cdf_exact(n, k, hi) <= af):
        raise ArithmeticError("upper bracket lost conservative CDF<=alpha invariant")
    return lo, hi


def bounded_mean_upper(
    n: int,
    k: int,
    alpha: Fraction | int | str,
    envelope: Fraction | int | str,
    *,
    deterministic_tail: Fraction | int | str = 0,
    bits: int = _DEFAULT_BITS,
) -> Fraction:
    """Conservative fixed-horizon mean cap B*q_U + deterministic_tail."""
    bf = _fraction(envelope)
    tail = _fraction(deterministic_tail)
    if bf < 0 or tail < 0:
        raise ValueError("envelope and deterministic_tail must be nonnegative")
    _lo, hi = clopper_pearson_upper_bracket(n, k, alpha, bits=bits)
    return bf * hi + tail


@dataclass(frozen=True)
class PreregisteredLook:
    n: int
    k: int
    alpha: Fraction


def familywise_fixed_horizon_upper_brackets(
    looks: tuple[PreregisteredLook, ...],
    total_alpha: Fraction | int | str,
    *,
    bits: int = _DEFAULT_BITS,
) -> tuple[tuple[Fraction, Fraction], ...]:
    """Bonferroni-valid upper brackets for multiple preregistered finite-hit looks.

    The looks must be strictly increasing in n and their explicit alpha spends
    must sum to at most ``total_alpha``.  This is deliberately conservative but
    requires no unproved anytime claim after finite hits appear.
    """
    if not looks:
        raise ValueError("at least one preregistered look is required")
    total = _fraction(total_alpha)
    _require_probability("total_alpha", total)

    previous_n = 0
    spent = Fraction(0)
    out: list[tuple[Fraction, Fraction]] = []
    for look in looks:
        if not isinstance(look, PreregisteredLook):
            raise TypeError("looks must contain PreregisteredLook values")
        _require_n_k(look.n, look.k)
        if look.n <= previous_n:
            raise ValueError("look horizons must be strictly increasing")
        af = _fraction(look.alpha)
        _require_probability("look alpha", af)
        spent += af
        if spent > total:
            raise ValueError("finite-hit looks exceed preregistered familywise alpha budget")
        out.append(clopper_pearson_upper_bracket(look.n, look.k, af, bits=bits))
        previous_n = look.n
    return tuple(out)


class ReferenceTests(unittest.TestCase):
    def test_zero_hit_endpoint_reduces_to_known_formula(self) -> None:
        n = 20
        alpha = Fraction(1, 20)
        lo, hi = clopper_pearson_upper_bracket(n, 0, alpha, bits=90)
        # For k=0, the binomial CDF is exactly (1-q)^n.  Check the
        # defining formula in exact rational arithmetic rather than converting
        # the 90-bit bracket to binary64, which can collapse both endpoints to
        # the same float and spuriously fail a correct certificate.
        self.assertEqual(binomial_cdf_exact(n, 0, lo), (1 - lo) ** n)
        self.assertEqual(binomial_cdf_exact(n, 0, hi), (1 - hi) ** n)
        self.assertGreater((1 - lo) ** n, alpha)
        self.assertLessEqual((1 - hi) ** n, alpha)
        self.assertLessEqual(hi - lo, Fraction(1, 2**90))

    def test_finite_hit_boundary_is_exactly_bracketed(self) -> None:
        alpha = Fraction(1, 20)
        lo, hi = clopper_pearson_upper_bracket(30, 2, alpha, bits=70)
        self.assertGreater(binomial_cdf_exact(30, 2, lo), alpha)
        self.assertLessEqual(binomial_cdf_exact(30, 2, hi), alpha)
        self.assertLessEqual(hi - lo, Fraction(1, 2**70))

    def test_more_hits_cannot_tighten_same_horizon_upper(self) -> None:
        alpha = Fraction(1, 20)
        uppers = [
            clopper_pearson_upper_bracket(40, k, alpha, bits=70)[1]
            for k in range(5)
        ]
        self.assertEqual(uppers, sorted(uppers))
        self.assertEqual(len(set(uppers)), len(uppers))

    def test_all_hits_has_exact_upper_one(self) -> None:
        self.assertEqual(
            clopper_pearson_upper_bracket(12, 12, Fraction(1, 20)),
            (Fraction(1), Fraction(1)),
        )

    def test_envelope_plus_deterministic_tail(self) -> None:
        alpha = Fraction(1, 20)
        cap = bounded_mean_upper(
            20,
            1,
            alpha,
            Fraction(3, 2),
            deterministic_tail=Fraction(1, 1000),
            bits=70,
        )
        _lo, hi = clopper_pearson_upper_bracket(20, 1, alpha, bits=70)
        self.assertEqual(cap, Fraction(3, 2) * hi + Fraction(1, 1000))

    def test_multiple_finite_looks_require_explicit_alpha_budget(self) -> None:
        looks = (
            PreregisteredLook(20, 0, Fraction(1, 40)),
            PreregisteredLook(40, 1, Fraction(1, 40)),
        )
        result = familywise_fixed_horizon_upper_brackets(
            looks, Fraction(1, 20), bits=60
        )
        self.assertEqual(len(result), 2)
        with self.assertRaises(ValueError):
            familywise_fixed_horizon_upper_brackets(
                (
                    PreregisteredLook(20, 0, Fraction(1, 20)),
                    PreregisteredLook(40, 1, Fraction(1, 20)),
                ),
                Fraction(1, 20),
                bits=40,
            )

    def test_nonincreasing_look_schedule_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            familywise_fixed_horizon_upper_brackets(
                (
                    PreregisteredLook(40, 1, Fraction(1, 40)),
                    PreregisteredLook(20, 0, Fraction(1, 40)),
                ),
                Fraction(1, 20),
            )

    def test_bounded_oracle_refuses_unbounded_production_n(self) -> None:
        with self.assertRaises(ValueError):
            clopper_pearson_upper_bracket(200_000_000, 0, Fraction(1, 20))

    def test_float_inputs_fail_closed(self) -> None:
        with self.assertRaises(TypeError):
            clopper_pearson_upper_bracket(20, 0, 0.05)
        with self.assertRaises(TypeError):
            bounded_mean_upper(20, 0, Fraction(1, 20), 1.0)


def _summary() -> dict[str, object]:
    alpha = Fraction(1, 20)
    lo, hi = clopper_pearson_upper_bracket(30, 2, alpha)
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "scope": "fixed-horizon IID/common-hit model; bounded exact oracle",
        "n": 30,
        "k": 2,
        "alpha": str(alpha),
        "q_upper_lower_bracket": str(lo),
        "q_upper_conservative": str(hi),
        "bracket_width": str(hi - lo),
        "multi_look_rule": "explicit preregistered alpha spending required after finite hits",
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
