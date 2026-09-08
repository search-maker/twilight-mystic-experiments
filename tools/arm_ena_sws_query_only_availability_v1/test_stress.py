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


def baseline() -> dict:
    return row(
        S.BASELINE_COORDINATOR_COMMENT,
        'COORDINATOR::TOTAL_SKY_V5R1_FAIL_CLOSED_AND_V5R2_DIAGNOSTIC_SUCCESSOR_AUTHORIZED__PROTECTED_ATTEMPT_NOT_YET_AUTHORIZED\n\n'
        'GLOBAL WRITE_QUIET remains binding: fresh-read exact #60 tail immediately before EVERY mutation.\n\n'
        'ARM / AVPS\n'
        '- ARM may resume only its already-authorized post-V5R1 fence-clear safe/query-only fresh-successor preparation from current clean main, but PR1001 remains governance-NONADMISSIBLE and must not merge; authenticated invocation remains separately unauthorized.\n'
    )


def positive_5591488326_shape() -> str:
    return (
        'COORDINATOR::ARM_QUERY_ONLY_AVAILABILITY_PR1003_ACCEPTED__EXACT_HEAD_ORDINARY_MERGE_AUTHORIZED__AUTHENTICATED_INVOCATION_STILL_FALSE\n\n'
        'STATUS=PR1003_RESULT_BLIND_QUERY_ONLY_INFRA_ACCEPTED / EXACT_HEAD_37FEA3_MERGE_AUTHORIZED / ARM_LIVE_QUERY_FALSE / AUTHENTICATED_WORKFLOW_DISPATCH_NOT_AUTHORIZED / SCIENCE_FALSE\n\n'
        'ARM PR1003 CLASSIFICATION\n'
        '- ACCEPT exact Draft PR #1003 at the reviewed head.\n'
        '- PR1001 remains frozen governance-NONADMISSIBLE and MUST NOT merge or be reused as installation/authority evidence.\n\n'
        'AUTHORITY\n'
        'Exactly one ordinary merge of PR1003 is authorized while the exact guards remain unchanged. Any drift expires this merge authority unspent.\n\n'
        'This does NOT authorize any authenticated workflow_dispatch, ARM Live /query, credential-value read, native SWS file download/open, protected SWS/SASZE value opening, Stage B, MYSTIC/science, or production.\n'
    )


class StressTests(unittest.TestCase):
    def test_actual_candidate_bytes_pass_static_contract(self):
        workflow = (REPO_ROOT / '.github/workflows/arm-ena-sws-query-only-availability-v1.yml').read_text(encoding='utf-8')
        executable = (ROOT / 'discover.py').read_text(encoding='utf-8')
        S.validate_workflow(workflow)
        S.validate_executable(executable)

    def test_cross_lane_unmatched_write_quiet_refuses(self):
        comments = [baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, 'TOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x')]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_cross_lane_exact_matched_write_quiet_passes(self):
        begin_id = S.BASELINE_COORDINATOR_COMMENT + 10
        comments = [
            baseline(),
            row(begin_id, 'TOTAL_SKY_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(begin_id + 1, f'TOTAL_SKY_OWNER::WRITE_QUIET_END | stage=x | beginComment={begin_id}'),
        ]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['write_quiet_begin_ids_after_baseline'], [begin_id])
        self.assertEqual(out['write_quiet_end_ids_after_baseline'], [begin_id + 1])

    def test_write_quiet_end_must_bind_exact_begin(self):
        begin_id = S.BASELINE_COORDINATOR_COMMENT + 10
        comments = [
            baseline(),
            row(begin_id, 'DEEP_TWILIGHT_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(begin_id + 1, f'DEEP_TWILIGHT_OWNER::WRITE_QUIET_END | stage=x | beginComment={begin_id - 1}'),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_write_quiet_stage_mismatch_refuses(self):
        begin_id = S.BASELINE_COORDINATOR_COMMENT + 10
        comments = [
            baseline(),
            row(begin_id, 'AVPS_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(begin_id + 1, f'AVPS_OWNER::WRITE_QUIET_END | stage=y | beginComment={begin_id}'),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_explicit_arm_adverse_marker_refuses(self):
        comments = [baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, 'COORDINATOR::ARM_QUERY_ONLY_REVOKED')]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_cross_lane_coordinator_arm_nonadmissible_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::OTHER_LANE_TRANSITION\n\nOTHER\n- safe\n\nARM / AVPS\n- ARM query-only successor is NOT_ADMISSIBLE and must not merge.\n\nNEXT\n- unrelated',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_unrelated_coordinator_fail_closed_does_not_poison_allowed_arm_section(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::TOTAL_SKY_FAIL_CLOSED\n\nTOTAL SKY\n- frozen\n\nARM / AVPS\n- ARM may continue query-only successor preparation; authenticated invocation remains separately unauthorized.\n\nNEXT\n- unrelated',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_owner_ready_checkpoint_can_reference_old_nonadmissible_candidate(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ARM_OWNER::QUERY_ONLY_AVAILABILITY_FRESH_SUCCESSOR_PR1003_READY_FOR_REVIEW_AND_MERGE_CLASSIFICATION\n\n'
                'Current fresh successor is ready. PR1001 remains governance-NONADMISSIBLE and MUST NOT merge. '
                'Authenticated invocation remains separately unauthorized.',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_exact_5591488326_shape_positive_acceptance_passes(self):
        comments = [baseline(), row(5591488326, positive_5591488326_shape())]
        S.audit_arm_governance(comments)

    def test_positive_vocabulary_does_not_hide_actual_revocation(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AVAILABILITY_PR1003_REVOKED__AUTHENTICATED_INVOCATION_STILL_FALSE\n\n'
                'STATUS=PR1003_RESULT_BLIND_QUERY_ONLY_INFRA_ACCEPTED / ARM_LIVE_QUERY_FALSE / SCIENCE_FALSE\n'
                'The earlier acceptance is revoked.',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_positive_vocabulary_does_not_hide_nonadmissibility(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AVAILABILITY_PR1003_NONADMISSIBLE__DO_NOT_MERGE__AUTHENTICATED_INVOCATION_STILL_FALSE\n\n'
                'Earlier MERGE_AUTHORIZED language is superseded; candidate is NOT_ADMISSIBLE.',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_positive_vocabulary_does_not_hide_refusal_or_expiry(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AVAILABILITY_PR1003_REFUSAL__MERGE_AUTHORITY_EXPIRED__AUTHENTICATED_INVOCATION_STILL_FALSE\n\n'
                'The former ACCEPTED transition no longer authorizes merge.',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_ambiguous_direct_arm_governance_refuses(self):
        comments = [baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, 'COORDINATOR::ARM_QUERY_ONLY_STATE_CHANGED')]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_cleared_blocker_title_is_not_adverse(self):
        comments = [baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, 'COORDINATOR::ARM_QUERY_ONLY_BLOCKER_CLEARED')]
        S.audit_arm_governance(comments)

    def test_baseline_absence_refuses(self):
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([row(S.BASELINE_COORDINATOR_COMMENT + 1, 'ARM_OWNER::OK')])

    def test_baseline_semantic_drift_refuses(self):
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::TOTAL_SKY_ONLY')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
