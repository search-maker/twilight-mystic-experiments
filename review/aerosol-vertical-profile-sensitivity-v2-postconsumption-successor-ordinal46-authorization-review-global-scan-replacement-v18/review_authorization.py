from __future__ import annotations

import ast
import base64
import hashlib
import os
import zlib
from pathlib import Path

FROZEN_V17_HEAD = 'fcd8f73db3d8cfb5899991756212ee653aa3c586'
FROZEN_V17_BLOB = '06867e14710f15cade77ed24fbdc33dafb9f2f74'
FROZEN_V17_STALE_RBR_AFTER_LIFT = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v18-20260914'
V18_RBR = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v18-20260915'
FROZEN_V4_HEAD = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
FROZEN_V4_CREATION_BASE = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'


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
                raise RuntimeError('V18 frozen V17 payload SHA assignment shape drift')
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
                raise RuntimeError('V18 frozen V17 payload B85 assignment shape drift')
            payload_b85 = node.func.value.value.replace('\n', '')
    if payload_sha is None or payload_b85 is None:
        raise RuntimeError('V18 frozen V17 payload assignments missing')
    return payload_sha, payload_b85


def _rbr_binding(tree: ast.AST) -> tuple[ast.AST, ast.Constant]:
    matches: list[tuple[ast.AST, ast.Constant]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == 'RBR' for target in node.targets):
                if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                    raise RuntimeError('V18 final RBR binding is not a constant string')
                matches.append((node, node.value))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == 'RBR':
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                raise RuntimeError('V18 final annotated RBR binding is not a constant string')
            matches.append((node, node.value))
    if len(matches) != 1:
        raise RuntimeError(f'V18 final RBR binding count drift: {len(matches)}')
    return matches[0]


def _replace_constant_source(source: str, value_node: ast.Constant, replacement: str) -> str:
    if value_node.lineno is None or value_node.end_lineno is None or value_node.col_offset is None or value_node.end_col_offset is None:
        raise RuntimeError('V18 final RBR source span missing')
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: value_node.lineno - 1]) + value_node.col_offset
    end = sum(len(line) for line in lines[: value_node.end_lineno - 1]) + value_node.end_col_offset
    return source[:start] + repr(replacement) + source[end:]


def _build_v18_effective_source() -> str:
    frozen_path_text = os.environ.get('V17_FROZEN_REVIEWER', '')
    if not frozen_path_text:
        raise RuntimeError('V18 frozen V17 reviewer path not supplied')
    frozen_path = Path(frozen_path_text)
    wrapper_text = frozen_path.read_text(encoding='utf-8')
    payload_sha, payload_b85 = _extract_payload(wrapper_text)
    raw = zlib.decompress(base64.b85decode(payload_b85.encode('ascii')))
    if hashlib.sha256(raw).hexdigest() != payload_sha:
        raise RuntimeError('V18 frozen V17 payload SHA-256 drift')
    source = raw.decode('utf-8')

    # Standard successor lift: only the current-version token changes here.
    if 'V18' in source or 'v18' in source:
        raise RuntimeError('V18 successor token already present before lift')
    lifted = source.replace('V17', 'V18').replace('v17', 'v18')

    # V18-only repair: structurally rebind the unique final effective-source RBR.
    lifted_tree = ast.parse(lifted)
    _, rbr_value = _rbr_binding(lifted_tree)
    if rbr_value.value != FROZEN_V17_STALE_RBR_AFTER_LIFT:
        raise RuntimeError(f'V18 inherited final carrier identity unexpected before rebind: {rbr_value.value!r}')
    patched = _replace_constant_source(lifted, rbr_value, V18_RBR)

    # Fail-closed structural proof after the exact local patch.
    patched_tree = ast.parse(patched)
    _, final_rbr_value = _rbr_binding(patched_tree)
    if final_rbr_value.value != V18_RBR:
        raise RuntimeError(f'V18 final carrier identity binding drift: {final_rbr_value.value!r}')
    if FROZEN_V17_STALE_RBR_AFTER_LIFT == final_rbr_value.value:
        raise RuntimeError('V18 stale date-bearing carrier survived as final binding')

    # Frozen historical-V4 identity must remain represented in the carried source.
    for required in ('1032', FROZEN_V4_HEAD, FROZEN_V4_CREATION_BASE):
        if required not in patched:
            raise RuntimeError(f'V18 frozen V4 identity token missing after carrier rebind: {required}')
    return patched


def _run() -> None:
    effective = _build_v18_effective_source()
    exec(compile(effective, str(Path(__file__).resolve()), 'exec'), globals(), globals())


if __name__ == '__main__':
    _run()
