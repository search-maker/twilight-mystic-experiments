#!/usr/bin/env python3
"""POST_V1/NONBLOCKING independent-block exact-zero reference certificate.

This module is solver-free and result-blind. It never turns an observed zero
into a positive epsilon and it does not alter Level-B.

Statistical scope
-----------------
The N-photon formula q <= 1 - alpha**(1/N) needs a common hit probability q
and independent trials (or an explicitly justified equivalent model). Under
arbitrary dependence there is no N-fold gain: perfectly dependent indicators
can make P(all zero)=1-q for every N.

For preregistered independent blocks, this module handles a more general and
useful case. Block b contains n_b independent equal-hazard trials with hit
probability q_b and a finite nonnegative per-score envelope B_b. If every
trial in every block is exactly zero, then the zero-only 1-alpha confidence
set is

    product_b (1-q_b)**n_b >= alpha.

Within that set, the worst-case mean score is obtained exactly by a water-fill
solution

    q_b* = max(0, 1 - lambda/B_b),

where lambda is the unique level satisfying

    product_b min(1, lambda/B_b)**n_b = alpha

for positive B_b. This is tighter than first relaxing the product constraint
into a single sum-q budget when envelopes differ.

The result remains conditional on the stated independence/common-hazard model
and on envelopes frozen independently of the observed scores. It is not a
physical-zero certificate and is not a substitute for the deterministic
transport tail/Bellman certificate.
"""

from __future__ import annotations

import argparse
import json
import math
import unittest
from dataclasses import dataclass
from typing import Iterable

_MAX_CERTIFIABLE_INTEGER_COUNT = (1 << 53) - 1


@dataclass(frozen=True)
class ZeroBlock:
    count: int
    envelope: float


def _require_probability(name: str, value: float) -> None:
    if not (math.isfinite(value) and 0.0 < value < 1.0):
        raise ValueError(f"{name} must be finite and strictly between 0 and 1")


def _normalize_blocks(blocks: Iterable[ZeroBlock]) -> tuple[ZeroBlock, ...]:
    normalized: list[ZeroBlock] = []
    total = 0
    for block in blocks:
        if not isinstance(block, ZeroBlock):
            raise TypeError("blocks must contain ZeroBlock instances")
        if not isinstance(block.count, int) or isinstance(block.count, bool) or block.count <= 0:
            raise ValueError("block count must be a positive integer")
        if not (math.isfinite(block.envelope) and block.envelope >= 0.0):
            raise ValueError("block envelope must be finite and >= 0")
        total += block.count
        if total > _MAX_CERTIFIABLE_INTEGER_COUNT:
            raise ValueError("total trial count exceeds binary64 exact-integer audit range")
        normalized.append(block)
    if not normalized:
        raise ValueError("at least one block is required")
    return tuple(normalized)


def common_q_independent_upper(alpha: float, n: int) -> float:
    """Common-q upper confidence bound after n independent exact zeros."""
    _require_probability("alpha", alpha)
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError("n must be a positive integer")
    return -math.expm1(math.log(alpha) / n)


def common_q_arbitrary_dependence_upper(alpha: float) -> float:
    """Worst-case common-q bound with arbitrary dependence: there is no N gain."""
    _require_probability("alpha", alpha)
    return 1.0 - alpha


