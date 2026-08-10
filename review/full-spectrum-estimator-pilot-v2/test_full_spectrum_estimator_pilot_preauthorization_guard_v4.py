from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('guard_v4', ROOT / 'full_spectrum_estimator_pilot_preauthorization_guard_v4.py')
assert spec and spec.loader
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

C = json.loads((ROOT / 'full-spectrum-estimator-pilot-preauthorization-contract-v4.json').read_text())
E = json.loads((ROOT / 'full-spectrum-estimator-pilot-execution-manifest-v4.json').read_text())
R = json.loads((ROOT / 'rendered-review-v5/renderer-review-report.json').read_text())
STATIC_HASHES = {k: v['rawSha256'] for k, v in C['staticFiles'].items()}
CI = C['reviewPackageCiContract']


def context() -> dict:
    return {
        'schemaVersion': 1,
        'mode': 'PRE_AUTHORIZATION',
        'issue60': {'latestDirectiveToken': 'MYSTIC-STATE-0066', 'supersedingDirectivePresent': False},
        'publication': {
            'packagePublished': True,
            'reviewPrNumber': 109,
            'reviewHeadSha': 'a' * 40,
            'reviewBaseMainSha': 'b' * 40,
            'liveMainSha': 'b' * 40,
            'publishedFileRawSha256': STATIC_HASHES,
        },
        'reviewPackageCi': {
            'headSha': 'a' * 40,
            'workflowPath': CI['workflowPath'],
            'jobName': CI['jobName'],
            'workflowRunAttempt': 1,
            'workflowConclusion': 'success',
            'packageCompileStepConclusion': 'success',
            'packageTestsStepConclusion': 'success',
            'packageTestCount': CI['expectedTestCount'],
            'packageTestModules': CI['testModules'],
            'checkRunnerRawSha256': CI['checkRunnerRawSha256'],
            'scientificExecutionPerformed': False,
        },
        'collisionRecheck': {
            'executionKeyCodeCollisionCount': 0,
            'executionKeyIssueCollisionCount': 0,
            'executionKeyPrCollisionCount': 0,
            'authorizationBranchHistoricalRunCount': 0,
            'dispatchBranchHistoricalRunCount': 0,
            'exactCaseArtifactCount': 0,
            'terminalArtifactCount': 0,
            'authorizationBranchCurrentExists': False,
            'dispatchBranchCurrentExists': False,
        },
        'globalOrdinalRecheck': {
            'candidateOrdinal': 14,
            'latestConsumedScientificOrdinal': 13,
            'nextAvailableScientificOrdinal': 14,
            'candidateOrdinalReservationCount': 0,
            'candidateOrdinalAuthorizationCount': 0,
            'candidateOrdinalScientificRunCount': 0,
            'candidateOrdinalAuthorizationBranchCount': 0,
            'candidateOrdinalDispatchBranchCount': 0,
            'candidateOrdinalTerminalArtifactCount': 0,
            'completeReviewedExecutionSurfaceInspected': True,
        },
        'seedRecheck': {
            'historicalSourceCount': 166,
            'historicalUniqueSeedCount': 166,
            'candidateSeedCount': 44,
            'candidateUniqueSeedCount': 44,
            'sourceCandidateSeedIntersectionCount': 0,
            'sourceCandidateSeedIntersection': [],
            'executionManifestSha256': E['manifestSha256'],
        },
        'runtimeIdentity': E['runtimeIdentityRequired'],
        'rendererRecheck': {
            'reportSha256': R['reportSha256'],
            'casesCanonicalSha256': R['casesCanonicalSha256'],
            'caseCount': 44,
            'allPhysicalFingerprintsMatchHistorical': True,
            'allRenderedInputHashesMatchReport': True,
            'executionManifestSha256': E['manifestSha256'],
        },
        'candidateIdentity': C['candidateIdentity'],
        'authorizationCommit': None,
    }


