#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
SPEC = importlib.util.spec_from_file_location('arm_query_stress', ROOT / 'stress.py')
assert SPEC and SPEC.loader
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


def row(cid: int, body: str) -> dict:
    return {'id': cid, 'body': body}


class StressTests(unittest.TestCase):
    def test_actual_candidate_bytes_pass_static_contract(self):
        workflow = (REPO_ROOT / '.github/workflows/arm-ena-sws-query-only-availability-v1.yml').read_text(encoding='utf-8')
        executable = (ROOT / 'discover.py').read_text(encoding='utf-8')
        S.validate_workflow(workflow)
        S.validate_executable(executable)

    def test_cross_lane_write_quiet_is_ignored(self):
        comments = [
            row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::ARM_PR998_MERGED_POSTMERGE_CI_SUCCESS__QUERY_ONLY_SUCCESSOR_PREP_ACTIVE'),
            row(S.BASELINE_COORDINATOR_COMMENT + 10, 'TOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x'),
        ]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['arm_scoped_comment_ids_after_baseline'], [])

    def test_unmatched_arm_write_quiet_refuses(self):
        comments = [
            row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::ARM_PR998_MERGED_POSTMERGE_CI_SUCCESS__QUERY_ONLY_SUCCESSOR_PREP_ACTIVE'),
            row(S.BASELINE_COORDINATOR_COMMENT + 10, 'ARM_OWNER::WRITE_QUIET_BEGIN | stage=x'),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_matched_arm_write_quiet_passes(self):
        comments = [
            row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::ARM_PR998_MERGED_POSTMERGE_CI_SUCCESS__QUERY_ONLY_SUCCESSOR_PREP_ACTIVE'),
            row(S.BASELINE_COORDINATOR_COMMENT + 10, 'ARM_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(S.BASELINE_COORDINATOR_COMMENT + 11, 'ARM_OWNER::WRITE_QUIET_END | stage=x'),
        ]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['arm_scoped_comment_ids_after_baseline'], [S.BASELINE_COORDINATOR_COMMENT + 10, S.BASELINE_COORDINATOR_COMMENT + 11])

    def test_explicit_arm_adverse_marker_refuses(self):
        comments = [
            row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::ARM_PR998_MERGED_POSTMERGE_CI_SUCCESS__QUERY_ONLY_SUCCESSOR_PREP_ACTIVE'),
            row(S.BASELINE_COORDINATOR_COMMENT + 10, 'COORDINATOR::ARM_QUERY_ONLY_REVOKED'),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_cleared_blocker_title_is_not_adverse(self):
        comments = [
            row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::ARM_PR998_MERGED_POSTMERGE_CI_SUCCESS__QUERY_ONLY_SUCCESSOR_PREP_ACTIVE'),
            row(S.BASELINE_COORDINATOR_COMMENT + 10, 'COORDINATOR::ARM_QUERY_ONLY_BLOCKER_CLEARED'),
        ]
        S.audit_arm_governance(comments)

    def test_baseline_absence_refuses(self):
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([row(S.BASELINE_COORDINATOR_COMMENT + 1, 'ARM_OWNER::OK')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
