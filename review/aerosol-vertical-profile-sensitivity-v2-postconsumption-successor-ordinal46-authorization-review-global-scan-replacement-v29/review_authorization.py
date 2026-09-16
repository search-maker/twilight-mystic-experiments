from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import re
import sys
import zlib
from pathlib import Path

MAIN = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'
OLD = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
V4 = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
V28_BLOB = 'f1e368e245ddea8750c39019dd3b29b4a0fcb2b5'
V17_BLOB = '06867e14710f15cade77ed24fbdc33dafb9f2f74'
P17 = '3cb6ad6603d53440cfc159d96da5b262c9441102ffca7db3ce7443c22b32f643'
FAIL = 'FAIL_V29_PREACTUAL_V4_INSERTION_VALUE_STATIC_PROVENANCE_OR_DOWNSTREAM'
HERE = Path(__file__).resolve()


def arg(k: str) -> str | None:
    try:
        i = sys.argv.index(k)
        return sys.argv[i + 1]
    except (ValueError, IndexError):
        return None


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def write(path: str | None, payload: dict) -> None:
    if not path:
        return
    out = dict(payload)
    canonical = json.dumps(out, sort_keys=True, separators=(',', ':')).encode()
    out['receiptSha256'] = sha(canonical)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, sort_keys=True, indent=2) + '\n')


def failure(exc: BaseException) -> None:
    if os.environ.get('V29_PREACTUAL_ACTIVE') != '1':
        return
    d = os.environ.get('V29_PREACTUAL_FAILURE_DIR')
    if not d:
        return
    p = Path(d) / 'failure.json'
    if p.exists():
        return
    write(str(p), {
        'status': FAIL,
        'type': type(exc).__name__,
        'message': str(exc),
        'authorizationRefCreated': False,
        'dispatchCreated': False,
        'scientificOrdinalAllocated': False,
        'scientificOrdinalReserved': False,
        'scientificOrdinalDispatched': False,
        'seedUniverseConsumed': False,
        'scienceInvoked': False,
        'solverExecuted': False,
        'protectedResultsOpened': False,
        'publisherInvoked': False,
        'newMappingOpened': False,
        'productionInvoked': False,
        'scienceFalse': True,
    })


def exact_file(env: str, expected_blob: str) -> bytes:
    p = os.environ.get(env, '')
    raw = Path(p).read_bytes() if p else b''
    got = blob(raw)
    if got != expected_blob:
        raise RuntimeError(f'V29 {env} blob drift: {got}')
    return raw


