from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path

FROZEN_V23_HEAD = '3f81d9c890a38e64be40e2510cbc7bbf467b6c98'
FROZEN_V23_BLOB = '52dd4af0f78e7d8418669d98562a77584bc7ab31'
FROZEN_V22_HEAD = '4b69615cd83a7bcec7e9fa7be17fd48b982367d8'
FROZEN_V22_BLOB = '98fe1ca468a44ad385005111f38dc48c89a08b9e'
ENTRY_PROOF_STATUS = 'PASS_V24_PREACTUAL_CONTROLLED_ENTRYPOINT_NAMESPACE_PROOF'
ZERO_PROOF_STATUS = 'PASS_V24_PREACTUAL_ZERO_RUNTIME_PROOF_TARGET_BINDING'
V5_PROOF_STATUS = 'PASS_V24_PREACTUAL_HISTORICAL_V5_BASE_SEPARATION_PROOF'
FAIL_STATUS = 'FAIL_V24_PREACTUAL_CONTROLLED_ENTRYPOINT_NAMESPACE_PROOF'
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
    fail_dir_text = os.environ.get('V24_PREACTUAL_FAILURE_DIR', '')
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


def _load_lifted_scope(
    env_name: str,
    expected_blob: str,
    old_upper: str,
    new_upper: str,
    old_lower: str,
    new_lower: str,
    filename: str,
    namespace: str,
) -> tuple[dict[str, object], bytes]:
    path_text = os.environ.get(env_name, '')
    if not path_text:
        raise RuntimeError(f'V24 frozen source path missing: {env_name}')
    path = Path(path_text)
    raw = path.read_bytes()
    if _git_blob_sha1(raw) != expected_blob:
        raise RuntimeError(f'V24 frozen source blob drift: {env_name}')
    text = raw.decode('utf-8')
    if new_upper in text or new_lower in text:
        raise RuntimeError(f'V24 successor token already present in frozen source: {env_name}')
    lifted = text.replace(old_upper, new_upper).replace(old_lower, new_lower)
    if lifted == text:
        raise RuntimeError(f'V24 frozen source mechanical lift produced no change: {env_name}')
    compile(lifted, filename, 'exec')
    scope: dict[str, object] = {'__file__': str(HERE), '__name__': namespace}
    exec(compile(lifted, filename, 'exec'), scope, scope)
    return scope, lifted.encode('utf-8')


def _generated_main_entry_name(source: bytes) -> str:
    tree = compile(source, '<v24-generated-builder-entrypoint-proof>', 'exec', flags=ast.PyCF_ONLY_AST, dont_inherit=True)
    if not isinstance(tree, ast.Module):
        raise RuntimeError('V24 generated builder AST is not a module')
    matches: list[str] = []
    for stmt in tree.body:
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        if not (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == '__name__'
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == '__main__'
        ):
            continue
        if stmt.orelse:
            raise RuntimeError('V24 generated builder main guard unexpectedly has else branch')
        if len(stmt.body) != 1 or not isinstance(stmt.body[0], ast.Expr):
            raise RuntimeError('V24 generated builder main guard body shape drift')
        call = stmt.body[0].value
        if not isinstance(call, ast.Call) or call.args or call.keywords or not isinstance(call.func, ast.Name):
            raise RuntimeError('V24 generated builder main guard call shape drift')
        matches.append(call.func.id)
    if len(matches) != 1:
        raise RuntimeError(f'V24 generated builder __main__ guard count drift: {len(matches)}')
    return matches[0]


def _globals_audit_assignment_count(source: bytes, key: str) -> int:
    tree = compile(source, '<v24-generated-builder-audit-proof>', 'exec', flags=ast.PyCF_ONLY_AST, dont_inherit=True)
    if not isinstance(tree, ast.Module):
        raise RuntimeError('V24 generated builder audit AST is not a module')
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            base = target.value
            if not (
                isinstance(base, ast.Call)
                and isinstance(base.func, ast.Name)
                and base.func.id == 'globals'
                and not base.args
                and not base.keywords
            ):
                continue
            sl = target.slice
            if isinstance(sl, ast.Constant) and sl.value == key:
                count += 1
    return count


