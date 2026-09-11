from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

SCANNER_PATH = Path('experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py')
SCHEMA = 'LUNAR_EXEC005_V5R2_REPOSITORY_CONTEXT_DIAGNOSTIC_V1'


def load_scanner():
    spec = importlib.util.spec_from_file_location('exec005_v5r2_bound_scanner', SCANNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('unable to load bound repository-global scanner')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Exact V5R1/V4 normalization contract. Do not broaden this list locally.
def _v4_stability_value(base: Any, value: Any, artifact_row: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            name: _v4_stability_value(base, value[name], False)
            for name in sorted(value)
            if name not in base.MUTABLE_OPERATIONAL_KEYS
            and name != 'pushed_at'
            and not (artifact_row and name == 'expired')
        }
    if isinstance(value, list):
        normalized = [_v4_stability_value(base, item, False) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False,
                allow_nan=False,
            ),
        )
    return value


def v4_canonical_stability_context(base: Any, context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    filtered = base._without_current_audit_self_metadata(context, current_run_id)
    out: dict[str, Any] = {}
    for surface in base.SURFACE_KEYS:
        rows = filtered[surface]
        normalized = [_v4_stability_value(base, row, surface == 'artifacts') for row in rows]
        out[surface] = sorted(
            normalized,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False,
                allow_nan=False,
            ),
        )
    return out


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def v4_stable_context_sha256(base: Any, context: dict[str, Any], current_run_id: int | None = None) -> str:
    return hashlib.sha256(_canonical_bytes(v4_canonical_stability_context(base, context, current_run_id))).hexdigest()


def row_identity(surface: str, row: dict[str, Any]) -> str:
    value = str(row.get('name') or '') if surface == 'branches' else str(row.get('id') or row.get('number') or '')
    if not value:
        raise RuntimeError(f'{surface} row lacks stable diagnostic identity')
    return value


def row_fingerprint(surface: str, row: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(row)).hexdigest()


def context_evidence(base: Any, context: dict[str, Any], current_run_id: int | None = None) -> dict[str, Any]:
    canonical = v4_canonical_stability_context(base, context, current_run_id)
    rows: dict[str, list[dict[str, str]]] = {}
    for surface in base.SURFACE_KEYS:
        entries = [
            {'id': row_identity(surface, row), 'sha256': row_fingerprint(surface, row)}
            for row in canonical[surface]
        ]
        entries.sort(key=lambda item: (item['id'], item['sha256']))
        if len({item['id'] for item in entries}) != len(entries):
            raise RuntimeError(f'{surface} diagnostic identity cardinality conflict')
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


def self_test(base: Any) -> dict[str, Any]:
    context = _empty_context(base)
    context['branches'] = [{'name': 'main', 'commit': {'sha': 'a' * 40}, 'pushed_at': 'noise-1'}]
    context['runs'] = [{'id': 101, 'head_sha': 'b' * 40, 'status': 'queued'}]
    context['artifacts'] = [{'id': 201, 'name': 'proof', 'expired': False, 'workflow_run': {'id': 99}}]
    context['pulls'] = [{'id': 301, 'number': 3, 'title': 'p'}]
    context['issues'] = [{'id': 401, 'number': 4, 'body': 'i'}]
    context['issueComments'] = [{'id': 501, 'body': 'c'}]
    context['pullReviewComments'] = [{'id': 601, 'body': 'r'}]
    context['commitComments'] = [{'id': 701, 'body': 'k'}]
    context['issue60Comments'] = [{'id': 801, 'body': '60'}]
    baseline = context_evidence(base, context)
    assert diff_count(diff_evidence(base, baseline, copy.deepcopy(baseline))) == 0

    noise = copy.deepcopy(context)
    noise['branches'][0]['pushed_at'] = 'noise-2'
    noise['runs'][0]['status'] = 'completed'
    noise['artifacts'][0]['expired'] = True
    assert diff_count(diff_evidence(base, baseline, context_evidence(base, noise))) == 0

    cases = [
        ('branches', lambda x: x['branches'][0]['commit'].__setitem__('sha', 'c' * 40)),
        ('artifacts', lambda x: x['artifacts'][0].__setitem__('name', 'proof-changed')),
        ('issues', lambda x: x['issues'][0].__setitem__('body', 'changed')),
        ('runs', lambda x: x['runs'][0].__setitem__('head_sha', 'd' * 40)),
    ]
    observed: list[str] = []
    for surface, mutate in cases:
        changed = copy.deepcopy(context)
        mutate(changed)
        diff = diff_evidence(base, baseline, context_evidence(base, changed))
        assert diff_count(diff) == 1, (surface, diff)
        assert diff['changed'][0]['surface'] == surface, (surface, diff)
        observed.append(surface)

    multi = copy.deepcopy(context)
    multi['branches'][0]['commit']['sha'] = 'e' * 40
    multi['issues'][0]['body'] = 'changed-again'
    multi['artifacts'].append({'id': 202, 'name': 'new-proof', 'expired': False, 'workflow_run': {'id': 98}})
    multi_diff = diff_evidence(base, baseline, context_evidence(base, multi))
    assert diff_count(multi_diff) == 3, multi_diff

    self_context = copy.deepcopy(context)
    self_context['runs'].append({'id': 999, 'head_sha': 'f' * 40})
    self_context['artifacts'].append({'id': 9991, 'name': 'self', 'workflow_run': {'id': 999}})
    without_self = context_evidence(base, self_context, 999)
    assert without_self['contextSha256'] == baseline['contextSha256']

    return {
        'sameContextPass': True,
        'reviewedNoiseIgnored': ['nested pushed_at', 'MUTABLE_OPERATIONAL_KEYS', 'artifact expired'],
        'meaningfulSingleRowDriftCaught': observed,
        'multiRowDriftCount': diff_count(multi_diff),
        'currentRunSelfMetadataExcluded': True,
    }


