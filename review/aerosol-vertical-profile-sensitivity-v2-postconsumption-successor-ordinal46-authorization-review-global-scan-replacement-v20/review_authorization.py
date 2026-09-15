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
V20_STALE_RBR = b'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v20-20260914'
V20_RBR = b'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v20-20260915'
FROZEN_V4_HEAD = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
FROZEN_V4_CREATION_BASE = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
FAIL_STATUS = 'FAIL_V20_PREACTUAL_REPRESENTATION_GENERATED_EFFECTIVE_CARRIER_PROOF'


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
                raise RuntimeError('V20 frozen V17 payload SHA assignment shape drift')
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
                raise RuntimeError('V20 frozen V17 payload B85 assignment shape drift')
            payload_b85 = node.func.value.value.replace('\n', '')
    if payload_sha is None or payload_b85 is None:
        raise RuntimeError('V20 frozen V17 payload assignments missing')
    return payload_sha, payload_b85


def _source_ast(source_bytes: bytes, filename: str) -> ast.Module:
    tree = compile(source_bytes, filename, 'exec', flags=ast.PyCF_ONLY_AST, dont_inherit=True)
    if not isinstance(tree, ast.Module):
        raise RuntimeError('V20 parser did not return Module AST')
    return tree


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
        raise RuntimeError(f'V20 generated effective _rbr_assignments call count drift: {len(calls)}')
    current: ast.AST = calls[0]
    while not isinstance(current, ast.stmt):
        if current not in parents:
            raise RuntimeError('V20 generated effective RBR call has no enclosing statement')
        current = parents[current]
    return current


def _rebind_block(indent: bytes) -> bytes:
    old = V20_STALE_RBR.decode('ascii')
    new = V20_RBR.decode('ascii')
    lines = [
        '# V20 narrow repair: prove and rebind generated effective-source RBR only.',
        'import ast as _v20_ast',
        f"_v20_expected_old = {old!r}",
        f"_v20_expected_new = {new!r}",
        "_v20_tree = compile(effective, '<v20-generated-effective>', 'exec', flags=_v20_ast.PyCF_ONLY_AST, dont_inherit=True)",
        '_v20_rbr_values = []',
        'for _v20_node in _v20_ast.walk(_v20_tree):',
        '    if isinstance(_v20_node, _v20_ast.Assign) and any(isinstance(_v20_target, _v20_ast.Name) and _v20_target.id == \'RBR\' for _v20_target in _v20_node.targets):',
        "        if not isinstance(_v20_node.value, _v20_ast.Constant) or not isinstance(_v20_node.value.value, str): raise RuntimeError('V20 generated effective RBR is not a direct string literal')",
        '        _v20_rbr_values.append(_v20_node.value.value)',
        "    elif isinstance(_v20_node, _v20_ast.AnnAssign) and isinstance(_v20_node.target, _v20_ast.Name) and _v20_node.target.id == 'RBR':",
        "        if not isinstance(_v20_node.value, _v20_ast.Constant) or not isinstance(_v20_node.value.value, str): raise RuntimeError('V20 generated effective annotated RBR is not a direct string literal')",
        '        _v20_rbr_values.append(_v20_node.value.value)',
        "if len(_v20_rbr_values) != 1: raise RuntimeError(f'V20 generated effective pre-rebind RBR count drift: {len(_v20_rbr_values)}')",
        "if _v20_rbr_values[0] != _v20_expected_old: raise RuntimeError(f'V20 generated effective pre-rebind RBR unexpected: {_v20_rbr_values[0]!r}')",
        'if isinstance(effective, bytes):',
        "    _v20_old_token = _v20_expected_old.encode('ascii')",
        "    _v20_new_token = _v20_expected_new.encode('ascii')",
        "    if effective.count(_v20_old_token) != 1: raise RuntimeError(f'V20 generated effective stale carrier byte count drift: {effective.count(_v20_old_token)}')",
        '    effective = effective.replace(_v20_old_token, _v20_new_token, 1)',
        'elif isinstance(effective, str):',
        "    if effective.count(_v20_expected_old) != 1: raise RuntimeError(f'V20 generated effective stale carrier text count drift: {effective.count(_v20_expected_old)}')",
        '    effective = effective.replace(_v20_expected_old, _v20_expected_new, 1)',
        'else:',
        "    raise RuntimeError(f'V20 generated effective source type unexpected: {type(effective).__name__}')",
        "_v20_post_tree = compile(effective, '<v20-generated-effective>', 'exec', flags=_v20_ast.PyCF_ONLY_AST, dont_inherit=True)",
        '_v20_post_values = []',
        'for _v20_node in _v20_ast.walk(_v20_post_tree):',
        '    if isinstance(_v20_node, _v20_ast.Assign) and any(isinstance(_v20_target, _v20_ast.Name) and _v20_target.id == \'RBR\' for _v20_target in _v20_node.targets):',
        "        if not isinstance(_v20_node.value, _v20_ast.Constant) or not isinstance(_v20_node.value.value, str): raise RuntimeError('V20 generated effective post-rebind RBR is not a direct string literal')",
        '        _v20_post_values.append(_v20_node.value.value)',
        "    elif isinstance(_v20_node, _v20_ast.AnnAssign) and isinstance(_v20_node.target, _v20_ast.Name) and _v20_node.target.id == 'RBR':",
        "        if not isinstance(_v20_node.value, _v20_ast.Constant) or not isinstance(_v20_node.value.value, str): raise RuntimeError('V20 generated effective post-rebind annotated RBR is not a direct string literal')",
        '        _v20_post_values.append(_v20_node.value.value)',
        "if _v20_post_values != [_v20_expected_new]: raise RuntimeError(f'V20 generated effective final RBR binding drift: {_v20_post_values!r}')",
        'if isinstance(effective, bytes):',
        "    if _v20_expected_old.encode('ascii') in effective: raise RuntimeError('V20 stale date-bearing carrier survived generated effective byte rebind')",
        "    if effective.count(_v20_expected_new.encode('ascii')) != 1: raise RuntimeError(f'V20 fresh generated carrier byte count drift: {effective.count(_v20_expected_new.encode(\"ascii\"))}')",
        'else:',
        "    if _v20_expected_old in effective: raise RuntimeError('V20 stale date-bearing carrier survived generated effective text rebind')",
        "    if effective.count(_v20_expected_new) != 1: raise RuntimeError(f'V20 fresh generated carrier text count drift: {effective.count(_v20_expected_new)}')",
    ]
    out = bytearray()
    for line in lines:
        if line.startswith('    '):
            relative = len(line) - len(line.lstrip(' '))
            out.extend(indent + b' ' * relative + line.lstrip(' ').encode('ascii') + b'\n')
        else:
            out.extend(indent + line.encode('ascii') + b'\n')
    return bytes(out)


