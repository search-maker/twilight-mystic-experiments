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
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction

_DECIMAL_PRECISION = 120
_CERTIFICATION_PRECISIONS = (120, 240, 480, 960)
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
    """Nearest Decimal conversion for candidate generation only, never proof."""
    return Decimal(value.numerator) / Decimal(value.denominator)


def _fraction_decimal_bounds(value: Fraction, precision: int) -> tuple[Decimal, Decimal]:
    """Outward Decimal enclosure of a positive exact Fraction."""
    with localcontext() as ctx:
        ctx.prec = precision
        ctx.rounding = ROUND_FLOOR
        lower = Decimal(value.numerator) / Decimal(value.denominator)
        ctx.rounding = ROUND_CEILING
        upper = Decimal(value.numerator) / Decimal(value.denominator)
    if lower <= 0 or upper <= 0:
        raise ArithmeticError("positive rational could not be enclosed at reference precision")
    return lower, upper


def _ln_fraction_bounds(value: Fraction, precision: int) -> tuple[Decimal, Decimal]:
    """Outward enclosure of ln(value), including rational-to-Decimal error."""
    lower, upper = _fraction_decimal_bounds(value, precision)
    with localcontext() as ctx:
        ctx.prec = precision
        # Decimal.ln is correctly rounded. Expand one representable value on
        # each side so the interval also encloses transcendental rounding.
        log_lower = lower.ln().next_minus()
        log_upper = upper.ln().next_plus()
    return log_lower, log_upper


def zero_upper_common_q(alpha: Fraction | int | str, independent_units: int) -> Decimal:
    """Conservative upper bound 1-alpha**(1/m) for m independent units."""
    a = _fraction(alpha)
    _require_probability("alpha", a)
    if not isinstance(independent_units, int) or isinstance(independent_units, bool) or independent_units <= 0:
        raise ValueError("independent_units must be a positive integer")
    with localcontext() as ctx:
        ctx.prec = _DECIMAL_PRECISION
        # Use a certified lower log(alpha) bound. A lower survival value gives
        # a conservative upper q value. Every subsequent transcendental or
        # arithmetic step is expanded outward rather than assuming that a
        # nearest Decimal conversion of the exact Fraction was exact.
        log_a_lower, _log_a_upper = _ln_fraction_bounds(a, _DECIMAL_PRECISION)
        exponent_lower = (log_a_lower / Decimal(independent_units)).next_minus()
        survival_lower = exponent_lower.exp().next_minus()
        return (Decimal(1) - survival_lower).next_plus()


def required_independent_units(
    alpha: Fraction | int | str,
    q_target: Fraction | int | str,
) -> int:
    """Minimum m with 1-alpha**(1/m) <= q_target, fail-closed near boundaries.

    Candidate generation may use nearest high-precision Decimal arithmetic, but
    certification never does. Exact rational alpha and survival=1-q_target are
    first enclosed with directed Decimal rounding; monotone logarithms are then
    expanded outward. This matters for adversarial targets beyond the working
    precision: one-ulp bounds around ln(nearest_decimal(exact_fraction)) do not
    in general enclose ln(exact_fraction).
    """
    a = _fraction(alpha)
    q = _fraction(q_target)
    _require_probability("alpha", a)
    _require_probability("q_target", q)
    survival = 1 - q
    saw_over_range_candidate = False

    # Equivalent inequality: m*ln(1-q) <= ln(alpha). Both logs are negative.
    # Precision escalates only when the exact rational target is too close to a
    # unit boundary for the current outward interval to prove both sufficiency
    # and one-unit minimality.
    for precision in _CERTIFICATION_PRECISIONS:
        with localcontext() as ctx:
            ctx.prec = precision
            approx_a = _to_decimal(a)
            approx_survival = _to_decimal(survival)
            if approx_survival == 1:
                # Target is smaller than this candidate precision can resolve.
                # Escalate rather than divide by ln(1)=0 or infer a result.
                continue
            raw = approx_a.ln() / approx_survival.ln()
            guess = max(1, int(raw.to_integral_value(rounding=ROUND_CEILING)))
            if guess > _MAX_UNITS:
                saw_over_range_candidate = True

            log_a_lo, log_a_hi = _ln_fraction_bounds(a, precision)
            log_s_lo, log_s_hi = _ln_fraction_bounds(survival, precision)

            # Rounding of the candidate quotient can move by one at an integer
            # boundary. Test the adjacent candidates with the certified log
            # intervals instead of trusting the rounded quotient itself.
            candidates = sorted(
                {
                    candidate
                    for candidate in (guess - 1, guess, guess + 1)
                    if 1 <= candidate <= _MAX_UNITS
                }
            )
            for candidate in candidates:
                # To prove sufficiency, use the least-negative possible
                # survival log and most-negative possible alpha log.
                sufficient = Decimal(candidate) * log_s_hi <= log_a_lo
                # To prove minimality, show candidate-1 fails using the
                # most-negative survival log and least-negative alpha log.
                minimal = candidate == 1 or Decimal(candidate - 1) * log_s_lo > log_a_hi
                if sufficient and minimal:
                    return candidate

    if saw_over_range_candidate:
        raise ValueError("required independent units exceed bounded reference range")
    raise ArithmeticError(
        "could not certify one-unit minimality within bounded reference precision"
    )


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
    """Fail-closed campaign check for an all-zero observation path.

    For the independent-unit tiers, decide against the exact rational target by
    comparing observed unit count with the certified minimum-unit oracle. Do
    not compare a conservative Decimal endpoint with a context-rounded Decimal
    conversion of q_target: near the boundary that can round the target upward
    and falsely accept an insufficient campaign.
    """
    a = _fraction(alpha)
    q = _fraction(q_target)
    _require_probability("alpha", a)
    _require_probability("q_target", q)
    tier = assumption_tier.strip().lower()
    if tier == "photon_iid":
        if not isinstance(photon_histories, int) or isinstance(photon_histories, bool) or photon_histories <= 0:
            raise ValueError("photon_iid tier requires positive photon_histories")
        return photon_histories >= required_independent_units(a, q)
    if tier == "block_independent":
        if not isinstance(independent_blocks, int) or isinstance(independent_blocks, bool) or independent_blocks <= 0:
            raise ValueError("block_independent tier requires positive independent_blocks")
        return independent_blocks >= required_independent_units(a, q)
    if tier == "arbitrary_dependence":
        return (1 - a) <= q
    raise ValueError("unknown assumption_tier")