def top_fn(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    found = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(found) != 1:
        raise RuntimeError(f'V29 {name} count drift: {len(found)}')
    return found[0]


def source_segment(src: str, node: ast.AST) -> str:
    out = ast.get_source_segment(src, node)
    if not isinstance(out, str):
        raise RuntimeError('V29 source segment unavailable')
    return out


def decode_v17_launcher(raw: bytes) -> str:
    text = raw.decode()
    payloads = re.findall(r'^PAYLOAD_B85 = r"""(.*?)"""\.replace\(\'\\n\', \'\'\)$', text, re.M | re.S)
    digests = re.findall(r"^PAYLOAD_SHA256 = '([0-9a-f]{64})'$", text, re.M)
    if len(payloads) != 1 or digests != [P17]:
        raise RuntimeError('V29 frozen V17 launcher binding drift')
    compressed = base64.b85decode(payloads[0].replace('\n', '').encode())
    decoded = zlib.decompress(compressed)
    if sha(decoded) != P17:
        raise RuntimeError('V29 frozen V17 payload SHA drift')
    src = decoded.decode()
    ast.parse(src)
    return src


def module_string_values(tree: ast.Module) -> dict[str, str]:
    pending: dict[str, ast.AST] = {}
    for n in tree.body:
        target = None
        value = None
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            target, value = n.targets[0].id, n.value
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
            target, value = n.target.id, n.value
        if target is not None and value is not None:
            pending[target] = value
    values: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for name, value in pending.items():
            if name in values:
                continue
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                values[name] = value.value
                changed = True
            elif isinstance(value, ast.Name) and value.id in values:
                values[name] = values[value.id]
                changed = True
    return values


def local_assignments(fn: ast.AST) -> dict[str, ast.AST]:
    by_name: dict[str, list[ast.AST]] = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            by_name.setdefault(n.targets[0].id, []).append(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
            by_name.setdefault(n.target.id, []).append(n.value)
    return {k: v[0] for k, v in by_name.items() if len(v) == 1}


def origin_tokens(node: ast.AST, locals_map: dict[str, ast.AST], module_values: dict[str, str], seen: set[str] | None = None) -> set[str]:
    if seen is None:
        seen = set()
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)
        elif isinstance(n, ast.Name):
            if n.id in module_values:
                out.add(module_values[n.id])
            if n.id in locals_map and n.id not in seen:
                out |= origin_tokens(locals_map[n.id], locals_map, module_values, seen | {n.id})
    return out


def origin_names(node: ast.AST, locals_map: dict[str, ast.AST], seen: set[str] | None = None) -> set[str]:
    if seen is None:
        seen = set()
    out: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
            if n.id in locals_map and n.id not in seen:
                out |= origin_names(locals_map[n.id], locals_map, seen | {n.id})
    return out


def has_key(tokens: set[str], key: str) -> bool:
    return any(key in t for t in tokens)


def insert_candidates(fn: ast.AST, module_values: dict[str, str]) -> list[dict]:
    lm = local_assignments(fn)
    candidates: list[dict] = []
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute) or n.func.attr != 'replace' or len(n.args) < 2:
            continue
        replacement_tokens = origin_tokens(n.args[1], lm, module_values)
        if not has_key(replacement_tokens, 'expectedBaseSha'):
            continue
        anchor_tokens = origin_tokens(n.args[0], lm, module_values)
        all_anchor = ' '.join(sorted(anchor_tokens)).lower()
        if 'v4' not in all_anchor:
            continue
        receiver_names = origin_names(n.func.value, lm)
        if 'source_text' not in receiver_names:
            continue
        unique = len(n.args) >= 3 and isinstance(n.args[2], ast.Constant) and n.args[2].value == 1
        if not unique:
            target_dump = ast.dump(n.args[0], include_attributes=False)
            for c in ast.walk(fn):
                if not isinstance(c, ast.Compare) or len(c.ops) != 1 or not isinstance(c.ops[0], (ast.Eq, ast.NotEq)) or len(c.comparators) != 1:
                    continue
                sides = (c.left, c.comparators[0])
                one = any(isinstance(s, ast.Constant) and s.value == 1 for s in sides)
                if not one:
                    continue
                for s in sides:
                    if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr == 'count' and len(s.args) == 1:
                        if ast.dump(s.args[0], include_attributes=False) == target_dump:
                            unique = True
        candidates.append({
            'line': getattr(n, 'lineno', None),
            'anchorTokens': sorted(anchor_tokens),
            'replacementTokens': sorted(replacement_tokens),
            'uniqueReplacementGuard': unique,
            'replacementUsesCurrentMain': MAIN in replacement_tokens,
        })
    return candidates


def binding_candidates(fn: ast.AST, module_values: dict[str, str]) -> list[dict]:
    lm = local_assignments(fn)
    out: list[dict] = []
    for n in ast.walk(fn):
        if not isinstance(n, ast.Compare):
            continue
        tokens = origin_tokens(n, lm, module_values)
        if OLD in tokens and has_key(tokens, 'expectedBaseSha'):
            out.append({
                'line': getattr(n, 'lineno', None),
                'tokens': sorted(tokens),
                'containsCurrentMain': MAIN in tokens,
            })
    return out


def assignment_target_for_call(fn: ast.AST, helper: str) -> tuple[str, ast.Call, int]:
    found: list[tuple[str, ast.Call, int]] = []
    for n in ast.walk(fn):
        if not isinstance(n, (ast.Assign, ast.AnnAssign)):
            continue
        value = n.value
        target = n.targets[0] if isinstance(n, ast.Assign) and len(n.targets) == 1 else n.target if isinstance(n, ast.AnnAssign) else None
        if isinstance(target, ast.Name) and isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == helper:
            found.append((target.id, value, getattr(n, 'lineno', 0)))
    if len(found) != 1:
        raise RuntimeError(f'V29 {helper} assignment count drift: {len(found)}')
    return found[0]


