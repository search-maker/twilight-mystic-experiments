from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

MUTABLE_STATUSES = ('in_progress', 'queued', 'requested', 'waiting', 'pending')
POSITIVE_TOKEN = 'PHYSICS_INDEPENDENT::EXEC005_V5R7_EXACT_BYTES_ACCEPTED_FOR_SINGLE_NON_SCIENCE_LIVE_CONTROL'
PREFIX = 'PHYSICS_INDEPENDENT::EXEC005_V5R7'
IDENTITY_FIELDS = ('branch', 'head', 'tree', 'artifact')
REJECTION_WORDS = ('REJECT', 'NONACCEPT', 'NOT_ACCEPTED', 'NOT ACCEPTED')


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


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def validate_unfiltered_pages(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, list) or not document:
        raise RuntimeError('Actions response must be a nonempty --paginate --slurp page list')
    rows: list[dict[str, Any]] = []
    totals: list[int] = []
    for index, page in enumerate(document, start=1):
        if not isinstance(page, dict):
            raise RuntimeError(f'Actions page {index} is not an object')
        total = page.get('total_count')
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise RuntimeError(f'Actions page {index} has malformed total_count')
        page_rows = page.get('workflow_runs')
        if not isinstance(page_rows, list):
            raise RuntimeError(f'Actions page {index} lacks workflow_runs list')
        if len(page_rows) > 100:
            raise RuntimeError(f'Actions page {index} exceeds per_page=100')
        totals.append(total)
        for row in page_rows:
            if not isinstance(row, dict):
                raise RuntimeError(f'Actions page {index} contains non-object row')
            _positive_int(row.get('id'), 'workflow-run id')
            if not isinstance(row.get('status'), str) or not row.get('status'):
                raise RuntimeError(f'workflow run {row.get("id")!r} has malformed status')
            rows.append(row)
    if len(set(totals)) != 1:
        raise RuntimeError(f'Actions total_count changed across pages totals={totals}')
    total = totals[0]
    if len(rows) != total:
        raise RuntimeError(f'Actions pagination count mismatch total_count={total} enumerated={len(rows)}')
    expected_pages = max(1, (total + 99) // 100)
    if len(document) != expected_pages:
        raise RuntimeError(f'Actions page-count mismatch expected={expected_pages} actual={len(document)}')
    ids = [_positive_int(row.get('id'), 'workflow-run id') for row in rows]
    if len(ids) != len(set(ids)):
        dup = sorted({rid for rid in ids if ids.count(rid) > 1})
        raise RuntimeError(f'Actions duplicate workflow-run ids across pages ids={dup}')
    if total and not document[-1].get('workflow_runs'):
        raise RuntimeError('nonzero Actions total_count with empty final page')
    return rows


def _project_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': _positive_int(row.get('id'), 'workflow-run id'),
        'status': row.get('status'),
        'conclusion': row.get('conclusion'),
        'run_attempt': row.get('run_attempt'),
        'head_sha': row.get('head_sha'),
        'head_branch': row.get('head_branch'),
        'path': row.get('path'),
        'event': row.get('event'),
    }


def mutable_inventory(document: Any, current_run_id: int) -> dict[str, Any]:
    current = _positive_int(current_run_id, 'current_run_id')
    rows = validate_unfiltered_pages(document)
    mutable_rows = [_project_run(row) for row in rows if row.get('status') in MUTABLE_STATUSES]
    self_rows = [row for row in mutable_rows if int(row['id']) == current]
    if len(self_rows) > 1:
        raise RuntimeError(f'current run {current} appeared more than once')
    blockers = [row for row in mutable_rows if int(row['id']) != current]
    blockers.sort(key=lambda row: int(row['id']))
    canonical = sorted(mutable_rows, key=lambda row: int(row['id']))
    return {
        'schema': 'LUNAR_EXEC005_V5R7_COMPLETE_UNFILTERED_ACTIONS_INVENTORY_V1',
        'completeUnfilteredPagination': True,
        'perPage': 100,
        'mutableStatuses': list(MUTABLE_STATUSES),
        'totalRunCount': len(rows),
        'mutableRunCount': len(mutable_rows),
        'currentRunId': current,
        'selfPresent': len(self_rows) == 1,
        'blockers': blockers,
        'blockerIds': [int(row['id']) for row in blockers],
        'canonicalMutableRows': canonical,
        'canonicalMutableSha256': hashlib.sha256(_canonical_bytes(canonical)).hexdigest(),
    }


def inventories_stable(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get('canonicalMutableSha256') == right.get('canonicalMutableSha256')
        and left.get('canonicalMutableRows') == right.get('canonicalMutableRows')
    )


def _first_line(body: str) -> str:
    lines = (body or '').splitlines()
    return lines[0].strip() if lines else ''


def _has_rejection(body: str) -> bool:
    upper = body.upper()
    return any(word in upper for word in REJECTION_WORDS)


