from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path.cwd()
INFRA = Path(__file__).resolve().parents[2]
SUBJECT_PR = 1026
SUBJECT_HEAD = '5028cb7c7cd585d720749f0d572aa15e2f614bf9'
SUBJECT_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-child-v1-20260909'
CONTROL_HEAD = '1e55c28a38c016175ba8b350933730b615060e4f'
CONTROL_BRANCH = 'review/avps-v2-postconsumption-successor-authorization-control-replacement-v2-20260909'
MAIN = '8cd85cf393e2d86a1b6d7325654747460a13e697'
RBR = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v3-20260910'
STAGE = 'AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEW_GLOBAL_SCAN_REPLACEMENT_V3'
WF = '.github/workflows/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v3.yml'
SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v3/review_authorization.py'
ART = 'avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v3-proof'
STRESS_ART = 'avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v3-actual-stress-proof'
AUTH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v2/authorization.json'
AUTH_SHA = '442b76aee266baea248848a2a84ae017cac864fdde3aa8f6f119baef45660cc5'
AUTH_BLOB = '3dd0f80ff878d09987a91af0b4860a449fd41a92'
AB = 'authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal-46'
DB = 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal-46'
KEY = 'aerosol-vertical-profile-sensitivity-v2-postconsumption-successor:numerical:46'
CA = 10130865093
CR = 34419338768
CD = 'sha256:f83fd355a91fe86665b9df84e59d340412a8a009f1c19ce5c71a3a7fa8d23adf'
RR = '980cf9351040f1f5a91490e75f7d5e5a1cc522f915bb75727c833c2d3408efca'
RC = '614bbb1e9eaadd0782949895696d59734de8932b3af56c978ad122bea2f41567'
SSH = '6ace6be3b0298f3fa35cdc522a3375c0480a4154371c15bbbf4a3f930a5d17cd'
RSH = '30c0c1e38755f2c04b59448569c15c38a8b3b850c73d235ea38ce8f880d30f8b'
CTRL = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-authorization-control-v2/authorization_control.py'
CTRL_BLOB = 'a75611614de6b1ecafc216b2affa5bde639a5516'
WQ_PATH = 'scripts/avps_write_quiet_parser_v1.py'
WQ_BLOB = '7628651c9ddf740669d1fedf8fb18887d7155fe6'
ORDINAL45_CONSUMED_MARKER = 'ORDINAL45_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_CONSUMED'
GENERIC_WF = '.github/workflows/contract.yml'
LAUNCH_PREFIX = 'AVPS_V3_PROTECTED_LAUNCH | authorized=true | '
GRAPHQL_URL = 'https://api.github.com/graphql'
DISCUSSION_QUERY = '''query AVPSDiscussionInventory($owner: String!, $name: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    discussions(first: $first, after: $after) {
      nodes {
        id
        number
        updatedAt
        category { id }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}'''
FALSE_FLAGS = (
    'scientificOrdinalAllocated', 'ordinalReserved', 'authorizationRefCreated',
    'authorizationCreated', 'candidateSeedsAppliedToCases', 'seedUniverseConsumed',
    'dispatchCreated', 'publisherInvoked', 'scienceInvoked',
    'scientificExecutionAuthorized', 'solverExecutionAuthorized', 'scientificRuntime',
    'solverExecuted', 'protectedResultsOpened', 'levelBOpened', 'protectedHoldoutOpened',
    'newMappingOccurred', 'productionOccurred', 'taylorOrJerusalemUsed',
    'githubRerunAllowed', 'retryAllowed', 'resumeAllowed',
)


class Refusal(RuntimeError):
    pass


def req(value, message):
    if not value:
        raise Refusal(message)


def run(*args, cwd=ROOT, check=True):
    proc = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if check and proc.returncode:
        raise Refusal(f'command failed {args}: {proc.stdout}\n{proc.stderr}')
    return proc


def out(*args, cwd=ROOT):
    return run(*args, cwd=cwd).stdout.strip()


def blob(path: Path):
    body = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()