def builder_dataflow(builder: ast.AST) -> dict:
    insert_name, insert_call, insert_line = assignment_target_for_call(builder, '_insert_v4_expected_base')
    repair_name, repair_call, repair_line = assignment_target_for_call(builder, '_repair_base_comparator')
    derived = {insert_name}
    if repair_call.args and isinstance(repair_call.args[0], ast.Name) and repair_call.args[0].id in derived:
        derived.add(repair_name)
    else:
        raise RuntimeError('V29 V17 repair input is not exact insert-derived source')
    assertions = [n for n in ast.walk(builder) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == '_assert_v4_historical_source_binding']
    if len(assertions) != 1:
        raise RuntimeError(f'V29 V17 historical assertion call count drift: {len(assertions)}')
    ac = assertions[0]
    if not ac.args or not isinstance(ac.args[0], ast.Name) or ac.args[0].id not in derived:
        raise RuntimeError('V29 V17 historical assertion is not bound to insert-derived source')
    assert_line = getattr(ac, 'lineno', 0)
    if not (insert_line < repair_line <= assert_line or insert_line < assert_line <= repair_line):
        raise RuntimeError('V29 V17 insertion/assertion call order drift')
    return {
        'insertResultName': insert_name,
        'repairResultName': repair_name,
        'assertInputName': ac.args[0].id,
        'insertLine': insert_line,
        'repairLine': repair_line,
        'assertCallLine': assert_line,
    }


def static_v4_insertion_provenance(v17_src: str, v28_src: str) -> dict:
    tree = ast.parse(v17_src)
    insert = top_fn(tree, '_insert_v4_expected_base')
    repair = top_fn(tree, '_repair_base_comparator')
    assertion = top_fn(tree, '_assert_v4_historical_source_binding')
    builder = top_fn(tree, '_build_v17_effective_source')
    module_values = module_string_values(tree)
    insert_src = source_segment(v17_src, insert)
    repair_src = source_segment(v17_src, repair)
    assertion_src = source_segment(v17_src, assertion)
    builder_src = source_segment(v17_src, builder)

    if OLD in insert_src:
        raise RuntimeError('V29 negative fixture failed: V28 same-span OLD literal unexpectedly present')
    ins = insert_candidates(insert, module_values)
    if len(ins) != 1:
        raise RuntimeError(f'V29 V17 insertion provenance candidate count drift: {len(ins)}')
    if not ins[0]['uniqueReplacementGuard']:
        raise RuntimeError('V29 V17 insertion replacement is not statically unique')
    if ins[0]['replacementUsesCurrentMain']:
        raise RuntimeError('V29 current-MAIN leakage into frozen-V4 insertion replacement')

    binds = binding_candidates(assertion, module_values)
    if len(binds) != 1:
        raise RuntimeError(f'V29 V17 immutable expected-base binding count drift: {len(binds)}')
    if binds[0]['containsCurrentMain']:
        raise RuntimeError('V29 current-MAIN leakage into frozen-V4 immutable binding')

    flow = builder_dataflow(builder)

    side_effects: list[str] = []
    for f in (insert, repair, assertion):
        for n in ast.walk(f):
            if not isinstance(n, ast.Call):
                continue
            if isinstance(n.func, ast.Name) and n.func.id in {'exec', 'eval', 'open', '__import__'}:
                side_effects.append(f'{getattr(n, "lineno", 0)}:{n.func.id}')
            if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in {'subprocess', 'os', 'requests', 'urllib', 'socket'}:
                side_effects.append(f'{getattr(n, "lineno", 0)}:{n.func.value.id}.{n.func.attr}')
    if side_effects:
        raise RuntimeError(f'V29 static provenance candidate has side effects: {side_effects!r}')

    v28_tree = ast.parse(v28_src)
    v28_dist = top_fn(v28_tree, 'distributed')
    v28_dist_src = source_segment(v28_src, v28_dist)
    old_test = "if ss['insert'].count(OLD)!=1 or 'expectedBaseSha' not in ss['insert']:raise RuntimeError('V28 V17 insert provenance drift')"
    if v28_dist_src.count(old_test) != 1:
        raise RuntimeError('V29 frozen V28 same-span negative fixture drift')

    return {
        'status': 'PASS_V29_PREACTUAL_V4_INSERTION_VALUE_STATIC_PROVENANCE',
        'historicalV4Base': OLD,
        'currentSuccessorMain': MAIN,
        'historicalBaseSeparatedFromCurrentMain': OLD != MAIN,
        'v17PayloadSha256': P17,
        'insertLine': insert.lineno,
        'repairLine': repair.lineno,
        'assertFunctionLine': assertion.lineno,
        'builderLine': builder.lineno,
        'insertSha256': sha(insert_src.encode()),
        'repairSha256': sha(repair_src.encode()),
        'assertSha256': sha(assertion_src.encode()),
        'builderSha256': sha(builder_src.encode()),
        'uniqueInsertionCandidate': ins[0],
        'uniqueImmutableBinding': binds[0],
        'builderDataflow': flow,
        'proofCandidateSideEffectFree': True,
        'oldV28SameSpanLiteralAssertionRejected': True,
    }


