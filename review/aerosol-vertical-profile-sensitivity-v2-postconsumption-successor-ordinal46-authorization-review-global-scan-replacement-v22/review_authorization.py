from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import sys
import zlib
from pathlib import Path

FROZEN_V17_HEAD = 'fcd8f73db3d8cfb5899991756212ee653aa3c586'
FROZEN_V17_BLOB = '06867e14710f15cade77ed24fbdc33dafb9f2f74'
V22_STALE_RBR = b'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v22-20260914'
V22_RBR = b'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v22-20260915'
FROZEN_V4_HEAD = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
FROZEN_V4_CREATION_BASE = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
FAIL_STATUS = 'FAIL_V22_PREACTUAL_REPRESENTATION_GENERATED_EFFECTIVE_CARRIER_SUBPROCESS_PROOF'
ZERO_PROOF_STATUS = 'PASS_V22_PREACTUAL_ZERO_RUNTIME_PROOF_TARGET_BINDING'


def _argv_value(flag: str) -> str | None:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


def _extract_payload(wrapper_text: str) -> tuple[str, str]:
    tree = ast.parse(wrapper_text)
    payload_sha = None
    payload_b85 = None
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            continue
        name = stmt.targets[0].id
        if name == 'PAYLOAD_SHA256':
            if not isinstance(stmt.value, ast.Constant) or not isinstance(stmt.value.value, str):
                raise RuntimeError('V22 frozen V17 payload SHA assignment shape drift')
            payload_sha = stmt.value.value
        elif name == 'PAYLOAD_B85':
            node = stmt.value
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'replace'
                and isinstance(node.func.value, ast.Constant)
                and isinstance(node.func.value.value, str)
                and len(node.args) == 2
                and all(isinstance(arg, ast.Constant) and isinstance(arg.value, str) for arg in node.args)
                and node.args[0].value == '\n'
                and node.args[1].value == ''
                and not node.keywords
            ):
                raise RuntimeError('V22 frozen V17 payload B85 assignment shape drift')
            payload_b85 = node.func.value.value.replace('\n', '')
    if payload_sha is None or payload_b85 is None:
        raise RuntimeError('V22 frozen V17 payload assignments missing')
    return payload_sha, payload_b85


def _source_ast(source_bytes: bytes, filename: str) -> ast.Module:
    tree = compile(source_bytes, filename, 'exec', flags=ast.PyCF_ONLY_AST, dont_inherit=True)
    if not isinstance(tree, ast.Module):
        raise RuntimeError('V22 parser did not return Module AST')
    return tree


def _direct_subprocess_surface(source_bytes: bytes, filename: str) -> list[str]:
    tree = _source_ast(source_bytes, filename)
    calls: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id == 'subprocess':
            calls.append(node.func.attr)
    return calls


def _generated_effective_rbr_call_stmt(tree: ast.Module) -> ast.stmt:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != '_rbr_assignments':
            continue
        if len(node.args) != 1 or not isinstance(node.args[0], ast.Name) or node.args[0].id != 'effective':
            continue
        if node.keywords:
            continue
        calls.append(node)
    if len(calls) != 1:
        raise RuntimeError(f'V22 generated effective _rbr_assignments call count drift: {len(calls)}')
    current: ast.AST = calls[0]
    while not isinstance(current, ast.stmt):
        if current not in parents:
            raise RuntimeError('V22 generated effective RBR call has no enclosing statement')
        current = parents[current]
    return current


