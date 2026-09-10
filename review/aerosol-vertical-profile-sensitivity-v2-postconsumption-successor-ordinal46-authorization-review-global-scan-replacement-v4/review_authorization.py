from __future__ import annotations

import argparse
import ast
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
MAIN = 'f5ebc646aba96ad13753d55baf2b0c55cff64ccb'
RBR = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v4-20260910'
STAGE = 'AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEW_GLOBAL_SCAN_REPLACEMENT_V4'
WF = '.github/workflows/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v4.yml'
SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v4/review_authorization.py'
ART = 'avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v4-proof'
STRESS_ART = 'avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v4-actual-stress-proof'
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
LAUNCH_PREFIX = 'AVPS_V4_PROTECTED_LAUNCH | authorized=true | '
GRAPHQL_URL = 'https://api.github.com/graphql'
HIST_BEGIN = 5613910902
HIST_MALFORMED_END = 5614235428
HIST_CORRECTION_END = 5618881442
HIST_STAGE = 'AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEW_GLOBAL_SCAN_REPLACEMENT_V2'
HIST_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v2-20260910'
HIST_HEAD = '2acc4d73c08f741ba76643057535d73b7ffc66bc'
HIST_RUN = '34443355962'
HIST_JOB = '102762814211'
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


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return load('avps46_review_ctrl_v4', path)


def canonical_wq_module():
    path = ROOT / WQ_PATH
    req(path.is_file(), 'canonical WQ parser missing from frozen subject')
    req(blob(path) == WQ_BLOB, 'canonical WQ parser byte drift')
    mod = load('avps46_subject_wq_parser_v1_v4', path)
    req(Path(mod.__file__).resolve() == path.resolve(), 'canonical WQ parser not subject-bound')
    req(hasattr(mod, 'is_write_quiet_begin') and hasattr(mod, 'record_write_quiet_end'), 'canonical WQ parser API drift')
    return mod


def first_line(body):
    lines = str(body or '').splitlines()
    return lines[0].strip() if lines else ''


def marker_parts(body, prefix):
    line = first_line(body)
    req(line.startswith(prefix + ' | '), f'wrong marker prefix: {line[:120]}')
    parts = [part.strip() for part in line.split('|')]
    req(len(parts) >= 2, 'marker missing stage')
    fields = {}
    for part in parts[2:]:
        if not part:
            continue
        req('=' in part, f'malformed marker token {part!r}')
        key, value = part.split('=', 1)
        key = key.strip()
        value = value.strip()
        req(key and value and key not in fields, f'duplicate/empty marker token {part!r}')
        fields[key] = value
    return parts[1], fields