class ReferenceTests(unittest.TestCase):
    def test_200m_photon_iid_reference(self) -> None:
        q = zero_upper_common_q(Fraction(1, 20), 200_000_000)
        self.assertAlmostEqual(float(q), 1.4978661255589807e-8, places=20)

    def test_zero_upper_is_conservative_for_nonterminating_rationals(self) -> None:
        # Keep exponents small enough that this is an exact Fraction oracle.
        for alpha, units in ((Fraction(1, 3), 37), (Fraction(7, 13), 111)):
            q_upper = Fraction(zero_upper_common_q(alpha, units))
            self.assertLessEqual((1 - q_upper) ** units, alpha)

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
        self.assertTrue(
            zero_only_target_met(
                alpha=alpha,
                q_target=target,
                assumption_tier="photon_iid",
                photon_histories=m,
            )
        )
        if m > 1:
            self.assertFalse(
                zero_only_target_met(
                    alpha=alpha,
                    q_target=target,
                    assumption_tier="photon_iid",
                    photon_histories=m - 1,
                )
            )

    def test_exact_rational_target_boundary_is_context_independent(self) -> None:
        alpha = Fraction(1, 20)
        # Exact target is 1e-30 below the true four-unit boundary
        # 1-alpha**(1/4). At ordinary Decimal precision it rounds upward to
        # 0.5271291954984120933491519401, which is above that boundary. The
        # decision must nevertheless remain fail-closed and require five
        # independent units because q_target itself is an exact Fraction.
        target = Fraction(
            "0.5271291954984120933491519400553924897149015986941298692940463288686548722339674556454690389674503999"
        )
        self.assertEqual(required_independent_units(alpha, target), 5)
        for ambient_precision in (9, 28, 50):
            with localcontext() as ctx:
                ctx.prec = ambient_precision
                self.assertFalse(
                    zero_only_target_met(
                        alpha=alpha,
                        q_target=target,
                        assumption_tier="photon_iid",
                        photon_histories=4,
                    )
                )
                self.assertTrue(
                    zero_only_target_met(
                        alpha=alpha,
                        q_target=target,
                        assumption_tier="photon_iid",
                        photon_histories=5,
                    )
                )
                self.assertFalse(
                    zero_only_target_met(
                        alpha=alpha,
                        q_target=target,
                        assumption_tier="block_independent",
                        independent_blocks=4,
                    )
                )
                self.assertTrue(
                    zero_only_target_met(
                        alpha=alpha,
                        q_target=target,
                        assumption_tier="block_independent",
                        independent_blocks=5,
                    )
                )

    def test_fraction_conversion_error_cannot_certify_insufficient_units(self) -> None:
        alpha = Fraction(1, 10)
        # This exact 245-digit rational is a truncation just below the true
        # 26-unit boundary. The previous implementation converted it to a
        # nearest 120-digit Decimal and then put one-ulp bounds around the log
        # of that rounded input; that incorrectly returned 26. Exact rational
        # powers provide an independent oracle: 26 fails and 27 succeeds.
        target = Fraction(
            "0.08475268912261102517473706390630667852817299944483826920399415052423477419565996897020140194852974207282586404105582494081711061659208388218990083500654772939913222133575396246593393988586746324786394812432023628876866503560875366978810280905500"
        )
        self.assertGreater((1 - target) ** 26, alpha)
        self.assertLessEqual((1 - target) ** 27, alpha)
        self.assertEqual(required_independent_units(alpha, target), 27)
        self.assertFalse(
            zero_only_target_met(
                alpha=alpha,
                q_target=target,
                assumption_tier="photon_iid",
                photon_histories=26,
            )
        )
        self.assertTrue(
            zero_only_target_met(
                alpha=alpha,
                q_target=target,
                assumption_tier="photon_iid",
                photon_histories=27,
            )
        )

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