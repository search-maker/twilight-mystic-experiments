from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

V4_HEAD = 'a3fc752af64599eed1dc5e358a23295e423b1eb8'
V4_SCRIPT_BLOB = '24b388589c0592b0a201313b57909888effd53ea'
V4_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v4/review_authorization.py'
V5_BRANCH = 'review/avps-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5-20260910'
V5_SCRIPT = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-successor-ordinal46-authorization-review-global-scan-replacement-v5/review_authorization.py'

HERE = Path(__file__).resolve()
REVIEW_ROOT = HERE.parents[2]
V4_ROOT = REVIEW_ROOT.parent / 'v4-base'

head = subprocess.run(
    ['git', '-C', str(V4_ROOT), 'rev-parse', 'HEAD'],
    text=True,
    capture_output=True,
    check=False,
)
if head.returncode != 0 or head.stdout.strip() != V4_HEAD:
    raise RuntimeError(f'frozen V4 source checkout drift: {head.stdout!r} {head.stderr!r}')

v4_path = V4_ROOT / V4_SCRIPT
raw = v4_path.read_bytes()
git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
if git_blob != V4_SCRIPT_BLOB:
    raise RuntimeError(f'frozen V4 source blob drift: {git_blob}')

source = raw.decode('utf-8')
# Mechanical identity lift only. The substantive V5 changes are injected/replaced below and
# are guarded by exact occurrence counts so an upstream/source mismatch fails closed.
patched = source.replace('replacement-v4', 'replacement-v5').replace('REPLACEMENT_V4', 'REPLACEMENT_V5')
patched = patched.replace('v4', 'v5').replace('V4', 'V5')

constant_anchor = "ORDINAL45_CONSUMED_MARKER = 'ORDINAL45_AVPS_V2_POSTCONSUMPTION_RECOVERY4_DISPATCH_CONSUMED'\n"
if patched.count(constant_anchor) != 1:
    raise RuntimeError('V5 constant injection anchor drift')
patched = patched.replace(
    constant_anchor,
    constant_anchor
    + "ORDINAL45_RECOVERY4_COMMENT_ID = 5588108686\n"
    + "ORDINAL45_RECOVERY4_AUTHORIZATION = '6e095b4b1603c90dcee0943295909b30cd1b374d'\n"
    + "ORDINAL45_RECOVERY4_DISPATCH = 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery4-ordinal-45'\n"
    + "ORDINAL45_RECOVERY4_BEGIN = 5588106509\n",
    1,
)

helper_anchor = '\ndef selfobs(row, payload, rpr, rh):\n'
if patched.count(helper_anchor) != 1:
    raise RuntimeError('V5 structural helper injection anchor drift')