def historical_pair_rows(rows):
    by_id = {}
    for row in rows:
        cid = int(row['id'])
        if cid in (HIST_BEGIN, HIST_MALFORMED_END, HIST_CORRECTION_END):
            req(cid not in by_id, f'duplicate historical WQ row id {cid}')
            by_id[cid] = row
    req(set(by_id) == {HIST_BEGIN, HIST_MALFORMED_END, HIST_CORRECTION_END}, 'historical V2 WQ correction triplet incomplete')
    req(HIST_BEGIN < HIST_MALFORMED_END < HIST_CORRECTION_END, 'historical V2 WQ chronology drift')

    begin_stage, begin_fields = marker_parts(by_id[HIST_BEGIN].get('body'), 'WRITE_QUIET_BEGIN')
    req(begin_stage == HIST_STAGE, 'historical V2 BEGIN stage drift')
    expected_begin = {
        'branch': HIST_BRANCH,
        'head': HIST_HEAD,
        'base': SUBJECT_HEAD,
        'subject_pr': str(SUBJECT_PR),
        'subject_head': SUBJECT_HEAD,
        'control_parent': CONTROL_HEAD,
    }
    req(begin_fields == expected_begin, f'historical V2 BEGIN fields drift {begin_fields}')

    old_stage, old_fields = marker_parts(by_id[HIST_MALFORMED_END].get('body'), 'WRITE_QUIET_END')
    req(old_stage == HIST_STAGE, 'historical malformed END stage drift')
    req(not any(k in old_fields for k in ('begin', 'beginComment', 'begin_comment')), 'historical malformed END unexpectedly gained machine linkage')
    expected_end = {
        'branch': HIST_BRANCH,
        'head': HIST_HEAD,
        'base': SUBJECT_HEAD,
        'subject_pr': str(SUBJECT_PR),
        'subject_head': SUBJECT_HEAD,
        'run': HIST_RUN,
        'attempt': '1',
        'job': HIST_JOB,
        'terminal': 'FAILURE',
        'artifact': 'NONE',
    }
    req(old_fields == expected_end, f'historical malformed END fields drift {old_fields}')
    req(f'Exact matching closure for BEGIN `{HIST_BEGIN}` only.' in str(by_id[HIST_MALFORMED_END].get('body') or ''), 'historical malformed END human linkage drift')

    new_stage, new_fields = marker_parts(by_id[HIST_CORRECTION_END].get('body'), 'WRITE_QUIET_END')
    req(new_stage == HIST_STAGE, 'historical correction END stage drift')
    req(new_fields.get('begin') == str(HIST_BEGIN), 'historical correction END begin linkage drift')
    req(not any(k in new_fields for k in ('beginComment', 'begin_comment')), 'historical correction END alias drift')
    compare = dict(new_fields)
    compare.pop('begin', None)
    req(compare == expected_end, f'historical correction END fields mismatch {compare}')
    correction_body = str(by_id[HIST_CORRECTION_END].get('body') or '')
    for text in (
        'CORRECTED MACHINE-READABLE FENCE RELEASE ONLY.',
        f'`begin={HIST_BEGIN}` linkage omitted from earlier human-readable END comment `{HIST_MALFORMED_END}`',
        'This correction changes only machine-readable linkage and does not alter any scientific or reviewer result.',
        'SCIENCE_FALSE',
    ):
        req(text in correction_body, f'historical correction END provenance missing {text!r}')

    binders = []
    for row in rows:
        line = first_line(row.get('body'))
        if not line.startswith('WRITE_QUIET_END |') and 'WRITE_QUIET_END' not in line:
            continue
        if any(token in line for token in (f'begin={HIST_BEGIN}', f'beginComment={HIST_BEGIN}', f'begin_comment={HIST_BEGIN}')):
            binders.append(int(row['id']))
    req(binders == [HIST_CORRECTION_END], f'historical correction duplicate/conflict binders {binders}')
    return by_id


def parse_wq_rows(rows):
    historical_pair_rows(rows)
    mod = canonical_wq_module()
    begins = {}
    seen = set()
    closed = set()
    for row in rows:
        cid = int(row['id'])
        body = str(row.get('body') or '')
        if cid == HIST_MALFORMED_END:
            continue
        if mod.record_write_quiet_end(body, cid, seen, closed):
            continue
        if mod.is_write_quiet_begin(body):
            seen.add(cid)
            begins[cid] = row
    req(HIST_BEGIN in seen and HIST_BEGIN in closed, 'historical V2 correction did not close exact BEGIN')
    return begins, seen, closed


def _fixture_begin():
    return (
        f'WRITE_QUIET_BEGIN | {HIST_STAGE} | branch={HIST_BRANCH} | head={HIST_HEAD} | base={SUBJECT_HEAD} | '
        f'subject_pr={SUBJECT_PR} | subject_head={SUBJECT_HEAD} | control_parent={CONTROL_HEAD}'
    )


def _fixture_old_end():
    return (
        f'WRITE_QUIET_END | {HIST_STAGE} | branch={HIST_BRANCH} | head={HIST_HEAD} | base={SUBJECT_HEAD} | '
        f'subject_pr={SUBJECT_PR} | subject_head={SUBJECT_HEAD} | run={HIST_RUN} | attempt=1 | job={HIST_JOB} | terminal=FAILURE | artifact=NONE\n\n'
        f'Exact matching closure for BEGIN `{HIST_BEGIN}` only.'
    )


def _fixture_correction():
    return (
        f'WRITE_QUIET_END | {HIST_STAGE} | begin={HIST_BEGIN} | branch={HIST_BRANCH} | head={HIST_HEAD} | base={SUBJECT_HEAD} | '
        f'subject_pr={SUBJECT_PR} | subject_head={SUBJECT_HEAD} | run={HIST_RUN} | attempt=1 | job={HIST_JOB} | terminal=FAILURE | artifact=NONE\n\n'
        f'CORRECTED MACHINE-READABLE FENCE RELEASE ONLY. This supplies the exact canonical `begin={HIST_BEGIN}` linkage omitted from earlier human-readable END comment `{HIST_MALFORMED_END}`. '
        'This correction changes only machine-readable linkage and does not alter any scientific or reviewer result. SCIENCE_FALSE'
    )


