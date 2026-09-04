#!/usr/bin/env python3
"""POST_V1/NONBLOCKING robust row-budget transport reference certificate.

This module is solver-free and result-blind. It implements exact rational
reference mathematics for a future deterministic upper bound on positive
multiple-scattering transport. It does not open protected MYSTIC results,
replace zero by epsilon, or alter Level-B.

For each current collision state i, admissible next-state masses p_ij obey

    lower_ij <= p_ij <= upper_ij,
    sum_j p_ij <= cap_i.

Given nonnegative future detector-importance y_j, the exact worst row
continuation F_i(y) is obtained by starting from every mandatory lower bound and
then greedily filling the remaining row budget into states with largest y_j.
This keeps phase-function normalization / energy-budget coupling instead of
pretending every elementwise upper bound can occur simultaneously.

If a nonnegative vector y satisfies, componentwise,

    y_i >= r_i + F_i(y),

then y is a robust Bellman supersolution: for every transition matrix compatible
with the row constraints, y bounds all remaining detector contribution from
each state. A nonnegative source vector b is therefore bounded by b^T y.

All reference arithmetic uses fractions.Fraction. Callers should supply exact
integers, Fractions, or decimal/rational strings. Binary floats are rejected so
they cannot silently weaken a future certificate.
"""

from __future__ import annotations

import argparse
import itertools
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


def _nonnegative(name: str, values: Sequence[Exact]) -> None:
    if any(v < 0 for v in values):
        raise ValueError(f"{name} must be componentwise nonnegative")


def row_worst_continuation(
    lower: Iterable[ExactLike],
    upper: Iterable[ExactLike],
    cap: ExactLike,
    importance: Iterable[ExactLike],
) -> tuple[Exact, tuple[Exact, ...]]:
    """Solve one row's robust continuation LP exactly.

    Returns (worst_objective, maximizing_allocation). Ties in importance are
    broken by original index only to make the witness deterministic; the
    objective is permutation invariant.
    """
    lo = _vec(lower)
    hi = _vec(upper)
    y = _vec(importance)
    c = as_exact(cap)
    if not (len(lo) == len(hi) == len(y)):
        raise ValueError("lower, upper, and importance must have equal length")
    if not lo:
        if c < 0:
            raise ValueError("cap must be nonnegative")
        return Fraction(0), ()
    _nonnegative("lower", lo)
    _nonnegative("upper", hi)
    _nonnegative("importance", y)
    if c < 0:
        raise ValueError("cap must be nonnegative")
    if any(a > b for a, b in zip(lo, hi)):
        raise ValueError("each lower bound must be <= its upper bound")

    mandatory = sum(lo, Fraction(0))
    if mandatory > c:
        raise ValueError("row infeasible: sum(lower) exceeds cap")

    total = min(c, sum(hi, Fraction(0)))
    remaining = total - mandatory
    allocation = list(lo)
    for j in sorted(range(len(y)), key=lambda k: (-y[k], k)):
        if remaining == 0:
            break
        room = hi[j] - lo[j]
        take = min(room, remaining)
        allocation[j] += take
        remaining -= take

    if remaining != 0:
        raise AssertionError("internal error: greedy fill left feasible row budget unused")
    objective = sum((allocation[j] * y[j] for j in range(len(y))), Fraction(0))
    return objective, tuple(allocation)


def verify_bellman_supersolution(
    lower_rows: Sequence[Sequence[ExactLike]],
    upper_rows: Sequence[Sequence[ExactLike]],
    caps: Sequence[ExactLike],
    score_upper: Sequence[ExactLike],
    importance: Sequence[ExactLike],
) -> dict[str, object]:
    """Verify y_i >= r_i + F_i(y) exactly for every row."""
    n = len(importance)
    if not (len(lower_rows) == len(upper_rows) == len(caps) == len(score_upper) == n):
        raise ValueError("row/cap/score dimensions must equal len(importance)")
    y = _vec(importance)
    r = _vec(score_upper)
    _nonnegative("importance", y)
    _nonnegative("score_upper", r)

    slacks: list[Exact] = []
    row_objectives: list[Exact] = []
    allocations: list[tuple[Exact, ...]] = []
    for i in range(n):
        if len(lower_rows[i]) != n or len(upper_rows[i]) != n:
            raise ValueError("every transition row must have len(importance) entries")
        objective, allocation = row_worst_continuation(
            lower_rows[i], upper_rows[i], caps[i], y
        )
        row_objectives.append(objective)
        allocations.append(allocation)
        slacks.append(y[i] - r[i] - objective)

    return {
        "valid": all(s >= 0 for s in slacks),
        "slacks": tuple(slacks),
        "row_objectives": tuple(row_objectives),
        "allocations": tuple(allocations),
    }


def source_upper(source: Sequence[ExactLike], importance: Sequence[ExactLike]) -> Exact:
    """Return exact b^T y for nonnegative source mass upper bounds."""
    b = _vec(source)
    y = _vec(importance)
    if len(b) != len(y):
        raise ValueError("source and importance must have equal length")
    _nonnegative("source", b)
    _nonnegative("importance", y)
    return sum((a * z for a, z in zip(b, y)), Fraction(0))


