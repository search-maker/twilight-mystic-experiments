#!/usr/bin/env python3
import hashlib
from pathlib import Path

SOURCE_SCIENCE = Path('.github/workflows/avps-v2-science.yml')
SOURCE_PUBLISHER = Path('.github/workflows/avps-v2-dispatch-publisher.yml')
SOURCE_BRIDGE = Path('.github/workflows/avps-v2-publisher-recovery2-trigger-bridge.yml')
OUT = Path('generated-avps-v2-recovery1')

NEW_SCIENCE = 'avps-v2-postconsumption-recovery1-science.yml'
NEW_PUBLISHER = 'avps-v2-postconsumption-recovery1-dispatch-publisher.yml'
NEW_BRIDGE = 'avps-v2-postconsumption-recovery1-publisher-trigger-bridge.yml'
NEW_AUTH_PATH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-authorization-control-v1/authorization.json'
NEW_SEED_PATH = 'review/aerosol-vertical-profile-sensitivity-v2-postconsumption-seed-freshness-v1/seed_ledger.py'
NEW_SEED_BLOB = '491d1b6653bea0fcc5275269723a76aa1af52300'
NEW_AUTH_BLOB = '4aa103548029a7b8748ad636ae6e3e7e8f69a8d2'

IDENTITY_REPLACEMENTS = [
    ('authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41', 'authorization/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42'),
    ('d5f5e4d9d19d7ede573fecae68565a92baabbec3', 'e627a689ada0493a8a5b9cdafc4aba0198fbabec'),
    ('b3d562222a38fc9d1ff5d218886afdda72c37fa2', 'a68f603d6da21cd28ab8324da080cc8ad27f9094'),
    ("AUTH_PR: '604'", "AUTH_PR: '629'"),
    ("AUTH_REVIEW_RUN: '33218101573'", "AUTH_REVIEW_RUN: '33250602685'"),
    ("AUTH_REVIEW_ARTIFACT: '9704345296'", "AUTH_REVIEW_ARTIFACT: '9714316591'"),
    ('sha256:fdabe0425c3de893866c25f14b0da1e0038a8e6498b83a281fcae0e773e605d4', 'sha256:083d7127a1591810870875d1b6c15f795c1fee0996c1dadaec5838b785bce8c2'),
    ('dispatch/aerosol-vertical-profile-sensitivity-v2-ordinal-41', 'dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42'),
    ('aerosol-vertical-profile-sensitivity-v2:numerical:41', 'aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1:numerical:42'),
    ('ORDINAL41_AVPS_V2_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=d5f5e4d9d19d7ede573fecae68565a92baabbec3 parent=b3d562222a38fc9d1ff5d218886afdda72c37fa2 pr=604', 'ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_AUTHORIZATION_ALLOCATED_REVIEWED_NOT_DISPATCHED commit=e627a689ada0493a8a5b9cdafc4aba0198fbabec parent=a68f603d6da21cd28ab8324da080cc8ad27f9094 pr=629'),
    ('ORDINAL41_AVPS_V2_DISPATCH_CONSUMED', 'ORDINAL42_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_CONSUMED'),
    ('02f624d582e9b2caba6b920d65a5e8a8bc8fc1a2693623bc2f73abf5d3f706d2', 'a514212990a94a39d577bd038b631a600e18e4c0f750f781bbd7c99b897228a7'),
    ('review/aerosol-vertical-profile-sensitivity-v2-authorization-control-v4/authorization.json', NEW_AUTH_PATH),
    ('dcfbd39081abe8e98604eedd48a1d934cea5483a', NEW_AUTH_BLOB),
    ("p['number']!=604", "p['number']!=629"),
    ("'authorizationPr':604", "'authorizationPr':629"),
    ("'scientificOrdinal':41", "'scientificOrdinal':42"),
]


def replace_required(text, old, new, *, at_least=1):
    n = text.count(old)
    if n < at_least:
        raise SystemExit(f'missing required source token: {old!r}')
    return text.replace(old, new)


