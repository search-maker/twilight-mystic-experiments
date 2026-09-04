#!/usr/bin/env python3
"""POST_V1/NONBLOCKING exact dual Bellman certificate for robust transport.

This reference is solver-free and result-blind.  It verifies, using exact
``fractions.Fraction`` arithmetic, a linear-program dual witness for the same
row-budget positive-transport uncertainty set as
``row_budget_transport_reference.py``.  A numerical LP solver may eventually
*propose* a candidate witness, but this module never trusts floating-point
solver status or tolerances: every scientific certificate inequality is
rechecked exactly here.

For row i, admissible transition masses obey

    lower_ij <= p_ij <= upper_ij,
    sum_j p_ij <= cap_i.

Let d_ij = upper_ij-lower_ij and
R_i = min(cap_i, sum_j upper_ij) - sum_j lower_ij.  For nonnegative detector
importance y, any lambda_i >= 0 and nu_ij >= 0 satisfying

    lambda_i + nu_ij >= y_j

give, by weak LP duality,

    F_i(y) <= lower_i.y + R_i*lambda_i + sum_j d_ij*nu_ij.

Therefore the entirely linear exact inequalities

    y_i >= r_i + lower_i.y + R_i*lambda_i + sum_j d_ij*nu_ij

certify y as a robust Bellman supersolution.  For nonnegative source upper
vector b, the unresolved detector contribution is then at most b.y.

No protected MYSTIC result is opened, no zero is replaced by epsilon, and no
Level-B behavior is changed.
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


def _row_geometry(
    lower: Sequence[ExactLike], upper: Sequence[ExactLike], cap: ExactLike
) -> tuple[tuple[Exact, ...], tuple[Exact, ...], tuple[Exact, ...], Exact]:
    lo = _vec(lower)
    hi = _vec(upper)
    c = as_exact(cap)
    if len(lo) != len(hi):
        raise ValueError("lower and upper must have equal length")
    if c < 0 or any(v < 0 for v in lo) or any(v < 0 for v in hi):
        raise ValueError("row bounds and cap must be nonnegative")
    if any(a > b for a, b in zip(lo, hi)):
        raise ValueError("each lower bound must be <= its upper bound")
    mandatory = sum(lo, Fraction(0))
    if mandatory > c:
        raise ValueError("row infeasible: sum(lower) exceeds cap")
    total = min(c, sum(hi, Fraction(0)))
    widths = tuple(b - a for a, b in zip(lo, hi))
    return lo, hi, widths, total - mandatory


def row_dual_bound(
    lower: Sequence[ExactLike],
    upper: Sequence[ExactLike],
    cap: ExactLike,
    importance: Sequence[ExactLike],
    dual_lambda: ExactLike,
    dual_nu: Sequence[ExactLike],
) -> dict[str, object]:
    """Verify one supplied row-dual witness and return its exact upper bound."""
    y = _vec(importance)
    lam = as_exact(dual_lambda)
    nu = _vec(dual_nu)
    lo, _hi, widths, residual = _row_geometry(lower, upper, cap)
    if not (len(y) == len(lo) == len(nu)):
        raise ValueError("row, importance, and dual_nu dimensions must agree")
    if lam < 0 or any(v < 0 for v in y) or any(v < 0 for v in nu):
        raise ValueError("importance and dual variables must be nonnegative")

    dual_slacks = tuple(lam + n - score for n, score in zip(nu, y))
    base = sum((a * score for a, score in zip(lo, y)), Fraction(0))
    upper_value = base + lam * residual + sum(
        (width * n for width, n in zip(widths, nu)), Fraction(0)
    )
    return {
        "valid": all(s >= 0 for s in dual_slacks),
        "upper": upper_value,
        "dual_slacks": dual_slacks,
        "residual_budget": residual,
    }


def verify_dual_bellman_supersolution(
    lower_rows: Sequence[Sequence[ExactLike]],
    upper_rows: Sequence[Sequence[ExactLike]],
    caps: Sequence[ExactLike],
    score_upper: Sequence[ExactLike],
    importance: Sequence[ExactLike],
    dual_lambdas: Sequence[ExactLike],
    dual_nus: Sequence[Sequence[ExactLike]],
    source_upper: Sequence[ExactLike] | None = None,
) -> dict[str, object]:
    """Verify a full exact rational dual Bellman certificate."""
    n = len(importance)
    if not all(
        len(values) == n
        for values in (
            lower_rows,
            upper_rows,
            caps,
            score_upper,
            dual_lambdas,
            dual_nus,
        )
    ):
        raise ValueError("top-level dimensions must equal len(importance)")

    y = _vec(importance)
    r = _vec(score_upper)
    lambdas = _vec(dual_lambdas)
    if any(v < 0 for v in y) or any(v < 0 for v in r) or any(v < 0 for v in lambdas):
        raise ValueError("importance, score_upper, and dual_lambdas must be nonnegative")

    rows: list[dict[str, object]] = []
    bellman_slacks: list[Exact] = []
    for i in range(n):
        if len(lower_rows[i]) != n or len(upper_rows[i]) != n or len(dual_nus[i]) != n:
            raise ValueError("every transition/dual row must have len(importance) entries")
        report = row_dual_bound(
            lower_rows[i],
            upper_rows[i],
            caps[i],
            y,
            lambdas[i],
            dual_nus[i],
        )
        slack = y[i] - r[i] - report["upper"]
        rows.append({**report, "bellman_slack": slack})
        bellman_slacks.append(slack)

    detector_upper: Exact | None = None
    if source_upper is not None:
        source = _vec(source_upper)
        if len(source) != n or any(v < 0 for v in source):
            raise ValueError("source_upper must be nonnegative with len(importance) entries")
        detector_upper = sum((a * z for a, z in zip(source, y)), Fraction(0))

    return {
        "valid": all(row["valid"] and row["bellman_slack"] >= 0 for row in rows),
        "rows": tuple(rows),
        "bellman_slacks": tuple(bellman_slacks),
        "detector_upper": detector_upper,
    }


def _s(value: Exact) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


class DualBellmanTests(unittest.TestCase):
    def test_exact_row_dual_optimum_fixture(self) -> None:
        # Greedy primal optimum is 1.30; lambda=3, nu=0 is an exact dual witness.
        result = row_dual_bound(
            ["0.10", "0.05", "0"],
            ["0.30", "0.40", "0.50"],
            "0.50",
            [2, 1, 3],
            3,
            [0, 0, 0],
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["upper"], Fraction("1.30"))

    def test_interior_dual_threshold_fixture(self) -> None:
        result = row_dual_bound(
            [0, 0, 0], ["0.2", "0.4", "0.5"], "0.5", [4, 3, 1], 3, [1, 0, 0]
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["upper"], Fraction("1.7"))

    def test_invalid_dual_constraint_fails(self) -> None:
        result = row_dual_bound([0], [1], 1, [2], 1, [0])
        self.assertFalse(result["valid"])
        self.assertEqual(result["dual_slacks"], (Fraction(-1),))

    def test_global_dual_bellman_fixture(self) -> None:
        result = verify_dual_bellman_supersolution(
            [[0, 0], [0, 0]],
            [["0.2", "0.1"], [0, "0.25"]],
            ["0.25", "0.25"],
            [1, "0.5"],
            [2, 1],
            [1, 1],
            [[1, 0], [1, 0]],
            source_upper=["0.1", "0.2"],
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["bellman_slacks"], (Fraction("0.55"), Fraction("0.25")))
        self.assertEqual(result["detector_upper"], Fraction("0.4"))

    def test_bad_bellman_witness_fails(self) -> None:
        result = verify_dual_bellman_supersolution(
            [[0]], [["0.9"]], ["0.9"], ["0.2"], [1], [1], [[0]]
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["bellman_slacks"], (Fraction("-0.1"),))

    def test_cap_above_sum_upper(self) -> None:
        result = row_dual_bound([0, 0], ["0.2", "0.3"], "0.9", [3, 1], 0, [3, 1])
        self.assertTrue(result["valid"])
        self.assertEqual(result["upper"], Fraction("0.9"))
        self.assertEqual(result["residual_budget"], Fraction("0.5"))

    def test_infeasible_row_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum\\(lower\\) exceeds cap"):
            row_dual_bound(["0.4", "0.3"], ["0.5", "0.5"], "0.6", [1, 2], 2, [0, 0])

    def test_float_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "floats are forbidden"):
            row_dual_bound([0], [1], 1, [1.0], 1, [0])


def _summary() -> dict[str, object]:
    result = verify_dual_bellman_supersolution(
        [[0, 0], [0, 0]],
        [["0.2", "0.1"], [0, "0.25"]],
        ["0.25", "0.25"],
        [1, "0.5"],
        [2, 1],
        [1, 1],
        [[1, 0], [1, 0]],
        source_upper=["0.1", "0.2"],
    )
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "certificate_valid": result["valid"],
        "bellman_slacks": [_s(v) for v in result["bellman_slacks"]],
        "detector_upper": _s(result["detector_upper"]),
        "arithmetic": "exact Fraction; binary floats forbidden",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(DualBellmanTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1
    print(json.dumps(_summary(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