def fixture_suite() -> dict:
    good = f"""OLD='{OLD}'\nMAIN='{MAIN}'\ndef _insert_v4_expected_base(source_text):\n    needle=\"{{'version':'v4'}}\"\n    repl=\"{{'version':'v4','expectedBaseSha':\"+OLD+\"}}\"\n    if source_text.count(needle) != 1: raise RuntimeError('x')\n    return source_text.replace(needle,repl,1)\ndef _assert_v4_historical_source_binding(source_text):\n    got={{'expectedBaseSha': OLD}}.get('expectedBaseSha')\n    if got != OLD: raise RuntimeError('x')\ndef _repair_base_comparator(source_text):\n    return source_text\ndef _build_v17_effective_source():\n    a=_insert_v4_expected_base('x')\n    b=_repair_base_comparator(a)\n    _assert_v4_historical_source_binding(b)\n    return b\n"""

    def analyze(src: str, old: str = OLD, main: str = MAIN) -> tuple[int, int, bool]:
        tree = ast.parse(src)
        mv = module_string_values(tree)
        ins = top_fn(tree, '_insert_v4_expected_base')
        ass = top_fn(tree, '_assert_v4_historical_source_binding')
        ic = insert_candidates(ins, mv)
        bc = binding_candidates(ass, mv)
        leak = any(x['replacementUsesCurrentMain'] for x in ic) or any(x['containsCurrentMain'] for x in bc)
        return len(ic), len(bc), leak

    if analyze(good) != (1, 1, False):
        raise RuntimeError('V29 exact synthetic provenance fixture failed')
    wrong = good.replace(f"OLD='{OLD}'", "OLD='" + '0' * 40 + "'", 1)
    wi, wb, wl = analyze(wrong)
    if wi != 1 or wb != 0 or wl:
        raise RuntimeError('V29 wrong-historical-base fixture did not fail closed')
    leak = good.replace(f"OLD='{OLD}'", f"OLD='{MAIN}'", 1)
    li, lb, ll = analyze(leak)
    if li != 1 or not ll:
        raise RuntimeError('V29 current-MAIN leakage fixture did not fail closed')
    zero = good.replace("return source_text.replace(needle,repl,1)", "return source_text", 1)
    if analyze(zero)[0] != 0:
        raise RuntimeError('V29 zero insertion provenance fixture did not fail closed')
    multi = good.replace("return source_text.replace(needle,repl,1)", "x=source_text.replace(needle,repl,1)\n    return x.replace(needle,repl,1)", 1)
    if analyze(multi)[0] != 2:
        raise RuntimeError('V29 multiple insertion provenance fixture did not fail closed')
    noise = good.replace("return source_text.replace(needle,repl,1)", "# source_text.replace(needle,repl,1) expectedBaseSha\n    return source_text", 1)
    if analyze(noise)[0] != 0:
        raise RuntimeError('V29 comments/templates noise fixture did not fail closed')
    return {
        'exactSyntheticPositive': True,
        'wrongHistoricalBaseFatal': True,
        'currentMainLeakageFatal': True,
        'zeroInsertionProvenanceFatal': True,
        'multipleInsertionProvenanceFatal': True,
        'commentsTemplatesNoiseCannotSatisfy': True,
    }


def load_patched_v28(v28_raw: bytes) -> dict:
    src = v28_raw.decode()
    tree = ast.parse(src)
    dist = top_fn(tree, 'distributed')
    dist_src = source_segment(src, dist)
    old_line = "    if ss['insert'].count(OLD)!=1 or 'expectedBaseSha' not in ss['insert']:raise RuntimeError('V28 V17 insert provenance drift')"
    new_line = "    v29_static_provenance_already_passed()"
    if dist_src.count(old_line) != 1:
        raise RuntimeError('V29 exact V28 distributed patch target drift')
    patched_dist_src = dist_src.replace(old_line, new_line, 1)
    compile(patched_dist_src, '<v29-patched-v28-distributed>', 'exec')

    scope = {'__file__': str(HERE), '__name__': '_v29_frozen_v28_'}
    exec(compile(src, '<v29-frozen-v28>', 'exec'), scope, scope)
    scope['v29_static_provenance_already_passed'] = lambda: None
    exec(compile(patched_dist_src, '<v29-patched-v28-distributed>', 'exec'), scope, scope)
    if not callable(scope.get('distributed')):
        raise RuntimeError('V29 patched V28 distributed missing')
    return scope


