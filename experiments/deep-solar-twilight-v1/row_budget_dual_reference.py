#!/usr/bin/env python3
"""POST_V1/NONBLOCKING exact dual oracle for robust row-budget transport.

This module is solver-free and result-blind.  It independently certifies the
row linear program implemented by ``row_budget_transport_reference.py``.
No protected MYSTIC result is opened, no zero is replaced by epsilon, and no
Level-B behavior is changed.

For one current collision state, let

    lower_j <= p_j <= upper_j,
    sum_j p_j <= cap,
    importance_j >= 0.

After mandatory lower mass is removed, write ``d_j = upper_j-lower_j`` and
``R = min(cap, sum upper)-sum lower``.  The residual primal is

    max sum_j importance_j x_j
    s.t. 0 <= x_j <= d_j, sum_j x_j <= R.

For every lambda >= 0, weak duality gives the exact analytic upper bound

    lambda*R + sum_j d_j * max(importance_j-lambda, 0).

The minimum is attained at lambda in {0} union {importance_j}.  Therefore the
finite enumeration below is an exact dual optimum in rational arithmetic.  Its
agreement with the independently implemented greedy primal witness gives a
primal/dual audit of the row certificate without a numerical LP solver.
"""

from __future__ import annotations

import argparse
import json
import unittest
from fractions import Fraction

from row_budget_transport_reference import as_exact, row_worst_continuation

Exact = Fraction
ExactLike = int | str | Fraction


def _vec(values):
    return tuple(as_exact(v) for v in values)


def row_dual_upper(lower, upper, cap, importance) -> tuple[Exact, Exact]:
    """Return (exact dual optimum, minimizing lambda) for one row.

    Binary floats are rejected by ``as_exact``.  Infeasible rows fail closed.
    Ties between dual minimizers are resolved by the smallest lambda only to
    make the witness deterministic.
    """
    lo = _vec(lower)
    hi = _vec(upper)
    y = _vec(importance)
    c = as_exact(cap)

    if not (len(lo) == len(hi) == len(y)):
        raise ValueError("lower, upper, and importance must have equal length")
    if any(v < 0 for v in lo):
        raise ValueError("lower must be componentwise nonnegative")
    if any(v < 0 for v in hi):
        raise ValueError("upper must be componentwise nonnegative")
    if any(v < 0 for v in y):
        raise ValueError("importance must be componentwise nonnegative")
    if c < 0:
        raise ValueError("cap must be nonnegative")
    if any(a > b for a, b in zip(lo, hi)):
        raise ValueError("each lower bound must be <= its upper bound")

    mandatory = sum(lo, Fraction(0))
    if mandatory > c:
        raise ValueError("row infeasible: sum(lower) exceeds cap")

    total = min(c, sum(hi, Fraction(0)))
    residual = total - mandatory
    base = sum((a * z for a, z in zip(lo, y)), Fraction(0))
    widths = tuple(b - a for a, b in zip(lo, hi))

    candidates = sorted(set((Fraction(0),) + y))
    best_value: Exact | None = None
    best_lambda: Exact | None = None
    for lam in candidates:
        value = base + lam * residual + sum(
            (width * max(score - lam, Fraction(0)) for width, score in zip(widths, y)),
            Fraction(0),
        )
        if best_value is None or value < best_value:
            best_value = value
            best_lambda = lam

    if best_value is None or best_lambda is None:
        # Empty rows have zero objective and a canonical zero dual witness.
        return Fraction(0), Fraction(0)
    return best_value, best_lambda


def certify_row_primal_dual(lower, upper, cap, importance) -> dict[str, object]:
    """Cross-check independent exact primal and dual row implementations."""
    primal, allocation = row_worst_continuation(lower, upper, cap, importance)
    dual, lam = row_dual_upper(lower, upper, cap, importance)
    return {
        "valid": primal == dual,
        "primal": primal,
        "dual": dual,
        "lambda": lam,
        "allocation": allocation,
    }


def _s(value: Exact) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