def expect_wq_failure(rows, label):
    try:
        parse_wq_rows(rows)
    except (Refusal, SystemExit):
        return
    raise Refusal(f'WQ negative fixture unexpectedly accepted: {label}')


def wq_correction_fixtures():
    base = [
        {'id': HIST_BEGIN, 'body': _fixture_begin()},
        {'id': HIST_MALFORMED_END, 'body': _fixture_old_end()},
        {'id': HIST_CORRECTION_END, 'body': _fixture_correction()},
    ]
    _, seen, closed = parse_wq_rows(base)
    req(HIST_BEGIN in seen and HIST_BEGIN in closed, 'WQ correction positive fixture failed')
    expect_wq_failure(base[:-1], 'correction absent')
    wrong = [dict(row) for row in base]
    wrong[2]['body'] = wrong[2]['body'].replace(f'head={HIST_HEAD}', 'head=0000000000000000000000000000000000000000', 1)
    expect_wq_failure(wrong, 'correction mismatch')
    duplicate = [dict(row) for row in base] + [{'id': HIST_CORRECTION_END + 1, 'body': _fixture_correction()}]
    expect_wq_failure(duplicate, 'duplicate correction binding')
    conflict = [dict(row) for row in base] + [{'id': HIST_CORRECTION_END + 1, 'body': _fixture_correction().replace(f'run={HIST_RUN}', 'run=99999999999', 1)}]
    expect_wq_failure(conflict, 'conflicting correction binding')
    unrelated = [dict(row) for row in base] + [{'id': HIST_CORRECTION_END + 1, 'body': 'WRITE_QUIET_END | UNRELATED_STAGE | head=x'}]
    expect_wq_failure(unrelated, 'unrelated malformed END')
    bad_old = [dict(row) for row in base]
    bad_old[1]['body'] = bad_old[1]['body'].replace(f'job={HIST_JOB}', 'job=1', 1)
    expect_wq_failure(bad_old, 'old/correction mismatch')
    return {
        'exactPositivePair': True,
        'missingCorrectionFatal': True,
        'wrongCorrectionFatal': True,
        'duplicateCorrectionFatal': True,
        'conflictingCorrectionFatal': True,
        'unrelatedMalformedEndFatal': True,
        'oldCorrectionMismatchFatal': True,
        'canonicalParserStillAuthoritative': True,
    }


def wq(c, repo, tok, rh, rpr, expect=None):
    rows = c.core.pages(c.core.repo_url(repo, 'issues/60/comments'), tok)
    begins, seen, closed = parse_wq_rows(rows)
    unmatched = sorted(x for x in seen if x not in closed)
    req(len(unmatched) == 1, f'expected own WQ only, got {unmatched}')
    begin_id = unmatched[0]
    if expect is not None:
        req(begin_id == expect, 'WQ begin changed')
    marker = first_line(begins[begin_id].get('body'))
    req(marker.startswith(f'WRITE_QUIET_BEGIN | {STAGE} |'), 'wrong WQ stage')
    for field in (
        f'branch={RBR}', f'head={rh}', f'base={MAIN}', f'subject_pr={SUBJECT_PR}',
        f'subject_head={SUBJECT_HEAD}', f'control_parent={CONTROL_HEAD}',
    ):
        req(field in marker, f'WQ missing {field}')
    return {
        'begin': begin_id,
        'count': len(rows),
        'tail': max(int(r['id']) for r in rows),
        'canonicalParserBlob': WQ_BLOB,
        'historicalMalformedEnd': HIST_MALFORMED_END,
        'historicalCanonicalCorrectionEnd': HIST_CORRECTION_END,
    }


def wq_absent(c, repo, tok):
    rows = c.core.pages(c.core.repo_url(repo, 'issues/60/comments'), tok)
    _, seen, closed = parse_wq_rows(rows)
    unmatched = sorted(x for x in seen if x not in closed)
    req(not unmatched, f'ACTUAL stress requires no unmatched WQ, got {unmatched}')
    return {
        'unmatched': [],
        'count': len(rows),
        'tail': max(int(r['id']) for r in rows),
        'canonicalParserBlob': WQ_BLOB,
        'historicalMalformedEnd': HIST_MALFORMED_END,
        'historicalCanonicalCorrectionEnd': HIST_CORRECTION_END,
    }


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


