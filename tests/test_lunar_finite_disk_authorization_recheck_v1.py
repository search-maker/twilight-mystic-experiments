from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'build_lunar_finite_disk_authorization_recheck_proof.py'
CONTRACT = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar-finite-disk-authorization-recheck-v1.json'

spec = importlib.util.spec_from_file_location('test_lunar_fd_auth_builder', BUILDER)
if spec is None or spec.loader is None:
    raise SystemExit('cannot import authorization recheck builder')
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

contract = json.loads(CONTRACT.read_text())
parent = contract['parentState']
head = 'a' * 40
prior = {
    'status': parent['seedFreshnessProofStatus'],
    'auditedHead': parent['seedFreshnessReviewHead'],
    'candidateSeedCount': parent['candidateSeedCount'],
    'candidateSeedCanonicalSha256': parent['candidateSeedCanonicalSha256'],
    'candidateRowsCanonicalSha256': parent['candidateRowsCanonicalSha256'],
    'repositoryGlobalCollisionCount': 0,
    'repositoryGlobalDoubleEnumerationStableAllBatches': True,
    'authorizationTimeRepositoryGlobalRecheckRequired': True,
    'candidateSeedsAppliedToCases': False,
    'solverExecutionAuthorized': False,
}

def global_report(i: int) -> dict:
    return {
        'auditMode': 'authorization-recheck',
        'candidateSeedCount': 72,
        'repositoryGlobalCollisionCount': 0,
        'repositoryGlobalCollisionSurfaceScanPassed': True,
        'repositoryGlobalDoubleEnumerationStable': True,
        'auditedBranchHeadMatchesRepositoryHead': True,
        'repositoryHeadExpected': head,
        'auditedBranchHeadShaObserved': head,
        'repositoryGlobalPostFenceCandidateSeedCollisionCount': 0,
        'repositoryGlobalStableContextSha256': f'{i:064x}',
        'repositoryGlobalSnapshotFenceSha256': f'{i+10:064x}',
        'repositoryGlobalPostFenceArrivalCounts': {},
    }

reports = [global_report(i) for i in range(1, 4)]
proof = mod.build(prior, reports, head)
assert proof['status'] == 'PASS_AUTHORIZATION_TIME_REPOSITORY_GLOBAL_SEED_RECHECK_ZERO_RUNTIME'
assert proof['candidateSeedCount'] == 198
assert proof['scannerCoverageUniqueCandidateCount'] == 198
assert proof['candidateSeedCanonicalSha256'] == parent['candidateSeedCanonicalSha256']
assert proof['candidateRowsCanonicalSha256'] == parent['candidateRowsCanonicalSha256']
assert proof['candidateSeedState'] == 'AUTHORIZATION_RECHECK_PASSED_STILL_UNAPPLIED'
assert proof['candidateSeedsAppliedToCases'] is False
assert proof['scientificExecutionAuthorizationCreated'] is False
assert proof['solverExecutionAuthorized'] is False
assert proof['solverExecuted'] is False
assert proof['resultOpeningAuthorized'] is False
assert proof['resultOpened'] is False
assert proof['finiteDiskAdequacyClaimed'] is False
assert proof['productionAuthorized'] is False

bad = deepcopy(prior)
bad['candidateSeedCanonicalSha256'] = '0' * 64
try:
    mod.build(bad, reports, head)
except mod.Refusal:
    pass
else:
    raise AssertionError('candidate seed hash drift must fail closed')

bad_reports = deepcopy(reports)
bad_reports[1]['repositoryGlobalCollisionCount'] = 1
bad_reports[1]['repositoryGlobalCollisionSurfaceScanPassed'] = False
try:
    mod.build(prior, bad_reports, head)
except mod.Refusal:
    pass
else:
    raise AssertionError('authorization-time collision must fail closed')

bad_reports = deepcopy(reports)
bad_reports[2]['auditMode'] = 'review-freeze'
try:
    mod.build(prior, bad_reports, head)
except mod.Refusal:
    pass
else:
    raise AssertionError('wrong audit mode must fail closed')

bad_reports = deepcopy(reports)
bad_reports[0]['auditedBranchHeadShaObserved'] = 'b' * 40
try:
    mod.build(prior, bad_reports, head)
except mod.Refusal:
    pass
else:
    raise AssertionError('branch movement must fail closed')

protected = contract['protectedBoundaries']
assert all(protected[key] is False for key in protected)
print('PASS lunar finite-disk authorization recheck v1 contract')
