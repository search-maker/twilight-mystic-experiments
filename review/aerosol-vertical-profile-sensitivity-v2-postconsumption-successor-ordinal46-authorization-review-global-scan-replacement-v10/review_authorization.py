from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

V9_HEAD = '05a91153a813d6b84de429645da4bf4d86f9e780'
V9_SCRIPT_BLOB = '4cc7e33e08e0add34b0b5229e9795f8820564d4a'
V9_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v9/review_authorization.py'
V10_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v10-20260914'
V10_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v10/review_authorization.py'
FROZEN_V9_MAIN = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
V10_MAIN = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V9_ROOT = REVIEW_ROOT.parent / 'v9-base'

head = subprocess.run(
    ['git', '-C', str(V9_ROOT), 'rev-parse', 'HEAD'],
    text=True,
    capture_output=True,
    check=False,
)
if head.returncode != 0 or head.stdout.strip() != V9_HEAD:
    raise RuntimeError(f'frozen V9 source checkout drift: {head.stdout!r} {head.stderr!r}')

v9_path = V9_ROOT / V9_SCRIPT
raw_v9 = v9_path.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw_v9)).encode() + b'\0' + raw_v9).hexdigest()
if git_blob != V9_SCRIPT_BLOB:
    raise RuntimeError(f'frozen V9 source blob drift: {git_blob}')

# Execute the exact frozen V9 transformation chain with only its demonstrated cardinality defect
# repaired.  V9 still reconstructs V8/V7/V6/V5/V4, runs the frozen V7 exact-two executable-site
# proof first, and applies the ordering transformation only after that proof has succeeded.
v9_source = raw_v9.decode('utf-8')

old_guard = """if V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_PREMATURE_WRITE) != 1:
    raise RuntimeError(
        f'V9 expected exactly one frozen V7 premature classification write, found '
        f'{V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_PREMATURE_WRITE)}'
    )"""
new_guard = """if V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_PREMATURE_WRITE) != 2:
    raise RuntimeError(
        f'V10 expected exactly two frozen V7 premature classification writes, found '
        f'{V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_PREMATURE_WRITE)}'
    )"""
if v9_source.count(old_guard) != 1:
    raise RuntimeError('V10 frozen V9 premature-write guard anchor drift')
v9_patched = v9_source.replace(old_guard, new_guard, 1)

old_remove = "V8_EFFECTIVE_SOURCE = V9_PROVED_V7_EFFECTIVE_SOURCE.replace(_V9_PREMATURE_WRITE, '', 1)"
new_remove = "V8_EFFECTIVE_SOURCE = V9_PROVED_V7_EFFECTIVE_SOURCE.replace(_V9_PREMATURE_WRITE, '', 2)"
if v9_patched.count(old_remove) != 1:
    raise RuntimeError('V10 frozen V9 two-write removal anchor drift')
v9_patched = v9_patched.replace(old_remove, new_remove, 1)

v9_final_exec = "exec(compile(V9_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"
if v9_patched.count(v9_final_exec) != 1:
    raise RuntimeError('V10 frozen V9 final effective exec anchor drift')
v9_patched = v9_patched.replace(
    v9_final_exec,
    'V10_PROVED_V9_EFFECTIVE_SOURCE = V9_EFFECTIVE_SOURCE',
    1,
)
exec(compile(v9_patched, str(HERE), 'exec'), globals(), globals())

if not isinstance(globals().get('V10_PROVED_V9_EFFECTIVE_SOURCE'), str) or not V10_PROVED_V9_EFFECTIVE_SOURCE:
    raise RuntimeError('V10 could not recover repaired/proved frozen V9 effective source')
if len(globals().get('V9_ORDERING_SITES', ())) != 2:
    raise RuntimeError('V10 repaired frozen V9 ordering proof did not produce exactly two pairs')
if len(_v7_operational_validator_sites(V10_PROVED_V9_EFFECTIVE_SOURCE)) != 2:
    raise RuntimeError('V10 repaired frozen V9 operational validator site count drift')
if V10_PROVED_V9_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v9-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V10 repaired frozen V9 classification write count drift')
if 'spent_diagnostic_proof = None' in V10_PROVED_V9_EFFECTIVE_SOURCE:
    raise RuntimeError('V10 inherited forbidden dummy initialization')

# Coordinator 5670429911 explicitly made the creation base conditional on then-live admissible
# main.  ARM PR1038 subsequently advanced main only by its separately authorized three-file install.
# Rebind the already-proved reviewer to that exact live main without changing any review semantics.
old_main_binding = f"MAIN = '{FROZEN_V9_MAIN}'"
new_main_binding = f"MAIN = '{V10_MAIN}'"
if V10_PROVED_V9_EFFECTIVE_SOURCE.count(old_main_binding) != 1:
    raise RuntimeError('V10 frozen effective MAIN binding anchor drift')