class T(unittest.TestCase):
    def test_static_and_pre_auth_ready_is_structural_only(self):
        out = guard.evaluate(context())
        self.assertIn('READY_TO_CREATE', out['status'])
        self.assertFalse(out['scientificExecutionAuthorized'])
        self.assertFalse(out['dispatchPermitted'])

    def test_directive_refused(self):
        x = context(); x['issue60']['latestDirectiveToken'] = 'MYSTIC-STATE-0067'; x['issue60']['supersedingDirectivePresent'] = True
        with self.assertRaises(guard.Refusal): guard.evaluate(x)

    def test_main_move_refused(self):
        x = context(); x['publication']['liveMainSha'] = 'c' * 40
        with self.assertRaisesRegex(guard.Refusal, 'live main moved'): guard.evaluate(x)

    def test_seed_refused(self):
        x = context(); x['seedRecheck']['sourceCandidateSeedIntersectionCount'] = 1; x['seedRecheck']['sourceCandidateSeedIntersection'] = [970001]
        with self.assertRaises(guard.Refusal): guard.evaluate(x)

    def test_runtime_refused(self):
        x = context(); x['runtimeIdentity'] = dict(x['runtimeIdentity']); x['runtimeIdentity']['uvspecSha256'] = '0' * 64
        with self.assertRaisesRegex(guard.Refusal, 'runtime identity mismatch'): guard.evaluate(x)

    def test_static_analysis_tamper_refused(self):
        x = context(); x['publication']['publishedFileRawSha256'] = dict(STATIC_HASHES); x['publication']['publishedFileRawSha256']['analysis'] = '0' * 64
        with self.assertRaisesRegex(guard.Refusal, 'published review-head file hashes'): guard.evaluate(x)

    def test_global_ordinal_advanced_refused(self):
        x = context(); x['globalOrdinalRecheck']['latestConsumedScientificOrdinal'] = 14; x['globalOrdinalRecheck']['nextAvailableScientificOrdinal'] = 15
        with self.assertRaises(guard.Refusal): guard.evaluate(x)

    def test_global_ordinal_reservation_or_execution_refused(self):
        for key in ('candidateOrdinalReservationCount', 'candidateOrdinalAuthorizationCount', 'candidateOrdinalScientificRunCount', 'candidateOrdinalTerminalArtifactCount'):
            x = context(); x['globalOrdinalRecheck'][key] = 1
            with self.subTest(key=key), self.assertRaises(guard.Refusal): guard.evaluate(x)

    def test_ci_must_match_exact_review_head_runner_and_test_universe(self):
        mutations = (
            ('headSha', 'c' * 40),
            ('workflowRunAttempt', 2),
            ('packageTestCount', CI['expectedTestCount'] - 1),
            ('checkRunnerRawSha256', '0' * 64),
            ('scientificExecutionPerformed', True),
        )
        for key, value in mutations:
            x = context(); x['reviewPackageCi'][key] = value
            with self.subTest(key=key), self.assertRaises(guard.Refusal): guard.evaluate(x)
        x = context(); x['reviewPackageCi']['packageTestModules'] = x['reviewPackageCi']['packageTestModules'][:-1]
        with self.assertRaises(guard.Refusal): guard.evaluate(x)

    def test_post_auth_requires_exact_parent_and_one_file(self):
        base = {
            'sha': 'c' * 40,
            'parentSha': 'a' * 40,
            'branch': C['candidateIdentity']['authorizationBranch'],
            'merged': False,
            'authorizationOrdinal': 14,
            'executionKey': C['candidateIdentity']['executionKey'],
            'scientificPayloadChanged': False,
        }
        x = context(); x['mode'] = 'POST_AUTHORIZATION_COMMIT'; x['authorizationCommit'] = {**base, 'changedFiles': ['experiments/full-spectrum-estimator-pilot-v2/authorization.json', 'README.md']}
        with self.assertRaises(guard.Refusal): guard.evaluate(x)
        x = context(); x['mode'] = 'POST_AUTHORIZATION_COMMIT'; x['authorizationCommit'] = {**base, 'changedFiles': ['experiments/full-spectrum-estimator-pilot-v2/authorization.json']}
        out = guard.evaluate(x)
        self.assertIn('STRUCTURALLY_VALID', out['status'])
        self.assertFalse(out['dispatchPermitted'])


if __name__ == '__main__':
    unittest.main()