def _require_generated_audits(
    scope: dict[str, object],
    builder_sha: str,
    outer_fixtures: dict[str, bool],
) -> tuple[dict[str, object], dict[str, object]]:
    zero = scope.get('V24_ZERO_RUNTIME_STATIC_PROOF_AUDIT')
    if not isinstance(zero, dict):
        raise RuntimeError('V24 zero-runtime binding audit missing after controlled generated entrypoint execution')
    expected_zero = {
        'status': ZERO_PROOF_STATUS,
        'proofTargetSha256': builder_sha,
        'proofTargetDirectSubprocessSurface': ['run'],
        'proofTargetIsExactCompiledBuilderBytes': True,
        'scannerReboundFromOuterLauncher': True,
        'scannerExpectedSurfacePreserved': True,
        'scienceFalse': True,
    }
    if zero != expected_zero:
        raise RuntimeError(f'V24 zero-runtime binding audit drift: {zero!r}')

    v5 = scope.get('V24_V5_EXPECTED_BASE_AUDIT')
    if not isinstance(v5, dict):
        raise RuntimeError('V24 V5 expected-base audit missing after controlled generated entrypoint execution')
    if v5.get('status') != V5_PROOF_STATUS or v5.get('scienceFalse') is not True:
        raise RuntimeError(f'V24 V5 expected-base audit drift: {v5!r}')
    fixtures = v5.get('fixtures')
    if not isinstance(fixtures, dict) or fixtures != outer_fixtures:
        raise RuntimeError(f'V24 V5 fixture audit mismatch: inner={fixtures!r} outer={outer_fixtures!r}')
    for false_key in (
        'authorizationRefCreated',
        'dispatchCreated',
        'scientificOrdinalAllocated',
        'seedUniverseConsumed',
        'scienceInvoked',
        'solverExecuted',
        'protectedResultsOpened',
    ):
        if v5.get(false_key) is not False:
            raise RuntimeError(f'V24 V5 audit protected-boundary drift: {false_key}={v5.get(false_key)!r}')
    return zero, v5


