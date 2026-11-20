#!/usr/bin/env python3
"""Pre-outcome statistical feasibility check; NO observational/model data."""
import argparse
import json
import math
import unittest

ALPHA = 0.05

def binomial_tail_ge(k, n, p):
    if not (0 <= k <= n and 0 <= p <= 1):
        raise ValueError('invalid binomial argument')
    return math.fsum(math.comb(n, i)*p**i*(1-p)**(n-i) for i in range(k, n+1))

def lower_cp(k, n, alpha=ALPHA, sides=2):
    if not (isinstance(k,int) and isinstance(n,int) and 0 <= k <= n and n > 0):
        raise ValueError('invalid events')
    if k == 0:
        return 0.0
    target=alpha/sides
    lo, hi=0.0, 1.0
    for _ in range(100):
        mid=(lo+hi)/2
        if binomial_tail_ge(k,n,mid) < target:
            lo=mid
        else:
            hi=mid
    return (lo+hi)/2

def report():
    scenarios=[('late_minimum_all_pass',6,6),('full_pilot_all_pass',18,18),
               ('full_pilot_fifteen_pass',15,18),('early_feasibility_ten_of_twelve',10,12),
               ('late_seventeen_all_pass',17,17)]
    return {'basis':'PRE-OUTCOME mathematical sensitivity only, not field results',
            'assumptions':'independent identically distributed Bernoulli events (optimistic, unverified)',
            'confidence':'95 percent Clopper-Pearson two-sided exact marginal lower bound',
            'coverage_target':0.80,
            'pilot_caps':{'total_events':18,'minimum_late_depth_events':6,'nights':3,'observers':3},
            'scenarios':[{'name':name,'successes':k,'trials':n,'apparent_coverage':k/n,
                          'lower_bound':lower_cp(k,n)} for name,k,n in scenarios],
            'minimum_all_successes_for_lower_bound_above_80_percent':
                next(n for n in range(1,100) if lower_cp(n,n)>0.8),
            'interpretation':'Even 6/6 late events leaves a lower bound near 0.541, not 0.80; 3 clustered nights make event-independent coverage inference optimistic. Pilot remains feasibility only; no model timing error or human first-sighting observation.'}

class Tests(unittest.TestCase):
    def test_all_successes_closed_form(self):
        for n in [3,6,17,18]:
            self.assertAlmostEqual(lower_cp(n,n),(ALPHA/2)**(1/n),places=12)
    def test_numeric_scenarios(self):
        self.assertAlmostEqual(lower_cp(6,6),0.540741874,places=8)
        self.assertAlmostEqual(lower_cp(18,18),0.814698032,places=8)
        self.assertAlmostEqual(lower_cp(15,18),0.585822509,places=8)
    def test_threshold_min_n(self):
        self.assertEqual(report()['minimum_all_successes_for_lower_bound_above_80_percent'],17)
    def test_count_validation(self):
        for n,k in [(0,0),(4,5),(4,-1)]:
            with self.assertRaises(ValueError): lower_cp(k,n)

if __name__ == '__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--self-test',action='store_true')
    options=a.parse_args()
    if options.self_test:
        unittest.main(argv=['statistical_fixture'],exit=False,verbosity=2)
    else:
        print(json.dumps(report(),indent=2,ensure_ascii=True))
