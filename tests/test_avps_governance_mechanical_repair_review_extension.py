from pathlib import Path
import unittest


REVIEWER = Path('.github/workflows/avps-governance-mechanical-repair-review-v1.yml')
CANONICAL_REVIEWER = Path('.github/workflows/avps-recovery4-canonical-parser-review-v2.yml')
PUBLISHER_PATH = '.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml'
SCIENCE_PATH = '.github/workflows/avps-v2-postconsumption-recovery4-science.yml'
PARSER_PATH = 'scripts/avps_write_quiet_parser_v1.py'
PARSER_TEST_PATH = 'tests/test_avps_recovery4_canonical_write_quiet_parser_v1.py'
LEGACY_PARSER_TEST_PATH = 'tests/test_avps_recovery4_ordinal45_write_quiet_parser_repair.py'
SELF_PATH = '.github/workflows/avps-governance-mechanical-repair-review-v1.yml'
EXTENSION_PATH = 'tests/test_avps_governance_mechanical_repair_review_extension.py'
LEGACY_REVIEWERS = (
    '.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-choreography-review-v67.yml',
    '.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-choreography-review-v71.yml',
    '.github/workflows/avps-v2-recovery4-ordinal45-publisher-v3-accepted-canonical-apply-review-v76.yml',
)


class AvpsGovernanceMechanicalReviewerExtensionContract(unittest.TestCase):
    def setUp(self):
        self.reviewer = REVIEWER.read_text(encoding='utf-8')
        self.canonical = CANONICAL_REVIEWER.read_text(encoding='utf-8')

    def test_historical_reviewer_remains_pull_request_only_and_read_only(self):
        on_block = self.reviewer.split('\non:\n', 1)[1].split('\npermissions:\n', 1)[0]
        self.assertIn('pull_request:', on_block)
        self.assertNotIn('workflow_dispatch:', on_block)
        permissions = self.reviewer.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        for permission in ('contents: read', 'pull-requests: read', 'issues: read', 'actions: read'):
            self.assertIn(permission, permissions)
        self.assertNotRegex(permissions, r'(?m):\s*write\s*$')

    def test_historical_reviewer_trigger_is_detached_from_canonical_phase_b(self):
        on_block = self.reviewer.split('\non:\n', 1)[1].split('\npermissions:\n', 1)[0]
        # Coordinator 5596384953: the old reviewer remains available for its
        # historical/self-contract scope, but must not trigger merely because
        # the new five-path canonical Phase-B changes publisher or migrated
        # legacy parser regression bytes.
        self.assertIn(SELF_PATH, on_block)
        self.assertIn(EXTENSION_PATH, on_block)
        for path in LEGACY_REVIEWERS:
            self.assertIn(path, on_block)
        self.assertNotIn(PUBLISHER_PATH, on_block)
        self.assertNotIn(LEGACY_PARSER_TEST_PATH, on_block)
        self.assertNotIn(SCIENCE_PATH, on_block)
        self.assertNotIn(PARSER_PATH, on_block)
        self.assertNotIn(PARSER_TEST_PATH, on_block)

    def test_historical_reviewer_keeps_frozen_pr978_evidence_and_projection(self):
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
            'synthetic unauthorized publisher mutation',
            'projection failed to reject unauthorized publisher mutation',
        )
        for token in required:
            self.assertIn(token, self.reviewer)

    def test_historical_reviewer_keeps_mechanical_governance_evidence(self):
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
            'repeated-identical standalone aliases must collapse to one distinct BEGIN id',
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

    def test_historical_reviewer_preserves_parser_regression_as_historical_scope(self):
        self.assertIn(f'PARSER_TEST_PATH: {LEGACY_PARSER_TEST_PATH}', self.reviewer)
        self.assertIn('Run canonical WRITE_QUIET parser regression', self.reviewer)
        self.assertIn('python "$PARSER_TEST_PATH"', self.reviewer)
        self.assertTrue(Path(LEGACY_PARSER_TEST_PATH).is_file())

    def test_installed_reviewer_v2_is_binding_for_exact_five_path_phase_b(self):
        for path in (
            SCIENCE_PATH,
            PUBLISHER_PATH,
            PARSER_PATH,
            PARSER_TEST_PATH,
            LEGACY_PARSER_TEST_PATH,
        ):
            self.assertIn(path, self.canonical)
        self.assertIn(
            'phase_b_required={science,publisher,parser,parser_test,legacy_parser_test}',
            self.canonical,
        )
        self.assertIn("mode='PHASE_B'", self.canonical)
        self.assertIn("mode='INSTALLATION'", self.canonical)
        self.assertIn('self_path not in changed', self.canonical)
        self.assertIn('install_test not in changed', self.canonical)
        self.assertIn('REVIEWER_OWNED_CANONICAL_PARSER_SEMANTIC_CORPUS_V1', self.canonical)
        self.assertIn('PARSER_STATIC_PURITY_GUARD_V1', self.canonical)
        self.assertIn('MUTABLE_TEST_NON_SPOOF_GUARD_V1', self.canonical)
        self.assertIn('REVIEWER_OWNED_ISOLATED_IMPORT_FIXTURE_V1', self.canonical)

    def test_installed_reviewer_v2_is_independent_read_only_zero_runtime(self):
        on_block = self.canonical.split('\non:\n', 1)[1].split('\npermissions:\n', 1)[0]
        self.assertIn('pull_request:', on_block)
        self.assertNotIn('workflow_dispatch:', on_block)
        permissions = self.canonical.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        self.assertNotRegex(permissions, r'(?m):\s*write\s*$')
        body = self.canonical.split('permissions:', 1)[1]
        for token in ('gh workflow run', 'gh api -X POST', 'command -v uvspec', 'rte_solver mystic'):
            self.assertNotIn(token, body)

    def test_cleanup_does_not_turn_historical_reviewer_into_phase_b_authority(self):
        summary = self.reviewer.split("echo '### AVPS governance mechanical review v1'", 1)[1]
        self.assertIn(
            'no solver, publisher invocation, WRITE_QUIET entry, dispatch, seed allocation, result opening, or science is authorized',
            summary,
        )
        # Historical publisher/parser references remain inside the frozen
        # evidence machinery, but are deliberately absent from the trigger.
        self.assertIn(f'PUBLISHER_PATH: {PUBLISHER_PATH}', self.reviewer)
        self.assertIn(f'PARSER_TEST_PATH: {LEGACY_PARSER_TEST_PATH}', self.reviewer)


if __name__ == '__main__':
    unittest.main()