def observe_batch(base: Any, repository: str, issue_number: int, token: str, current_run_id: int | None) -> dict[str, Any]:
    first_raw = base.collect(repository, issue_number, token)
    fence = base.build_snapshot_fence(first_raw, current_run_id)
    first = base.apply_snapshot_fence(first_raw, fence, current_run_id)
    second_raw = base.collect(repository, issue_number, token)
    second = base.apply_snapshot_fence(second_raw, fence, current_run_id)
    first_evidence = context_evidence(base, first, current_run_id)
    second_evidence = context_evidence(base, second, current_run_id)
    intra = diff_evidence(base, first_evidence, second_evidence)
    return {
        'stable': diff_count(intra) == 0,
        'stableContextSha256': second_evidence['contextSha256'],
        'snapshotFenceSha256': hashlib.sha256(_canonical_bytes(fence)).hexdigest(),
        'postFenceArrivalCounts': {
            surface: len(rows)
            for surface, rows in base.post_fence_rows(second_raw, fence, current_run_id).items()
        },
        'intraBatchDiff': intra,
        'evidence': second_evidence,
    }


def run_live(base: Any, repository: str, issue_number: int, token: str, current_run_id: int | None) -> tuple[int, dict[str, Any]]:
    batches = [observe_batch(base, repository, issue_number, token, current_run_id) for _ in range(3)]
    captured = batches[0]['evidence']
    cross = [
        {'fromBatch': 1, 'toBatch': index + 1, 'diff': diff_evidence(base, captured, batches[index]['evidence'])}
        for index in (1, 2)
    ]
    final_raw = base.collect(repository, issue_number, token)
    final_evidence = context_evidence(base, final_raw, current_run_id)
    final_diff = diff_evidence(base, captured, final_evidence)
    all_stable = all(batch['stable'] for batch in batches)
    common = all(diff_count(item['diff']) == 0 for item in cross)
    final_equal = diff_count(final_diff) == 0
    status = 'PASS_V5R2_DIAGNOSTIC_STABLE_NOT_AUTHORIZED' if all_stable and common and final_equal else 'FAIL_CLOSED_V5R2_DIAGNOSTIC_DRIFT_OBSERVED_NOT_AUTHORIZED'
    receipt = {
        'schema': SCHEMA,
        'status': status,
        'scienceAuthorized': False,
        'protectedAttemptAuthorized': False,
        'seedValuesPresent': False,
        'solverRuntimePresent': False,
        'normalization': {
            'preservedFromV5R1': True,
            'recursiveMutableOperationalKeysExcluded': sorted(base.MUTABLE_OPERATIONAL_KEYS),
            'nestedPushedAtExcluded': True,
            'artifactExpiredExcludedOnlyAtArtifactRow': True,
        },
        'batchCount': 3,
        'batches': batches,
        'crossBatchDiffs': cross,
        'finalLiveReenumeration': {
            'evidence': final_evidence,
            'diffFromCapturedBatch1': final_diff,
        },
        'allIntraBatchStable': all_stable,
        'crossBatchCommonContext': common,
        'finalLiveEqualsCapturedContext': final_equal,
    }
    return (0 if status.startswith('PASS_') else 3), receipt


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
    code, receipt = run_live(base, args.repository, args.issue_number, token, args.current_run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(receipt['status'])
    return code


if __name__ == '__main__':
    raise SystemExit(main())
