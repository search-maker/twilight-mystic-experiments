#!/usr/bin/env python3
"""POST_V1/NONBLOCKING heterogeneous finite-hit confidence reference.

This module provides a conservative finite-hit fallback when photon/run hit
probabilities need not be identical. It is solver-free, result-blind, and
never interprets an exact estimator zero as a physical zero or substitutes an
epsilon.

Photon-level model
------------------
Let independent Bernoulli indicators I_i have arbitrary hit probabilities
p_i, and let S=sum I_i. Write mu=sum p_i. Independence gives

    Var(S) = sum p_i(1-p_i)
           <= mu * (1 - mu/n),

where the final inequality is Cauchy/Jensen. If a fixed preregistered horizon
observes S=k and a candidate mu>k is true, Cantelli's one-sided inequality
implies

    P_mu[S <= k]
      <= Vmax / (Vmax + (mu-k)^2),
    Vmax = mu*(1-mu/n).

Inverting the alpha boundary yields the quadratic

    [alpha + (1-alpha)/n] mu^2
      - [2 alpha k + (1-alpha)] mu
      + alpha k^2 = 0.

The larger root is a conservative fixed-horizon upper endpoint for mu. This
requires independent indicators but not a common hit probability. For k=0 it
is deliberately weaker than the exact all-zero product/AM-GM certificate; the
all-zero path should continue to use that stronger result.

Block-only fallback
-------------------
If independence is justified only between runs/blocks, define H_b=1 when a
block contains at least one positive score. Arbitrary within-block dependence
is allowed. Apply the same heterogeneous Cantelli inversion to the independent
block indicators H_b. If block b has n_b photons and a frozen per-photon
envelope B_b, then its total score obeys

    block_score_b <= n_b * B_b * H_b.

Given only an upper bound on sum P(H_b=1), the worst expected score allocates
that probability budget to the largest block weights n_b*B_b first. The
reference implements this grouped fractional-knapsack step exactly with
Fraction arithmetic.

Repeated finite-hit looks do not receive the special all-zero nested-path
anytime privilege. This module is a fixed-horizon/reference component; a
multi-look campaign must use a separately preregistered alpha-spending or
validated confidence-sequence rule.
"""

from __future__ import annotations

import argparse
import itertools
import json
import unittest
from dataclasses import dataclass
from fractions import Fraction

_DEFAULT_BITS = 96


