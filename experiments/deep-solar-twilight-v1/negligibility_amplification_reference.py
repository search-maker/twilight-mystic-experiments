#!/usr/bin/env python3
"""POST_V1/NONBLOCKING deterministic solar-negligibility reference.

This module is solver-free and result-blind. It does not infer any physical
optical-property bound. Instead it composes already-frozen conservative bounds
for a solar contribution and tests whether that entire contribution is
material relative to a separately frozen lower bound on non-solar radiance.

If U_s is an upper bound on solar radiance, A_i >= 1 are multiplicative
amplification bounds, U_add is a nonnegative additive solar/tail bound, and
L_ns > 0 is a lower bound on non-solar radiance, then

    R = (U_s * product(A_i) + U_add) / L_ns

is a deterministic upper bound on the fractional total-radiance increase from
retaining the solar term only when the multiplicative factors are jointly
composable. Separate one-at-a-time or marginal sensitivities are not, by
themselves, a proof that their product is a joint upper bound. Therefore this
reference refuses to multiply more than one factor unless the caller explicitly
asserts that a separate reviewed joint/conditional composability proof exists.

Ignoring the solar term changes sky magnitude by at most

    delta_m = 2.5 * log10(1 + R).

For a magnitude tolerance t, the exact materiality boundary is

    R <= 10**(t/2.5) - 1.

The implementation uses exact Fraction arithmetic for all supplied physical
bounds and a directed high-precision Decimal lower enclosure of the allowed
ratio. A PASS therefore cannot be created by binary64 rounding. Exact zero is
never replaced by epsilon.
"""

from __future__ import annotations

import argparse
import json
import unittest
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction

_CERTIFICATION_PRECISIONS = (120, 240, 480, 960)