def zero_runtime_static_proof():
    workflow = (INFRA / WF).read_text()
    script = (INFRA / SCRIPT).read_text()
    req('workflow_dispatch:' not in workflow, 'reviewer workflow unexpectedly exposes workflow_dispatch')
    tree = ast.parse(script)
    subprocess_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == 'subprocess':
                subprocess_calls.append(node.func.attr)
    req(subprocess_calls == ['run'], f'unexpected subprocess API surface {subprocess_calls}')
    req('libRadtran' not in workflow and 'MYSTIC' not in workflow, 'runtime package token in reviewer workflow')
    req(shutil.which('uvspec') is None, 'uvspec present in zero-runtime reviewer environment')
    return {
        'workflowDispatchAbsent': True,
        'onlySubprocessApi': 'run',
        'uvspecAbsentFromPath': True,
        'reviewerChangedOnlyControlFiles': True,
        'scientificRuntimeSetupPerformed': False,
        'scientificExecutionPerformed': False,
        'solverExecutionPerformed': False,
        'protectedResultsOpened': False,
    }


def static_common(c, a, expected_action):
    req(ROOT.resolve() != INFRA.resolve(), 'subject/reviewer checkouts must be distinct')
    req(a.event == 'pull_request' and a.action == expected_action and a.attempt == 1, 'wrong event/action/attempt')
    req(a.rb == RBR and a.base == MAIN and a.bb == 'main', 'review carrier identity drift')
    req(out('git', 'rev-parse', 'HEAD') == SUBJECT_HEAD, 'subject checkout drift')
    req(out('git', 'rev-parse', f'HEAD:{AUTH}') == AUTH_BLOB, 'authorization blob drift')
    req(hashlib.sha256((ROOT / AUTH).read_bytes()).hexdigest() == AUTH_SHA, 'authorization raw-byte drift')
    req(out('git', 'rev-parse', 'HEAD', cwd=INFRA) == a.rh, 'reviewer checkout drift')
    req(not out('git', 'rev-list', '--merges', f'{MAIN}..{a.rh}', cwd=INFRA), 'reviewer merge found')
    local_tree = out('git', 'rev-parse', 'HEAD^{tree}', cwd=INFRA)
    script_blob = out('git', 'rev-parse', f'HEAD:{SCRIPT}', cwd=INFRA)
    workflow_blob = out('git', 'rev-parse', f'HEAD:{WF}', cwd=INFRA)
    req(script_blob == blob(INFRA / SCRIPT), 'reviewer script blob/local drift')
    req(workflow_blob == blob(INFRA / WF), 'reviewer workflow blob/local drift')
    api_commit = c.core.req_json(c.core.repo_url(a.repo, f'git/commits/{a.rh}'), a.tok)
    req(str((api_commit.get('tree') or {}).get('sha') or '') == local_tree, 'reviewer tree API/local drift')
    paths = sorted(x for x in out('git', 'diff', '--name-only', f'{MAIN}...{a.rh}', cwd=INFRA).splitlines() if x)
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
    req(reviewer_pr['base']['sha'] == MAIN and reviewer_pr['base']['ref'] == 'main', 'reviewer PR exact-main base drift')
    self_run = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{a.run}'), a.tok)
    req(self_run.get('event') == 'pull_request' and int(self_run.get('run_attempt') or 0) == 1, 'self-run event/attempt drift')
    req(self_run.get('head_sha') == a.rh and self_run.get('head_branch') == RBR and self_run.get('path') == WF, 'self-run registration drift')
    mod = canonical_wq_module()
    req(Path(mod.__file__).resolve() == (ROOT / WQ_PATH).resolve(), 'subject-bound WQ parser import-root proof failed')
    runtime_proof = zero_runtime_static_proof()
    return paths, local_tree, reviewer_pr, script_blob, workflow_blob, runtime_proof


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
            'User-Agent': 'avps-v4-result-blind-discussion-inventory',
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
    query_flat = ' '.join(DISCUSSION_QUERY.split())
    req('category { id }' in query_flat, 'current nested category query absent')
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
        {'errors': 'not-a-list'},
        {'data': None},
        {'data': {'repository': None}},
        {'data': {'repository': {'discussions': None}}},
        {'data': {'repository': {'discussions': {'nodes': {}, 'pageInfo': {}}}}},
        {'data': {'repository': {'discussions': {'nodes': [{'id': 'D', 'number': 1, 'updatedAt': 'x', 'categoryId': 'obsolete'}], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}}}},
        {'data': {'repository': {'discussions': {'nodes': [valid_a], 'pageInfo': {'hasNextPage': True, 'endCursor': None}}}}},
    ]
    refused = 0
    for case in malformed_cases:
        try:
            parse_discussion_page(case)
        except Refusal:
            refused += 1
    req(refused == len(malformed_cases), 'malformed/obsolete discussion response fixture failed')
    repeated_pages = {
        None: {'data': {'repository': {'discussions': {'nodes': [valid_a], 'pageInfo': {'hasNextPage': True, 'endCursor': 'SAME'}}}}},
        'SAME': {'data': {'repository': {'discussions': {'nodes': [valid_b], 'pageInfo': {'hasNextPage': True, 'endCursor': 'SAME'}}}}},
    }
    def repeat_transport(tok, owner, name, cursor):
        return repeated_pages[cursor]
    try:
        collect_discussions('search-maker/twilight-mystic-experiments', 'fixture-token', repeat_transport)
    except Refusal:
        pass
    else:
        raise Refusal('discussion repeated-cursor fixture failed')
    return {
        'pagination': True,
        'nullNode': True,
        'empty': True,
        'canonicalization': True,
        'categoryIdNormalization': True,
        'malformedRefusal': True,
        'allGraphqlErrorsCollected': True,
        'repeatedCursorRefusal': True,
    }


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
    preauth = c.core.load('avps46_review_surface_v4', ROOT / c.core.PREAUTH_SURFACE_PATH)
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
    req(set(fields) == {'head', 'generic_run', 'stress_run', 'stress_artifact', 'stress_digest', 'wq_begin'}, f'protected launch fields drift {sorted(fields)}')
    req(fields['head'] == a.rh, 'protected launch head drift')
    generic_run = int(fields['generic_run'])
    stress_run = int(fields['stress_run'])
    stress_artifact = int(fields['stress_artifact'])
    wq_begin = int(fields['wq_begin'])
    req(generic_run > 0 and stress_run > 0 and stress_artifact > 0 and wq_begin > 0, 'protected launch numeric binding invalid')
    generic = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{generic_run}'), a.tok)
    req(generic.get('status') == 'completed' and generic.get('conclusion') == 'success', 'generic prelaunch run not successful')
    req(int(generic.get('run_attempt') or 0) == 1 and generic.get('head_sha') == a.rh and generic.get('path') == GENERIC_WF, 'generic prelaunch identity drift')
    stress_run_row = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{stress_run}'), a.tok)
    req(stress_run_row.get('status') == 'completed' and stress_run_row.get('conclusion') == 'success', 'ACTUAL stress prelaunch run not successful')
    req(int(stress_run_row.get('run_attempt') or 0) == 1 and stress_run_row.get('head_sha') == a.rh and stress_run_row.get('path') == WF and stress_run_row.get('event') == 'pull_request', 'ACTUAL stress identity drift')
    artifacts = c.core.req_json(c.core.repo_url(a.repo, f'actions/runs/{stress_run}/artifacts?per_page=100'), a.tok)
    matches = [row for row in artifacts.get('artifacts', []) if row.get('name') == STRESS_ART and row.get('expired') is False and int(row.get('id') or 0) == stress_artifact]
    req(len(matches) == 1, 'ACTUAL stress immutable proof artifact missing/duplicate')
    req(str(matches[0].get('digest') or '') == fields['stress_digest'], 'ACTUAL stress artifact digest binding drift')
    raw = c.safe_request_bytes(c.core.repo_url(a.repo, f'actions/artifacts/{stress_artifact}/zip'), a.tok)
    req('sha256:' + hashlib.sha256(raw).hexdigest() == fields['stress_digest'], 'ACTUAL stress downloaded ZIP digest drift')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        req('actual-stress-receipt.json' in archive.namelist(), 'ACTUAL stress receipt absent')
        receipt = json.loads(archive.read('actual-stress-receipt.json'))
    req(receipt.get('status') == 'PASS_NONAUTHORIZING_ACTUAL_V4_EXACT_EXECUTABLE_STRESS', 'ACTUAL stress receipt status drift')
    req(receipt.get('exactExecutableStressPass') is True, 'ACTUAL stress exact executable PASS flag drift')
    req(receipt.get('reviewerHead') == a.rh and receipt.get('stressRunId') == stress_run and receipt.get('reviewRunAttempt') == 1, 'ACTUAL stress receipt identity drift')
    req(receipt.get('subjectAuthorizationHead') == SUBJECT_HEAD and receipt.get('canonicalWqParserBlob') == WQ_BLOB, 'ACTUAL stress subject/WQ binding drift')
    req(receipt.get('discussionLiveSchemaPassed') is True and receipt.get('discussionFixtureSuitePassed') is True, 'ACTUAL stress discussion proof drift')
    req(receipt.get('historicalWqCorrectionFixtureSuitePassed') is True, 'ACTUAL stress WQ correction proof drift')
    return {'genericRun': generic_run, 'stressRun': stress_run, 'wqBegin': wq_begin, 'stressArtifactId': stress_artifact, 'stressArtifactDigest': fields['stress_digest']}