def independent_block_zero_mean_upper(
    alpha: float,
    blocks: Iterable[ZeroBlock],
) -> tuple[float, float, tuple[float, ...]]:
    """Exact zero-only mean-score upper bound for independent equal-hazard blocks.

    Returns ``(mean_upper, lambda_level, q_star_in_input_order)``.

    The confidence inversion is exact for the stated block model. Numerical
    evaluation is performed in log space with binary64; trial counts are
    therefore restricted to the exact-integer range used elsewhere by the
    post-V1 reference code.
    """
    _require_probability("alpha", alpha)
    normalized = _normalize_blocks(blocks)
    total_count = sum(block.count for block in normalized)

    positive = [
        (idx, block)
        for idx, block in enumerate(normalized)
        if block.envelope > 0.0
    ]
    if not positive:
        return 0.0, 0.0, tuple(0.0 for _ in normalized)

    # Highest envelope enters the active set first. For a proposed active set A,
    # the product constraint gives
    #   log(lambda) = (log(alpha) + sum_A n_b log(B_b)) / sum_A n_b.
    # The first set for which lambda >= next B is the KKT-consistent active set.
    positive.sort(key=lambda item: item[1].envelope, reverse=True)
    weighted_log_b = 0.0
    active_count = 0
    log_alpha = math.log(alpha)
    log_lambda = float("nan")

    for rank, (_idx, block) in enumerate(positive):
        active_count += block.count
        weighted_log_b += block.count * math.log(block.envelope)
        log_lambda = (log_alpha + weighted_log_b) / active_count
        lambda_level = math.exp(log_lambda)
        next_envelope = (
            positive[rank + 1][1].envelope
            if rank + 1 < len(positive)
            else 0.0
        )
        # Equality is harmless: the next block would receive q*=0 either way.
        if lambda_level >= next_envelope:
            break
    else:  # pragma: no cover - the last rank always terminates.
        raise AssertionError("active-set scan failed to terminate")

    q_star = [0.0] * len(normalized)
    weighted_mean_numerator = 0.0
    log_zero_probability = 0.0
    for idx, block in enumerate(normalized):
        if block.envelope <= 0.0 or block.envelope <= lambda_level:
            q = 0.0
            log_survival = 0.0
        else:
            # Stable when lambda/B is close to one.
            log_ratio = log_lambda - math.log(block.envelope)
            q = -math.expm1(log_ratio)
            q = min(1.0, max(0.0, q))
            log_survival = log_ratio
        q_star[idx] = q
        weighted_mean_numerator += block.count * block.envelope * q
        log_zero_probability += block.count * log_survival

    # Fail closed if accumulated binary64 error does not reproduce the boundary.
    if not math.isclose(log_zero_probability, log_alpha, rel_tol=0.0, abs_tol=5e-13):
        raise ArithmeticError(
            "block water-fill failed to reproduce the alpha confidence boundary"
        )

    return (
        weighted_mean_numerator / total_count,
        lambda_level,
        tuple(q_star),
    )


def relaxed_sum_q_envelope_upper(
    alpha: float,
    blocks: Iterable[ZeroBlock],
) -> float:
    """Older AM-GM + linear-budget relaxation, retained only as a QA comparator."""
    _require_probability("alpha", alpha)
    normalized = _normalize_blocks(blocks)
    total = sum(block.count for block in normalized)
    q_bar = common_q_independent_upper(alpha, total)
    budget = total * q_bar

    # Each individual trial may receive at most q=1 under the relaxation. Fill
    # highest envelopes first. This intentionally discards the exact product
    # structure and therefore cannot beat the exact block result.
    remaining = budget
    numerator = 0.0
    for block in sorted(normalized, key=lambda b: b.envelope, reverse=True):
        if remaining <= 0.0:
            break
        allocated = min(float(block.count), remaining)
        numerator += allocated * block.envelope
        remaining -= allocated
    return numerator / total