def _bruteforce_row_on_grid(
    lower: Sequence[ExactLike],
    upper: Sequence[ExactLike],
    cap: ExactLike,
    importance: Sequence[ExactLike],
    step: ExactLike,
) -> Exact:
    """Test-only exhaustive LP oracle for small rational grids."""
    lo = _vec(lower)
    hi = _vec(upper)
    y = _vec(importance)
    c = as_exact(cap)
    h = as_exact(step)
    if h <= 0:
        raise ValueError("step must be positive")
    choices: list[list[Exact]] = []
    for a, b in zip(lo, hi):
        width = b - a
        if width < 0 or width % h != 0:
            raise ValueError("grid bounds must be ordered and step-aligned")
        choices.append([a + k * h for k in range(int(width / h) + 1)])
    best: Exact | None = None
    for x in itertools.product(*choices):
        if sum(x, Fraction(0)) <= c:
            obj = sum((x[j] * y[j] for j in range(len(y))), Fraction(0))
            best = obj if best is None else max(best, obj)
    if best is None:
        raise ValueError("no feasible grid point")
    return best


def _s(value: Exact) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


class ReferenceTests(unittest.TestCase):
    def test_exact_greedy_with_mandatory_mass(self) -> None:
        objective, alloc = row_worst_continuation(
            ["0.10", "0.05", "0"],
            ["0.30", "0.40", "0.50"],
            "0.50",
            ["2", "1", "3"],
        )
        self.assertEqual(alloc, _vec(["0.10", "0.05", "0.35"]))
        self.assertEqual(objective, Fraction("1.30"))

    def test_cap_above_sum_upper(self) -> None:
        objective, alloc = row_worst_continuation(
            [0, 0], ["0.2", "0.3"], "0.9", [3, 1]
        )
        self.assertEqual(alloc, _vec(["0.2", "0.3"]))
        self.assertEqual(objective, Fraction("0.9"))

    def test_infeasible_lower_sum_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum\\(lower\\) exceeds cap"):
            row_worst_continuation(["0.3", "0.3"], ["0.4", "0.4"], "0.5", [1, 2])

    def test_float_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "floats are forbidden"):
            row_worst_continuation([0.0], ["1"], "1", ["1"])

    def test_tie_witness_is_deterministic(self) -> None:
        objective, alloc = row_worst_continuation([0, 0], [1, 1], 1, [2, 2])
        self.assertEqual(objective, 2)
        self.assertEqual(alloc, (Fraction(1), Fraction(0)))

    def test_permutation_invariant_objective(self) -> None:
        args = (["0.1", "0", "0.2"], ["0.4", "0.5", "0.4"], "0.7", [1, 4, 2])
        objective, _ = row_worst_continuation(*args)
        p = [2, 0, 1]
        objective_p, _ = row_worst_continuation(
            [args[0][j] for j in p],
            [args[1][j] for j in p],
            args[2],
            [args[3][j] for j in p],
        )
        self.assertEqual(objective, objective_p)

    def test_greedy_matches_bruteforce_grid_oracle(self) -> None:
        lower = ["0", "0.25", "0"]
        upper = ["0.5", "0.5", "0.75"]
        cap = "1.0"
        importance = ["3", "1", "2"]
        greedy, _ = row_worst_continuation(lower, upper, cap, importance)
        brute = _bruteforce_row_on_grid(lower, upper, cap, importance, "0.25")
        self.assertEqual(greedy, brute)

    def test_bellman_supersolution_and_source_bound(self) -> None:
        lower = [[0, 0], [0, 0]]
        upper = [["0.2", "0.1"], [0, "0.25"]]
        caps = ["0.25", "0.25"]
        score = [1, "0.5"]
        y = [2, 1]
        result = verify_bellman_supersolution(lower, upper, caps, score, y)
        self.assertTrue(result["valid"])
        self.assertEqual(result["slacks"], _vec(["0.55", "0.25"]))
        self.assertEqual(source_upper(["0.1", "0.2"], y), Fraction("0.4"))

    def test_bellman_violation_fails(self) -> None:
        result = verify_bellman_supersolution(
            [[0]], [["0.9"]], ["0.9"], ["0.2"], [1]
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["slacks"], (Fraction("-0.1"),))

    def test_tighter_row_cap_cannot_raise_worst_objective(self) -> None:
        loose, _ = row_worst_continuation([0, 0], [1, 1], "1.0", [3, 1])
        tight, _ = row_worst_continuation([0, 0], [1, 1], "0.4", [3, 1])
        self.assertLessEqual(tight, loose)


def _summary() -> dict[str, object]:
    result = verify_bellman_supersolution(
        [[0, 0], [0, 0]],
        [["0.2", "0.1"], [0, "0.25"]],
        ["0.25", "0.25"],
        [1, "0.5"],
        [2, 1],
    )
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "certificate_valid": result["valid"],
        "slacks": [_s(v) for v in result["slacks"]],
        "source_upper_example": _s(source_upper(["0.1", "0.2"], [2, 1])),
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
