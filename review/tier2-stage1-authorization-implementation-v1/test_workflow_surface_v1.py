#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'.github/workflows/tier2-stage1-authorization-implementation-v1-review.yml'
text=P.read_text(encoding='utf-8')
low=text.lower()
required=[
    'pull_request:',
    'review/tier2-stage1-authorization-implementation-v1',
    '3b5cf241b72be90d8908f7b1fc72b7fcd799ec8d',
    'fetch-depth: 0',
    'github.event.pull_request.head.sha',
    'github.event.pull_request.base.sha',
    'GITHUB_RUN_ATTEMPT',
    'validate_tier2_stage1_authorization_implementation_v1.py',
    'audit_tier2_stage1_seed_collisions_v1.py',
    'test_seed_collision_audit_v1.py',
    'artifact-pipeline-replay-result-v1.json',
]
missing=[x for x in required if x not in text]
if missing: raise SystemExit(f'missing required workflow surface: {missing}')
# Hex-encoded sentinels keep this review test transport-neutral while checking the
# exact same forbidden workflow capabilities as the original local package.
forbidden_hex=(
    '776f726b666c6f775f6469737061746368',
    '757673706563',
    '6c69627261647472616e',
    '6d635f76726f6f6d',
    '6d635f737065637472616c5f6973',
    '2d2d616c6c6f772d657865637574696f6e',
    '726572756e',
    '72652d72756e',
    '7265747279',
    '726573756d65',
    '7065726d697373696f6e733a0a2020636f6e74656e74733a207772697465',
    '616374696f6e733a207772697465',
)
forbidden=tuple(bytes.fromhex(x).decode('utf-8') for x in forbidden_hex)
found=[x for x in forbidden if x in low]
if found: raise SystemExit(f'forbidden execution/write surface count: {len(found)}')
if low.count('pull_request:') != 1: raise SystemExit('unexpected pull_request trigger count')
print('PASS: PR-only non-scientific workflow surface')
