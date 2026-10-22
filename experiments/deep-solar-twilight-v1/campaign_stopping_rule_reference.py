#!/usr/bin/env python3
"""POST_V1/NONBLOCKING rare-event campaign stopping-policy reference.

This module composes the already separated deep-twilight numerical paths without
changing any estimator physics:

* while every inspected score is exactly zero, an all-zero anytime certificate
  may be used under its separately stated stochastic assumptions;
* after the first positive score, the all-zero path is permanently unavailable;
* finite-hit inference may be reported only at preregistered fixed horizons;
* the all-zero branch and all finite-hit looks share one explicit familywise
  failure-probability budget.

The last point prevents an easy optional-stopping error. If the anytime-zero
certificate has failure probability at most alpha_zero and finite fixed-horizon
look j has failure probability at most alpha_j, then regardless of which branch
is ultimately reported,

    P(any reported upper bound fails)
      <= alpha_zero + sum_j alpha_j.

The finite-look events are evaluated at fixed preregistered horizons. Restricting
reporting to trajectories that have already seen a positive score cannot enlarge
any fixed-horizon failure event, so a union bound is sufficient. Unused look
alpha is not silently recycled. No epsilon is introduced and this module does
not assert photon independence; the bound engine used at each look must justify
its own assumptions independently.
"""

from __future__ import annotations

import argparse
import json
import unittest
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable


@dataclass(frozen=True)
class FiniteLook:
    horizon: int
    alpha: Fraction


@dataclass(frozen=True)
class CampaignPolicy:
    total_alpha: Fraction
    zero_alpha: Fraction
    finite_looks: tuple[FiniteLook, ...]


@dataclass(frozen=True)
class Observation:
    horizon: int
    cumulative_hits: int


@dataclass(frozen=True)
class Decision:
    horizon: int
    cumulative_hits: int
    mode: str
    alpha: Fraction | None


def _fraction(name: str, value: Fraction | int | str) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{name} must be Fraction/int/decimal-string; float is refused")
    try:
        out = value if isinstance(value, Fraction) else Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not an exact rational value") from exc
    return out


def make_policy(
    total_alpha: Fraction | int | str,
    zero_alpha: Fraction | int | str,
    finite_looks: Iterable[tuple[int, Fraction | int | str]],
) -> CampaignPolicy:
    total = _fraction("total_alpha", total_alpha)
    zero = _fraction("zero_alpha", zero_alpha)
    if not (Fraction(0) < total < Fraction(1)):
        raise ValueError("total_alpha must lie strictly between 0 and 1")
    if not (Fraction(0) < zero < Fraction(1)):
        raise ValueError("zero_alpha must lie strictly between 0 and 1")

    looks: list[FiniteLook] = []
    previous_horizon = 0
    for horizon, alpha_value in finite_looks:
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon <= 0:
            raise ValueError("finite-look horizons must be positive integers")
        if horizon <= previous_horizon:
            raise ValueError("finite-look horizons must be strictly increasing")
        alpha = _fraction("finite look alpha", alpha_value)
        if not (Fraction(0) < alpha < Fraction(1)):
            raise ValueError("each finite-look alpha must lie strictly between 0 and 1")
        looks.append(FiniteLook(horizon, alpha))
        previous_horizon = horizon

    spent = zero + sum((look.alpha for look in looks), Fraction(0))
    if spent > total:
        raise ValueError(
            "familywise alpha overspend: zero_alpha + finite-look alphas exceeds total_alpha"
        )
    return CampaignPolicy(total, zero, tuple(looks))


def allocated_alpha(policy: CampaignPolicy) -> Fraction:
    return policy.zero_alpha + sum((look.alpha for look in policy.finite_looks), Fraction(0))


def unused_alpha(policy: CampaignPolicy) -> Fraction:
    return policy.total_alpha - allocated_alpha(policy)


def _look_map(policy: CampaignPolicy) -> dict[int, Fraction]:
    return {look.horizon: look.alpha for look in policy.finite_looks}


def decisions_for_trace(
    policy: CampaignPolicy,
    observations: Iterable[Observation],
) -> tuple[Decision, ...]:
    """Classify a cumulative observation trace under the frozen policy.

    ``ZERO_ANYTIME`` means the all-zero reference may be consulted at that
    horizon, subject to its own assumptions. ``FINITE_FIXED_LOOK`` means a
    positive score has occurred and this horizon is one of the preregistered
    finite-hit looks. ``NO_CLAIM_WAIT_FOR_FIXED_LOOK`` means a positive score has
    occurred but the current horizon is not a frozen finite-hit look.
    """
    looks = _look_map(policy)
    out: list[Decision] = []
    prior_horizon = 0
    prior_hits = 0
    positive_seen = False

    for obs in observations:
        if not isinstance(obs, Observation):
            raise TypeError("observations must contain Observation instances")
        if not isinstance(obs.horizon, int) or isinstance(obs.horizon, bool) or obs.horizon <= 0:
            raise ValueError("observation horizon must be a positive integer")
        if obs.horizon <= prior_horizon:
            raise ValueError("observation horizons must be strictly increasing")
        if (
            not isinstance(obs.cumulative_hits, int)
            or isinstance(obs.cumulative_hits, bool)
            or obs.cumulative_hits < 0
            or obs.cumulative_hits > obs.horizon
        ):
            raise ValueError("cumulative_hits must be an integer in [0, horizon]")
        if obs.cumulative_hits < prior_hits:
            raise ValueError("cumulative hit count cannot decrease")

        if obs.cumulative_hits > 0:
            positive_seen = True

        if not positive_seen:
            decision = Decision(obs.horizon, 0, "ZERO_ANYTIME", policy.zero_alpha)
        elif obs.horizon in looks:
            decision = Decision(
                obs.horizon,
                obs.cumulative_hits,
                "FINITE_FIXED_LOOK",
                looks[obs.horizon],
            )
        else:
            decision = Decision(
                obs.horizon,
                obs.cumulative_hits,
                "NO_CLAIM_WAIT_FOR_FIXED_LOOK",
                None,
            )
        out.append(decision)
        prior_horizon = obs.horizon
        prior_hits = obs.cumulative_hits

    return tuple(out)