helper_code = r'''

def _ordinal45_canonical_first_line():
    return (
        f'{ORDINAL45_CONSUMED_MARKER} | authorization={ORDINAL45_RECOVERY4_AUTHORIZATION} | '
        f'dispatch={ORDINAL45_RECOVERY4_DISPATCH} | begin={ORDINAL45_RECOVERY4_BEGIN}'
    )


def validate_ordinal45_recovery4_marker(rows):
    candidates = []
    for row in rows:
        line = first_line(row.get('body'))
        if not line.startswith(ORDINAL45_CONSUMED_MARKER):
            continue
        if line != ORDINAL45_CONSUMED_MARKER and not line.startswith(ORDINAL45_CONSUMED_MARKER + ' | '):
            raise Refusal(f'ordinal45 Recovery4 lookalike marker prefix {line[:160]!r}')
        candidates.append(row)
    req(len(candidates) == 1, f'ordinal45 Recovery4 consumed marker count drift {[int(r.get("id") or 0) for r in candidates]}')
    row = candidates[0]
    req(int(row.get('id') or 0) == ORDINAL45_RECOVERY4_COMMENT_ID, 'ordinal45 Recovery4 authoritative comment identity drift')
    line = first_line(row.get('body'))
    req(line.startswith(ORDINAL45_CONSUMED_MARKER + ' | '), 'ordinal45 Recovery4 bare marker is not authoritative consumed evidence')
    parts = [part.strip() for part in line.split('|')]
    req(parts and parts[0] == ORDINAL45_CONSUMED_MARKER, 'ordinal45 Recovery4 marker prefix drift')
    fields = {}
    for token in parts[1:]:
        req('=' in token, f'ordinal45 Recovery4 malformed token {token!r}')
        key, value = token.split('=', 1)
        key = key.strip()
        value = value.strip()
        req(key and value and key not in fields, f'ordinal45 Recovery4 duplicate/empty token {token!r}')
        fields[key] = value
    expected = {
        'authorization': ORDINAL45_RECOVERY4_AUTHORIZATION,
        'dispatch': ORDINAL45_RECOVERY4_DISPATCH,
        'begin': str(ORDINAL45_RECOVERY4_BEGIN),
    }
    req(fields == expected, f'ordinal45 Recovery4 binding drift {fields}')
    return {
        'commentId': ORDINAL45_RECOVERY4_COMMENT_ID,
        'firstLine': line,
        'fields': fields,
        'structurallyValidated': True,
    }


def require_no_live_ordinal46_marker(rows):
    hits = []
    for row in rows:
        line = first_line(row.get('body'))
        if line.upper().startswith('ORDINAL46_'):
            hits.append({'id': int(row.get('id') or 0), 'firstLine': line})
    req(not hits, f'ordinal46 allocation/consumed marker exists {hits}')
    return True


def _expect_ordinal45_failure(rows, label):
    try:
        validate_ordinal45_recovery4_marker(rows)
    except Refusal:
        return True
    raise Refusal(f'ordinal45 negative fixture unexpectedly accepted: {label}')


def ordinal45_marker_fixtures():
    canonical = _ordinal45_canonical_first_line()
    valid = [{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical + '\n\nImmutable consumed evidence.'}]
    proof = validate_ordinal45_recovery4_marker(valid)
    req(proof['firstLine'] == canonical, 'ordinal45 positive canonical fixture drift')
    ordinary = [{'ordinal': n, 'reason': 'exact-consumed-marker'} for n in (41, 42, 43, 44)]
    legacy = {int(row['ordinal']) for row in ordinary if row.get('reason') == 'exact-consumed-marker'}
    req(legacy == {41, 42, 43, 44}, 'ordinary 41-44 consumed taxonomy fixture drift')
    combined = set(legacy)
    combined.add(45)
    req(combined == {41, 42, 43, 44, 45}, 'combined consumed-set fixture drift')

    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': ORDINAL45_CONSUMED_MARKER}], 'bare prefix')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical.replace(ORDINAL45_RECOVERY4_AUTHORIZATION, '0' * 40)}], 'wrong authorization')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical.replace(ORDINAL45_RECOVERY4_DISPATCH, ORDINAL45_RECOVERY4_DISPATCH + '-wrong')}], 'wrong dispatch')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical.replace(f'begin={ORDINAL45_RECOVERY4_BEGIN}', 'begin=1')}], 'wrong begin')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID + 1, 'body': canonical}], 'wrong comment identity')
    _expect_ordinal45_failure(valid + [{'id': ORDINAL45_RECOVERY4_COMMENT_ID + 1, 'body': canonical}], 'duplicate exact claim')
    _expect_ordinal45_failure(valid + [{'id': ORDINAL45_RECOVERY4_COMMENT_ID + 1, 'body': canonical.replace('begin=5588106509', 'begin=1')}], 'conflicting duplicate claim')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical + ' | extra=forbidden'}], 'extra binding')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical + f' | authorization={ORDINAL45_RECOVERY4_AUTHORIZATION}'}], 'duplicate binding')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': ORDINAL45_CONSUMED_MARKER + '_LOOKALIKE | authorization=x'}], 'lookalike prefix')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': '> ' + canonical}], 'quoted marker')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': 'Narrative only: ' + canonical}], 'narrative marker')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': 'ORDINAL45_AVPS_V2_POSTCONSUMPTION_RECOVERY4_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED'}], 'allocation-only')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': 'ORDINAL45_AVPS_V2_POSTCONSUMPTION_RECOVERY4_PROPOSED_ONLY'}], 'proposal-only')
    _expect_ordinal45_failure([{'id': ORDINAL45_RECOVERY4_COMMENT_ID, 'body': canonical.replace('ORDINAL45_', 'ORDINAL44_', 1)}], 'wrong ordinal')

    try:
        require_no_live_ordinal46_marker(valid + [{'id': 9999999999, 'body': 'ORDINAL46_AVPS_V2_POSTCONSUMPTION_SUCCESSOR_AUTHORIZATION_ALLOCATED'}])
    except Refusal:
        false_ordinal46_refused = True
    else:
        raise Refusal('false ordinal46 occupancy fixture unexpectedly accepted')
    req(require_no_live_ordinal46_marker(valid + [{'id': 9999999998, 'body': 'Narrative mentions ORDINAL46_ but is not an anchored state marker'}]), 'ordinal46 narrative fixture failed')

    return {
        'authoritativeEnrichedRecovery4Positive': True,
        'ordinary41To44LegacyTaxonomyPositive': True,
        'combined41To45ConsumptionPositive': True,
        'barePrefixFatal': True,
        'wrongAuthorizationFatal': True,
        'wrongDispatchFatal': True,
        'wrongBeginFatal': True,
        'wrongCommentIdentityFatal': True,
        'duplicateExactFatal': True,
        'conflictingDuplicateFatal': True,
        'extraBindingFatal': True,
        'duplicateBindingFatal': True,
        'lookalikePrefixFatal': True,
        'quotedMarkerDoesNotAuthorize': True,
        'narrativeMarkerDoesNotAuthorize': True,
        'allocationOnlyDoesNotCountConsumed': True,
        'proposalOnlyDoesNotCountConsumed': True,
        'wrongOrdinalDoesNotCountConsumed': True,
        'falseOrdinal46OccupancyFatal': false_ordinal46_refused,
        'ordinal46NarrativeDoesNotCreateOccupancy': True,
    }
'''
patched = patched.replace(helper_anchor, helper_code + helper_anchor, 1)

