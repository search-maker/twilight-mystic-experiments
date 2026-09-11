from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

V7_HEAD = '832a812b1d62e1bd304f64af2f5309c0c035277f'
V7_SCRIPT_BLOB = 'de2140ac1fe4becf7dfa648469c79544100e52fd'
V7_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v7/review_authorization.py'
V8_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v8-20260910'
V8_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v8/review_authorization.py'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V7_ROOT = REVIEW_ROOT.parent / 'v7-base'

head = subprocess.run(
    ['git', '-C', str(V7_ROOT), 'rev-parse', 'HEAD'],
    text=True,
    capture_output=True,
    check=False,
)
if head.returncode != 0 or head.stdout.strip() != V7_HEAD:
    raise RuntimeError(f'frozen V7 source checkout drift: {head.stdout!r} {head.stderr!r}')

v7_path = V7_ROOT / V7_SCRIPT
raw = v7_path.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
if git_blob != V7_SCRIPT_BLOB:
    raise RuntimeError(f'frozen V7 source blob drift: {git_blob}')


def _is_validator_assignment(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return False
    target = node.targets[0]
    if not isinstance(target, ast.Tuple) or len(target.elts) != 2:
        return False
    if not all(isinstance(elt, ast.Name) for elt in target.elts):
        return False
    if [elt.id for elt in target.elts] != ['spent_diagnostic_proof', 'observations']:
        return False
    call = node.value
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        return False
    if call.func.id != 'validate_spent_nonauth_diagnostic_artifacts' or call.keywords:
        return False
    if len(call.args) != 4 or not all(isinstance(arg, ast.Name) for arg in call.args):
        return False
    return [arg.id for arg in call.args] == ['c', 'a', 'payload', 'observations']


def _is_classification_write(node: ast.stmt) -> bool:
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
        and path_arg.right.value == 'v8-spent-nonauth-diagnostic-classification.json'
    )


def _ordering_sites(source_text: str) -> tuple[tuple[int, int, int, int], ...]:
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
                    if index + 1 >= len(seq) or not _is_classification_write(seq[index + 1]):
                        raise RuntimeError(
                            f'V8 classification evidence write is not immediately after validator at '
                            f'{stmt.lineno}:{stmt.col_offset}'
                        )
                    nxt = seq[index + 1]
                    pairs.append((stmt.lineno, stmt.col_offset, nxt.lineno, nxt.col_offset))
                if _is_classification_write(stmt):
                    writes.append(stmt)

    if len(validators) != 2:
        raise RuntimeError(f'V8 operational validator site count drift: {len(validators)}')
    if len(writes) != 2:
        raise RuntimeError(f'V8 classification write site count drift: {len(writes)}')
    if len(pairs) != 2:
        raise RuntimeError(f'V8 validator/write pair count drift: {len(pairs)}')
    return tuple(pairs)


_POSITIVE = '''
def first(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
    return observations

def second(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
    return observations
'''
if len(_ordering_sites(_POSITIVE)) != 2:
    raise RuntimeError('V8 ordering positive fixture drift')

_NOISE = _POSITIVE + '''
literal = "write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
# write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
'''
if len(_ordering_sites(_NOISE)) != 2:
    raise RuntimeError('V8 ordering string/comment noise fixture drift')

_BAD_EARLY = '''
def first(c, a, payload, observations):
    write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return observations

def second(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
    return observations
'''
try:
    _ordering_sites(_BAD_EARLY)
except RuntimeError:
    pass
else:
    raise RuntimeError('V8 ordering early-write negative fixture failed open')

_BAD_MISSING = '''
def first(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
    return observations

def second(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return observations
'''
try:
    _ordering_sites(_BAD_MISSING)
except RuntimeError:
    pass
else:
    raise RuntimeError('V8 ordering missing-write negative fixture failed open')

_BAD_EXTRA = _POSITIVE + '''
def third(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)
    return observations
'''
try:
    _ordering_sites(_BAD_EXTRA)
except RuntimeError:
    pass
else:
    raise RuntimeError('V8 ordering extra-path negative fixture failed open')


# Execute the exact frozen V7 wrapper, altering only its final effective-source execution.
# The V7 wrapper still reconstructs the exact V6/V5/V4 semantics and runs its AST proof.
v7_wrapper = raw.decode('utf-8')
terminal_exec = "exec(compile(V7_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"
if v7_wrapper.count(terminal_exec) != 1:
    raise RuntimeError('V8 frozen V7 terminal effective exec anchor drift')

terminal_replacement = r'''_V8_PREMATURE_WRITE = "    write(a.ev / 'v7-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)\n"
_V8_VALIDATOR_LINE = "    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)\n"

if V7_EFFECTIVE_SOURCE.count(_V8_PREMATURE_WRITE) != 1:
    raise RuntimeError(
        f'V8 expected exactly one frozen V7 premature classification write, found '
        f'{V7_EFFECTIVE_SOURCE.count(_V8_PREMATURE_WRITE)}'
    )
if V7_EFFECTIVE_SOURCE.count(_V8_VALIDATOR_LINE) != 2:
    raise RuntimeError(
        f'V8 expected exactly two frozen V7 operational validator lines, found '
        f'{V7_EFFECTIVE_SOURCE.count(_V8_VALIDATOR_LINE)}'
    )

# Narrow V8 repair: remove only the premature materialization and place the same evidence write
# immediately after each exact operational validator has returned and bound spent_diagnostic_proof.
V8_EFFECTIVE_SOURCE = V7_EFFECTIVE_SOURCE.replace(_V8_PREMATURE_WRITE, '', 1)
V8_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace(
    _V8_VALIDATOR_LINE,
    _V8_VALIDATOR_LINE + _V8_PREMATURE_WRITE,
)
V8_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace('replacement-v7', 'replacement-v8').replace('REPLACEMENT_V7', 'REPLACEMENT_V8')
V8_EFFECTIVE_SOURCE = V8_EFFECTIVE_SOURCE.replace('v7', 'v8').replace('V7', 'V8')

if 'replacement-v7' in V8_EFFECTIVE_SOURCE or 'REPLACEMENT_V7' in V8_EFFECTIVE_SOURCE:
    raise RuntimeError('V8 mechanical identity lift incomplete')
if "spent_diagnostic_proof = None" in V8_EFFECTIVE_SOURCE:
    raise RuntimeError('V8 dummy initialization is forbidden')
if V8_EFFECTIVE_SOURCE.count(
    "write(a.ev / 'v8-spent-nonauth-diagnostic-classification.json', spent_diagnostic_proof)"
) != 2:
    raise RuntimeError('V8 classification write count drift after narrow ordering repair')

V8_ORDERING_SITES = _ordering_sites(V8_EFFECTIVE_SOURCE)
V8_ORDERING_REPAIR_AUDIT = {
    'frozenV7Head': V7_HEAD,
    'frozenV7ScriptGitBlobSha1': V7_SCRIPT_BLOB,
    'classificationWriteAfterValidator': True,
    'operationalValidatorWritePairs': [list(row) for row in V8_ORDERING_SITES],
    'operationalValidatorWritePairCount': len(V8_ORDERING_SITES),
    'dummyInitializationUsed': False,
    'classificationWriteSuppressed': False,
    'spentArtifactTaxonomyBroadened': False,
    'allV7SemanticControlsAndAstProofCarried': True,
}
exec(compile(V8_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())'''

v8_v7_wrapper = v7_wrapper.replace(terminal_exec, terminal_replacement, 1)
exec(compile(v8_v7_wrapper, str(HERE), 'exec'), globals(), globals())