def _write_entry_proof(path_text: str, payload: dict[str, object]) -> None:
    target = Path(path_text)
    target.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    out = dict(payload)
    out['receiptSha256'] = hashlib.sha256(canonical).hexdigest()
    target.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _prepare_builder() -> tuple[
    bytes,
    str,
    dict[str, object],
    dict[str, bool],
    object,
    object,
    str,
    dict[str, object],
]:
    v23_scope, v23_lifted = _load_lifted_scope(
        'V23_FROZEN_REVIEWER',
        FROZEN_V23_BLOB,
        'V23',
        'V24',
        'v23',
        'v24',
        '<v24-lifted-v23-reviewer>',
        '_avps_v24_lifted_v23_',
    )
    observed_loader = v23_scope.get('_load_observed_v5_metadata')
    fixture_builder = v23_scope.get('_metadata_fixtures')
    v5_patch_builder = v23_scope.get('_v5_patch_block')
    write_v5_proof = v23_scope.get('_write_v5_proof')
    if not callable(observed_loader) or not callable(fixture_builder) or not callable(v5_patch_builder) or not callable(write_v5_proof):
        raise RuntimeError('V24 lifted V23 helper API drift')
    if callable(v23_scope.get('_run')) is not True:
        raise RuntimeError('V24 lifted V23 reviewer entrypoint missing')

    observed = observed_loader()  # type: ignore[misc]
    outer_fixtures = fixture_builder()  # type: ignore[misc]
    if not isinstance(observed, dict) or not isinstance(outer_fixtures, dict):
        raise RuntimeError('V24 lifted V23 metadata proof API result drift')

    v22_scope, v22_lifted = _load_lifted_scope(
        'V22_FROZEN_REVIEWER',
        FROZEN_V22_BLOB,
        'V22',
        'V24',
        'v22',
        'v24',
        '<v24-lifted-v22-reviewer>',
        '_avps_v24_lifted_v22_',
    )
    original_rebind = v22_scope.get('_rebind_block')
    builder_fn = v22_scope.get('_build_v24_builder_bytes')
    surface_fn = v22_scope.get('_direct_subprocess_surface')
    write_zero_proof = v22_scope.get('_write_zero_proof')
    if not callable(original_rebind) or not callable(builder_fn) or not callable(surface_fn) or not callable(write_zero_proof):
        raise RuntimeError('V24 lifted V22 builder API drift')
    if callable(v22_scope.get('_run')) is not True:
        raise RuntimeError('V24 lifted V22 reviewer entrypoint missing')

    v22_scope['_rebind_block'] = original_rebind
    baseline = builder_fn()  # type: ignore[misc]
    if not isinstance(baseline, bytes):
        raise RuntimeError('V24 lifted V22 baseline builder did not return bytes')

    captured: dict[str, bytes] = {}

    def combined_rebind(indent: bytes) -> bytes:
        base = original_rebind(indent)  # type: ignore[misc]
        if not isinstance(base, bytes):
            raise RuntimeError('V24 lifted V22 rebind block did not return bytes')
        extra = v5_patch_builder(indent)  # type: ignore[misc]
        if not isinstance(extra, bytes):
            raise RuntimeError('V24 lifted V23 V5 patch block did not return bytes')
        marker = b'# V24 narrow repair: frozen V5 immutable expected-base separation only.\n'
        if extra.count(marker) != 1 or base.count(marker) != 0:
            raise RuntimeError('V24 V5 local repair block marker drift')
        captured['extra'] = extra
        return base + extra

    v22_scope['_rebind_block'] = combined_rebind
    builder = builder_fn()  # type: ignore[misc]
    if not isinstance(builder, bytes):
        raise RuntimeError('V24 generated builder did not return bytes')
    extra = captured.get('extra')
    if not isinstance(extra, bytes) or not extra:
        raise RuntimeError('V24 generated V5 repair block was not captured')
    if builder.count(extra) != 1:
        raise RuntimeError(f'V24 generated V5 repair block count drift: {builder.count(extra)}')
    if builder.replace(extra, b'', 1) != baseline:
        raise RuntimeError('V24 V5 repair is not the only delta from accepted V22->V24 generated builder')

    builder_sha = hashlib.sha256(builder).hexdigest()
    surface = surface_fn(builder, '<v24-authoritative-generated-builder-proof-target>')  # type: ignore[misc]
    if surface != ['run']:
        raise RuntimeError(f'V24 authoritative proof-target subprocess API surface drift: {surface!r}')
    entry_name = _generated_main_entry_name(builder)
    if _globals_audit_assignment_count(builder, 'V24_ZERO_RUNTIME_STATIC_PROOF_AUDIT') != 1:
        raise RuntimeError('V24 zero-runtime audit producer count drift')
    if _globals_audit_assignment_count(builder, 'V24_V5_EXPECTED_BASE_AUDIT') != 1:
        raise RuntimeError('V24 V5 audit producer count drift')

    provenance = {
        'frozenV23Head': FROZEN_V23_HEAD,
        'frozenV23Blob': FROZEN_V23_BLOB,
        'frozenV22Head': FROZEN_V22_HEAD,
        'frozenV22Blob': FROZEN_V22_BLOB,
        'liftedV23SourceSha256': hashlib.sha256(v23_lifted).hexdigest(),
        'liftedV22SourceSha256': hashlib.sha256(v22_lifted).hexdigest(),
        'baselineGeneratedBuilderSha256': hashlib.sha256(baseline).hexdigest(),
        'authoritativeGeneratedBuilderSha256': builder_sha,
        'v5RepairBlockSha256': hashlib.sha256(extra).hexdigest(),
        'v5RepairIsOnlyDeltaFromAcceptedLiftedV22Builder': True,
        'directSubprocessSurface': list(surface),
        'generatedMainGuardEntryName': entry_name,
        'zeroAuditProducerCount': 1,
        'v5AuditProducerCount': 1,
    }
    return builder, builder_sha, observed, outer_fixtures, write_zero_proof, write_v5_proof, entry_name, provenance


