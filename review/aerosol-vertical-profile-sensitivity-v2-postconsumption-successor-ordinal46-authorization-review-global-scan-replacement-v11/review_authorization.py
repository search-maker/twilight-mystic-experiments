from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

V10_HEAD = '7af724da176133f87cb32fd36029575525e0423d'
V10_SCRIPT_BLOB = 'c7fdf87adb95328eeb6d776918e35dad7f2aca00'
V10_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v10/review_authorization.py'
V11_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v11-20260914'
V11_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v11/review_authorization.py'
V11_MAIN = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V10_ROOT = REVIEW_ROOT.parent / 'v10-base'


def _argv_value(flag: str) -> str | None:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


def _persist_v11_wrapper_failure(exc: BaseException) -> None:
    ev_arg = _argv_value('--ev')
    if not ev_arg:
        return
    ev = Path(ev_arg)
    ev.mkdir(parents=True, exist_ok=True)
    run_arg = _argv_value('--run') or '0'
    attempt_arg = _argv_value('--attempt') or '0'
    payload = {
        'schemaVersion': 1,
        'status': 'FAIL_RESULT_BLIND_V11_WRAPPER',
        'type': type(exc).__name__,
        'message': str(exc),
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
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    payload['receiptSha256'] = hashlib.sha256(canonical).hexdigest()
    target = ev / 'failure.json'
    tmp = ev / 'failure.json.tmp'
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, target)


def _v11_is_classification_write(node: ast.stmt, filename: str) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    if not isinstance(call.func, ast.Name) or call.func.id != 'write' or call.keywords:
        return False
    if len(call.args) != 2:
        return False
    path_arg, proof_arg = call.args
    if not isinstance(proof_arg, ast.Name) or proof_arg.id != 'spent_diagnostic_proof':
        return False
    if not isinstance(path_arg, ast.BinOp) or not isinstance(path_arg.op, ast.Div):
        return False
    if not isinstance(path_arg.left, ast.Attribute) or not isinstance(path_arg.left.value, ast.Name):
        return False
    if path_arg.left.value.id != 'a' or path_arg.left.attr != 'ev':
        return False
    return isinstance(path_arg.right, ast.Constant) and path_arg.right.value == filename


def _v11_executable_ordering_sites(source_text: str, filename: str) -> tuple[tuple[int, int, int, int], ...]:
    tree = ast.parse(source_text)
    validators: list[ast.stmt] = []
    writes: list[ast.stmt] = []
    pairs: list[tuple[int, int, int, int]] = []
    for node in ast.walk(tree):
        for attr in ('body', 'orelse', 'finalbody'):
            seq = getattr(node, attr, None)
            if not isinstance(seq, list):
                continue
            for index, stmt in enumerate(seq):
                if _is_validator_assignment(stmt):
                    validators.append(stmt)
                    if index + 1 >= len(seq) or not _v11_is_classification_write(seq[index + 1], filename):
                        raise RuntimeError(
                            f'V11 classification evidence write is not immediately after validator at '
                            f'{stmt.lineno}:{stmt.col_offset}'
                        )
                    nxt = seq[index + 1]
                    pairs.append((stmt.lineno, stmt.col_offset, nxt.lineno, nxt.col_offset))
                if _v11_is_classification_write(stmt, filename):
                    writes.append(stmt)
    if len(validators) != 2:
        raise RuntimeError(f'V11 operational validator site count drift: {len(validators)}')
    if len(writes) != 2:
        raise RuntimeError(f'V11 classification write site count drift: {len(writes)}')
    if len(pairs) != 2:
        raise RuntimeError(f'V11 validator/write pair count drift: {len(pairs)}')
    return tuple(pairs)


