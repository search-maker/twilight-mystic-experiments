#!/usr/bin/env python3
"""Zero-ARM-runtime exact-executable stress audit for query-only discovery.

Reads the ACTUAL candidate workflow/executable/manifest bytes and the complete
then-live Issue #60 control ledger. It never contacts ARM and never reads ARM
credentials. Its only network access is GitHub control-plane readback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

REPO = 'search-maker/twilight-mystic-experiments'
ISSUE = 60
BASELINE_COORDINATOR_COMMENT = 5590748165
EXPECTED_MANIFEST_SHA256 = '8a0756be59dac59cd8ad4fab77e499ec19069e24d2d2a636fa4352713b550def'
EXPECTED_PURPOSE = 'ARM_ENA_SWS_V1_E0_SUCCESSOR_QUERY_ONLY_AVAILABILITY_DISCOVERY'


class StressFailure(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def github_json(url: str, token: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {token}',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'arm-query-only-exact-executable-stress-v1',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        raise StressFailure(f'GitHub control-plane read failed: {type(exc).__name__}') from None


def complete_issue_comments(token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        url = f'https://api.github.com/repos/{REPO}/issues/{ISSUE}/comments?per_page=100&page={page}'
        batch = github_json(url, token)
        if not isinstance(batch, list):
            raise StressFailure('Issue #60 comments response is not a list')
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 100:
            raise StressFailure('Issue #60 pagination exceeded bounded maximum')
    return rows


def first_nonempty(body: str) -> str:
    return next((line.strip() for line in str(body or '').splitlines() if line.strip()), '')


def _field(line: str, key: str) -> str | None:
    m = re.search(rf'(?:^|[|\s]){re.escape(key)}=([^|\s]+)', line, flags=re.I)
    return m.group(1) if m else None


def _is_section_heading(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith(('-', '*')) or len(s) > 120:
        return False
    return s == s.upper() and re.fullmatch(r'[A-Z0-9 _/():.-]+', s) is not None


def _arm_control_text(body: str) -> str:
    lines = str(body or '').splitlines()
    first = first_nonempty(body)
    upper = first.upper()
    if upper.startswith('ARM_OWNER::') or upper.startswith('COORDINATOR::ARM'):
        return str(body or '')
    if not upper.startswith('COORDINATOR::'):
        return ''

    captured: list[str] = []
    active = False
    for raw in lines[1:]:
        s = raw.strip()
        up = s.upper()
        arm_header = bool(
            re.fullmatch(r'ARM(?:\s*/\s*[A-Z0-9 _-]+)+', up)
            or re.match(r'^ARM\s*[:|]', up)
            or re.match(r'^-\s*ARM\b', up)
        )
        if arm_header:
            active = True
            captured.append(s)
            continue
        if active and _is_section_heading(s) and not up.startswith('ARM'):
            break
        if active:
            captured.append(s)
    return '\n'.join(captured)


_DIRECT_ADVERSE_TITLE_MARKERS = (
    'REVOKED', 'DO_NOT_USE', 'NOT_ADMISSIBLE', 'NONADMISSIBLE', 'QUARANTINE',
    'CANCELLED', 'CANCELED', 'WITHDRAWN', 'DO_NOT MERGE', 'DO_NOT_MERGE',
    'MUST NOT MERGE', 'MUST_NOT_MERGE', 'READ-ONLY', 'READ_ONLY', 'PARKED',
    'MERGE_PROHIBITED', 'REFUSAL', 'REFUSED', 'AUTHORITY_EXPIRED',
    'AUTHORITY_EXPIRY', 'EXPIRED',
)

_DIRECT_ALLOWED_TITLE_MARKERS = (
    'ACCEPTED', 'MERGE_AUTHORIZED', 'INSTALL_AUTHORIZED', 'REPAIR_AUTHORIZED',
    'SUCCESSOR_AUTHORIZED', 'CANDIDATE_AUTHORIZED', 'BLOCKER_CLEARED',
    'READY_FOR_REVIEW', 'READY_FOR_CLASSIFICATION',
)


def _direct_arm_control_disposition(first: str) -> str:
    """Classify direct ARM owner/Coordinator governance from its structured title.

    Protected-boundary phrases such as AUTHENTICATED_INVOCATION_*_FALSE or
    NOT_AUTHORIZED do not themselves make a positive acceptance/repair
    transition adverse. Explicit revocation/nonadmissibility/refusal titles do.
    Unknown direct ARM governance remains fail-closed.
    """
    upper = first.upper()
    if not (upper.startswith('ARM_OWNER::') or upper.startswith('COORDINATOR::ARM')):
        raise StressFailure('direct ARM disposition called for non-direct control')

    if any(marker in upper for marker in _DIRECT_ADVERSE_TITLE_MARKERS):
        return 'adverse'
    if re.search(r'(?<!NO_)(?<!NON_)\bBLOCKER\b', upper) and 'BLOCKER_CLEARED' not in upper:
        return 'adverse'
    if ('FAIL_CLOSED' in upper or 'FAIL-CLOSED' in upper) and not any(
        marker in upper for marker in ('REPAIR_AUTHORIZED', 'SUCCESSOR_AUTHORIZED', 'CANDIDATE_AUTHORIZED')
    ):
        return 'adverse'
    if any(marker in upper for marker in _DIRECT_ALLOWED_TITLE_MARKERS):
        return 'allowed'
    raise StressFailure(f'ambiguous/unclassified direct ARM governance title: {first}')


def _adverse_arm_control(body: str) -> bool:
    first_raw = first_nonempty(body)
    first = first_raw.upper()
    text = _arm_control_text(body)
    if not text:
        return False

    if first.startswith('ARM_OWNER::') or first.startswith('COORDINATOR::ARM'):
        return _direct_arm_control_disposition(first_raw) == 'adverse'

    upper = text.upper()
    fatal = (
        'REVOKED', 'DO_NOT_USE', 'NOT_ADMISSIBLE', 'NONADMISSIBLE', 'QUARANTINE',
        'CANCELLED', 'CANCELED', 'WITHDRAWN', 'DO NOT MERGE', 'MUST NOT MERGE',
        'READ-ONLY', 'PARKED',
    )
    if any(word in upper for word in fatal):
        return True
    if re.search(r'(?<!NO_)(?<!NON_)\bBLOCKER\b', upper) and 'BLOCKER_CLEARED' not in upper:
        return True
    return False


def audit_arm_governance(comments: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [int(row.get('id', 0)) for row in comments]
    baseline = next((row for row in comments if int(row.get('id', 0)) == BASELINE_COORDINATOR_COMMENT), None)
    if baseline is None:
        raise StressFailure('required Coordinator fence-clear preparation baseline missing from complete #60 ledger')
    baseline_body = str(baseline.get('body', ''))
    required_baseline = (
        'ARM may resume only its already-authorized post-V5R1 fence-clear safe/query-only fresh-successor preparation',
        'PR1001 remains governance-NONADMISSIBLE and must not merge',
        'authenticated invocation remains separately unauthorized',
        'GLOBAL WRITE_QUIET remains binding',
    )
    for needle in required_baseline:
        if needle not in baseline_body:
            raise StressFailure(f'Coordinator fence-clear baseline semantic drift: {needle}')

    open_begins: dict[int, str | None] = {}
    begin_ids: list[int] = []
    end_ids: list[int] = []
    arm_relevant: list[int] = []
    adverse: list[int] = []

    for row in comments:
        cid = int(row.get('id', 0))
        if cid <= BASELINE_COORDINATOR_COMMENT:
            continue
        body = str(row.get('body', ''))
        first = first_nonempty(body)
        upper = first.upper()

        if 'WRITE_QUIET_BEGIN' in upper:
            if cid in open_begins:
                raise StressFailure(f'duplicate WRITE_QUIET_BEGIN identity: {cid}')
            open_begins[cid] = _field(first, 'stage')
            begin_ids.append(cid)

        if 'WRITE_QUIET_END' in upper:
            raw_begin = _field(first, 'beginComment')
            if raw_begin is None or not raw_begin.isdigit():
                raise StressFailure(f'WRITE_QUIET_END lacks exact beginComment binding: {cid}')
            begin_id = int(raw_begin)
            if begin_id not in open_begins:
                raise StressFailure(f'WRITE_QUIET_END references no open post-baseline BEGIN: {cid}->{begin_id}')
            begin_stage = open_begins[begin_id]
            end_stage = _field(first, 'stage')
            if begin_stage and end_stage and begin_stage != end_stage:
                raise StressFailure(f'WRITE_QUIET stage mismatch: {begin_id}->{cid}')
            del open_begins[begin_id]
            end_ids.append(cid)

        if _arm_control_text(body):
            arm_relevant.append(cid)
            if _adverse_arm_control(body):
                adverse.append(cid)

    if open_begins:
        raise StressFailure(f'unmatched repository-global WRITE_QUIET_BEGIN after baseline: {sorted(open_begins)[-1]}')
    if adverse:
        raise StressFailure(f'adverse ARM governance marker after baseline: {sorted(set(adverse))[-1]}')

    canonical = json.dumps(
        [{'id': int(r.get('id', 0)), 'body': str(r.get('body', ''))} for r in comments],
        sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    ).encode('utf-8')
    return {
        'comment_count': len(comments),
        'latest_comment_id': max(ids) if ids else None,
        'ledger_sha256': sha256(canonical),
        'arm_relevant_comment_ids_after_baseline': arm_relevant,
        'write_quiet_begin_ids_after_baseline': begin_ids,
        'write_quiet_end_ids_after_baseline': end_ids,
        'baseline_coordinator_comment': BASELINE_COORDINATOR_COMMENT,
    }


def validate_workflow(workflow: str) -> None:
    required = (
        'workflow_dispatch:',
        "if: github.event_name == 'workflow_dispatch'",
        'ARM_USER_ID: ${{ secrets.ARM_USER_ID }}',
        'ARM_ACCESS_TOKEN: ${{ secrets.ARM_ACCESS_TOKEN }}',
        'discover.py',
        'query-only-receipt.json',
        'actions/upload-artifact@v4',
        'needs: exact-executable-stress',
    )
    for needle in required:
        if needle not in workflow:
            raise StressFailure(f'workflow missing required dispatch contract: {needle}')
    forbidden = ('continue-on-error', '/saveData', 'netCDF4', '--user-id', '--access-token')
    for needle in forbidden:
        if needle in workflow:
            raise StressFailure(f'workflow contains forbidden query-only surface: {needle}')
    try:
        auth = workflow.split('\n  query-only-discovery:', 1)[1]
    except IndexError:
        raise StressFailure('query-only-discovery job block missing') from None
    checkout_segment = auth.split('- uses: actions/checkout@v4', 1)
    if len(checkout_segment) != 2:
        raise StressFailure('authenticated job checkout missing')
    after_checkout = checkout_segment[1].split('\n      - ', 1)[0]
    if 'ref:' in after_checkout:
        raise StressFailure('authenticated checkout must follow selected dispatch ref; explicit ref rebinding forbidden')


def validate_executable(source: str) -> None:
    for needle in ('/saveData', 'netCDF4', 'urlretrieve(', 'download_native(', 'Dataset('):
        if needle in source:
            raise StressFailure(f'executable contains forbidden native-file capability: {needle}')
    for needle in ('BASE_URL + "/query?"', 'ARM_USER_ID', 'ARM_ACCESS_TOKEN', 'EXPECTED_MANIFEST_SHA256'):
        if needle not in source:
            raise StressFailure(f'executable missing required query-only binding: {needle}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--workflow', type=Path, required=True)
    ap.add_argument('--executable', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()

    if os.environ.get('ARM_USER_ID') or os.environ.get('ARM_ACCESS_TOKEN'):
        raise SystemExit('stress process refuses ARM credentials')
    token = os.environ.get('GITHUB_TOKEN', '').strip()
    if not token:
        raise SystemExit('GITHUB_TOKEN is required for complete #60 readback')

    workflow_b = args.workflow.read_bytes()
    executable_b = args.executable.read_bytes()
    manifest_b = args.manifest.read_bytes()
    if sha256(manifest_b) != EXPECTED_MANIFEST_SHA256:
        raise StressFailure('actual manifest bytes do not match frozen manifest identity')
    manifest = json.loads(manifest_b.decode('utf-8'))
    if manifest.get('purpose') != EXPECTED_PURPOSE or len(manifest.get('ordered_case_ids', [])) != 25:
        raise StressFailure('actual manifest semantic identity/cardinality drift')

    workflow = workflow_b.decode('utf-8')
    executable = executable_b.decode('utf-8')
    validate_workflow(workflow)
    validate_executable(executable)

    event_name = os.environ.get('GITHUB_EVENT_NAME', '')
    ref = os.environ.get('GITHUB_REF', '')
    sha = os.environ.get('GITHUB_SHA', '')
    if event_name not in {'pull_request', 'push', 'workflow_dispatch'}:
        raise StressFailure(f'unexpected stress event: {event_name!r}')
    repo_obj = github_json(f'https://api.github.com/repos/{REPO}', token)
    if repo_obj.get('default_branch') != 'main':
        raise StressFailure('repository default branch drift')
    comments = complete_issue_comments(token)
    gov = audit_arm_governance(comments)

    receipt = {
        'schema': 1,
        'status': 'EXACT_EXECUTABLE_STRESS_PASS',
        'purpose': EXPECTED_PURPOSE,
        'workflow_sha256': sha256(workflow_b),
        'executable_sha256': sha256(executable_b),
        'ordered_case_manifest_sha256': sha256(manifest_b),
        'event_name': event_name,
        'github_ref': ref,
        'github_sha': sha,
        'default_branch': 'main',
        'issue60_comment_count': gov['comment_count'],
        'issue60_latest_comment_id': gov['latest_comment_id'],
        'issue60_ledger_sha256': gov['ledger_sha256'],
        'baseline_coordinator_comment': gov['baseline_coordinator_comment'],
        'arm_relevant_comment_ids_after_baseline': gov['arm_relevant_comment_ids_after_baseline'],
        'write_quiet_begin_ids_after_baseline': gov['write_quiet_begin_ids_after_baseline'],
        'write_quiet_end_ids_after_baseline': gov['write_quiet_end_ids_after_baseline'],
        'arm_network_access_performed': False,
        'arm_credentials_read': False,
        'native_file_download_performed': False,
        'native_file_open_performed': False,
        'protected_sws_sasze_values_read': False,
        'stage_b_authorized': False,
        'mystic_science_authorized': False,
        'production_authorized': False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('EXACT_EXECUTABLE_STRESS_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
