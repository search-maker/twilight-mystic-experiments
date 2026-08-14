#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AUTH_BRANCH = 'authorization/level-b-v2-densified58-fresh-validation-ordinal26-v1'
LOCK_BRANCH = 'allocation/level-b-v2-densified58-fresh-validation-ordinal26-v1'
DISPATCH_BRANCH = 'dispatch/level-b-v2-densified58-fresh-validation-ordinal26-v1'
ORDINAL_PREFIX = 'ALLOCATED-SCIENCE-IDENTITY | MYSTIC-STATE-0070 | ordinal=26 | '
SEED_SUFFIX = ' | seeds=2101000049-2101000072'


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def _flat_pages(value: Any, key: str | None = None) -> list[dict[str, Any]]:
    req(isinstance(value, list), 'paginated JSON array required')
    out: list[dict[str, Any]] = []
    for page in value:
        req(isinstance(page, (list, dict)), 'invalid page object')
        rows = page.get(key, []) if key is not None and isinstance(page, dict) else page
        req(isinstance(rows, list), 'page rows must be an array')
        out.extend(row for row in rows if isinstance(row, dict))
    return out


def exact_marker(auth_head: str) -> str:
    return f'{ORDINAL_PREFIX}authHead={auth_head}{SEED_SUFFIX}'


def validate_logical_markers(comments: list[dict[str, Any]], auth_head: str) -> dict[str, Any]:
    expected = exact_marker(auth_head)
    ordinal = [str(c.get('body') or '').strip() for c in comments if ORDINAL_PREFIX in str(c.get('body') or '')]
    req(len(ordinal) >= 1, 'ordinal26 allocation marker missing')
    distinct = sorted(set(ordinal))
    req(distinct == [expected], f'distinct ordinal26 allocation marker body detected: {distinct}')
    exact_count = sum(body == expected for body in ordinal)
    req(exact_count >= 1, 'exact ordinal26 allocation marker missing')
    return {'expectedMarkerBody': expected, 'exactMarkerCopies': exact_count, 'logicalAllocationIdentityCount': 1}


def validate_dispatch_state(branch_pages: Any, run_pages: Any, comment_pages: Any, auth_head: str, current_run_id: int) -> dict[str, Any]:
    branches = _flat_pages(branch_pages)
    runs = _flat_pages(run_pages, 'workflow_runs')
    comments = _flat_pages(comment_pages)

    by_name = {str(b.get('name') or ''): str((b.get('commit') or {}).get('sha') or '') for b in branches}
    req(by_name.get(AUTH_BRANCH) == auth_head, 'authorization branch/head drift')
    req(by_name.get(LOCK_BRANCH) == auth_head, 'atomic allocation lock missing or wrong head')
    req(by_name.get(DISPATCH_BRANCH) == auth_head, 'dispatch branch/head drift')

    for prefix, exact in (
        ('authorization/level-b-v2-densified58-fresh-validation-ordinal26-', AUTH_BRANCH),
        ('allocation/level-b-v2-densified58-fresh-validation-ordinal26-', LOCK_BRANCH),
        ('dispatch/level-b-v2-densified58-fresh-validation-ordinal26-', DISPATCH_BRANCH),
    ):
        aliases = [(name, sha) for name, sha in by_name.items() if name.startswith(prefix) and not (name == exact and sha == auth_head)]
        req(not aliases, f'competing ordinal26 ref detected: {aliases}')

    ordinal_dispatch_runs = [r for r in runs if r.get('event') == 'push' and str(r.get('head_branch') or '').startswith('dispatch/level-b-v2-densified58-fresh-validation-ordinal26-')]
    req(len(ordinal_dispatch_runs) == 1, f'expected exactly one ordinal26 dispatch push run, found {[(r.get("id"),r.get("head_branch"),r.get("head_sha")) for r in ordinal_dispatch_runs]}')
    current = ordinal_dispatch_runs[0]
    req(int(current.get('id') or 0) == int(current_run_id), 'dispatch push run is not current run')
    req(str(current.get('head_branch') or '') == DISPATCH_BRANCH and str(current.get('head_sha') or '') == auth_head, 'dispatch run identity drift')
    req(int(current.get('run_attempt') or 0) == 1, 'dispatch run attempt must be exactly 1')

    marker = validate_logical_markers(comments, auth_head)
    return {
        'status': 'PASS',
        'authorizationBranch': AUTH_BRANCH,
        'allocationLockBranch': LOCK_BRANCH,
        'dispatchBranch': DISPATCH_BRANCH,
        'authHead': auth_head,
        'currentRunId': int(current_run_id),
        **marker,
    }


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('markers')
    m.add_argument('--comments', type=Path, required=True)
    m.add_argument('--auth-head', required=True)
    d = sub.add_parser('dispatch')
    d.add_argument('--branches', type=Path, required=True)
    d.add_argument('--runs', type=Path, required=True)
    d.add_argument('--comments', type=Path, required=True)
    d.add_argument('--auth-head', required=True)
    d.add_argument('--current-run-id', type=int, required=True)
    args = ap.parse_args()
    try:
        if args.cmd == 'markers':
            result = validate_logical_markers(_flat_pages(load(args.comments)), args.auth_head)
        else:
            result = validate_dispatch_state(load(args.branches), load(args.runs), load(args.comments), args.auth_head, args.current_run_id)
        print(json.dumps({'status': 'PASS', **result}, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'REFUSED', 'reason': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
