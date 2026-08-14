#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECOVERY = ROOT / 'review/level-b-v2-densified58-fresh-validation-recovery-v2/recovery-v2.json'
CONTRACT_V2 = ROOT / 'review/level-b-v2-densified58-fresh-validation-recovery-v2/contract-v2.json'
CORE = ROOT / 'review/level-b-v2-densified58-fresh-validation-recovery-v2/fresh_validation_v2.py'
MANIFEST = ROOT / 'experiments/level-b-v2-densified58-fresh-validation-recovery-v2/build_manifest_v2.py'
BASE_CONTRACT = ROOT / 'review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json'
ADAPTER = ROOT / 'experiments/level-b-v2-densified58-fresh-validation-v1/adapter_v1.py'
BASE_EXECUTOR = ROOT / 'experiments/level-b-v2-densified58-fresh-validation-v1/executor_v1.py'
VERSIONED_EXECUTOR = ROOT / 'experiments/level-b-v2-densified58-fresh-validation-recovery-v2/executor_v2.py'


def mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = mod('fresh_validation_recovery_v2_test', CORE)
manifest_mod = mod('fresh_validation_recovery_manifest_v2_test', MANIFEST)
adapter = mod('fresh_validation_adapter_v1_reuse_test', ADAPTER)
base_executor = mod('fresh_validation_executor_v1_regression_test', BASE_EXECUTOR)
versioned_executor = mod('fresh_validation_executor_v2_recovery_test', VERSIONED_EXECUTOR)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recovery = json.loads(RECOVERY.read_text(encoding='utf-8'))
        cls.contract_v2 = json.loads(CONTRACT_V2.read_text(encoding='utf-8'))
        cls.base = json.loads(BASE_CONTRACT.read_text(encoding='utf-8'))
        cls.contract = core.effective_contract(cls.recovery, ROOT)

    def test_frozen_science_subtrees_are_byte_semantically_unchanged(self):
        for key in ('authorization','boundaries','failureSemantics','geometrySelection','modelAndEvaluation','runtimeIdentityRequired','sourceBindings'):
            self.assertEqual(self.contract[key], self.base[key], key)
        base_env = copy.deepcopy(self.base['executionEnvelope'])
        new_env = copy.deepcopy(self.contract['executionEnvelope'])
        for env in (base_env, new_env):
            env.pop('candidateScientificOrdinal')
            env.pop('reservedSeeds')
            env.pop('scientificOrdinalAllocated')
        self.assertEqual(new_env, base_env)

    def test_ordinal25_identity_and_fresh_seed_order(self):
        rows = core.expected_cases(self.contract, self.recovery, ROOT)
        self.assertEqual(self.contract['executionEnvelope']['candidateScientificOrdinal'], 25)
        self.assertEqual([row['seed'] for row in rows], list(range(2101000025, 2101000049)))
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({row['caseId'] for row in rows}), 24)
        self.assertTrue(all(row['caseId'].startswith('v0070-o25-holdout-') for row in rows))
        self.assertEqual([row['block'] for row in rows[:4]], [1,2,3,4])

    def test_versioned_executor_is_exact_ordinal25_guard(self):
        self.assertEqual(base_executor.BRANCH_RE.pattern, r'^dispatch/level-b-v2-densified58-fresh-validation-ordinal[1-9][0-9]*-v1$')
        self.assertIsNone(base_executor.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal24-v3'))
        self.assertEqual(versioned_executor.BASE_EXECUTOR_GIT_BLOB_SHA, '5bf0477f0d5100dcb73da8027233e8415ce9021c')
        self.assertEqual(versioned_executor.BRANCH_RE.pattern, r'^dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1$')
        self.assertIsNotNone(versioned_executor.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1'))
        self.assertIsNone(versioned_executor.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal24-v3'))
        self.assertIsNone(versioned_executor.BRANCH_RE.fullmatch('dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v2'))

    def test_versioned_recovery_contract_binds_only_identity_transport_change(self):
        c = self.contract_v2
        self.assertEqual((c['schemaVersion'], c['contractId'], c['governance']), (2, 'level-b-v2-densified58-fresh-protected-validation-v2-ordinal25-recovery', 'MYSTIC-STATE-0070'))
        self.assertEqual(c['baseScientificContract']['gitBlobSha'], 'aad11350311ce3768488e64ed72edc3e48646ff9')
        self.assertEqual(c['scientificIdentityCandidate']['scientificOrdinal'], 25)
        self.assertEqual(c['scientificIdentityCandidate']['reservedSeeds'], list(range(2101000025,2101000049)))
        self.assertFalse(c['scientificIdentityCandidate']['allocated'])
        self.assertFalse(c['scientificIdentityCandidate']['consumed'])
        self.assertEqual(c['versionedExecutionSurface']['executorPath'], 'experiments/level-b-v2-densified58-fresh-validation-recovery-v2/executor_v2.py')
        self.assertEqual(c['versionedExecutionSurface']['exactAllowedDispatchBranch'], 'dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1')
        self.assertTrue(all(v is False for v in c['closedBoundaries'].values()))

    def test_manifest_reuses_adapter_contract_and_is_review_only(self):
        manifest = manifest_mod.build(ROOT, self.recovery)
        adapter.validate_manifest(manifest)
        self.assertEqual(manifest['schemaVersion'], 2)
        self.assertEqual(manifest['manifestId'], 'level-b-v2-densified58-fresh-validation-execution-manifest-v1')
        self.assertEqual((manifest['geometryCount'],manifest['caseCount'],manifest['configuredPhotonHistories']), (6,24,960_000_000))
        self.assertEqual([case['seed'] for case in manifest['cases']], list(range(2101000025,2101000049)))
        self.assertEqual(manifest['scientificOrdinalCandidate'], 25)
        self.assertFalse(manifest['ordinal24ProtectedValuesRead'])
        self.assertEqual(manifest['ordinal24SolverExecutionCount'], 0)
        self.assertFalse(manifest['closedUntilAuthorization']['scientificOrdinalAllocated'])
        self.assertFalse(manifest['closedUntilAuthorization']['protectedHoldoutOpeningAuthorized'])
        self.assertFalse(manifest['closedUntilAuthorization']['holdoutValuesMayBeRead'])
        self.assertFalse(manifest['closedUntilAuthorization']['scientificSolverExecutionAuthorized'])
        body = copy.deepcopy(manifest)
        got = body['manifestSha256']
        body['manifestSha256'] = None
        self.assertEqual(got, manifest_mod.canon(body))

    def test_recovery_records_ordinal24_as_consumed_but_scientifically_unopened(self):
        prior = self.recovery['ordinal24DispatchRefusal']
        self.assertTrue(prior['scientificIdentityConsumed'])
        self.assertTrue(prior['priorSeedsRetired'])
        self.assertEqual(prior['dispatchRunId'], 31840757436)
        self.assertEqual(prior['caseJobCount'], 24)
        self.assertEqual(prior['terminalCaseFailureCount'], 24)
        self.assertEqual(prior['syntaxCheckCount'], 0)
        self.assertEqual(prior['solverExecutionCount'], 0)
        self.assertFalse(prior['protectedValuesRead'])
        self.assertEqual(prior['evaluationConclusion'], 'skipped')

    def test_recovery_binds_versioned_executor_instead_of_reusing_executor_identity(self):
        vr = self.recovery['versionedRecoveryBindings']
        self.assertEqual(vr['contractGitBlobSha'], '1370e53bd33cff442be9c4525e7a7dcb7710084f')
        self.assertEqual(vr['executorGitBlobSha'], '661f3c3bf4fef94c46eca096fd059f1a124a8e3c')
        self.assertEqual(vr['exactAllowedDispatchBranch'], 'dispatch/level-b-v2-densified58-fresh-validation-ordinal25-v1')
        self.assertNotIn('sameExecutorBlob', self.recovery['frozenScience'])
        self.assertTrue(self.recovery['frozenScience']['baseExecutorScientificLogicReused'])
        self.assertTrue(self.recovery['frozenScience']['executorVersionedOnlyForDispatchIdentityGuard'])

    def test_review_surface_remains_inert(self):
        self.assertTrue(all(value is False for value in self.recovery['reviewSurface'].values()))
        self.assertFalse(self.contract['executionEnvelope']['scientificOrdinalAllocated'])
        self.assertFalse(self.contract['boundaries']['protectedValidationAuthorized'])
        self.assertFalse(self.contract['boundaries']['protectedValuesMayBeRead'])
        self.assertFalse(self.contract['boundaries']['scientificSolverExecutionAuthorized'])


if __name__ == '__main__':
    unittest.main()