def canon(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def load(name, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec and spec.loader, f'cannot load {path}')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def ctrl():
    path = ROOT / CTRL
    req(blob(path) == CTRL_BLOB, 'Control-V2 wrapper byte drift')
    return load('avps46_review_ctrl_v3', path)


def canonical_wq_module():
    path = ROOT / WQ_PATH
    req(path.is_file(), 'canonical WQ parser missing from frozen subject')
    req(blob(path) == WQ_BLOB, 'canonical WQ parser byte drift')
    mod = load('avps46_subject_wq_parser_v1', path)
    req(Path(mod.__file__).resolve() == path.resolve(), 'canonical WQ parser not subject-bound')
    req(hasattr(mod, 'is_write_quiet_begin') and hasattr(mod, 'record_write_quiet_end'), 'canonical WQ parser API drift')
    return mod


def parse_wq_rows(rows):
    mod = canonical_wq_module()
    begins = {}
    seen = set()
    closed = set()
    for row in rows:
        body = str(row.get('body') or '')
        if mod.record_write_quiet_end(body, int(row['id']), seen, closed):
            continue
        if mod.is_write_quiet_begin(body):
            seen.add(int(row['id']))
            begins[int(row['id'])] = row
    return begins, seen, closed


def wq(c, repo, tok, rh, rpr, expect=None):
    rows = c.core.pages(c.core.repo_url(repo, 'issues/60/comments'), tok)
    begins, seen, closed = parse_wq_rows(rows)
    unmatched = sorted(x for x in seen if x not in closed)
    req(len(unmatched) == 1, f'expected own WQ only, got {unmatched}')
    begin_id = unmatched[0]
    if expect is not None:
        req(begin_id == expect, 'WQ begin changed')
    first = str(begins[begin_id].get('body') or '').splitlines()[0].strip()
    req(first.startswith(f'WRITE_QUIET_BEGIN | {STAGE} |'), 'wrong WQ stage')
    for field in (
        f'branch={RBR}', f'head={rh}', f'base={SUBJECT_HEAD}', f'subject_pr={SUBJECT_PR}',
        f'subject_head={SUBJECT_HEAD}', f'control_parent={CONTROL_HEAD}',
    ):
        req(field in first, f'WQ missing {field}')
    return {'begin': begin_id, 'count': len(rows), 'tail': max(int(r['id']) for r in rows), 'canonicalParserBlob': WQ_BLOB}


def wq_absent(c, repo, tok):
    rows = c.core.pages(c.core.repo_url(repo, 'issues/60/comments'), tok)
    _, seen, closed = parse_wq_rows(rows)
    unmatched = sorted(x for x in seen if x not in closed)
    req(not unmatched, f'ACTUAL stress requires no unmatched WQ, got {unmatched}')
    return {'unmatched': [], 'count': len(rows), 'tail': max(int(r['id']) for r in rows), 'canonicalParserBlob': WQ_BLOB}


def mutable(c, repo, tok, status):
    rows = []
    total = None
    page = 1
    while True:
        payload = c.core.req_json(c.core.repo_url(repo, f'actions/runs?status={status}&per_page=100&page={page}'), tok)
        req(isinstance(payload, dict) and isinstance(payload.get('workflow_runs'), list), f'bad Actions {status} payload')
        count = int(payload.get('total_count') or 0)
        total = count if total is None else total
        req(count == total, f'Actions {status} count changed during pagination')
        batch = list(payload['workflow_runs'])
        rows += batch
        if len(batch) < 100:
            break
        page += 1
        req(page < 1000, 'Actions pagination runaway')
    req(len(rows) == total and len({int(r.get('id') or 0) for r in rows}) == len(rows), f'Actions {status} pagination/ID mismatch')
    return rows


def quiesce(c, a):
    statuses = ('in_progress', 'queued', 'waiting', 'requested', 'pending')
    for _ in range(90):
        blockers = []
        counts = {}
        for status in statuses:
            rows = mutable(c, a.repo, a.tok, status)
            counts[status] = len(rows)
            blockers += [r for r in rows if int(r.get('id') or 0) != a.run]
        if not blockers:
            time.sleep(20)
            final = {}
            blockers = []
            for status in statuses:
                rows = mutable(c, a.repo, a.tok, status)
                final[status] = len(rows)
                blockers += [r for r in rows if int(r.get('id') or 0) != a.run]
            req(not blockers, f'Actions resumed before scan {[r.get("id") for r in blockers]}')
            return {'allPages': True, 'initial': counts, 'final': final}
        time.sleep(10)
    raise Refusal('Actions never quiescent')


def static_common(c, a, expected_action):
    req(ROOT.resolve() != INFRA.resolve(), 'subject/reviewer checkouts must be distinct')
    req(a.event == 'pull_request' and a.action == expected_action and a.attempt == 1, 'wrong event/action/attempt')
    req(a.rb == RBR and a.base == SUBJECT_HEAD and a.bb == SUBJECT_BRANCH, 'review carrier identity drift')
    req(out('git', 'rev-parse', 'HEAD') == SUBJECT_HEAD, 'subject checkout drift')
    req(out('git', 'rev-parse', f'HEAD:{AUTH}') == AUTH_BLOB, 'authorization blob drift')
    req(hashlib.sha256((ROOT / AUTH).read_bytes()).hexdigest() == AUTH_SHA, 'authorization raw-byte drift')
    req(out('git', 'rev-parse', 'HEAD', cwd=INFRA) == a.rh, 'reviewer checkout drift')
    req(not out('git', 'rev-list', '--merges', f'{SUBJECT_HEAD}..{a.rh}', cwd=INFRA), 'reviewer merge found')
    local_tree = out('git', 'rev-parse', 'HEAD^{tree}', cwd=INFRA)
    api_commit = c.core.req_json(c.core.repo_url(a.repo, f'git/commits/{a.rh}'), a.tok)
    req(str((api_commit.get('tree') or {}).get('sha') or '') == local_tree, 'reviewer tree API/local drift')
    paths = sorted(x for x in out('git', 'diff', '--name-only', f'{SUBJECT_HEAD}...{a.rh}', cwd=INFRA).splitlines() if x)
    req(paths == sorted([WF, SCRIPT]), f'reviewer changed paths {paths}')
    req(c.core.branch_head(a.repo, 'main', a.tok) == MAIN, 'main drift')
    req(c.core.branch_head(a.repo, SUBJECT_BRANCH, a.tok) == SUBJECT_HEAD, 'subject branch drift')
    req(c.core.branch_head(a.repo, CONTROL_BRANCH, a.tok) == CONTROL_HEAD, 'control branch drift')
    req(c.core.branch_head(a.repo, RBR, a.tok) == a.rh, 'reviewer branch drift')
    subject_pr = c.core.current_pr(a.repo, SUBJECT_PR, a.tok)
    req(subject_pr.get('state') == 'open' and subject_pr.get('draft') is True and subject_pr.get('merged_at') is None, 'PR1026 state drift')
    req(subject_pr['head']['sha'] == SUBJECT_HEAD and subject_pr['base']['sha'] == CONTROL_HEAD, 'PR1026 head/base drift')
    req(int(subject_pr.get('commits') or 0) == 1 and int(subject_pr.get('changed_files') or 0) == 1, 'PR1026 scope drift')
    reviewer_pr = c.core.current_pr(a.repo, a.rpr, a.tok)
    req(reviewer_pr.get('state') == 'open' and reviewer_pr.get('draft') is True and reviewer_pr.get('merged_at') is None, 'reviewer PR state drift')
    req(reviewer_pr['head']['sha'] == a.rh and reviewer_pr['head']['ref'] == RBR, 'reviewer PR head drift')
    req(reviewer_pr['base']['sha'] == SUBJECT_HEAD and reviewer_pr['base']['ref'] == SUBJECT_BRANCH, 'reviewer PR base drift')
    self_run = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{a.run}'), a.tok)
    req(self_run.get('event') == 'pull_request' and int(self_run.get('run_attempt') or 0) == 1, 'self-run event/attempt drift')
    req(self_run.get('head_sha') == a.rh and self_run.get('head_branch') == RBR and self_run.get('path') == WF, 'self-run registration drift')
    req(shutil.which('uvspec') is None, 'uvspec present in zero-runtime review')
    mod = canonical_wq_module()
    req(Path(mod.__file__).resolve() == (ROOT / WQ_PATH).resolve(), 'subject-bound WQ parser import-root proof failed')
    return paths, local_tree, reviewer_pr


def control_artifact(c, a, subject):
    run_row = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{CR}'), a.tok)
    req(run_row.get('status') == 'completed' and run_row.get('conclusion') == 'success', 'Control-V2 run status drift')
    req(int(run_row.get('run_attempt') or 0) == 1 and run_row.get('head_sha') == CONTROL_HEAD, 'Control-V2 run identity drift')
    payload = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{CR}/artifacts?per_page=100'), a.tok)
    matches = [x for x in payload.get('artifacts', []) if int(x.get('id') or 0) == CA]
    req(len(matches) == 1 and matches[0].get('name') == 'vertical-profile-v2-postconsumption-successor-authorization-control-v2-proof', 'Control-V2 artifact identity drift')
    req(matches[0].get('digest') == CD and matches[0].get('expired') is False, 'Control-V2 artifact digest/expiry drift')
    raw = c.safe_request_bytes(c.core.repo_url(a.repo, f'actions/artifacts/{CA}/zip'), a.tok)
    req('sha256:' + hashlib.sha256(raw).hexdigest() == CD, 'Control-V2 ZIP digest drift')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        req(len(names) == 27 and 'authorization-proposal.json' in names and 'authorization-control-receipt.json' in names, 'Control-V2 ZIP layout drift')
        proposal = archive.read('authorization-proposal.json')
        receipt_raw = archive.read('authorization-control-receipt.json')
    req(hashlib.sha256(proposal).hexdigest() == AUTH_SHA and proposal == subject, 'proposal/PR1026 byte mismatch')
    req(hashlib.sha256(receipt_raw).hexdigest() == RR, 'Control-V2 receipt raw SHA drift')
    receipt = json.loads(receipt_raw)
    saved = receipt.get('receiptSha256')
    check = dict(receipt)
    check.pop('receiptSha256', None)
    req(saved == RC and canon(check) == RC, 'corrected Control-V2 receipt self-hash drift')
    req(receipt.get('status') == 'PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_CONTROL_PROPOSAL_ONLY_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED', 'Control-V2 receipt status drift')
    req(receipt.get('controlHead') == CONTROL_HEAD and receipt.get('controlRunId') == CR, 'Control-V2 receipt identity drift')
    return receipt


def graphql_payload(tok, owner, name, cursor):
    body = json.dumps({'query': DISCUSSION_QUERY, 'variables': {'owner': owner, 'name': name, 'first': 100, 'after': cursor}}, separators=(',', ':')).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        method='POST',
        headers={
            'Authorization': f'Bearer {tok}',
            'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json',
            'User-Agent': 'avps-v3-result-blind-discussion-inventory',
            'X-GitHub-Api-Version': '2022-11-28',
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise Refusal(f'GraphQL HTTP {exc.code}: {raw.decode("utf-8", "replace")[:2000]}') from None
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise Refusal(f'GraphQL malformed JSON response: {type(exc).__name__}') from None
    req(isinstance(value, dict), 'GraphQL top-level response is not an object')
    return value


def graphql_errors(payload):
    rows = payload.get('errors') or []
    req(isinstance(rows, list), 'GraphQL errors member malformed')
    messages = []
    for row in rows:
        if isinstance(row, dict):
            messages.append(str(row.get('message') or '<missing-message>'))
        else:
            messages.append(str(row))
    return tuple(messages)


def normalize_discussion_node(node):
    req(isinstance(node, dict), 'discussion node malformed')
    did = node.get('id')
    number = node.get('number')
    updated = node.get('updatedAt')
    category = node.get('category')
    req(isinstance(did, str) and did, 'discussion id missing')
    req(isinstance(number, int) and number > 0, 'discussion number missing')
    req(isinstance(updated, str) and updated, 'discussion updatedAt missing')
    req(isinstance(category, dict), 'discussion nested category missing')
    category_id = category.get('id')
    req(isinstance(category_id, str) and category_id, 'discussion nested category.id missing')
    return {'id': did, 'number': number, 'updatedAt': updated, 'categoryId': category_id}


def parse_discussion_page(payload):
    errors = graphql_errors(payload)
    if errors:
        raise Refusal('discussionsGraphqlErrors=' + repr(errors))
    data = payload.get('data')
    req(isinstance(data, dict), 'GraphQL data missing')
    repository = data.get('repository')
    req(isinstance(repository, dict), 'GraphQL repository missing/null')
    discussions = repository.get('discussions')
    req(isinstance(discussions, dict), 'GraphQL discussions missing/null')
    nodes = discussions.get('nodes')
    page_info = discussions.get('pageInfo')
    req(isinstance(nodes, list), 'GraphQL discussions.nodes malformed')
    req(isinstance(page_info, dict), 'GraphQL discussions.pageInfo malformed')
    normalized = [normalize_discussion_node(node) for node in nodes if node is not None]
    has_next = page_info.get('hasNextPage')
    cursor = page_info.get('endCursor')
    req(isinstance(has_next, bool), 'GraphQL pageInfo.hasNextPage malformed')
    if has_next:
        req(isinstance(cursor, str) and cursor, 'GraphQL pagination cursor missing')
    elif cursor is not None:
        req(isinstance(cursor, str), 'GraphQL terminal cursor malformed')
    return normalized, has_next, cursor


def collect_discussions(repo, tok, transport=graphql_payload):
    owner, name = repo.split('/', 1)
    rows = []
    cursor = None
    seen_cursors = set()
    pages = 0
    while True:
        payload = transport(tok, owner, name, cursor)
        batch, has_next, next_cursor = parse_discussion_page(payload)
        rows.extend(batch)
        pages += 1
        req(pages < 10000, 'discussion pagination runaway')
        if not has_next:
            break
        req(next_cursor not in seen_cursors, 'discussion pagination cursor repeated')
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    rows.sort(key=lambda row: (row['number'], row['id']))
    req(len({row['id'] for row in rows}) == len(rows), 'duplicate discussion node ids')
    req(len({row['number'] for row in rows}) == len(rows), 'duplicate discussion numbers')
    return {
        'surface': 'discussions',
        'allPages': True,
        'pageCount': pages,
        'count': len(rows),
        'rows': rows,
        'discussionsGraphqlErrors': [],
        'canonicalSha256': canon(rows),
        'categoryIdentityField': 'categoryId',
        'categorySourceSelection': 'category { id }',
    }


def discussion_fixtures():
    req('category { id }' in ' '.join(DISCUSSION_QUERY.split()), 'current nested category query absent')
    req('categoryId' not in DISCUSSION_QUERY, 'obsolete Discussion.categoryId field selected')
    valid_a = {'id': 'D_2', 'number': 2, 'updatedAt': '2026-09-10T00:00:00Z', 'category': {'id': 'C_2'}}
    valid_b = {'id': 'D_1', 'number': 1, 'updatedAt': '2026-09-09T00:00:00Z', 'category': {'id': 'C_1'}}
    empty = {'data': {'repository': {'discussions': {'nodes': [], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}}
    rows, more, cursor = parse_discussion_page(empty)
    req(rows == [] and more is False and cursor is None, 'empty discussion fixture failed')
    null_node = {'data': {'repository': {'discussions': {'nodes': [None, valid_a], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}}
    rows, _, _ = parse_discussion_page(null_node)
    req(rows == [{'id': 'D_2', 'number': 2, 'updatedAt': '2026-09-10T00:00:00Z', 'categoryId': 'C_2'}], 'null-node/category normalization fixture failed')
    pages = {
        None: {'data': {'repository': {'discussions': {'nodes': [valid_a], 'pageInfo': {'hasNextPage': True, 'endCursor': 'NEXT'}}}}},
        'NEXT': {'data': {'repository': {'discussions': {'nodes': [valid_b], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}},
    }
    calls = []
    def fake(tok, owner, name, cursor):
        calls.append(cursor)
        return pages[cursor]
    inventory = collect_discussions('search-maker/twilight-mystic-experiments', 'fixture-token', fake)
    req(calls == [None, 'NEXT'] and [row['number'] for row in inventory['rows']] == [1, 2], 'discussion pagination fixture failed')
    req(inventory['rows'][0]['categoryId'] == 'C_1' and 'category' not in inventory['rows'][0], 'stable categoryId normalization failed')
    req(inventory['canonicalSha256'] == canon(inventory['rows']), 'discussion stable canonicalization failed')
    errors_payload = {'errors': [{'message': "Field 'categoryId' doesn't exist on type 'Discussion'"}, {'message': 'Second schema error'}]}
    req(graphql_errors(errors_payload) == ("Field 'categoryId' doesn't exist on type 'Discussion'", 'Second schema error'), 'all GraphQL errors fixture failed')
    malformed_cases = [
        {'data': {'repository': None}},
        {'data': {'repository': {'discussions': None}}},
        {'data': {'repository': {'discussions': {'nodes': {}, 'pageInfo': {}}}}},
        {'data': {'repository': {'discussions': {'nodes': [{'id': 'D', 'number': 1, 'updatedAt': 'x', 'categoryId': 'obsolete'}], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}},
    ]
    refused = 0
    for case in malformed_cases:
        try:
            parse_discussion_page(case)
        except Refusal:
            refused += 1
    req(refused == len(malformed_cases), 'malformed/obsolete discussion response fixture failed')
    return {'pagination': True, 'nullNode': True, 'empty': True, 'canonicalization': True, 'categoryIdNormalization': True, 'malformedRefusal': True, 'allGraphqlErrorsCollected': True}


def selfobs(row, payload, rpr, rh):
    if int(row.get('ordinal') or -1) != 46:
        return False
    surface = str(row.get('surface') or '')
    identity = str(row.get('id') or '')
    if surface == 'branch' and identity in (SUBJECT_BRANCH, RBR):
        return True
    if surface in ('pull-request', 'pull-request-prose') and identity in (str(SUBJECT_PR), str(rpr)):
        return True
    if surface == 'workflow-run':
        for run_row in payload.get('runs', []):
            if str(run_row.get('id') or '') == identity and (
                (run_row.get('head_branch') == SUBJECT_BRANCH and run_row.get('head_sha') == SUBJECT_HEAD)
                or (run_row.get('head_branch') == RBR and run_row.get('head_sha') == rh)
            ):
                return True
    return False


def frozen_semantics(c, a, subject, evidence_dir, include_global_scan=True):
    source_api = c.core.verify_source_api(a.repo, a.tok)
    source, h42, tmp = c.core.source_worktree(a.repo)
    try:
        c.core.verify_source_code(source)
        scanner_wrapper, ledger_module = c.core.load_source_modules(source, h42)
        scanner = scanner_wrapper.mod
        c.core.require_bound_scanner_mode(scanner)
        scanner.REVIEW_PROOF_ARTIFACT_NAME = ART
        ledger = c.core.validate_source_ledger(ledger_module, h42)
        req(ledger['candidateSeedCanonicalSha256'] == SSH and ledger['candidateRowsCanonicalSha256'] == RSH, 'fresh ledger drift')
        tracked = c.core.tracked_tree_scan(evidence_dir, ledger)
        seeds = {int(value) for value in ledger['candidateSeeds']}
        req(len(seeds) == 72, 'seed cardinality drift')
        rep = None
        if include_global_scan:
            ctx, stable, fence, post = scanner.collect_stable(a.repo, 60, a.tok, a.run, seeds, 'authorization-recheck')
            rep = scanner.evaluate_context(
                ctx, seeds, a.run,
                stable_double_enumeration_passed=True,
                stable_context_sha256_value=stable,
                audit_mode='authorization-recheck',
                expected_branch_name=RBR,
                expected_repo_head=a.rh,
                snapshot_fence=fence,
                post_fence_arrival_counts=post,
            )
            for key, value in {
                'candidateSeedCount': 72,
                'repositoryGlobalCollisionCount': 0,
                'repositoryGlobalCollisionSurfaceScanPassed': True,
                'repositoryGlobalDoubleEnumerationStable': True,
                'repositoryGlobalEnumerationPassCount': 2,
                'auditedBranchHeadMatchesRepositoryHead': True,
                'repositoryGlobalPostFenceCandidateSeedCollisionCount': 0,
                'allStatePullRequestsInspected': True,
                'allStateIssuesInspected': True,
                'allRepositoryIssueCommentsInspected': True,
                'allRepositoryPullReviewCommentsInspected': True,
                'allRepositoryCommitCommentsInspected': True,
            }.items():
                req(rep.get(key) == value, f'global scan drift {key}={rep.get(key)!r}')
            req(not scanner.final_review_proof_artifacts(a.repo, a.tok, a.run), 'prior review-proof artifact identity exists')
    finally:
        c.core.cleanup_worktrees(source, h42, tmp)
    consumed45 = c.core.verify_consumed45(a.repo, a.tok)
    preauth = c.core.load('avps46_review_surface_v3', ROOT / c.core.PREAUTH_SURFACE_PATH)
    payload = preauth.collect(a.repo, a.tok)
    latest = preauth.latest_consumed_or_dispatched_ordinal(payload)
    req(latest == 45, f'latest consumed/dispatched={latest}')
    _, _, ordinal_module = preauth._modules()
    observations = ordinal_module.authoritative_global_ordinal_observations(payload, current_run_id=a.run)
    nonself = [row for row in observations if not selfobs(row, payload, a.rpr, a.rh)]
    req(nonself and max(int(row['ordinal']) for row in nonself) == 45, 'non-self global ordinal max drift')
    req(not [row for row in nonself if int(row['ordinal']) == 46], 'non-self ordinal46 occupancy')
    consumed = {int(row['ordinal']) for row in nonself if row.get('reason') == 'exact-consumed-marker'}
    req({41, 42, 43, 44, 45}.issubset(consumed), f'consumed markers incomplete {sorted(consumed)}')
    auth = json.loads(subject)
    branches = {str(row.get('name') or '') for row in payload.get('branches', [])}
    req(AB not in branches and DB not in branches, 'live ordinal46 auth/dispatch ref exists')
    comments = [str(row.get('body') or '').strip() for row in payload.get('issue60Comments', [])]
    req(sum(1 for row in comments if row == ORDINAL45_CONSUMED_MARKER) == 1, 'ordinal45 consumed marker count drift')
    req(not any(row.upper().startswith('ORDINAL46_') for row in comments), 'ordinal46 allocation/consumed marker exists')
    proposed_paths = {auth['proposedPublisherWorkflowPath'], auth['proposedScienceWorkflowPath']}
    req(not any(str(row.get('path') or '') in proposed_paths for row in payload.get('runs', [])), 'ordinal46 proposed publisher/science run exists')
    freshness, _, _ = preauth._modules()
    key_scan = c.proposal_aware_execution_key_scan(payload, KEY, 46, freshness.positive_candidate_claims, current_pr=SUBJECT_PR, current_run_id=a.run)
    req(key_scan['authoritativeExecutionKeyUseCount'] == 0, f'authoritative execution-key use {key_scan["authoritativeExecutionKeyUseRows"]}')
    grep = run('git', 'grep', '-n', '-F', KEY, check=False)
    lines = [line for line in grep.stdout.splitlines() if line]
    req(grep.returncode == 0 and len(lines) == 1 and lines[0].startswith(AUTH + ':'), 'tracked execution-key occurrence not self-only')
    req(auth['scientificOrdinal'] == 46 and auth['latestPriorConsumedOrDispatchedScientificOrdinal'] == 45, 'PR1026 ordinal semantics drift')
    req(auth['authorizationBranch'] == AB and auth['dispatchBranch'] == DB and auth['executionKey'] == KEY, 'PR1026 identity semantics drift')
    req(auth['candidateSeedCount'] == 72 and auth['candidateSeedCanonicalSha256'] == SSH and auth['candidateRowsCanonicalSha256'] == RSH, 'PR1026 seed semantics drift')
    req(all(auth.get(key) is False for key in FALSE_FLAGS), 'PR1026 frozen false boundary drift')
    installed = c.core.verify_installed_blobs(source_api['identity'])
    return {
        'sourceApi': source_api,
        'tracked': tracked,
        'repositoryGlobal': rep,
        'consumed45': consumed45,
        'payload': payload,
        'latest': latest,
        'observations': observations,
        'keyScan': key_scan,
        'installed': installed,
    }


def verify_launch_binding(c, a, reviewer_pr):
    body = str(reviewer_pr.get('body') or '')
    lines = [line.strip() for line in body.splitlines() if line.strip().startswith(LAUNCH_PREFIX)]
    req(len(lines) == 1, 'missing/duplicate protected launch binding')
    fields = {}
    for token in lines[0][len(LAUNCH_PREFIX):].split(' | '):
        req('=' in token, 'malformed protected launch token')
        key, value = token.split('=', 1)
        req(key not in fields and value, 'duplicate/empty protected launch token')
        fields[key] = value
    req(set(fields) == {'head', 'generic_run', 'stress_run', 'wq_begin'}, f'protected launch fields drift {sorted(fields)}')
    req(fields['head'] == a.rh, 'protected launch head drift')
    generic_run = int(fields['generic_run'])
    stress_run = int(fields['stress_run'])
    wq_begin = int(fields['wq_begin'])
    req(generic_run > 0 and stress_run > 0 and wq_begin > 0, 'protected launch numeric binding invalid')
    generic = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{generic_run}'), a.tok)
    req(generic.get('status') == 'completed' and generic.get('conclusion') == 'success', 'generic prelaunch run not successful')
    req(int(generic.get('run_attempt') or 0) == 1 and generic.get('head_sha') == a.rh and generic.get('path') == GENERIC_WF, 'generic prelaunch identity drift')
    stress = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{stress_run}'), a.tok)
    req(stress.get('status') == 'completed' and stress.get('conclusion') == 'success', 'ACTUAL stress prelaunch run not successful')
    req(int(stress.get('run_attempt') or 0) == 1 and stress.get('head_sha') == a.rh and stress.get('path') == WF and stress.get('event') == 'pull_request', 'ACTUAL stress identity drift')
    artifacts = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{stress_run}/artifacts?per_page=100'), a.tok)
    matches = [row for row in artifacts.get('artifacts', []) if row.get('name') == STRESS_ART and row.get('expired') is False]
    req(len(matches) == 1, 'ACTUAL stress immutable proof artifact missing/duplicate')
    raw = c.safe_request_bytes(c.core.repo_url(a.repo, f'actions/artifacts/{int(matches[0]["id"])}/zip'), a.tok)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        req('actual-stress-receipt.json' in archive.namelist(), 'ACTUAL stress receipt absent')
        receipt = json.loads(archive.read('actual-stress-receipt.json'))
    req(receipt.get('status') == 'PASS_NONAUTHORIZING_ACTUAL_V3_EXACT_EXECUTABLE_STRESS', 'ACTUAL stress receipt status drift')
    req(receipt.get('reviewerHead') == a.rh and receipt.get('stressRunId') == stress_run and receipt.get('reviewRunAttempt') == 1, 'ACTUAL stress receipt identity drift')
    req(receipt.get('subjectAuthorizationHead') == SUBJECT_HEAD and receipt.get('canonicalWqParserBlob') == WQ_BLOB, 'ACTUAL stress subject/WQ binding drift')
    req(receipt.get('discussionLiveSchemaPassed') is True and receipt.get('discussionFixtureSuitePassed') is True, 'ACTUAL stress discussion proof drift')
    return {'genericRun': generic_run, 'stressRun': stress_run, 'wqBegin': wq_begin, 'stressArtifactId': int(matches[0]['id'])}


def stress(a):
    req(not out('git', 'status', '--porcelain', '--untracked-files=no'), 'tracked subject workspace dirty')
    req(not out('git', 'status', '--porcelain'), 'subject workspace dirty')
    req(not out('git', 'status', '--porcelain', cwd=INFRA), 'reviewer workspace dirty')
    c = ctrl()
    a.ev.mkdir(parents=True, exist_ok=False)
    paths, reviewer_tree, _ = static_common(c, a, 'opened')
    pre_wq = wq_absent(c, a.repo, a.tok)
    subject = (ROOT / AUTH).read_bytes()
    control_receipt = control_artifact(c, a, subject)
    fixtures = discussion_fixtures()
    live1 = collect_discussions(a.repo, a.tok)
    live2 = collect_discussions(a.repo, a.tok)
    req(live1['canonicalSha256'] == live2['canonicalSha256'] and live1['count'] == live2['count'], 'live Discussions surface unstable across two passes')
    frozen = frozen_semantics(c, a, subject, a.ev, include_global_scan=True)
    post_wq = wq_absent(c, a.repo, a.tok)
    req(post_wq['tail'] == pre_wq['tail'], '#60 tail changed during ACTUAL stress')
    req(c.core.branch_head(a.repo, 'main', a.tok) == MAIN and c.core.branch_head(a.repo, RBR, a.tok) == a.rh, 'final ACTUAL main/reviewer branch drift')
    req(not out('git', 'status', '--porcelain', '--untracked-files=no'), 'tracked subject workspace became dirty')
    req(not out('git', 'status', '--porcelain', cwd=INFRA), 'reviewer workspace became dirty')
    write(a.ev / 'discussion-fixtures.json', fixtures)
    write(a.ev / 'discussion-live-inventory.json', live2)
    write(a.ev / 'repository-global-seed-recheck.json', frozen['repositoryGlobal'])
    write(a.ev / 'global-ordinal-observations.json', frozen['observations'])
    write(a.ev / 'proposal-aware-execution-key-scan.json', frozen['keyScan'])
    write(a.ev / 'control-v2-receipt.json', control_receipt)
    write(a.ev / 'write-quiet-pre.json', pre_wq)
    write(a.ev / 'write-quiet-post.json', post_wq)
    receipt = {
        'schemaVersion': 1,
        'status': 'PASS_NONAUTHORIZING_ACTUAL_V3_EXACT_EXECUTABLE_STRESS',
        'reviewerPr': a.rpr,
        'reviewerHead': a.rh,
        'reviewerBranch': RBR,
        'reviewerTree': reviewer_tree,
        'stressRunId': a.run,
        'reviewRunAttempt': a.attempt,
        'subjectAuthorizationPr': SUBJECT_PR,
        'subjectAuthorizationHead': SUBJECT_HEAD,
        'subjectAuthorizationParent': CONTROL_HEAD,
        'authorizationJsonSha256': AUTH_SHA,
        'authorizationJsonGitBlobSha1': AUTH_BLOB,
        'canonicalWqParserPath': WQ_PATH,
        'canonicalWqParserBlob': WQ_BLOB,
        'canonicalWqParserSubjectBound': True,
        'discussionLiveSchemaPassed': True,
        'discussionFixtureSuitePassed': True,
        'discussionCount': live2['count'],
        'discussionCanonicalSha256': live2['canonicalSha256'],
        'discussionGraphqlErrors': [],
        'candidateSeedCount': 72,
        'candidateSeedCanonicalSha256': SSH,
        'candidateRowsCanonicalSha256': RSH,
        'latestPriorConsumedOrDispatchedScientificOrdinal': frozen['latest'],
        'nextAvailableScientificOrdinal': 46,
        'authorizationBranch': AB,
        'dispatchBranch': DB,
        'executionKey': KEY,
        'scientificOrdinalAllocated': False,
        'ordinalReserved': False,
        'authorizationRefCreated': False,
        'dispatchCreated': False,
        'candidateSeedsAppliedToCases': False,
        'seedUniverseConsumed': False,
        'publisherInvoked': False,
        'scienceInvoked': False,
        'solverExecuted': False,
        'protectedResultsOpened': False,
    }
    receipt['receiptSha256'] = canon(receipt)
    write(a.ev / 'actual-stress-receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True))


def review(a):
    req(not out('git', 'status', '--porcelain', '--untracked-files=no'), 'tracked subject workspace dirty')
    req(not out('git', 'status', '--porcelain'), 'subject workspace dirty')
    req(not out('git', 'status', '--porcelain', cwd=INFRA), 'reviewer workspace dirty')
    c = ctrl()
    a.ev.mkdir(parents=True, exist_ok=False)
    paths, reviewer_tree, reviewer_pr = static_common(c, a, 'edited')
    launch = verify_launch_binding(c, a, reviewer_pr)
    pre = wq(c, a.repo, a.tok, a.rh, a.rpr, launch['wqBegin'])
    subject = (ROOT / AUTH).read_bytes()
    control_receipt = control_artifact(c, a, subject)
    fixtures = discussion_fixtures()
    discussion_pre = collect_discussions(a.repo, a.tok)
    source_api = c.core.verify_source_api(a.repo, a.tok)
    source, h42, tmp = c.core.source_worktree(a.repo)
    try:
        c.core.verify_source_code(source)
        scanner_wrapper, ledger_module = c.core.load_source_modules(source, h42)
        scanner = scanner_wrapper.mod
        c.core.require_bound_scanner_mode(scanner)
        scanner.REVIEW_PROOF_ARTIFACT_NAME = ART
        ledger = c.core.validate_source_ledger(ledger_module, h42)
        req(ledger['candidateSeedCanonicalSha256'] == SSH and ledger['candidateRowsCanonicalSha256'] == RSH, 'fresh ledger drift')
        tracked = c.core.tracked_tree_scan(a.ev, ledger)
        seeds = {int(value) for value in ledger['candidateSeeds']}
        req(len(seeds) == 72, 'seed cardinality drift')
        guard = wq(c, a.repo, a.tok, a.rh, a.rpr, pre['begin'])
        req(guard['tail'] == pre['tail'], '#60 tail changed before scan')
        actions_guard = quiesce(c, a)
        guard = wq(c, a.repo, a.tok, a.rh, a.rpr, pre['begin'])
        req(guard['tail'] == pre['tail'], '#60 tail changed immediately before scan')
        req(c.core.branch_head(a.repo, 'main', a.tok) == MAIN and c.core.branch_head(a.repo, SUBJECT_BRANCH, a.tok) == SUBJECT_HEAD, 'base moved before scan')
        discussion_guard = collect_discussions(a.repo, a.tok)
        req(discussion_guard['canonicalSha256'] == discussion_pre['canonicalSha256'] and discussion_guard['count'] == discussion_pre['count'], 'Discussions surface changed before protected snapshot')
        ctx, stable, fence, post = scanner.collect_stable(a.repo, 60, a.tok, a.run, seeds, 'authorization-recheck')
        rep = scanner.evaluate_context(
            ctx, seeds, a.run,
            stable_double_enumeration_passed=True,
            stable_context_sha256_value=stable,
            audit_mode='authorization-recheck',
            expected_branch_name=RBR,
            expected_repo_head=a.rh,
            snapshot_fence=fence,
            post_fence_arrival_counts=post,
        )
        for key, value in {
            'candidateSeedCount': 72,
            'repositoryGlobalCollisionCount': 0,
            'repositoryGlobalCollisionSurfaceScanPassed': True,
            'repositoryGlobalDoubleEnumerationStable': True,
            'repositoryGlobalEnumerationPassCount': 2,
            'auditedBranchHeadMatchesRepositoryHead': True,
            'repositoryGlobalPostFenceCandidateSeedCollisionCount': 0,
            'allStatePullRequestsInspected': True,
            'allStateIssuesInspected': True,
            'allRepositoryIssueCommentsInspected': True,
            'allRepositoryPullReviewCommentsInspected': True,
            'allRepositoryCommitCommentsInspected': True,
        }.items():
            req(rep.get(key) == value, f'global scan drift {key}={rep.get(key)!r}')
        req(not scanner.final_review_proof_artifacts(a.repo, a.tok, a.run), 'prior review-proof artifact identity exists')
        discussion_post = collect_discussions(a.repo, a.tok)
        req(discussion_post['canonicalSha256'] == discussion_guard['canonicalSha256'] and discussion_post['count'] == discussion_guard['count'], 'Discussions surface changed across protected snapshot')
    finally:
        c.core.cleanup_worktrees(source, h42, tmp)
    consumed45 = c.core.verify_consumed45(a.repo, a.tok)
    preauth = c.core.load('avps46_review_surface_v3_final', ROOT / c.core.PREAUTH_SURFACE_PATH)
    payload = preauth.collect(a.repo, a.tok)
    latest = preauth.latest_consumed_or_dispatched_ordinal(payload)
    req(latest == 45, f'latest consumed/dispatched={latest}')
    _, _, ordinal_module = preauth._modules()
    observations = ordinal_module.authoritative_global_ordinal_observations(payload, current_run_id=a.run)
    nonself = [row for row in observations if not selfobs(row, payload, a.rpr, a.rh)]
    req(nonself and max(int(row['ordinal']) for row in nonself) == 45, 'non-self global ordinal max drift')
    req(not [row for row in nonself if int(row['ordinal']) == 46], 'non-self ordinal46 occupancy')
    consumed = {int(row['ordinal']) for row in nonself if row.get('reason') == 'exact-consumed-marker'}
    req({41, 42, 43, 44, 45}.issubset(consumed), f'consumed markers incomplete {sorted(consumed)}')
    auth = json.loads(subject)
    branches = {str(row.get('name') or '') for row in payload.get('branches', [])}
    req(AB not in branches and DB not in branches, 'live ordinal46 auth/dispatch ref exists')
    comments = [str(row.get('body') or '').strip() for row in payload.get('issue60Comments', [])]
    req(sum(1 for row in comments if row == ORDINAL45_CONSUMED_MARKER) == 1, 'ordinal45 consumed marker count drift')
    req(not any(row.upper().startswith('ORDINAL46_') for row in comments), 'ordinal46 allocation/consumed marker exists')
    proposed_paths = {auth['proposedPublisherWorkflowPath'], auth['proposedScienceWorkflowPath']}
    req(not any(str(row.get('path') or '') in proposed_paths for row in payload.get('runs', [])), 'ordinal46 proposed publisher/science run exists')
    freshness, _, _ = preauth._modules()
    key_scan = c.proposal_aware_execution_key_scan(payload, KEY, 46, freshness.positive_candidate_claims, current_pr=SUBJECT_PR, current_run_id=a.run)
    req(key_scan['authoritativeExecutionKeyUseCount'] == 0, f'authoritative execution-key use {key_scan["authoritativeExecutionKeyUseRows"]}')
    grep = run('git', 'grep', '-n', '-F', KEY, check=False)
    lines = [line for line in grep.stdout.splitlines() if line]
    req(grep.returncode == 0 and len(lines) == 1 and lines[0].startswith(AUTH + ':'), 'tracked execution-key occurrence not self-only')
    req(auth['scientificOrdinal'] == 46 and auth['latestPriorConsumedOrDispatchedScientificOrdinal'] == 45, 'PR1026 frozen ordinal semantics drift')
    req(auth['authorizationBranch'] == AB and auth['dispatchBranch'] == DB and auth['executionKey'] == KEY, 'PR1026 frozen identity semantics drift')
    req(auth['candidateSeedCount'] == 72 and auth['candidateSeedCanonicalSha256'] == SSH and auth['candidateRowsCanonicalSha256'] == RSH, 'PR1026 frozen seed semantics drift')
    req(all(auth.get(key) is False for key in FALSE_FLAGS), 'PR1026 frozen false boundary drift')
    installed = c.core.verify_installed_blobs(source_api['identity'])
    post_wq = wq(c, a.repo, a.tok, a.rh, a.rpr, pre['begin'])
    req(post_wq['tail'] == pre['tail'], '#60 tail changed during review')
    req(c.core.branch_head(a.repo, 'main', a.tok) == MAIN and c.core.branch_head(a.repo, SUBJECT_BRANCH, a.tok) == SUBJECT_HEAD and c.core.branch_head(a.repo, RBR, a.tok) == a.rh, 'final branch/main drift')
    write(a.ev / 'repository-global-seed-recheck.json', rep)
    write(a.ev / 'discussion-fixtures.json', fixtures)
    write(a.ev / 'discussion-live-inventory.json', discussion_post)
    write(a.ev / 'global-ordinal-observations.json', observations)
    write(a.ev / 'proposal-aware-execution-key-scan.json', key_scan)
    write(a.ev / 'mutable-actions-quiescence.json', actions_guard)
    write(a.ev / 'control-v2-receipt.json', control_receipt)
    write(a.ev / 'consumed-ordinal45-readback.json', consumed45)
    write(a.ev / 'installed-byte-readback.json', installed)
    write(a.ev / 'prelaunch-run-bindings.json', launch)
    write(a.ev / 'write-quiet-pre.json', pre)
    write(a.ev / 'write-quiet-post.json', post_wq)
    receipt = {
        'schemaVersion': 1,
        'status': 'PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEWED_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED',
        'reviewerPr': a.rpr,
        'reviewerHead': a.rh,
        'reviewerBranch': RBR,
        'reviewerTree': reviewer_tree,
        'reviewRunId': a.run,
        'reviewRunAttempt': a.attempt,
        'subjectAuthorizationPr': SUBJECT_PR,
        'subjectAuthorizationHead': SUBJECT_HEAD,
        'subjectAuthorizationParent': CONTROL_HEAD,
        'authorizationJsonSha256': AUTH_SHA,
        'authorizationJsonGitBlobSha1': AUTH_BLOB,
        'controlArtifact': CA,
        'controlArtifactDigest': CD,
        'controlReceiptRawSha256': RR,
        'controlReceiptCanonicalSelfSha256': RC,
        'canonicalWqParserPath': WQ_PATH,
        'canonicalWqParserBlob': WQ_BLOB,
        'canonicalWqParserSubjectBound': True,
        'discussionLiveSchemaPassed': True,
        'discussionFixtureSuitePassed': True,
        'discussionCount': discussion_post['count'],
        'discussionCanonicalSha256': discussion_post['canonicalSha256'],
        'discussionGraphqlErrors': [],
        'genericPrelaunchRunId': launch['genericRun'],
        'actualStressPrelaunchRunId': launch['stressRun'],
        'actualStressArtifactId': launch['stressArtifactId'],
        'writeQuietBeginCommentId': pre['begin'],
        'candidateSeedCount': 72,
        'candidateSeedCanonicalSha256': SSH,
        'candidateRowsCanonicalSha256': RSH,
        'trackedTreeExternalCollisionCount': tracked.get('trackedTreeExternalCollisionCount'),
        'repositoryGlobalCollisionCount': rep.get('repositoryGlobalCollisionCount'),
        'repositoryGlobalDoubleEnumerationStable': rep.get('repositoryGlobalDoubleEnumerationStable'),
        'repositoryGlobalStableContextSha256': rep.get('repositoryGlobalStableContextSha256'),
        'repositoryGlobalSnapshotFenceSha256': rep.get('repositoryGlobalSnapshotFenceSha256'),
        'latestPriorConsumedOrDispatchedScientificOrdinal': latest,
        'nonSelfGlobalScientificOrdinalMax': 45,
        'nextAvailableScientificOrdinal': 46,
        'authorizationBranch': AB,
        'dispatchBranch': DB,
        'executionKey': KEY,
        'authoritativeExecutionKeyUseCount': key_scan['authoritativeExecutionKeyUseCount'],
    }
    receipt.update({key: False for key in FALSE_FLAGS})
    receipt['receiptSha256'] = canon(receipt)
    write(a.ev / 'authorization-review-receipt.json', receipt)
    print(json.dumps(receipt, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    for name in ('repo', 'tok', 'rh', 'rb', 'base', 'bb', 'event', 'action', 'mode'):
        parser.add_argument('--' + name, required=True)
    for name in ('rpr', 'run', 'attempt'):
        parser.add_argument('--' + name, type=int, required=True)
    parser.add_argument('--ev', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == 'stress':
            stress(args)
        elif args.mode == 'review':
            review(args)
        else:
            raise Refusal('unknown mode')
    except Exception as exc:
        try:
            args.ev.mkdir(parents=True, exist_ok=True)
            write(args.ev / 'failure.json', {'type': type(exc).__name__, 'message': str(exc)[:8000]})
        except Exception:
            pass
        raise


if __name__ == '__main__':
    main()
