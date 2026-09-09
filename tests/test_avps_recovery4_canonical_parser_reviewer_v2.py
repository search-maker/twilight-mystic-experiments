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

    def test_installation_and_phase_b_are_direct_children_and_cannot_self_certify(self):
        for token in (
            "mode='INSTALLATION'",
            "mode='PHASE_B'",
            'changed==install',
            'self_path not in changed',
            'install_test not in changed',
            'test "${#PARENTS[@]}" = 1',
            'test "${PARENTS[0]}" = "$EVENT_BASE"',
            'installation-mode execution is installation evidence only',
        ):
            self.assertIn(token, self.text)

    def test_exact_event_head_base_and_attempt_are_bound(self):
        for token in (
            'test "$GITHUB_RUN_ATTEMPT" = 1',
            'test "$(git rev-parse HEAD)" = "$EVENT_HEAD"',
            'test "$(git merge-base "$EVENT_BASE" HEAD)" = "$EVENT_BASE"',
            'git rev-list --min-parents=2 "$EVENT_BASE"..HEAD',
        ):
            self.assertIn(token, self.text)

    def test_parser_purity_is_exact_module_fail_closed_and_self_tested(self):
        for token in (
            'PARSER_STATIC_PURITY_GUARD_V2',
            'REVIEWER_OWNED_PURITY_NEGATIVE_MATRIX_V2',
            "ALLOWED_MODULES={'re'}",
            'import module not exactly allowlisted',
            'from-import module not exactly allowlisted',
            'star import forbidden',
            'nested import forbidden',
            'multi-hop qualified reference forbidden',
            'dynamic/multi-hop call target forbidden',
            "'urllib.parse.urlopen'",
            "'http.client'",
            "'requests.sessions'",
            "'pathlib.Path.read_text'",
            "'os.environ'",
            "'os.system'",
            "'os.popen'",
            "'subprocess'",
            "'importlib'",
            "'tempfile'",
            "'socket'",
            "'time'",
            "'datetime'",
            "'random'",
            "'secrets'",
            "'urllib alias'",
            "'os alias'",
            "'open'",
            "'eval'",
            "'exec'",
            "'compile'",
            "'__import__'",
            "'star import'",
            "analyze_source(safe,'safe-positive')",
        ):
            self.assertIn(token, self.text)
        self.assertNotIn("allowed_import_roots={'re'}", self.text)
        self.assertLess(
            self.text.index('Statically prove canonical parser purity and run immutable hostile matrix'),
            self.text.index('Run reviewer-owned immutable semantic corpus against actual parser'),
        )

    def test_mutable_tests_are_exact_module_whitelisted_before_execution(self):
        for token in (
            'MUTABLE_TEST_NON_SPOOF_GUARD_V2',
            "allowed_modules={'pathlib','re','textwrap','unittest','scripts.avps_write_quiet_parser_v1'}",
            'Phase-B test imports non-whitelisted module',
            'Phase-B test star import forbidden',
            'Phase-B test mutating/runtime attribute forbidden',
        ):
            self.assertIn(token, self.text)
        static_index=self.text.index('Statically prove mutable Phase-B tests cannot execute runtime or spoof later checks')
        semantic_index=self.text.index('Run reviewer-owned immutable semantic corpus against actual parser')
        wiring_index=self.text.index('Verify actual executable-chain wiring and isolated publisher bindings before mutable tests')
        mutable_index=self.text.index('Run mutable parser regressions only after immutable semantic and wiring checks')
        self.assertLess(static_index, semantic_index)
        self.assertLess(semantic_index, wiring_index)
        self.assertLess(wiring_index, mutable_index)

    def test_reviewer_owned_semantic_corpus_has_exact_duplicate_and_supersession_contracts(self):
        for token in (
            'REVIEWER_OWNED_CANONICAL_PARSER_SEMANTIC_CORPUS_V2',
            "WRITE_QUIET_END | begin=999 | stage=legacy\\nbeginComment=123",
            '5471141095',
            '5562775627',
            '5467858336',
            '5467875147',
            'shared-evidence mismatch',
            'wrong-predecessor reference',
            '_write_quiet_end_records',
            'UNAUTHORIZED_DUPLICATE_MATCHING_SHARED_EVIDENCE_V1',
            'TEST_VALID_SHARED_EVIDENCE',
            'unauthorized matching-evidence same-BEGIN duplicate',
        ):
            self.assertIn(token, self.text)

    def test_both_executables_and_historical_regression_consume_canonical_parser(self):
        self.assertIn("if science.count(import_token) != 2", self.text)
        self.assertIn("if publisher.count(import_token) != 3", self.text)
        self.assertIn("if legacy_test.count(import_token) != 1", self.text)
        self.assertIn("for path_name,text in (('science',science),('publisher',publisher))", self.text)
        self.assertIn("if 'def write_quiet_end_binding' in science or 'def write_quiet_end_binding' in publisher", self.text)
        self.assertIn("if 'BEGIN_WRITE_QUIET_END_LINE_PARSER_V1' in legacy_test", self.text)

    def test_publisher_isolated_mode_binding_is_mandatory_and_independently_proven(self):
        for token in (
            'ISOLATED_MODE_IMPORTABILITY_PROOF_V1',
            'shell: /usr/bin/python3 -I -S {0}',
            "sys.path.insert(0, os.environ['GITHUB_WORKSPACE'])",
            'PYTHONPATH="$ROOT" /usr/bin/python3 -I -S -c',
            'test "$UNBOUND_RC" -ne 0',
            "iso='shell: /usr/bin/python3 -I -S {0}'",
            "if publisher.count(iso)!=3",
            "if 'PYTHONPATH' in seg",
            'binding_re=re.compile',
            'lacks exactly one explicit GITHUB_WORKSPACE sys.path binding immediately before canonical import',
            'does not invoke an imported canonical API',
        ):
            self.assertIn(token, self.text)
        self.assertIn("import os,sys[ \\t]*\\n[ \\t]*sys\\.path\\.insert", self.text)

    def test_reviewer_contains_no_authorizing_or_science_runtime_surface(self):
        permissions = self.text.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        self.assertNotIn(': write', permissions)
        for token in ('gh workflow '+'run', 'gh api -X '+'POST', 'command -v '+'uvspec', 'rte_solver '+'mystic', 'mc_'+'photons 20000000'):
            self.assertNotIn(token, self.text)
        self.assertIn('no publisher invocation, WRITE_QUIET entry, dispatch, seed or ordinal allocation, solver, result opening, science authority', self.text)


if __name__ == '__main__':
    unittest.main()
