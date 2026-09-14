from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

V12_HEAD = 'ca44daf0355abc030da2bdfe6f647e0de9aa0805'
V12_SCRIPT_BLOB = '3c8b7f3ef02ad5d2d4ce09c2036bc071427e75a0'
V12_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v12/review_authorization.py'
V13_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v13-20260914'
V13_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v13/review_authorization.py'
V13_MAIN = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'
V4_PR = 1032
V4_HEAD = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
V4_BASE_REF = 'main'
V4_CREATION_BASE = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
V4_ERROR = 'v4 PR base drift'
V4_HISTORICAL_CONSTANT = 'V4_HISTORICAL_CREATION_BASE_SHA'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V12_ROOT = REVIEW_ROOT.parent / 'v12-base'


def _argv_value(flag: str) -> str | None:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


def _canon(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    ).hexdigest()


def _write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def _persist_v13_wrapper_failure(exc: BaseException) -> None:
    ev_arg = _argv_value('--ev')
    if not ev_arg:
        return
    ev = Path(ev_arg)
    ev.mkdir(parents=True, exist_ok=True)
    run_arg = _argv_value('--run') or '0'
    attempt_arg = _argv_value('--attempt') or '0'
    payload = {
        'schemaVersion': 1,
        'status': 'FAIL_RESULT_BLIND_V13_WRAPPER',
        'type': type(exc).__name__,
        'message': str(exc)[:8000],
        'phase': 'pre_effective_source_wrapper',
        'reviewerHead': _argv_value('--rh') or '',
        'runId': int(run_arg) if run_arg.isdigit() else run_arg,
        'attempt': int(attempt_arg) if attempt_arg.isdigit() else attempt_arg,
        'authorizationRefCreated': False,
        'dispatchCreated': False,
        'protectedResultsOpened': False,
        'scienceInvoked': False,
        'scientificOrdinalAllocated': False,
        'seedUniverseConsumed': False,
        'solverExecuted': False,
    }
    payload['receiptSha256'] = _canon(payload)
    _write_json_atomic(ev / 'failure.json', payload)


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def _static_constants(tree: ast.AST) -> dict[str, object]:
    result: dict[str, object] = {}
    for node in getattr(tree, 'body', []):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or not isinstance(node.value, ast.Constant):
            continue
        result[target.id] = node.value.value
    return result


def _resolve_static(node: ast.AST, constants: dict[str, object]):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    return None


def _attribute_tail(node: ast.AST) -> str | None:
    return node.attr if isinstance(node, ast.Attribute) else None


def _subscript_path(node: ast.AST) -> tuple[str, tuple[str, ...]] | None:
    keys: list[str] = []
    current = node
    while isinstance(current, ast.Subscript):
        key = current.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.append(key.value)
        else:
            return None
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    keys.reverse()
    return current.id, tuple(keys)


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    result: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            result[child] = parent
    return result


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
    return None


def _req_calls_with_message(tree: ast.AST, message: str) -> list[ast.Call]:
    found: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != 'req':
            continue
        if len(node.args) < 2:
            continue
        msg = node.args[1]
        if isinstance(msg, ast.Constant) and msg.value == message:
            found.append(node)
    return found


def _current_pr_assignment(function: ast.AST, constants: dict[str, object]) -> tuple[str, ast.Assign]:
    found: list[tuple[str, ast.Assign]] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or _attribute_tail(value.func) != 'current_pr' or len(value.args) < 2:
            continue
        if _resolve_static(value.args[1], constants) == V4_PR:
            found.append((node.targets[0].id, node))
    if len(found) != 1:
        raise RuntimeError(f'V13 historical V4 current_pr assignment count drift: {len(found)}')
    return found[0]


def _compare_has_pair(compare: ast.Compare, left_test, right_test) -> tuple[ast.AST, ast.AST] | None:
    operands = [compare.left] + list(compare.comparators)
    if len(operands) != 2 or len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
        return None
    left, right = operands
    if left_test(left) and right_test(right):
        return left, right
    if left_test(right) and right_test(left):
        return right, left
    return None


