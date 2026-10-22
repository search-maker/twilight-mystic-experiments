from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

V8_HEAD = '03c6837bc31f5b8545987b11aed8da260b32ba11'
V8_SCRIPT_BLOB = '44b2deb795c3baa2890d99fffdfc58ee01a341a3'
V8_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v8/review_authorization.py'
V9_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v9-20260914'
V9_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v9/review_authorization.py'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V8_ROOT = REVIEW_ROOT.parent / 'v8-base'

head = subprocess.run(
    ['git', '-C', str(V8_ROOT), 'rev-parse', 'HEAD'],
    text=True,
    capture_output=True,
    check=False,
)
if head.returncode != 0 or head.stdout.strip() != V8_HEAD:
    raise RuntimeError(f'frozen V8 source checkout drift: {head.stdout!r} {head.stderr!r}')

v8_path = V8_ROOT / V8_SCRIPT
raw_v8 = v8_path.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw_v8)).encode() + b'\0' + raw_v8).hexdigest()
if git_blob != V8_SCRIPT_BLOB:
    raise RuntimeError(f'frozen V8 source blob drift: {git_blob}')

# Preserve and execute the exact frozen V8 prelude: exact V7 checkout/blob binding plus the
# V8 ordering-proof helpers and positive/negative fixtures.  The defective V8 transformation
# layer itself is intentionally not executed; V9 applies the same ordering repair only after the
# frozen V7 structural proof has already completed on the V7 effective source.
v8_source = raw_v8.decode('utf-8')
v8_transform_marker = '# Execute the exact frozen V7 wrapper, altering only its final effective-source execution.\n'
if v8_source.count(v8_transform_marker) != 1:
    raise RuntimeError('V9 frozen V8 transform marker drift')
v8_prelude, _v8_defective_tail = v8_source.split(v8_transform_marker, 1)
exec(compile(v8_prelude, str(HERE), 'exec'), globals(), globals())

# The exact V8 prelude leaves `raw` bound to the verified frozen V7 bytes.  Recover the V7
# effective source only after its own exact-two executable validator-site structural proof has
# run successfully.  Crucially, no V9/V8 successor transformation text is inserted into the V7
# builder before that proof, preventing successor scaffolding from appearing as operational sites.
v7_wrapper = raw.decode('utf-8')
v7_outer_exec = "exec(compile(v7_builder, str(HERE), 'exec'), globals(), globals())"
if v7_wrapper.count(v7_outer_exec) != 1:
    raise RuntimeError('V9 frozen V7 outer builder exec anchor drift')

v7_extract_replacement = r'''_V9_V7_INNER_EXEC = "exec(compile(V7_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"
if v7_builder.count(_V9_V7_INNER_EXEC) != 1:
    raise RuntimeError(
        f'V9 frozen V7 proved-effective exec anchor drift: {v7_builder.count(_V9_V7_INNER_EXEC)}'
    )
_v9_v7_proof_builder = v7_builder.replace(
    _V9_V7_INNER_EXEC,
    'V9_PROVED_V7_EFFECTIVE_SOURCE = V7_EFFECTIVE_SOURCE',
    1,
)
exec(compile(_v9_v7_proof_builder, str(HERE), 'exec'), globals(), globals())'''

v7_extractor = v7_wrapper.replace(v7_outer_exec, v7_extract_replacement, 1)
exec(compile(v7_extractor, str(HERE), 'exec'), globals(), globals())

if not isinstance(globals().get('V9_PROVED_V7_EFFECTIVE_SOURCE'), str) or not V9_PROVED_V7_EFFECTIVE_SOURCE:
    raise RuntimeError('V9 could not recover structurally-proved frozen V7 effective source')

# Frozen V7 proof must still expose exactly the two operational repository-global validator sites.
_v9_frozen_v7_sites = _v7_operational_validator_sites(V9_PROVED_V7_EFFECTIVE_SOURCE)
if len(_v9_frozen_v7_sites) != 2:
    raise RuntimeError(
        f'V9 frozen V7 proved effective source validator site drift: {_v9_frozen_v7_sites!r}'
    )

# Apply the exact V8 ordering repair only now, after V7's structural proof has completed.
_V9_PREMATURE_WRITE = "    write(a.ev / 'v7-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)\n"
_V9_VALIDATOR_LINE = "    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)\n"

if V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_PREMATURE_WRITE) != 1:
    raise RuntimeError(
        f'V9 expected exactly one frozen V7 premature classification write, found '
        f'{V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_PREMATURE_WRITE)}'
    )
if V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_VALIDATOR_LINE) != 2:
    raise RuntimeError(
        f'V9 expected exactly two frozen V7 operational validator lines, found '
        f'{V9_PROVED_V7_EFFECTIVE_SOURCE.count(_V9_VALIDATOR_LINE)}'
    )

