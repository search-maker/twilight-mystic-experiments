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
FROZEN_V17_STALE_RBR_AFTER_LIFT = b'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v19-20260914'
V19_RBR = b'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v19-20260915'
FROZEN_V4_HEAD = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
FROZEN_V4_CREATION_BASE = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
FAIL_STATUS = 'FAIL_V19_PREACTUAL_REPRESENTATION_CARRIER_PROOF'


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
                raise RuntimeError('V19 frozen V17 payload SHA assignment shape drift')
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
                raise RuntimeError('V19 frozen V17 payload B85 assignment shape drift')
            payload_b85 = node.func.value.value.replace('\n', '')
    if payload_sha is None or payload_b85 is None:
        raise RuntimeError('V19 frozen V17 payload assignments missing')
    return payload_sha, payload_b85


def _source_ast(source_bytes: bytes, filename: str) -> ast.Module:
    tree = compile(source_bytes, filename, 'exec', flags=ast.PyCF_ONLY_AST, dont_inherit=True)
    if not isinstance(tree, ast.Module):
        raise RuntimeError('V19 parser did not return Module AST')
    return tree


def _rbr_binding(tree: ast.AST) -> tuple[ast.AST, ast.Constant]:
    matches: list[tuple[ast.AST, ast.Constant]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == 'RBR' for target in node.targets):
                if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                    raise RuntimeError('V19 final RBR binding is not a constant string')
                matches.append((node, node.value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == 'RBR':
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                raise RuntimeError('V19 final annotated RBR binding is not a constant string')
            matches.append((node, node.value))
    if len(matches) != 1:
        raise RuntimeError(f'V19 final RBR binding count drift: {len(matches)}')
    return matches[0]


def _write_failure(exc: BaseException) -> None:
    fail_dir_text = os.environ.get('V19_PREACTUAL_FAILURE_DIR', '')
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


def _build_v19_effective_bytes() -> bytes:
    frozen_path_text = os.environ.get('V17_FROZEN_REVIEWER', '')
    if not frozen_path_text:
        raise RuntimeError('V19 frozen V17 reviewer path not supplied')
    frozen_path = Path(frozen_path_text)
    wrapper_text = frozen_path.read_text(encoding='utf-8')
    payload_sha, payload_b85 = _extract_payload(wrapper_text)
    raw = zlib.decompress(base64.b85decode(payload_b85.encode('ascii')))
    if hashlib.sha256(raw).hexdigest() != payload_sha:
        raise RuntimeError('V19 frozen V17 payload SHA-256 drift')

    # The exact decompressed bytes are authoritative. Parse them with the same
    # Python source semantics used by execution; do not decode using a fixed text encoding.
    filename = str(Path(__file__).resolve())
    _source_ast(raw, filename)

    # Standard successor lift is byte-local and preserves every unrelated source byte.
    if b'V19' in raw or b'v19' in raw:
        raise RuntimeError('V19 successor token already present before lift')
    lifted = raw.replace(b'V17', b'V19').replace(b'v17', b'v19')
    lifted_tree = _source_ast(lifted, filename)
    _, rbr_value = _rbr_binding(lifted_tree)
    stale_text = FROZEN_V17_STALE_RBR_AFTER_LIFT.decode('ascii')
    if rbr_value.value != stale_text:
        raise RuntimeError(f'V19 inherited final carrier identity unexpected before rebind: {rbr_value.value!r}')
    if lifted.count(FROZEN_V17_STALE_RBR_AFTER_LIFT) != 1:
        raise RuntimeError(f'V19 stale carrier byte occurrence count drift: {lifted.count(FROZEN_V17_STALE_RBR_AFTER_LIFT)}')

    # V19-only repair: replace only the exact stale carrier bytes after AST proof.
    patched = lifted.replace(FROZEN_V17_STALE_RBR_AFTER_LIFT, V19_RBR, 1)
    patched_tree = _source_ast(patched, filename)
    _, final_rbr_value = _rbr_binding(patched_tree)
    fresh_text = V19_RBR.decode('ascii')
    if final_rbr_value.value != fresh_text:
        raise RuntimeError(f'V19 final carrier identity binding drift: {final_rbr_value.value!r}')
    if FROZEN_V17_STALE_RBR_AFTER_LIFT in patched:
        raise RuntimeError('V19 stale date-bearing carrier survived final byte patch')
    if patched.count(V19_RBR) != 1:
        raise RuntimeError(f'V19 fresh carrier byte occurrence count drift: {patched.count(V19_RBR)}')

    # Frozen historical-V4 identity must remain represented in the carried bytes.
    for required in (b'1032', FROZEN_V4_HEAD.encode('ascii'), FROZEN_V4_CREATION_BASE.encode('ascii')):
        if required not in patched:
            raise RuntimeError(f'V19 frozen V4 identity token missing after carrier rebind: {required!r}')
    return patched


def _run() -> None:
    try:
        effective = _build_v19_effective_bytes()
        exec(compile(effective, str(Path(__file__).resolve()), 'exec'), globals(), globals())
    except BaseException as exc:
        if '--v19-proof-only' in sys.argv or os.environ.get('V19_PREACTUAL_ACTIVE') == '1':
            _write_failure(exc)
        raise


if __name__ == '__main__':
    _run()
