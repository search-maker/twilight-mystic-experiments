from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PLANNER_PATH = HERE / 'lunar_finite_disk_transfer_kernel_sensitivity.py'
STAGE_ID = 'lunar-finite-disk-transfer-kernel-sensitivity-v1'
NAMESPACE = f'{STAGE_ID}|replacement-case-seed-after-disclosure|sha256-v1'
MIN_SEED = 10_000_000
MAX_EXCLUSIVE = 2_147_483_647
SPAN = MAX_EXCLUSIVE - MIN_SEED
# The originally preregistered contiguous candidate range was disclosed in
# repository metadata before a repository-global freshness proof. It is
# permanently retired from execution. These bounds are a refusal boundary,
# not a replacement seed source.
RETIRED_START = 32_910_001
RETIRED_STOP = 32_910_198
EXPECTED_CASE_COUNT = 198
AUDIT_BATCH_SIZE = 72


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def _load_planner():
    spec = importlib.util.spec_from_file_location('lunar_finite_disk_seed_bound_planner', PLANNER_PATH)
    if spec is None or spec.loader is None:
        raise Refusal('cannot import finite-disk planner')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _case_ids() -> list[str]:
    planner = _load_planner()
    cases = planner.frozen_cases()
    case_ids = [str(row['caseId']) for row in cases]
    if len(case_ids) != EXPECTED_CASE_COUNT or len(set(case_ids)) != EXPECTED_CASE_COUNT:
        raise Refusal('frozen finite-disk case universe drift')
    return case_ids


def derive_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    for case_id in _case_ids():
        counter = 0
        while True:
            material = f'{NAMESPACE}|caseId={case_id}|counter={counter}'
            digest = hashlib.sha256(material.encode()).hexdigest()
            seed = (int(digest[:16], 16) % SPAN) + MIN_SEED
            if RETIRED_START <= seed <= RETIRED_STOP:
                counter += 1
                continue
            if seed not in used:
                break
            counter += 1
        if not MIN_SEED <= seed < MAX_EXCLUSIVE:
            raise Refusal('derived seed escaped scanner-visible signed-32-bit domain')
        used.add(seed)
        rows.append({
            'caseId': case_id,
            'collisionCounter': counter,
            'derivationMaterialSha256': digest,
            'seed': seed,
        })
    if len(rows) != EXPECTED_CASE_COUNT or len(used) != EXPECTED_CASE_COUNT:
        raise Refusal('replacement candidate seed cardinality/uniqueness drift')
    return rows


def audit_batches(seeds: list[int]) -> list[list[int]]:
    if len(seeds) != EXPECTED_CASE_COUNT or len(set(seeds)) != EXPECTED_CASE_COUNT:
        raise Refusal('audit batch source must contain exact unique candidate universe')
    first = seeds[:72]
    second = seeds[72:144]
    third = seeds[144:] + seeds[:18]
    batches = [first, second, third]
    if any(len(batch) != AUDIT_BATCH_SIZE or len(set(batch)) != AUDIT_BATCH_SIZE for batch in batches):
        raise Refusal('72-seed scanner batch construction drift')
    covered = set().union(*(set(batch) for batch in batches))
    if covered != set(seeds):
        raise Refusal('scanner batches do not cover exact candidate universe')
    return batches


def build_ledger() -> dict[str, Any]:
    rows = derive_rows()
    seeds = [int(row['seed']) for row in rows]
    batches = audit_batches(seeds)
    return {
        'schemaVersion': 1,
        'stageId': f'{STAGE_ID}-replacement-candidate-seeds-v1',
        'status': 'CANDIDATE_ONLY_ARTIFACT_ONLY_NOT_APPLIED_NOT_AUTHORIZED',
        'namespace': NAMESPACE,
        'replacementReason': 'original contiguous candidate range was disclosed before repository-global freshness proof',
        'retiredPriorCandidateRangeMayEverExecute': False,
        'derivation': 'seed=(uint64_be(SHA256(namespace|caseId|counter)[0:8]) % (MAX_EXCLUSIVE-MIN_SEED)) + MIN_SEED; reject retired disclosed range; increment counter for retired-range or within-ledger collision',
        'scannerCompatibility': {
            'minimumSeedInclusive': MIN_SEED,
            'maximumSeedExclusive': MAX_EXCLUSIVE,
            'allCandidateSeedsHaveAtLeastSevenDecimalDigits': True,
            'scannerBatchSize': AUDIT_BATCH_SIZE,
            'scannerBatchCount': len(batches),
            'scannerCoverageMethod': 'first72; second72; final54 plus first18 repeated only to satisfy bound 72-seed scanner cardinality',
        },
        'candidateSeedCount': EXPECTED_CASE_COUNT,
        'candidateSeeds': seeds,
        'candidateRows': rows,
        'candidateSeedCanonicalSha256': canonical_sha256(seeds),
        'candidateRowsCanonicalSha256': canonical_sha256(rows),
        'auditBatchCanonicalSha256': [canonical_sha256(batch) for batch in batches],
        'allCollisionCountersNonnegative': all(int(row['collisionCounter']) >= 0 for row in rows),
        'allSeedsOutsideRetiredRange': all(not RETIRED_START <= seed <= RETIRED_STOP for seed in seeds),
        'trackedCandidateSeedLedger': False,
        'candidateSeedFreshnessProven': False,
        'scientificOrdinalAllocated': False,
        'authorizationCreated': False,
        'dispatchCreated': False,
        'candidateSeedsAppliedToCases': False,
        'scientificExecutionAuthorized': False,
        'solverExecutionAuthorized': False,
        'resultOpeningAuthorized': False,
        'productionAuthorized': False,
    }


def validate_ledger() -> dict[str, Any]:
    ledger = build_ledger()
    seeds = ledger['candidateSeeds']
    if len(seeds) != EXPECTED_CASE_COUNT or len(set(seeds)) != EXPECTED_CASE_COUNT:
        raise Refusal('candidate ledger uniqueness drift')
    if not ledger['allSeedsOutsideRetiredRange']:
        raise Refusal('replacement candidate entered retired disclosed range')
    audit_batches(seeds)
    return ledger


if __name__ == '__main__':
    value = validate_ledger()
    print(json.dumps({
        'status': 'PASS_LUNAR_FINITE_DISK_REPLACEMENT_CANDIDATE_LEDGER_DETERMINISTIC_ARTIFACT_ONLY_NOT_AUTHORIZED',
        'candidateSeedCount': value['candidateSeedCount'],
        'candidateSeedCanonicalSha256': value['candidateSeedCanonicalSha256'],
        'candidateRowsCanonicalSha256': value['candidateRowsCanonicalSha256'],
        'auditBatchCanonicalSha256': value['auditBatchCanonicalSha256'],
        'allSeedsOutsideRetiredRange': value['allSeedsOutsideRetiredRange'],
        'trackedCandidateSeedLedger': value['trackedCandidateSeedLedger'],
        'candidateSeedFreshnessProven': value['candidateSeedFreshnessProven'],
    }, sort_keys=True))
