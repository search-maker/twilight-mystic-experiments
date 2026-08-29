#!/usr/bin/env python3
import hashlib
from pathlib import Path

SCIENCE_SRC = Path('.github/workflows/avps-v2-science.yml')
PUBLISHER_SRC = Path('.github/workflows/avps-v2-dispatch-publisher.yml')
BRIDGE_SRC = Path('.github/workflows/avps-v2-publisher-recovery2-trigger-bridge.yml')
OUT = Path('generated-avps-v2-recovery1')

SCIENCE_OUT = 'avps-v2-postconsumption-recovery1-science.yml'
PUBLISHER_OUT = 'avps-v2-postconsumption-recovery1-dispatch-publisher.yml'
BRIDGE_OUT = 'avps-v2-postconsumption-recovery1-publisher-trigger-bridge.yml'
AUTH_PATH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-authorization-control-v1/authorization.json'
SEED_PATH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py'
AUTH_BLOB = '4aa103548029a7b8748ad636ae6e3e7e8f69a8d2'
SEED_BLOB = '491d1b6653bea0fcc5275269723a76aa1af52300'

OLD_ALLOCATION = 'ORDINAL41_AVPS_V2_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=d5f5e4d9d19d7ede573fecae68565a92baabbec3 parent=b3d562222a38fc9d1ff5d218886afdda72c37fa2 pr=604'
NEW_ALLOCATION = 'ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=e627a689ada0493a8a5b9cdafc4aba0198fbabec parent=a68f603d6da21cd28ab8324da080cc8ad27f9094 pr=629'
OLD_AUTH_BRANCH = 'authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41'
NEW_AUTH_BRANCH = 'authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42'
OLD_AUTH_HEAD = 'd5f5e4d9d19d7ede573fecae68565a92baabbec3'
NEW_AUTH_HEAD = 'e627a689ada0493a8a5b9cdafc4aba0198fbabec'
OLD_AUTH_PARENT = 'b3d562222a38fc9d1ff5d218886afdda72c37fa2'
NEW_AUTH_PARENT = 'a68f603d6da21cd28ab8324da080cc8ad27f9094'
OLD_DISPATCH = 'dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41'
NEW_DISPATCH = 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42'
OLD_KEY = 'aerosol-vertical-profile-sensitivity-v2:numerical:41'
NEW_KEY = 'aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42'
OLD_CONSUMED = 'ORDINAL41_AVPS_V2_DISPATCH_CONSUMED'
NEW_CONSUMED = 'ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED'
OLD_SEED = '02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2'
NEW_SEED = 'a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7'


def must(text: str, old: str, new: str) -> str:
    if old not in text:
        raise SystemExit(f'missing required source token: {old!r}')
    return text.replace(old, new)


def identity(text: str) -> str:
    # Replace composite values before their component SHAs so exact-source
    # assertions remain deterministic rather than becoming self-invalidating.
    pairs = [
        (OLD_ALLOCATION, NEW_ALLOCATION),
        (OLD_AUTH_BRANCH, NEW_AUTH_BRANCH),
        (OLD_AUTH_HEAD, NEW_AUTH_HEAD),
        (OLD_AUTH_PARENT, NEW_AUTH_PARENT),
        ("AUTH_PR: '604'", "AUTH_PR: '629'"),
        ("AUTH_REVIEW_RUN: '33218101573'", "AUTH_REVIEW_RUN: '33250602685'"),
        ("AUTH_REVIEW_ARTIFACT: '9704345296'", "AUTH_REVIEW_ARTIFACT: '9714316591'"),
        ('sha256:fdabe0425c3de893866c25f14b0da1e0038a8e6498b83a281fcae0e773e605d4', 'sha256:083d7127a1591810870875d1b6c15f795c1fee0996c1dadaec5838b785bce8c2'),
        (OLD_DISPATCH, NEW_DISPATCH),
        (OLD_KEY, NEW_KEY),
        (OLD_CONSUMED, NEW_CONSUMED),
        (OLD_SEED, NEW_SEED),
    ]
    for old, new in pairs:
        text = must(text, old, new)
    return text


def blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def science() -> str:
    t = identity(SCIENCE_SRC.read_text())
    t = must(t, 'run-name: AVPS v2 ordinal 41 |', 'run-name: AVPS v2 postconsumption recovery1 ordinal 42 |')
    t = must(t, 'group: avps-v2-ordinal-41-science', 'group: avps-v2-postconsumption-recovery1-ordinal-42-science')
    t = must(t, 'actions/workflows/avps-v2-science.yml/runs', f'actions/workflows/{SCIENCE_OUT}/runs')
    t = must(t, 'review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json', AUTH_PATH)
    t = must(t, 'dcfbd39081abe8e98604eedd48a1d934cea5483a', AUTH_BLOB)
    t = must(t, f'cmp -s execution-preflight/authorization.json {AUTH_PATH}', f'test "$(git hash-object execution-preflight/authorization.json)" = "{AUTH_BLOB}"')
    t = must(t, "p['number']!=604", "p['number']!=629")
    t = must(t, "'scientificOrdinal':41", "'scientificOrdinal':42")
    t = must(t, "'authorizationPr':604", "'authorizationPr':629")
    t = must(t, "'status':'EXACT_ONE_USE_AVPS_V2_DISPATCH_AUTHORIZED'", "'status':'EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_AUTHORIZED'")
    marker = "git ls-files -z > execution-preflight/tracked-files.nul\n          python - <<'PY'"
    inserted = (
        "git ls-files -z > execution-preflight/tracked-files.nul\n"
        f"          git show \"$AUTH_HEAD:{SEED_PATH}\" > execution-preflight/recovery-seed-ledger.py\n"
        f"          test \"$(git hash-object execution-preflight/recovery-seed-ledger.py)\" = \"{SEED_BLOB}\"\n"
        "          python - <<'PY'"
    )
    t = must(t, marker, inserted)
    t = must(t, "path=Path('review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py')", "path=Path('execution-preflight/recovery-seed-ledger.py')")
    forbidden = [OLD_AUTH_BRANCH, OLD_DISPATCH, OLD_CONSUMED, OLD_SEED, "'scientificOrdinal':41"]
    for token in forbidden:
        if token in t:
            raise SystemExit(f'old science identity remains: {token}')
    return t