def proof(v4_path: str, v5_path: str) -> None:
    v28_raw = exact_file('V28_FROZEN_REVIEWER', V28_BLOB)
    v17_raw = exact_file('V17_FROZEN_REVIEWER', V17_BLOB)
    v17_src = decode_v17_launcher(v17_raw)
    static = static_v4_insertion_provenance(v17_src, v28_raw.decode())
    fixtures = fixture_suite()
    write(arg('--v29-insertion-proof-out'), {
        'schemaVersion': 1,
        'status': static['status'],
        'staticProvenance': static,
        'fixtures': fixtures,
        'authorizationRefCreated': False,
        'dispatchCreated': False,
        'scientificOrdinalAllocated': False,
        'scientificOrdinalReserved': False,
        'scientificOrdinalDispatched': False,
        'seedUniverseConsumed': False,
        'scienceInvoked': False,
        'solverExecuted': False,
        'protectedResultsOpened': False,
        'publisherInvoked': False,
        'newMappingOpened': False,
        'productionInvoked': False,
        'scienceFalse': True,
    })

    scope = load_patched_v28(v28_raw)
    downstream = scope.get('proof')
    if not callable(downstream):
        raise RuntimeError('V29 frozen V28 proof entry missing')
    old_argv = list(sys.argv)
    old_v28_active = os.environ.get('V28_PREACTUAL_ACTIVE')
    old_v28_dir = os.environ.get('V28_PREACTUAL_FAILURE_DIR')
    try:
        sys.argv = [sys.argv[0], '--v28-proof-only', '--v4-metadata', v4_path, '--v5-metadata', v5_path]
        for v29flag, v28flag in (
            ('--v29-zero-runtime-proof-out', '--v28-zero-runtime-proof-out'),
            ('--v29-v5-proof-out', '--v28-v5-proof-out'),
            ('--v29-entrypoint-proof-out', '--v28-entrypoint-proof-out'),
        ):
            value = arg_from(old_argv, v29flag)
            if value:
                sys.argv += [v28flag, value]
        os.environ['V28_PREACTUAL_ACTIVE'] = '1'
        if os.environ.get('V29_PREACTUAL_FAILURE_DIR'):
            os.environ['V28_PREACTUAL_FAILURE_DIR'] = os.environ['V29_PREACTUAL_FAILURE_DIR']
        downstream(v4_path, v5_path, arg_from(old_argv, '--v29-downstream-proof-out'))
    finally:
        sys.argv = old_argv
        if old_v28_active is None:
            os.environ.pop('V28_PREACTUAL_ACTIVE', None)
        else:
            os.environ['V28_PREACTUAL_ACTIVE'] = old_v28_active
        if old_v28_dir is None:
            os.environ.pop('V28_PREACTUAL_FAILURE_DIR', None)
        else:
            os.environ['V28_PREACTUAL_FAILURE_DIR'] = old_v28_dir


def arg_from(argv: list[str], key: str) -> str | None:
    try:
        i = argv.index(key)
        return argv[i + 1]
    except (ValueError, IndexError):
        return None


def actual(v5_path: str) -> None:
    if os.environ.get('V29_NONAUTH_ACTUAL') != '1':
        raise RuntimeError('V29 ACTUAL requires explicit NON_AUTH mode')
    v28_raw = exact_file('V28_FROZEN_REVIEWER', V28_BLOB)
    scope = {'__file__': str(HERE), '__name__': '_v29_frozen_v28_actual_'}
    exec(compile(v28_raw.decode(), '<v29-frozen-v28-actual>', 'exec'), scope, scope)
    run = scope.get('actual')
    if not callable(run):
        raise RuntimeError('V29 frozen V28 ACTUAL entry missing')
    old = os.environ.get('V28_NONAUTH_ACTUAL')
    try:
        os.environ['V28_NONAUTH_ACTUAL'] = '1'
        run(v5_path)
    finally:
        if old is None:
            os.environ.pop('V28_NONAUTH_ACTUAL', None)
        else:
            os.environ['V28_NONAUTH_ACTUAL'] = old


def main() -> None:
    try:
        v5 = arg('--v5-metadata')
        if not v5:
            raise RuntimeError('V29 frozen V5 metadata input missing')
        if '--v29-proof-only' in sys.argv or os.environ.get('V29_PREACTUAL_ACTIVE') == '1':
            v4 = arg('--v4-metadata')
            if not v4:
                raise RuntimeError('V29 frozen V4 metadata input missing')
            proof(v4, v5)
            return
        actual(v5)
    except BaseException as exc:
        failure(exc)
        raise


if __name__ == '__main__':
    main()
