from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

V6_HEAD = 'efdf9cbab4e0dbeb718a800a823b59e7735ba755'
V6_SCRIPT_BLOB = 'b53cdc4787b6714b6f14f6de90fca56c897ba751'
V6_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v6/review_authorization.py'
V7_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v7-20260910'
V7_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v7/review_authorization.py'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V6_ROOT = REVIEW_ROOT.parent / 'v6-base'

head = subprocess.run(
    ['git', '-C', str(V6_ROOT), 'rev-parse', 'HEAD'],
    text=True,
    capture_output=True,
    check=False,
)
if head.returncode != 0 or head.stdout.strip() != V6_HEAD:
    raise RuntimeError(f'frozen V6 source checkout drift: {head.stdout!r} {head.stderr!r}')

v6_path = V6_ROOT / V6_SCRIPT
raw = v6_path.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
if git_blob != V6_SCRIPT_BLOB:
    raise RuntimeError(f'frozen V6 source blob drift: {git_blob}')


def _v7_operational_validator_sites(source_text: str) -> tuple[tuple[int, int], ...]:
    """Return only the two executable repository-global validator assignment sites.

    The proof deliberately ignores helper definitions, comments/strings and fixture calls that do
    not have the exact operational assignment/call shape.  A third executable site with the exact
    shape is still counted and therefore fails closed.
    """
    tree = ast.parse(source_text)
    sites: list[tuple[int, int]] = []
    expected_args = ['c', 'a', 'payload', 'observations']
    expected_targets = ['spent_diagnostic_proof', 'observations']
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Tuple) or len(target.elts) != 2:
            continue
        if not all(isinstance(elt, ast.Name) for elt in target.elts):
            continue
        if [elt.id for elt in target.elts] != expected_targets:
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            continue
        if call.func.id != 'validate_spent_nonauth_diagnostic_artifacts' or call.keywords:
            continue
        if len(call.args) != 4 or not all(isinstance(arg, ast.Name) for arg in call.args):
            continue
        if [arg.id for arg in call.args] != expected_args:
            continue
        sites.append((node.lineno, node.col_offset))
    return tuple(sites)


# Exercise the structural proof itself before touching the frozen builder.  Helper definitions,
# fixture calls, strings and comments must not inflate the operational count; true extra/missing
# operational sites must remain visible and fail closed.
_POSITIVE_TWO = '''
def first(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return observations

def second(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return observations
'''
if len(_v7_operational_validator_sites(_POSITIVE_TWO)) != 2:
    raise RuntimeError('V7 operational validator AST positive fixture drift')

_NOISE_DOES_NOT_COUNT = _POSITIVE_TWO + '''
def validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations):
    return None, observations

def fixture(c, a, payload, observations):
    fixture_proof, fixture_observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return fixture_observations

literal = "spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)"
# spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
'''
if len(_v7_operational_validator_sites(_NOISE_DOES_NOT_COUNT)) != 2:
    raise RuntimeError('V7 operational validator AST noise fixture drift')

_ONE_SITE = '''
def only(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return observations
'''
if len(_v7_operational_validator_sites(_ONE_SITE)) != 1:
    raise RuntimeError('V7 operational validator AST missing-site fixture drift')

_THREE_SITES = _POSITIVE_TWO + '''
def third(c, a, payload, observations):
    spent_diagnostic_proof, observations = validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)
    return observations
'''
if len(_v7_operational_validator_sites(_THREE_SITES)) != 3:
    raise RuntimeError('V7 operational validator AST extra-site fixture drift')

v6_wrapper = raw.decode('utf-8')
bad_guard = """if patched.count('validate_spent_nonauth_diagnostic_artifacts(c, a, payload, observations)') != 2:
    raise RuntimeError('V6 spent diagnostic validator call count drift')"""
if v6_wrapper.count(bad_guard) != 1:
    raise RuntimeError('V7 frozen V6 defective guard anchor drift')

replacement_guard = """_v7_validator_sites = _v7_operational_validator_sites(patched)
if len(_v7_validator_sites) != 2:
    raise RuntimeError(f'V7 operational spent diagnostic validator site count drift: {_v7_validator_sites!r}')"""
v7_builder = v6_wrapper.replace(bad_guard, replacement_guard, 1)

terminal_exec = "exec(compile(patched, str(HERE), 'exec'), globals(), globals())"
terminal_index = v7_builder.rfind(terminal_exec)
if terminal_index < 0:
    raise RuntimeError('V7 frozen V6 terminal exec anchor missing')
if v7_builder.find(terminal_exec, terminal_index + 1) != -1:
    raise RuntimeError('V7 frozen V6 terminal exec anchor ambiguity')

terminal_replacement = """V7_EFFECTIVE_SOURCE = patched.replace('replacement-v6', 'replacement-v7').replace('REPLACEMENT_V6', 'REPLACEMENT_V7')
V7_EFFECTIVE_SOURCE = V7_EFFECTIVE_SOURCE.replace('v6', 'v7').replace('V6', 'V7')
if V7_EFFECTIVE_SOURCE == patched:
    raise RuntimeError('V7 mechanical identity lift produced no change')
if 'replacement-v6' in V7_EFFECTIVE_SOURCE or 'REPLACEMENT_V6' in V7_EFFECTIVE_SOURCE:
    raise RuntimeError('V7 mechanical identity lift incomplete')
V7_TRANSFORM_AUDIT = {
    'frozenV6Head': V6_HEAD,
    'frozenV6ScriptGitBlobSha1': V6_SCRIPT_BLOB,
    'operationalValidatorSites': list(_v7_validator_sites),
    'operationalValidatorSiteCount': len(_v7_validator_sites),
    'proofMode': 'AST_EXACT_EXECUTABLE_ASSIGNMENT_CALL_SITE',
    'helperFixtureStringCommentNoiseIgnored': True,
    'missingOrExtraOperationalSiteFatal': True,
    'allV6SemanticControlsAndArtifactTaxonomyCarried': True,
}
exec(compile(V7_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"""
v7_builder = (
    v7_builder[:terminal_index]
    + terminal_replacement
    + v7_builder[terminal_index + len(terminal_exec):]
)

# Execute the frozen V6 builder with only the authorized structural-proof repair.  That builder
# still reconstructs exact V5/V4 semantics and exact V4/V5 spent-diagnostic artifact taxonomy;
# its final effective reviewer is mechanically identity-lifted to V7 immediately before execution.
exec(compile(v7_builder, str(HERE), 'exec'), globals(), globals())
