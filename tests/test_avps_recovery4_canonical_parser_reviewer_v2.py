from pathlib import Path
import ast
import os
import subprocess
import tempfile
import textwrap
import unittest

REVIEWER = Path('.github/workflows/avps-recovery4-canonical-parser-review-v2.yml')
PUBLISHER = Path('.github/workflows/avps-v2-recovery4-ordinal45-final-dispatch-publisher-v3.yml')


def _named_steps(text):
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith('      - name: ')]
    result = {}
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        name = lines[start].split('- name:', 1)[1].strip()
        chunk = lines[start:end]
        shell = None
        run_at = None
        for j, line in enumerate(chunk):
            if line.startswith('        shell: '):
                shell = line.split('shell:', 1)[1].strip()
            if line.startswith('        run: |'):
                run_at = j
                break
        if run_at is not None:
            result[name] = (shell, textwrap.dedent('\n'.join(chunk[run_at + 1:])))
    return result


def _is_workspace_insert(stmt):
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return False
    call = stmt.value
    func = call.func
    if not (
        isinstance(func, ast.Attribute)
        and func.attr == 'insert'
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == 'path'
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == 'sys'
    ):
        return False
    if len(call.args) != 2 or call.keywords:
        return False
    first, second = call.args
    if not (isinstance(first, ast.Constant) and first.value == 0):
        return False
    return (
        isinstance(second, ast.Subscript)
        and isinstance(second.value, ast.Attribute)
        and second.value.attr == 'environ'
        and isinstance(second.value.value, ast.Name)
        and second.value.value.id == 'os'
        and isinstance(second.slice, ast.Constant)
        and second.slice.value == 'GITHUB_WORKSPACE'
    )


