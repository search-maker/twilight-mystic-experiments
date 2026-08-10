#!/usr/bin/env python3
from __future__ import annotations

import compileall
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST_MODULES = (
    'test_full_spectrum_estimator_pilot_analysis_v6',
    'test_full_spectrum_estimator_pilot_artifact_contract_v5',
    'test_full_spectrum_estimator_pilot_directive_surface_v6',
    'test_full_spectrum_estimator_pilot_frozen_evidence_verifiers_v1',
    'test_full_spectrum_estimator_pilot_preauthorization_guard_v4',
    'test_full_spectrum_estimator_pilot_protocol_v2',
    'test_full_spectrum_estimator_pilot_review_portability_v1',
)
EXPECTED_TEST_COUNT = 39


def main() -> int:
    if not compileall.compile_dir(ROOT, quiet=1, force=True):
        print(json.dumps({'status': 'COMPILE_FAILED'}))
        return 2

    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for name in TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(name))
    count = suite.countTestCases()
    if count != EXPECTED_TEST_COUNT:
        print(json.dumps({'status': 'TEST_COUNT_DRIFT', 'expected': EXPECTED_TEST_COUNT, 'observed': count}))
        return 2
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {
        'status': 'PASSED' if result.wasSuccessful() else 'FAILED',
        'testCount': count,
        'failureCount': len(result.failures),
        'errorCount': len(result.errors),
        'testModules': list(TEST_MODULES),
        'scientificExecutionPerformed': False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result.wasSuccessful() else 2


if __name__ == '__main__':
    raise SystemExit(main())