def _parse_identity(body: str) -> tuple[dict[str, str], list[str]]:
    parsed: dict[str, list[str]] = {name: [] for name in IDENTITY_FIELDS}
    malformed_lines: list[str] = []
    pattern = re.compile(r'^(branch|head|tree|artifact)\s*[:=]\s*([^\s`]+)\s*$')
    for raw in (body or '').splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        match = pattern.fullmatch(line)
        if match:
            parsed[match.group(1)].append(match.group(2))
            continue
        lower = line.lower()
        if any(lower.startswith(name + '=') or lower.startswith(name + ':') for name in IDENTITY_FIELDS):
            malformed_lines.append(line)
    if malformed_lines:
        raise RuntimeError(f'malformed anchored Physics identity lines: {malformed_lines}')
    out: dict[str, str] = {}
    for name in IDENTITY_FIELDS:
        values = parsed[name]
        if len(values) != 1:
            raise RuntimeError(f'Physics identity field {name} cardinality={len(values)}')
        out[name] = values[0]
    return out, malformed_lines


def classify_physics(
    comments: list[dict[str, Any]],
    *,
    cutoff: int,
    head: str,
    tree: str,
    branch: str,
    artifact_id: int,
) -> dict[str, Any]:
    cutoff_i = _positive_int(cutoff, 'cutoff')
    artifact_i = _positive_int(artifact_id, 'artifact_id')
    expected = {'branch': branch, 'head': head, 'tree': tree, 'artifact': str(artifact_i)}
    positive_ids: list[int] = []
    rejection_ids: list[int] = []
    malformed_ids: list[int] = []
    ambiguous_ids: list[int] = []
    for row in comments:
        row_id = _positive_int(row.get('id'), 'Physics comment id')
        if row_id <= cutoff_i:
            continue
        body = str(row.get('body') or '')
        first = _first_line(body)
        if not first.startswith(PREFIX):
            continue
        if _has_rejection(body):
            rejection_ids.append(row_id)
            continue
        if first != POSITIVE_TOKEN:
            ambiguous_ids.append(row_id)
            continue
        try:
            parsed, _ = _parse_identity(body)
        except RuntimeError:
            malformed_ids.append(row_id)
            continue
        if parsed != expected:
            malformed_ids.append(row_id)
            continue
        positive_ids.append(row_id)
    authorized = (
        len(positive_ids) == 1
        and not rejection_ids
        and not malformed_ids
        and not ambiguous_ids
    )
    return {
        'schema': 'LUNAR_EXEC005_V5R7_EXACT_PHYSICS_BINDING_V1',
        'positiveToken': POSITIVE_TOKEN,
        'expectedIdentity': expected,
        'positiveCommentIds': sorted(positive_ids),
        'rejectionCommentIds': sorted(rejection_ids),
        'malformedCommentIds': sorted(malformed_ids),
        'ambiguousCommentIds': sorted(ambiguous_ids),
        'authorized': authorized,
    }