def _build_v11_effective_source() -> str:
    head = subprocess.run(
        ['git', '-C', str(V10_ROOT), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0 or head.stdout.strip() != V10_HEAD:
        raise RuntimeError(f'frozen V10 source checkout drift: {head.stdout!r} {head.stderr!r}')

    v10_path = V10_ROOT / V10_SCRIPT
    raw_v10 = v10_path.read_bytes()
    git_blob = hashlib.sha1(b'blob ' + str(len(raw_v10)).encode() + b'\0' + raw_v10).hexdigest()
    if git_blob != V10_SCRIPT_BLOB:
        raise RuntimeError(f'frozen V10 source blob drift: {git_blob}')

    v10_source = raw_v10.decode('utf-8')

    old_pre_count = '''if V10_PROVED_V9_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v9-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V10 repaired frozen V9 classification write count drift')'''
    new_pre_count = '''_v11_pre_v10_ordering_sites = _v11_executable_ordering_sites(
    V10_PROVED_V9_EFFECTIVE_SOURCE,
    'v9-spent-nonauth-diagnostic-classification.json',
)
if len(_v11_pre_v10_ordering_sites) != 2:
    raise RuntimeError('V11 repaired frozen V10 pre-lift ordering proof did not produce two pairs')'''
    if v10_source.count(old_pre_count) != 1:
        raise RuntimeError('V11 frozen V10 pre-lift count assertion anchor drift')
    v10_patched = v10_source.replace(old_pre_count, new_pre_count, 1)

    old_post_count = '''if V10_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v10-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V10 classification write count drift after identity lift')'''
    new_post_count = '''_v11_post_v10_ordering_sites = _v11_executable_ordering_sites(
    V10_EFFECTIVE_SOURCE,
    'v10-spent-nonauth-diagnostic-classification.json',
)
if len(_v11_post_v10_ordering_sites) != 2:
    raise RuntimeError('V11 repaired frozen V10 post-lift ordering proof did not produce two pairs')'''
    if v10_patched.count(old_post_count) != 1:
        raise RuntimeError('V11 frozen V10 post-lift count assertion anchor drift')
    v10_patched = v10_patched.replace(old_post_count, new_post_count, 1)

    v10_final_exec = "exec(compile(V10_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"
    if v10_patched.count(v10_final_exec) != 1:
        raise RuntimeError('V11 frozen V10 final effective exec anchor drift')
    v10_patched = v10_patched.replace(
        v10_final_exec,
        'V11_PROVED_V10_EFFECTIVE_SOURCE = V10_EFFECTIVE_SOURCE',
        1,
    )

    exec(compile(v10_patched, str(HERE), 'exec'), globals(), globals())

    proved = globals().get('V11_PROVED_V10_EFFECTIVE_SOURCE')
    if not isinstance(proved, str) or not proved:
        raise RuntimeError('V11 could not recover repaired/proved frozen V10 effective source')
    if len(globals().get('V10_ORDERING_SITES', ())) != 2:
        raise RuntimeError('V11 repaired frozen V10 ordering proof did not produce exactly two pairs')
    if len(_v7_operational_validator_sites(proved)) != 2:
        raise RuntimeError('V11 repaired frozen V10 operational validator site count drift')
    prelift_pairs = _v11_executable_ordering_sites(
        proved,
        'v10-spent-nonauth-diagnostic-classification.json',
    )
    if len(prelift_pairs) != 2:
        raise RuntimeError('V11 repaired frozen V10 effective ordering pair count drift')
    if 'spent_diagnostic_proof = None' in proved:
        raise RuntimeError('V11 inherited forbidden dummy initialization')

    effective = proved.replace('replacement-v10', 'replacement-v11').replace('REPLACEMENT_V10', 'REPLACEMENT_V11')
    effective = effective.replace('v10', 'v11').replace('V10', 'V11')

    if effective == proved:
        raise RuntimeError('V11 mechanical identity lift produced no change')
    if 'replacement-v10' in effective or 'REPLACEMENT_V10' in effective:
        raise RuntimeError('V11 mechanical identity lift incomplete')
    if f"MAIN = '{V11_MAIN}'" not in effective:
        raise RuntimeError('V11 admissible current-main binding missing after identity lift')
    if 'spent_diagnostic_proof = None' in effective:
        raise RuntimeError('V11 dummy initialization is forbidden after identity lift')
    if len(_v7_operational_validator_sites(effective)) != 2:
        raise RuntimeError('V11 final operational validator site count drift')

    final_pairs = _v11_executable_ordering_sites(
        effective,
        'v11-spent-nonauth-diagnostic-classification.json',
    )
    if len(final_pairs) != 2:
        raise RuntimeError('V11 final validator/write pair count drift')

    globals()['V11_TRANSFORM_AUDIT'] = {
        'frozenV10Head': V10_HEAD,
        'frozenV10ScriptGitBlobSha1': V10_SCRIPT_BLOB,
        'admissibleCreationMain': V11_MAIN,
        'preLiftOperationalValidatorWritePairs': [list(row) for row in prelift_pairs],
        'postLiftOperationalValidatorWritePairs': [list(row) for row in final_pairs],
        'operationalValidatorWritePairCount': len(final_pairs),
        'preEffectiveTextualCountAssertionReplacedByExecutableAstProof': True,
        'wrapperFailureEvidenceDirectoryCreatedBeforeFailureWrite': True,
        'v8FourSitesTransformationLayerDefectRemainsRemoved': True,
        'v7ExactTwoOperationalSiteGatePreserved': True,
        'dummyInitializationUsed': False,
        'classificationWriteSuppressed': False,
        'spentArtifactTaxonomyBroadened': False,
        'unknownArtifactExemptionAdded': False,
        'siteCountGateRelaxed': False,
        'allV7V8V9V10SemanticAndFailClosedControlsCarried': True,
    }
    return effective


try:
    V11_EFFECTIVE_SOURCE = _build_v11_effective_source()
except BaseException as exc:
    _persist_v11_wrapper_failure(exc)
    raise

exec(compile(V11_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())
