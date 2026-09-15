from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path

FROZEN_V22_HEAD = '4b69615cd83a7bcec7e9fa7be17fd48b982367d8'
FROZEN_V22_BLOB = '98fe1ca468a44ad385005111f38dc48c89a08b9e'
FROZEN_V5_PR = 1033
FROZEN_V5_HEAD = '0d7ad7030aacc1c34bca93fef6c02fd7dcf776c2'
FROZEN_V5_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5-20260910'
FROZEN_V5_BASE_REF = 'main'
FROZEN_V5_CREATION_BASE = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
SUCCESSOR_MAIN = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'
V5_PROOF_STATUS = 'PASS_V23_PREACTUAL_HISTORICAL_V5_BASE_SEPARATION_PROOF'
FAIL_STATUS = 'FAIL_V23_PREACTUAL_HISTORICAL_V5_BASE_SEPARATION_PROOF'
HERE = Path(__file__).resolve()


def _argv_value(flag: str) -> str | None:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def _write_failure(exc: BaseException) -> None:
    fail_dir_text = os.environ.get('V23_PREACTUAL_FAILURE_DIR', '')
    if not fail_dir_text:
        return
    fail_dir = Path(fail_dir_text)
    fail_dir.mkdir(parents=True, exist_ok=True)
    path = fail_dir / 'failure.json'
    if path.exists():
        return
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
    path.write_text(json.dumps(payload, sort_keys=True) + '\n', encoding='utf-8')


def _require_v5_metadata(meta: object) -> None:
    if not isinstance(meta, dict):
        raise RuntimeError('V23 frozen V5 PR metadata is not an object')
    if meta.get('state') != 'open' or meta.get('draft') is not True or meta.get('merged_at') is not None:
        raise RuntimeError('V23 frozen V5 PR state/merged identity drift')
    head = meta.get('head')
    base = meta.get('base')
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise RuntimeError('V23 frozen V5 PR head/base metadata shape drift')
    if head.get('sha') != FROZEN_V5_HEAD:
        raise RuntimeError('V23 frozen V5 PR head drift')
    if head.get('ref') != FROZEN_V5_BRANCH:
        raise RuntimeError('V23 frozen V5 PR branch drift')
    if base.get('ref') != FROZEN_V5_BASE_REF:
        raise RuntimeError('V23 frozen V5 PR base-ref drift')
    if base.get('sha') != FROZEN_V5_CREATION_BASE:
        raise RuntimeError('V23 frozen V5 PR historical base drift')


def _load_observed_v5_metadata() -> dict[str, object]:
    path_text = _argv_value('--v5-metadata')
    if not path_text:
        raise RuntimeError('V23 frozen V5 metadata path missing')
    value = json.loads(Path(path_text).read_text(encoding='utf-8'))
    _require_v5_metadata(value)
    return value


def _expect_meta_failure(meta: dict[str, object], label: str) -> bool:
    try:
        _require_v5_metadata(meta)
    except RuntimeError:
        return True
    raise RuntimeError(f'V23 V5 metadata negative fixture unexpectedly accepted: {label}')