class ReferenceTests(unittest.TestCase):
    def test_equal_envelope_recovers_pooled_common_q(self) -> None:
        alpha = 0.05
        blocks = (ZeroBlock(5, 7.0), ZeroBlock(8, 7.0), ZeroBlock(11, 7.0))
        upper, _level, q = independent_block_zero_mean_upper(alpha, blocks)
        expected_q = common_q_independent_upper(alpha, 24)
        self.assertTrue(all(math.isclose(v, expected_q, rel_tol=2e-15) for v in q))
        self.assertTrue(math.isclose(upper, 7.0 * expected_q, rel_tol=2e-15))

    def test_heterogeneous_envelopes_strictly_tighten_relaxation(self) -> None:
        alpha = 0.05
        blocks = (ZeroBlock(5, 1.0), ZeroBlock(5, 10.0))
        upper, level, q = independent_block_zero_mean_upper(alpha, blocks)
        relaxed = relaxed_sum_q_envelope_upper(alpha, blocks)
        self.assertAlmostEqual(level, 5.492802716530589, places=14)
        self.assertEqual(q[0], 0.0)
        self.assertAlmostEqual(q[1], 0.4507197283469411, places=14)
        self.assertAlmostEqual(upper, 2.2535986417347056, places=14)
        self.assertLess(upper, relaxed)

    def test_product_boundary_is_alpha(self) -> None:
        alpha = 0.01
        blocks = (ZeroBlock(2, 1.0), ZeroBlock(3, 2.0), ZeroBlock(5, 5.0))
        _upper, _level, q = independent_block_zero_mean_upper(alpha, blocks)
        log_p0 = sum(
            block.count * math.log1p(-qb)
            for block, qb in zip(blocks, q)
        )
        self.assertAlmostEqual(log_p0, math.log(alpha), places=13)

    def test_permutation_invariant(self) -> None:
        alpha = 0.05
        a = (ZeroBlock(2, 1.0), ZeroBlock(3, 4.0), ZeroBlock(7, 2.0))
        b = (a[2], a[0], a[1])
        ua, la, _ = independent_block_zero_mean_upper(alpha, a)
        ub, lb, _ = independent_block_zero_mean_upper(alpha, b)
        self.assertAlmostEqual(ua, ub, places=15)
        self.assertAlmostEqual(la, lb, places=15)

    def test_zero_envelopes_do_not_consume_confidence_budget(self) -> None:
        alpha = 0.05
        upper, level, q = independent_block_zero_mean_upper(
            alpha, (ZeroBlock(1000, 0.0), ZeroBlock(10, 3.0))
        )
        expected_q = common_q_independent_upper(alpha, 10)
        self.assertEqual(q[0], 0.0)
        self.assertAlmostEqual(q[1], expected_q, places=15)
        self.assertAlmostEqual(upper, 10 * 3.0 * expected_q / 1010, places=15)
        self.assertAlmostEqual(level, 3.0 * (alpha ** (1.0 / 10.0)), places=14)

    def test_perfect_dependence_has_no_n_gain(self) -> None:
        alpha = 0.05
        self.assertEqual(common_q_arbitrary_dependence_upper(alpha), 0.95)
        self.assertLess(common_q_independent_upper(alpha, 200_000_000), 2e-8)
        # Construction: X_i=B*Z for every i, Z~Bernoulli(q). Then P(all zero)=1-q.
        # At q=1-alpha, the all-zero event still has probability alpha for any N.
        self.assertTrue(
            math.isclose(
                1.0 - common_q_arbitrary_dependence_upper(alpha),
                alpha,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
        )

    def test_small_grid_oracle(self) -> None:
        alpha = 0.05
        blocks = (ZeroBlock(2, 1.0), ZeroBlock(3, 4.0))
        exact, _level, _q = independent_block_zero_mean_upper(alpha, blocks)
        best = 0.0
        # Coarse independent oracle: any feasible grid point must not exceed the
        # analytic optimum. This catches active-set/sign mistakes without using
        # the water-fill implementation itself.
        steps = 300
        for i in range(steps + 1):
            q1 = i / steps
            if q1 == 1.0:
                continue
            for j in range(steps + 1):
                q2 = j / steps
                if q2 == 1.0:
                    continue
                log_p0 = 2 * math.log1p(-q1) + 3 * math.log1p(-q2)
                if log_p0 + 1e-15 >= math.log(alpha):
                    mean = (2 * 1.0 * q1 + 3 * 4.0 * q2) / 5
                    best = max(best, mean)
        self.assertLessEqual(best, exact + 1e-12)
        self.assertLess(exact - best, 0.02)

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            independent_block_zero_mean_upper(0.05, ())
        with self.assertRaises(ValueError):
            independent_block_zero_mean_upper(0.05, (ZeroBlock(0, 1.0),))
        with self.assertRaises(ValueError):
            independent_block_zero_mean_upper(0.05, (ZeroBlock(1, float("inf")),))
        with self.assertRaises(ValueError):
            common_q_independent_upper(0.05, 0)


def _summary() -> dict[str, object]:
    demo = (ZeroBlock(5, 1.0), ZeroBlock(5, 10.0))
    upper, level, q = independent_block_zero_mean_upper(0.05, demo)
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "assumption": "independent equal-hazard trials within preregistered blocks",
        "heterogeneous_demo_mean_upper": upper,
        "heterogeneous_demo_lambda": level,
        "heterogeneous_demo_q_star": list(q),
        "heterogeneous_demo_relaxed_upper": relaxed_sum_q_envelope_upper(0.05, demo),
        "arbitrary_dependence_common_q_95_upper": common_q_arbitrary_dependence_upper(0.05),
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
