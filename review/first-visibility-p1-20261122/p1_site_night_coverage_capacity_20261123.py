#!/usr/bin/env python3
"""Pre-outcome P1 design capacity check; no star or outcome data are ingested.

All-success exact Clopper-Pearson lower bounds for independent, identically
sampled site-night pass/fail observations. These are optimistic under any
clustering, selection bias, incomplete meteorology or target cherry-picking.
"""
import json
import math
from datetime import date

ALPHA = 0.05

def all_success_lower(n: int, *, tails: int = 1) -> float:
    if not isinstance(n, int) or n <= 0 or tails not in (1, 2):
        raise ValueError('n must be positive integer; tails=1 or 2')
    return math.exp(math.log(ALPHA / tails) / n)

def min_all_success_n(target_coverage: float, *, tails: int = 1) -> int:
    if not 0 < target_coverage < 1 or tails not in (1, 2):
        raise ValueError('invalid target or tails')
    n = max(1, math.floor(math.log(ALPHA / tails) / math.log(target_coverage)))
    while all_success_lower(n, tails=tails) < target_coverage:
        n += 1
    while n > 1 and all_success_lower(n - 1, tails=tails) >= target_coverage:
        n -= 1
    return n

def main():
    assert min_all_success_n(0.90) == 29
    assert min_all_success_n(0.95) == 59
    assert min_all_success_n(0.90, tails=2) == 36
    assert min_all_success_n(0.95, tails=2) == 72
    assert abs(all_success_lower(6, tails=2) - 0.5407418735600995) < 1e-12
    ns = [3, 4, 10, 12, 24, 30, 59, 72]
    result = {
        'fixture': 'P1_INDEPENDENT_SITE_NIGHT_COVERAGE_CAPACITY',
        'authored_date': str(date(2026, 11, 23)),
        'source': 'Exact all-success binomial Clopper-Pearson confidence limit',
        'alpha': ALPHA,
        'hypothetical_only': True,
        'real_human_events': 0,
        'important_caveat': 'Assumes independent representative site-night trials and ALL successes; neither is established. Coverage is not timing error or true first sighting.',
        'all_success_site_nights': [
            {'n': n,
             'lower_95pct_one_sided': round(all_success_lower(n), 9),
             'lower_95pct_two_sided': round(all_success_lower(n, tails=2), 9)} for n in ns
        ],
        'minimum_all_success_independent_site_nights': {
            'target_90pct_one_sided_95pct': min_all_success_n(0.90),
            'target_95pct_one_sided_95pct': min_all_success_n(0.95),
            'target_90pct_two_sided_95pct': min_all_success_n(0.90, tails=2),
            'target_95pct_two_sided_95pct': min_all_success_n(0.95, tails=2)
        },
        'existing_P1_cap_site_nights': 24,
        'external_quantitative_screen_site_nights': 30,
        'source_freeze': {'model_sha': None, 'observer_consent': False,
                          'approved_sites': 0, 'observations': 0},
        'release_classification': 'NO_GO_PILOT_ONLY'
    }
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