def _run_shell(source, cwd, env):
    return subprocess.run(
        ['/bin/bash', '-c', source],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _git(cwd, *args, env=None):
    result = subprocess.run(
        ['git', *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def _write_commit(repo, path, content, message):
    target = Path(repo, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    _git(repo, 'add', path)
    _git(repo, 'commit', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD')


def _read_github_env(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
    return values


class CanonicalParserReviewerInstallationContract(unittest.TestCase):
    def setUp(self):
        proof = os.environ.get('REVIEWER_PROOF_PATH')
        self.text = Path(proof).read_text(encoding='utf-8') if proof else REVIEWER.read_text(encoding='utf-8')

    def test_pull_request_only_read_only(self):
        on = self.text.split('\non:\n', 1)[1].split('\npermissions:\n', 1)[0]
        self.assertIn('pull_request:', on)
        self.assertNotIn('workflow_dispatch:', on)
        permissions = self.text.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        for key in ('contents: read', 'actions: read', 'issues: read', 'pull-requests: read'):
            self.assertIn(key, permissions)
        self.assertNotIn(': write', permissions)
        self.assertIn('persist-credentials: false', self.text)

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

    def test_exact_head_base_and_fresh_phase_b_direct_child_are_bound(self):
        for token in (
            'test "$GITHUB_RUN_ATTEMPT" = 1',
            'test "$(git rev-parse HEAD)" = "$EVENT_HEAD"',
            'test "$(git merge-base "$EVENT_BASE" HEAD)" = "$EVENT_BASE"',
            'Bind installation ancestry as merge-free',
            'test -z "$(git rev-list --min-parents=2 "$EVENT_BASE"..HEAD)"',
            "if: env.MODE == 'PHASE_B'",
            'test "$EVENT_BASE" = "$LIVE_MAIN_SHA"',
            'test "${#PARENTS[@]}" = 1',
            'test "${PARENTS[0]}" = "$EVENT_BASE"',
        ):
            self.assertIn(token, self.text)

    def test_phase_b_reviewer_proof_bytes_are_bound_to_authoritative_live_main(self):
        for token in (
            'Bind reviewer proof bytes to authoritative live-main source',
            'EXPECTED_DEFAULT_BRANCH: main',
            'PHASE_A4_INSTALLED_MAIN: a35365a433d08b5d65ed2134187c814f476e5aad',
            'test "$EVENT_DEFAULT_BRANCH" = "$EXPECTED_DEFAULT_BRANCH"',
            'git_read ls-remote --symref origin HEAD',
            'git_read fetch --no-tags --force origin "$EXPECTED_DEFAULT_REF"',
            'test "$LIVE_MAIN_SHA" = "$ADVERTISED_DEFAULT_SHA"',
            'git_read ls-remote --heads origin "$EXPECTED_DEFAULT_REF"',
            'test "$CONFIRMED_LIVE_SHA" = "$LIVE_MAIN_SHA"',
            'git merge-base --is-ancestor "$HISTORICAL_PHASE_B_MERGE_BASE" "$LIVE_MAIN_SHA"',
            'git merge-base --is-ancestor "$PHASE_A4_INSTALLED_MAIN" "$LIVE_MAIN_SHA"',
            'git diff-tree -m --no-commit-id --name-only -r "$commit"',
            'actual-live-main-net-paths.txt',
            'actual-live-main-touched-paths.txt',
            'git show "$LIVE_MAIN_SHA:$SELF_PATH" > "$REVIEWER_PROOF_PATH"',
            'git show "$LIVE_MAIN_SHA:$INSTALL_TEST" > "$INSTALL_TEST_PROOF_PATH"',
            'REVIEWER_PROOF_PATH="$SELF_PATH"',
            'INSTALL_TEST_PROOF_PATH="$INSTALL_TEST"',
            "p=Path(os.environ['REVIEWER_PROOF_PATH']).read_text()",
            'python "$INSTALL_TEST_PROOF_PATH" CanonicalParserReviewerInstallationContract.test_phase_b_publisher_isolated_mode_import_wiring',
        ):
            self.assertIn(token, self.text)
        self.assertNotIn('git show "$EVENT_BASE:$SELF_PATH" > "$REVIEWER_PROOF_PATH"', self.text)
        self.assertNotIn("p=Path(os.environ['SELF_PATH']).read_text()", self.text)

        _, source = _named_steps(self.text)['Bind reviewer proof bytes to authoritative live-main source']
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_repo = root / 'source'
            source_repo.mkdir()
            _git(source_repo, 'init', '-q')
            _git(source_repo, 'config', 'user.name', 'AVPS test')
            _git(source_repo, 'config', 'user.email', 'avps-test@example.invalid')
            _git(source_repo, 'branch', '-M', 'main')
            Path(source_repo, 'reviewer.yml').write_text('stale reviewer bytes\n', encoding='utf-8')
            Path(source_repo, 'reviewer_test.py').write_text('stale reviewer test bytes\n', encoding='utf-8')
            _git(source_repo, 'add', 'reviewer.yml', 'reviewer_test.py')
            _git(source_repo, 'commit', '-m', 'historical stale reviewer')
            historical = _git(source_repo, 'rev-parse', 'HEAD')

            Path(source_repo, 'reviewer.yml').write_text('installed reviewer bytes\n', encoding='utf-8')
            Path(source_repo, 'reviewer_test.py').write_text('installed reviewer test bytes\n', encoding='utf-8')
            _git(source_repo, 'add', 'reviewer.yml', 'reviewer_test.py')
            _git(source_repo, 'commit', '-m', 'accepted reviewer install')
            installed = _git(source_repo, 'rev-parse', 'HEAD')

            remote = root / 'remote.git'
            _git(root, 'clone', '--bare', str(source_repo), str(remote))
            workspace = root / 'workspace'
            _git(root, 'clone', str(remote), str(workspace))
            _git(workspace, 'config', 'user.name', 'AVPS test')
            _git(workspace, 'config', 'user.email', 'avps-test@example.invalid')
            _git(workspace, 'checkout', '-q', '--detach', historical)
            _write_commit(workspace, 'phase.txt', 'phase bytes\n', 'phase semantic work')
            self.assertEqual(Path(workspace, 'reviewer.yml').read_text(encoding='utf-8'), 'stale reviewer bytes\n')

            runner_temp = workspace / 'runner-temp'
            runner_temp.mkdir()
            github_env = workspace / 'github-env.txt'
            base_env = os.environ.copy()
            base_env.pop('GITHUB_TOKEN', None)
            base_env.update({
                'MODE': 'PHASE_B',
                'EVENT_DEFAULT_BRANCH': 'main',
                'EXPECTED_DEFAULT_BRANCH': 'main',
                'HISTORICAL_PHASE_B_MERGE_BASE': historical,
                'PHASE_A4_INSTALLED_MAIN': installed,
                'SELF_PATH': 'reviewer.yml',
                'INSTALL_TEST': 'reviewer_test.py',
                'RUNNER_TEMP': str(runner_temp),
                'GITHUB_ENV': str(github_env),
            })
            result = _run_shell(source, workspace, base_env)
            self.assertEqual(result.returncode, 0, f'live-main proof binding failed: {result.stderr}\n{result.stdout}')
            values = _read_github_env(github_env)
            self.assertEqual(values['LIVE_MAIN_SHA'], installed)
            reviewer_proof = Path(values['REVIEWER_PROOF_PATH'])
            install_test_proof = Path(values['INSTALL_TEST_PROOF_PATH'])
            self.assertEqual(reviewer_proof.read_text(encoding='utf-8'), 'installed reviewer bytes\n')
            self.assertEqual(install_test_proof.read_text(encoding='utf-8'), 'installed reviewer test bytes\n')
            self.assertNotEqual(reviewer_proof.read_text(encoding='utf-8'), Path(workspace, 'reviewer.yml').read_text(encoding='utf-8'))

            wrong_event_default = base_env.copy()
            wrong_event_default['EVENT_DEFAULT_BRANCH'] = 'trunk'
            result = _run_shell(source, workspace, wrong_event_default)
            self.assertNotEqual(result.returncode, 0, 'wrong event default branch unexpectedly passed')

            _git(remote, 'symbolic-ref', 'HEAD', 'refs/heads/dev')
            result = _run_shell(source, workspace, base_env)
            self.assertNotEqual(result.returncode, 0, 'wrong remote default ref unexpectedly passed')
            _git(remote, 'symbolic-ref', 'HEAD', 'refs/heads/main')

            _git(source_repo, 'push', '--force', str(remote), f'{historical}:refs/heads/main')
            result = _run_shell(source, workspace, base_env)
            self.assertNotEqual(result.returncode, 0, 'stale historical proof source unexpectedly passed')
            _git(source_repo, 'push', '--force', str(remote), f'{installed}:refs/heads/main')

            historical_tree = _git(source_repo, 'show', '-s', '--format=%T', historical)
            unrelated = _git(source_repo, 'commit-tree', historical_tree, '-m', 'non-descendant live main')
            _git(source_repo, 'push', '--force', str(remote), f'{unrelated}:refs/heads/main')
            result = _run_shell(source, workspace, base_env)
            self.assertNotEqual(result.returncode, 0, 'non-descendant live main unexpectedly passed')
            _git(source_repo, 'push', '--force', str(remote), f'{installed}:refs/heads/main')

            _git(source_repo, 'checkout', '-q', 'main')
            self.assertEqual(_git(source_repo, 'rev-parse', 'HEAD'), installed)
            drift = _write_commit(source_repo, 'semantic.txt', 'forbidden drift\n', 'unrelated semantic drift')
            _git(source_repo, 'push', '--force', str(remote), f'{drift}:refs/heads/main')
            result = _run_shell(source, workspace, base_env)
            self.assertNotEqual(result.returncode, 0, 'unrelated live-main path drift unexpectedly passed')

            github_env.write_text('', encoding='utf-8')
            install_env = os.environ.copy()
            install_env.update({
                'MODE': 'INSTALLATION',
                'SELF_PATH': 'reviewer.yml',
                'INSTALL_TEST': 'reviewer_test.py',
                'RUNNER_TEMP': str(runner_temp),
                'GITHUB_ENV': str(github_env),
            })
            result = _run_shell(source, workspace, install_env)
            self.assertEqual(result.returncode, 0, f'installation proof binding failed: {result.stderr}')
            values = _read_github_env(github_env)
            self.assertEqual(values['LIVE_MAIN_SHA'], '')
            self.assertEqual(values['REVIEWER_PROOF_PATH'], 'reviewer.yml')
            self.assertEqual(values['INSTALL_TEST_PROOF_PATH'], 'reviewer_test.py')

    def test_preserved_identity_exception_is_exact_and_live_main_is_separate_from_historical_base(self):
        for token in (
            'PRESERVED_PHASE_B_REF: repair/avps-recovery4-canonical-write-quiet-parser-v1-20260909',
            'FROZEN_PHASE_B_HEAD: d591a3208b923f1a374b490266292ded4291ace0',
            'HISTORICAL_PHASE_B_MERGE_BASE: 4310e58c0c4ecb8ece305f0f27b47122c1febad6',
            'PHASE_A4_INSTALLED_MAIN: a35365a433d08b5d65ed2134187c814f476e5aad',
            'if [ "$EVENT_HEAD_REF" = "$PRESERVED_PHASE_B_REF" ]; then',
            'test "$(git merge-base "$EVENT_BASE" HEAD)" = "$HISTORICAL_PHASE_B_MERGE_BASE"',
            'git merge-base --is-ancestor "$HISTORICAL_PHASE_B_MERGE_BASE" "$EVENT_BASE"',
            'git merge-base --is-ancestor "$EVENT_BASE" "$LIVE_MAIN_SHA"',
            'CURRENT="$(git rev-parse HEAD)"',
            'while [ "$CURRENT" != "$FROZEN_PHASE_B_HEAD" ]; do',
            'test "${#PARENTS[@]}" = 2',
            'test -z "$MERGE"',
            'test "${PARENTS[0]}" = "$FROZEN_PHASE_B_HEAD"',
            'test "${PARENTS[1]}" = "$HISTORICAL_PHASE_B_MERGE_BASE"',
            'git merge-tree --write-tree "$FROZEN_PHASE_B_HEAD" "$HISTORICAL_PHASE_B_MERGE_BASE"',
            'test "$ACTUAL_TREE" = "$EXPECTED_TREE"',
        ):
            self.assertIn(token, self.text)
        self.assertNotIn('git rev-list --min-parents=2 "$FROZEN_PHASE_B_HEAD"..HEAD', self.text)
        self.assertNotIn('git show "$EVENT_BASE:$SELF_PATH" > "$REVIEWER_PROOF_PATH"', self.text)

    def test_phase_b_ancestry_modes_and_adverse_cases_execute(self):
        _, source = _named_steps(self.text)['Bind Phase-B ancestry with one exact preserved-identity exception']
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _git(repo, 'init', '-q')
            _git(repo, 'config', 'user.name', 'AVPS test')
            _git(repo, 'config', 'user.email', 'avps-test@example.invalid')
            root = _write_commit(repo, 'root.txt', 'root\n', 'root')

            _git(repo, 'checkout', '-q', '-b', 'frozen', root)
            frozen = _write_commit(repo, 'frozen.txt', 'frozen\n', 'frozen')

            _git(repo, 'checkout', '-q', '--detach', root)
            historical = _write_commit(repo, 'historical.txt', 'historical\n', 'historical')

            merge_tree = _git(repo, 'merge-tree', '--write-tree', frozen, historical)
            phase_merge = _git(repo, 'commit-tree', merge_tree, '-p', frozen, '-p', historical, '-m', 'phase merge')
            _git(repo, 'checkout', '-q', '--detach', phase_merge)
            phase_head = _write_commit(repo, 'phase.txt', 'phase\n', 'phase linear')

            _git(repo, 'checkout', '-q', '--detach', historical)
            live_main = _write_commit(repo, 'reviewer.yml', 'installed reviewer\n', 'installed reviewer')
            _git(repo, 'checkout', '-q', '--detach', live_main)
            ordinary_head = _write_commit(repo, 'ordinary.txt', 'ordinary\n', 'ordinary phase b')

            base_env = os.environ.copy()
            base_env.update({
                'PRESERVED_PHASE_B_REF': 'preserved/phase-b',
                'FROZEN_PHASE_B_HEAD': frozen,
                'HISTORICAL_PHASE_B_MERGE_BASE': historical,
            })

            ordinary = base_env.copy()
            ordinary.update({'EVENT_BASE': live_main, 'EVENT_HEAD_REF': 'fresh/phase-b', 'LIVE_MAIN_SHA': live_main})
            result = _run_shell(source, repo, ordinary)
            self.assertEqual(result.returncode, 0, f'ordinary live-main direct-child mode failed: {result.stderr}')

            ordinary_wrong_live = ordinary.copy()
            ordinary_wrong_live['LIVE_MAIN_SHA'] = historical
            result = _run_shell(source, repo, ordinary_wrong_live)
            self.assertNotEqual(result.returncode, 0, 'ordinary mode with non-live event base unexpectedly passed')

            _git(repo, 'checkout', '-q', '--detach', phase_head)
            preserved = base_env.copy()
            preserved.update({'EVENT_BASE': historical, 'EVENT_HEAD_REF': 'preserved/phase-b', 'LIVE_MAIN_SHA': live_main})
            result = _run_shell(source, repo, preserved)
            self.assertEqual(result.returncode, 0, f'preserved live-main-separated mode failed: {result.stderr}')

            wrong_base = preserved.copy()
            wrong_base['HISTORICAL_PHASE_B_MERGE_BASE'] = root
            result = _run_shell(source, repo, wrong_base)
            self.assertNotEqual(result.returncode, 0, 'wrong historical base unexpectedly passed')

            _git(repo, 'checkout', '-q', '--detach', historical)
            other_event_base = _write_commit(repo, 'other.txt', 'other\n', 'other event base')
            _git(repo, 'checkout', '-q', '--detach', phase_head)
            event_base_not_in_live = preserved.copy()
            event_base_not_in_live['EVENT_BASE'] = other_event_base
            result = _run_shell(source, repo, event_base_not_in_live)
            self.assertNotEqual(result.returncode, 0, 'event base not ancestral to bound live main unexpectedly passed')

            phase_tree = _git(repo, 'show', '-s', '--format=%T', phase_head)
            extra_merge = _git(repo, 'commit-tree', phase_tree, '-p', phase_head, '-p', historical, '-m', 'extra phase merge')
            _git(repo, 'checkout', '-q', '--detach', extra_merge)
            result = _run_shell(source, repo, preserved)
            self.assertNotEqual(result.returncode, 0, 'extra Phase-B merge unexpectedly passed')

            _git(repo, 'checkout', '-q', '--detach', historical)
            replay = _write_commit(repo, 'replay.txt', 'replay\n', 'replayed identity')
            replay_env = preserved.copy()
            result = _run_shell(source, repo, replay_env)
            self.assertNotEqual(result.returncode, 0, 'Phase-B replay not descending from frozen identity unexpectedly passed')

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
        self.assertIn('reviewer-owned immutable semantic corpus and executable wiring checks execute before any mutable Phase-B test', self.text)

    def test_canonical_parser_is_statically_pure_before_import(self):
        for token in (
            'PARSER_STATIC_PURITY_GUARD_V1',
            'Statically prove canonical parser is pure before importing it',
            "allowed_import_roots={'re'}",
            "forbidden_names={'open','eval','exec','compile','__import__','input','breakpoint','globals','locals','vars','getattr','setattr','delattr'}",
            "forbidden_attr_roots={'os','subprocess','socket','pathlib','requests','urllib','http','ftplib','paramiko','importlib','shutil','sys'}",
            'ast.literal_eval(stmt.value)',
            'canonical parser module-level assignment must be literal/container only',
            'canonical parser annotations are forbidden',
            'canonical parser dunder/dynamic namespace access forbidden',
            'canonical parser has executable module-level statement',
        ):
            self.assertIn(token, self.text)
        self.assertLess(
            self.text.index('Statically prove canonical parser is pure before importing it'),
            self.text.index('Run reviewer-owned immutable semantic corpus against actual parser'),
        )

    def test_mutable_phase_b_tests_cannot_execute_or_spoof(self):
        for token in (
            'MUTABLE_TEST_NON_SPOOF_GUARD_V1',
            'Statically prove mutable Phase-B tests cannot execute runtime or spoof later checks',
            "allowed_import_roots={'pathlib','re','textwrap','unittest','scripts'}",
            "allowed_scripts_module='scripts.avps_write_quiet_parser_v1'",
            "forbidden_calls={'open','eval','exec','compile','__import__','input','breakpoint','globals','locals','vars','getattr','setattr','delattr'}",
            "forbidden_methods={'open','write_text','write_bytes','touch','unlink','rename','replace','mkdir','rmdir','chmod','symlink_to','hardlink_to'}",
            'Phase-B test imports non-whitelisted module',
            'Phase-B test imports noncanonical project module',
            'Phase-B test mutating/dynamic attribute forbidden',
        ):
            self.assertIn(token, self.text)
        static_index=self.text.index('Statically prove mutable Phase-B tests cannot execute runtime or spoof later checks')
        semantic_index=self.text.index('Run reviewer-owned immutable semantic corpus against actual parser')
        isolated_index=self.text.index('Run reviewer-owned isolated-mode publisher wiring and importability proof')
        wiring_index=self.text.index('Verify actual executable-chain wiring before mutable tests execute')
        mutable_index=self.text.index('Run mutable parser regressions only after immutable semantic and wiring checks')
        self.assertLess(static_index, semantic_index)
        self.assertLess(semantic_index, isolated_index)
        self.assertLess(isolated_index, wiring_index)
        self.assertLess(wiring_index, mutable_index)

    def test_mutable_regression_runner_collects_executes_and_fails_closed(self):
        _, source = _named_steps(self.text)['Run mutable parser regressions only after immutable semantic and wiring checks']
        self.assertIn('python -m unittest -v "$PARSER_TEST"', source)
        self.assertIn('python -m unittest -v "$LEGACY_PARSER_TEST"', source)
        self.assertEqual(source.count("grep -Eq '^Ran [1-9][0-9]* tests? in '"), 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'scripts').mkdir()
            (root / 'tests').mkdir()
            (root / 'scripts' / 'helper.py').write_text('VALUE = 7\n', encoding='utf-8')
            one = root / 'tests' / 'test_one.py'
            two = root / 'tests' / 'test_two.py'
            one.write_text(
                "import os, unittest\nfrom pathlib import Path\nfrom scripts.helper import VALUE\nclass T(unittest.TestCase):\n    def test_runs(self):\n        self.assertEqual(VALUE, 7)\n        Path(os.environ['MARK_ONE']).write_text('ran')\n",
                encoding='utf-8',
            )
            two.write_text(
                "import os, unittest\nfrom pathlib import Path\nfrom scripts.helper import VALUE\nclass T(unittest.TestCase):\n    def test_runs(self):\n        self.assertEqual(VALUE, 7)\n        Path(os.environ['MARK_TWO']).write_text('ran')\n",
                encoding='utf-8',
            )
            env = os.environ.copy()
            env.update({
                'PARSER_TEST': 'tests/test_one.py',
                'LEGACY_PARSER_TEST': 'tests/test_two.py',
                'RUNNER_TEMP': str(root / 'runner-temp'),
                'MARK_ONE': str(root / 'one.marker'),
                'MARK_TWO': str(root / 'two.marker'),
            })
            Path(env['RUNNER_TEMP']).mkdir()
            result = _run_shell(source, root, env)
            self.assertEqual(result.returncode, 0, f'real unittest runner failed: {result.stderr}\n{result.stdout}')
            self.assertTrue(Path(env['MARK_ONE']).exists(), 'first module test body did not execute')
            self.assertTrue(Path(env['MARK_TWO']).exists(), 'second module test body did not execute')

            one.write_text('import unittest\n', encoding='utf-8')
            result = _run_shell(source, root, env)
            self.assertNotEqual(result.returncode, 0, 'zero-test module unexpectedly passed')

            one.write_text('this is not valid python\n', encoding='utf-8')
            result = _run_shell(source, root, env)
            self.assertNotEqual(result.returncode, 0, 'unimportable module unexpectedly passed')

            one.write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_fails(self):\n        self.fail('expected')\n",
                encoding='utf-8',
            )
            result = _run_shell(source, root, env)
            self.assertNotEqual(result.returncode, 0, 'failing collected test unexpectedly passed')

    def test_phase_b_publisher_isolated_mode_import_wiring(self):
        for token in (
            'REVIEWER_OWNED_ISOLATED_IMPORT_FIXTURE_V1',
            'Run reviewer-owned isolated-mode publisher wiring and importability proof',
            'CanonicalParserReviewerInstallationContract.test_phase_b_publisher_isolated_mode_import_wiring',
            "sys.path.insert(0, os.environ['GITHUB_WORKSPACE'])",
            '/usr/bin/python3 -I -S',
            'PYTHONPATH',
        ):
            self.assertIn(token, self.text)
        semantic_index=self.text.index('Run reviewer-owned immutable semantic corpus against actual parser')
        isolated_index=self.text.index('Run reviewer-owned isolated-mode publisher wiring and importability proof')
        wiring_index=self.text.index('Verify actual executable-chain wiring before mutable tests execute')
        self.assertLess(semantic_index, isolated_index)
        self.assertLess(isolated_index, wiring_index)

        if os.environ.get('MODE') != 'PHASE_B':
            return

        publisher = PUBLISHER.read_text(encoding='utf-8')
        steps = _named_steps(publisher)
        expected = (
            'Fresh repository-global candidate-seed recheck and one-use guard',
            'Protected dispatch consumption and same-BEGIN science binding',
            'Close exact fence only after science preflight guard terminal',
        )
        canonical_module = 'scripts.avps_write_quiet_parser_v1'
        canonical_names = {'record_write_quiet_end', 'is_write_quiet_begin'}
        for name in expected:
            self.assertIn(name, steps, f'missing publisher callsite: {name}')
            shell, source = steps[name]
            self.assertEqual(shell, '/usr/bin/python3 -I -S {0}', f'publisher shell drift: {name}')
            tree = ast.parse(source, filename=f'publisher step {name}')
            imports = [
                (index, stmt)
                for index, stmt in enumerate(tree.body)
                if isinstance(stmt, ast.ImportFrom) and stmt.module == canonical_module
            ]
            self.assertEqual(len(imports), 1, f'canonical import cardinality drift: {name}')
            import_index, import_stmt = imports[0]
            self.assertGreater(import_index, 0, f'canonical import lacks preceding workspace binding: {name}')
            self.assertTrue(_is_workspace_insert(tree.body[import_index - 1]), f'workspace binding not immediately before canonical import: {name}')

            imported_os = False
            imported_sys = False
            for stmt in tree.body[:import_index]:
                if isinstance(stmt, ast.Import):
                    for alias in stmt.names:
                        if alias.asname is None and alias.name == 'os':
                            imported_os = True
                        if alias.asname is None and alias.name == 'sys':
                            imported_sys = True
            self.assertTrue(imported_os and imported_sys, f'publisher callsite must import os and sys before workspace binding: {name}')

            imported = {alias.name for alias in import_stmt.names if alias.asname is None}
            self.assertTrue(canonical_names.issubset(imported), f'publisher callsite missing canonical API imports: {name}')
            calls = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertTrue(canonical_names.issubset(calls), f'publisher callsite does not invoke canonical API: {name}')
            local_defs = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            self.assertTrue(canonical_names.isdisjoint(local_defs), f'publisher callsite shadows canonical API locally: {name}')

        repo_root = Path(os.environ['GITHUB_WORKSPACE']).resolve()
        self.assertEqual(repo_root, Path.cwd().resolve(), 'reviewer workspace/cwd drift')
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        unbound = subprocess.run(
            ['/usr/bin/python3', '-I', '-S', '-c', 'from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin'],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(unbound.returncode, 0, 'unbound isolated-mode repo-local import unexpectedly succeeded')
        self.assertIn("No module named 'scripts'", unbound.stderr)
        bound_code = (
            "import os,sys; "
            "sys.path.insert(0, os.environ['GITHUB_WORKSPACE']); "
            "from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin; "
            "assert callable(is_write_quiet_begin)"
        )
        bound = subprocess.run(
            ['/usr/bin/python3', '-I', '-S', '-c', bound_code],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(bound.returncode, 0, f'workspace-bound isolated-mode canonical import failed: {bound.stderr}')

    def test_reviewer_contains_no_authorizing_or_science_runtime_surface(self):
        permissions = self.text.split('\npermissions:\n', 1)[1].split('\nconcurrency:\n', 1)[0]
        self.assertNotIn(': write', permissions)
        for token in ('gh workflow '+'run', 'gh api -X '+'POST', 'git '+'push', 'command -v '+'uvspec', 'rte_solver '+'mystic', 'mc_'+'photons 20000000'):
            self.assertNotIn(token, self.text)
        self.assertIn('no publisher invocation, WRITE_QUIET entry, dispatch, seed or ordinal allocation, solver, result opening, science authority', self.text)


if __name__ == '__main__':
    unittest.main()