def _rebind_block(indent: bytes) -> bytes:
    old = V22_STALE_RBR.decode('ascii')
    new = V22_RBR.decode('ascii')
    lines = [
        '# V22 narrow repair: generated effective RBR + zero-runtime proof target binding only.',
        'import ast as _v22_ast',
        'import hashlib as _v22_hashlib',
        f"_v22_expected_old = {old!r}",
        f"_v22_expected_new = {new!r}",
        "_v22_tree = compile(effective, '<v22-generated-effective>', 'exec', flags=_v22_ast.PyCF_ONLY_AST, dont_inherit=True)",
        '_v22_rbr_values = []',
        'for _v22_node in _v22_ast.walk(_v22_tree):',
        '    if isinstance(_v22_node, _v22_ast.Assign) and any(isinstance(_v22_target, _v22_ast.Name) and _v22_target.id == \'RBR\' for _v22_target in _v22_node.targets):',
        "        if not isinstance(_v22_node.value, _v22_ast.Constant) or not isinstance(_v22_node.value.value, str): raise RuntimeError('V22 generated effective RBR is not a direct string literal')",
        '        _v22_rbr_values.append(_v22_node.value.value)',
        "    elif isinstance(_v22_node, _v22_ast.AnnAssign) and isinstance(_v22_node.target, _v22_ast.Name) and _v22_node.target.id == 'RBR':",
        "        if not isinstance(_v22_node.value, _v22_ast.Constant) or not isinstance(_v22_node.value.value, str): raise RuntimeError('V22 generated effective annotated RBR is not a direct string literal')",
        '        _v22_rbr_values.append(_v22_node.value.value)',
        "if len(_v22_rbr_values) != 1: raise RuntimeError(f'V22 generated effective pre-rebind RBR count drift: {len(_v22_rbr_values)}')",
        "if _v22_rbr_values[0] != _v22_expected_old: raise RuntimeError(f'V22 generated effective pre-rebind RBR unexpected: {_v22_rbr_values[0]!r}')",
        'if isinstance(effective, bytes):',
        "    _v22_old_token = _v22_expected_old.encode('ascii')",
        "    _v22_new_token = _v22_expected_new.encode('ascii')",
        "    if effective.count(_v22_old_token) != 1: raise RuntimeError(f'V22 generated effective stale carrier byte count drift: {effective.count(_v22_old_token)}')",
        '    effective = effective.replace(_v22_old_token, _v22_new_token, 1)',
        'elif isinstance(effective, str):',
        "    if effective.count(_v22_expected_old) != 1: raise RuntimeError(f'V22 generated effective stale carrier text count drift: {effective.count(_v22_expected_old)}')",
        '    effective = effective.replace(_v22_expected_old, _v22_expected_new, 1)',
        'else:',
        "    raise RuntimeError(f'V22 generated effective source type unexpected: {type(effective).__name__}')",
        "_v22_post_tree = compile(effective, '<v22-generated-effective>', 'exec', flags=_v22_ast.PyCF_ONLY_AST, dont_inherit=True)",
        '_v22_zero_funcs = [_v22_node for _v22_node in _v22_ast.walk(_v22_post_tree) if isinstance(_v22_node, (_v22_ast.FunctionDef, _v22_ast.AsyncFunctionDef)) and _v22_node.name == \'zero_runtime_static_proof\']',
        "if len(_v22_zero_funcs) != 1: raise RuntimeError(f'V22 zero_runtime_static_proof definition count drift: {len(_v22_zero_funcs)}')",
        '_v22_zero_func = _v22_zero_funcs[0]',
        '_v22_script_reads = []',
        'for _v22_node in _v22_ast.walk(_v22_zero_func):',
        '    if not isinstance(_v22_node, _v22_ast.Assign) or len(_v22_node.targets) != 1 or not isinstance(_v22_node.targets[0], _v22_ast.Name) or _v22_node.targets[0].id != \'script\':',
        '        continue',
        '    _v22_value = _v22_node.value',
        '    if not isinstance(_v22_value, _v22_ast.Call) or _v22_value.args or _v22_value.keywords:',
        '        continue',
        '    if not isinstance(_v22_value.func, _v22_ast.Attribute) or _v22_value.func.attr != \'read_text\':',
        '        continue',
        '    _v22_base = _v22_value.func.value',
        '    if not isinstance(_v22_base, _v22_ast.BinOp) or not isinstance(_v22_base.op, _v22_ast.Div):',
        '        continue',
        '    if not isinstance(_v22_base.left, _v22_ast.Name) or _v22_base.left.id != \'INFRA\':',
        '        continue',
        '    if not isinstance(_v22_base.right, _v22_ast.Name) or _v22_base.right.id != \'SCRIPT\':',
        '        continue',
        '    _v22_script_reads.append(_v22_node)',
        "if len(_v22_script_reads) != 1: raise RuntimeError(f'V22 historical self-file scanner assignment count drift: {len(_v22_script_reads)}')",
        '_v22_script_read = _v22_script_reads[0]',
        "if _v22_script_read.lineno != _v22_script_read.end_lineno: raise RuntimeError('V22 scanner assignment is not line-local')",
        '_v22_effective_lines = effective.splitlines(keepends=True)',
        '_v22_script_index = int(_v22_script_read.lineno) - 1',
        "if _v22_script_index < 0 or _v22_script_index >= len(_v22_effective_lines): raise RuntimeError('V22 scanner assignment line outside generated effective source')",
        '_v22_script_line = _v22_effective_lines[_v22_script_index]',
        "_v22_script_indent = _v22_script_line[: len(_v22_script_line) - len(_v22_script_line.lstrip(b' \\t' if isinstance(_v22_script_line, bytes) else ' \\t'))]",
        "if not _v22_script_indent: raise RuntimeError('V22 scanner assignment indentation missing')",
        'if isinstance(effective, bytes):',
        "    _v22_nl = b'\\n' if _v22_script_line.endswith(b'\\n') else b''",
        "    _v22_replacement = _v22_script_indent + b'script = _V22_ZERO_RUNTIME_STATIC_SOURCE' + _v22_nl + _v22_script_indent + b\"req(hashlib.sha256(script).hexdigest() == _V22_ZERO_RUNTIME_STATIC_SOURCE_SHA256, 'V22 zero-runtime proof target SHA drift')\" + _v22_nl",
        '    _v22_effective_lines[_v22_script_index:_v22_script_index + 1] = [_v22_replacement]',
        "    effective = b''.join(_v22_effective_lines)",
        'else:',
        "    _v22_nl = '\\n' if _v22_script_line.endswith('\\n') else ''",
        "    _v22_replacement = _v22_script_indent + 'script = _V22_ZERO_RUNTIME_STATIC_SOURCE' + _v22_nl + _v22_script_indent + \"req(hashlib.sha256(script).hexdigest() == _V22_ZERO_RUNTIME_STATIC_SOURCE_SHA256, 'V22 zero-runtime proof target SHA drift')\" + _v22_nl",
        '    _v22_effective_lines[_v22_script_index:_v22_script_index + 1] = [_v22_replacement]',
        "    effective = ''.join(_v22_effective_lines)",
        "_v22_final_tree = compile(effective, '<v22-generated-effective>', 'exec', flags=_v22_ast.PyCF_ONLY_AST, dont_inherit=True)",
        '_v22_post_values = []',
        'for _v22_node in _v22_ast.walk(_v22_final_tree):',
        '    if isinstance(_v22_node, _v22_ast.Assign) and any(isinstance(_v22_target, _v22_ast.Name) and _v22_target.id == \'RBR\' for _v22_target in _v22_node.targets):',
        "        if not isinstance(_v22_node.value, _v22_ast.Constant) or not isinstance(_v22_node.value.value, str): raise RuntimeError('V22 generated effective post-rebind RBR is not a direct string literal')",
        '        _v22_post_values.append(_v22_node.value.value)',
        "    elif isinstance(_v22_node, _v22_ast.AnnAssign) and isinstance(_v22_node.target, _v22_ast.Name) and _v22_node.target.id == 'RBR':",
        "        if not isinstance(_v22_node.value, _v22_ast.Constant) or not isinstance(_v22_node.value.value, str): raise RuntimeError('V22 generated effective post-rebind annotated RBR is not a direct string literal')",
        '        _v22_post_values.append(_v22_node.value.value)',
        "if _v22_post_values != [_v22_expected_new]: raise RuntimeError(f'V22 generated effective final RBR binding drift: {_v22_post_values!r}')",
        '_v22_final_zero_funcs = [_v22_node for _v22_node in _v22_ast.walk(_v22_final_tree) if isinstance(_v22_node, (_v22_ast.FunctionDef, _v22_ast.AsyncFunctionDef)) and _v22_node.name == \'zero_runtime_static_proof\']',
        "if len(_v22_final_zero_funcs) != 1: raise RuntimeError(f'V22 final zero_runtime_static_proof definition count drift: {len(_v22_final_zero_funcs)}')",
        '_v22_final_script_bindings = []',
        'for _v22_node in _v22_ast.walk(_v22_final_zero_funcs[0]):',
        '    if isinstance(_v22_node, _v22_ast.Assign) and len(_v22_node.targets) == 1 and isinstance(_v22_node.targets[0], _v22_ast.Name) and _v22_node.targets[0].id == \'script\':',
        '        _v22_final_script_bindings.append(_v22_node.value)',
        "if len(_v22_final_script_bindings) != 1 or not isinstance(_v22_final_script_bindings[0], _v22_ast.Name) or _v22_final_script_bindings[0].id != '_V22_ZERO_RUNTIME_STATIC_SOURCE': raise RuntimeError('V22 final scanner proof-target binding drift')",
        "_v22_target_source = globals().get('_V22_ZERO_RUNTIME_STATIC_SOURCE')",
        "_v22_target_sha = globals().get('_V22_ZERO_RUNTIME_STATIC_SOURCE_SHA256')",
        "if not isinstance(_v22_target_source, bytes) or not isinstance(_v22_target_sha, str): raise RuntimeError('V22 exact proof target globals missing')",
        "if _v22_hashlib.sha256(_v22_target_source).hexdigest() != _v22_target_sha: raise RuntimeError('V22 exact proof target global SHA drift')",
        "_v22_target_tree = compile(_v22_target_source, '<v22-authoritative-decompressed-builder-proof-target>', 'exec', flags=_v22_ast.PyCF_ONLY_AST, dont_inherit=True)",
        '_v22_target_surface = []',
        'for _v22_node in _v22_ast.walk(_v22_target_tree):',
        '    if isinstance(_v22_node, _v22_ast.Call) and isinstance(_v22_node.func, _v22_ast.Attribute) and isinstance(_v22_node.func.value, _v22_ast.Name) and _v22_node.func.value.id == \'subprocess\':',
        '        _v22_target_surface.append(_v22_node.func.attr)',
        "if _v22_target_surface != ['run']: raise RuntimeError(f'V22 proof-target subprocess API surface drift: {_v22_target_surface!r}')",
        "globals()['V22_ZERO_RUNTIME_STATIC_PROOF_AUDIT'] = {'status': 'PASS_V22_PREACTUAL_ZERO_RUNTIME_PROOF_TARGET_BINDING', 'proofTargetSha256': _v22_target_sha, 'proofTargetDirectSubprocessSurface': list(_v22_target_surface), 'proofTargetIsExactCompiledBuilderBytes': True, 'scannerReboundFromOuterLauncher': True, 'scannerExpectedSurfacePreserved': True, 'scienceFalse': True}",
        'if isinstance(effective, bytes):',
        "    if _v22_expected_old.encode('ascii') in effective: raise RuntimeError('V22 stale date-bearing carrier survived generated effective byte rebind')",
        "    if effective.count(_v22_expected_new.encode('ascii')) != 1: raise RuntimeError(f'V22 fresh generated carrier byte count drift: {effective.count(_v22_expected_new.encode(\"ascii\"))}')",
        'else:',
        "    if _v22_expected_old in effective: raise RuntimeError('V22 stale date-bearing carrier survived generated effective text rebind')",
        "    if effective.count(_v22_expected_new) != 1: raise RuntimeError(f'V22 fresh generated carrier text count drift: {effective.count(_v22_expected_new)}')",
    ]
    out = bytearray()
    for line in lines:
        if line.startswith('    '):
            relative = len(line) - len(line.lstrip(' '))
            out.extend(indent + b' ' * relative + line.lstrip(' ').encode('ascii') + b'\n')
        else:
            out.extend(indent + line.encode('ascii') + b'\n')
    return bytes(out)


