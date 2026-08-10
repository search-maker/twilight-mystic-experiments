#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path('/mnt/data')
READINESS = ROOT / 'full-spectrum-training-acquisition-readiness-v1.json'
PILOT = ROOT / 'full-spectrum-estimator-pilot-preregistration-v2.json'
EXECUTION = ROOT / 'full-spectrum-estimator-pilot-execution-manifest-v4.json'
OUTPUT = ROOT / 'full-spectrum-estimator-pilot-seed-collision-audit-v4.json'
SEED_RE = re.compile(r'^\s*mc_randomseed\s+(\d+)\s*$', re.MULTILINE)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    return sha256_bytes(payload)

readiness = json.loads(READINESS.read_text())
pilot = json.loads(PILOT.read_text())
execution = json.loads(EXECUTION.read_text())
if execution.get('protocolSha256') != pilot.get('protocolSha256'):
    raise SystemExit('pilot/execution protocol binding drift')
p_by={c['caseId']:c for c in pilot['cases']}
e_by={c['caseId']:c for c in execution['cases']}
if set(p_by)!=set(e_by):
    raise SystemExit('pilot/execution case-id universe drift')
for cid,pc in p_by.items():
    ec=e_by[cid]
    for key in ('geometryId','method','replicate','seed','photonHistories'):
        if pc.get(key)!=ec.get(key): raise SystemExit(f'pilot/execution case binding drift: {cid}.{key}')
    if pc.get('importanceCenterNm')!=ec.get('numericalMethod',{}).get('mc_spectral_is_nm'):
        raise SystemExit(f'pilot/execution importance-center drift: {cid}')
worklist = readiness['worklist']

# The training ledger is authoritative for the exact expected 166 geometry/block identities.
identities = []
seen = set()
for row in worklist:
    key = (row['geometryId'], int(row['block']))
    if key in seen:
        raise SystemExit(f'duplicate expected source identity: {key}')
    seen.add(key)
    identities.append((key, row))
if len(identities) != 166:
    raise SystemExit(f'expected 166 source identities, got {len(identities)}')

source_rows = []
missing = []
for (geometry_id, block), meta in identities:
    zip_path = ROOT / f'{geometry_id}-b{block}.zip'
    if not zip_path.is_file():
        missing.append(str(zip_path))
        continue
    zip_raw = sha256_file(zip_path)
    expected_digest = meta.get('githubZipDigest')
    digest_matches = None if not expected_digest else zip_raw == expected_digest.removeprefix('sha256:')
    with zipfile.ZipFile(zip_path) as zf:
        matches = [n for n in zf.namelist() if Path(n).name == 'input-resolved.txt']
        if len(matches) != 1:
            raise SystemExit(f'{zip_path.name}: expected one input-resolved.txt, found {matches}')
        input_bytes = zf.read(matches[0])
    text = input_bytes.decode('utf-8')
    seed_matches = SEED_RE.findall(text)
    if len(seed_matches) != 1:
        raise SystemExit(f'{zip_path.name}: expected one mc_randomseed, got {seed_matches}')
    seed = int(seed_matches[0])
    source_rows.append({
        'geometryId': geometry_id,
        'block': block,
        'sourceWave': meta.get('sourceWave'),
        'sourceRunId': meta.get('sourceRunId'),
        'sourceRunAttempt': meta.get('sourceRunAttempt'),
        'artifactId': meta.get('artifactId'),
        'artifactName': meta.get('artifactName'),
        'githubZipDigest': expected_digest,
        'localZipPath': str(zip_path),
        'localZipSha256': zip_raw,
        'githubZipDigestMatch': digest_matches,
        'inputResolvedMember': matches[0],
        'inputResolvedSha256': sha256_bytes(input_bytes),
        'seed': seed,
    })

if missing:
    raise SystemExit('missing expected source ZIPs: ' + ', '.join(missing))
if len(source_rows) != 166:
    raise SystemExit(f'parsed {len(source_rows)} source rows')

source_seeds = [r['seed'] for r in source_rows]
source_seed_counts = Counter(source_seeds)
source_seed_duplicates = sorted(seed for seed, n in source_seed_counts.items() if n > 1)

candidate_rows = [{
    'caseId': c['caseId'],
    'geometryId': c['geometryId'],
    'method': c['method'],
    'replicate': c['replicate'],
    'seed': c['seed'],
    'photonHistories': c['photonHistories'],
    **({'importanceCenterNm': c['importanceCenterNm']} if 'importanceCenterNm' in c else {}),
} for c in pilot['cases']]
candidate_seeds = [r['seed'] for r in candidate_rows]
candidate_seed_counts = Counter(candidate_seeds)
candidate_duplicates = sorted(seed for seed, n in candidate_seed_counts.items() if n > 1)
intersection = sorted(set(source_seeds).intersection(candidate_seeds))

historical_case_tokens = {f'{r["geometryId"]}-b{r["block"]}' for r in source_rows}
candidate_case_ids = [r['caseId'] for r in candidate_rows]
case_id_duplicates = sorted(k for k, n in Counter(candidate_case_ids).items() if n > 1)
case_token_collision = sorted(set(candidate_case_ids).intersection(historical_case_tokens))