def apply_identity(text):
    for old, new in IDENTITY_REPLACEMENTS:
        text = replace_required(text, old, new)
    return text


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def generate_science() -> str:
    t = SOURCE_SCIENCE.read_text()
    t = apply_identity(t)
    t = replace_required(t, 'run-name: AVPS v2 ordinal 41 |', 'run-name: AVPS v2 postconsumption recovery1 ordinal 42 |')
    t = replace_required(t, 'group: avps-v2-ordinal-41-science', 'group: avps-v2-postconsumption-recovery1-ordinal-42-science')
    t = replace_required(t, 'actions/workflows/avps-v2-science.yml/runs', f'actions/workflows/{NEW_SCIENCE}/runs')
    t = replace_required(t, "cmp -s execution-preflight/authorization.json " + NEW_AUTH_PATH, 'test "$(git hash-object execution-preflight/authorization.json)" = "' + NEW_AUTH_BLOB + '"')
    marker = "git ls-files -z > execution-preflight/tracked-files.nul\n          python - <<'PY'"
    inserted = (
        "git ls-files -z > execution-preflight/tracked-files.nul\n"
        f"          git show \"$AUTH_HEAD:{NEW_SEED_PATH}\" > execution-preflight/recovery-seed-ledger.py\n"
        f"          test \"$(git hash-object execution-preflight/recovery-seed-ledger.py)\" = \"{NEW_SEED_BLOB}\"\n"
        "          python - <<'PY'"
    )
    t = replace_required(t, marker, inserted)
    t = replace_required(t, "path=Path('review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py')", "path=Path('execution-preflight/recovery-seed-ledger.py')")
    t = replace_required(t, "'status':'EXACT_ONE_USE_AVPS_V2_DISPATCH_AUTHORIZED'", "'status':'EXACT_ONE_USE_AVPS_V2_POSTCONSUMPTION_RECOVERY1_DISPATCH_AUTHORIZED'")
    old_forbidden = ['ordinal 41 |', 'authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41', 'ORDINAL41_AVPS_V2_DISPATCH_CONSUMED']
    for token in old_forbidden:
        if token in t:
            raise SystemExit(f'old science identity remains: {token}')
    return t


def generate_publisher() -> str:
    t = SOURCE_PUBLISHER.read_text()
    t = apply_identity(t)
    t = replace_required(t, 'run-name: AVPS v2 ordinal 41 zero-runtime dispatch publisher', 'run-name: AVPS v2 postconsumption recovery1 ordinal 42 zero-runtime dispatch publisher')
    t = replace_required(t, 'group: avps-v2-ordinal-41-dispatch-publisher', 'group: avps-v2-postconsumption-recovery1-ordinal-42-dispatch-publisher')
    t = replace_required(t, '.github/workflows/avps-v2-science.yml', f'.github/workflows/{NEW_SCIENCE}')
    t = replace_required(t, '.github/workflows/avps-v2-dispatch-publisher.yml', f'.github/workflows/{NEW_PUBLISHER}')
    t = replace_required(t, 'actions/workflows/avps-v2-science.yml/runs', f'actions/workflows/{NEW_SCIENCE}/runs')
    marker = "git ls-files -z > dispatch-evidence/tracked-files.nul\n          python - <<'PY'"
    inserted = (
        "git ls-files -z > dispatch-evidence/tracked-files.nul\n"
        f"          git show \"$AUTH_HEAD:{NEW_SEED_PATH}\" > dispatch-evidence/recovery-seed-ledger.py\n"
        f"          test \"$(git hash-object dispatch-evidence/recovery-seed-ledger.py)\" = \"{NEW_SEED_BLOB}\"\n"
        "          python - <<'PY'"
    )
    t = replace_required(t, marker, inserted)
    t = replace_required(t, "p=Path('review/aerosol-vertical-profile-sensitivity-v2-seed-freshness/seed_ledger.py')", "p=Path('dispatch-evidence/recovery-seed-ledger.py')")
    t = replace_required(t, 'actions/workflows/aerosol-vertical-profile-sensitivity-v2-science-workflow-v1-review.yml/runs', 'actions/workflows/aerosol-vertical-profile-sensitivity-v2-postconsumption-implementation-generator-v1-review.yml/runs')
    t = replace_required(t, '-n avps-v2-science-workflow-v1-review', '-n avps-v2-postconsumption-implementation-generator-v1-review')
    t = replace_required(t, "'status':'PASS_SOLVER_FREE_SCIENCE_WORKFLOW_AND_ZERO_RUNTIME_PUBLISHER_REVIEW_DISPATCH_NOT_CREATED'", "'status':'PASS_AVPS_V2_POSTCONSUMPTION_RECOVERY1_GENERATED_IMPLEMENTATION_REVIEW_DISPATCH_NOT_CREATED'")
    t = replace_required(t, "name: avps-v2-dispatch-publisher-ordinal-41", "name: avps-v2-postconsumption-recovery1-dispatch-publisher-ordinal-42")
    t = replace_required(t, 'actions/workflows/avps-v2-science.yml/dispatches', f'actions/workflows/{NEW_SCIENCE}/dispatches')
    old_payload = 'PAYLOAD=\'{"ref":"main","inputs":{"dispatch_ref":"dispatch/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42"}}\''
    if old_payload not in t:
        raise SystemExit('final publisher payload did not normalize to recovery dispatch ref')
    for token in ['ordinal 41 zero-runtime', 'authorization/aerosol-vertical-profile-sensitivity-v2-ordinal-41', 'ORDINAL41_AVPS_V2_DISPATCH_CONSUMED']:
        if token in t:
            raise SystemExit(f'old publisher identity remains: {token}')
    return t