def _prove_local_rebind_block(block: bytes, indent: bytes, patched: bytes, lifted: bytes) -> None:
    marker = b'# V22 narrow repair: generated effective RBR + zero-runtime proof target binding only.\n'
    if block.count(marker) != 1 or patched.count(marker) != 1:
        raise RuntimeError('V22 generated-effective repair block marker count drift')
    if block.count(V22_STALE_RBR) != 1:
        raise RuntimeError(f'V22 local repair stale carrier token count drift: {block.count(V22_STALE_RBR)}')
    if block.count(V22_RBR) != 1:
        raise RuntimeError(f'V22 local repair fresh carrier token count drift: {block.count(V22_RBR)}')
    if patched.count(block) != 1:
        raise RuntimeError(f'V22 generated-effective repair block count drift: {patched.count(block)}')
    if patched.replace(block, b'', 1) != lifted:
        raise RuntimeError('V22 generated-effective repair block is not the only outer-builder edit')

    local_lines = block.splitlines(keepends=True)
    if not local_lines or any(line.strip() and not line.startswith(indent) for line in local_lines):
        raise RuntimeError('V22 generated-effective repair block indentation drift')
    local = b''.join(line[len(indent):] if line.strip() else line for line in local_lines)
    tree = _source_ast(local, '<v22-local-generated-effective-repair-block>')

    expected_assignments: dict[str, list[str]] = {'_v22_expected_old': [], '_v22_expected_new': []}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            continue
        name = stmt.targets[0].id
        if name not in expected_assignments:
            continue
        if not isinstance(stmt.value, ast.Constant) or not isinstance(stmt.value.value, str):
            raise RuntimeError(f'V22 local repair {name} is not a direct string literal')
        expected_assignments[name].append(stmt.value.value)
    if expected_assignments['_v22_expected_old'] != [V22_STALE_RBR.decode('ascii')]:
        raise RuntimeError(f"V22 local repair old-carrier binding drift: {expected_assignments['_v22_expected_old']!r}")
    if expected_assignments['_v22_expected_new'] != [V22_RBR.decode('ascii')]:
        raise RuntimeError(f"V22 local repair new-carrier binding drift: {expected_assignments['_v22_expected_new']!r}")

    final_checks = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if not isinstance(test.left, ast.Name) or test.left.id != '_v22_post_values':
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.NotEq) or len(test.comparators) != 1:
            continue
        comparator = test.comparators[0]
        if not isinstance(comparator, ast.List) or len(comparator.elts) != 1:
            continue
        elt = comparator.elts[0]
        if not isinstance(elt, ast.Name) or elt.id != '_v22_expected_new':
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Raise):
            raise RuntimeError('V22 local final generated-effective RBR check body drift')
        final_checks.append(node)
    if len(final_checks) != 1:
        raise RuntimeError(f'V22 local final generated-effective RBR check count drift: {len(final_checks)}')

    if local.count(b"script = _V22_ZERO_RUNTIME_STATIC_SOURCE") != 2:
        raise RuntimeError('V22 local scanner binding construction/proof token count drift')
    if b"proofTargetDirectSubprocessSurface': list(_v22_target_surface)" not in local:
        raise RuntimeError('V22 local proof-target subprocess audit missing')
    if b"_v22_target_surface != ['run']" not in local:
        raise RuntimeError('V22 exact ordered subprocess surface guard missing')


