from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / 'experiments'
    / 'aerosol-family-challenge-v2'
    / 'repository_global_seed_scan.py'
)
SPEC = importlib.util.spec_from_file_location('aerosol_family_repository_global_seed_scan', MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


def empty_context() -> dict[str, list[dict]]:
    return {key: [] for key in scan.SURFACE_KEYS}


class SnapshotFenceTests(unittest.TestCase):
    def baseline(self) -> dict[str, list[dict]]:
        ctx = empty_context()
        ctx['branches'] = [{'name': 'main', 'commit': {'sha': 'a' * 40}}]
        ctx['runs'] = [{'id': 20, 'status': 'queued', 'updated_at': '2026-01-01T00:00:00Z', 'display_title': 'safe'}]
        ctx['issues'] = [{'id': 30, 'number': 7, 'body': 'safe'}]
        ctx['issueComments'] = [{'id': 40, 'body': 'safe'}]
        return ctx

    def test_harmless_post_fence_rows_do_not_break_two_pass_snapshot(self):
        first_raw = self.baseline()
        fence = scan.build_snapshot_fence(first_raw)
        first = scan.apply_snapshot_fence(first_raw, fence)

        second_raw = copy.deepcopy(first_raw)
        second_raw['runs'][0]['status'] = 'completed'
        second_raw['runs'][0]['updated_at'] = '2026-01-01T00:02:00Z'
        second_raw['runs'].append({'id': 21, 'status': 'queued', 'display_title': 'new harmless run'})
        second_raw['issueComments'].append({'id': 41, 'body': 'new harmless comment'})
        second_raw['branches'].append({'name': 'new-harmless-branch', 'commit': {'sha': 'b' * 40}})

        second = scan.apply_snapshot_fence(second_raw, fence)
        self.assertEqual(scan.require_two_pass_stability(first, second), scan.stable_context_sha256(second))
        post = scan.post_fence_rows(second_raw, fence)
        self.assertEqual(len(post['runs']), 1)
        self.assertEqual(len(post['issueComments']), 1)
        self.assertEqual(len(post['branches']), 1)

    def test_post_fence_candidate_seed_is_still_fail_closed(self):
        seed = 1234567
        first_raw = self.baseline()
        fence = scan.build_snapshot_fence(first_raw)
        second_raw = copy.deepcopy(first_raw)
        second_raw['issueComments'].append({'id': 41, 'body': f'new seed {seed}'})

        collisions = scan.find_post_fence_seed_collisions(second_raw, fence, {seed})
        self.assertEqual(collisions, [{'surface': 'issueComments', 'id': '41', 'seeds': [seed]}])

    def test_existing_fenced_content_edit_remains_unstable(self):
        first_raw = self.baseline()
        fence = scan.build_snapshot_fence(first_raw)
        first = scan.apply_snapshot_fence(first_raw, fence)
        second_raw = copy.deepcopy(first_raw)
        second_raw['issues'][0]['body'] = 'changed content'
        second = scan.apply_snapshot_fence(second_raw, fence)

        with self.assertRaisesRegex(RuntimeError, 'metadata changed between two complete enumerations'):
            scan.require_two_pass_stability(first, second)

    def test_existing_fenced_branch_head_movement_remains_unstable(self):
        first_raw = self.baseline()
        fence = scan.build_snapshot_fence(first_raw)
        first = scan.apply_snapshot_fence(first_raw, fence)
        second_raw = copy.deepcopy(first_raw)
        second_raw['branches'][0]['commit']['sha'] = 'c' * 40
        second = scan.apply_snapshot_fence(second_raw, fence)

        with self.assertRaisesRegex(RuntimeError, 'metadata changed between two complete enumerations'):
            scan.require_two_pass_stability(first, second)

    def test_post_fence_review_proof_artifact_is_not_hidden_by_fence(self):
        first_raw = self.baseline()
        fence = scan.build_snapshot_fence(first_raw)
        second_raw = copy.deepcopy(first_raw)
        second_raw['artifacts'].append({
            'id': 55,
            'name': scan.REVIEW_PROOF_ARTIFACT_NAME,
            'workflow_run': {'id': 777},
        })

        self.assertEqual(scan.apply_snapshot_fence(second_raw, fence)['artifacts'], [])
        self.assertEqual(len(scan.external_review_proof_artifacts(second_raw)), 1)

    def test_pagination_duplicate_is_deduped_but_conflicting_duplicate_refuses(self):
        first_raw = self.baseline()
        first_raw['issueComments'].append({'id': 40, 'body': 'safe', 'updated_at': '2026-01-01T00:03:00Z'})
        fence = scan.build_snapshot_fence(first_raw)
        fenced = scan.apply_snapshot_fence(first_raw, fence)
        self.assertEqual(len(fenced['issueComments']), 1)

        conflicting = self.baseline()
        conflicting['issueComments'].append({'id': 40, 'body': 'different'})
        with self.assertRaisesRegex(RuntimeError, 'changed within one complete enumeration'):
            scan.build_snapshot_fence(conflicting)


if __name__ == '__main__':
    unittest.main()
