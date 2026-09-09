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


def _git_result(cwd, *args, env=None):
    return subprocess.run(
        ['git', *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


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
        for token in (
            "mode='INSTALLATION'", "mode='PHASE_B'", 'changed==install',
            'self_path not in changed', 'install_test not in changed',
            'installation-mode execution is installation evidence only',
        ):
            self.assertIn(token, self.text)

    def test_exact_head_base_and_fresh_phase_b_direct_child_are_bound(self):
        for token in (
            'test "$GITHUB_RUN_ATTEMPT" = 1',
            'test "$(git rev-parse HEAD)" = "$EVENT_HEAD"',
            'test "$(git merge-base "$EVENT_BASE" HEAD)" = "$EVENT_BASE"',
            'Bind installation ancestry as merge-free',
            'test -z "$(git rev-list --min-parents=2 "$EVENT_BASE"..HEAD)"',
            "if: env.MODE == 'PHASE_B'",
            'test "$EVENT_BASE" = "$EFFECTIVE_EVENT_BASE"',
            'test "${#PARENTS[@]}" = 1',
            'test "${PARENTS[0]}" = "$EVENT_BASE"',
        ):
            self.assertIn(token, self.text)

    def test_phase_b_reviewer_proof_bytes_are_event_bound_to_effective_base(self):
        for token in (
            'Bind reviewer proof bytes to event-bound effective base',
            'EXPECTED_DEFAULT_BRANCH: main',
            'PHASE_A4_INSTALLED_MAIN: a35365a433d08b5d65ed2134187c814f476e5aad',
            'EVENT_MERGE_SHA: ${{ github.sha }}',
            'EVENT_NUMBER: ${{ github.event.pull_request.number }}',
            'test "$EVENT_DEFAULT_BRANCH" = "$EXPECTED_DEFAULT_BRANCH"',
            'test "$EVENT_BASE_REF" = "$EXPECTED_DEFAULT_BRANCH"',
            'MERGE_REF="refs/pull/$EVENT_NUMBER/merge"',
            'git_read fetch --no-tags --force origin "$MERGE_REF"',
            'test "$FETCHED_MERGE_SHA" = "$EVENT_MERGE_SHA"',
            'mapfile -t MERGE_PARENTS',
            'test "${#MERGE_PARENTS[@]}" = 2',
            'EFFECTIVE_EVENT_BASE="${MERGE_PARENTS[0]}"',
            'test "${MERGE_PARENTS[1]}" = "$EVENT_HEAD"',
            'git merge-base --is-ancestor "$HISTORICAL_PHASE_B_MERGE_BASE" "$EFFECTIVE_EVENT_BASE"',
            'git merge-base --is-ancestor "$PHASE_A4_INSTALLED_MAIN" "$EFFECTIVE_EVENT_BASE"',
            'actual-effective-base-net-paths.txt',
            'actual-effective-base-touched-paths.txt',
            'git diff-tree -m --no-commit-id --name-only -r "$commit"',
            'git show "$EFFECTIVE_EVENT_BASE:$SELF_PATH" > "$REVIEWER_PROOF_PATH"',
            'git show "$EFFECTIVE_EVENT_BASE:$INSTALL_TEST" > "$INSTALL_TEST_PROOF_PATH"',
            'REVIEWER_PROOF_PATH="$SELF_PATH"',
            'INSTALL_TEST_PROOF_PATH="$INSTALL_TEST"',
            "p=Path(os.environ['REVIEWER_PROOF_PATH']).read_text()",
            'python "$INSTALL_TEST_PROOF_PATH" CanonicalParserReviewerInstallationContract.test_phase_b_publisher_isolated_mode_import_wiring',
        ):
            self.assertIn(token, self.text)
        _, source = _named_steps(self.text)['Bind reviewer proof bytes to event-bound effective base']
        for forbidden in (
            'git show "$EVENT_BASE:$SELF_PATH" > "$REVIEWER_PROOF_PATH"',
            'git show "$EVENT_MERGE_SHA:$SELF_PATH" > "$REVIEWER_PROOF_PATH"',
            'git show "$EVENT_HEAD:$SELF_PATH" > "$REVIEWER_PROOF_PATH"',
            'LIVE_MAIN_SHA', 'ls-remote --symref origin HEAD', 'ls-remote --heads origin',
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("p=Path(os.environ['SELF_PATH']).read_text()", self.text)

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

            _git(source_repo, 'checkout', '-q', '-b', 'phase', historical)
            phase_head = _write_commit(source_repo, 'phase.txt', 'phase bytes\n', 'phase semantic work')
            _git(source_repo, 'checkout', '-q', 'main')

            merge_tree = _git(source_repo, 'merge-tree', '--write-tree', installed, phase_head)
            synthetic = _git(source_repo, 'commit-tree', merge_tree, '-p', installed, '-p', phase_head, '-m', 'synthetic pr merge')

            remote = root / 'remote.git'
            _git(root, 'clone', '--bare', str(source_repo), str(remote))
            _git(source_repo, 'push', str(remote), f'{synthetic}:refs/pull/1015/merge')
            workspace = root / 'workspace'
            _git(root, 'clone', str(remote), str(workspace))
            _git(workspace, 'config', 'user.name', 'AVPS test')
            _git(workspace, 'config', 'user.email', 'avps-test@example.invalid')
            _git(workspace, 'checkout', '-q', '--detach', phase_head)
            self.assertEqual(Path(workspace, 'reviewer.yml').read_text(encoding='utf-8'), 'stale reviewer bytes\n')

            runner_temp = workspace / 'runner-temp'
            runner_temp.mkdir()
            github_env = workspace / 'github-env.txt'
            base_env = os.environ.copy()
            base_env.pop('GITHUB_TOKEN', None)
            base_env.update({
                'MODE': 'PHASE_B',
                'EVENT_DEFAULT_BRANCH': 'main',
                'EVENT_BASE_REF': 'main',
                'EVENT_HEAD': phase_head,
                'EVENT_NUMBER': '1015',
                'EVENT_MERGE_SHA': synthetic,
                'EXPECTED_DEFAULT_BRANCH': 'main',
                'HISTORICAL_PHASE_B_MERGE_BASE': historical,
                'PHASE_A4_INSTALLED_MAIN': installed,
                'SELF_PATH': 'reviewer.yml',
                'INSTALL_TEST': 'reviewer_test.py',
                'RUNNER_TEMP': str(runner_temp),
                'GITHUB_ENV': str(github_env),
            })
            result = _run_shell(source, workspace, base_env)
            self.assertEqual(result.returncode, 0, f'event-bound effective-base proof failed: {result.stderr}\n{result.stdout}')
            values = _read_github_env(github_env)
            self.assertEqual(values['EFFECTIVE_EVENT_BASE'], installed)
            reviewer_proof = Path(values['REVIEWER_PROOF_PATH'])
            install_test_proof = Path(values['INSTALL_TEST_PROOF_PATH'])
            self.assertEqual(reviewer_proof.read_text(encoding='utf-8'), 'installed reviewer bytes\n')
            self.assertEqual(install_test_proof.read_text(encoding='utf-8'), 'installed reviewer test bytes\n')
            self.assertNotEqual(reviewer_proof.read_text(encoding='utf-8'), Path(workspace, 'reviewer.yml').read_text(encoding='utf-8'))

            wrong_default = base_env.copy(); wrong_default['EVENT_DEFAULT_BRANCH'] = 'trunk'
            self.assertNotEqual(_run_shell(source, workspace, wrong_default).returncode, 0)
            wrong_base_ref = base_env.copy(); wrong_base_ref['EVENT_BASE_REF'] = 'trunk'
            self.assertNotEqual(_run_shell(source, workspace, wrong_base_ref).returncode, 0)

            wrong_second = _git(source_repo, 'commit-tree', merge_tree, '-p', installed, '-p', historical, '-m', 'wrong second')
            _git(source_repo, 'push', '--force', str(remote), f'{wrong_second}:refs/pull/1015/merge')
            wrong_second_env = base_env.copy(); wrong_second_env['EVENT_MERGE_SHA'] = wrong_second
            self.assertNotEqual(_run_shell(source, workspace, wrong_second_env).returncode, 0)

            one_parent = _git(source_repo, 'commit-tree', merge_tree, '-p', installed, '-m', 'one parent')
            _git(source_repo, 'push', '--force', str(remote), f'{one_parent}:refs/pull/1015/merge')
            one_env = base_env.copy(); one_env['EVENT_MERGE_SHA'] = one_parent
            self.assertNotEqual(_run_shell(source, workspace, one_env).returncode, 0)
            three_parent = _git(source_repo, 'commit-tree', merge_tree, '-p', installed, '-p', phase_head, '-p', historical, '-m', 'three parents')
            _git(source_repo, 'push', '--force', str(remote), f'{three_parent}:refs/pull/1015/merge')
            three_env = base_env.copy(); three_env['EVENT_MERGE_SHA'] = three_parent
            self.assertNotEqual(_run_shell(source, workspace, three_env).returncode, 0)

            _git(source_repo, 'push', '--force', str(remote), f'{synthetic}:refs/pull/1015/merge')
            mismatch = base_env.copy(); mismatch['EVENT_MERGE_SHA'] = wrong_second
            self.assertNotEqual(_run_shell(source, workspace, mismatch).returncode, 0)
            _git(remote, 'update-ref', '-d', 'refs/pull/1015/merge')
            self.assertNotEqual(_run_shell(source, workspace, base_env).returncode, 0, 'moving main substituted for missing event snapshot')

            stale_tree = _git(source_repo, 'merge-tree', '--write-tree', historical, phase_head)
            stale_merge = _git(source_repo, 'commit-tree', stale_tree, '-p', historical, '-p', phase_head, '-m', 'stale base synthetic')
            _git(source_repo, 'push', '--force', str(remote), f'{stale_merge}:refs/pull/1015/merge')
            stale_env = base_env.copy(); stale_env['EVENT_MERGE_SHA'] = stale_merge
            self.assertNotEqual(_run_shell(source, workspace, stale_env).returncode, 0)

            historical_tree = _git(source_repo, 'show', '-s', '--format=%T', historical)
            orphan = _git(source_repo, 'commit-tree', historical_tree, '-m', 'orphan effective base')
            orphan_merge = _git(source_repo, 'commit-tree', merge_tree, '-p', orphan, '-p', phase_head, '-m', 'orphan-base synthetic')
            _git(source_repo, 'push', '--force', str(remote), f'{orphan_merge}:refs/pull/1015/merge')
            orphan_env = base_env.copy(); orphan_env['EVENT_MERGE_SHA'] = orphan_merge
            self.assertNotEqual(_run_shell(source, workspace, orphan_env).returncode, 0)

            _git(source_repo, 'checkout', '-q', '--detach', installed)
            drift = _write_commit(source_repo, 'semantic.txt', 'forbidden drift\n', 'unrelated semantic drift')
            drift_tree = _git(source_repo, 'merge-tree', '--write-tree', drift, phase_head)
            drift_merge = _git(source_repo, 'commit-tree', drift_tree, '-p', drift, '-p', phase_head, '-m', 'drift-base synthetic')
            _git(source_repo, 'push', '--force', str(remote), f'{drift_merge}:refs/pull/1015/merge')
            drift_env = base_env.copy(); drift_env['EVENT_MERGE_SHA'] = drift_merge
            self.assertNotEqual(_run_shell(source, workspace, drift_env).returncode, 0)

            github_env.write_text('', encoding='utf-8')
            install_env = os.environ.copy()
            install_env.update({
                'MODE': 'INSTALLATION', 'SELF_PATH': 'reviewer.yml', 'INSTALL_TEST': 'reviewer_test.py',
                'RUNNER_TEMP': str(runner_temp), 'GITHUB_ENV': str(github_env),
            })
            result = _run_shell(source, workspace, install_env)
            self.assertEqual(result.returncode, 0, f'installation proof binding failed: {result.stderr}')
            values = _read_github_env(github_env)
            self.assertEqual(values['EFFECTIVE_EVENT_BASE'], '')
            self.assertEqual(values['REVIEWER_PROOF_PATH'], 'reviewer.yml')
            self.assertEqual(values['INSTALL_TEST_PROOF_PATH'], 'reviewer_test.py')

    def test_preserved_identity_exception_is_exact_and_effective_base_is_separate_from_historical_base(self):
        for token in (
            'PRESERVED_PHASE_B_REF: repair/avps-recovery4-canonical-write-quiet-parser-v1-20260909',
            'FROZEN_PHASE_B_HEAD: d591a3208b923f1a374b490266292ded4291ace0',
            'HISTORICAL_PHASE_B_MERGE_BASE: 4310e58c0c4ecb8ece305f0f27b47122c1febad6',
            'PHASE_A4_INSTALLED_MAIN: a35365a433d08b5d65ed2134187c814f476e5aad',
            'if [ "$EVENT_HEAD_REF" = "$PRESERVED_PHASE_B_REF" ]; then',
            'test "$(git merge-base "$EVENT_BASE" HEAD)" = "$HISTORICAL_PHASE_B_MERGE_BASE"',
            'git merge-base --is-ancestor "$HISTORICAL_PHASE_B_MERGE_BASE" "$EVENT_BASE"',
            'git merge-base --is-ancestor "$EVENT_BASE" "$EFFECTIVE_EVENT_BASE"',
            'CURRENT="$(git rev-parse HEAD)"',
            'while [ "$CURRENT" != "$FROZEN_PHASE_B_HEAD" ]; do',
            'test "${#PARENTS[@]}" = 2', 'test -z "$MERGE"',
            'test "${PARENTS[0]}" = "$FROZEN_PHASE_B_HEAD"',
            'test "${PARENTS[1]}" = "$HISTORICAL_PHASE_B_MERGE_BASE"',
            'git merge-tree --write-tree "$FROZEN_PHASE_B_HEAD" "$HISTORICAL_PHASE_B_MERGE_BASE"',
            'test "$ACTUAL_TREE" = "$EXPECTED_TREE"',
        ):
            self.assertIn(token, self.text)
        self.assertNotIn('git rev-list --min-parents=2 "$FROZEN_PHASE_B_HEAD"..HEAD', self.text)

    def test_phase_b_ancestry_modes_and_adverse_cases_execute(self):
        _, source = _named_steps(self.text)['Bind Phase-B ancestry with one exact preserved-identity exception']
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _git(repo, 'init', '-q'); _git(repo, 'config', 'user.name', 'AVPS test'); _git(repo, 'config', 'user.email', 'avps-test@example.invalid')
            root = _write_commit(repo, 'root.txt', 'root\n', 'root')
            _git(repo, 'checkout', '-q', '-b', 'frozen', root); frozen = _write_commit(repo, 'frozen.txt', 'frozen\n', 'frozen')
            _git(repo, 'checkout', '-q', '--detach', root); historical = _write_commit(repo, 'historical.txt', 'historical\n', 'historical')
            merge_tree = _git(repo, 'merge-tree', '--write-tree', frozen, historical)
            phase_merge = _git(repo, 'commit-tree', merge_tree, '-p', frozen, '-p', historical, '-m', 'phase merge')
            _git(repo, 'checkout', '-q', '--detach', phase_merge); phase_head = _write_commit(repo, 'phase.txt', 'phase\n', 'phase linear')
            _git(repo, 'checkout', '-q', '--detach', historical); effective = _write_commit(repo, 'reviewer.yml', 'installed reviewer\n', 'installed reviewer')
            _git(repo, 'checkout', '-q', '--detach', effective); _write_commit(repo, 'ordinary.txt', 'ordinary\n', 'ordinary phase b')
            base_env = os.environ.copy(); base_env.update({'PRESERVED_PHASE_B_REF':'preserved/phase-b','FROZEN_PHASE_B_HEAD':frozen,'HISTORICAL_PHASE_B_MERGE_BASE':historical})
            ordinary = base_env.copy(); ordinary.update({'EVENT_BASE':effective,'EVENT_HEAD_REF':'fresh/phase-b','EFFECTIVE_EVENT_BASE':effective})
            self.assertEqual(_run_shell(source, repo, ordinary).returncode, 0)
            wrong_effective = ordinary.copy(); wrong_effective['EFFECTIVE_EVENT_BASE'] = historical
            self.assertNotEqual(_run_shell(source, repo, wrong_effective).returncode, 0)
            _git(repo, 'checkout', '-q', '--detach', phase_head)
            preserved = base_env.copy(); preserved.update({'EVENT_BASE':historical,'EVENT_HEAD_REF':'preserved/phase-b','EFFECTIVE_EVENT_BASE':effective})
            self.assertEqual(_run_shell(source, repo, preserved).returncode, 0)
            wrong_base = preserved.copy(); wrong_base['HISTORICAL_PHASE_B_MERGE_BASE'] = root
            self.assertNotEqual(_run_shell(source, repo, wrong_base).returncode, 0)
            _git(repo, 'checkout', '-q', '--detach', historical); other_base = _write_commit(repo, 'other.txt', 'other\n', 'other event base')
            _git(repo, 'checkout', '-q', '--detach', phase_head); not_ancestor = preserved.copy(); not_ancestor['EVENT_BASE'] = other_base
            self.assertNotEqual(_run_shell(source, repo, not_ancestor).returncode, 0)
            phase_tree = _git(repo, 'show', '-s', '--format=%T', phase_head)
            extra_merge = _git(repo, 'commit-tree', phase_tree, '-p', phase_head, '-p', historical, '-m', 'extra phase merge')
            _git(repo, 'checkout', '-q', '--detach', extra_merge)
            self.assertNotEqual(_run_shell(source, repo, preserved).returncode, 0)
            _git(repo, 'checkout', '-q', '--detach', historical); _write_commit(repo, 'replay.txt', 'replay\n', 'replayed identity')
            self.assertNotEqual(_run_shell(source, repo, preserved).returncode, 0)

    def test_both_executables_and_historical_regression_must_consume_canonical_parser(self):
        for token in (
            "publisher=Path(os.environ['PUBLISHER_PATH']).read_text()",
            "legacy_test=Path(os.environ['LEGACY_PARSER_TEST']).read_text()",
            "if science.count(import_token) != 2:", "if publisher.count(import_token) != 3:",
            "if legacy_test.count(import_token) != 1:",
            "for path_name,text in (('science',science),('publisher',publisher)):",
            "if 'def write_quiet_end_binding' in science or 'def write_quiet_end_binding' in publisher:",
            "if 'BEGIN_WRITE_QUIET_END_LINE_PARSER_V1' in legacy_test or 'expected three embedded parser blocks' in legacy_test:",
        ):
            self.assertIn(token, self.text)

    def test_reviewer_owns_independent_semantic_corpus(self):
        for token in (
            'REVIEWER_OWNED_CANONICAL_PARSER_SEMANTIC_CORPUS_V1',
            "WRITE_QUIET_END | begin=999 | stage=legacy\\nbeginComment=123", '5471141095', '5562775627',
            '5467858336', '5467875147', 'shared-evidence mismatch', 'wrong-predecessor reference',
            '_write_quiet_end_records', 'ordinary same-BEGIN duplicate',
        ):
            self.assertIn(token, self.text)
        self.assertIn('Run reviewer-owned immutable semantic corpus against actual parser', self.text)
        self.assertIn('reviewer-owned immutable semantic corpus and executable wiring checks execute before any mutable Phase-B test', self.text)

    def test_canonical_parser_is_statically_pure_before_import(self):
        for token in (
            'PARSER_STATIC_PURITY_GUARD_V1', 'Statically prove canonical parser is pure before importing it',
            "allowed_import_roots={'re'}",
            "forbidden_names={'open','eval','exec','compile','__import__','input','breakpoint','globals','locals','vars','getattr','setattr','delattr'}",
            "forbidden_attr_roots={'os','subprocess','socket','pathlib','requests','urllib','http','ftplib','paramiko','importlib','shutil','sys'}",
            'ast.literal_eval(stmt.value)', 'canonical parser module-level assignment must be literal/container only',
            'canonical parser annotations are forbidden', 'canonical parser dunder/dynamic namespace access forbidden',
            'canonical parser has executable module-level statement',
        ):
            self.assertIn(token, self.text)
        self.assertLess(self.text.index('Statically prove canonical parser is pure before importing it'), self.text.index('Run reviewer-owned immutable semantic corpus against actual parser'))

    def test_mutable_phase_b_tests_cannot_execute_or_spoof(self):
        for token in (
            'MUTABLE_TEST_NON_SPOOF_GUARD_V1', 'Statically prove mutable Phase-B tests cannot execute runtime or spoof later checks',
            "allowed_import_roots={'pathlib','re','textwrap','unittest','scripts'}",
            "allowed_scripts_module='scripts.avps_write_quiet_parser_v1'",
            "forbidden_calls={'open','eval','exec','compile','__import__','input','breakpoint','globals','locals','vars','getattr','setattr','delattr'}",
            "forbidden_methods={'open','write_text','write_bytes','touch','unlink','rename','replace','mkdir','rmdir','chmod','symlink_to','hardlink_to'}",
            'Phase-B test imports non-whitelisted module', 'Phase-B test imports noncanonical project module', 'Phase-B test mutating/dynamic attribute forbidden',
        ):
            self.assertIn(token, self.text)
        order = [
            'Statically prove mutable Phase-B tests cannot execute runtime or spoof later checks',
            'Run reviewer-owned immutable semantic corpus against actual parser',
            'Run reviewer-owned isolated-mode publisher wiring and importability proof',
            'Verify actual executable-chain wiring before mutable tests execute',
            'Run mutable parser regressions only after immutable semantic and wiring checks',
        ]
        positions = [self.text.index(x) for x in order]
        self.assertEqual(positions, sorted(positions))

    def test_mutable_regression_runner_collects_executes_and_fails_closed(self):
        _, source = _named_steps(self.text)['Run mutable parser regressions only after immutable semantic and wiring checks']
        self.assertIn('python -m unittest -v "$PARSER_TEST"', source)
        self.assertIn('python -m unittest -v "$LEGACY_PARSER_TEST"', source)
        self.assertEqual(source.count("grep -Eq '^Ran [1-9][0-9]* tests? in '"), 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/'scripts').mkdir(); (root/'tests').mkdir(); (root/'scripts'/'helper.py').write_text('VALUE = 7\n', encoding='utf-8')
            one=root/'tests'/'test_one.py'; two=root/'tests'/'test_two.py'
            one.write_text("import os, unittest\nfrom pathlib import Path\nfrom scripts.helper import VALUE\nclass T(unittest.TestCase):\n    def test_runs(self):\n        self.assertEqual(VALUE, 7)\n        Path(os.environ['MARK_ONE']).write_text('ran')\n", encoding='utf-8')
            two.write_text("import os, unittest\nfrom pathlib import Path\nfrom scripts.helper import VALUE\nclass T(unittest.TestCase):\n    def test_runs(self):\n        self.assertEqual(VALUE, 7)\n        Path(os.environ['MARK_TWO']).write_text('ran')\n", encoding='utf-8')
            env=os.environ.copy(); env.update({'PARSER_TEST':'tests/test_one.py','LEGACY_PARSER_TEST':'tests/test_two.py','RUNNER_TEMP':str(root/'runner-temp'),'MARK_ONE':str(root/'one.marker'),'MARK_TWO':str(root/'two.marker')}); Path(env['RUNNER_TEMP']).mkdir()
            result=_run_shell(source,root,env); self.assertEqual(result.returncode,0,f'real unittest runner failed: {result.stderr}\n{result.stdout}')
            self.assertTrue(Path(env['MARK_ONE']).exists()); self.assertTrue(Path(env['MARK_TWO']).exists())
            one.write_text('import unittest\n',encoding='utf-8'); self.assertNotEqual(_run_shell(source,root,env).returncode,0)
            one.write_text('this is not valid python\n',encoding='utf-8'); self.assertNotEqual(_run_shell(source,root,env).returncode,0)
            one.write_text("import unittest\nclass T(unittest.TestCase):\n    def test_fails(self):\n        self.fail('expected')\n",encoding='utf-8'); self.assertNotEqual(_run_shell(source,root,env).returncode,0)

    def test_phase_b_publisher_isolated_mode_import_wiring(self):
        for token in (
            'REVIEWER_OWNED_ISOLATED_IMPORT_FIXTURE_V1', 'Run reviewer-owned isolated-mode publisher wiring and importability proof',
            'CanonicalParserReviewerInstallationContract.test_phase_b_publisher_isolated_mode_import_wiring',
            "sys.path.insert(0, os.environ['GITHUB_WORKSPACE'])", '/usr/bin/python3 -I -S', 'PYTHONPATH',
        ):
            self.assertIn(token, self.text)
        semantic_index=self.text.index('Run reviewer-owned immutable semantic corpus against actual parser')
        isolated_index=self.text.index('Run reviewer-owned isolated-mode publisher wiring and importability proof')
        wiring_index=self.text.index('Verify actual executable-chain wiring before mutable tests execute')
        self.assertLess(semantic_index, isolated_index); self.assertLess(isolated_index, wiring_index)
        if os.environ.get('MODE') != 'PHASE_B': return
        publisher=PUBLISHER.read_text(encoding='utf-8'); steps=_named_steps(publisher)
        expected=('Fresh repository-global candidate-seed recheck and one-use guard','Protected dispatch consumption and same-BEGIN science binding','Close exact fence only after science preflight guard terminal')
        canonical_module='scripts.avps_write_quiet_parser_v1'; canonical_names={'record_write_quiet_end','is_write_quiet_begin'}
        for name in expected:
            self.assertIn(name,steps); shell,source=steps[name]; self.assertEqual(shell,'/usr/bin/python3 -I -S {0}')
            tree=ast.parse(source,filename=f'publisher step {name}')
            imports=[(i,s) for i,s in enumerate(tree.body) if isinstance(s,ast.ImportFrom) and s.module==canonical_module]
            self.assertEqual(len(imports),1); import_index,import_stmt=imports[0]; self.assertGreater(import_index,0); self.assertTrue(_is_workspace_insert(tree.body[import_index-1]))
            imported_os=imported_sys=False
            for stmt in tree.body[:import_index]:
                if isinstance(stmt,ast.Import):
                    for alias in stmt.names:
                        if alias.asname is None and alias.name=='os': imported_os=True
                        if alias.asname is None and alias.name=='sys': imported_sys=True
            self.assertTrue(imported_os and imported_sys)
            imported={a.name for a in import_stmt.names if a.asname is None}; self.assertTrue(canonical_names.issubset(imported))
            calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}; self.assertTrue(canonical_names.issubset(calls))
            local_defs={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}; self.assertTrue(canonical_names.isdisjoint(local_defs))
        repo_root=Path(os.environ['GITHUB_WORKSPACE']).resolve(); self.assertEqual(repo_root,Path.cwd().resolve())
        env=os.environ.copy(); env.pop('PYTHONPATH',None)
        unbound=subprocess.run(['/usr/bin/python3','-I','-S','-c','from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin'],cwd=repo_root,env=env,capture_output=True,text=True,check=False)
        self.assertNotEqual(unbound.returncode,0); self.assertIn("No module named 'scripts'",unbound.stderr)
        bound_code="import os,sys; sys.path.insert(0, os.environ['GITHUB_WORKSPACE']); from scripts.avps_write_quiet_parser_v1 import is_write_quiet_begin; assert callable(is_write_quiet_begin)"
        bound=subprocess.run(['/usr/bin/python3','-I','-S','-c',bound_code],cwd=repo_root,env=env,capture_output=True,text=True,check=False)
        self.assertEqual(bound.returncode,0,f'workspace-bound isolated-mode canonical import failed: {bound.stderr}')

    def test_reviewer_contains_no_authorizing_or_science_runtime_surface(self):
        permissions=self.text.split('\npermissions:\n',1)[1].split('\nconcurrency:\n',1)[0]; self.assertNotIn(': write',permissions)
        for token in ('gh workflow '+'run','gh api -X '+'POST','git '+'push','command -v '+'uvspec','rte_solver '+'mystic','mc_'+'photons 20000000'):
            self.assertNotIn(token,self.text)
        self.assertIn('no publisher invocation, WRITE_QUIET entry, dispatch, seed or ordinal allocation, solver, result opening, science authority',self.text)


if __name__ == '__main__':
    unittest.main()
