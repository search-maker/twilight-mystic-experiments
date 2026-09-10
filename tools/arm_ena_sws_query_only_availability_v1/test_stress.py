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
PREFLIGHT_SPEC = importlib.util.spec_from_file_location(
    'arm_query_preflight_v1',
    REPO_ROOT / 'tools/arm_e0_successor_case_binding_audit_v1/preflight_query_authorization_v1.py',
)
assert PREFLIGHT_SPEC and PREFLIGHT_SPEC.loader
P = importlib.util.module_from_spec(PREFLIGHT_SPEC)
PREFLIGHT_SPEC.loader.exec_module(P)


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


def exact_historical_wq_correction_rows() -> list[dict]:
    stage = 'AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEW_GLOBAL_SCAN_REPLACEMENT_V2'
    common = (
        'branch=review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v2-20260910 | '
        'head=2acc4d73c08f741ba76643057535d73b7ffc66bc | '
        'base=5028cb7c7cd585d720749f0d572aa15e2f614bf9 | '
        'subject_pr=1026 | subject_head=5028cb7c7cd585d720749f0d572aa15e2f614bf9 | '
        'run=34443355962 | attempt=1 | job=102762814211 | terminal=FAILURE | artifact=NONE'
    )
    return [
        row(
            S._HISTORICAL_WQ_CORRECTION_BEGIN,
            f'WRITE_QUIET_BEGIN | {stage} | branch=review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v2-20260910',
        ),
        row(
            S._HISTORICAL_WQ_PROSE_END,
            f'WRITE_QUIET_END | {stage} | {common}\n\n'
            f'Exact matching closure for BEGIN `{S._HISTORICAL_WQ_CORRECTION_BEGIN}` only. Historical prose-bound closure.',
        ),
        row(
            S._HISTORICAL_WQ_CANONICAL_END,
            f'WRITE_QUIET_END | {stage} | begin={S._HISTORICAL_WQ_CORRECTION_BEGIN} | {common}\n\n'
            'CORRECTED MACHINE-READABLE FENCE RELEASE ONLY.',
        ),
    ]


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

    def test_cross_lane_exact_short_begin_write_quiet_passes(self):
        begin_id = S.BASELINE_COORDINATOR_COMMENT + 10
        comments = [
            baseline(),
            row(begin_id, 'AVPS_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(begin_id + 1, f'AVPS_OWNER::WRITE_QUIET_END | stage=x | begin={begin_id}'),
        ]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['write_quiet_begin_ids_after_baseline'], [begin_id])
        self.assertEqual(out['write_quiet_end_ids_after_baseline'], [begin_id + 1])

    def test_exact_historical_wq_canonical_correction_pair_passes(self):
        comments = [baseline(), *exact_historical_wq_correction_rows()]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['write_quiet_begin_ids_after_baseline'], [S._HISTORICAL_WQ_CORRECTION_BEGIN])
        self.assertEqual(
            out['write_quiet_end_ids_after_baseline'],
            [S._HISTORICAL_WQ_PROSE_END, S._HISTORICAL_WQ_CANONICAL_END],
        )

    def test_historical_wq_correction_mismatched_binding_refuses(self):
        rows = exact_historical_wq_correction_rows()
        rows[-1] = row(
            S._HISTORICAL_WQ_CANONICAL_END,
            rows[-1]['body'].replace('head=2acc4d73c08f741ba76643057535d73b7ffc66bc', 'head=0' * 20, 1),
        )
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([baseline(), *rows])

    def test_unrelated_duplicate_write_quiet_end_still_refuses(self):
        begin_id = S.BASELINE_COORDINATOR_COMMENT + 10
        comments = [
            baseline(),
            row(begin_id, 'AVPS_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(begin_id + 1, f'AVPS_OWNER::WRITE_QUIET_END | stage=x | begin={begin_id}'),
            row(begin_id + 2, f'AVPS_OWNER::WRITE_QUIET_END | stage=x | begin={begin_id}'),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_write_quiet_end_conflicting_begin_aliases_refuse(self):
        begin_id = S.BASELINE_COORDINATOR_COMMENT + 10
        comments = [
            baseline(),
            row(begin_id, 'AVPS_OWNER::WRITE_QUIET_BEGIN | stage=x'),
            row(
                begin_id + 1,
                f'AVPS_OWNER::WRITE_QUIET_END | stage=x | beginComment={begin_id} | begin={begin_id + 1}',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_write_quiet_reference_field_is_not_an_end_event(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ATMOSPHERE_OWNER::AVPS_CONTROL_FAILURE | write_quiet_end=5608708381 | artifact_count=0',
            ),
        ]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['write_quiet_begin_ids_after_baseline'], [])
        self.assertEqual(out['write_quiet_end_ids_after_baseline'], [])

    def test_write_quiet_reference_field_is_not_a_begin_event(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ATMOSPHERE_OWNER::AVPS_CONTROL_PREP | write_quiet_begin=5608671968 | science=false',
            ),
        ]
        out = S.audit_arm_governance(comments)
        self.assertEqual(out['write_quiet_begin_ids_after_baseline'], [])
        self.assertEqual(out['write_quiet_end_ids_after_baseline'], [])

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

    def test_exact_temporary_avps_cross_lane_serialization_passes(self):
        title = (
            'COORDINATOR::AVPS_SUCCESSOR_PREAUTH_RECEIPT_ACCEPTED_TRANSITION_ELIGIBLE_NOT_ALLOCATED__'
            'ONE_FRESH_ORDINAL46_AUTHORIZATION_CONTROL_BOUNDARY_AUTHORIZED__TOTAL_SKY_YIELDS_NEXT_LIVE_SLOT__SCIENCE_FALSE'
        )
        body = (
            title + '\n\nSERIALIZATION / OTHER V1 LANES\n'
            '- ARM PR1016 remains result-blind and clean-looking; do not merge it while moving main would invalidate/restart the exact AVPS control chain. '
            'Keep branch/prep/CI work parallel. This is a temporary exact-base dependency, not a rejection and not a generic freeze.\n'
        )
        S.audit_arm_governance([baseline(), row(5608360629, body)])

    def test_temporary_avps_cross_lane_serialization_nearby_variant_refuses(self):
        title = (
            'COORDINATOR::AVPS_SUCCESSOR_PREAUTH_RECEIPT_ACCEPTED_TRANSITION_ELIGIBLE_NOT_ALLOCATED__'
            'ONE_FRESH_ORDINAL46_AUTHORIZATION_CONTROL_BOUNDARY_AUTHORIZED__TOTAL_SKY_YIELDS_NEXT_LIVE_SLOT__SCIENCE_FALSE__REVOKED'
        )
        body = (
            title + '\n\nARM / AVPS\n'
            '- ARM PR1016 remains result-blind and clean-looking; do not merge it while moving main would invalidate/restart the exact AVPS control chain.\n'
        )
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, body)])

    def test_cleared_blocker_title_is_not_adverse(self):
        comments = [baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, 'COORDINATOR::ARM_QUERY_ONLY_BLOCKER_CLEARED')]
        S.audit_arm_governance(comments)

    def test_exact_5591488326_shape_positive_acceptance_passes(self):
        comments = [
            baseline(),
            row(
                5591488326,
                'COORDINATOR::ARM_QUERY_ONLY_AVAILABILITY_PR1003_ACCEPTED__EXACT_HEAD_ORDINARY_MERGE_AUTHORIZED__AUTHENTICATED_INVOCATION_STILL_FALSE\n\n'
                'STATUS=PR1003_RESULT_BLIND_QUERY_ONLY_INFRA_ACCEPTED / EXACT_HEAD_37FEA3_MERGE_AUTHORIZED / ARM_LIVE_QUERY_FALSE / AUTHENTICATED_WORKFLOW_DISPATCH_NOT_AUTHORIZED / SCIENCE_FALSE\n\n'
                'ARM PR1003 CLASSIFICATION\n'
                '- ACCEPT exact Draft PR #1003.\n'
                '- PR1001 remains frozen governance-NONADMISSIBLE and MUST NOT merge or be reused.\n\n'
                'AUTHORITY\n'
                'Exactly one ordinary merge of PR1003 is authorized.\n\n'
                'This does NOT authorize authenticated workflow_dispatch, ARM Live /query, protected opening, Stage B, science, or production.',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_current_postmerge_repair_authorization_passes(self):
        comments = [
            baseline(),
            row(
                5591521704,
                'COORDINATOR::ARM_QUERY_ONLY_POSTMERGE_STRESS_FALSE_POSITIVE_DEFECT__ONE_FRESH_NARROW_MECHANICAL_REPAIR_AUTHORIZED__AUTHENTICATED_INVOCATION_REMAINS_FALSE\n\n'
                'STATUS=PR1003_MERGED_TO_MAIN / POSTMERGE_LIVE_GOVERNANCE_STRESS_FAIL_CLOSED / POSITIVE_COORDINATOR_ACCEPTANCE_MISCLASSIFIED_AS_ADVERSE / ONE_FRESH_NONSCIENCE_REPAIR_CANDIDATE_AUTHORIZED / ARM_LIVE_QUERY_FALSE / AUTHENTICATED_WORKFLOW_DISPATCH_FALSE',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_current_owner_ready_for_coordinator_classification_passes(self):
        comments = [
            baseline(),
            row(
                5591870413,
                'ARM_OWNER::QUERY_ONLY_POSTMERGE_GOVERNANCE_FALSE_POSITIVE_REPAIR_PR1006_READY_FOR_COORDINATOR_CLASSIFICATION\n\n'
                'MATERIAL / RESULT_BLIND / NON_SCIENCE / NO_ARM_LIVE_QUERY.\n\n'
                'Authenticated workflow_dispatch remains FALSE and requires a separate fresh Coordinator protected-boundary transition.',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_exact_authenticated_discovery_authorization_title_passes(self):
        comments = [
            baseline(),
            row(
                5592250337,
                'COORDINATOR::ARM_QUERY_ONLY_AUTHENTICATED_DISCOVERY_ONE_SHOT_AUTHORIZED__HUMAN_WORKFLOW_DISPATCH_IF_NEEDED\n\n'
                'STATUS=ARM_QUERY_ONLY_INFRA_POSTMERGE_STABLE / EXACTLY_ONE_AUTHENTICATED_QUERY_ONLY_ATTEMPT1_AUTHORIZED / NATIVE_FILE_DOWNLOAD_FALSE / PROTECTED_VALUE_OPENING_FALSE / STAGE_B_FALSE / SCIENCE_FALSE',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_authenticated_discovery_authorization_nearby_not_authorized_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AUTHENTICATED_DISCOVERY_ONE_SHOT_NOT_AUTHORIZED__HUMAN_WORKFLOW_DISPATCH_IF_NEEDED',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_authenticated_discovery_authorization_nearby_revoked_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AUTHENTICATED_DISCOVERY_ONE_SHOT_AUTHORIZED__HUMAN_WORKFLOW_DISPATCH_IF_NEEDED__REVOKED',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_authenticated_discovery_authorization_nearby_extra_attempt_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AUTHENTICATED_DISCOVERY_ONE_SHOT_AUTHORIZED__HUMAN_WORKFLOW_DISPATCH_IF_NEEDED__SECOND_ATTEMPT',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_exact_consumed_attempt_repair_allowed_title_passes(self):
        comments = [
            baseline(),
            row(
                5594247950,
                'COORDINATOR::ARM_QUERY_ONLY_ATTEMPT1_CONSUMED_PREQUERY_STRESS_REFUSAL__ONE_FRESH_NARROW_NONSCIENCE_REPAIR_ALLOWED\n\n'
                'STATUS=ARM_QUERY_ONLY_ATTEMPT1_TERMINAL_FAILURE_CONSUMED / QUERY_ONLY_DISCOVERY_SKIPPED / NO_ARM_LIVE_QUERY / ONE_FRESH_NONSCIENCE_STRESS_CLASSIFIER_REPAIR_ALLOWED / NEW_AUTHENTICATED_ATTEMPT_NOT_AUTHORIZED',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_consumed_attempt_repair_nearby_not_allowed_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_ATTEMPT1_CONSUMED_PREQUERY_STRESS_REFUSAL__ONE_FRESH_NARROW_NONSCIENCE_REPAIR_NOT_ALLOWED',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_exact_current_predispatch_authorization_request_title_passes(self):
        comments = [
            baseline(),
            row(
                5596023369,
                'ARM_OWNER::FINAL_MAIN_PREDISPATCH_REALITY_CHECK_CLEAN__REPLACEMENT_QUERY_ONLY_AUTHORIZATION_REQUEST\n\n'
                'CONTROL_ONLY / RESULT_BLIND / NON_SCIENCE. Authenticated authority is requested, not self-granted.',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_exact_pr1016_current_main_refresh_merge_classification_title_passes(self):
        comments = [
            baseline(),
            row(
                5607859393,
                'ARM_OWNER::PR1016_CURRENT_MAIN_REFRESH_TERMINAL_CLEAN__REQUEST_EXACT_MERGE_CLASSIFICATION__RESULT_BLIND__AUTH_FALSE\n\n'
                'RESULT_BLIND / NON_SCIENCE / NON_AUTHORIZING exact ordinary merge-classification request.',
            ),
        ]
        S.audit_arm_governance(comments)

    def test_pr1016_current_main_refresh_merge_classification_nearby_variant_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ARM_OWNER::PR1016_CURRENT_MAIN_REFRESH_TERMINAL_CLEAN__REQUEST_EXACT_MERGE_CLASSIFICATION__RESULT_BLIND__AUTH_FALSE__SECOND_ATTEMPT',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_exact_pr1016_postmerge_benign_title_is_ledger_allowed(self):
        title = 'ARM_OWNER::PR1016_POSTMERGE_STABLE__RESULT_BLIND_INSTALLATION_COMPLETE__AUTH_FALSE'
        self.assertEqual(S._direct_arm_control_disposition(title), 'allowed')
        out = S.audit_arm_governance([baseline(), row(5617483200, title)])
        self.assertIn(5617483200, out['arm_relevant_comment_ids_after_baseline'])

    def test_pr1016_postmerge_benign_title_unknown_variant_still_refuses(self):
        title = 'ARM_OWNER::PR1016_POSTMERGE_STABLE__RESULT_BLIND_INSTALLATION_COMPLETE__AUTH_FALSE__UNCLASSIFIED'
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, title)])

    def test_pr1016_postmerge_benign_title_revoked_variant_still_refuses(self):
        title = 'ARM_OWNER::PR1016_POSTMERGE_STABLE__RESULT_BLIND_INSTALLATION_COMPLETE__AUTH_FALSE__REVOKED'
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([baseline(), row(S.BASELINE_COORDINATOR_COMMENT + 10, title)])

    def test_future_positive_authorization_shape_is_allowed_and_v1_preflight_compatible(self):
        cid = S.BASELINE_COORDINATOR_COMMENT + 10
        main_sha = 'a' * 40
        title = 'COORDINATOR::ARM_QUERY_ONLY_SUCCESSOR_AUTHORIZED__ONE_SHOT__ATTEMPT1'
        body = (
            title + '\n\n'
            f'workflow: `{P.WORKFLOW_PATH}`\n'
            'event: `workflow_dispatch`\n'
            f'main: `{main_sha}`\n'
            'attempt_1 only\n'
            'one-shot only\n'
        )
        comments = [baseline(), row(cid, body)]
        self.assertEqual(S._direct_arm_control_disposition(title), 'allowed')
        receipt = P.preflight(
            comments,
            authorization_comment=cid,
            authorization_title=title,
            exact_main_sha=main_sha,
            expected_current_main_sha=main_sha,
            expected_issue60_comment_count=len(comments),
            expected_issue60_latest_comment_id=cid,
        )
        self.assertEqual(receipt['status'], P.STATUS)
        self.assertEqual(receipt['stress_classifier_disposition'], 'allowed')

    def test_current_predispatch_authorization_request_nearby_revoked_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ARM_OWNER::FINAL_MAIN_PREDISPATCH_REALITY_CHECK_CLEAN__REPLACEMENT_QUERY_ONLY_AUTHORIZATION_REQUEST__REVOKED',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_current_predispatch_authorization_request_nearby_variant_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ARM_OWNER::FINAL_MAIN_PREDISPATCH_REALITY_CHECK_CLEAN__REPLACEMENT_QUERY_ONLY_AUTHORIZATION_REQUEST__SECOND_ATTEMPT',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_positive_vocabulary_in_actual_nonadmissibility_still_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AVAILABILITY_PR1005_NONADMISSIBLE__DO_NOT_MERGE__AUTHENTICATED_INVOCATION_FALSE\n\n'
                'A different historical PR was accepted, but this candidate is NOT_ADMISSIBLE.',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_positive_vocabulary_in_actual_revocation_still_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_AUTHORITY_REVOKED__REPAIR_NOT_AUTHORIZED\n\n'
                'Earlier merge acceptance is historical; current ARM authority is revoked.',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_positive_vocabulary_in_actual_refusal_still_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_REFUSAL__AUTHENTICATED_INVOCATION_FALSE\n\n'
                'Do not treat earlier accepted infrastructure as current authority.',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_negated_acceptance_cannot_match_positive_substring(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_PR1007_NOT_ACCEPTED__AUTHENTICATED_INVOCATION_FALSE',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_negated_coordinator_readiness_cannot_match_positive_substring(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'ARM_OWNER::QUERY_ONLY_PR1007_NOT_READY_FOR_COORDINATOR_CLASSIFICATION',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_ambiguous_direct_arm_governance_refuses(self):
        comments = [
            baseline(),
            row(
                S.BASELINE_COORDINATOR_COMMENT + 10,
                'COORDINATOR::ARM_QUERY_ONLY_BOUNDARY_UPDATE__AUTHENTICATED_INVOCATION_FALSE',
            ),
        ]
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance(comments)

    def test_baseline_absence_refuses(self):
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([row(S.BASELINE_COORDINATOR_COMMENT + 1, 'ARM_OWNER::OK')])

    def test_baseline_semantic_drift_refuses(self):
        with self.assertRaises(S.StressFailure):
            S.audit_arm_governance([row(S.BASELINE_COORDINATOR_COMMENT, 'COORDINATOR::TOTAL_SKY_ONLY')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
