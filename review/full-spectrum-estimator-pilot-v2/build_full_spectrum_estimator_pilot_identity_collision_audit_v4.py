#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OLD = ROOT / 'full-spectrum-estimator-pilot-identity-collision-audit-v3.json'
EXEC = ROOT / 'full-spectrum-estimator-pilot-execution-manifest-v4.json'
SEED = ROOT / 'full-spectrum-estimator-pilot-seed-collision-audit-v4.json'
OUT = ROOT / 'full-spectrum-estimator-pilot-identity-collision-audit-v4.json'

def canon(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def raw(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

o = json.loads(OLD.read_text())
e = json.loads(EXEC.read_text())
s = json.loads(SEED.read_text())
body = {k: v for k, v in o.items() if k != 'auditSha256'}
body['auditId'] = 'public-tier1-full-spectrum-estimator-pilot-identity-collision-audit-v4'
body['executionManifestRawSha256'] = raw(EXEC)
body['executionManifestSelfHash'] = e['manifestSha256']
body['seedCollisionAuditRawSha256'] = raw(SEED)
body['seedCollisionAuditSelfHash'] = s['auditSha256']
body['status'] = 'CANDIDATE_IDENTITY_CLEAR_ON_REVIEWED_SURFACES_NOT_RESERVED'
body['manifestHardeningNote'] = (
    'Execution manifest v4 closes the raw-evidence member contract and seed audit v4 binds the complete '
    '166/166 historical seed universe. Candidate ordinal/key/ref/title are unchanged. This remains a '
    'review-time negative collision audit only; a complete fresh collision/run-history recheck is mandatory '
    'immediately before any authorization.'
)
body['auditSha256'] = canon(body)
OUT.write_text(json.dumps(body, indent=2, sort_keys=True, allow_nan=False) + '\n')
print(json.dumps({'auditSha256': body['auditSha256'], 'rawSha256': raw(OUT), 'candidate': body['candidateIdentity']}, indent=2))