def familywise_failure_upper(policy: CampaignPolicy) -> Fraction:
    """Exact union-bound ceiling for any report permitted by this policy."""
    return allocated_alpha(policy)


class ReferenceTests(unittest.TestCase):
    def test_exact_alpha_budget_closes(self) -> None:
        policy = make_policy(
            "0.05",
            "0.025",
            ((50, "0.00625"), (100, "0.00625"), (200, "0.00625"), (400, "0.00625")),
        )
        self.assertEqual(allocated_alpha(policy), Fraction(1, 20))
        self.assertEqual(unused_alpha(policy), 0)
        self.assertEqual(familywise_failure_upper(policy), Fraction(1, 20))

    def test_reusing_full_alpha_in_both_branches_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            make_policy("0.05", "0.05", ((100, "0.05"),))

    def test_nonincreasing_finite_horizons_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            make_policy("0.05", "0.02", ((100, "0.01"), (100, "0.01")))

    def test_float_alpha_configuration_is_refused(self) -> None:
        with self.assertRaises(TypeError):
            make_policy(0.05, "0.02", ((100, "0.01"),))
        with self.assertRaises(TypeError):
            make_policy("0.05", 0.02, ((100, "0.01"),))
        with self.assertRaises(TypeError):
            make_policy("0.05", "0.02", ((100, 0.01),))

    def test_repeated_all_zero_inspections_remain_zero_anytime(self) -> None:
        policy = make_policy("0.05", "0.02", ((100, "0.01"), (200, "0.01")))
        trace = decisions_for_trace(
            policy,
            (Observation(10, 0), Observation(57, 0), Observation(199, 0), Observation(500, 0)),
        )
        self.assertTrue(all(item.mode == "ZERO_ANYTIME" for item in trace))
        self.assertTrue(all(item.alpha == Fraction(1, 50) for item in trace))

    def test_first_positive_permanently_switches_off_zero_path(self) -> None:
        policy = make_policy("0.05", "0.02", ((100, "0.01"), (200, "0.01")))
        trace = decisions_for_trace(
            policy,
            (
                Observation(50, 0),
                Observation(75, 1),
                Observation(100, 1),
                Observation(150, 1),
                Observation(200, 2),
            ),
        )
        self.assertEqual([item.mode for item in trace], [
            "ZERO_ANYTIME",
            "NO_CLAIM_WAIT_FOR_FIXED_LOOK",
            "FINITE_FIXED_LOOK",
            "NO_CLAIM_WAIT_FOR_FIXED_LOOK",
            "FINITE_FIXED_LOOK",
        ])
        self.assertEqual(trace[2].alpha, Fraction(1, 100))
        self.assertEqual(trace[4].alpha, Fraction(1, 100))

    def test_positive_exactly_at_frozen_horizon_is_reportable(self) -> None:
        policy = make_policy("0.05", "0.02", ((100, "0.01"),))
        trace = decisions_for_trace(policy, (Observation(99, 0), Observation(100, 1)))
        self.assertEqual(trace[-1].mode, "FINITE_FIXED_LOOK")

    def test_skipped_finite_looks_do_not_recycle_alpha(self) -> None:
        policy = make_policy("0.05", "0.02", ((100, "0.01"), (200, "0.01")))
        trace = decisions_for_trace(policy, (Observation(150, 1), Observation(200, 1)))
        self.assertEqual(trace[0].mode, "NO_CLAIM_WAIT_FOR_FIXED_LOOK")
        self.assertEqual(trace[1].alpha, Fraction(1, 100))
        self.assertEqual(unused_alpha(policy), Fraction(1, 100))
        self.assertEqual(familywise_failure_upper(policy), Fraction(1, 25))

    def test_cumulative_hit_count_cannot_decrease(self) -> None:
        policy = make_policy("0.05", "0.02", ((100, "0.01"), (200, "0.01")))
        with self.assertRaises(ValueError):
            decisions_for_trace(policy, (Observation(100, 1), Observation(200, 0)))

    def test_invalid_observation_fails_closed(self) -> None:
        policy = make_policy("0.05", "0.02", ())
        with self.assertRaises(ValueError):
            decisions_for_trace(policy, (Observation(10, 11),))
        with self.assertRaises(ValueError):
            decisions_for_trace(policy, (Observation(10, 0), Observation(10, 0)))


def _summary() -> dict[str, object]:
    policy = make_policy(
        "0.05",
        "0.025",
        ((50_000_000, "0.00625"), (100_000_000, "0.00625"), (200_000_000, "0.00625"), (400_000_000, "0.00625")),
    )
    trace = decisions_for_trace(
        policy,
        (Observation(25_000_000, 0), Observation(75_000_000, 1), Observation(100_000_000, 1)),
    )
    return {
        "status": "REFERENCE_ONLY_NO_SCIENCE",
        "total_alpha": str(policy.total_alpha),
        "zero_alpha": str(policy.zero_alpha),
        "finite_look_alphas": [str(look.alpha) for look in policy.finite_looks],
        "familywise_failure_upper": str(familywise_failure_upper(policy)),
        "trace_modes": [decision.mode for decision in trace],
        "epsilon_substitution": False,
        "photon_independence_asserted": False,
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