def _metadata_fixtures() -> dict[str, bool]:
    canonical: dict[str, object] = {
        'state': 'open',
        'draft': True,
        'merged_at': None,
        'head': {'sha': FROZEN_V5_HEAD, 'ref': FROZEN_V5_BRANCH},
        'base': {'sha': FROZEN_V5_CREATION_BASE, 'ref': FROZEN_V5_BASE_REF},
    }
    _require_v5_metadata(canonical)

    def copy_meta() -> dict[str, object]:
        return json.loads(json.dumps(canonical))

    wrong_base = copy_meta(); wrong_base['base']['sha'] = '0' * 40  # type: ignore[index]
    wrong_head = copy_meta(); wrong_head['head']['sha'] = '0' * 40  # type: ignore[index]
    wrong_branch = copy_meta(); wrong_branch['head']['ref'] = FROZEN_V5_BRANCH + '-wrong'  # type: ignore[index]
    wrong_base_ref = copy_meta(); wrong_base_ref['base']['ref'] = 'wrong'  # type: ignore[index]
    wrong_state = copy_meta(); wrong_state['state'] = 'closed'
    wrong_merged = copy_meta(); wrong_merged['merged_at'] = '2026-09-10T00:00:00Z'
    live_main = copy_meta(); live_main['base']['sha'] = SUCCESSOR_MAIN  # type: ignore[index]
    if SUCCESSOR_MAIN == FROZEN_V5_CREATION_BASE:
        raise RuntimeError('V23 current-main leakage fixture is not distinguishable from frozen V5 base')
    return {
        'exactFrozenV5MetadataPasses': True,
        'wrongHistoricalBaseFatal': _expect_meta_failure(wrong_base, 'wrong historical base'),
        'wrongHeadFatal': _expect_meta_failure(wrong_head, 'wrong head'),
        'wrongBranchFatal': _expect_meta_failure(wrong_branch, 'wrong branch'),
        'wrongBaseRefFatal': _expect_meta_failure(wrong_base_ref, 'wrong base ref'),
        'wrongStateFatal': _expect_meta_failure(wrong_state, 'wrong state'),
        'mergedIdentityFatal': _expect_meta_failure(wrong_merged, 'merged identity'),
        'successorCurrentMainLeakageFatal': _expect_meta_failure(live_main, 'current MAIN leakage'),
    }