def _fraction(value: Fraction | int | str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("bounds must be exact Fraction/int/decimal-string values")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    raise TypeError("unsupported exact scalar type")


def _require_nonnegative(name: str, value: Fraction) -> None:
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")


def _joint_factor_product(
    multiplicative_factors: tuple[Fraction | int | str, ...],
    *,
    jointly_composable: bool,
) -> Fraction:
    """Return an exact product only under an explicit composition contract.

    A single factor may already be a reviewed joint upper bound and therefore
    needs no extra flag. More than one factor is rejected by default because
    separately certified marginal/one-factor sensitivities need not remain
    valid under simultaneous perturbation. Setting jointly_composable=True is
    an assertion that a separate reviewed proof establishes that the supplied
    factors are uniform conditional bounds whose product is a valid joint upper
    bound; the flag is not itself that proof.
    """
    if not isinstance(jointly_composable, bool):
        raise TypeError("jointly_composable must be a bool")

    factors: list[Fraction] = []
    for raw_factor in multiplicative_factors:
        factor = _fraction(raw_factor)
        if factor < 1:
            raise ValueError(
                "multiplicative amplification factors must be >= 1; attenuation-only "
                "credit requires a separately reviewed bound"
            )
        factors.append(factor)

    if len(factors) > 1 and not jointly_composable:
        raise ValueError(
            "multiple amplification factors are not automatically composable; "
            "separate marginal/one-at-a-time bounds cannot be multiplied without "
            "a reviewed joint or uniform-conditional composability proof"
        )

    product = Fraction(1)
    for factor in factors:
        product *= factor
    return product


def _fraction_decimal_bounds(value: Fraction, precision: int) -> tuple[Decimal, Decimal]:
    """Directed Decimal enclosure of a nonnegative exact Fraction."""
    if value < 0:
        raise ValueError("cannot enclose a negative Fraction")
    with localcontext() as ctx:
        ctx.prec = precision
        ctx.rounding = ROUND_FLOOR
        lower = Decimal(value.numerator) / Decimal(value.denominator)
        ctx.rounding = ROUND_CEILING
        upper = Decimal(value.numerator) / Decimal(value.denominator)
    if not lower <= upper:
        raise ArithmeticError("Fraction Decimal enclosure inverted")
    return lower, upper


def magnitude_ratio_budget_lower(
    magnitude_tolerance: Fraction | int | str,
) -> Fraction:
    """Conservative lower bound on 10**(t/2.5)-1 for exact positive t.

    Returning a lower enclosure is deliberate: a negligibility PASS compares an
    exact upper radiance ratio against this smaller allowed budget.
    """
    tolerance = _fraction(magnitude_tolerance)
    if tolerance <= 0:
        raise ValueError("magnitude_tolerance must be positive")

    for precision in _CERTIFICATION_PRECISIONS:
        tolerance_lo, _tolerance_hi = _fraction_decimal_bounds(tolerance, precision)
        with localcontext() as ctx:
            ctx.prec = precision
            # Decimal.ln()/exp() are correctly rounded; one representable step
            # outward also covers the transcendental rounding itself.
            ln10_lo = Decimal(10).ln().next_minus()
            ctx.rounding = ROUND_FLOOR
            exponent_lo = (
                ln10_lo * tolerance_lo * Decimal(2) / Decimal(5)
            ).next_minus()
            exp_lo = exponent_lo.exp().next_minus()
            budget_lo = (exp_lo - Decimal(1)).next_minus()
        if budget_lo > 0:
            return Fraction(budget_lo)

    raise ArithmeticError(
        "could not certify a positive magnitude-ratio budget within bounded precision"
    )


def amplified_solar_upper(
    base_solar_upper: Fraction | int | str,
    *,
    multiplicative_factors: tuple[Fraction | int | str, ...] = (),
    jointly_composable: bool = False,
    additive_solar_upper: Fraction | int | str = 0,
) -> Fraction:
    """Exact composition of frozen multiplicative and additive solar bounds.

    More than one multiplicative factor requires jointly_composable=True, which
    asserts that an external reviewed joint/conditional proof makes the product
    a valid upper bound. Marginal factors are rejected by default.
    """
    base = _fraction(base_solar_upper)
    additive = _fraction(additive_solar_upper)
    _require_nonnegative("base_solar_upper", base)
    _require_nonnegative("additive_solar_upper", additive)

    factor_product = _joint_factor_product(
        multiplicative_factors,
        jointly_composable=jointly_composable,
    )
    return base * factor_product + additive


def solar_to_nonsolar_ratio_upper(
    base_solar_upper: Fraction | int | str,
    non_solar_lower: Fraction | int | str,
    *,
    multiplicative_factors: tuple[Fraction | int | str, ...] = (),
    jointly_composable: bool = False,
    additive_solar_upper: Fraction | int | str = 0,
) -> Fraction:
    """Exact upper bound U_s/L_ns after frozen amplification composition."""
    non_solar = _fraction(non_solar_lower)
    if non_solar <= 0:
        raise ValueError("non_solar_lower must be positive")
    solar = amplified_solar_upper(
        base_solar_upper,
        multiplicative_factors=multiplicative_factors,
        jointly_composable=jointly_composable,
        additive_solar_upper=additive_solar_upper,
    )
    return solar / non_solar


def max_multiplicative_amplification(
    *,
    base_solar_upper: Fraction | int | str,
    additive_solar_upper: Fraction | int | str,
    non_solar_lower: Fraction | int | str,
    magnitude_tolerance: Fraction | int | str,
) -> Fraction:
    """Largest admissible total multiplicative factor allowed by the gate.

    The returned factor uses the conservative *lower* allowed-ratio enclosure.
    A separately certified optical-property factor A is safe only when
    A <= returned_factor. Because admissible amplification factors satisfy
    A >= 1, this function returns zero when even A=1 cannot satisfy the gate;
    it never reports an attenuation-like factor below one as usable headroom.
    """
    base = _fraction(base_solar_upper)
    additive = _fraction(additive_solar_upper)
    non_solar = _fraction(non_solar_lower)
    _require_nonnegative("base_solar_upper", base)
    _require_nonnegative("additive_solar_upper", additive)
    if non_solar <= 0:
        raise ValueError("non_solar_lower must be positive")
    if base == 0:
        raise ValueError("base_solar_upper must be positive to define an amplification factor")

    budget = magnitude_ratio_budget_lower(magnitude_tolerance)
    residual = budget * non_solar - additive
    if residual <= 0:
        return Fraction(0)
    limit = residual / base
    if limit < 1:
        return Fraction(0)
    return limit


@dataclass(frozen=True)
class NegligibilityCertificate:
    amplified_solar_upper: Fraction
    non_solar_lower: Fraction
    ratio_upper: Fraction
    ratio_budget_lower: Fraction
    negligible: bool


def negligibility_certificate(
    *,
    base_solar_upper: Fraction | int | str,
    non_solar_lower: Fraction | int | str,
    magnitude_tolerance: Fraction | int | str,
    multiplicative_factors: tuple[Fraction | int | str, ...] = (),
    jointly_composable: bool = False,
    additive_solar_upper: Fraction | int | str = 0,
) -> NegligibilityCertificate:
    """Return a fail-closed deterministic U_s/L_ns materiality certificate."""
    non_solar = _fraction(non_solar_lower)
    if non_solar <= 0:
        raise ValueError("non_solar_lower must be positive")
    solar = amplified_solar_upper(
        base_solar_upper,
        multiplicative_factors=multiplicative_factors,
        jointly_composable=jointly_composable,
        additive_solar_upper=additive_solar_upper,
    )
    ratio = solar / non_solar
    budget = magnitude_ratio_budget_lower(magnitude_tolerance)
    return NegligibilityCertificate(
        amplified_solar_upper=solar,
        non_solar_lower=non_solar,
        ratio_upper=ratio,
        ratio_budget_lower=budget,
        negligible=ratio <= budget,
    )


class ReferenceTests(unittest.TestCase):
    def test_001_mag_ratio_budget_is_conservative_and_tight(self) -> None:
        budget = magnitude_ratio_budget_lower(Fraction(1, 100))
        # Known high-precision value is about 0.009252886076684412.
        self.assertGreater(budget, Fraction("0.00925288607668440"))
        self.assertLess(budget, Fraction("0.00925288607668442"))

    def test_exact_ratio_composition_with_joint_contract(self) -> None:
        ratio = solar_to_nonsolar_ratio_upper(
            Fraction(3, 1000),
            Fraction(2),
            multiplicative_factors=(Fraction(3, 2), Fraction(4, 3)),
            jointly_composable=True,
            additive_solar_upper=Fraction(1, 1000),
        )
        self.assertEqual(ratio, Fraction(7, 2000))

    def test_multiple_marginal_factors_rejected_by_default(self) -> None:
        with self.assertRaisesRegex(ValueError, "not automatically composable"):
            amplified_solar_upper(
                Fraction(1, 1000),
                multiplicative_factors=(2, 2),
            )

    def test_joint_flag_is_assertion_not_needed_for_single_factor(self) -> None:
        self.assertEqual(
            amplified_solar_upper(
                Fraction(1, 1000),
                multiplicative_factors=(Fraction(3, 2),),
            ),
            Fraction(3, 2000),
        )
        self.assertEqual(
            amplified_solar_upper(
                Fraction(1, 1000),
                multiplicative_factors=(Fraction(3, 2), Fraction(4, 3)),
                jointly_composable=True,
            ),
            Fraction(1, 500),
        )

    def test_joint_flag_must_be_bool(self) -> None:
        with self.assertRaises(TypeError):
            amplified_solar_upper(
                1,
                multiplicative_factors=(2, 2),
                jointly_composable="yes",  # type: ignore[arg-type]
            )

    def test_amplification_factor_below_one_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            amplified_solar_upper(
                1,
                multiplicative_factors=(Fraction(99, 100),),
            )

    def test_exact_boundary_pass_and_one_step_above_fail(self) -> None:
        budget = magnitude_ratio_budget_lower(Fraction(1, 100))
        at_boundary = negligibility_certificate(
            base_solar_upper=budget,
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
        )
        self.assertTrue(at_boundary.negligible)

        above = negligibility_certificate(
            base_solar_upper=budget + Fraction(1, 10**140),
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
        )
        self.assertFalse(above.negligible)

    def test_smaller_nonsolar_lower_cannot_improve_gate(self) -> None:
        common = dict(
            base_solar_upper=Fraction(1, 1000),
            magnitude_tolerance=Fraction(1, 100),
            multiplicative_factors=(Fraction(3, 2),),
        )
        strong = negligibility_certificate(non_solar_lower=1, **common)
        weak = negligibility_certificate(non_solar_lower=Fraction(1, 2), **common)
        self.assertGreater(weak.ratio_upper, strong.ratio_upper)

    def test_larger_amplification_cannot_improve_gate(self) -> None:
        low = negligibility_certificate(
            base_solar_upper=Fraction(1, 1000),
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
            multiplicative_factors=(Fraction(6, 5),),
        )
        high = negligibility_certificate(
            base_solar_upper=Fraction(1, 1000),
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
            multiplicative_factors=(Fraction(3, 2),),
        )
        self.assertGreater(high.ratio_upper, low.ratio_upper)

    def test_max_amplification_matches_gate_boundary(self) -> None:
        limit = max_multiplicative_amplification(
            base_solar_upper=Fraction(1, 1000),
            additive_solar_upper=Fraction(1, 10000),
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
        )
        cert = negligibility_certificate(
            base_solar_upper=Fraction(1, 1000),
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
            multiplicative_factors=(limit,),
            additive_solar_upper=Fraction(1, 10000),
        )
        self.assertTrue(cert.negligible)
        cert_above = negligibility_certificate(
            base_solar_upper=Fraction(1, 1000),
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
            multiplicative_factors=(limit + Fraction(1, 10**130),),
            additive_solar_upper=Fraction(1, 10000),
        )
        self.assertFalse(cert_above.negligible)

    def test_additive_tail_can_exhaust_all_amplification_headroom(self) -> None:
        budget = magnitude_ratio_budget_lower(Fraction(1, 100))
        self.assertEqual(
            max_multiplicative_amplification(
                base_solar_upper=Fraction(1, 1000),
                additive_solar_upper=budget,
                non_solar_lower=1,
                magnitude_tolerance=Fraction(1, 100),
            ),
            0,
        )

    def test_unamplified_base_failure_has_no_admissible_headroom(self) -> None:
        budget = magnitude_ratio_budget_lower(Fraction(1, 100))
        base = budget
        additive = budget / 2
        self.assertEqual(
            max_multiplicative_amplification(
                base_solar_upper=base,
                additive_solar_upper=additive,
                non_solar_lower=1,
                magnitude_tolerance=Fraction(1, 100),
            ),
            0,
        )
        cert = negligibility_certificate(
            base_solar_upper=base,
            additive_solar_upper=additive,
            non_solar_lower=1,
            magnitude_tolerance=Fraction(1, 100),
        )
        self.assertFalse(cert.negligible)

    def test_float_inputs_fail_closed(self) -> None:
        with self.assertRaises(TypeError):
            negligibility_certificate(
                base_solar_upper=0.001,
                non_solar_lower=1,
                magnitude_tolerance=Fraction(1, 100),
            )
        with self.assertRaises(TypeError):
            magnitude_ratio_budget_lower(0.01)


def _summary() -> dict[str, object]:
    tolerance = Fraction(1, 100)
    budget = magnitude_ratio_budget_lower(tolerance)
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "scope": "deterministic amplified U_s/L_ns negligibility gate",
        "magnitude_tolerance": str(tolerance),
        "ratio_budget_lower": str(budget),
        "rule": "PASS only when exact ratio_upper <= conservative ratio_budget_lower",
        "multiple_factor_policy": (
            "REJECT unless jointly_composable=True asserts a separate reviewed "
            "joint/uniform-conditional composability proof"
        ),
        "no_epsilon_substitution": True,
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
