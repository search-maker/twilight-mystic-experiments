from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/low-altitude-stellar-phase-b-protected-validation-v1-one-shot.yml'


class ProtectedOneShotWorkflowV1Tests(unittest.TestCase):
    def test_exact_candidate_and_frozen_matrix_are_bound(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("CANDIDATE_SOURCE_RUN_ID: '33311205702'", text)
        self.assertIn("CANDIDATE_SOURCE_JOB_ID: '99256463098'", text)
        self.assertIn("CANDIDATE_ARTIFACT_ID: '9732025874'", text)
        self.assertIn("CANDIDATE_ARTIFACT_DIGEST: 'sha256:ce499746ee929bbd5800c70dce56004068bf6d17f964d332dabe306f5bed17a8'", text)
        self.assertIn("CANDIDATE_SOURCE_DISPATCH_SHA: '06d99628d05ec2dbb923fdb500b40673eb086385'", text)
        self.assertIn("CANDIDATE_RUNTIME_SHA256: '2ab71a13dee10374d7ebba854bd46cedb61e77d293d0d24804ea75dcd2a33ea3'", text)
        self.assertIn("'protectedAtmosphericSpectrumCount':176", text)
        self.assertIn("'protectedJohnsonVComparisonCount':528", text)
        self.assertIn("assert d['representativeLibraryNumbers']==[1,26,45]", text)
        self.assertIn("assert d['maxAbsDeltaAvMagLimit']==0.025", text)
        self.assertIn("assert d['rmsDeltaAvMagLimit']==0.010", text)

    def test_attempt_one_no_retry_no_back_selection(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', text)
        self.assertIn("'githubRerunPermitted':False", text)
        self.assertIn("'solverRetryPermitted':False", text)
        self.assertIn("'solverResumePermitted':False", text)
        self.assertIn("'positiveEpsilonSubstitutionAllowed':False", text)
        self.assertIn("'postResultFloorBackSelectionAuthorized':False", text)
        self.assertIn("'postResultRetuningAuthorized':False", text)
        self.assertIn("'taylorOrJerusalemUsed':False", text)
        self.assertNotIn('workflow_dispatch:', text)
        for forbidden in ('AnnArbor.csv', 'Taylor residual', 'Jerusalem residual', 'first-seeing', 'halachic'):
            self.assertNotIn(forbidden, text)

    def test_result_is_published_for_pass_or_fail(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("v['status']=='PROTECTED_VALIDATION_PASS'", text)
        self.assertIn("v['status']=='PROTECTED_VALIDATION_FAIL'", text)
        self.assertIn("v['status']=='PROTECTED_VALIDATION_FAIL_NUMERICALLY_UNRESOLVED'", text)
        self.assertIn('Publish immutable protected decision evidence', text)
        self.assertIn('if: always()', text)
        self.assertIn("assert v['solverInvocationCount']==176", text)
        self.assertIn("assert v['exactHorizonSupported'] is False", text)
        self.assertIn("assert v['applicationSupportChanged'] is False", text)
        self.assertIn("assert v['productionAuthorized'] is False", text)

    def test_refraction_and_empirical_fitting_are_excluded(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn("'refractionAppliedInRadiativeTransfer':False", text)
        self.assertIn("'taylorOrJerusalemUsed':False", text)
        self.assertIn('rte_solver', (ROOT / 'review/low-altitude-stellar-transport-v1/run_phase_b_protected_validation_v1.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