def _write_failure(exc: BaseException) -> None:
    fail_dir_text = os.environ.get('V20_PREACTUAL_FAILURE_DIR', '')
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


def _build_v20_builder_bytes() -> bytes:
    frozen_path_text = os.environ.get('V17_FROZEN_REVIEWER', '')
    if not frozen_path_text:
        raise RuntimeError('V20 frozen V17 reviewer path not supplied')
    frozen_path = Path(frozen_path_text)
    wrapper_text = frozen_path.read_text(encoding='utf-8')
    payload_sha, payload_b85 = _extract_payload(wrapper_text)
    raw = zlib.decompress(base64.b85decode(payload_b85.encode('ascii')))
    if hashlib.sha256(raw).hexdigest() != payload_sha:
        raise RuntimeError('V20 frozen V17 payload SHA-256 drift')

    filename = '<v20-generated-effective>'
    _source_ast(raw, filename)
    if b'V20' in raw or b'v20' in raw:
        raise RuntimeError('V20 successor token already present before lift')
    lifted = raw.replace(b'V17', b'V20').replace(b'v17', b'v20')
    lifted_tree = _source_ast(lifted, filename)
    call_stmt = _generated_effective_rbr_call_stmt(lifted_tree)
    if not hasattr(call_stmt, 'lineno'):
        raise RuntimeError('V20 generated effective RBR call statement has no line number')

    lines = lifted.splitlines(keepends=True)
    index = int(call_stmt.lineno) - 1
    if index < 0 or index >= len(lines):
        raise RuntimeError('V20 generated effective RBR call line outside source')
    line = lines[index]
    indent = line[: len(line) - len(line.lstrip(b' \t'))]
    if not indent or b'\t' in indent:
        raise RuntimeError('V20 generated effective RBR call indentation unexpected')
    block = _rebind_block(indent)
    patched = b''.join(lines[:index]) + block + b''.join(lines[index:])
    _source_ast(patched, filename)

    if patched.count(V20_STALE_RBR) != 1:
        raise RuntimeError(f'V20 outer builder stale RBR proof-token count drift: {patched.count(V20_STALE_RBR)}')
    if patched.count(V20_RBR) != 1:
        raise RuntimeError(f'V20 outer builder fresh RBR proof-token count drift: {patched.count(V20_RBR)}')
    for required in (b'1032', FROZEN_V4_HEAD.encode('ascii'), FROZEN_V4_CREATION_BASE.encode('ascii')):
        if required not in patched:
            raise RuntimeError(f'V20 frozen V4 identity token missing after generated-effective carrier repair: {required!r}')
    return patched


def _run() -> None:
    try:
        builder = _build_v20_builder_bytes()
        exec(compile(builder, '<v20-generated-effective>', 'exec'), globals(), globals())
    except BaseException as exc:
        if '--v20-proof-only' in sys.argv or os.environ.get('V20_PREACTUAL_ACTIVE') == '1':
            _write_failure(exc)
        raise


if __name__ == '__main__':
    _run()