known_digest_count = sum(r['githubZipDigest'] is not None for r in source_rows)
known_digest_mismatch = [r['localZipPath'] for r in source_rows if r['githubZipDigestMatch'] is False]

body = {
    'schemaVersion': 1,
    'auditId': 'public-tier1-full-spectrum-estimator-pilot-seed-collision-audit-v4',
    'status': 'PASSED_LOCAL_EXACT_166_SOURCE_SEED_AUDIT',
    'sourceLedgerId': readiness['sourceLedgerId'],
    'sourceLedgerSha256': readiness['sourceLedgerSha256'],
    'sourceReadinessRawSha256': sha256_file(READINESS),
    'pilotProtocolId': pilot['protocolId'],
    'pilotProtocolSha256': pilot['protocolSha256'],
    'pilotPreregistrationRawSha256': sha256_file(PILOT),
    'executionManifestId': execution['manifestId'],
    'executionManifestSha256': execution['manifestSha256'],
    'executionManifestRawSha256': sha256_file(EXECUTION),
    'exactSourceUniverse': {
        'expectedCaseCount': 166,
        'observedCaseCount': len(source_rows),
        'uniqueGeometryBlockIdentityCount': len(seen),
        'allExpectedSourceZipsPresent': True,
        'knownGithubZipDigestCount': known_digest_count,
        'knownGithubZipDigestMismatchCount': len(known_digest_mismatch),
        'knownGithubZipDigestMismatches': known_digest_mismatch,
        'sourceSeedCount': len(source_seeds),
        'sourceUniqueSeedCount': len(source_seed_counts),
        'sourceDuplicateSeeds': source_seed_duplicates,
        'sourceSeedMinimum': min(source_seeds),
        'sourceSeedMaximum': max(source_seeds),
    },
    'candidateUniverse': {
        'candidateCaseCount': len(candidate_rows),
        'candidateSeedCount': len(candidate_seeds),
        'candidateUniqueSeedCount': len(candidate_seed_counts),
        'candidateDuplicateSeeds': candidate_duplicates,
        'candidateSeedMinimum': min(candidate_seeds),
        'candidateSeedMaximum': max(candidate_seeds),
        'preregisteredCandidateSeedRange': pilot['candidateSeedRange'],
        'candidateCaseIdDuplicates': case_id_duplicates,
    },
    'collisionResults': {
        'sourceCandidateSeedIntersection': intersection,
        'sourceCandidateSeedIntersectionCount': len(intersection),
        'candidateCaseIdHistoricalGeometryBlockTokenIntersection': case_token_collision,
        'candidateCaseIdHistoricalGeometryBlockTokenIntersectionCount': len(case_token_collision),
        'localExactSourceCollisionAuditPassed': not source_seed_duplicates and not candidate_duplicates and not intersection and not case_id_duplicates and not case_token_collision,
    },
    'sourceCases': sorted(source_rows, key=lambda r: (r['geometryId'], r['block'])),
    'candidateCases': candidate_rows,
    'repositorySearchEvidence': {
        'exact970001CodeSearchResults': 0,
        'mcRandomseed9700CodeSearchResults': 0,
        'exact970001PullRequestSearchResults': 0,
        'note': 'Connector searches were performed before this audit. Numeric substring searches for 97000/97004 produced only radiance-value false positives, not seed declarations. This is supplemental evidence, not a substitute for the exact 166 raw-input audit.',
    },
    'limitations': [
        'This audit proves zero seed collision against the exact 166 source case inputs in the frozen training ledger and checks selected committed-repository/PR search surfaces.',
        'It does not prove absence from every expired or unrelated GitHub Actions artifact among the repository-wide historical artifact universe; a separate preauthorization run-history/artifact duplicate guard must remain mandatory.',
        'It does not authorize a solver execution, fitting, holdout opening, Tier-2, or production use.',
    ],
    'authorizationPermitted': False,
    'solverExecutionPerformed': False,
    'scientificExecutionAuthorized': False,
    'fittingAuthorized': False,
    'holdoutOpeningAuthorized': False,
    'tier2Authorized': False,
    'productionAuthorization': False,
}
body['sourceCasesCanonicalSha256'] = canonical_hash(body['sourceCases'])
body['candidateCasesCanonicalSha256'] = canonical_hash(body['candidateCases'])
body['auditSha256'] = canonical_hash({k:v for k,v in body.items() if k != 'auditSha256'})
OUTPUT.write_text(json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
print(json.dumps({
    'status': body['status'],
    'sourceCount': len(source_rows),
    'sourceUniqueSeeds': len(source_seed_counts),
    'candidateCount': len(candidate_rows),
    'candidateUniqueSeeds': len(candidate_seed_counts),
    'intersection': intersection,
    'knownGithubDigests': known_digest_count,
    'knownDigestMismatches': len(known_digest_mismatch),
    'auditSha256': body['auditSha256'],
    'rawSha256': sha256_file(OUTPUT),
}, indent=2))