def _page(total: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {'total_count': total, 'workflow_runs': rows}


def _run(run_id: int, status: str, *, path: str = 'fixture', conclusion: Any = None) -> dict[str, Any]:
    return {
        'id': run_id,
        'status': status,
        'conclusion': conclusion,
        'run_attempt': 1,
        'head_sha': 'a' * 40,
        'head_branch': 'fixture',
        'path': path,
        'event': 'push',
    }


def self_test() -> dict[str, Any]:
    current = 999999
    completed = [_run(i + 1, 'completed', conclusion='success') for i in range(100)]
    sentinel = _run(1001, 'queued', path='page2-sentinel')
    pages = [_page(101, completed), _page(101, [sentinel])]
    inv = mutable_inventory(pages, current)
    page2 = inv['blockerIds'] == [1001]

    all_mutable_rows = [_run(2000 + i, status) for i, status in enumerate(MUTABLE_STATUSES)]
    all_mutable = mutable_inventory([_page(len(all_mutable_rows), all_mutable_rows)], current)
    all_statuses = {row['status'] for row in all_mutable['blockers']} == set(MUTABLE_STATUSES)

    self_row = _run(current, 'in_progress', path='self')
    other = _run(3001, 'waiting', path='other')
    self_inv = mutable_inventory([_page(2, [self_row, other])], current)
    self_exclusion = self_inv['blockerIds'] == [3001] and self_inv['selfPresent'] is True

    incomplete_fail = malformed_fail = count_fail = duplicate_fail = False
    try:
        validate_unfiltered_pages([_page(101, completed)])
    except RuntimeError:
        incomplete_fail = True
    try:
        validate_unfiltered_pages([{'total_count': 0}])
    except RuntimeError:
        malformed_fail = True
    try:
        validate_unfiltered_pages([_page(2, [_run(1, 'completed')])])
    except RuntimeError:
        count_fail = True
    try:
        validate_unfiltered_pages([_page(2, [_run(7, 'queued'), _run(7, 'in_progress')])])
    except RuntimeError:
        duplicate_fail = True

    q1 = mutable_inventory([_page(1, [_run(4001, 'queued')])], current)
    q2 = mutable_inventory([_page(1, [_run(4001, 'in_progress')])], current)
    queued_transition = q1['blockerIds'] == q2['blockerIds'] == [4001] and not inventories_stable(q1, q2)
    r1 = mutable_inventory([_page(1, [_run(4002, 'requested')])], current)
    r2 = mutable_inventory([_page(1, [_run(4002, 'queued')])], current)
    requested_transition = r1['blockerIds'] == r2['blockerIds'] == [4002] and not inventories_stable(r1, r2)

    head = '1' * 40
    tree = '2' * 40
    branch = 'review/v5r7'
    artifact = 123456
    identity = f'branch={branch}\nhead={head}\ntree={tree}\nartifact={artifact}'
    good_body = f'{POSITIVE_TOKEN}\n{identity}'
    good = classify_physics([{'id': 5001, 'body': good_body}], cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact)
    same_comment_reject = classify_physics(
        [{'id': 5001, 'body': good_body + '\nREJECTED because fixture'}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )
    duplicate_positive = classify_physics(
        [{'id': 5001, 'body': good_body}, {'id': 5002, 'body': good_body}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )
    duplicate_binding_body = f'{POSITIVE_TOKEN}\n{identity}\nhead={head}'
    duplicate_binding = classify_physics(
        [{'id': 5003, 'body': duplicate_binding_body}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )
    missing_binding_body = f'{POSITIVE_TOKEN}\nbranch={branch}\nhead={head}\ntree={tree}'
    missing_binding = classify_physics(
        [{'id': 5004, 'body': missing_binding_body}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )
    wrong_binding_body = f'{POSITIVE_TOKEN}\nbranch={branch}\nhead={"3"*40}\ntree={tree}\nartifact={artifact}'
    wrong_binding = classify_physics(
        [{'id': 5005, 'body': wrong_binding_body}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )
    quoted_context_body = f'{POSITIVE_TOKEN}\n> branch={branch}\n> head={head}\n> tree={tree}\n> artifact={artifact}'
    quoted_context = classify_physics(
        [{'id': 5006, 'body': quoted_context_body}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )
    legacy_alias = classify_physics(
        [{'id': 5007, 'body': f'{PREFIX}_EXACT_BYTE_ACCEPTED\n{identity}'}],
        cutoff=5000, head=head, tree=tree, branch=branch, artifact_id=artifact,
    )

    return {
        'schema': 'LUNAR_EXEC005_V5R7_CONTROL_GUARD_SELFTEST_V1',
        'completeUnfilteredPaginationPage2Blocker': page2,
        'allMutableStatusesLocallyFiltered': all_statuses,
        'exactSelfExclusion': self_exclusion,
        'incompletePaginationFailsClosed': incomplete_fail,
        'malformedPaginationFailsClosed': malformed_fail,
        'countMismatchFailsClosed': count_fail,
        'duplicatePageShiftFailsClosed': duplicate_fail,
        'queuedToInProgressRemainsBlockedAndUnstable': queued_transition,
        'requestedToQueuedRemainsBlockedAndUnstable': requested_transition,
        'exactPositivePhysicsTokenAccepted': good['authorized'] is True,
        'sameCommentRejectionPrecedenceFailsClosed': same_comment_reject['authorized'] is False,
        'duplicatePositiveFailsClosed': duplicate_positive['authorized'] is False,
        'duplicateIdentityBindingFailsClosed': duplicate_binding['authorized'] is False,
        'missingIdentityBindingFailsClosed': missing_binding['authorized'] is False,
        'wrongIdentityBindingFailsClosed': wrong_binding['authorized'] is False,
        'quotedContextOnlyBindingFailsClosed': quoted_context['authorized'] is False,
        'legacyAliasFailsClosed': legacy_alias['authorized'] is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--actions-pages', type=Path)
    parser.add_argument('--compare-actions-pages', type=Path)
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
        result = self_test()
        if not all(value is True for key, value in result.items() if key != 'schema'):
            raise RuntimeError(f'guard self-test failed: {result}')
        print(json.dumps(result, sort_keys=True))
        return 0

    if args.output is None:
        raise SystemExit('--output is required')

    if args.actions_pages is not None:
        if args.current_run_id is None:
            raise SystemExit('--current-run-id is required with --actions-pages')
        document = json.loads(args.actions_pages.read_text())
        result = mutable_inventory(document, args.current_run_id)
        if args.compare_actions_pages is not None:
            other = mutable_inventory(json.loads(args.compare_actions_pages.read_text()), args.current_run_id)
            result['stableAgainstComparison'] = inventories_stable(result, other)
            result['comparisonCanonicalMutableSha256'] = other['canonicalMutableSha256']
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
        result = classify_physics(
            comments,
            cutoff=args.cutoff,
            head=args.head,
            tree=args.tree,
            branch=args.branch,
            artifact_id=args.artifact_id,
        )
    else:
        raise SystemExit('select --self-test, --actions-pages, or --physics-comments')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