def _write_failure(exc: BaseException) -> None:
    fail_dir_text = os.environ.get('V22_PREACTUAL_FAILURE_DIR', '')
    if not fail_dir_text:
        return
    fail_dir = Path(fail_dir_text)
    fail_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'status': FAIL_STATUS,
        'type': type(exc).__name__,
        'message': str(exc),
        'authorizationRefCreated': False,
        'dispatchCreated': False,
        'scientificOrdinalAllocated': False,
        'seedUniverseConsumed': False,
        'scienceInvoked': False,
        'solverExecuted': False,
        'protectedResultsOpened': False,
        'scienceFalse': True,
    }
    out = fail_dir / 'failure.json'
    out.write_text(json.dumps(payload, sort_keys=True) + '\n', encoding='utf-8')


def _build_v22_builder_bytes() -> bytes:
    frozen_path_text = os.environ.get('V17_FROZEN_REVIEWER', '')
    if not frozen_path_text:
        raise RuntimeError('V22 frozen V17 reviewer path not supplied')
    frozen_path = Path(frozen_path_text)
    wrapper_text = frozen_path.read_text(encoding='utf-8')
    payload_sha, payload_b85 = _extract_payload(wrapper_text)
    raw = zlib.decompress(base64.b85decode(payload_b85.encode('ascii')))
    if hashlib.sha256(raw).hexdigest() != payload_sha:
        raise RuntimeError('V22 frozen V17 payload SHA-256 drift')

    filename = '<v22-generated-effective>'
    _source_ast(raw, filename)
    if b'V22' in raw or b'v22' in raw:
        raise RuntimeError('V22 successor token already present before lift')
    lifted = raw.replace(b'V17', b'V22').replace(b'v17', b'v22')
    lifted_tree = _source_ast(lifted, filename)
    call_stmt = _generated_effective_rbr_call_stmt(lifted_tree)
    if not hasattr(call_stmt, 'lineno'):
        raise RuntimeError('V22 generated effective RBR call statement has no line number')

    lines = lifted.splitlines(keepends=True)
    index = int(call_stmt.lineno) - 1
    if index < 0 or index >= len(lines):
        raise RuntimeError('V22 generated effective RBR call line outside source')
    line = lines[index]
    indent = line[: len(line) - len(line.lstrip(b' \t'))]
    if not indent or b'\t' in indent:
        raise RuntimeError('V22 generated effective RBR call indentation unexpected')
    block = _rebind_block(indent)
    patched = b''.join(lines[:index]) + block + b''.join(lines[index:])
    patched_tree = _source_ast(patched, filename)

    if patched.count(V22_STALE_RBR) != 1:
        raise RuntimeError(f'V22 outer builder stale RBR proof-token count drift: {patched.count(V22_STALE_RBR)}')
    _prove_local_rebind_block(block, indent, patched, lifted)
    patched_call_stmt = _generated_effective_rbr_call_stmt(patched_tree)
    if not hasattr(patched_call_stmt, 'lineno'):
        raise RuntimeError('V22 patched generated effective RBR call statement has no line number')
    patched_lines = patched.splitlines(keepends=True)
    patched_index = int(patched_call_stmt.lineno) - 1
    if patched_index < 0 or patched_index >= len(patched_lines):
        raise RuntimeError('V22 patched generated effective RBR call line outside source')
    if not b''.join(patched_lines[:patched_index]).endswith(block):
        raise RuntimeError('V22 local generated-effective repair block is not immediately before final RBR assignment check')

    for required in (b'1032', FROZEN_V4_HEAD.encode('ascii'), FROZEN_V4_CREATION_BASE.encode('ascii')):
        if required not in patched:
            raise RuntimeError(f'V22 frozen V4 identity token missing after generated-effective repair: {required!r}')
    return patched


