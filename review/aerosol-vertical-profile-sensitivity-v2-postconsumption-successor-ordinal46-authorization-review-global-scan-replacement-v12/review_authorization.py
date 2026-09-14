from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

V11_HEAD = 'dc1e8f736f2f467dfef3b020ac879b2e4c692732'
V11_SCRIPT_BLOB = 'e1d28737337e6213ebf634dabce5ae76b185d089'
V11_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v11/review_authorization.py'
V12_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v12-20260914'
V12_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v12/review_authorization.py'
V12_MAIN = '6cd7c075766fe0c86bc7561ec205a3f9120fd1fb'
V12_STALE_LIFTED_RBR = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v12-20260910'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V11_ROOT = REVIEW_ROOT.parent / 'v11-base'


def _argv_value(flag: str) -> str | None:
    try:
        index = sys.argv.index(flag)
    except ValueError:
        return None
    if index + 1 >= len(sys.argv):
        return None
    return sys.argv[index + 1]


def _persist_v12_wrapper_failure(exc: BaseException) -> None:
    ev_arg = _argv_value('--ev')
    if not ev_arg:
        return
    ev = Path(ev_arg)
    ev.mkdir(parents=True, exist_ok=True)
    run_arg = _argv_value('--run') or '0'
    attempt_arg = _argv_value('--attempt') or '0'
    payload = {
        'schemaVersion': 1,
        'status': 'FAIL_RESULT_BLIND_V12_WRAPPER',
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


def _v12_rbr_assignments(source_text: str) -> tuple[tuple[ast.Assign, str], ...]:
    tree = ast.parse(source_text)
    found: list[tuple[ast.Assign, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != 'RBR':
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            raise RuntimeError('V12 final RBR assignment is not a literal string')
        found.append((node, node.value.value))
    return tuple(found)


def _v12_rebind_final_rbr(source_text: str) -> tuple[str, str]:
    found = _v12_rbr_assignments(source_text)
    if len(found) != 1:
        raise RuntimeError(f'V12 final effective-source RBR assignment count drift: {len(found)}')
    node, old_value = found[0]
    if old_value != V12_STALE_LIFTED_RBR:
        raise RuntimeError(f'V12 unexpected pre-rebind RBR identity: {old_value!r}')
    if node.lineno != node.end_lineno or node.col_offset != 0:
        raise RuntimeError('V12 RBR assignment shape drift; refusing non-line-local rewrite')
    lines = source_text.splitlines(keepends=True)
    index = node.lineno - 1
    if index < 0 or index >= len(lines):
        raise RuntimeError('V12 RBR assignment line index drift')
    ending = '\n' if lines[index].endswith('\n') else ''
    lines[index] = f"RBR = {V12_BRANCH!r}{ending}"
    rebound = ''.join(lines)
    rebound_found = _v12_rbr_assignments(rebound)
    if len(rebound_found) != 1 or rebound_found[0][1] != V12_BRANCH:
        raise RuntimeError('V12 final RBR structural rebind verification failed')
    return rebound, old_value


def _build_v12_effective_source() -> str:
    head = subprocess.run(
        ['git', '-C', str(V11_ROOT), 'rev-parse', 'HEAD'],
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0 or head.stdout.strip() != V11_HEAD:
        raise RuntimeError(f'frozen V11 source checkout drift: {head.stdout!r} {head.stderr!r}')

    v11_path = V11_ROOT / V11_SCRIPT
    raw_v11 = v11_path.read_bytes()
    git_blob = hashlib.sha1(b'blob ' + str(len(raw_v11)).encode() + b'\0' + raw_v11).hexdigest()
    if git_blob != V11_SCRIPT_BLOB:
        raise RuntimeError(f'frozen V11 source blob drift: {git_blob}')

    v11_source = raw_v11.decode('utf-8')
    v11_final_exec = "exec(compile(V11_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())"
    if v11_source.count(v11_final_exec) != 1:
        raise RuntimeError('V12 frozen V11 final effective exec anchor drift')
    v11_patched = v11_source.replace(
        v11_final_exec,
        'V12_PROVED_V11_EFFECTIVE_SOURCE = V11_EFFECTIVE_SOURCE',
        1,
    )

    exec(compile(v11_patched, str(HERE), 'exec'), globals(), globals())

    proved = globals().get('V12_PROVED_V11_EFFECTIVE_SOURCE')
    if not isinstance(proved, str) or not proved:
        raise RuntimeError('V12 could not recover repaired/proved frozen V11 effective source')
    if len(_v7_operational_validator_sites(proved)) != 2:
        raise RuntimeError('V12 frozen V11 operational validator site count drift')
    prelift_pairs = _v11_executable_ordering_sites(
        proved,
        'v11-spent-nonauth-diagnostic-classification.json',
    )
    if len(prelift_pairs) != 2:
        raise RuntimeError('V12 frozen V11 validator/write pair count drift')
    if 'spent_diagnostic_proof = None' in proved:
        raise RuntimeError('V12 inherited forbidden dummy initialization')

    effective = proved.replace('replacement-v11', 'replacement-v12').replace('REPLACEMENT_V11', 'REPLACEMENT_V12')
    effective = effective.replace('v11', 'v12').replace('V11', 'V12')

    if effective == proved:
        raise RuntimeError('V12 mechanical identity lift produced no change')
    if 'replacement-v11' in effective or 'REPLACEMENT_V11' in effective:
        raise RuntimeError('V12 mechanical identity lift incomplete')
    if f"MAIN = '{V12_MAIN}'" not in effective:
        raise RuntimeError('V12 admissible current-main binding missing after identity lift')
    if 'spent_diagnostic_proof = None' in effective:
        raise RuntimeError('V12 dummy initialization is forbidden after identity lift')
    if len(_v7_operational_validator_sites(effective)) != 2:
        raise RuntimeError('V12 post-lift operational validator site count drift before carrier rebind')

    postlift_pairs_before_rebind = _v11_executable_ordering_sites(
        effective,
        'v12-spent-nonauth-diagnostic-classification.json',
    )
    if len(postlift_pairs_before_rebind) != 2:
        raise RuntimeError('V12 post-lift validator/write pair count drift before carrier rebind')

    effective, stale_rbr = _v12_rebind_final_rbr(effective)

    if len(_v7_operational_validator_sites(effective)) != 2:
        raise RuntimeError('V12 final operational validator site count drift')
    final_pairs = _v11_executable_ordering_sites(
        effective,
        'v12-spent-nonauth-diagnostic-classification.json',
    )
    if len(final_pairs) != 2:
        raise RuntimeError('V12 final validator/write pair count drift')
    final_rbr = _v12_rbr_assignments(effective)
    if len(final_rbr) != 1 or final_rbr[0][1] != V12_BRANCH:
        raise RuntimeError('V12 final carrier identity binding drift')

    globals()['V12_TRANSFORM_AUDIT'] = {
        'frozenV11Head': V11_HEAD,
        'frozenV11ScriptGitBlobSha1': V11_SCRIPT_BLOB,
        'admissibleCreationMain': V12_MAIN,
        'staleLiftedCarrierBranch': stale_rbr,
        'finalCarrierBranch': V12_BRANCH,
        'preLiftOperationalValidatorWritePairs': [list(row) for row in prelift_pairs],
        'postLiftOperationalValidatorWritePairsBeforeCarrierRebind': [list(row) for row in postlift_pairs_before_rebind],
        'finalOperationalValidatorWritePairs': [list(row) for row in final_pairs],
        'operationalValidatorWritePairCount': len(final_pairs),
        'finalRbrAssignmentCount': len(final_rbr),
        'finalRbrStructurallyReboundToActualCarrier': True,
        'wrapperFailureEvidenceDirectoryCreatedBeforeFailureWrite': True,
        'v8FourSitesTransformationLayerDefectRemainsRemoved': True,
        'v7ExactTwoOperationalSiteGatePreserved': True,
        'dummyInitializationUsed': False,
        'classificationWriteSuppressed': False,
        'spentArtifactTaxonomyBroadened': False,
        'unknownArtifactExemptionAdded': False,
        'siteCountGateRelaxed': False,
        'carrierGateRelaxed': False,
        'allV7V8V9V10V11SemanticAndFailClosedControlsCarried': True,
    }
    return effective


try:
    V12_EFFECTIVE_SOURCE = _build_v12_effective_source()
except BaseException as exc:
    _persist_v12_wrapper_failure(exc)
    raise

exec(compile(V12_EFFECTIVE_SOURCE, str(HERE), 'exec'), globals(), globals())
