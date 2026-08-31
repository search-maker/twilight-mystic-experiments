from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'repository_global_seed_scan_hardening.py'
spec = importlib.util.spec_from_file_location('lunar_exec003_scan_hardening_test_target', HELPER)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot import hardening helper')
hard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = hard
spec.loader.exec_module(hard)


class RepositoryGlobalSeedScanHardeningTests(unittest.TestCase):
    def empty_context(self):
        return {key: [] for key in hard.base.SURFACE_KEYS}

    def test_nested_repository_pushed_at_is_stability_only_noise(self):
        first = self.empty_context()
        second = copy.deepcopy(first)
        first['runs'] = [{
            'id': 101,
            'display_title': 'safe',
            'repository': {'id': 22, 'full_name': 'owner/repo', 'pushed_at': '2026-08-31T09:00:00Z'},
        }]
        second['runs'] = [{
            'id': 101,
            'display_title': 'safe',
            'repository': {'id': 22, 'full_name': 'owner/repo', 'pushed_at': '2026-08-31T09:01:00Z'},
        }]
        self.assertEqual(
            hard.require_two_pass_stability(first, second),
            hard.require_two_pass_stability(second, first),
        )
        self.assertEqual(hard.stability_diff_summary(first, second), [])

    def test_stability_normalization_does_not_weaken_raw_seed_detection(self):
        seed = 12345678
        row = {'id': 101, 'repository': {'pushed_at': str(seed)}}
        stability = hard._canonical_stability_value(row)
        raw_collision = hard.base._canonical_collision_value(row)
        self.assertNotIn('pushed_at', stability['repository'])
        self.assertIn('pushed_at', raw_collision['repository'])
        self.assertEqual(hard.base.seed_literals(raw_collision, {seed}), [seed])

    def test_existing_branch_head_change_still_fails_with_identity_diagnostic(self):
        first = self.empty_context()
        second = self.empty_context()
        first['branches'] = [{'name': 'main', 'commit': {'sha': 'a' * 40}}]
        second['branches'] = [{'name': 'main', 'commit': {'sha': 'b' * 40}}]
        with self.assertRaisesRegex(RuntimeError, r'changed=branches\[main\]'):
            hard.require_two_pass_stability(first, second)

    def test_meaningful_existing_row_change_still_fails_with_identity_diagnostic(self):
        first = self.empty_context()
        second = self.empty_context()
        first['issueComments'] = [{'id': 7, 'body': 'safe'}]
        second['issueComments'] = [{'id': 7, 'body': 'changed'}]
        with self.assertRaisesRegex(RuntimeError, r'changed=issueComments\[7\]'):
            hard.require_two_pass_stability(first, second)

    def test_install_changes_only_stability_comparator_hook(self):
        raw_canonicalizer = hard.base._canonical_collision_value
        seed_parser = hard.base.seed_literals
        installed = hard.install_into_bound_scanner()
        self.assertIs(installed.require_two_pass_stability, hard.require_two_pass_stability)
        self.assertIs(installed._canonical_collision_value, raw_canonicalizer)
        self.assertIs(installed.seed_literals, seed_parser)


if __name__ == '__main__':
    unittest.main(verbosity=2)