def _run() -> None:
    try:
        builder, builder_sha, observed, outer_fixtures, write_zero_proof, write_v5_proof, entry_name, provenance = _prepare_builder()
        proof_only = '--v24-proof-only' in sys.argv or os.environ.get('V24_PREACTUAL_ACTIVE') == '1'

        if not proof_only:
            globals()['_V24_ZERO_RUNTIME_STATIC_SOURCE'] = builder
            globals()['_V24_ZERO_RUNTIME_STATIC_SOURCE_SHA256'] = builder_sha
            globals()['_V24_OBSERVED_V5_METADATA'] = observed
            exec(compile(builder, '<v24-generated-effective>', 'exec'), globals(), globals())
            return

        common: dict[str, object] = {
            '__file__': str(HERE),
            '_V24_ZERO_RUNTIME_STATIC_SOURCE': builder,
            '_V24_ZERO_RUNTIME_STATIC_SOURCE_SHA256': builder_sha,
            '_V24_OBSERVED_V5_METADATA': observed,
        }

        negative_scope = dict(common)
        negative_scope['__name__'] = '_avps_v24_negative_v23_like_nonmain_'
        exec(compile(builder, '<v24-generated-effective-negative>', 'exec'), negative_scope, negative_scope)
        if negative_scope.get('V24_ZERO_RUNTIME_STATIC_PROOF_AUDIT') is not None:
            raise RuntimeError('V24 V23-like non-main namespace unexpectedly materialized zero-runtime audit')
        if negative_scope.get('V24_V5_EXPECTED_BASE_AUDIT') is not None:
            raise RuntimeError('V24 V23-like non-main namespace unexpectedly materialized V5 audit')
        negative_rejected = False
        negative_message = ''
        try:
            _require_generated_audits(negative_scope, builder_sha, outer_fixtures)
        except RuntimeError as exc:
            negative_rejected = True
            negative_message = str(exc)
        if not negative_rejected or 'zero-runtime binding audit missing' not in negative_message:
            raise RuntimeError(f'V24 V23-like non-main namespace did not fail on missing audit: {negative_message!r}')

        controlled_name = '_avps_v24_preactual_controlled_'
        controlled_scope = dict(common)
        controlled_scope['__name__'] = controlled_name
        exec(compile(builder, '<v24-generated-effective-controlled>', 'exec'), controlled_scope, controlled_scope)
        if controlled_scope.get('V24_ZERO_RUNTIME_STATIC_PROOF_AUDIT') is not None:
            raise RuntimeError('V24 controlled namespace materialized zero audit before explicit entrypoint call')
        if controlled_scope.get('V24_V5_EXPECTED_BASE_AUDIT') is not None:
            raise RuntimeError('V24 controlled namespace materialized V5 audit before explicit entrypoint call')
        generated_entry = controlled_scope.get(entry_name)
        if not callable(generated_entry):
            raise RuntimeError(f'V24 controlled generated entrypoint missing: {entry_name!r}')
        generated_entry()  # type: ignore[misc]
        if controlled_scope.get('__name__') != controlled_name:
            raise RuntimeError('V24 controlled generated entrypoint changed namespace identity')
        zero_audit, v5_audit = _require_generated_audits(controlled_scope, builder_sha, outer_fixtures)

        zero_out = _argv_value('--v24-zero-runtime-proof-out')
        if zero_out:
            write_zero_proof(zero_out, zero_audit)  # type: ignore[misc]
        v5_out = _argv_value('--v24-v5-proof-out')
        if v5_out:
            write_v5_proof(v5_out, v5_audit)  # type: ignore[misc]

        entry_audit: dict[str, object] = {
            'status': ENTRY_PROOF_STATUS,
            **provenance,
            'negativeSyntheticNonMainRejected': True,
            'negativeSyntheticFailureMessage': negative_message,
            'controlledNamespace': controlled_name,
            'controlledNamespaceRemainedNonMain': True,
            'controlledGeneratedEntrypointCalledDirectly': True,
            'controlledGeneratedEntrypointCallCount': 1,
            'zeroAuditMaterializedAfterControlledEntrypoint': True,
            'v5AuditMaterializedAfterControlledEntrypoint': True,
            'zeroAuditStatus': zero_audit['status'],
            'v5AuditStatus': v5_audit['status'],
            'actualReviewerEntrypointActivated': False,
            'protectedReviewerActivated': False,
            'scienceInvoked': False,
            'solverExecuted': False,
            'authorizationRefCreated': False,
            'dispatchCreated': False,
            'scientificOrdinalAllocated': False,
            'seedUniverseConsumed': False,
            'protectedResultsOpened': False,
            'scienceFalse': True,
        }
        entry_out = _argv_value('--v24-entrypoint-proof-out')
        if entry_out:
            _write_entry_proof(entry_out, entry_audit)
    except BaseException as exc:
        if '--v24-proof-only' in sys.argv or os.environ.get('V24_PREACTUAL_ACTIVE') == '1':
            _write_failure(exc)
        raise


if __name__ == '__main__':
    _run()