def _v5_patch_block(indent: bytes) -> bytes:
    # This block executes only inside the already-proven V22-generated builder at the exact
    # generated-effective repair site.  It edits one unique frozen-V5 spent-diagnostic spec
    # literal by adding expectedBaseSha; the accepted comparator and V4 spec remain unchanged.
    lines = [
        '# V23 narrow repair: frozen V5 immutable expected-base separation only.',
        "_v23_v5_expected_base = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'",
        "_v23_v5_head = '0d7ad7030aacc1c34bca93fef6c02fd7dcf776c2'",
        "_v23_v5_branch = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5-20260910'",
        "_v23_v4_head = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'",
        "_v23_successor_main = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'",
        "_v23_v5_tree_before = compile(effective, '<v23-generated-effective-v5-pre>', 'exec', flags=_v23_ast.PyCF_ONLY_AST, dont_inherit=True)",
        'def _v23_const_map(_node):',
        '    _out = {}',
        '    if not isinstance(_node, _v23_ast.Dict): return _out',
        '    for _k, _v in zip(_node.keys, _node.values):',
        '        if isinstance(_k, _v23_ast.Constant) and isinstance(_k.value, str) and isinstance(_v, _v23_ast.Constant): _out[_k.value] = _v.value',
        '    return _out',
        'def _v23_spec_candidates(_tree, _pr, _head, _branch):',
        '    _rows = []',
        '    for _node in _v23_ast.walk(_tree):',
        '        if not isinstance(_node, _v23_ast.Dict): continue',
        '        _m = _v23_const_map(_node)',
        '        _vals = set(_m.values())',
        '        if _pr in _vals and _head in _vals and _branch in _vals: _rows.append((_node, _m))',
        '    return _rows',
        "_v23_v5_specs = _v23_spec_candidates(_v23_v5_tree_before, 1033, _v23_v5_head, _v23_v5_branch)",
        "if len(_v23_v5_specs) != 1: raise RuntimeError(f'V23 frozen V5 spent spec count drift: {len(_v23_v5_specs)}')",
        '_v23_v5_node, _v23_v5_map_before = _v23_v5_specs[0]',
        "if 'expectedBaseSha' in _v23_v5_map_before: raise RuntimeError('V23 frozen V5 expectedBaseSha unexpectedly pre-existing')",
        "_v23_v4_specs = [(_n, _v23_const_map(_n)) for _n in _v23_ast.walk(_v23_v5_tree_before) if isinstance(_n, _v23_ast.Dict) and _v23_v4_head in set(_v23_const_map(_n).values()) and 1032 in set(_v23_const_map(_n).values())]",
        "if len(_v23_v4_specs) != 1: raise RuntimeError(f'V23 frozen V4 spent spec count drift: {len(_v23_v4_specs)}')",
        '_v23_v4_node, _v23_v4_map_before = _v23_v4_specs[0]',
        "if _v23_v4_map_before.get('expectedBaseSha') != _v23_v5_expected_base: raise RuntimeError('V23 accepted frozen V4 expected-base semantics drift')",
        "_v23_helpers = [_n for _n in _v23_ast.walk(_v23_v5_tree_before) if isinstance(_n, (_v23_ast.FunctionDef, _v23_ast.AsyncFunctionDef)) and _n.name == '_validate_spent_bundle']",
        "if len(_v23_helpers) != 1: raise RuntimeError(f'V23 spent bundle helper definition count drift: {len(_v23_helpers)}')",
        '_v23_helper = _v23_helpers[0]',
        'def _v23_is_get(_node, _name, _key, _argc):',
        '    return isinstance(_node, _v23_ast.Call) and isinstance(_node.func, _v23_ast.Attribute) and isinstance(_node.func.value, _v23_ast.Name) and _node.func.value.id == _name and _node.func.attr == \'get\' and len(_node.args) == _argc and not _node.keywords and isinstance(_node.args[0], _v23_ast.Constant) and _node.args[0].value == _key',
        '_v23_base_compares = []',
        'for _n in _v23_ast.walk(_v23_helper):',
        '    if not isinstance(_n, _v23_ast.Compare) or len(_n.ops) != 1 or not isinstance(_n.ops[0], _v23_ast.Eq) or len(_n.comparators) != 1: continue',
        '    _a, _b = _n.left, _n.comparators[0]',
        '    for _left, _right in ((_a, _b), (_b, _a)):',
        "        if not _v23_is_get(_left, 'pbase', 'sha', 1): continue",
        "        if not _v23_is_get(_right, 'spec', 'expectedBaseSha', 2): continue",
        "        if not isinstance(_right.args[1], _v23_ast.Name) or _right.args[1].id != 'MAIN': continue",
        '        _v23_base_compares.append(_n)',
        '        break',
        "if len(_v23_base_compares) != 1: raise RuntimeError(f'V23 immutable-base comparator count drift: {len(_v23_base_compares)}')",
        "_v23_main_assigns = [_n for _n in _v23_v5_tree_before.body if isinstance(_n, _v23_ast.Assign) and len(_n.targets) == 1 and isinstance(_n.targets[0], _v23_ast.Name) and _n.targets[0].id == 'MAIN' and isinstance(_n.value, _v23_ast.Constant) and isinstance(_n.value.value, str)]",
        "if len(_v23_main_assigns) != 1 or _v23_main_assigns[0].value.value != _v23_successor_main: raise RuntimeError('V23 live successor MAIN binding drift')",
        "if _v23_successor_main == _v23_v5_expected_base: raise RuntimeError('V23 frozen V5 expected base aliases live successor MAIN')",
        'def _v23_segment(_src, _node):',
        '    if isinstance(_src, str):',
        '        _seg = _v23_ast.get_source_segment(_src, _node)',
        "        if not isinstance(_seg, str): raise RuntimeError('V23 string source segment unavailable')",
        '        return _seg',
        '    if isinstance(_src, bytes):',
        '        _lines = _src.splitlines(keepends=True)',
        "        if not hasattr(_node, 'end_lineno') or _node.end_lineno is None: raise RuntimeError('V23 byte source segment lacks AST end position')",
        '        _start = sum(len(_line) for _line in _lines[: int(_node.lineno) - 1]) + int(_node.col_offset)',
        '        _end = sum(len(_line) for _line in _lines[: int(_node.end_lineno) - 1]) + int(_node.end_col_offset)',
        '        return _src[_start:_end]',
        "    raise RuntimeError(f'V23 generated effective source type unexpected: {type(_src).__name__}')",
        '_v23_v4_segment_before = _v23_segment(effective, _v23_v4_node)',
        '_v23_v5_segment_before = _v23_segment(effective, _v23_v5_node)',
        'if isinstance(_v23_v5_segment_before, bytes):',
        "    _close = _v23_v5_segment_before.rfind(b'}')",
        "    if _close < 0: raise RuntimeError('V23 V5 spec closing brace missing')",
        '    _prefix = _v23_v5_segment_before[:_close]',
        "    _sep = b'' if _prefix.rstrip().endswith(b',') else b','",
        "    _v23_v5_segment_after = _prefix + _sep + b\" 'expectedBaseSha': 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'\" + _v23_v5_segment_before[_close:]",
        'else:',
        "    _close = _v23_v5_segment_before.rfind('}')",
        "    if _close < 0: raise RuntimeError('V23 V5 spec closing brace missing')",
        '    _prefix = _v23_v5_segment_before[:_close]',
        "    _sep = '' if _prefix.rstrip().endswith(',') else ','",
        "    _v23_v5_segment_after = _prefix + _sep + \" 'expectedBaseSha': 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'\" + _v23_v5_segment_before[_close:]",
        "if effective.count(_v23_v5_segment_before) != 1: raise RuntimeError(f'V23 frozen V5 spec source occurrence drift: {effective.count(_v23_v5_segment_before)}')",
        '_v23_effective_before_v5 = effective',
        'effective = effective.replace(_v23_v5_segment_before, _v23_v5_segment_after, 1)',
        "if effective.replace(_v23_v5_segment_after, _v23_v5_segment_before, 1) != _v23_effective_before_v5: raise RuntimeError('V23 frozen V5 expected-base insertion is not the only source edit')",
        "_v23_v5_tree_after = compile(effective, '<v23-generated-effective-v5-post>', 'exec', flags=_v23_ast.PyCF_ONLY_AST, dont_inherit=True)",
        "_v23_v5_specs_after = _v23_spec_candidates(_v23_v5_tree_after, 1033, _v23_v5_head, _v23_v5_branch)",
        "if len(_v23_v5_specs_after) != 1: raise RuntimeError(f'V23 post-repair frozen V5 spent spec count drift: {len(_v23_v5_specs_after)}')",
        "if _v23_v5_specs_after[0][1].get('expectedBaseSha') != _v23_v5_expected_base: raise RuntimeError('V23 frozen V5 immutable expected-base binding drift')",
        "_v23_v4_specs_after = [(_n, _v23_const_map(_n)) for _n in _v23_ast.walk(_v23_v5_tree_after) if isinstance(_n, _v23_ast.Dict) and _v23_v4_head in set(_v23_const_map(_n).values()) and 1032 in set(_v23_const_map(_n).values())]",
        "if len(_v23_v4_specs_after) != 1 or _v23_v4_specs_after[0][1] != _v23_v4_map_before: raise RuntimeError('V23 frozen V4 expected-base spec changed')",
        "if _v23_segment(effective, _v23_v4_specs_after[0][0]) != _v23_v4_segment_before: raise RuntimeError('V23 frozen V4 expected-base bytes/text changed')",
        "_v23_helpers_after = [_n for _n in _v23_ast.walk(_v23_v5_tree_after) if isinstance(_n, (_v23_ast.FunctionDef, _v23_ast.AsyncFunctionDef)) and _n.name == '_validate_spent_bundle']",
        "if len(_v23_helpers_after) != 1: raise RuntimeError('V23 post-repair spent bundle helper definition drift')",
        "if _v23_segment(effective, _v23_helpers_after[0]) != _v23_segment(_v23_effective_before_v5, _v23_helper): raise RuntimeError('V23 spent bundle helper changed while repairing V5 spec')",
        'def _v23_validate_meta(_m):',
        "    if not isinstance(_m, dict): raise RuntimeError('V23 V5 fixture metadata shape')",
        "    if _m.get('state') != 'open' or _m.get('draft') is not True or _m.get('merged_at') is not None: raise RuntimeError('V23 V5 fixture state/merged')",
        "    _h, _b = _m.get('head'), _m.get('base')",
        "    if not isinstance(_h, dict) or not isinstance(_b, dict): raise RuntimeError('V23 V5 fixture head/base shape')",
        "    if _h.get('sha') != _v23_v5_head: raise RuntimeError('V23 V5 fixture head')",
        "    if _h.get('ref') != _v23_v5_branch: raise RuntimeError('V23 V5 fixture branch')",
        "    if _b.get('ref') != 'main': raise RuntimeError('V23 V5 fixture base ref')",
        "    if _b.get('sha') != _v23_v5_expected_base: raise RuntimeError('V23 V5 fixture historical base')",
        '    return True',
        "_v23_obs = globals().get('_V23_OBSERVED_V5_METADATA')",
        "if not _v23_validate_meta(_v23_obs): raise RuntimeError('V23 observed frozen V5 metadata did not validate')",
        "_v23_fixture = {'state':'open','draft':True,'merged_at':None,'head':{'sha':_v23_v5_head,'ref':_v23_v5_branch},'base':{'sha':_v23_v5_expected_base,'ref':'main'}}",
        "if not _v23_validate_meta(_v23_fixture): raise RuntimeError('V23 canonical V5 fixture failed')",
        'def _v23_expect_fail(_mutator, _label):',
        '    import copy as _v23_copy',
        '    _x = _v23_copy.deepcopy(_v23_fixture)',
        '    _mutator(_x)',
        '    try: _v23_validate_meta(_x)',
        '    except RuntimeError: return True',
        "    raise RuntimeError(f'V23 V5 negative fixture unexpectedly accepted: {_label}')",
        "_v23_f_wrong_base = _v23_expect_fail(lambda _x: _x['base'].__setitem__('sha', '0'*40), 'wrong historical base')",
        "_v23_f_wrong_head = _v23_expect_fail(lambda _x: _x['head'].__setitem__('sha', '0'*40), 'wrong head')",
        "_v23_f_wrong_branch = _v23_expect_fail(lambda _x: _x['head'].__setitem__('ref', _v23_v5_branch + '-wrong'), 'wrong branch')",
        "_v23_f_wrong_base_ref = _v23_expect_fail(lambda _x: _x['base'].__setitem__('ref', 'wrong'), 'wrong base ref')",
        "_v23_f_wrong_state = _v23_expect_fail(lambda _x: _x.__setitem__('state', 'closed'), 'wrong state')",
        "_v23_f_merged = _v23_expect_fail(lambda _x: _x.__setitem__('merged_at', '2026-09-10T00:00:00Z'), 'merged identity')",
        "_v23_f_main_leak = _v23_expect_fail(lambda _x: _x['base'].__setitem__('sha', _v23_successor_main), 'successor MAIN leakage')",
        "globals()['V23_V5_EXPECTED_BASE_AUDIT'] = {'status':'PASS_V23_PREACTUAL_HISTORICAL_V5_BASE_SEPARATION_PROOF','frozenV5Pr':1033,'frozenV5Head':_v23_v5_head,'frozenV5Branch':_v23_v5_branch,'frozenV5BaseRef':'main','frozenV5ExpectedBaseSha':_v23_v5_expected_base,'successorMain':_v23_successor_main,'expectedBaseComparatorUsesSpecFallbackMain':True,'frozenV4SpecByteSemanticEquivalent':True,'observedFrozenV5MetadataPasses':True,'fixtures':{'exactFrozenV5MetadataPasses':True,'wrongHistoricalBaseFatal':_v23_f_wrong_base,'wrongHeadFatal':_v23_f_wrong_head,'wrongBranchFatal':_v23_f_wrong_branch,'wrongBaseRefFatal':_v23_f_wrong_base_ref,'wrongStateFatal':_v23_f_wrong_state,'mergedIdentityFatal':_v23_f_merged,'successorCurrentMainLeakageFatal':_v23_f_main_leak},'authorizationRefCreated':False,'dispatchCreated':False,'scientificOrdinalAllocated':False,'seedUniverseConsumed':False,'scienceInvoked':False,'solverExecuted':False,'protectedResultsOpened':False,'scienceFalse':True}",
    ]
    out = bytearray()
    for line in lines:
        if line.startswith('    '):
            relative = len(line) - len(line.lstrip(' '))
            out.extend(indent + b' ' * relative + line.lstrip(' ').encode('ascii') + b'\n')
        else:
            out.extend(indent + line.encode('ascii') + b'\n')
    return bytes(out)