def publisher() -> str:
    t = identity(PUBLISHER_SRC.read_text())
    t = must(t, 'run-name: AVPS v2 ordinal 41 zero-runtime dispatch publisher', 'run-name: AVPS v2 postconsumption recovery1 ordinal 42 zero-runtime dispatch publisher')
    t = must(t, 'group: avps-v2-ordinal-41-dispatch-publisher', 'group: avps-v2-postconsumption-recovery1-ordinal-42-dispatch-publisher')
    t = must(t, '.github/workflows/avps-v2-science.yml', f'.github/workflows/{SCIENCE_OUT}')
    t = must(t, '.github/workflows/avps-v2-dispatch-publisher.yml', f'.github/workflows/{PUBLISHER_OUT}')
    t = must(t, 'actions/workflows/avps-v2-science.yml/runs', f'actions/workflows/{SCIENCE_OUT}/runs')
    t = must(t, "p['number']!=604", "p['number']!=629")
    t = must(t, "'authorizationPr':604", "'authorizationPr':629")
    t = must(t, "'scientificOrdinal':41", "'scientificOrdinal':42")
    marker = "git ls-files -z > dispatch-evidence/tracked-files.nul\n          python - <<'PY'"
    inserted = (
        "git ls-files -z > dispatch-evidence/tracked-files.nul\n"
        f"          git show \"$AUTH_HEAD:{SEED_PATH}\" > dispatch-evidence/recovery-seed-ledger.py\n"
        f"          test \"$(git hash-object dispatch-evidence/recovery-seed-ledger.py)\" = \"{SEED_BLOB}\"\n"
        "          python - <<'PY'"
    )
    t = must(t, marker, inserted)
    t = must(t, "p=Path('review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py')", "p=Path('dispatch-evidence/recovery-seed-ledger.py')")
    t = must(t, 'actions/workflows/aerosol-vertical-profile-sensitivity-v2-science-workflow-v1-review.yml/runs', 'actions/workflows/aerosol-vertical-profile-sensitivity-v2-postconsumption-implementation-generator-v1-review.yml/runs')
    t = must(t, '-n avps-v2-science-workflow-v1-review', '-n avps-v2-postconsumption-implementation-generator-v1-review')
    t = must(t, "'status':'PASS_SOLVER_FREE_SCIENCE_WORKFLOW_AND_ZERO_RUNTIME_PUBLISHER_REVIEW_DISPATCH_NOT_CREATED'", "'status':'PASS_AVPS_V2_POSTCONSUMPTION_RECOVERY1_GENERATED_IMPLEMENTATION_REVIEW_DISPATCH_NOT_CREATED'")
    t = must(t, 'name: avps-v2-dispatch-publisher-ordinal-41', 'name: avps-v2-postconsumption-recovery1-dispatch-publisher-ordinal-42')
    t = must(t, 'actions/workflows/avps-v2-science.yml/dispatches', f'actions/workflows/{SCIENCE_OUT}/dispatches')
    forbidden = [OLD_AUTH_BRANCH, OLD_DISPATCH, OLD_CONSUMED, OLD_SEED, "'scientificOrdinal':41"]
    for token in forbidden:
        if token in t:
            raise SystemExit(f'old publisher identity remains: {token}')
    return t


def bridge(publisher_blob: str) -> str:
    t = BRIDGE_SRC.read_text()
    replacements = [
        ('avps-v2-dispatch-publisher-recovery2.yml', PUBLISHER_OUT),
        ('79317065f4a6019c19fdbf8ab81ea4b4952ef868', publisher_blob),
        ('dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-ordinal-41-publisher-recovery2', 'dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42-publisher'),
        ('dispatch-triggers/avps-v2-ordinal41-publisher-recovery2.txt', 'dispatch-triggers/avps-v2-postconsumption-recovery1-ordinal42-publisher.txt'),
        ("SCIENTIFIC_ORDINAL: '41'", "SCIENTIFIC_ORDINAL: '42'"),
        ("'scientificOrdinal':41", "'scientificOrdinal':42"),
    ]
    for old, new in replacements:
        t = must(t, old, new)
    t = t.replace('ordinal 41', 'postconsumption recovery1 ordinal 42')
    t = t.replace('recovery2', 'postconsumption-recovery1-ordinal42')
    if 'ordinal 41' in t or 'recovery2' in t or "SCIENTIFIC_ORDINAL: '41'" in t:
        raise SystemExit('old bridge identity remains')
    return t


def main():
    OUT.mkdir(exist_ok=True)
    s = science()
    p = publisher()
    b = bridge(blob_sha1(p.encode()))
    generated = {SCIENCE_OUT: s, PUBLISHER_OUT: p, BRIDGE_OUT: b}
    rows = []
    for name, text in generated.items():
        raw = text.encode()
        (OUT / name).write_bytes(raw)
        rows.append((name, hashlib.sha256(raw).hexdigest(), blob_sha1(raw), len(raw)))
    (OUT / 'MANIFEST.tsv').write_text('path\tsha256\tgitBlobSha1\tbytes\n' + ''.join(f'{a}\t{b}\t{c}\t{d}\n' for a,b,c,d in rows))

if __name__ == '__main__':
    main()
