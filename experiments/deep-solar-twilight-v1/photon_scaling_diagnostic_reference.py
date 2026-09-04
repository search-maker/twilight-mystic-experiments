#!/usr/bin/env python3
"""POST_V1/NONBLOCKING photon-count scaling diagnostic reference.

This module provides a result-blind, solver-free diagnostic for a future deep-
twilight campaign that repeats the *same frozen configuration* in independent
blocks at different photon counts. It does not treat exact zero as physical
zero, does not replace zero by epsilon, and does not authorize science.

Model-qualified diagnostic
--------------------------
For a block containing ``n`` photon histories, let ``H=1`` mean at least one
positive-score history was observed. Under the *strong* photon-level model

    - photon histories are IID within a block,
    - every history has the same hit probability q,
    - blocks are independent,
    - the physical/configuration state is otherwise frozen,

we have

    h_n = P(H=1) = 1 - (1-q)^n.

Equivalently the survival-rate parameter

    theta = -log(1-q)

must be common across photon counts, because

    -log(1-h_n) / n = theta.

This module never assumes that relation merely because different MYSTIC seeds
were supplied. Instead it turns independent block hit/no-hit counts at each
photon count into exact Clopper-Pearson intervals for ``h_n``, maps those
intervals monotonically to intervals for ``theta``, and checks whether all
intervals intersect. Explicit per-group alpha spends are Bonferroni-controlled
against one preregistered familywise budget.

An empty common-theta intersection is evidence *against* the stronger
photon-IID/common-q scaling model at the frozen familywise level. It does not
identify the cause: underconvergence/photon scarcity, RNG stream dependence,
configuration drift, estimator drift, or another violated assumption remain
possible. A non-empty intersection is only a consistency diagnostic, never a
proof of independence.

Without the stronger photon-IID/common-q assumption there is no n-photon
scaling law to test here; callers must use the weaker block-only certificates
instead.
"""

from __future__ import annotations

import argparse
import json
import math
import unittest
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction

_MAX_BLOCKS_PER_GROUP = 512
_DEFAULT_BITS = 80
_DECIMAL_PRECISION = 90