def _write_zero_proof(path_text: str, audit: dict[str, object]) -> None:
    target = Path(path_text)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(audit)
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    payload['receiptSha256'] = hashlib.sha256(canonical).hexdigest()
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _run() -> None:
    try:
        builder = _build_v22_builder_bytes()
        builder_sha = hashlib.sha256(builder).hexdigest()
        surface = _direct_subprocess_surface(builder, '<v22-authoritative-decompressed-builder-proof-target>')
        if surface != ['run']:
            raise RuntimeError(f'V22 authoritative proof-target subprocess API surface drift: {surface!r}')
        globals()['_V22_ZERO_RUNTIME_STATIC_SOURCE'] = builder
        globals()['_V22_ZERO_RUNTIME_STATIC_SOURCE_SHA256'] = builder_sha
        exec(compile(builder, '<v22-generated-effective>', 'exec'), globals(), globals())
        audit = globals().get('V22_ZERO_RUNTIME_STATIC_PROOF_AUDIT')
        if not isinstance(audit, dict):
            raise RuntimeError('V22 zero-runtime binding audit missing after generated builder execution')
        expected = {
            'status': ZERO_PROOF_STATUS,
            'proofTargetSha256': builder_sha,
            'proofTargetDirectSubprocessSurface': ['run'],
            'proofTargetIsExactCompiledBuilderBytes': True,
            'scannerReboundFromOuterLauncher': True,
            'scannerExpectedSurfacePreserved': True,
            'scienceFalse': True,
        }
        if audit != expected:
            raise RuntimeError(f'V22 zero-runtime binding audit drift: {audit!r}')
        zero_out = _argv_value('--v22-zero-runtime-proof-out')
        if zero_out:
            _write_zero_proof(zero_out, audit)
    except BaseException as exc:
        if '--v22-proof-only' in sys.argv or os.environ.get('V22_PREACTUAL_ACTIVE') == '1':
            _write_failure(exc)
        raise


if __name__ == '__main__':
    _run()
