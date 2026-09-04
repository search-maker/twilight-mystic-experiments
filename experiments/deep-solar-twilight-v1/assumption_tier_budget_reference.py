#!/usr/bin/env python3
"""POST_V1/NONBLOCKING rare-event assumption-tier campaign budget reference.

This module is result-blind and solver-free. It turns a frozen all-zero
materiality target into the minimum amount of *independent statistical units*
required under three distinct dependence assumptions:

1. photon-IID/common-q: the independent unit is one photon history;
2. independent blocks with arbitrary within-block dependence: the independent
   unit is one block/run, so photons added inside an existing block do not buy
   an N-photon zero bound;
3. arbitrary global dependence: repeated zero observations provide no sample-
   count gain; the sharp common-q upper bound remains 1-alpha.

No exact zero is interpreted as physical zero and no epsilon substitution is
used. The output is planning/reference mathematics only; it does not authorize
MYSTIC execution, protected-result opening, Level-B changes, or any AVPS
transition.
"""

from __future__ import annotations

import argparse
import json
import unittest
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, localcontext
from fractions import Fraction

_DECIMAL_PRECISION = 120
_MAX_UNITS = 10**15


def _fraction(value: Fraction | int | str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("exact probabilities/budgets must not be binary64 floats")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    raise TypeError("unsupported exact scalar type")


def _require_probability(name: str, value: Fraction) -> None:
    if not (Fraction(0) < value < Fraction(1)):
        raise ValueError(f"{name} must lie strictly between 0 and 1")


def _require_nonnegative(name: str, value: Fraction) -> None:
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _to_decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def zero_upper_common_q(alpha: Fraction | int | str, independent_units: int) -> Decimal:
    """Conservative upper bound 1-alpha**(1/m) for m independent units."""
    a = _fraction(alpha)
    _require_probability("alpha", a)
    if not isinstance(independent_units, int) or isinstance(independent_units, bool) or independent_units <= 0:
        raise ValueError("independent_units must be a positive integer")
    with localcontext() as ctx:
        ctx.prec = _DECIMAL_PRECISION
        log_a = _to_decimal(a).ln()
        root = (log_a / Decimal(independent_units)).exp()
        # q=1-root is monotone decreasing in root. next_minus() makes the
        # survival value conservative downward, hence q conservative upward.
        survival_lower = root.next_minus()
        return (Decimal(1) - survival_lower).next_plus()


def required_independent_units(
    alpha: Fraction | int | str,
    q_target: Fraction | int | str,
) -> int:
    """Minimum m with 1-alpha**(1/m) <= q_target, fail-closed near boundaries."""
    a = _fraction(alpha)
    q = _fraction(q_target)
    _require_probability("alpha", a)
    _require_probability("q_target", q)

    # Equivalent inequality: m*ln(1-q) <= ln(alpha).  Both logs are negative.
    # Use high-precision Decimal for the candidate, then certify m and m-1 with
    # outward one-ulp log bounds rather than trusting a rounded quotient alone.
    for precision in (_DECIMAL_PRECISION, _DECIMAL_PRECISION * 2):
        with localcontext() as ctx:
            ctx.prec = precision
            log_a = _to_decimal(a).ln()
            log_s = (Decimal(1) - _to_decimal(q)).ln()
            raw = log_a / log_s
            m = int(raw.to_integral_value(rounding=ROUND_CEILING))
            m = max(1, m)
            if m > _MAX_UNITS:
                raise ValueError("required independent units exceed bounded reference range")

            # True logs lie between adjacent representable Decimals around the
            # rounded results. To prove m sufficient, use the least-favourable
            # (least negative) survival log and most-negative alpha log.
            log_a_lo = log_a.next_minus()
            log_a_hi = log_a.next_plus()
            log_s_lo = log_s.next_minus()
            log_s_hi = log_s.next_plus()
            sufficient = Decimal(m) * log_s_hi <= log_a_lo
            minimal = m == 1 or Decimal(m - 1) * log_s_lo > log_a_hi
            if sufficient and minimal:
                return m
    raise ArithmeticError("could not certify one-unit minimality; increase reference precision")


def q_target_from_mean_budget(
    *,
    finite_order_envelope: Fraction | int | str,
    deterministic_tail_upper: Fraction | int | str,
    allowed_total_mean: Fraction | int | str,
) -> Fraction:
    """Exact q target from B*q + U_tail <= allowed_total_mean."""
    envelope = _fraction(finite_order_envelope)
    tail = _fraction(deterministic_tail_upper)
    allowed = _fraction(allowed_total_mean)
    _require_nonnegative("finite_order_envelope", envelope)
    _require_nonnegative("deterministic_tail_upper", tail)
    _require_nonnegative("allowed_total_mean", allowed)
    residual = allowed - tail
    if residual <= 0:
        raise ValueError("deterministic tail exhausts the allowed mean budget")
    if envelope == 0:
        return Fraction(1, 1)
    q = residual / envelope
    if q >= 1:
        return Fraction(1, 1)
    if q <= 0:
        raise ValueError("nonpositive q target is not certifiable by finite zero sampling")
    return q


@dataclass(frozen=True)
class TierPlan:
    q_target: Fraction
    photon_iid_histories_required: int
    block_only_independent_blocks_required: int
    arbitrary_dependence_can_reach_target: bool
    arbitrary_dependence_q_upper: Fraction
    photons_per_block: int | None
    block_only_total_photons_required: int | None


def plan_zero_only_tiers(
    *,
    alpha: Fraction | int | str,
    q_target: Fraction | int | str,
    photons_per_block: int | None = None,
) -> TierPlan:
    """Compare campaign cost semantics across dependence assumptions."""
    a = _fraction(alpha)
    q = _fraction(q_target)
    _require_probability("alpha", a)
    if q == 1:
        # Any single independent unit is enough when the target is >=1.
        units = 1
    else:
        _require_probability("q_target", q)
        units = required_independent_units(a, q)

    if photons_per_block is not None:
        if not isinstance(photons_per_block, int) or isinstance(photons_per_block, bool) or photons_per_block <= 0:
            raise ValueError("photons_per_block must be a positive integer when supplied")
        total_photons = units * photons_per_block
    else:
        total_photons = None

    arbitrary_q = 1 - a
    return TierPlan(
        q_target=q,
        photon_iid_histories_required=units,
        block_only_independent_blocks_required=units,
        arbitrary_dependence_can_reach_target=arbitrary_q <= q,
        arbitrary_dependence_q_upper=arbitrary_q,
        photons_per_block=photons_per_block,
        block_only_total_photons_required=total_photons,
    )


def zero_only_target_met(
    *,
    alpha: Fraction | int | str,
    q_target: Fraction | int | str,
    assumption_tier: str,
    photon_histories: int | None = None,
    independent_blocks: int | None = None,
) -> bool:
    """Fail-closed campaign check for an all-zero observation path."""
    a = _fraction(alpha)
    q = _fraction(q_target)
    _require_probability("alpha", a)
    _require_probability("q_target", q)
    tier = assumption_tier.strip().lower()
    if tier == "photon_iid":
        if not isinstance(photon_histories, int) or isinstance(photon_histories, bool) or photon_histories <= 0:
            raise ValueError("photon_iid tier requires positive photon_histories")
        return zero_upper_common_q(a, photon_histories) <= _to_decimal(q)
    if tier == "block_independent":
        if not isinstance(independent_blocks, int) or isinstance(independent_blocks, bool) or independent_blocks <= 0:
            raise ValueError("block_independent tier requires positive independent_blocks")
        return zero_upper_common_q(a, independent_blocks) <= _to_decimal(q)
    if tier == "arbitrary_dependence":
        return (1 - a) <= q
    raise ValueError("unknown assumption_tier")


class ReferenceTests(unittest.TestCase):
    def test_200m_photon_iid_reference(self) -> None:
        q = zero_upper_common_q(Fraction(1, 20), 200_000_000)
        self.assertAlmostEqual(float(q), 1.4978661255589807e-8, places=20)

    def test_single_block_200m_has_no_block_only_gain(self) -> None:
        alpha = Fraction(1, 20)
        self.assertFalse(
            zero_only_target_met(
                alpha=alpha,
                q_target=Fraction(1, 1_000_000),
                assumption_tier="block_independent",
                independent_blocks=1,
                photon_histories=200_000_000,
            )
        )
        with localcontext() as ctx:
            ctx.prec = _DECIMAL_PRECISION
            expected = Decimal("0.95").next_plus()
        # The returned conservative endpoint is defined at the module's frozen
        # precision, not at the caller's ambient Decimal context. Guard this
        # explicitly so a low/default context cannot make the test itself lie.
        for ambient_precision in (9, 28, 50):
            with localcontext() as ctx:
                ctx.prec = ambient_precision
                self.assertEqual(zero_upper_common_q(alpha, 1), expected)

    def test_photon_iid_can_meet_target_that_one_block_cannot(self) -> None:
        target = Fraction(1, 1_000_000)
        self.assertTrue(
            zero_only_target_met(
                alpha=Fraction(1, 20),
                q_target=target,
                assumption_tier="photon_iid",
                photon_histories=200_000_000,
            )
        )
        self.assertFalse(
            zero_only_target_met(
                alpha=Fraction(1, 20),
                q_target=target,
                assumption_tier="block_independent",
                independent_blocks=1,
            )
        )

    def test_required_units_are_minimal(self) -> None:
        alpha = Fraction(1, 20)
        target = Fraction(1, 10_000_000)
        m = required_independent_units(alpha, target)
        self.assertTrue(zero_upper_common_q(alpha, m) <= _to_decimal(target))
        if m > 1:
            self.assertTrue(zero_upper_common_q(alpha, m - 1) > _to_decimal(target))

    def test_same_unit_count_different_semantics(self) -> None:
        plan = plan_zero_only_tiers(
            alpha=Fraction(1, 20),
            q_target=Fraction(1, 1_000_000),
            photons_per_block=10_000_000,
        )
        self.assertEqual(
            plan.photon_iid_histories_required,
            plan.block_only_independent_blocks_required,
        )
        self.assertEqual(
            plan.block_only_total_photons_required,
            plan.block_only_independent_blocks_required * 10_000_000,
        )
        self.assertFalse(plan.arbitrary_dependence_can_reach_target)

    def test_arbitrary_dependence_has_no_sample_count_gain(self) -> None:
        alpha = Fraction(1, 20)
        target = Fraction(9, 10)
        self.assertFalse(
            zero_only_target_met(
                alpha=alpha,
                q_target=target,
                assumption_tier="arbitrary_dependence",
                photon_histories=10**12,
                independent_blocks=10**6,
            )
        )
        self.assertTrue(
            zero_only_target_met(
                alpha=alpha,
                q_target=Fraction(19, 20),
                assumption_tier="arbitrary_dependence",
            )
        )

    def test_exact_materiality_target(self) -> None:
        q = q_target_from_mean_budget(
            finite_order_envelope=Fraction(10),
            deterministic_tail_upper=Fraction(1, 1000),
            allowed_total_mean=Fraction(1, 100),
        )
        self.assertEqual(q, Fraction(9, 10_000))

    def test_tail_exhaustion_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "tail exhausts"):
            q_target_from_mean_budget(
                finite_order_envelope=1,
                deterministic_tail_upper=1,
                allowed_total_mean=1,
            )

    def test_float_configuration_refused(self) -> None:
        with self.assertRaises(TypeError):
            required_independent_units(0.05, Fraction(1, 1000))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            q_target_from_mean_budget(
                finite_order_envelope=1.0,  # type: ignore[arg-type]
                deterministic_tail_upper=0,
                allowed_total_mean=1,
            )

    def test_unknown_tier_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            zero_only_target_met(
                alpha=Fraction(1, 20),
                q_target=Fraction(1, 100),
                assumption_tier="seeded_therefore_independent",
                photon_histories=10,
            )


def _summary() -> dict[str, object]:
    plan = plan_zero_only_tiers(
        alpha=Fraction(1, 20),
        q_target=Fraction(1, 1_000_000),
        photons_per_block=10_000_000,
    )
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "q_target": str(plan.q_target),
        "photon_iid_histories_required": plan.photon_iid_histories_required,
        "block_only_independent_blocks_required": plan.block_only_independent_blocks_required,
        "block_only_total_photons_required": plan.block_only_total_photons_required,
        "arbitrary_dependence_q_upper": str(plan.arbitrary_dependence_q_upper),
        "arbitrary_dependence_can_reach_target": plan.arbitrary_dependence_can_reach_target,
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
