import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / 'experiments/aerosol-family-challenge-v2-r8/execution-candidate'


def load(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)


class R8FailedAuthorizationRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh = load('afc2_r8_failed_recovery_freshness', CAND / 'freshness.py')
        sys.modules['freshness'] = cls.fresh
        cls.ordinal = load('afc2_r8_failed_recovery_ordinal', CAND / 'preauthorization_ordinal.py')
        sys.modules['preauthorization_ordinal'] = cls.ordinal
        cls.surface = load('afc2_r8_failed_recovery_surface', CAND / 'authorization_surface.py')

    def payload(self):
        p = {
            'branches': [
                {'name': 'main', 'commit': {'sha': 'a' * 40}},
                {'name': 'dispatch/other-project-ordinal-31', 'commit': {'sha': 'b' * 40}},
            ],
            'runs': [],
            'artifacts': [],
            'pulls': [],
            'issues': [],
            'issueComments': [],
            'pullReviewComments': [],
            'commitComments': [],
            'issue60Comments': [],
        }

        # Exact retired-undispatched proof for R8 ordinal 32.
        head32 = '3' * 40
        request32 = '4' * 40
        auth32 = self.fresh.authorization_branch(32)
        publisher32 = 'status/aerosol-family-v2-r8-dispatch-publisher-ordinal-32'
        p['branches'].extend([
            {'name': auth32, 'commit': {'sha': head32}},
            {'name': publisher32, 'commit': {'sha': request32}},
        ])
        p['pulls'].append({
            'number': 277,
            'state': 'closed',
            'merged_at': None,
            'head': {'ref': auth32, 'sha': head32},
        })
        p['runs'].extend([
            {
                'id': 32418602755,
                'head_branch': auth32,
                'head_sha': head32,
                'path': self.ordinal.AUTH_REVIEW_WORKFLOW,
                'event': 'pull_request',
                'run_attempt': 1,
                'status': 'completed',
                'conclusion': 'success',
            },
            {
                'id': 32419436160,
                'head_branch': publisher32,
                'head_sha': request32,
                'path': self.ordinal.PUBLISHER_WORKFLOW,
                'event': 'push',
                'run_attempt': 1,
                'status': 'completed',
                'conclusion': 'failure',
            },
        ])
        p['issue60Comments'].extend([
            {
                'id': 1,
                'body': self.fresh.authorization_marker(32, head32, 'a' * 40, 277),
            },
            {
                'id': 2,
                'body': self.ordinal.retired_authorization_marker(32),
            },
        ])

        # Exact preserved failed attempt-1 authorization-review proof for ordinal 33.
        failed33 = '5' * 40
        auth33 = self.fresh.authorization_branch(33)
        history33 = 'history/aerosol-family-challenge-v2-r8-ordinal-33-auth-review-failed-1'
        p['branches'].extend([
            {'name': auth33, 'commit': {'sha': failed33}},
            {'name': history33, 'commit': {'sha': failed33}},
        ])
        p['pulls'].append({
            'number': 280,
            'state': 'closed',
            'merged_at': None,
            'title': 'Authorize AFC2 R8 ordinal 33 pending separate dispatch',
            'body': (
                'Failed attempt preserved. execution key '
                'aerosol-family-challenge-v2-r8:numerical:33. '
                'Ordinal 33 was not allocated and no dispatch occurred.'
            ),
            'head': {'ref': auth33, 'sha': failed33},
        })
        p['runs'].append({
            'id': 32424931223,
            'head_branch': auth33,
            'head_sha': failed33,
            'path': self.ordinal.AUTH_REVIEW_WORKFLOW,
            'event': 'pull_request',
            'run_attempt': 1,
            'status': 'completed',
            'conclusion': 'failure',
        })
        p['issue60Comments'].append({
            'id': 3,
            'body': (
                'AFC2-R8-ORDINAL33-AUTHORIZATION-REVIEW-FAILED-UNALLOCATED\n'
                'ordinal 33 was not allocated; no dispatch or scientific runtime occurred.'
            ),
        })
        return p

    def test_failed_attempt_keeps_ordinal_33_retryable_without_reserving_key(self):
        p = self.payload()
        candidate, observations = self.ordinal.derive_next_global_ordinal(p, 31)
        self.assertEqual(33, candidate)
        self.assertEqual(33, max(row['ordinal'] for row in observations))

        out = self.surface.build_surface(
            p,
            33,
            active_authorization_path_on_main_exists=False,
            candidate_code_paths_on_main_inspected=True,
        )
        self.assertEqual(33, out['nextAvailableScientificOrdinal'])
        self.assertTrue(out['globalCandidateOrdinalValidatedAcrossRetiredGaps'])
        self.assertTrue(out['authorizationBranchReusableAfterFailedReview'])
        self.assertEqual(['5' * 40], out['failedAuthorizationHistoryHeads'])
        self.assertEqual([280], out['failedAuthorizationHistoryPrNumbers'])
        self.assertEqual([32424931223], out['failedAuthorizationHistoryReviewRunIds'])
        self.assertEqual(0, out['candidatePriorScientificRunCount'])
        self.assertEqual(0, out['candidateExecutionKeyPriorUseCount'])
        self.assertEqual(0, out['positiveCandidateClaimsExcludingCurrent'])

    def test_fresh_new_head_for_same_ordinal_passes_monotonic_surface(self):
        p = self.payload()
        auth33 = self.fresh.authorization_branch(33)
        fresh_head = '6' * 40
        p['branches'] = [row for row in p['branches'] if row['name'] != auth33]
        p['branches'].append({'name': auth33, 'commit': {'sha': fresh_head}})
        p['pulls'].append({
            'number': 281,
            'state': 'open',
            'merged_at': None,
            'body': 'Current Draft authorization for ordinal 33.',
            'head': {'ref': auth33, 'sha': fresh_head},
        })
        p['runs'].append({
            'id': 32430000000,
            'head_branch': auth33,
            'head_sha': fresh_head,
            'path': self.ordinal.AUTH_REVIEW_WORKFLOW,
            'event': 'pull_request',
            'run_attempt': 1,
            'status': 'in_progress',
            'conclusion': None,
        })

        out = self.surface.build_surface(
            p,
            33,
            current_pr=281,
            current_run_id=32430000000,
            active_authorization_path_on_main_exists=False,
            candidate_code_paths_on_main_inspected=True,
        )
        self.assertEqual(33, out['nextAvailableScientificOrdinal'])
        self.assertTrue(out['globalCandidateOrdinalValidatedAcrossRetiredGaps'])
        self.assertFalse(out['authorizationBranchReusableAfterFailedReview'])
        self.assertEqual(0, out['candidatePriorScientificRunCount'])
        self.assertEqual(0, out['candidateExecutionKeyPriorUseCount'])
        self.assertEqual(0, out['positiveCandidateClaimsExcludingCurrent'])

    def test_failed_history_requires_exact_closed_attempt1_failure_evidence(self):
        mutations = ('missing-history', 'open-pr', 'successful-review', 'rerun-review')
        for mode in mutations:
            with self.subTest(mode=mode):
                p = self.payload()
                if mode == 'missing-history':
                    p['branches'] = [
                        row for row in p['branches']
                        if not row['name'].startswith('history/aerosol-family-challenge-v2-r8-ordinal-33-')
                    ]
                elif mode == 'open-pr':
                    next(row for row in p['pulls'] if row['number'] == 280)['state'] = 'open'
                elif mode == 'successful-review':
                    next(row for row in p['runs'] if row['id'] == 32424931223)['conclusion'] = 'success'
                else:
                    next(row for row in p['runs'] if row['id'] == 32424931223)['run_attempt'] = 2
                with self.assertRaises(self.ordinal.GlobalOrdinalRefusal):
                    self.ordinal.derive_next_global_ordinal(p, 31)

    def test_failed_head_refuses_allocation_dispatch_or_execution_evidence(self):
        for mode in ('allocation-marker', 'dispatch-branch', 'execution-run'):
            with self.subTest(mode=mode):
                p = self.payload()
                failed33 = '5' * 40
                if mode == 'allocation-marker':
                    p['issue60Comments'].append({
                        'id': 4,
                        'body': self.fresh.authorization_marker(33, failed33, 'a' * 40, 280),
                    })
                elif mode == 'dispatch-branch':
                    p['branches'].append({
                        'name': self.fresh.dispatch_branch(33),
                        'commit': {'sha': failed33},
                    })
                else:
                    p['runs'].append({
                        'id': 32430000001,
                        'head_branch': self.fresh.dispatch_branch(33),
                        'head_sha': failed33,
                        'path': self.ordinal.EXECUTION_WORKFLOW,
                        'event': 'workflow_dispatch',
                        'run_attempt': 1,
                        'status': 'completed',
                        'conclusion': 'failure',
                    })
                with self.assertRaises(self.ordinal.GlobalOrdinalRefusal):
                    self.ordinal.derive_next_global_ordinal(p, 31)

    def test_higher_identity_or_missing_retirement_refuses_candidate_33(self):
        p = self.payload()
        p['branches'].append({
            'name': 'authorization/other-project-ordinal-34',
            'commit': {'sha': '7' * 40},
        })
        with self.assertRaises(self.ordinal.GlobalOrdinalRefusal):
            self.ordinal.validate_current_candidate_global_ordinal(p, 31, 33)

        p = self.payload()
        p['issue60Comments'] = [
            row for row in p['issue60Comments']
            if row['body'] != self.ordinal.retired_authorization_marker(32)
        ]
        with self.assertRaises(self.ordinal.GlobalOrdinalRefusal):
            self.ordinal.derive_next_global_ordinal(p, 31)


if __name__ == '__main__':
    unittest.main()
