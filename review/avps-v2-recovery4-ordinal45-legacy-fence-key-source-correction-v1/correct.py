#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

OLD = "              if first.startswith('WRITE_QUIET_END') and f.get('begin','').isdigit(): closed.add(int(f['begin']))\n"
NEW = """              if first.startswith('WRITE_QUIET_END'):
                  vals=[]
                  for key in ('begin','beginComment','begin_comment'):
                      v=f.get(key,'')
                      if v.isdigit(): vals.append(int(v))
                  if vals:
                      if len(set(vals))!=1: raise SystemExit(f'conflicting WRITE_QUIET_END begin ids: {vals}')
                      closed.add(vals[0])
"""
EXPECTED_OLD_BLOB = 'df0763b61ce89063de6992bb984dc854024a1aad'


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def parse_closed(first: str) -> set[int]:
    fields: dict[str, str] = {}
    for token in first.replace('|', ' ').split():
        if '=' in token:
            k, v = token.split('=', 1)
            fields[k] = v
    closed: set[int] = set()
    if first.startswith('WRITE_QUIET_END'):
        vals=[]
        for key in ('begin','beginComment','begin_comment'):
            v=fields.get(key,'')
            if v.isdigit(): vals.append(int(v))
        if vals:
            if len(set(vals)) != 1:
                raise ValueError(f'conflicting WRITE_QUIET_END begin ids: {vals}')
            closed.add(vals[0])
    return closed


def self_test() -> None:
    assert parse_closed('WRITE_QUIET_END begin=11 token=x') == {11}
    assert parse_closed('WRITE_QUIET_END beginComment=5463819190 token=x') == {5463819190}
    assert parse_closed('WRITE_QUIET_END begin_comment=5467489757 token=x') == {5467489757}
    assert parse_closed('NOTE WRITE_QUIET_END begin=77') == set()
    try:
        parse_closed('WRITE_QUIET_END begin=1 beginComment=2 token=x')
    except ValueError:
        pass
    else:
        raise AssertionError('conflicting begin keys must fail closed')


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--receipt', type=Path, required=True)
    args=ap.parse_args()
    self_test()
    before=args.input.read_bytes()
    if git_blob(before) != EXPECTED_OLD_BLOB:
        raise SystemExit(f'old workflow blob drift: {git_blob(before)}')
    text=before.decode('utf-8')
    if text.count(OLD) != 1:
        raise SystemExit(f'exact legacy parser anchor cardinality drift: {text.count(OLD)}')
    after=text.replace(OLD, NEW, 1).encode('utf-8')
    if OLD.encode() in after:
        raise SystemExit('legacy begin-only parser remains after correction')
    for token in ("('begin','beginComment','begin_comment')", 'conflicting WRITE_QUIET_END begin ids'):
        if token.encode() not in after:
            raise SystemExit(f'corrected parser token missing: {token}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(after)
    receipt={
        'schemaVersion':1,
        'status':'PASS_AVPS_RECOVERY4_ORDINAL45_LEGACY_WRITE_QUIET_END_KEY_CORRECTION_ZERO_RUNTIME',
        'scientificOrdinal':45,
        'sourcePublicationHead':'fe9d2ffdfc44ba37b9a57f817f97adf5ade99b3c',
        'sourceWorkflowGitBlobSha1':EXPECTED_OLD_BLOB,
        'correctedWorkflowGitBlobSha1':git_blob(after),
        'sourceWorkflowSha256':hashlib.sha256(before).hexdigest(),
        'correctedWorkflowSha256':hashlib.sha256(after).hexdigest(),
        'acceptedEndBindingKeys':['begin','beginComment','begin_comment'],
        'conflictingEndBindingIdsFailClosed':True,
        'laterBodyMentionsIgnored':True,
        'replacementCount':1,
        'frozenScienceChanged':False,
        'seedIdentityChanged':False,
        'authorizationChanged':False,
        'dispatchCreated':False,
        'seedConsumption':False,
        'solverExecution':False,
        'resultsOpened':False,
        'levelBOpeningAuthorized':False,
        'holdoutOpeningAuthorized':False,
        'productionAuthorized':False,
        'taylorOrJerusalemUsed':False,
        'newMappingAuthorized':False,
    }
    args.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
