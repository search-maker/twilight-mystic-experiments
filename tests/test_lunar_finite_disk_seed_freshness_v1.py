from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1'
LEDGER_PATH = HERE / 'lunar_finite_disk_seed_ledger.py'
PROOF_PATH = HERE / 'build_lunar_finite_disk_seed_freshness_proof.py'


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class LunarFiniteDiskSeedFreshnessV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger_mod = load_module('lunar_fd_seed_ledger_tested', LEDGER_PATH)
        cls.proof_mod = load_module('lunar_fd_seed_proof_tested', PROOF_PATH)
        cls.ledger = cls.ledger_mod.validate_ledger()

    def test_replacement_candidates_are_deterministic_unique_and_outside_retired_range(self):
        again = self.ledger_mod.validate_ledger()
        self.assertEqual(self.ledger['candidateSeedCount'], 198)
        self.assertEqual(self.ledger['candidateSeedCanonicalSha256'], again['candidateSeedCanonicalSha256'])
        self.assertEqual(self.ledger['candidateRowsCanonicalSha256'], again['candidateRowsCanonicalSha256'])
        seeds = self.ledger['candidateSeeds']
        self.assertEqual(len(seeds), 198)
        self.assertEqual(len(set(seeds)), 198)
        self.assertTrue(all(10_000_000 <= seed < 2_147_483_647 for seed in seeds))
        self.assertTrue(all(not self.ledger_mod.RETIRED_START <= seed <= self.ledger_mod.RETIRED_STOP for seed in seeds))
        self.assertFalse(self.ledger['retiredPriorCandidateRangeMayEverExecute'])
        self.assertFalse(self.ledger['trackedCandidateSeedLedger'])
        self.assertFalse(self.ledger['candidateSeedFreshnessProven'])
        self.assertFalse(self.ledger['scientificExecutionAuthorized'])
        self.assertFalse(self.ledger['solverExecutionAuthorized'])
        self.assertFalse(self.ledger['resultOpeningAuthorized'])
        self.assertFalse(self.ledger['productionAuthorized'])

    def test_bound_72_seed_scanner_batches_cover_all_198_candidates(self):
        seeds = self.ledger['candidateSeeds']
        batches = self.ledger_mod.audit_batches(seeds)
        self.assertEqual(len(batches), 3)
        self.assertTrue(all(len(batch) == 72 and len(set(batch)) == 72 for batch in batches))
        self.assertEqual(set().union(*(set(batch) for batch in batches)), set(seeds))
        self.assertEqual(set(batches[0]) & set(batches[1]), set())
        self.assertEqual(set(batches[1]) & set(batches[2]), set())
        self.assertEqual(set(batches[0]) & set(batches[2]), set(batches[0][:18]))

    def test_rows_bind_one_candidate_to_each_frozen_directional_case(self):
        rows = self.ledger['candidateRows']
        self.assertEqual(len(rows), 198)
        self.assertEqual(len({row['caseId'] for row in rows}), 198)
        self.assertEqual(len({row['seed'] for row in rows}), 198)
        self.assertTrue(all(isinstance(row['derivationMaterialSha256'], str) and len(row['derivationMaterialSha256']) == 64 for row in rows))
        self.assertTrue(all(isinstance(row['collisionCounter'], int) and row['collisionCounter'] >= 0 for row in rows))

    def _tracked_report(self):
        return {
            'candidateSeedCount': 72,
            'trackedTreeExternalCollisionCount': 0,
            'exactHeadTrackedTreeByteScanPassed': True,
            'requiredSelfLedgerPathsPresent': True,
            'selfLedgerHitCount': 0,
        }

    def _global_report(self, head: str):
        return {
            'auditMode': 'review-freeze',
            'candidateSeedCount': 72,
            'repositoryGlobalCollisionCount': 0,
            'repositoryGlobalCollisionSurfaceScanPassed': True,
            'repositoryGlobalDoubleEnumerationStable': True,
            'auditedBranchHeadMatchesRepositoryHead': True,
            'repositoryHeadExpected': head,
            'auditedBranchHeadShaObserved': head,
            'priorReviewProofArtifactCount': 0,
            'reviewProofIdentityFresh': True,
            'repositoryGlobalPostFenceCandidateSeedCollisionCount': 0,
            'repositoryGlobalStableContextSha256': '1' * 64,
            'repositoryGlobalSnapshotFenceSha256': '2' * 64,
            'repositoryGlobalPostFenceArrivalCounts': {},
        }

    def test_combined_proof_requires_all_three_clean_batches_and_remains_review_only(self):
        head = 'a' * 40
        proof = self.proof_mod.build(
            [self._tracked_report() for _ in range(3)],
            [self._global_report(head) for _ in range(3)],
            head,
        )
        self.assertEqual(proof['status'], 'PASS_REPLACEMENT_CANDIDATE_SEEDS_FRESH_REVIEW_ONLY_NOT_ALLOCATED')
        self.assertEqual(proof['candidateSeedCount'], 198)
        self.assertEqual(proof['scannerCoverageUniqueCandidateCount'], 198)
        self.assertEqual(proof['auditBatchCount'], 3)
        self.assertEqual(proof['auditBatchSize'], 72)
        self.assertTrue(proof['scannerCoverageIncludes18IntentionalRepeatedCandidatesInFinalBatch'])
        self.assertTrue(proof['allSeedsOutsideRetiredDisclosedRange'])
        self.assertFalse(proof['retiredPriorCandidateRangeMayEverExecute'])
        self.assertFalse(proof['candidateSeedsTrackedInGit'])
        self.assertFalse(proof['candidateSeedsAppliedToCases'])
        self.assertFalse(proof['scientificOrdinalAllocated'])
        self.assertFalse(proof['authorizationCreated'])
        self.assertFalse(proof['dispatchCreated'])
        self.assertFalse(proof['scientificExecutionAuthorized'])
        self.assertFalse(proof['solverExecutionAuthorized'])
        self.assertFalse(proof['resultOpeningAuthorized'])
        self.assertFalse(proof['productionAuthorized'])
        self.assertTrue(proof['authorizationTimeRepositoryGlobalRecheckRequired'])

    def test_any_collision_or_head_mismatch_fails_closed(self):
        head = 'b' * 40
        global_reports = [self._global_report(head) for _ in range(3)]
        global_reports[1]['repositoryGlobalCollisionCount'] = 1
        with self.assertRaises(self.proof_mod.Refusal):
            self.proof_mod.build([self._tracked_report() for _ in range(3)], global_reports, head)

        global_reports = [self._global_report(head) for _ in range(3)]
        global_reports[2]['auditedBranchHeadMatchesRepositoryHead'] = False
        with self.assertRaises(self.proof_mod.Refusal):
            self.proof_mod.build([self._tracked_report() for _ in range(3)], global_reports, head)


if __name__ == '__main__':
    unittest.main()