def generate_bridge(publisher_blob: str) -> str:
    t = SOURCE_BRIDGE.read_text()
    replacements = [
        ('AVPS v2 publisher recovery2 trigger bridge', 'AVPS v2 postconsumption recovery1 publisher trigger bridge'),
        ('AVPS v2 ordinal 41 publisher recovery2 trigger bridge', 'AVPS v2 postconsumption recovery1 ordinal 42 publisher trigger bridge'),
        ('dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-ordinal-41-publisher-recovery2', 'dispatch-trigger/aerosol-vertical-profile-sensitivity-v2-postconsumption-recovery1-ordinal-42-publisher'),
        ('dispatch-triggers/avps-v2-ordinal41-publisher-recovery2.txt', 'dispatch-triggers/avps-v2-postconsumption-recovery1-ordinal42-publisher.txt'),
        ('avps-v2-dispatch-publisher-recovery2.yml', NEW_PUBLISHER),
        ('79317065f4a6019c19fdbf8ab81ea4b4952ef868', publisher_blob),
        ("SCIENTIFIC_ORDINAL: '41'", "SCIENTIFIC_ORDINAL: '42'"),
        ('group: avps-v2-ordinal-41-publisher-recovery2-trigger-bridge', 'group: avps-v2-postconsumption-recovery1-ordinal-42-publisher-trigger-bridge'),
        ('trigger-recovery2', 'trigger-recovery1-ordinal42'),
        ('recovery2-publisher-run-ids.txt', 'recovery1-ordinal42-publisher-run-ids.txt'),
        ('trigger-recovery2-evidence', 'trigger-recovery1-ordinal42-evidence'),
        ('AVPS_V2_PUBLISHER_RECOVERY2_TRIGGER_V1', 'AVPS_V2_POSTCONSUMPTION_RECOVERY1_ORDINAL42_PUBLISHER_TRIGGER_V1'),
        ('RECOVERY2_PRE_TRIGGER_BRIDGE_PASS_ZERO_RUNTIME', 'POSTCONSUMPTION_RECOVERY1_ORDINAL42_PRE_TRIGGER_BRIDGE_PASS_ZERO_RUNTIME'),
        ('RECOVERY2_PUBLISHER_WORKFLOW_DISPATCH_REQUESTED_BY_ZERO_RUNTIME_BRIDGE', 'POSTCONSUMPTION_RECOVERY1_ORDINAL42_PUBLISHER_WORKFLOW_DISPATCH_REQUESTED_BY_ZERO_RUNTIME_BRIDGE'),
        ('recovery2 publisher', 'recovery1 ordinal42 publisher'),
        ('recovery2 pre-trigger', 'recovery1 ordinal42 pre-trigger'),
        ('recovery2 post-trigger', 'recovery1 ordinal42 post-trigger'),
    ]
    for old, new in replacements:
        t = replace_required(t, old, new)
    t = replace_required(t, "'scientificOrdinal':41", "'scientificOrdinal':42")
    if 'ordinal 41' in t or 'recovery2' in t:
        raise SystemExit('old bridge identity remains')
    return t


def main():
    OUT.mkdir(exist_ok=True)
    science = generate_science()
    publisher = generate_publisher()
    publisher_blob = git_blob_sha1(publisher.encode())
    bridge = generate_bridge(publisher_blob)
    files = {NEW_SCIENCE: science, NEW_PUBLISHER: publisher, NEW_BRIDGE: bridge}
    manifest = []
    for name, text in files.items():
        raw = text.encode()
        (OUT / name).write_bytes(raw)
        manifest.append((name, hashlib.sha256(raw).hexdigest(), git_blob_sha1(raw), len(raw)))
    (OUT / 'MANIFEST.tsv').write_text('path\tsha256\tgitBlobSha1\tbytes\n' + ''.join(f'{a}\t{b}\t{c}\t{d}\n' for a,b,c,d in manifest))

if __name__ == '__main__':
    main()