_v10_rebased_source = V10_PROVED_V9_EFFECTIVE_SOURCE.replace(old_main_binding, new_main_binding, 1)
if old_main_binding in _v10_rebased_source or _v10_rebased_source.count(new_main_binding) != 1:
    raise RuntimeError('V10 exact current-main rebind incomplete')

# Mechanical identity lift only after the frozen V7/V8/V9 structural/semantic proofs have passed.
V10_EFFECTIVE_SOURCE = _v10_rebased_source.replace('replacement-v9', 'replacement-v10').replace('REPLACEMENT_V9', 'REPLACEMENT_V10')
V10_EFFECTIVE_SOURCE = V10_EFFECTIVE_SOURCE.replace('v9', 'v10').replace('V9', 'V10')

if V10_EFFECTIVE_SOURCE == _v10_rebased_source:
    raise RuntimeError('V10 mechanical identity lift produced no change')
if 'replacement-v9' in V10_EFFECTIVE_SOURCE or 'REPLACEMENT_V9' in V10_EFFECTIVE_SOURCE:
    raise RuntimeError('V10 mechanical identity lift incomplete')
if old_main_binding in V10_EFFECTIVE_SOURCE or V10_EFFECTIVE_SOURCE.count(new_main_binding) != 1:
    raise RuntimeError('V10 current-main binding drift after identity lift')
if 'spent_diagnostic_proof = None' in V10_EFFECTIVE_SOURCE:
    raise RuntimeError('V10 dummy initialization is forbidden after identity lift')
if V10_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v10-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V10 classification write count drift after identity lift')

_v10_final_validator_sites = _v7_operational_validator_sites(V10_EFFECTIVE_SOURCE)
if len(_v10_final_validator_sites) != 2:
    raise RuntimeError(
        f'V10 final operational validator site count drift: {_v10_final_validator_sites!r}'
    )


def _v10_is_classification_write(node: ast.stmt) -> bool:
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
    return (
        isinstance(path_arg.right, ast.Constant)
        and path_arg.right.value == 'v10-spent-nonauth-diagnostic-classification.json'
    )


def _v10_ordering_sites(source_text: str) -> tuple[tuple[int, int, int, int], ...]:
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
                    if index + 1 >= len(seq) or not _v10_is_classification_write(seq[index + 1]):
                        raise RuntimeError(
                            f'V10 classification evidence write is not immediately after validator at '
                            f'{stmt.lineno}:{stmt.col_offset}'
                        )
                    nxt = seq[index + 1]
                    pairs.append((stmt.lineno, stmt.col_offset, nxt.lineno, nxt.col_offset))
                if _v10_is_classification_write(stmt):
                    writes.append(stmt)
    if len(validators) != 2:
        raise RuntimeError(f'V10 operational validator site count drift: {len(validators)}')
    if len(writes) != 2:
        raise RuntimeError(f'V10 classification write site count drift: {len(writes)}')
    if len(pairs) != 2:
        raise RuntimeError(f'V10 validator/write pair count drift: {len(pairs)}')
    return tuple(pairs)


V10_ORDERING_SITES = _v10_ordering_sites(V10_EFFECTIVE_SOURCE)
V10_TRANSFORM_AUDIT = {
    'frozenV9Head': V9_HEAD,
    'frozenV9ScriptGitBlobSha1': V9_SCRIPT_BLOB,
    'frozenV9Main': FROZEN_V9_MAIN,
    'admissibleCreationMain': V10_MAIN,
    'frozenV9LegacyPrematureClassificationWriteCount': 2,
    'legacyPrematureWritesRemovedExactly': 2,
    'classificationWriteAfterEachValidator': True,
    'operationalValidatorWritePairs': [list(row) for row in V10_ORDERING_SITES],
    'operationalValidatorWritePairCount': len(V10_ORDERING_SITES),
    'v8FourSitesTransformationLayerDefectRemainsRemoved': True,
    'v7ExactTwoOperationalSiteGatePreserved': True,
    'dummyInitializationUsed': False,
    'classificationWriteSuppressed': False,
    'spentArtifactTaxonomyBroadened': False,
    'unknownArtifactExemptionAdded': False,
    'siteCountGateRelaxed': False,
    'allV7V8V9SemanticAndFailClosedControlsCarried': True,
}

exec(compile(V10_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())
