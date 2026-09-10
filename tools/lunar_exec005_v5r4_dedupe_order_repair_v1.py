from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

SCANNER_PATH = Path('experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py')
SCHEMA = 'LUNAR_EXEC005_V5R4_REPOSITORY_CONTEXT_DIAGNOSTIC_V1'
PASS_STATUS = 'PASS_V5R4_DEDUPE_ORDER_REPAIR_STABLE_NOT_AUTHORIZED'
DRIFT_STATUS = 'FAIL_CLOSED_V5R4_REPOSITORY_CONTEXT_DRIFT_OBSERVED_NOT_AUTHORIZED'
EXCEPTION_STATUS = 'FAIL_CLOSED_V5R4_REPOSITORY_CONTEXT_EXCEPTION_NOT_AUTHORIZED'


def load_scanner():
    spec = importlib.util.spec_from_file_location('exec005_v5r4_bound_scanner', SCANNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('unable to load bound repository-global scanner')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _project_repository_identity(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise RuntimeError('embedded repository identity must be an object or null')
    out: dict[str, Any] = {}
    for key in ('id', 'node_id', 'name', 'full_name'):
        if key in value:
            out[key] = value[key]
    owner = value.get('owner')
    if owner is not None:
        if not isinstance(owner, dict):
            raise RuntimeError('embedded repository owner identity must be an object or null')
        owner_out: dict[str, Any] = {}
        for key in ('id', 'node_id', 'login'):
            if key in owner:
                owner_out[key] = owner[key]
        out['owner'] = owner_out
    if not out:
        raise RuntimeError('embedded repository object lacks stable identity fields')
    return out


def _retain_root_operational_field(surface: str, path: tuple[str, ...], name: str) -> bool:
    if path:
        return False
    if surface == 'runs' and name in {'status', 'conclusion', 'run_attempt'}:
        return True
    if surface == 'pulls' and name in {'state', 'state_reason'}:
        return True
    return False


def _v5r4_stability_value(
    base: Any,
    surface: str,
    value: Any,
    *,
    path: tuple[str, ...] = (),
    artifact_row: bool = False,
) -> Any:
    """Project row semantics before any same-ID equivalence/conflict decision."""
    if isinstance(value, dict):
        if surface == 'pulls' and path in {('head', 'repo'), ('base', 'repo')}:
            return _project_repository_identity(value)
        if surface == 'runs' and path in {('repository',), ('head_repository',)}:
            return _project_repository_identity(value)
        out: dict[str, Any] = {}
        for name in sorted(value):
            if name == 'pushed_at':
                continue
            if artifact_row and not path and name == 'expired':
                continue
            if name in base.MUTABLE_OPERATIONAL_KEYS and not _retain_root_operational_field(surface, path, name):
                continue
            out[name] = _v5r4_stability_value(
                base,
                surface,
                value[name],
                path=path + (name,),
                artifact_row=False,
            )
        return out
    if isinstance(value, list):
        normalized = [
            _v5r4_stability_value(base, surface, item, path=path + ('[]',), artifact_row=False)
            for item in value
        ]
        return sorted(normalized, key=_canonical_bytes)
    return value


def row_identity(surface: str, row: dict[str, Any]) -> str:
    if surface == 'branches':
        value = str(row.get('name') or '')
    else:
        value = str(row.get('id') or row.get('number') or '')
    if not value:
        raise RuntimeError(f'{surface} row lacks stable diagnostic identity')
    return value


def _numeric_row_id(row: dict[str, Any], surface: str) -> int:
    try:
        value = int(row.get('id') or 0)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f'{surface} row lacks a numeric id required for snapshot fencing') from exc
    if value <= 0:
        raise RuntimeError(f'{surface} row lacks a positive id required for snapshot fencing')
    return value


def _v5r4_projected_row(base: Any, surface: str, row: dict[str, Any]) -> Any:
    return _v5r4_stability_value(base, surface, row, artifact_row=(surface == 'artifacts'))


def _v5r4_dedupe_rows(base: Any, surface: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate only after V5R4 path-specific projection has defined semantic equality."""
    by_id: dict[str, dict[str, Any]] = {}
    projected_by_id: dict[str, Any] = {}
    for row in rows:
        identity = row_identity(surface, row)
        projected = _v5r4_projected_row(base, surface, row)
        if identity in projected_by_id and projected_by_id[identity] != projected:
            raise RuntimeError(f'{surface} row {identity} changed within one complete enumeration after V5R4 projection')
        by_id[identity] = row
        projected_by_id[identity] = projected
    if surface == 'branches':
        return [by_id[key] for key in sorted(by_id)]
    return [by_id[key] for key in sorted(by_id, key=int)]


def _filtered(base: Any, context: dict[str, Any], current_run_id: int | None) -> dict[str, Any]:
    return base._without_current_audit_self_metadata(context, current_run_id)


def v5r4_build_snapshot_fence(base: Any, context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    filtered = _filtered(base, context, current_run_id)
    branches = _v5r4_dedupe_rows(base, 'branches', filtered['branches'])
    max_ids: dict[str, int] = {}
    for surface in base.SNAPSHOT_ID_SURFACES:
        rows = _v5r4_dedupe_rows(base, surface, filtered[surface])
        max_ids[surface] = max((_numeric_row_id(row, surface) for row in rows), default=0)
    return {
        'mode': 'FIRST_COMPLETE_ENUMERATION_HIGH_WATER_V5R4_PROJECT_BEFORE_DEDUPE',
        'branchNames': [str(row['name']) for row in branches],
        'maxIds': max_ids,
    }


def v5r4_apply_snapshot_fence(
    base: Any,
    context: dict[str, Any],
    fence: dict[str, Any],
    current_run_id: int | None = None,
) -> dict[str, Any]:
    filtered = _filtered(base, context, current_run_id)
    expected_branches = {str(name) for name in fence.get('branchNames', [])}
    branches = _v5r4_dedupe_rows(base, 'branches', filtered['branches'])
    branch_map = {str(row.get('name') or ''): row for row in branches}
    missing = sorted(expected_branches - set(branch_map))
    if missing:
        raise RuntimeError(f'snapshot-fenced branches disappeared during audit: {missing}')
    out: dict[str, Any] = {'branches': [branch_map[name] for name in sorted(expected_branches)]}
    max_ids = fence.get('maxIds')
    if not isinstance(max_ids, dict):
        raise ValueError('snapshot fence requires maxIds object')
    for surface in base.SNAPSHOT_ID_SURFACES:
        high_water = int(max_ids.get(surface, 0) or 0)
        rows = _v5r4_dedupe_rows(base, surface, filtered[surface])
        out[surface] = [row for row in rows if _numeric_row_id(row, surface) <= high_water]
    return out


def v5r4_post_fence_rows(
    base: Any,
    context: dict[str, Any],
    fence: dict[str, Any],
    current_run_id: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    filtered = _filtered(base, context, current_run_id)
    expected_branches = {str(name) for name in fence.get('branchNames', [])}
    branches = _v5r4_dedupe_rows(base, 'branches', filtered['branches'])
    out: dict[str, list[dict[str, Any]]] = {
        'branches': [row for row in branches if str(row.get('name') or '') not in expected_branches]
    }
    max_ids = fence.get('maxIds')
    if not isinstance(max_ids, dict):
        raise ValueError('snapshot fence requires maxIds object')
    for surface in base.SNAPSHOT_ID_SURFACES:
        high_water = int(max_ids.get(surface, 0) or 0)
        rows = _v5r4_dedupe_rows(base, surface, filtered[surface])
        out[surface] = [row for row in rows if _numeric_row_id(row, surface) > high_water]
    return out


def v5r4_canonical_stability_context(base: Any, context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    filtered = _filtered(base, context, current_run_id)
    out: dict[str, Any] = {}
    for surface in base.SURFACE_KEYS:
        normalized = [
            _v5r4_projected_row(base, surface, row)
            for row in filtered[surface]
        ]
        out[surface] = sorted(normalized, key=_canonical_bytes)
    return out


def row_fingerprint(row: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(row)).hexdigest()


def context_evidence(base: Any, context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    canonical = v5r4_canonical_stability_context(base, context, current_run_id)
    rows: dict[str, list[dict[str, str]]] = {}
    for surface in base.SURFACE_KEYS:
        entries = [{'id': row_identity(surface, row), 'sha256': row_fingerprint(row)} for row in canonical[surface]]
        entries.sort(key=lambda item: (item['id'], item['sha256']))
        identities = [item['id'] for item in entries]
        if len(set(identities)) != len(identities):
            duplicates = sorted({identity for identity in identities if identities.count(identity) > 1})
            raise RuntimeError(f'{surface} diagnostic identity cardinality conflict ids={duplicates}')
        rows[surface] = entries
    return {
        'contextSha256': hashlib.sha256(_canonical_bytes(canonical)).hexdigest(),
        'surfaceCounts': {surface: len(rows[surface]) for surface in base.SURFACE_KEYS},
        'rows': rows,
    }


def diff_evidence(base: Any, left: dict[str, Any], right: dict[str, Any]) -> dict[str, list[dict[str, str | None]]]:
    out: dict[str, list[dict[str, str | None]]] = {'added': [], 'removed': [], 'changed': []}
    for surface in base.SURFACE_KEYS:
        a = {item['id']: item['sha256'] for item in left['rows'][surface]}
        b = {item['id']: item['sha256'] for item in right['rows'][surface]}
        for identity in sorted(set(b) - set(a)):
            out['added'].append({'surface': surface, 'id': identity, 'before': None, 'after': b[identity]})
        for identity in sorted(set(a) - set(b)):
            out['removed'].append({'surface': surface, 'id': identity, 'before': a[identity], 'after': None})
        for identity in sorted(set(a) & set(b)):
            if a[identity] != b[identity]:
                out['changed'].append({'surface': surface, 'id': identity, 'before': a[identity], 'after': b[identity]})
    return out


def diff_count(diff: dict[str, list[dict[str, str | None]]]) -> int:
    return sum(len(diff[key]) for key in ('added', 'removed', 'changed'))


def _empty_context(base: Any) -> dict[str, list[dict[str, Any]]]:
    return {surface: [] for surface in base.SURFACE_KEYS}


def _sanitize_exception_message(message: str) -> str:
    text = re.sub(r'(?i)bearer\s+\S+', 'Bearer <redacted>', str(message))
    text = re.sub(r'https?://\S+', '<url>', text)
    text = re.sub(r'(?i)(gh[pousr]_[A-Za-z0-9_]+)', '<redacted-token>', text)
    return ' '.join(text.split())[:1000]


def _base_receipt() -> dict[str, Any]:
    return {
        'schema': SCHEMA,
        'status': EXCEPTION_STATUS,
        'scienceAuthorized': False,
        'protectedAttemptAuthorized': False,
        'seedValuesPresent': False,
        'solverRuntimePresent': False,
        'candidateCount': 198,
        'candidateState': 'candidate-only/unallocated/unapplied/unconsumed',
        'normalization': {
            'preservedReviewedLifecycleNormalization': True,
            'nestedPushedAtExcluded': True,
            'artifactExpiredExcludedOnlyAtArtifactRow': True,
            'pullHeadBaseRepositoryCanonicalProjection': True,
            'runRepositoryCanonicalProjection': True,
            'rootRunStatusConclusionAttemptPreserved': True,
            'rootPullStateAndStateReasonPreserved': True,
            'pathSpecificProjectionPrecedesStableIdDedupe': True,
            'allObservationsUseV5R4BoundPath': True,
        },
        'batchCount': 3,
        'completedStage': 'initialized',
        'batches': [],
        'crossBatchDiffs': [],
        'finalLiveReenumeration': None,
        'allIntraBatchStable': False,
        'crossBatchCommonContext': False,
        'finalLiveEqualsCapturedContext': False,
        'exception': None,
    }


def _record_exception(receipt: dict[str, Any], exc: BaseException) -> None:
    receipt['status'] = EXCEPTION_STATUS
    receipt['exception'] = {'class': type(exc).__name__, 'message': _sanitize_exception_message(str(exc))}


def write_receipt(output: Path, receipt: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')


def bound_observation(base: Any, raw: dict[str, Any], fence: dict[str, Any], current_run_id: int | None) -> dict[str, Any]:
    bounded = v5r4_apply_snapshot_fence(base, raw, fence, current_run_id)
    evidence = context_evidence(base, bounded, current_run_id)
    arrivals = {surface: len(rows) for surface, rows in v5r4_post_fence_rows(base, raw, fence, current_run_id).items()}
    return {'stableContextSha256': evidence['contextSha256'], 'postFenceArrivalCounts': arrivals, 'evidence': evidence}


def observe_batch(base: Any, collect_fn: Callable[[], dict[str, Any]], fence: dict[str, Any], current_run_id: int | None) -> dict[str, Any]:
    first = bound_observation(base, collect_fn(), fence, current_run_id)
    second = bound_observation(base, collect_fn(), fence, current_run_id)
    intra = diff_evidence(base, first['evidence'], second['evidence'])
    return {
        'stable': diff_count(intra) == 0,
        'stableContextSha256': second['stableContextSha256'],
        'postFenceArrivalCounts': second['postFenceArrivalCounts'],
        'intraBatchDiff': intra,
        'evidence': second['evidence'],
    }


def run_live(
    base: Any,
    repository: str,
    issue_number: int,
    token: str,
    current_run_id: int | None,
    receipt: dict[str, Any],
    collect_override: Callable[[], dict[str, Any]] | None = None,
) -> int:
    collect_fn = collect_override or (lambda: base.collect(repository, issue_number, token))
    receipt['completedStage'] = 'collecting-shared-snapshot-fence'
    initial_raw = collect_fn()
    fence = v5r4_build_snapshot_fence(base, initial_raw, current_run_id)
    first = bound_observation(base, initial_raw, fence, current_run_id)
    receipt['snapshotFenceSha256'] = hashlib.sha256(_canonical_bytes(fence)).hexdigest()
    receipt['capturedContextSha256'] = first['evidence']['contextSha256']
    receipt['completedStage'] = 'shared-snapshot-fence-captured'

    second = bound_observation(base, collect_fn(), fence, current_run_id)
    intra1 = diff_evidence(base, first['evidence'], second['evidence'])
    receipt['batches'].append({
        'stable': diff_count(intra1) == 0,
        'stableContextSha256': second['stableContextSha256'],
        'postFenceArrivalCounts': second['postFenceArrivalCounts'],
        'intraBatchDiff': intra1,
        'evidence': second['evidence'],
    })
    receipt['completedStage'] = 'batch-1-complete'

    for index in (2, 3):
        receipt['batches'].append(observe_batch(base, collect_fn, fence, current_run_id))
        receipt['completedStage'] = f'batch-{index}-complete'

    captured = receipt['batches'][0]['evidence']
    cross = [
        {'fromBatch': 1, 'toBatch': index + 1, 'diff': diff_evidence(base, captured, receipt['batches'][index]['evidence'])}
        for index in (1, 2)
    ]
    receipt['crossBatchDiffs'] = cross
    receipt['completedStage'] = 'cross-batch-comparison-complete'

    final = bound_observation(base, collect_fn(), fence, current_run_id)
    final_diff = diff_evidence(base, captured, final['evidence'])
    receipt['finalLiveReenumeration'] = {
        'stableContextSha256': final['stableContextSha256'],
        'postFenceArrivalCounts': final['postFenceArrivalCounts'],
        'evidence': final['evidence'],
        'diffFromCapturedBatch1': final_diff,
    }
    receipt['completedStage'] = 'final-live-reenumeration-complete'

    receipt['allIntraBatchStable'] = all(batch['stable'] for batch in receipt['batches'])
    receipt['crossBatchCommonContext'] = all(diff_count(item['diff']) == 0 for item in cross)
    receipt['finalLiveEqualsCapturedContext'] = diff_count(final_diff) == 0
    passed = receipt['allIntraBatchStable'] and receipt['crossBatchCommonContext'] and receipt['finalLiveEqualsCapturedContext']
    receipt['status'] = PASS_STATUS if passed else DRIFT_STATUS
    receipt['completedStage'] = 'terminal-classification'
    return 0 if passed else 3


def _repo(identity: str = 'search-maker/twilight-mystic-experiments', repo_id: int = 1321052980, size: int = 22000) -> dict[str, Any]:
    owner, name = identity.split('/', 1)
    return {
        'id': repo_id,
        'node_id': f'R_{repo_id}',
        'name': name,
        'full_name': identity,
        'owner': {'id': 304153003, 'node_id': 'U_owner', 'login': owner, 'html_url': 'https://example.invalid/owner'},
        'size': size,
        'open_issues_count': 250,
        'open_issues': 250,
        'watchers_count': 0,
        'forks_count': 0,
        'default_branch': 'main',
        'pushed_at': 'repo-wide-noise',
        'html_url': 'https://example.invalid/repo',
    }


def _fixture_context(base: Any) -> dict[str, Any]:
    context = _empty_context(base)
    context['branches'] = [{'name': 'main', 'commit': {'sha': 'a' * 40}, 'pushed_at': 'noise-1'}]
    context['runs'] = [{
        'id': 101, 'name': 'workflow-name', 'path': '.github/workflows/example.yml', 'workflow_id': 909,
        'event': 'push', 'status': 'completed', 'conclusion': 'success', 'run_attempt': 1,
        'head_sha': 'b' * 40, 'head_branch': 'main', 'repository': _repo(), 'head_repository': _repo(),
        'updated_at': 'lifecycle-1',
    }]
    context['artifacts'] = [{'id': 201, 'name': 'proof', 'expired': False, 'workflow_run': {'id': 99}}]
    context['pulls'] = [{
        'id': 301, 'number': 3, 'title': 'p', 'state': 'open', 'state_reason': None,
        'head': {'sha': 'c' * 40, 'ref': 'feature', 'repo': _repo()},
        'base': {'sha': 'd' * 40, 'ref': 'main', 'repo': _repo()}, 'updated_at': 'lifecycle-1',
    }]
    context['issues'] = [{'id': 401, 'number': 4, 'body': 'i'}]
    context['issueComments'] = [{'id': 501, 'body': 'c'}]
    context['pullReviewComments'] = [{'id': 601, 'body': 'r'}]
    context['commitComments'] = [{'id': 701, 'body': 'k'}]
    context['issue60Comments'] = [{'id': 801, 'body': '60'}]
    return context


def _single_change(base: Any, baseline: dict[str, Any], context: dict[str, Any], surface: str, identity: str) -> None:
    fence = v5r4_build_snapshot_fence(base, context, None)
    evidence = bound_observation(base, context, fence, None)['evidence']
    diff = diff_evidence(base, baseline, evidence)
    assert diff_count(diff) == 1, (surface, identity, diff)
    assert diff['changed'][0]['surface'] == surface and diff['changed'][0]['id'] == identity, diff


def _expect_same_id_conflict(base: Any, context: dict[str, Any], surface: str, mutate: Callable[[dict[str, Any]], None], identity: str) -> str:
    fixture = copy.deepcopy(context)
    repeated = copy.deepcopy(fixture[surface][0])
    mutate(repeated)
    fixture[surface].append(repeated)
    message = ''
    try:
        v5r4_build_snapshot_fence(base, fixture, None)
    except RuntimeError as exc:
        message = str(exc)
    assert f'{surface} row {identity}' in message and 'V5R4 projection' in message, message
    return message


def self_test(base: Any) -> dict[str, Any]:
    context = _fixture_context(base)
    fence = v5r4_build_snapshot_fence(base, context, None)
    baseline = bound_observation(base, context, fence, None)['evidence']
    assert diff_count(diff_evidence(base, baseline, copy.deepcopy(baseline))) == 0

    summary_noise = copy.deepcopy(context)
    for repo in (
        summary_noise['pulls'][0]['head']['repo'], summary_noise['pulls'][0]['base']['repo'],
        summary_noise['runs'][0]['repository'], summary_noise['runs'][0]['head_repository'],
    ):
        repo['size'] += 999
        repo['open_issues_count'] += 7
        repo['open_issues'] += 7
        repo['watchers_count'] += 3
        repo['default_branch'] = 'temporary-repo-summary-noise'
        repo['pushed_at'] = 'repo-wide-noise-2'
    summary_noise['branches'][0]['pushed_at'] = 'noise-2'
    summary_noise['artifacts'][0]['expired'] = True
    summary_noise['runs'][0]['updated_at'] = 'lifecycle-2'
    summary_noise['pulls'][0]['updated_at'] = 'lifecycle-2'
    summary_evidence = bound_observation(base, summary_noise, fence, None)['evidence']
    assert diff_count(diff_evidence(base, baseline, summary_evidence)) == 0

    meaningful_cases: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
        ('pulls', '301', lambda x: x['pulls'][0]['head'].__setitem__('sha', '1' * 40)),
        ('pulls', '301', lambda x: x['pulls'][0]['head'].__setitem__('ref', 'different-feature')),
        ('pulls', '301', lambda x: x['pulls'][0]['base'].__setitem__('sha', '2' * 40)),
        ('pulls', '301', lambda x: x['pulls'][0]['base'].__setitem__('ref', 'release')),
        ('pulls', '301', lambda x: x['pulls'][0]['head']['repo'].__setitem__('full_name', 'other/repo')),
        ('pulls', '301', lambda x: x['pulls'][0].__setitem__('state', 'closed')),
        ('pulls', '301', lambda x: x['pulls'][0].__setitem__('state_reason', 'completed')),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('event', 'workflow_dispatch')),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('status', 'in_progress')),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('conclusion', 'failure')),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('run_attempt', 2)),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('head_sha', '3' * 40)),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('head_branch', 'feature')),
        ('runs', '101', lambda x: x['runs'][0].__setitem__('workflow_id', 910)),
        ('runs', '101', lambda x: x['runs'][0]['repository'].__setitem__('id', 999999)),
    ]
    for surface, identity, mutate in meaningful_cases:
        changed = copy.deepcopy(context)
        mutate(changed)
        _single_change(base, baseline, changed, surface, identity)

    identical = copy.deepcopy(context)
    identical['runs'].append(copy.deepcopy(identical['runs'][0]))
    identical_fence = v5r4_build_snapshot_fence(base, identical, None)
    assert bound_observation(base, identical, identical_fence, None)['evidence']['surfaceCounts']['runs'] == 1

    lifecycle = copy.deepcopy(context)
    lifecycle_repeat = copy.deepcopy(lifecycle['runs'][0])
    lifecycle_repeat['updated_at'] = 'different-lifecycle-time'
    lifecycle['runs'].append(lifecycle_repeat)
    lifecycle_fence = v5r4_build_snapshot_fence(base, lifecycle, None)
    assert bound_observation(base, lifecycle, lifecycle_fence, None)['evidence']['surfaceCounts']['runs'] == 1

    run_summary_duplicate = copy.deepcopy(context)
    run_repeat = copy.deepcopy(run_summary_duplicate['runs'][0])
    run_repeat['repository']['size'] += 1
    run_repeat['repository']['open_issues_count'] += 1
    run_repeat['head_repository']['watchers_count'] += 1
    run_summary_duplicate['runs'].append(run_repeat)
    run_summary_fence = v5r4_build_snapshot_fence(base, run_summary_duplicate, None)
    assert bound_observation(base, run_summary_duplicate, run_summary_fence, None)['evidence']['surfaceCounts']['runs'] == 1

    pull_summary_duplicate = copy.deepcopy(context)
    pull_repeat = copy.deepcopy(pull_summary_duplicate['pulls'][0])
    pull_repeat['head']['repo']['size'] += 1
    pull_repeat['base']['repo']['open_issues_count'] += 1
    pull_summary_duplicate['pulls'].append(pull_repeat)
    pull_summary_fence = v5r4_build_snapshot_fence(base, pull_summary_duplicate, None)
    assert bound_observation(base, pull_summary_duplicate, pull_summary_fence, None)['evidence']['surfaceCounts']['pulls'] == 1

    duplicate_conflicts = {
        'runStatus': _expect_same_id_conflict(base, context, 'runs', lambda r: r.__setitem__('status', 'in_progress'), '101'),
        'runConclusion': _expect_same_id_conflict(base, context, 'runs', lambda r: r.__setitem__('conclusion', 'failure'), '101'),
        'runAttempt': _expect_same_id_conflict(base, context, 'runs', lambda r: r.__setitem__('run_attempt', 2), '101'),
        'runHeadSha': _expect_same_id_conflict(base, context, 'runs', lambda r: r.__setitem__('head_sha', '9' * 40), '101'),
        'pullState': _expect_same_id_conflict(base, context, 'pulls', lambda r: r.__setitem__('state', 'closed'), '301'),
        'pullStateReason': _expect_same_id_conflict(base, context, 'pulls', lambda r: r.__setitem__('state_reason', 'completed'), '301'),
    }

    self_context = copy.deepcopy(context)
    self_context['runs'].append({'id': 999, 'head_sha': 'f' * 40})
    self_context['artifacts'].append({'id': 9991, 'name': 'self', 'workflow_run': {'id': 999}})
    self_fence = v5r4_build_snapshot_fence(base, self_context, 999)
    assert bound_observation(base, self_context, self_fence, 999)['evidence']['contextSha256'] == baseline['contextSha256']

    exception_path = Path('v5r4-diagnostic-selftest-exception.json')
    receipt = _base_receipt()
    conflict = copy.deepcopy(context)
    conflict_repeat = copy.deepcopy(conflict['runs'][0])
    conflict_repeat['status'] = 'in_progress'
    conflict['runs'].append(conflict_repeat)
    sequence = [copy.deepcopy(context), conflict]

    def collect_fixture() -> dict[str, Any]:
        if not sequence:
            raise RuntimeError('fixture exhausted')
        return sequence.pop(0)

    try:
        run_live(base, 'fixture/repo', 60, 'fixture-token', None, receipt, collect_override=collect_fixture)
        raise AssertionError('conflicting repeat fixture unexpectedly passed')
    except RuntimeError as exc:
        _record_exception(receipt, exc)
    finally:
        write_receipt(exception_path, receipt)
    persisted = json.loads(exception_path.read_text())
    exception_path.unlink()
    assert persisted['schema'] == SCHEMA
    assert persisted['status'] == EXCEPTION_STATUS
    assert persisted['scienceAuthorized'] is False and persisted['protectedAttemptAuthorized'] is False
    assert persisted['candidateCount'] == 198
    assert persisted['candidateState'] == 'candidate-only/unallocated/unapplied/unconsumed'
    assert persisted['exception']['class'] == 'RuntimeError'
    assert 'runs row 101' in persisted['exception']['message']

    return {
        'sameContextPass': True,
        'nestedRepositorySummaryNoiseIgnored': True,
        'meaningfulPullRunDriftCaughtCount': len(meaningful_cases),
        'identicalRepeatedStableIdCollapsed': {'surface': 'runs', 'id': '101'},
        'lifecycleOnlyRepeatedStableIdCollapsed': {'surface': 'runs', 'id': '101'},
        'sameIdRunRepositorySummaryOnlyCollapsed': {'surface': 'runs', 'id': '101'},
        'sameIdPullRepositorySummaryOnlyCollapsed': {'surface': 'pulls', 'id': '301'},
        'meaningfulSameIdConflictsRejectedAndNamed': sorted(duplicate_conflicts),
        'currentRunSelfMetadataExcluded': True,
        'exceptionReceiptPersisted': True,
        'pathSpecificProjectionPrecedesStableIdDedupe': True,
        'finalUsesSameBoundObservationPath': True,
        'candidateCount': 198,
        'candidateState': 'candidate-only/unallocated/unapplied/unconsumed',
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--repository')
    parser.add_argument('--issue-number', type=int, default=60)
    parser.add_argument('--current-run-id', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    base = load_scanner()
    if args.self_test:
        print(json.dumps(self_test(base), sort_keys=True))
        return 0
    if not args.repository or args.output is None:
        raise SystemExit('--repository and --output are required for live diagnostic')
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise SystemExit('GITHUB_TOKEN required')
    receipt = _base_receipt()
    code = 4
    try:
        code = run_live(base, args.repository, args.issue_number, token, args.current_run_id, receipt)
    except BaseException as exc:
        _record_exception(receipt, exc)
        code = 4
    finally:
        write_receipt(args.output, receipt)
    print(receipt['status'])
    return code


if __name__ == '__main__':
    raise SystemExit(main())
