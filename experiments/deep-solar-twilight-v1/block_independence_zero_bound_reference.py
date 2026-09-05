#!/usr/bin/env python3
"""POST_V1/NONBLOCKING block-independence-only exact-zero reference.

This module isolates a weaker stochastic assumption than photon-level IID.
Blocks are independent of one another, but dependence inside each block may be
arbitrary. No observed zero is replaced by epsilon, no solver is run, and no
Level-B or protected scientific result is touched.

Model
-----
Block b contains n_b nonnegative scores X_bi with a common marginal hit
probability q_b = P(X_bi > 0) and a frozen finite envelope
0 <= X_bi <= B_b. The joint law inside a block is otherwise unrestricted.
The block vectors are mutually independent.

If A_b is the event that every score in block b is exactly zero, then

    A_b subseteq {X_b1 = 0}, so P(A_b) <= 1 - q_b.

This inequality is sharp: perfect dependence inside the block
X_b1=...=X_bn realizes equality. Therefore

    P(all blocks all-zero) <= product_b (1-q_b).

Consequently an all-zero observation gives the conservative, least-favourable
1-alpha confidence set

    product_b (1-q_b) >= alpha.

The worst-case average mean score inside this set maximizes

    sum_b n_b B_b q_b / sum_b n_b.

Writing W_b=n_b B_b, the exact KKT water-fill is

    q_b* = max(0, 1 - lambda/W_b),

with lambda chosen so

    product_b min(1, lambda/W_b) = alpha

for positive W_b. This shows the hierarchy cleanly: with only one independent
block there is no photon-count gain; with K identical independent blocks the
common-q bound is 1-alpha**(1/K); only a separately justified photon-level
independence model earns an N-photon exponent.

The result is still a statistical numerical-uncertainty bound, not a physical
zero certificate, and it does not replace the deterministic transport/Bellman
negligibility certificate.
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
class DependenceBlock:
    count: int
    envelope: float


def _require_probability(name: str, value: float) -> None:
    if not (math.isfinite(value) and 0.0 < value < 1.0):
        raise ValueError(f"{name} must be finite and strictly between 0 and 1")


def _normalize_blocks(blocks: Iterable[DependenceBlock]) -> tuple[DependenceBlock, ...]:
    normalized: list[DependenceBlock] = []
    total = 0
    for block in blocks:
        if not isinstance(block, DependenceBlock):
            raise TypeError("blocks must contain DependenceBlock instances")
        if not isinstance(block.count, int) or isinstance(block.count, bool) or block.count <= 0:
            raise ValueError("block count must be a positive integer")
        if not (math.isfinite(block.envelope) and block.envelope >= 0.0):
            raise ValueError("block envelope must be finite and >= 0")
        total += block.count
        if total > _MAX_CERTIFIABLE_INTEGER_COUNT:
            raise ValueError("total trial count exceeds binary64 exact-integer audit range")
        weight = block.count * block.envelope
        if not math.isfinite(weight):
            raise ValueError("block count times envelope must remain finite")
        normalized.append(block)
    if not normalized:
        raise ValueError("at least one block is required")
    return tuple(normalized)


def common_q_independent_blocks_upper(alpha: float, block_count: int) -> float:
    """Common-q bound with independent blocks and arbitrary within-block dependence."""
    _require_probability("alpha", alpha)
    if not isinstance(block_count, int) or isinstance(block_count, bool) or block_count <= 0:
        raise ValueError("block_count must be a positive integer")
    return -math.expm1(math.log(alpha) / block_count)


def least_favourable_block_mean_upper(
    alpha: float,
    blocks: Iterable[DependenceBlock],
) -> tuple[float, float, tuple[float, ...]]:
    """Worst mean bound using independence only between blocks.

    Returns ``(mean_upper, lambda_level, q_star_in_input_order)``. Dependence
    inside a block is unrestricted; the bound uses the sharp least-favourable
    block all-zero probability 1-q_b.
    """
    _require_probability("alpha", alpha)
    normalized = _normalize_blocks(blocks)
    total_count = sum(block.count for block in normalized)

    weighted = [
        (idx, block.count * block.envelope)
        for idx, block in enumerate(normalized)
        if block.envelope > 0.0
    ]
    if not weighted:
        return 0.0, 0.0, tuple(0.0 for _ in normalized)

    weighted.sort(key=lambda item: item[1], reverse=True)
    log_alpha = math.log(alpha)
    sum_log_weight = 0.0
    active_blocks = 0
    log_lambda = float("nan")
    lambda_level = float("nan")

    for rank, (_idx, weight) in enumerate(weighted):
        active_blocks += 1
        sum_log_weight += math.log(weight)
        log_lambda = (log_alpha + sum_log_weight) / active_blocks
        lambda_level = math.exp(log_lambda)
        next_weight = weighted[rank + 1][1] if rank + 1 < len(weighted) else 0.0
        if lambda_level >= next_weight:
            break
    else:  # pragma: no cover - final active set always terminates.
        raise AssertionError("active-set scan failed to terminate")

    q_star = [0.0] * len(normalized)
    numerator = 0.0
    log_least_favourable_zero_probability = 0.0
    for idx, block in enumerate(normalized):
        weight = block.count * block.envelope
        if weight <= 0.0 or weight <= lambda_level:
            q = 0.0
            log_survival = 0.0
        else:
            log_ratio = log_lambda - math.log(weight)
            q = -math.expm1(log_ratio)
            q = min(1.0, max(0.0, q))
            log_survival = log_ratio
        q_star[idx] = q
        numerator += weight * q
        log_least_favourable_zero_probability += log_survival

    if not math.isclose(
        log_least_favourable_zero_probability,
        log_alpha,
        rel_tol=0.0,
        abs_tol=5e-13,
    ):
        raise ArithmeticError("block water-fill failed to reproduce alpha boundary")

    return numerator / total_count, lambda_level, tuple(q_star)


class ReferenceTests(unittest.TestCase):
    def test_single_block_has_no_photon_count_gain(self) -> None:
        alpha = 0.05
        block = DependenceBlock(200_000_000, 3.0)
        upper, level, q = least_favourable_block_mean_upper(alpha, (block,))
        self.assertAlmostEqual(q[0], 1.0 - alpha, places=15)
        self.assertAlmostEqual(upper, 3.0 * (1.0 - alpha), places=14)
        self.assertAlmostEqual(level, block.count * block.envelope * alpha, places=5)

    def test_identical_blocks_recover_k_block_common_q(self) -> None:
        alpha = 0.05
        blocks = tuple(DependenceBlock(100, 2.0) for _ in range(8))
        upper, _level, q = least_favourable_block_mean_upper(alpha, blocks)
        expected_q = common_q_independent_blocks_upper(alpha, 8)
        self.assertTrue(all(math.isclose(v, expected_q, rel_tol=2e-15) for v in q))
        self.assertTrue(math.isclose(upper, 2.0 * expected_q, rel_tol=2e-15))

    def test_more_independent_blocks_tighten_common_q(self) -> None:
        alpha = 0.05
        one = common_q_independent_blocks_upper(alpha, 1)
        ten = common_q_independent_blocks_upper(alpha, 10)
        hundred = common_q_independent_blocks_upper(alpha, 100)
        self.assertGreater(one, ten)
        self.assertGreater(ten, hundred)
        self.assertAlmostEqual(one, 0.95, places=15)

    def test_heterogeneous_weight_product_boundary(self) -> None:
        alpha = 0.05
        blocks = (DependenceBlock(5, 1.0), DependenceBlock(5, 10.0))
        upper, _level, q = least_favourable_block_mean_upper(alpha, blocks)
        log_p0 = sum(math.log1p(-qb) for qb in q)
        self.assertAlmostEqual(log_p0, math.log(alpha), places=13)
        self.assertGreater(q[1], q[0])
        self.assertGreater(upper, 0.0)

    def test_perfect_dependence_inside_each_block_is_sharp(self) -> None:
        alpha = 0.05
        q = common_q_independent_blocks_upper(alpha, 4)
        # Construction in every block: X_bi=B*Z_b for all i, with independent
        # Z_b~Bernoulli(q). Then P(all-zero)=product_b(1-q)=alpha exactly.
        self.assertAlmostEqual(4.0 * math.log1p(-q), math.log(alpha), places=14)

    def test_block_only_bound_is_weaker_than_photon_iid_bound(self) -> None:
        alpha = 0.05
        blocks = 10
        photons_per_block = 1000
        q_block_only = common_q_independent_blocks_upper(alpha, blocks)
        q_photon_iid = common_q_independent_blocks_upper(alpha, blocks * photons_per_block)
        self.assertGreater(q_block_only, q_photon_iid)

    def test_zero_envelope_does_not_consume_confidence_budget(self) -> None:
        alpha = 0.05
        blocks = (DependenceBlock(1_000_000, 0.0), DependenceBlock(7, 4.0))
        upper, _level, q = least_favourable_block_mean_upper(alpha, blocks)
        self.assertEqual(q[0], 0.0)
        self.assertAlmostEqual(q[1], 1.0 - alpha, places=15)
        expected = 7 * 4.0 * (1.0 - alpha) / 1_000_007
        self.assertAlmostEqual(upper, expected, places=15)

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            least_favourable_block_mean_upper(0.05, ())
        with self.assertRaises(ValueError):
            least_favourable_block_mean_upper(0.05, (DependenceBlock(0, 1.0),))
        with self.assertRaises(ValueError):
            least_favourable_block_mean_upper(0.05, (DependenceBlock(1, float("inf")),))
        with self.assertRaises(ValueError):
            common_q_independent_blocks_upper(0.05, 0)


def _summary() -> dict[str, object]:
    demo = (DependenceBlock(5, 1.0), DependenceBlock(5, 10.0))
    upper, level, q = least_favourable_block_mean_upper(0.05, demo)
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "assumption": "independent blocks; arbitrary within-block dependence; common marginal q per block",
        "single_block_common_q_95_upper": common_q_independent_blocks_upper(0.05, 1),
        "ten_block_common_q_95_upper": common_q_independent_blocks_upper(0.05, 10),
        "heterogeneous_demo_mean_upper": upper,
        "heterogeneous_demo_lambda": level,
        "heterogeneous_demo_q_star": list(q),
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