def stress(a):
    req(not out('git', 'status', '--porcelain', '--untracked-files=no'), 'tracked subject workspace dirty')
    req(not out('git', 'status', '--porcelain'), 'subject workspace dirty')
    req(not out('git', 'status', '--porcelain', cwd=INFRA), 'reviewer workspace dirty')
    c = ctrl()
    a.ev.mkdir(parents=True, exist_ok=False)
    paths, reviewer_tree, _, script_blob, workflow_blob, runtime_proof = static_common(c, a, 'opened')
    pre_wq = wq_absent(c, a.repo, a.tok)
    subject = (ROOT / AUTH).read_bytes()
    control_receipt = control_artifact(c, a, subject)
    wq_fixtures = wq_correction_fixtures()
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
    write(a.ev / 'write-quiet-correction-fixtures.json', wq_fixtures)
    write(a.ev / 'repository-global-seed-recheck.json', frozen['repositoryGlobal'])
    write(a.ev / 'global-ordinal-observations.json', frozen['observations'])
    write(a.ev / 'proposal-aware-execution-key-scan.json', frozen['keyScan'])
    write(a.ev / 'control-v2-receipt.json', control_receipt)
    write(a.ev / 'write-quiet-pre.json', pre_wq)
    write(a.ev / 'write-quiet-post.json', post_wq)
    write(a.ev / 'zero-runtime-static-proof.json', runtime_proof)
    receipt = {
        'schemaVersion': 1,
        'status': 'PASS_NONAUTHORIZING_ACTUAL_V4_EXACT_EXECUTABLE_STRESS',
        'exactExecutableStressPass': True,
        'reviewerPr': a.rpr,
        'reviewerHead': a.rh,
        'reviewerBranch': RBR,
        'reviewerTree': reviewer_tree,
        'reviewerScriptGitBlobSha1': script_blob,
        'reviewerWorkflowGitBlobSha1': workflow_blob,
        'stressRunId': a.run,
        'reviewRunAttempt': a.attempt,
        'subjectAuthorizationPr': SUBJECT_PR,
        'subjectAuthorizationHead': SUBJECT_HEAD,
        'subjectAuthorizationParent': CONTROL_HEAD,
        'exactMain': MAIN,
        'authorizationJsonSha256': AUTH_SHA,
        'authorizationJsonGitBlobSha1': AUTH_BLOB,
        'canonicalWqParserPath': WQ_PATH,
        'canonicalWqParserBlob': WQ_BLOB,
        'canonicalWqParserSubjectBound': True,
        'historicalMalformedEndCommentId': HIST_MALFORMED_END,
        'historicalCanonicalCorrectionCommentId': HIST_CORRECTION_END,
        'historicalWqCorrectionFixtureSuitePassed': True,
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
        'protectedReviewerLaunched': False,
        'scientificRuntimeSetupPerformed': False,
    }
    receipt['receiptSha256'] = canon(receipt)
    write(a.ev / 'actual-stress-receipt.json', receipt)
    print('EXACT_EXECUTABLE_STRESS_PASS')
    print(json.dumps(receipt, sort_keys=True))


