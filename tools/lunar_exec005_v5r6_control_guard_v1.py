from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

MUTABLE_STATUSES = ('in_progress', 'queued', 'requested', 'waiting', 'pending')
POSITIVE_TOKEN = 'PHYSICS_INDEPENDENT::EXEC005_V5R6_EXACT_BYTES_ACCEPTED_FOR_SINGLE_NON_SCIENCE_LIVE_CONTROL'
PREFIX = 'PHYSICS_INDEPENDENT::EXEC005_V5R6'


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f'{label} must be a positive integer')
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f'{label} must be a positive integer') from exc
    if out <= 0:
        raise RuntimeError(f'{label} must be a positive integer')
    return out


def validate_status_pages(document: Any, expected_status: str) -> list[dict[str, Any]]:
    if expected_status not in MUTABLE_STATUSES:
        raise RuntimeError(f'unreviewed mutable status {expected_status!r}')
    if not isinstance(document, list) or not document:
        raise RuntimeError(f'{expected_status}: paginated response must be a nonempty slurped page list')
    rows: list[dict[str, Any]] = []
    totals: list[int] = []
    for index, page in enumerate(document, start=1):
        if not isinstance(page, dict):
            raise RuntimeError(f'{expected_status}: page {index} is not an object')
        total = page.get('total_count')
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise RuntimeError(f'{expected_status}: page {index} has malformed total_count')
        page_rows = page.get('workflow_runs')
        if not isinstance(page_rows, list):
            raise RuntimeError(f'{expected_status}: page {index} lacks workflow_runs list')
        if len(page_rows) > 100:
            raise RuntimeError(f'{expected_status}: page {index} exceeds per_page=100')
        totals.append(total)
        for row in page_rows:
            if not isinstance(row, dict):
                raise RuntimeError(f'{expected_status}: page {index} contains non-object row')
            if row.get('status') != expected_status:
                raise RuntimeError(f'{expected_status}: row status mismatch id={row.get("id")!r} status={row.get("status")!r}')
            _positive_int(row.get('id'), f'{expected_status}: row id')
            rows.append(row)
    if len(set(totals)) != 1:
        raise RuntimeError(f'{expected_status}: total_count changed across pagination pages totals={totals}')
    total = totals[0]
    if len(rows) != total:
        raise RuntimeError(f'{expected_status}: pagination count mismatch total_count={total} enumerated={len(rows)}')
    ids = [_positive_int(row.get('id'), f'{expected_status}: row id') for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f'{expected_status}: duplicate workflow-run ids within complete pagination')
    expected_pages = max(1, (total + 99) // 100)
    if len(document) != expected_pages:
        raise RuntimeError(f'{expected_status}: pagination page-count mismatch expected={expected_pages} actual={len(document)}')
    if total and len(document[-1].get('workflow_runs', [])) == 0:
        raise RuntimeError(f'{expected_status}: nonzero total_count with empty final page')
    return rows


def mutable_inventory(prefix: Path, current_run_id: int) -> dict[str, Any]:
    current = _positive_int(current_run_id, 'current_run_id')
    all_rows: list[dict[str, Any]] = []
    per_status: dict[str, int] = {}
    for status in MUTABLE_STATUSES:
        path = Path(f'{prefix}-{status}.json')
        if not path.is_file():
            raise RuntimeError(f'missing paginated status file {path}')
        rows = validate_status_pages(json.loads(path.read_text()), status)
        per_status[status] = len(rows)
        all_rows.extend(rows)
    seen: dict[int, str] = {}
    blockers: list[dict[str, Any]] = []
    self_rows: list[dict[str, Any]] = []
    for row in all_rows:
        run_id = _positive_int(row.get('id'), 'workflow-run id')
        status = str(row.get('status'))
        if run_id in seen:
            raise RuntimeError(f'workflow run {run_id} appeared in multiple mutable-status enumerations: {seen[run_id]} and {status}')
        seen[run_id] = status
        projected = {
            'id': run_id,
            'status': status,
            'path': row.get('path'),
            'head_sha': row.get('head_sha'),
            'head_branch': row.get('head_branch'),
            'event': row.get('event'),
            'run_attempt': row.get('run_attempt'),
        }
        if run_id == current:
            self_rows.append(projected)
        else:
            blockers.append(projected)
    if len(self_rows) > 1:
        raise RuntimeError(f'current run {current} appeared more than once in complete mutable inventory')
    blockers.sort(key=lambda row: (int(row['id']), str(row['status'])))
    return {
        'schema': 'LUNAR_EXEC005_V5R6_COMPLETE_MUTABLE_ACTION_INVENTORY_V1',
        'completePagination': True,
        'perPage': 100,
        'mutableStatuses': list(MUTABLE_STATUSES),
        'perStatusCounts': per_status,
        'enumeratedMutableCount': len(all_rows),
        'currentRunId': current,
        'selfExcluded': bool(self_rows),
        'blockers': blockers,
        'blockerIds': [int(row['id']) for row in blockers],
    }


def _first_line(body: str) -> str:
    lines = (body or '').splitlines()
    return lines[0].strip() if lines else ''


def classify_physics(comments: list[dict[str, Any]], *, cutoff: int, head: str, tree: str, branch: str, artifact_id: int) -> dict[str, Any]:
    cutoff_i = _positive_int(cutoff, 'cutoff')
    artifact_i = _positive_int(artifact_id, 'artifact_id')
    expected_terms = (head, tree, branch, str(artifact_i))
    relevant: list[dict[str, Any]] = []
    positive_rows: list[dict[str, Any]] = []
    malformed_positive: list[int] = []
    rejection_rows: list[int] = []
    ambiguous_rows: list[int] = []
    for row in comments:
        row_id = _positive_int(row.get('id'), 'Physics comment id')
        if row_id <= cutoff_i:
            continue
        body = str(row.get('body') or '')
        first = _first_line(body)
        if not first.startswith(PREFIX):
            continue
        relevant.append(row)
        upper = body.upper()
        if first == POSITIVE_TOKEN:
            if all(term in body for term in expected_terms):
                positive_rows.append(row)
            else:
                malformed_positive.append(row_id)
            continue
        if any(word in upper for word in ('REJECT', 'NONACCEPT', 'NOT_ACCEPTED', 'NOT ACCEPTED')):
            if any(term in body for term in (head, tree, branch, str(artifact_i))):
                rejection_rows.append(row_id)
            else:
                ambiguous_rows.append(row_id)
        else:
            ambiguous_rows.append(row_id)
    positive_ids = [int(row['id']) for row in positive_rows]
    authorized = len(positive_ids) == 1 and not malformed_positive and not rejection_rows and not ambiguous_rows
    return {
        'schema': 'LUNAR_EXEC005_V5R6_EXACT_PHYSICS_BINDING_V1',
        'positiveToken': POSITIVE_TOKEN,
        'head': head,
        'tree': tree,
        'branch': branch,
        'artifactId': artifact_i,
        'positiveCommentIds': positive_ids,
        'malformedPositiveCommentIds': sorted(malformed_positive),
        'rejectionCommentIds': sorted(rejection_rows),
        'ambiguousCommentIds': sorted(ambiguous_rows),
        'authorized': authorized,
    }


def _page(total: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {'total_count': total, 'workflow_runs': rows}


def self_test() -> dict[str, Any]:
    status_cases: dict[str, bool] = {}
    for status in MUTABLE_STATUSES:
        rows = [{'id': i + 1, 'status': status, 'path': f'{status}-{i}'} for i in range(101)]
        pages = [_page(101, rows[:100]), _page(101, rows[100:])]
        got = validate_status_pages(pages, status)
        status_cases[status] = len(got) == 101 and int(got[-1]['id']) == 101
    page2_status = 'in_progress'
    rows = [{'id': i + 10, 'status': page2_status, 'path': 'fixture'} for i in range(101)]
    page2 = validate_status_pages([_page(101, rows[:100]), _page(101, rows[100:])], page2_status)
    page2_blocker_seen = int(page2[-1]['id']) == 110

    current = 999
    tmp = Path('v5r6-guard-selftest')
    tmp.mkdir(exist_ok=True)
    for status in MUTABLE_STATUSES:
        fixture_rows: list[dict[str, Any]] = []
        if status == 'in_progress':
            fixture_rows = [
                {'id': current, 'status': status, 'path': 'self', 'head_sha': 'selfsha'},
                {'id': 1001, 'status': status, 'path': 'other', 'head_sha': 'othersha'},
            ]
        Path(f'{tmp}/inv-{status}.json').write_text(json.dumps([_page(len(fixture_rows), fixture_rows)]))
    inv = mutable_inventory(tmp / 'inv', current)
    self_exclusion = inv['blockerIds'] == [1001] and inv['selfExcluded'] is True

    incomplete_failed = False
    malformed_failed = False
    count_mismatch_failed = False
    try:
        validate_status_pages([_page(101, rows[:100])], page2_status)
    except RuntimeError:
        incomplete_failed = True
    try:
        validate_status_pages([{'total_count': 0}], 'queued')
    except RuntimeError:
        malformed_failed = True
    try:
        validate_status_pages([_page(2, [{'id': 1, 'status': 'waiting'}])], 'waiting')
    except RuntimeError:
        count_mismatch_failed = True

    head = 'a' * 40
    tree = 'b' * 40
    branch = 'review/v5r6'
    artifact = 123456
    good_body = f'{POSITIVE_TOKEN}\nhead={head}\ntree={tree}\nbranch={branch}\nartifact={artifact}'
    good = classify_physics([{'id': 200, 'body': good_body}], cutoff=100, head=head, tree=tree, branch=branch, artifact_id=artifact)
    duplicate = classify_physics([{'id': 200, 'body': good_body}, {'id': 201, 'body': good_body}], cutoff=100, head=head, tree=tree, branch=branch, artifact_id=artifact)
    rejected = classify_physics([{'id': 200, 'body': good_body}, {'id': 202, 'body': f'{PREFIX}_REJECTED\nhead={head}'}], cutoff=100, head=head, tree=tree, branch=branch, artifact_id=artifact)
    mismatch_body = f'{POSITIVE_TOKEN}\nhead={"c" * 40}\ntree={tree}\nbranch={branch}\nartifact={artifact}'
    mismatch = classify_physics([{'id': 203, 'body': mismatch_body}], cutoff=100, head=head, tree=tree, branch=branch, artifact_id=artifact)
    loose_alias = classify_physics([{'id': 204, 'body': f'{PREFIX}_EXACT_BYTE_ACCEPTED\nhead={head}\ntree={tree}\nbranch={branch}\nartifact={artifact}'}], cutoff=100, head=head, tree=tree, branch=branch, artifact_id=artifact)

    for path in tmp.glob('*'):
        path.unlink()
    tmp.rmdir()
    return {
        'schema': 'LUNAR_EXEC005_V5R6_CONTROL_GUARD_SELFTEST_V1',
        'allMutableStatusesPaginated': status_cases,
        'page2PlusBlockerEnumerated': page2_blocker_seen,
        'exactSelfExclusion': self_exclusion,
        'incompletePaginationFailsClosed': incomplete_failed,
        'malformedPaginationFailsClosed': malformed_failed,
        'countMismatchFailsClosed': count_mismatch_failed,
        'exactPositivePhysicsTokenAccepted': good['authorized'] is True,
        'duplicatePositivePhysicsFailsClosed': duplicate['authorized'] is False,
        'rejectionConflictFailsClosed': rejected['authorized'] is False,
        'identityMismatchFailsClosed': mismatch['authorized'] is False,
        'legacyLooseAliasNotAccepted': loose_alias['authorized'] is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--actions-prefix', type=Path)
    parser.add_argument('--current-run-id', type=int)
    parser.add_argument('--physics-comments', type=Path)
    parser.add_argument('--cutoff', type=int)
    parser.add_argument('--head')
    parser.add_argument('--tree')
    parser.add_argument('--branch')
    parser.add_argument('--artifact-id', type=int)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if args.output is None:
        raise SystemExit('--output is required')
    if args.actions_prefix is not None:
        if args.current_run_id is None:
            raise SystemExit('--current-run-id is required with --actions-prefix')
        result = mutable_inventory(args.actions_prefix, args.current_run_id)
    elif args.physics_comments is not None:
        required = (args.cutoff, args.head, args.tree, args.branch, args.artifact_id)
        if any(value is None for value in required):
            raise SystemExit('Physics classification requires cutoff/head/tree/branch/artifact-id')
        pages = json.loads(args.physics_comments.read_text())
        if not isinstance(pages, list) or not pages:
            raise RuntimeError('Physics comments must be complete --paginate --slurp page list')
        comments: list[dict[str, Any]] = []
        for index, page in enumerate(pages, start=1):
            if not isinstance(page, list):
                raise RuntimeError(f'Physics comment page {index} is not a list')
            comments.extend(page)
        result = classify_physics(comments, cutoff=args.cutoff, head=args.head, tree=args.tree, branch=args.branch, artifact_id=args.artifact_id)
    else:
        raise SystemExit('select --self-test, --actions-prefix, or --physics-comments')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