def _write_v5_proof(path_text: str, audit: dict[str, object]) -> None:
    target = Path(path_text)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(audit)
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    payload['receiptSha256'] = hashlib.sha256(canonical).hexdigest()
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _run() -> None:
    try:
        observed = _load_observed_v5_metadata()
        outer_fixtures = _metadata_fixtures()
        frozen_path_text = os.environ.get('V22_FROZEN_REVIEWER', '')
        if not frozen_path_text:
            raise RuntimeError('V23 frozen V22 reviewer path not supplied')
        frozen_path = Path(frozen_path_text)
        raw = frozen_path.read_bytes()
        if _git_blob_sha1(raw) != FROZEN_V22_BLOB:
            raise RuntimeError('V23 frozen V22 reviewer blob drift')
        text = raw.decode('utf-8')
        if 'V23' in text or 'v23' in text:
            raise RuntimeError('V23 successor token already present in frozen V22 reviewer')
        lifted = text.replace('V22', 'V23').replace('v22', 'v23')
        compile(lifted, '<v23-lifted-v22-reviewer>', 'exec')
        scope: dict[str, object] = {'__file__': str(HERE), '__name__': '_avps_v23_lifted_v22_'}
        exec(compile(lifted, '<v23-lifted-v22-reviewer>', 'exec'), scope, scope)
        original = scope.get('_rebind_block')
        lifted_run = scope.get('_run')
        if not callable(original) or not callable(lifted_run):
            raise RuntimeError('V23 lifted V22 reviewer API drift')

        def combined_rebind(indent: bytes) -> bytes:
            base = original(indent)  # type: ignore[misc]
            if not isinstance(base, bytes):
                raise RuntimeError('V23 lifted rebind block did not return bytes')
            extra = _v5_patch_block(indent)
            marker = b'# V23 narrow repair: frozen V5 immutable expected-base separation only.\n'
            if extra.count(marker) != 1 or base.count(marker) != 0:
                raise RuntimeError('V23 V5 local repair block marker drift')
            return base + extra

        scope['_rebind_block'] = combined_rebind
        scope['_V23_OBSERVED_V5_METADATA'] = observed
        lifted_run()  # type: ignore[misc]
        audit = scope.get('V23_V5_EXPECTED_BASE_AUDIT')
        if not isinstance(audit, dict):
            raise RuntimeError('V23 V5 expected-base audit missing after lifted reviewer execution')
        if audit.get('status') != V5_PROOF_STATUS or audit.get('scienceFalse') is not True:
            raise RuntimeError(f'V23 V5 expected-base audit drift: {audit!r}')
        fixtures = audit.get('fixtures')
        if not isinstance(fixtures, dict) or fixtures != outer_fixtures:
            raise RuntimeError(f'V23 V5 fixture audit mismatch: inner={fixtures!r} outer={outer_fixtures!r}')
        proof_out = _argv_value('--v23-v5-proof-out')
        if proof_out:
            _write_v5_proof(proof_out, audit)
    except BaseException as exc:
        if '--v23-proof-only' in sys.argv or os.environ.get('V23_PREACTUAL_ACTIVE') == '1':
            _write_failure(exc)
        raise


if __name__ == '__main__':
    _run()