def _node_segment(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if not isinstance(segment, str):
        raise RuntimeError('V13 could not recover AST source segment')
    return segment


def _replace_node_segment(source: str, node: ast.AST, replacement: str) -> str:
    if not all(hasattr(node, name) for name in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')):
        raise RuntimeError('V13 replacement node lacks source coordinates')
    if node.lineno != node.end_lineno:
        raise RuntimeError('V13 refuses multiline historical-base operand rewrite')
    lines = source.splitlines(keepends=True)
    index = node.lineno - 1
    if index < 0 or index >= len(lines):
        raise RuntimeError('V13 historical-base operand line index drift')
    line = lines[index]
    start = node.col_offset
    end = node.end_col_offset
    if line[start:end] != _node_segment(source, node):
        raise RuntimeError('V13 historical-base operand coordinate drift')
    lines[index] = line[:start] + replacement + line[end:]
    return ''.join(lines)


def _inject_historical_constant(source: str) -> str:
    tree = ast.parse(source)
    main_assignments = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'MAIN':
            main_assignments.append(node)
    if len(main_assignments) != 1:
        raise RuntimeError(f'V13 MAIN assignment count drift before historical injection: {len(main_assignments)}')
    node = main_assignments[0]
    if not isinstance(node.value, ast.Constant) or node.value.value != V13_MAIN:
        raise RuntimeError(f'V13 source MAIN is not exact admissible current main: {ast.dump(node.value)}')
    if node.lineno != node.end_lineno or node.col_offset != 0:
        raise RuntimeError('V13 MAIN assignment shape drift')
    if V4_HISTORICAL_CONSTANT in source:
        raise RuntimeError('V13 historical-base constant unexpectedly pre-exists')
    lines = source.splitlines(keepends=True)
    index = node.lineno
    lines.insert(index, f"{V4_HISTORICAL_CONSTANT} = {V4_CREATION_BASE!r}\n")
    injected = ''.join(lines)
    constants = _static_constants(ast.parse(injected))
    if constants.get(V4_HISTORICAL_CONSTANT) != V4_CREATION_BASE:
        raise RuntimeError('V13 historical-base constant injection verification failed')
    return injected


def _locate_v4_base_path(source: str, expected_symbol: str) -> dict[str, object]:
    tree = ast.parse(source)
    constants = _static_constants(tree)
    if constants.get('MAIN') != V13_MAIN:
        raise RuntimeError(f'V13 current MAIN binding drift in reconstructed source: {constants.get("MAIN")!r}')
    calls = _req_calls_with_message(tree, V4_ERROR)
    if len(calls) != 1:
        raise RuntimeError(f'V13 v4 PR base drift emitter count is not unique: {len(calls)}')
    call = calls[0]
    parents = _parent_map(tree)
    function = _enclosing_function(call, parents)
    if function is None:
        raise RuntimeError('V13 historical V4 base refusal is not inside a function')
    pr_var, assignment = _current_pr_assignment(function, constants)
    condition = call.args[0]

    sha_matches: list[tuple[ast.AST, ast.AST]] = []
    ref_matches: list[tuple[ast.AST, ast.AST]] = []
    for node in ast.walk(condition):
        if not isinstance(node, ast.Compare):
            continue
        sha = _compare_has_pair(
            node,
            lambda value: _subscript_path(value) == (pr_var, ('base', 'sha')),
            lambda value: isinstance(value, ast.Name) and value.id == expected_symbol,
        )
        if sha:
            sha_matches.append(sha)
        ref = _compare_has_pair(
            node,
            lambda value: _subscript_path(value) == (pr_var, ('base', 'ref')),
            lambda value: isinstance(value, ast.Constant) and value.value == V4_BASE_REF,
        )
        if ref:
            ref_matches.append(ref)
    if len(sha_matches) != 1:
        raise RuntimeError(f'V13 V4 base-SHA comparator count for {expected_symbol} drift: {len(sha_matches)}')
    if len(ref_matches) != 1:
        raise RuntimeError(f'V13 V4 base-ref comparator count drift: {len(ref_matches)}')
    path_node, expected_node = sha_matches[0]
    assignment_call = assignment.value
    pr_arg = assignment_call.args[1] if isinstance(assignment_call, ast.Call) else None
    if _resolve_static(pr_arg, constants) != V4_PR:
        raise RuntimeError('V13 historical current_pr dataflow no longer resolves to PR1032')
    return {
        'tree': tree,
        'call': call,
        'function': function,
        'condition': condition,
        'prVariable': pr_var,
        'assignment': assignment,
        'basePathNode': path_node,
        'expectedNode': expected_node,
        'constants': constants,
        'refComparatorCount': len(ref_matches),
        'emitterLine': call.lineno,
        'assignmentLine': assignment.lineno,
        'conditionSource': _node_segment(source, condition),
    }


def _validate_v4_metadata(row: dict) -> dict[str, object]:
    if not isinstance(row, dict):
        raise RuntimeError('V13 V4 metadata row is not an object')
    if int(row.get('number') or 0) != V4_PR:
        raise RuntimeError('V13 V4 PR identity drift')
    if row.get('state') != 'open' or row.get('draft') is not True or row.get('merged_at') is not None:
        raise RuntimeError('V13 V4 state/merged identity drift')
    head = row.get('head') or {}
    base = row.get('base') or {}
    if str(head.get('sha') or '') != V4_HEAD:
        raise RuntimeError('V13 V4 head drift')
    if str(base.get('ref') or '') != V4_BASE_REF:
        raise RuntimeError('V13 V4 base ref drift')
    if str(base.get('sha') or '') != V4_CREATION_BASE:
        raise RuntimeError('V13 V4 historical creation base drift')
    return {
        'pr': V4_PR,
        'state': 'open',
        'draft': True,
        'mergedAt': None,
        'headSha': V4_HEAD,
        'baseRef': V4_BASE_REF,
        'baseSha': V4_CREATION_BASE,
    }


def _expect_metadata_failure(row: dict, label: str) -> bool:
    try:
        _validate_v4_metadata(row)
    except RuntimeError:
        return True
    raise RuntimeError(f'V13 V4 metadata negative fixture unexpectedly accepted: {label}')


def _v4_metadata_fixtures() -> dict[str, bool]:
    base = {
        'number': V4_PR,
        'state': 'open',
        'draft': True,
        'merged_at': None,
        'head': {'sha': V4_HEAD},
        'base': {'ref': V4_BASE_REF, 'sha': V4_CREATION_BASE},
    }
    _validate_v4_metadata(base)
    wrong_base = copy.deepcopy(base)
    wrong_base['base']['sha'] = '0' * 40
    wrong_head = copy.deepcopy(base)
    wrong_head['head']['sha'] = '0' * 40
    wrong_ref = copy.deepcopy(base)
    wrong_ref['base']['ref'] = 'not-main'
    wrong_state = copy.deepcopy(base)
    wrong_state['state'] = 'closed'
    merged = copy.deepcopy(base)
    merged['merged_at'] = '2026-09-14T00:00:00Z'
    successor_leak = copy.deepcopy(base)
    successor_leak['base']['sha'] = V13_MAIN
    return {
        'exactFrozenV4MetadataPositive': True,
        'wrongV4BaseShaFatal': _expect_metadata_failure(wrong_base, 'wrong base SHA'),
        'wrongV4HeadFatal': _expect_metadata_failure(wrong_head, 'wrong head'),
        'wrongBaseRefFatal': _expect_metadata_failure(wrong_ref, 'wrong base ref'),
        'wrongV4StateFatal': _expect_metadata_failure(wrong_state, 'wrong state'),
        'mergedV4IdentityFatal': _expect_metadata_failure(merged, 'merged identity'),
        'successorCurrentMainLeakageFatal': _expect_metadata_failure(successor_leak, 'successor MAIN leakage'),
    }


def _reconstruct_frozen_v12_effective_source() -> tuple[str, dict]:
    head = subprocess.run(
        ['git', '-C', str(V12_ROOT), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0 or head.stdout.strip() != V12_HEAD:
        raise RuntimeError(f'frozen V12 source checkout drift: {head.stdout!r} {head.stderr!r}')
    v12_path = V12_ROOT / V12_SCRIPT
    raw = v12_path.read_bytes()
    git_blob = _git_blob_sha1(raw)
    if git_blob != V12_SCRIPT_BLOB:
        raise RuntimeError(f'frozen V12 source blob drift: {git_blob}')
    v12_source = raw.decode('utf-8')
    final_exec = "exec(compile(V12_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"
    if v12_source.count(final_exec) != 1:
        raise RuntimeError('V13 frozen V12 final effective exec anchor drift')
    extractor = v12_source.replace(
        final_exec,
        'V13_FROZEN_V12_EFFECTIVE_SOURCE = V12_EFFECTIVE_SOURCE',
        1,
    )
    scope = {'__file__': str(HERE), '__name__': '_avps_v12_exact_effective_source_builder_'}
    exec(compile(extractor, str(HERE), 'exec'), scope, scope)
    source = scope.get('V13_FROZEN_V12_EFFECTIVE_SOURCE')
    if not isinstance(source, str) or not source:
        raise RuntimeError('V13 could not reconstruct exact final V12 effective source')
    return source, scope


def _build_v13_effective_source(observed_v4: dict) -> tuple[str, dict]:
    observed = _validate_v4_metadata(observed_v4)
    fixtures = _v4_metadata_fixtures()
    frozen, scope = _reconstruct_frozen_v12_effective_source()
    frozen_sha = hashlib.sha256(frozen.encode('utf-8')).hexdigest()

    pre = _locate_v4_base_path(frozen, 'MAIN')
    if pre['constants'].get('MAIN') != V13_MAIN:
        raise RuntimeError('V13 pre-repair successor MAIN identity drift')
    if observed['baseSha'] == V13_MAIN:
        raise RuntimeError('V13 proof cannot establish leakage because observed V4 base equals current MAIN')
    if observed['baseSha'] != V4_CREATION_BASE:
        raise RuntimeError('V13 direct V4 observation does not match frozen creation base')

    injected = _inject_historical_constant(frozen)
    after_injection = _locate_v4_base_path(injected, 'MAIN')
    repaired = _replace_node_segment(injected, after_injection['expectedNode'], V4_HISTORICAL_CONSTANT)
    post = _locate_v4_base_path(repaired, V4_HISTORICAL_CONSTANT)
    if any(isinstance(node, ast.Name) and node.id == 'MAIN' for node in ast.walk(post['condition'])):
        raise RuntimeError('V13 successor/current MAIN still leaks into frozen-V4 base comparator')
    if post['constants'].get(V4_HISTORICAL_CONSTANT) != V4_CREATION_BASE:
        raise RuntimeError('V13 repaired historical V4 expected base constant drift')

    effective = repaired.replace('replacement-v12', 'replacement-v13').replace('REPLACEMENT_V12', 'REPLACEMENT_V13')
    effective = effective.replace('v12', 'v13').replace('V12', 'V13')
    if effective == repaired:
        raise RuntimeError('V13 mechanical identity lift produced no change')
    if 'replacement-v12' in effective or 'REPLACEMENT_V12' in effective:
        raise RuntimeError('V13 mechanical identity lift incomplete')

    final = _locate_v4_base_path(effective, V4_HISTORICAL_CONSTANT)
    if final['constants'].get('MAIN') != V13_MAIN:
        raise RuntimeError('V13 final current-main binding drift')
    if final['constants'].get(V4_HISTORICAL_CONSTANT) != V4_CREATION_BASE:
        raise RuntimeError('V13 final frozen-V4 historical base binding drift')
    if any(isinstance(node, ast.Name) and node.id == 'MAIN' for node in ast.walk(final['condition'])):
        raise RuntimeError('V13 final frozen-V4 comparator leaked successor/current MAIN')

    rbr = final['constants'].get('RBR')
    if rbr != V13_BRANCH:
        raise RuntimeError(f'V13 final carrier RBR drift: {rbr!r}')

    validator_sites = scope.get('_v7_operational_validator_sites')
    ordering_sites = scope.get('_v11_executable_ordering_sites')
    if not callable(validator_sites) or not callable(ordering_sites):
        raise RuntimeError('V13 inherited structural proof helpers unavailable')
    operational = validator_sites(effective)
    if len(operational) != 2:
        raise RuntimeError(f'V13 final operational validator site count drift: {len(operational)}')
    pairs = ordering_sites(effective, 'v13-spent-nonauth-diagnostic-classification.json')
    if len(pairs) != 2:
        raise RuntimeError(f'V13 final validator/classification-write pair count drift: {len(pairs)}')
    if 'spent_diagnostic_proof = None' in effective:
        raise RuntimeError('V13 forbidden dummy proof initialization detected')

    effective_sha = hashlib.sha256(effective.encode('utf-8')).hexdigest()
    proof = {
        'schemaVersion': 1,
        'status': 'PASS_V13_PREACTUAL_HISTORICAL_V4_BASE_BINDING_PROOF',
        'frozenV12Head': V12_HEAD,
        'frozenV12ScriptGitBlobSha1': V12_SCRIPT_BLOB,
        'frozenV12EffectiveSourceSha256': frozen_sha,
        'v4RefusalEmitterCount': 1,
        'v4RefusalEmitterLine': pre['emitterLine'],
        'v4CurrentPrAssignmentLine': pre['assignmentLine'],
        'v4CurrentPrVariable': pre['prVariable'],
        'v4CurrentPrIdentity': V4_PR,
        'v4BaseComparatorConditionBeforeRepair': pre['conditionSource'],
        'preRepairExpectedBaseSymbol': 'MAIN',
        'preRepairExpectedBaseSha': V13_MAIN,
        'observedV4Metadata': observed,
        'observedV4CreationBaseSha': observed['baseSha'],
        'expectedObservedMismatchUniquelyEstablished': V13_MAIN != observed['baseSha'],
        'cause': 'frozen V4 creation-base comparator incorrectly expected successor/current MAIN',
        'repair': f'separate immutable {V4_HISTORICAL_CONSTANT} from live MAIN',
        'postRepairExpectedBaseSymbol': V4_HISTORICAL_CONSTANT,
        'postRepairExpectedBaseSha': V4_CREATION_BASE,
        'successorCurrentMainLeakageAfterRepair': False,
        'v4MetadataFixtures': fixtures,
        'operationalValidatorSiteCount': len(operational),
        'validatorClassificationWritePairCount': len(pairs),
        'validatorClassificationWritePairs': [list(row) for row in pairs],
        'v7ExactTwoOperationalSiteGatePreserved': True,
        'oneClassificationWriteImmediatelyAfterEachReturnBinding': True,
        'v12CarrierRebindPreserved': True,
        'durableFailureDirectoryCreationPreserved': True,
        'dummyInitializationUsed': False,
        'classificationWriteSuppressed': False,
        'spentArtifactTaxonomyBroadened': False,
        'unknownArtifactIgnoreRuleAdded': False,
        'siteCountGateRelaxed': False,
        'carrierGateRelaxed': False,
        'historicalV4BaseGateRelaxed': False,
        'finalV13EffectiveSourceSha256': effective_sha,
        'authorizationRefCreated': False,
        'dispatchCreated': False,
        'protectedResultsOpened': False,
        'scienceInvoked': False,
        'scientificOrdinalAllocated': False,
        'seedUniverseConsumed': False,
        'solverExecuted': False,
        'scienceFalse': True,
    }
    proof['receiptSha256'] = _canon(proof)
    return effective, proof


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RuntimeError(f'V13 JSON object expected at {path}')
    return value


def _proof_only() -> None:
    metadata_arg = _argv_value('--v4-metadata')
    output_arg = _argv_value('--v13-proof-out')
    if not metadata_arg or not output_arg:
        raise RuntimeError('V13 proof-only mode requires --v4-metadata and --v13-proof-out')
    output = Path(output_arg)
    try:
        _, proof = _build_v13_effective_source(_load_json(Path(metadata_arg)))
        _write_json_atomic(output, proof)
        print(json.dumps(proof, sort_keys=True))
    except BaseException as exc:
        failure = {
            'schemaVersion': 1,
            'status': 'FAIL_V13_PREACTUAL_HISTORICAL_V4_BASE_BINDING_PROOF',
            'type': type(exc).__name__,
            'message': str(exc)[:8000],
            'authorizationRefCreated': False,
            'dispatchCreated': False,
            'protectedResultsOpened': False,
            'scienceInvoked': False,
            'scientificOrdinalAllocated': False,
            'seedUniverseConsumed': False,
            'solverExecuted': False,
            'scienceFalse': True,
        }
        failure['receiptSha256'] = _canon(failure)
        _write_json_atomic(output, failure)
        raise


def _actual_source() -> str:
    preproof_path = os.environ.get('V13_PREPROOF_PATH', '').strip()
    if not preproof_path:
        raise RuntimeError('V13 ACTUAL execution requires bound pre-ACTUAL proof path')
    preproof = _load_json(Path(preproof_path))
    if preproof.get('status') != 'PASS_V13_PREACTUAL_HISTORICAL_V4_BASE_BINDING_PROOF':
        raise RuntimeError('V13 bound pre-ACTUAL proof is not PASS')
    saved = preproof.get('receiptSha256')
    check = dict(preproof)
    check.pop('receiptSha256', None)
    if saved != _canon(check):
        raise RuntimeError('V13 bound pre-ACTUAL proof self-hash drift')
    observed = preproof.get('observedV4Metadata')
    if not isinstance(observed, dict):
        raise RuntimeError('V13 bound pre-ACTUAL proof lacks observed V4 metadata')
    effective, repeated = _build_v13_effective_source({
        'number': observed.get('pr'),
        'state': observed.get('state'),
        'draft': observed.get('draft'),
        'merged_at': observed.get('mergedAt'),
        'head': {'sha': observed.get('headSha')},
        'base': {'ref': observed.get('baseRef'), 'sha': observed.get('baseSha')},
    })
    for key in (
        'frozenV12EffectiveSourceSha256',
        'preRepairExpectedBaseSha',
        'observedV4CreationBaseSha',
        'postRepairExpectedBaseSha',
        'finalV13EffectiveSourceSha256',
        'operationalValidatorSiteCount',
        'validatorClassificationWritePairCount',
    ):
        if repeated.get(key) != preproof.get(key):
            raise RuntimeError(f'V13 ACTUAL/preproof deterministic binding drift at {key}')
    return effective


if '--v13-proof-only' in sys.argv:
    _proof_only()
    raise SystemExit(0)

try:
    V13_EFFECTIVE_SOURCE = _actual_source()
except BaseException as exc:
    _persist_v13_wrapper_failure(exc)
    raise

exec(compile(V13_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())
