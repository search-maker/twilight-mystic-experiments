from pathlib import Path
import re
import unittest


REVIEWER = Path('.github/workflows/avps-governance-mechanical-repair-review-v1.yml')
PUBLISHER = Path('.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml')
PARSER_TEST = Path('tests/test_avps_recovery4_ordinal45_write_quiet_parser_repair.py')


class AvpsGovernanceMechanicalReviewerExtensionContract(unittest.TestCase):
    def setUp(self):
        self.reviewer = REVIEWER.read_text(encoding='utf-8')
        self.publisher = PUBLISHER.read_text(encoding='utf-8')

    def test_reviewer_remains_pull_request_only_and_read_only(self):
        on_block = self.reviewer.split('\non:\n', 1)[1].split('\npermissions:\n', 1)[0]
        self.assertIn('pull_request:', on_block)
        self.assertNotIn('workflow_dispatch:', on_block)
        permissions = self.reviewer.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        self.assertIn('contents: read', permissions)
        self.assertIn('pull-requests: read', permissions)
        self.assertIn('issues: read', permissions)
        self.assertIn('actions: read', permissions)
        self.assertNotRegex(permissions, r'(?m):\s*write\s*$')

    def test_phase_a_scope_contains_only_durable_reviewer_contract_surfaces(self):
        required = (
            '.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml',
            '.github/workflows/avps-governance-mechanical-repair-review-v1.yml',
            'tests/test_avps_recovery4_ordinal45_write_quiet_parser_repair.py',
            'tests/test_avps_governance_mechanical_repair_review_extension.py',
        )
        for path in required:
            self.assertIn(path, self.reviewer)
        self.assertIn('non-governance path changed', self.reviewer)
        self.assertIn('historical reviewer may only be deleted, never recreated/modified', self.reviewer)

    def test_exact_phase_b_authority_is_pinned_in_reviewer_fixtures(self):
        required = (
            '5576203465',
            '5535375905',
            '5563105177',
            '5562775627',
            '5471174859',
            '5471141095',
            '5472575510',
            '5472560826',
            '5573615763',
            '5573638267',
            'WRITE_QUIET_END begin=123 beginComment=124',
            'WRITE_QUIET_END | beginComment=123\\nbegin=124',
            'Narrative only with historical `begin=123` mention',
            'TOTAL_SKY_OWNER::WRITE_QUIET_BEGIN',
            'ATMOSPHERE_OWNER::WRITE_QUIET_BEGIN',
            'COORDINATOR::AVPS_PUBLISHER_BLOCKER',
            'publisher changed outside the Coordinator-authorized mechanical compatibility surface',
            'ACTUAL publisher mechanical grammar helpers missing',
            'post-cutoff narrative FAIL-CLOSED text must not bind',
            'structured post-cutoff AVPS blocker must remain fail-closed',
            'full seven-case Total-Sky V3 parser corpus',
        )
        for token in required:
            self.assertIn(token, self.reviewer)

    def test_actual_publisher_anchor_cardinalities_match_reviewer_projection_contract(self):
        self.assertEqual(self.publisher.count('# BEGIN_WRITE_QUIET_END_LINE_PARSER_V1'), 3)
        self.assertEqual(self.publisher.count('# END_WRITE_QUIET_END_LINE_PARSER_V1'), 3)
        self.assertEqual(self.publisher.count('def avps_governance_blocker(body,cid=None):'), 1)
        self.assertEqual(len(re.findall(r'(?m)^\s*KNOWN_DEFECT=\d+$', self.publisher)), 1)
        old_count = self.publisher.count("elif first.startswith('WRITE_QUIET_BEGIN'):")
        owner_aware_count = self.publisher.count('elif is_write_quiet_begin(body):')
        self.assertIn((old_count, owner_aware_count), {(3, 0), (0, 3)})
        self.assertEqual(old_count + owner_aware_count, 3)

    def test_projection_masks_classifier_before_parser_and_keeps_negative_control(self):
        projection = self.reviewer.split('          def projection(text, label):\n', 1)[1].split(
            '          def projection_sha(text):\n', 1
        )[0]
        self.assertLess(
            projection.index("text = gov.sub('          # AVPS_GOVERNED_POST_CUTOFF_CLASSIFIER\\n', text)"),
            projection.index("text = parser.sub('          # AVPS_GOVERNED_WRITE_QUIET_END_AND_BEGIN_GRAMMAR', text)"),
        )
        self.assertNotIn("text = gov.sub('          # AVPS_GOVERNED_POST_CUTOFF_CLASSIFIER', text)", projection)
        self.assertIn('synthetic unauthorized publisher mutation', self.reviewer)
        self.assertIn('projection failed to reject unauthorized publisher mutation', self.reviewer)

    def test_projection_separator_preserves_parser_sentinel_cardinality(self):
        begin = '# BEGIN_WRITE_QUIET_END_LINE_PARSER_V1'
        end = '# END_WRITE_QUIET_END_LINE_PARSER_V1'
        parser = re.compile(r'(?ms)^\s*' + re.escape(begin) + r'\n.*?^\s*' + re.escape(end) + r'$')
        gov = re.compile(r'(?ms)^          def avps_governance_blocker\(body,cid=None\):\n.*?(?=^          # BEGIN_WRITE_QUIET_END_LINE_PARSER_V1$)')
        self.assertEqual(len(gov.findall(self.publisher)), 1)
        projected = gov.sub('          # AVPS_GOVERNED_POST_CUTOFF_CLASSIFIER\n', self.publisher)
        self.assertEqual(projected.count(begin), 3)
        self.assertEqual(len(parser.findall(projected)), 3)
        self.assertIn('# AVPS_GOVERNED_POST_CUTOFF_CLASSIFIER\n          # BEGIN_WRITE_QUIET_END_LINE_PARSER_V1', projected)

    def test_frozen_pr978_exact_projection_diagnostic_is_pinned(self):
        required = (
            'f73eed74738ce0354f75a2ad2dbb375322737089',
            '0a30788b93dcf0bc08753dd03e6840c961c1bd9d',
            'FROZEN_PR978_BASE',
            'FROZEN_PR978_HEAD',
            'PROJECTION_SHA256',
            'PROJECTION_RESIDUAL_UNIFIED_DIFF_BEGIN',
            'PROJECTION_RESIDUAL_UNIFIED_DIFF_END',
            'difflib.unified_diff',
            "hashlib.sha256(text.encode('utf-8')).hexdigest()",
            'repository_file_at_ref',
            'frozen PR978 exact-byte diagnostic PASS',
        )
        for token in required:
            self.assertIn(token, self.reviewer)
        self.assertIn("r'(?ms)^          ' + re.escape(begin)", self.reviewer)
        projection_step = self.reviewer.split(
            '      - name: Prove publisher changes stay inside the Coordinator-authorized mechanical surface\n', 1
        )[1].split(
            '      - name: Run exact Phase-B semantic fixtures against ACTUAL publisher bytes when publisher changes\n', 1
        )[0]
        self.assertNotIn("parser = re.compile(r'(?ms)^\\s*'", projection_step)
        self.assertIn("if projection(frozen_synthetic, 'FROZEN_PR978_SYNTHETIC') == projection(frozen_head, 'FROZEN_PR978_HEAD'):", projection_step)

    def test_frozen_pr978_begin_anchor_cardinality_is_relational_not_magic(self):
        self.assertIn('if frozen_base_old < 1 or frozen_base_new != 0:', self.reviewer)
        self.assertIn('if frozen_head_old != 0 or frozen_head_new != frozen_base_old:', self.reviewer)
        self.assertNotIn('if (frozen_base_old, frozen_base_new) != (3, 0):', self.reviewer)
        self.assertNotIn('if (frozen_head_old, frozen_head_new) != (0, 3):', self.reviewer)
        self.assertNotIn("not in {(3, 0), (0, 3)}", self.reviewer)

    def test_stale_second_whole_marker_negative_is_replaced_by_first_line_conflict(self):
        self.assertIn("'WRITE_QUIET_END | beginComment=123\\nbegin=124'", self.reviewer)
        self.assertNotIn("'WRITE_QUIET_END | beginComment=123\\nWRITE_QUIET_END | beginComment=123'", self.reviewer)

    def test_existing_corrected_end_regression_remains_part_of_durable_review(self):
        self.assertTrue(PARSER_TEST.is_file())
        parser_test = PARSER_TEST.read_text(encoding='utf-8')
        self.assertIn("self.assertIn('record_write_quiet_end', namespace)", parser_test)
        self.assertIn('python "$PARSER_TEST_PATH"', self.reviewer)
        self.assertIn('Run canonical WRITE_QUIET parser regression', self.reviewer)

    def test_reviewer_cannot_self_authorize_science_or_publisher_invocation(self):
        summary = self.reviewer.split("echo '### AVPS governance mechanical review v1'", 1)[1]
        self.assertIn('no solver, publisher invocation, WRITE_QUIET entry, dispatch, seed allocation, result opening, or science is authorized', summary)
        self.assertNotIn('contents: write', self.reviewer.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0])


if __name__ == '__main__':
    unittest.main()