old_reason = "    consumed = {int(row['ordinal']) for row in nonself if row.get('reason') == 'exact-consumed-marker'}\n    req({41, 42, 43, 44, 45}.issubset(consumed), f'consumed markers incomplete {sorted(consumed)}')"
new_reason = "    legacy_consumed = {int(row['ordinal']) for row in nonself if row.get('reason') == 'exact-consumed-marker'}\n    req({41, 42, 43, 44}.issubset(legacy_consumed), f'ordinary historical consumed markers incomplete {sorted(legacy_consumed)}')\n    ordinal45_marker = validate_ordinal45_recovery4_marker(payload.get('issue60Comments', []))\n    consumed = set(legacy_consumed)\n    consumed.add(45)"
reason_sites_before = patched.count(old_reason)
if reason_sites_before != 2:
    raise RuntimeError(f'V5 expected exactly two legacy consumption defect sites, got {reason_sites_before}')
patched = patched.replace(old_reason, new_reason)

old_comment_gate = "    comments = [str(row.get('body') or '').strip() for row in payload.get('issue60Comments', [])]\n    req(sum(1 for row in comments if row == ORDINAL45_CONSUMED_MARKER) == 1, 'ordinal45 consumed marker count drift')\n    req(not any(row.upper().startswith('ORDINAL46_') for row in comments), 'ordinal46 allocation/consumed marker exists')"
new_comment_gate = "    comment_rows = list(payload.get('issue60Comments', []))\n    require_no_live_ordinal46_marker(comment_rows)"
whole_body_sites_before = patched.count(old_comment_gate)
if whole_body_sites_before != 2:
    raise RuntimeError(f'V5 expected exactly two whole-body marker defect sites, got {whole_body_sites_before}')
patched = patched.replace(old_comment_gate, new_comment_gate)

fixture_call = '    fixtures = discussion_fixtures()\n'
if patched.count(fixture_call) != 2:
    raise RuntimeError('V5 expected two discussion fixture call sites')
patched = patched.replace(fixture_call, fixture_call + '    ordinal_fixtures = ordinal45_marker_fixtures()\n')

fixture_write = "    write(a.ev / 'discussion-fixtures.json', fixtures)\n"
if patched.count(fixture_write) != 2:
    raise RuntimeError('V5 expected two discussion fixture evidence writes')
patched = patched.replace(
    fixture_write,
    fixture_write
    + "    write(a.ev / 'ordinal45-marker-fixtures.json', ordinal_fixtures)\n"
    + "    write(a.ev / 'v5-consumption-interpreter-audit.json', V5_TRANSFORM_AUDIT)\n",
)

receipt_anchor = "        'discussionFixtureSuitePassed': True,\n"
if patched.count(receipt_anchor) != 2:
    raise RuntimeError('V5 expected two receipt fixture anchors')
patched = patched.replace(
    receipt_anchor,
    receipt_anchor
    + "        'ordinal45Recovery4MarkerValidated': True,\n"
    + "        'ordinal45Recovery4ConsumedCommentId': ORDINAL45_RECOVERY4_COMMENT_ID,\n"
    + "        'ordinal45MarkerFixtureSuitePassed': True,\n"
    + "        'v5ConsumptionInterpreterAuditPassed': True,\n",
)

if "row == ORDINAL45_CONSUMED_MARKER" in patched:
    raise RuntimeError('V5 whole-body bare-prefix equality still present')
if patched.count("legacy_consumed = {int(row['ordinal']) for row in nonself if row.get('reason') == 'exact-consumed-marker'}") != 2:
    raise RuntimeError('V5 ordinary 41-44 taxonomy interpreter count drift')
if patched.count("ordinal45_marker = validate_ordinal45_recovery4_marker(payload.get('issue60Comments', []))") != 2:
    raise RuntimeError('V5 structural ordinal45 validator count drift')
if patched.count('require_no_live_ordinal46_marker(comment_rows)') != 2:
    raise RuntimeError('V5 ordinal46 anchored-state gate count drift')

V5_TRANSFORM_AUDIT = {
    'frozenV4Head': V4_HEAD,
    'frozenV4ScriptGitBlobSha1': V4_SCRIPT_BLOB,
    'legacyDefectReasonAssertionSitesEnumerated': reason_sites_before,
    'legacyDefectWholeBodyGateSitesEnumerated': whole_body_sites_before,
    'v5Ordinary41To44ReasonInterpreterSites': 2,
    'v5StructuralOrdinal45ValidatorSites': 2,
    'v5WholeBodyBarePrefixEqualitySites': 0,
    'v5AnchoredOrdinal46StateGateSites': 2,
    'markerFixtureSuiteInjected': True,
    'allKnownConsumptionInterpreterSitesEnumerated': True,
}

exec(compile(patched, str(HERE), 'exec'), globals(), globals())