class DualReferenceTests(unittest.TestCase):
    def test_mandatory_mass_fixture_matches_primal(self) -> None:
        result = certify_row_primal_dual(
            ["0.10", "0.05", "0"],
            ["0.30", "0.40", "0.50"],
            "0.50",
            ["2", "1", "3"],
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["primal"], Fraction("1.30"))
        self.assertEqual(result["dual"], Fraction("1.30"))
        self.assertEqual(result["lambda"], Fraction(3))

    def test_dual_threshold_inside_ranked_scores(self) -> None:
        result = certify_row_primal_dual(
            [0, 0, 0], ["0.2", "0.4", "0.5"], "0.5", [4, 3, 1]
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["primal"], Fraction("1.7"))
        self.assertEqual(result["lambda"], Fraction(3))

    def test_cap_above_sum_upper_matches_primal(self) -> None:
        result = certify_row_primal_dual([0, 0], ["0.2", "0.3"], "0.9", [3, 1])
        self.assertTrue(result["valid"])
        self.assertEqual(result["dual"], Fraction("0.9"))
        self.assertEqual(result["lambda"], Fraction(0))

    def test_zero_residual_budget(self) -> None:
        result = certify_row_primal_dual(
            ["0.2", "0.3"], ["0.8", "0.9"], "0.5", [7, 2]
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["primal"], Fraction(2))

    def test_zero_importance(self) -> None:
        result = certify_row_primal_dual([0, 0], [1, 1], 1, [0, 0])
        self.assertTrue(result["valid"])
        self.assertEqual(result["dual"], Fraction(0))
        self.assertEqual(result["lambda"], Fraction(0))

    def test_infeasible_row_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum\\(lower\\) exceeds cap"):
            row_dual_upper(["0.4", "0.3"], ["0.5", "0.5"], "0.6", [1, 2])

    def test_float_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "floats are forbidden"):
            row_dual_upper([0], [1], "1", [1.0])

    def test_deterministic_small_grid_family(self) -> None:
        # A bounded exact family probes different active-capacity orderings and
        # mandatory-mass patterns without randomness or a numerical solver.
        fixtures = [
            ([0, 0], ["1/4", "3/4"], "1/2", [5, 1]),
            (["1/4", 0], ["1/2", "3/4"], "3/4", [1, 5]),
            ([0, "1/4", 0], ["1/2", "1/2", "1/2"], "1", [3, 2, 4]),
            (["1/8", "1/8", "1/8"], ["3/8", "5/8", "7/8"], "7/8", [0, 2, 1]),
            ([0, 0, 0, 0], ["1/4"] * 4, "3/4", [4, 3, 2, 1]),
        ]
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                result = certify_row_primal_dual(*fixture)
                self.assertTrue(result["valid"])

    def test_dual_is_weak_upper_bound_for_explicit_feasible_allocations(self) -> None:
        lower = _vec(["0.1", "0.2", "0"])
        upper = _vec(["0.5", "0.5", "0.4"])
        cap = Fraction("0.8")
        importance = _vec([4, 1, 3])
        dual, _ = row_dual_upper(lower, upper, cap, importance)
        candidates = [
            _vec(["0.1", "0.2", "0"]),
            _vec(["0.5", "0.2", "0.1"]),
            _vec(["0.2", "0.2", "0.4"]),
            _vec(["0.3", "0.3", "0.2"]),
        ]
        for allocation in candidates:
            self.assertLessEqual(sum(allocation, Fraction(0)), cap)
            self.assertTrue(all(a <= x <= b for a, x, b in zip(lower, allocation, upper)))
            objective = sum((x * y for x, y in zip(allocation, importance)), Fraction(0))
            self.assertLessEqual(objective, dual)


def _summary() -> dict[str, object]:
    result = certify_row_primal_dual(
        ["0.10", "0.05", "0"],
        ["0.30", "0.40", "0.50"],
        "0.50",
        ["2", "1", "3"],
    )
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "primal_dual_equal": result["valid"],
        "objective": _s(result["primal"]),
        "dual_lambda": _s(result["lambda"]),
        "arithmetic": "exact Fraction; binary floats forbidden",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(DualReferenceTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    print(json.dumps(_summary(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