V8_EFFECTIVE_SOURCE = V9_PROVED_V7_EFFECTIVE_SOURCE.replace(_V9_PREMATURE_WRITE, '', 1)
V8_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace(
    _V9_VALIDATOR_LINE,
    _V9_VALIDATOR_LINE + _V9_PREMATURE_WRITE,
)
V8_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace('replacement-v7', 'replacement-v8').replace('REPLACEMENT_V7', 'REPLACEMENT_V8')
V8_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace('v7', 'v8').replace('V7', 'V8')

if 'replacement-v7' in V8_EFFECTIVE_SOURCE or 'REPLACEMENT_V7' in V8_EFFECTIVE_SOURCE:
    raise RuntimeError('V9 preserved V8 mechanical identity lift incomplete')
if 'spent_diagnostic_proof = None' in V8_EFFECTIVE_SOURCE:
    raise RuntimeError('V9 dummy initialization is forbidden')
if V8_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V9 preserved V8 classification write count drift')

# Re-run the exact frozen V8 ordering gate on the post-V7-proof effective source.  This is the
# same AST/executable-path proof and retains all of V8's fail-closed fixtures and semantics.
V8_ORDERING_SITES = _ordering_sites(V8_EFFECTIVE_SOURCE)
if len(V8_ORDERING_SITES) != 2:
    raise RuntimeError('V9 preserved V8 ordering proof did not produce two validator/write pairs')

# Mechanical identity lift only after every frozen V7/V8 structural gate above has passed.
V9_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace('replacement-v8', 'replacement-v9').replace('REPLACEMENT_V8', 'REPLACEMENT_V9')
V9_EFFECTIVE_SOURCE = V9_EFFECTIVE_SOURCE.replace('v8', 'v9').replace('V8', 'V9')

if V9_EFFECTIVE_SOURCE == V8_EFFECTIVE_SOURCE:
    raise RuntimeError('V9 mechanical identity lift produced no change')
if 'replacement-v8' in V9_EFFECTIVE_SOURCE or 'REPLACEMENT_V8' in V9_EFFECTIVE_SOURCE:
    raise RuntimeError('V9 mechanical identity lift incomplete')
if 'spent_diagnostic_proof = None' in V9_EFFECTIVE_SOURCE:
    raise RuntimeError('V9 dummy initialization is forbidden after identity lift')
if V9_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v9-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V9 classification write count drift after identity lift')

_v9_final_validator_sites = _v7_operational_validator_sites(V9_EFFECTIVE_SOURCE)
if len(_v9_final_validator_sites) != 2:
    raise RuntimeError(
        f'V9 final operational validator site count drift: {_v9_final_validator_sites!r}'
    )


def _v9_is_classification_write(node: ast.stmt) -> bool:
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
        and path_arg.right.value == 'v9-spent-nonauth-diagnostic-classification.json'
    )


def _v9_ordering_sites(source_text: str) -> tuple[tuple[int, int, int, int], ...]:
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
                    if index + 1 >= len(seq) or not _v9_is_classification_write(seq[index + 1]):
                        raise RuntimeError(
                            f'V9 classification evidence write is not immediately after validator at '
                            f'{stmt.lineno}:{stmt.col_offset}'
                        )
                    nxt = seq[index + 1]
                    pairs.append((stmt.lineno, stmt.col_offset, nxt.lineno, nxt.col_offset))
                if _v9_is_classification_write(stmt):
                    writes.append(stmt)
    if len(validators) != 2:
        raise RuntimeError(f'V9 operational validator site count drift: {len(validators)}')
    if len(writes) != 2:
        raise RuntimeError(f'V9 classification write site count drift: {len(writes)}')
    if len(pairs) != 2:
        raise RuntimeError(f'V9 validator/write pair count drift: {len(pairs)}')
    return tuple(pairs)


V9_ORDERING_SITES = _v9_ordering_sites(V9_EFFECTIVE_SOURCE)
V9_TRANSFORM_AUDIT = {
    'frozenV8Head': V8_HEAD,
    'frozenV8ScriptGitBlobSha1': V8_SCRIPT_BLOB,
    'frozenV7OperationalValidatorSites': [list(row) for row in _v9_frozen_v7_sites],
    'frozenV7OperationalValidatorSiteCount': len(_v9_frozen_v7_sites),
    'v8OrderingRepairAppliedAfterFrozenV7StructuralProof': True,
    'v8OperationalValidatorWritePairs': [list(row) for row in V8_ORDERING_SITES],
    'v9OperationalValidatorWritePairs': [list(row) for row in V9_ORDERING_SITES],
    'v9OperationalValidatorWritePairCount': len(V9_ORDERING_SITES),
    'dummyInitializationUsed': False,
    'classificationWriteSuppressed': False,
    'spentArtifactTaxonomyBroadened': False,
    'unknownArtifactExemptionAdded': False,
    'siteCountGateRelaxed': False,
    'allV7V8SemanticAndFailClosedControlsCarried': True,
}

exec(compile(V9_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())