def review(a):
    req(not out('git', 'status', '--porcelain', '--untracked-files=no'), 'tracked subject workspace dirty')
    req(not out('git', 'status', '--porcelain'), 'subject workspace dirty')
    req(not out('git', 'status', '--porcelain', cwd=INFRA), 'reviewer workspace dirty')
    c = ctrl()
    a.ev.mkdir(parents=True, exist_ok=False)
    paths, reviewer_tree, reviewer_pr, script_blob, workflow_blob, runtime_proof = static_common(c, a, 'edited')
    launch = verify_launch_binding(c, a, reviewer_pr)
    pre = wq(c, a.repo, a.tok, a.rh, a.rpr, launch['wqBegin'])
    subject = (ROOT / AUTH).read_bytes()
    control_receipt = control_artifact(c, a, subject)
    wq_fixtures = wq_correction_fixtures()
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
    preauth = c.core.load('avps46_review_surface_v4_final', ROOT / c.core.PREAUTH_SURFACE_PATH)
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
    write(a.ev / 'write-quiet-correction-fixtures.json', wq_fixtures)
    write(a.ev / 'global-ordinal-observations.json', observations)
    write(a.ev / 'proposal-aware-execution-key-scan.json', key_scan)
    write(a.ev / 'mutable-actions-quiescence.json', actions_guard)
    write(a.ev / 'control-v2-receipt.json', control_receipt)
    write(a.ev / 'consumed-ordinal45-readback.json', consumed45)
    write(a.ev / 'installed-byte-readback.json', installed)
    write(a.ev / 'prelaunch-run-bindings.json', launch)
    write(a.ev / 'write-quiet-pre.json', pre)
    write(a.ev / 'write-quiet-post.json', post_wq)
    write(a.ev / 'zero-runtime-static-proof.json', runtime_proof)
    receipt = {
        'schemaVersion': 1,
        'status': 'PASS_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_ORDINAL46_AUTHORIZATION_REVIEWED_NOT_ALLOCATED_NOT_RESERVED_NOT_DISPATCHED',
        'reviewerPr': a.rpr,
        'reviewerHead': a.rh,
        'reviewerBranch': RBR,
        'reviewerTree': reviewer_tree,
        'reviewerScriptGitBlobSha1': script_blob,
        'reviewerWorkflowGitBlobSha1': workflow_blob,
        'reviewRunId': a.run,
        'reviewRunAttempt': a.attempt,
        'subjectAuthorizationPr': SUBJECT_PR,
        'subjectAuthorizationHead': SUBJECT_HEAD,
        'subjectAuthorizationParent': CONTROL_HEAD,
        'exactMain': MAIN,
        'authorizationJsonSha256': AUTH_SHA,
        'authorizationJsonGitBlobSha1': AUTH_BLOB,
        'controlArtifact': CA,
        'controlArtifactDigest': CD,
        'controlReceiptRawSha256': RR,
        'controlReceiptCanonicalSelfSha256': RC,
        'canonicalWqParserPath': WQ_PATH,
        'canonicalWqParserBlob': WQ_BLOB,
        'canonicalWqParserSubjectBound': True,
        'historicalMalformedEndCommentId': HIST_MALFORMED_END,
        'historicalCanonicalCorrectionCommentId': HIST_CORRECTION_END,
        'historicalWqCorrectionFixtureSuitePassed': True,
        'discussionLiveSchemaPassed': True,
        'discussionFixtureSuitePassed': True,
        'discussionCount': discussion_post['count'],
        'discussionCanonicalSha256': discussion_post['canonicalSha256'],
        'discussionGraphqlErrors': [],
        'genericPrelaunchRunId': launch['genericRun'],
        'actualStressPrelaunchRunId': launch['stressRun'],
        'actualStressArtifactId': launch['stressArtifactId'],
        'actualStressArtifactDigest': launch['stressArtifactDigest'],
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
    except BaseException as exc:
        try:
            args.ev.mkdir(parents=True, exist_ok=True)
            failure = {
                'schemaVersion': 1,
                'status': 'FAIL_RESULT_BLIND_V4',
                'type': type(exc).__name__,
                'message': str(exc)[:8000],
                'reviewerHead': getattr(args, 'rh', None),
                'runId': getattr(args, 'run', None),
                'attempt': getattr(args, 'attempt', None),
                'scientificOrdinalAllocated': False,
                'authorizationRefCreated': False,
                'dispatchCreated': False,
                'seedUniverseConsumed': False,
                'scienceInvoked': False,
                'solverExecuted': False,
                'protectedResultsOpened': False,
            }
            failure['receiptSha256'] = canon(failure)
            write(args.ev / 'failure.json', failure)
        except BaseException:
            pass
        raise


if __name__ == '__main__':
    main()