def _fraction(value: Fraction | int | str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError("inputs must be exact Fraction/int/decimal-string values")
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
    if not isinstance(k, int) or isinstance(k, bool) or not (0 <= k <= n):
        raise ValueError("k must be an integer in [0,n]")


def cantelli_gap(
    n: int,
    k: int,
    alpha: Fraction | int | str,
    mu: Fraction | int | str,
) -> Fraction:
    """Exact signed Cantelli boundary polynomial."""
    _require_n_k(n, k)
    af = _fraction(alpha)
    _require_probability("alpha", af)
    mf = _fraction(mu)
    if not (Fraction(k) <= mf <= Fraction(n)):
        raise ValueError("mu must lie in [k,n] for the upper-root bracket")
    return af * (mf - k) ** 2 - (1 - af) * mf * (1 - mf / Fraction(n))


def heterogeneous_hit_sum_upper_bracket(
    n: int,
    k: int,
    alpha: Fraction | int | str,
    *,
    bits: int = _DEFAULT_BITS,
) -> tuple[Fraction, Fraction]:
    """Exact-rational bracket for the heterogeneous independent-hit mu upper."""
    _require_n_k(n, k)
    af = _fraction(alpha)
    _require_probability("alpha", af)
    if not isinstance(bits, int) or isinstance(bits, bool) or bits <= 0:
        raise ValueError("bits must be a positive integer")
    if k == n:
        return Fraction(n), Fraction(n)

    lo = Fraction(k)
    hi = Fraction(n)
    if cantelli_gap(n, k, af, lo) > 0:
        raise ArithmeticError("lower Cantelli bracket has wrong sign")
    if cantelli_gap(n, k, af, hi) < 0:
        raise ArithmeticError("upper Cantelli bracket has wrong sign")

    for _ in range(bits):
        mid = (lo + hi) / 2
        if cantelli_gap(n, k, af, mid) < 0:
            lo = mid
        else:
            hi = mid

    if cantelli_gap(n, k, af, lo) > 0:
        raise ArithmeticError("lower Cantelli bracket lost nonpositive invariant")
    if cantelli_gap(n, k, af, hi) < 0:
        raise ArithmeticError("upper Cantelli bracket lost nonnegative invariant")
    return lo, hi


def average_hit_probability_upper(
    n: int,
    k: int,
    alpha: Fraction | int | str,
    *,
    bits: int = _DEFAULT_BITS,
) -> Fraction:
    """Conservative upper bound on average p_i under the heterogeneous model."""
    _lo, hi = heterogeneous_hit_sum_upper_bracket(n, k, alpha, bits=bits)
    return hi / Fraction(n)


@dataclass(frozen=True)
class EnvelopeGroup:
    count: int
    envelope: Fraction | int | str


def grouped_worst_mean_from_hit_budget(
    groups: tuple[EnvelopeGroup, ...],
    hit_sum_upper: Fraction | int | str,
) -> Fraction:
    """Worst average score given only sum p_i <= hit_sum_upper."""
    if not groups:
        raise ValueError("at least one envelope group is required")
    budget = _fraction(hit_sum_upper)
    if budget < 0:
        raise ValueError("hit_sum_upper must be nonnegative")

    normalized: list[tuple[Fraction, int]] = []
    total_count = 0
    for group in groups:
        if not isinstance(group, EnvelopeGroup):
            raise TypeError("groups must contain EnvelopeGroup values")
        if not isinstance(group.count, int) or isinstance(group.count, bool) or group.count <= 0:
            raise ValueError("group counts must be positive integers")
        envelope = _fraction(group.envelope)
        if envelope < 0:
            raise ValueError("envelopes must be nonnegative")
        normalized.append((envelope, group.count))
        total_count += group.count

    if budget > total_count:
        raise ValueError("hit_sum_upper cannot exceed total indicator count")

    remaining = budget
    total_score = Fraction(0)
    for envelope, count in sorted(normalized, key=lambda item: item[0], reverse=True):
        take = min(remaining, Fraction(count))
        total_score += envelope * take
        remaining -= take
        if remaining == 0:
            break
    if remaining != 0:
        raise ArithmeticError("grouped allocation failed to exhaust hit budget")
    return total_score / Fraction(total_count)


def heterogeneous_bounded_mean_upper(
    groups: tuple[EnvelopeGroup, ...],
    k: int,
    alpha: Fraction | int | str,
    *,
    deterministic_tail: Fraction | int | str = 0,
    bits: int = _DEFAULT_BITS,
) -> Fraction:
    """Finite-hit mean cap for independent non-identical indicators."""
    n = sum(group.count for group in groups)
    _lo, mu_hi = heterogeneous_hit_sum_upper_bracket(n, k, alpha, bits=bits)
    tail = _fraction(deterministic_tail)
    if tail < 0:
        raise ValueError("deterministic_tail must be nonnegative")
    return grouped_worst_mean_from_hit_budget(groups, mu_hi) + tail


@dataclass(frozen=True)
class BlockEnvelope:
    photons: int
    per_photon_envelope: Fraction | int | str


def block_only_mean_upper(
    blocks: tuple[BlockEnvelope, ...],
    hit_blocks: int,
    alpha: Fraction | int | str,
    *,
    deterministic_tail: Fraction | int | str = 0,
    bits: int = _DEFAULT_BITS,
) -> Fraction:
    """Mean-score cap with arbitrary within-block dependence."""
    if not blocks:
        raise ValueError("at least one block is required")
    weights: list[Fraction] = []
    total_photons = 0
    for block in blocks:
        if not isinstance(block, BlockEnvelope):
            raise TypeError("blocks must contain BlockEnvelope values")
        if not isinstance(block.photons, int) or isinstance(block.photons, bool) or block.photons <= 0:
            raise ValueError("block photon counts must be positive integers")
        envelope = _fraction(block.per_photon_envelope)
        if envelope < 0:
            raise ValueError("block envelopes must be nonnegative")
        weights.append(Fraction(block.photons) * envelope)
        total_photons += block.photons

    _require_n_k(len(blocks), hit_blocks)
    _lo, hsum_hi = heterogeneous_hit_sum_upper_bracket(
        len(blocks), hit_blocks, alpha, bits=bits
    )

    remaining = hsum_hi
    total_score = Fraction(0)
    for weight in sorted(weights, reverse=True):
        take = min(remaining, Fraction(1))
        total_score += weight * take
        remaining -= take
        if remaining == 0:
            break
    if remaining != 0:
        raise ArithmeticError("block allocation failed to exhaust hit-probability budget")

    tail = _fraction(deterministic_tail)
    if tail < 0:
        raise ValueError("deterministic_tail must be nonnegative")
    return total_score / Fraction(total_photons) + tail


def _poisson_binomial_cdf_exact(probabilities: tuple[Fraction, ...], k: int) -> Fraction:
    """Tiny exact oracle used only by deterministic self-tests."""
    n = len(probabilities)
    if not 0 <= k <= n:
        raise ValueError("k out of range")
    mass = [Fraction(1)] + [Fraction(0)] * n
    used = 0
    for p in probabilities:
        if not Fraction(0) <= p <= Fraction(1):
            raise ValueError("probabilities must lie in [0,1]")
        nxt = [Fraction(0)] * (n + 1)
        for j in range(used + 1):
            nxt[j] += mass[j] * (1 - p)
            nxt[j + 1] += mass[j] * p
        mass = nxt
        used += 1
    return sum(mass[: k + 1])


class ReferenceTests(unittest.TestCase):
    def test_200m_finite_hit_reference_values(self) -> None:
        alpha = Fraction(1, 20)
        q1 = average_hit_probability_upper(200_000_000, 1, alpha, bits=120)
        q2 = average_hit_probability_upper(200_000_000, 2, alpha, bits=120)
        self.assertTrue(Fraction("0.00000010476135") < q1 < Fraction("0.00000010476136"))
        self.assertTrue(Fraction("0.00000011412374") < q2 < Fraction("0.00000011412375"))

    def test_large_n_is_supported_without_binomial_cdf(self) -> None:
        lo, hi = heterogeneous_hit_sum_upper_bracket(
            200_000_000, 2, Fraction(1, 20), bits=100
        )
        self.assertLess(lo, hi)
        self.assertLessEqual(hi - lo, Fraction(200_000_000, 2**100))
        self.assertLessEqual(cantelli_gap(200_000_000, 2, Fraction(1, 20), lo), 0)
        self.assertGreaterEqual(cantelli_gap(200_000_000, 2, Fraction(1, 20), hi), 0)

    def test_more_hits_cannot_tighten_heterogeneous_upper(self) -> None:
        alpha = Fraction(1, 20)
        values = [
            average_hit_probability_upper(1000, k, alpha, bits=80)
            for k in range(6)
        ]
        self.assertEqual(values, sorted(values))

    def test_zero_case_is_intentionally_loose(self) -> None:
        alpha = Fraction(1, 20)
        cantelli_q = average_hit_probability_upper(100, 0, alpha, bits=90)
        self.assertGreater(cantelli_q, Fraction(1, 100))

    def test_coarse_poisson_binomial_grid_respects_tail_certificate(self) -> None:
        n = 4
        k = 1
        alpha = Fraction(1, 4)
        _lo, mu_hi = heterogeneous_hit_sum_upper_bracket(n, k, alpha, bits=80)
        grid = tuple(Fraction(i, 4) for i in range(5))
        checked = 0
        for probabilities in itertools.product(grid, repeat=n):
            if sum(probabilities) > mu_hi:
                checked += 1
                self.assertLessEqual(
                    _poisson_binomial_cdf_exact(probabilities, k), alpha
                )
        self.assertGreater(checked, 0)

    def test_grouped_envelope_allocation_is_exact_greedy(self) -> None:
        groups = (
            EnvelopeGroup(2, Fraction(10)),
            EnvelopeGroup(8, Fraction(1)),
        )
        self.assertEqual(
            grouped_worst_mean_from_hit_budget(groups, Fraction(3, 2)),
            Fraction(3, 2),
        )

    def test_grouped_constant_envelope_reduces_to_B_times_average_p(self) -> None:
        groups = (EnvelopeGroup(7, Fraction(3, 2)), EnvelopeGroup(3, Fraction(3, 2)))
        budget = Fraction(7, 4)
        self.assertEqual(
            grouped_worst_mean_from_hit_budget(groups, budget),
            Fraction(3, 2) * budget / 10,
        )

    def test_block_only_single_block_has_no_photon_count_gain(self) -> None:
        alpha = Fraction(1, 20)
        cap = block_only_mean_upper(
            (BlockEnvelope(200_000_000, Fraction(1)),),
            hit_blocks=0,
            alpha=alpha,
            bits=100,
        )
        cantelli_single_block = average_hit_probability_upper(1, 0, alpha, bits=100)
        self.assertEqual(cap, cantelli_single_block)

    def test_block_weights_allocate_to_largest_first(self) -> None:
        alpha = Fraction(1, 4)
        blocks = (
            BlockEnvelope(100, Fraction(1)),
            BlockEnvelope(10, Fraction(1)),
            BlockEnvelope(1, Fraction(1)),
            BlockEnvelope(1, Fraction(1)),
        )
        cap = block_only_mean_upper(blocks, 1, alpha, bits=90)
        self.assertGreater(cap, Fraction(0))
        self.assertLessEqual(cap, Fraction(1))

    def test_fail_closed_inputs(self) -> None:
        with self.assertRaises(TypeError):
            average_hit_probability_upper(100, 1, 0.05)
        with self.assertRaises(ValueError):
            heterogeneous_hit_sum_upper_bracket(100, 101, Fraction(1, 20))
        with self.assertRaises(ValueError):
            grouped_worst_mean_from_hit_budget(
                (EnvelopeGroup(1, Fraction(1)),), Fraction(2)
            )
        with self.assertRaises(TypeError):
            grouped_worst_mean_from_hit_budget(
                (EnvelopeGroup(1, 1.0),), Fraction(1, 2)
            )


def _summary() -> dict[str, object]:
    alpha = Fraction(1, 20)
    q1 = average_hit_probability_upper(200_000_000, 1, alpha, bits=120)
    q2 = average_hit_probability_upper(200_000_000, 2, alpha, bits=120)
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "scope": "fixed-horizon independent non-identical Bernoulli hits; Cantelli inversion",
        "alpha": str(alpha),
        "n": 200_000_000,
        "k1_average_hit_probability_upper": str(q1),
        "k2_average_hit_probability_upper": str(q2),
        "block_fallback": "independent blocks; arbitrary within-block dependence",
        "zero_rule": "prefer stronger exact all-zero product/AM-GM certificate when k=0",
        "multi_look_rule": "separate preregistered alpha spending/confidence-sequence required",
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