def _fraction(value: Fraction | int | str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("probabilities must be exact Fraction/int/decimal-string values")
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


def _require_count(name: str, value: int, *, positive: bool = True) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if not positive and value < 0:
        raise ValueError(f"{name} must be nonnegative")


def binomial_cdf_exact(n: int, k: int, p: Fraction) -> Fraction:
    _require_count("n", n)
    if n > _MAX_BLOCKS_PER_GROUP:
        raise ValueError(f"bounded exact oracle supports n <= {_MAX_BLOCKS_PER_GROUP}")
    if not isinstance(k, int) or isinstance(k, bool) or not (0 <= k <= n):
        raise ValueError("k must be an integer in [0,n]")
    if not (Fraction(0) <= p <= Fraction(1)):
        raise ValueError("p must lie in [0,1]")
    one_minus = 1 - p
    return sum(
        math.comb(n, j) * (p**j) * (one_minus ** (n - j))
        for j in range(k + 1)
    )


def clopper_pearson_upper_bracket(
    n: int,
    k: int,
    alpha: Fraction,
    *,
    bits: int = _DEFAULT_BITS,
) -> tuple[Fraction, Fraction]:
    """Exact dyadic bracket for the one-sided binomial upper endpoint."""
    _require_count("n", n)
    if n > _MAX_BLOCKS_PER_GROUP:
        raise ValueError(f"bounded exact oracle supports n <= {_MAX_BLOCKS_PER_GROUP}")
    if not isinstance(k, int) or isinstance(k, bool) or not (0 <= k <= n):
        raise ValueError("k must be an integer in [0,n]")
    _require_probability("alpha", alpha)
    _require_count("bits", bits)
    if k == n:
        return Fraction(1), Fraction(1)

    lo = Fraction(0)
    hi = Fraction(1)
    for _ in range(bits):
        mid = (lo + hi) / 2
        if binomial_cdf_exact(n, k, mid) > alpha:
            lo = mid
        else:
            hi = mid

    if not (binomial_cdf_exact(n, k, lo) > alpha):
        raise ArithmeticError("lower bracket lost strict CDF>alpha invariant")
    if not (binomial_cdf_exact(n, k, hi) <= alpha):
        raise ArithmeticError("upper bracket lost conservative CDF<=alpha invariant")
    return lo, hi


def clopper_pearson_two_sided_interval(
    blocks: int,
    hit_blocks: int,
    alpha_group: Fraction,
    *,
    bits: int = _DEFAULT_BITS,
) -> tuple[Fraction, Fraction]:
    """Conservative two-sided interval with total failure <= alpha_group."""
    _require_count("blocks", blocks)
    if blocks > _MAX_BLOCKS_PER_GROUP:
        raise ValueError(
            f"bounded exact oracle supports blocks <= {_MAX_BLOCKS_PER_GROUP}"
        )
    if not isinstance(hit_blocks, int) or isinstance(hit_blocks, bool) or not (
        0 <= hit_blocks <= blocks
    ):
        raise ValueError("hit_blocks must be an integer in [0,blocks]")
    _require_probability("alpha_group", alpha_group)
    tail = alpha_group / 2

    if hit_blocks == 0:
        lower = Fraction(0)
    else:
        # Failure count Y=blocks-S has probability 1-h. The one-sided upper
        # endpoint for P(Y <= blocks-hit_blocks) maps to a conservative lower
        # endpoint for h via h >= 1-u_fail.
        _lo_fail, hi_fail = clopper_pearson_upper_bracket(
            blocks, blocks - hit_blocks, tail, bits=bits
        )
        lower = 1 - hi_fail

    if hit_blocks == blocks:
        upper = Fraction(1)
    else:
        _lo, upper = clopper_pearson_upper_bracket(
            blocks, hit_blocks, tail, bits=bits
        )

    if not (Fraction(0) <= lower <= upper <= Fraction(1)):
        raise ArithmeticError("invalid Clopper-Pearson interval ordering")
    return lower, upper


def _fraction_decimal_bounds(value: Fraction) -> tuple[Decimal, Decimal]:
    """Outward Decimal enclosure of an exact nonnegative Fraction."""
    if value < 0:
        raise ValueError("fraction bound input must be nonnegative")
    with localcontext() as ctx:
        ctx.prec = _DECIMAL_PRECISION
        ctx.rounding = ROUND_FLOOR
        lower = Decimal(value.numerator) / Decimal(value.denominator)
        ctx.rounding = ROUND_CEILING
        upper = Decimal(value.numerator) / Decimal(value.denominator)
    if not (lower <= upper):
        raise ArithmeticError("fraction Decimal enclosure is inverted")
    return lower, upper


def hit_probability_to_theta_interval(
    photon_count: int,
    h_interval: tuple[Fraction, Fraction],
) -> tuple[Decimal, Decimal]:
    """Certified map h -> theta=-log(1-h)/n.

    The input endpoints are exact Fractions.  Convert the exact survival
    probabilities 1-h directly with directed Decimal rounding; do not first
    round h and then subtract from one, because cancellation can move the
    transformed endpoint inward.  Monotonicity of -log(survival) then gives a
    proof-oriented outward theta interval.
    """
    _require_count("photon_count", photon_count)
    lower_h, upper_h = h_interval
    if not (Fraction(0) <= lower_h <= upper_h <= Fraction(1)):
        raise ValueError("h_interval must lie in [0,1] with lower<=upper")

    if lower_h == 0:
        lower_theta = Decimal(0)
    elif lower_h == 1:
        lower_theta = Decimal("Infinity")
    else:
        lower_survival = 1 - lower_h
        _survival_lo, survival_hi = _fraction_decimal_bounds(lower_survival)
        if survival_hi <= 0:
            raise ArithmeticError("positive lower-endpoint survival lost in Decimal enclosure")
        with localcontext() as ctx:
            ctx.prec = _DECIMAL_PRECISION
            # survival_hi >= exact survival, so -ln(survival_hi) is a lower
            # bound.  Expand ln upward, negate, then divide downward.
            log_hi = survival_hi.ln().next_plus()
            ctx.rounding = ROUND_FLOOR
            lower_theta = (-log_hi) / Decimal(photon_count)
            if lower_theta < 0:
                lower_theta = Decimal(0)

    if upper_h == 1:
        upper_theta = Decimal("Infinity")
    else:
        upper_survival = 1 - upper_h
        survival_lo, _survival_hi = _fraction_decimal_bounds(upper_survival)
        if survival_lo <= 0:
            raise ArithmeticError("positive upper-endpoint survival lost in Decimal enclosure")
        with localcontext() as ctx:
            ctx.prec = _DECIMAL_PRECISION
            # survival_lo <= exact survival, so -ln(survival_lo) is an upper
            # bound.  Expand ln downward, negate, then divide upward.
            log_lo = survival_lo.ln().next_minus()
            ctx.rounding = ROUND_CEILING
            upper_theta = (-log_lo) / Decimal(photon_count)

    if lower_theta > upper_theta:
        raise ArithmeticError("theta interval mapping produced an inverted enclosure")
    return lower_theta, upper_theta


@dataclass(frozen=True)
class ScalingGroup:
    photon_count: int
    blocks: int
    hit_blocks: int
    alpha: Fraction


@dataclass(frozen=True)
class ScalingDiagnostic:
    consistent: bool
    theta_lower: Decimal
    theta_upper: Decimal
    group_theta_intervals: tuple[tuple[Decimal, Decimal], ...]


def common_theta_scaling_diagnostic(
    groups: tuple[ScalingGroup, ...],
    total_alpha: Fraction | int | str,
    *,
    assume_photon_iid_common_q: bool,
    bits: int = _DEFAULT_BITS,
) -> ScalingDiagnostic:
    """Familywise model-consistency diagnostic across photon-count groups."""
    if not assume_photon_iid_common_q:
        raise ValueError(
            "photon-count scaling law requires an explicit photon-IID/common-q assumption"
        )
    if len(groups) < 2:
        raise ValueError("at least two photon-count groups are required")
    total = _fraction(total_alpha)
    _require_probability("total_alpha", total)

    spent = Fraction(0)
    seen_counts: set[int] = set()
    intervals: list[tuple[Decimal, Decimal]] = []
    for group in groups:
        if not isinstance(group, ScalingGroup):
            raise TypeError("groups must contain ScalingGroup values")
        _require_count("photon_count", group.photon_count)
        _require_count("blocks", group.blocks)
        if group.blocks > _MAX_BLOCKS_PER_GROUP:
            raise ValueError(
                f"bounded exact oracle supports blocks <= {_MAX_BLOCKS_PER_GROUP}"
            )
        if not isinstance(group.hit_blocks, int) or isinstance(group.hit_blocks, bool) or not (
            0 <= group.hit_blocks <= group.blocks
        ):
            raise ValueError("hit_blocks must be an integer in [0,blocks]")
        if group.photon_count in seen_counts:
            raise ValueError("photon_count values must be unique across diagnostic groups")
        seen_counts.add(group.photon_count)
        af = _fraction(group.alpha)
        _require_probability("group alpha", af)
        spent += af
        if spent > total:
            raise ValueError("group alpha spends exceed preregistered familywise budget")

        h_interval = clopper_pearson_two_sided_interval(
            group.blocks, group.hit_blocks, af, bits=bits
        )
        intervals.append(hit_probability_to_theta_interval(group.photon_count, h_interval))

    theta_lower = max(interval[0] for interval in intervals)
    theta_upper = min(interval[1] for interval in intervals)
    return ScalingDiagnostic(
        consistent=theta_lower <= theta_upper,
        theta_lower=theta_lower,
        theta_upper=theta_upper,
        group_theta_intervals=tuple(intervals),
    )


def theta_to_hit_probability(theta: Decimal, photon_count: int) -> Decimal:
    _require_count("photon_count", photon_count)
    if theta.is_nan() or theta < 0:
        raise ValueError("theta must be nonnegative and not NaN")
    if theta.is_infinite():
        return Decimal(1)
    with localcontext() as ctx:
        ctx.prec = _DECIMAL_PRECISION
        value = Decimal(1) - (-theta * Decimal(photon_count)).exp()
        return min(Decimal(1), max(Decimal(0), value))


class ReferenceTests(unittest.TestCase):
    def test_two_sided_interval_boundaries(self) -> None:
        alpha = Fraction(1, 20)
        lo0, hi0 = clopper_pearson_two_sided_interval(20, 0, alpha, bits=70)
        self.assertEqual(lo0, 0)
        self.assertGreater(hi0, 0)
        lo_all, hi_all = clopper_pearson_two_sided_interval(20, 20, alpha, bits=70)
        self.assertLess(lo_all, 1)
        self.assertEqual(hi_all, 1)

    def test_all_zero_same_block_count_tightens_with_more_photons(self) -> None:
        alpha = Fraction(1, 40)
        h_interval = clopper_pearson_two_sided_interval(20, 0, alpha, bits=70)
        low_n = hit_probability_to_theta_interval(1_000_000, h_interval)
        high_n = hit_probability_to_theta_interval(10_000_000, h_interval)
        self.assertEqual(low_n[0], Decimal(0))
        self.assertEqual(high_n[0], Decimal(0))
        self.assertLess(high_n[1], low_n[1])

    def test_theta_interval_encloses_adversarial_dyadics_beyond_context_precision(self) -> None:
        # These 100-bit singleton intervals expose both cancellation directions
        # in the old implementation.  Rounding h first and then computing 1-h
        # put the lower endpoint above truth for h=2^-100 and the upper endpoint
        # below truth for h=1-2^-100.  The exact-survival mapping must enclose a
        # substantially higher-precision reference in both cases.
        denominator = 1 << 100
        for h in (Fraction(1, denominator), Fraction(denominator - 1, denominator)):
            lower, upper = hit_probability_to_theta_interval(1, (h, h))
            with localcontext() as ctx:
                ctx.prec = 250
                survival = Decimal((1 - h).numerator) / Decimal((1 - h).denominator)
                reference = -(survival.ln())
            self.assertLessEqual(lower, reference)
            self.assertGreaterEqual(upper, reference)

    def test_consistent_synthetic_groups_have_common_theta(self) -> None:
        groups = (
            ScalingGroup(1_000_000, 40, 2, Fraction(1, 40)),
            ScalingGroup(2_000_000, 40, 4, Fraction(1, 40)),
        )
        result = common_theta_scaling_diagnostic(
            groups, Fraction(1, 20), assume_photon_iid_common_q=True, bits=70
        )
        self.assertTrue(result.consistent)
        self.assertLessEqual(result.theta_lower, result.theta_upper)

    def test_incompatible_scaling_rejects_common_theta(self) -> None:
        groups = (
            ScalingGroup(1_000_000, 60, 0, Fraction(1, 40)),
            ScalingGroup(10_000_000, 60, 60, Fraction(1, 40)),
        )
        result = common_theta_scaling_diagnostic(
            groups, Fraction(1, 20), assume_photon_iid_common_q=True, bits=70
        )
        self.assertFalse(result.consistent)
        self.assertGreater(result.theta_lower, result.theta_upper)

    def test_group_alpha_budget_is_fail_closed(self) -> None:
        groups = (
            ScalingGroup(1_000, 20, 0, Fraction(1, 20)),
            ScalingGroup(2_000, 20, 0, Fraction(1, 20)),
        )
        with self.assertRaises(ValueError):
            common_theta_scaling_diagnostic(
                groups, Fraction(1, 20), assume_photon_iid_common_q=True
            )

    def test_scaling_assumption_must_be_explicit(self) -> None:
        groups = (
            ScalingGroup(1_000, 20, 0, Fraction(1, 40)),
            ScalingGroup(2_000, 20, 0, Fraction(1, 40)),
        )
        with self.assertRaises(ValueError):
            common_theta_scaling_diagnostic(
                groups, Fraction(1, 20), assume_photon_iid_common_q=False
            )

    def test_duplicate_photon_count_refused(self) -> None:
        groups = (
            ScalingGroup(1_000, 20, 0, Fraction(1, 40)),
            ScalingGroup(1_000, 20, 1, Fraction(1, 40)),
        )
        with self.assertRaises(ValueError):
            common_theta_scaling_diagnostic(
                groups, Fraction(1, 20), assume_photon_iid_common_q=True
            )

    def test_theta_hit_probability_monotone_in_photons(self) -> None:
        theta = Decimal("1e-8")
        h1 = theta_to_hit_probability(theta, 10_000_000)
        h2 = theta_to_hit_probability(theta, 100_000_000)
        self.assertGreater(h2, h1)
        self.assertGreater(h1, 0)
        self.assertLess(h2, 1)

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(TypeError):
            common_theta_scaling_diagnostic(
                (
                    ScalingGroup(1_000, 20, 0, Fraction(1, 40)),
                    ScalingGroup(2_000, 20, 0, Fraction(1, 40)),
                ),
                0.05,  # type: ignore[arg-type]
                assume_photon_iid_common_q=True,
            )
        with self.assertRaises(ValueError):
            clopper_pearson_two_sided_interval(0, 0, Fraction(1, 20))
        with self.assertRaises(ValueError):
            hit_probability_to_theta_interval(0, (Fraction(0), Fraction(1, 2)))


def _summary() -> dict[str, object]:
    groups = (
        ScalingGroup(1_000_000, 40, 2, Fraction(1, 40)),
        ScalingGroup(2_000_000, 40, 4, Fraction(1, 40)),
    )
    result = common_theta_scaling_diagnostic(
        groups, Fraction(1, 20), assume_photon_iid_common_q=True, bits=70
    )
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "model": "independent blocks plus explicit photon-IID/common-q scaling hypothesis",
        "familywise_alpha": "0.05",
        "consistent": result.consistent,
        "common_theta_lower": str(result.theta_lower),
        "common_theta_upper": str(result.theta_upper),
        "group_theta_intervals": [
            [str(lower), str(upper)]
            for lower, upper in result.group_theta_intervals
        ],
        "interpretation": (
            "empty intersection rejects the scaling model at the frozen familywise level; "
            "non-empty intersection is not proof of independence"
        ),
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