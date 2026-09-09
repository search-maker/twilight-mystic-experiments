from pathlib import Path
import unittest

REVIEWER = Path('.github/workflows/avps-recovery4-canonical-parser-review-v2.yml')


class CanonicalParserReviewerInstallationContract(unittest.TestCase):
    def setUp(self):
        self.text = REVIEWER.read_text(encoding='utf-8')

    def test_pull_request_only_read_only(self):
        on = self.text.split('\non:\n', 1)[1].split('\npermissions:\n', 1)[0]
        self.assertIn('pull_request:', on)
        self.assertNotIn('workflow_dispatch:', on)
        permissions = self.text.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        for key in ('contents: read', 'actions: read', 'issues: read', 'pull-requests: read'):
            self.assertIn(key, permissions)
        self.assertNotIn(': write', permissions)

    def test_future_phase_b_surface_requires_complete_parser_migration(self):
        for path in (
            '.github/workflows/avps-v2-postconsumption-recovery4-science.yml',
            '.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml',
            'scripts/avps_write_quiet_parser_v1.py',
            'tests/test_avps_recovery4_canonical_write_quiet_parser_v1.py',
            'tests/test_avps_recovery4_ordinal45_write_quiet_parser_repair.py',
        ):
            self.assertIn(path, self.text)
        self.assertIn('phase_b_required={science,publisher,parser,parser_test,legacy_parser_test}', self.text)
        self.assertIn('changed==phase_b_required', self.text)

    def test_installation_cannot_self_certify_phase_b(self):
        self.assertIn("mode='INSTALLATION'", self.text)
        self.assertIn("mode='PHASE_B'", self.text)
        self.assertIn('changed==install', self.text)
        self.assertIn('self_path not in changed', self.text)
        self.assertIn('install_test not in changed', self.text)
        self.assertIn('installation-mode execution is installation evidence only', self.text)

    def test_exact_head_base_ancestry_and_phase_b_direct_child_are_bound(self):
        for token in (
            'test "$GITHUB_RUN_ATTEMPT" = 1',
            'test "$(git rev-parse HEAD)" = "$EVENT_HEAD"',
            'test "$(git merge-base "$EVENT_BASE" HEAD)" = "$EVENT_BASE"',
            'git rev-list --min-parents=2 "$EVENT_BASE"..HEAD',
            "if: env.MODE == 'PHASE_B'",
            'test "${#PARENTS[@]}" = 1',
            'test "${PARENTS[0]}" = "$EVENT_BASE"',
        ):
            self.assertIn(token, self.text)

    def test_both_executables_and_historical_regression_must_consume_canonical_parser(self):
        self.assertIn("publisher=Path(os.environ['PUBLISHER_PATH']).read_text()", self.text)
        self.assertIn("legacy_test=Path(os.environ['LEGACY_PARSER_TEST']).read_text()", self.text)
        self.assertIn("if science.count(import_token) != 2:", self.text)
        self.assertIn("if publisher.count(import_token) != 3:", self.text)
        self.assertIn("if legacy_test.count(import_token) != 1:", self.text)
        self.assertIn("for path_name,text in (('science',science),('publisher',publisher)):", self.text)
        self.assertIn("if 'def write_quiet_end_binding' in science or 'def write_quiet_end_binding' in publisher:", self.text)
        self.assertIn("if 'BEGIN_WRITE_QUIET_END_LINE_PARSER_V1' in legacy_test or 'expected three embedded parser blocks' in legacy_test:", self.text)

    def test_reviewer_owns_independent_semantic_corpus(self):
        for token in (
            'REVIEWER_OWNED_CANONICAL_PARSER_SEMANTIC_CORPUS_V1',
            "WRITE_QUIET_END | begin=999 | stage=legacy\\nbeginComment=123",
            '5471141095',
            '5562775627',
            '5467858336',
            '5467875147',
            'shared-evidence mismatch',
            'wrong-predecessor reference',
            '_write_quiet_end_records',
            'ordinary same-BEGIN duplicate',
        ):
            self.assertIn(token, self.text)
        self.assertIn('Run reviewer-owned immutable semantic corpus against actual parser', self.text)
        self.assertIn('reviewer-owned immutable semantic corpus independently tests actual parser semantics', self.text)

    def test_canonical_parser_is_statically_pure_before_import(self):
        for token in (
            'PARSER_STATIC_PURITY_GUARD_V1',
            'Statically prove canonical parser is pure before importing it',
            "allowed_import_roots={'re'}",
            "forbidden_names={'open','eval','exec','compile','__import__','input','breakpoint'}",
            "forbidden_attr_roots={'os','subprocess','socket','pathlib','requests','urllib','http','ftplib','paramiko','importlib','shutil','sys'}",
            'canonical parser module-level assignment must be literal/container only',
            'canonical parser has executable module-level statement',
        ):
            self.assertIn(token, self.text)
        self.assertLess(
            self.text.index('Statically prove canonical parser is pure before importing it'),
            self.text.index('Run reviewer-owned immutable semantic corpus against actual parser'),
        )

    def test_mutable_phase_b_tests_cannot_hide_runtime(self):
        self.assertIn('Statically refuse hidden runtime in mutable Phase-B parser tests', self.text)
        self.assertIn('forbidden_import_roots', self.text)
        for token in ('subprocess', 'requests', 'urllib', 'socket', 'http', 'ftplib', 'paramiko'):
            self.assertIn(token, self.text)
        for token in ("forbidden_calls={'eval','exec','compile','__import__'}", "node.func.attr in {'system','popen','spawnl','spawnlp','spawnv','spawnvp'}"):
            self.assertIn(token, self.text)

    def test_reviewer_contains_no_authorizing_or_science_runtime_surface(self):
        permissions = self.text.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        self.assertNotIn(': write', permissions)
        for token in ('gh workflow '+'run', 'gh api -X '+'POST', 'command -v '+'uvspec', 'rte_solver '+'mystic', 'mc_'+'photons 20000000'):
            self.assertNotIn(token, self.text)
        self.assertIn('no publisher invocation, WRITE_QUIET entry, dispatch, seed or ordinal allocation, solver, result opening, science authority', self.text)


if __name__ == '__main__':
    unittest.main()
