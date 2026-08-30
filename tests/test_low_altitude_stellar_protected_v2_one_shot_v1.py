import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github/workflows/low-altitude-stellar-protected-v2-validation-v1-one-shot.yml'


class ProtectedV2OneShotWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WF.read_text(encoding='utf-8')

    def test_exact_fresh_identity(self):
        t=self.text
        self.assertIn('dispatch/low-altitude-stellar-protected-v2-validation-v1-exec001',t)
        self.assertIn('low-altitude-stellar-protected-v2-fresh-cell-centers',t)
        self.assertIn("CANDIDATE_SOURCE_RUN_ID: '33313239384'",t)
        self.assertIn("CANDIDATE_SOURCE_JOB_ID: '99261929321'",t)
        self.assertIn("CANDIDATE_ARTIFACT_ID: '9732635873'",t)
        self.assertIn('low-altitude-stellar-phase-b-training-candidate-v1-exec003',t)
        self.assertIn('4730c4404ef4ee93c07930f5fe8eb391f117cdc84f2c9eff49c5e7ee9f73b72e',t)

    def test_fresh_matrix_and_acceptance_frozen(self):
        t=self.text
        self.assertIn("[0.375,0.625,0.875,1.25,1.75,2.25,2.75,3.25,3.75,4.25,4.75]",t)
        self.assertIn("[250.0,875.0,1625.0,2250.0]",t)
        self.assertIn("[0.075,0.15,0.25,0.35]",t)
        self.assertIn("d['maxAbsDeltaAvMagLimit']==0.025",t)
        self.assertIn("d['rmsDeltaAvMagLimit']==0.010",t)
        self.assertIn("d['globalAndEveryAltitudeCellCenterMustPass'] is True",t)
        self.assertIn("d['minimumSupportedGeometricAltitudeIfPassDeg']==0.25",t)
        self.assertIn("d['exactHorizonSupported'] is False",t)

    def test_one_shot_fail_closed_surface(self):
        t=self.text
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1',t)
        self.assertIn("'githubRerunPermitted':False",t)
        self.assertIn("'solverRetryPermitted':False",t)
        self.assertIn("'solverResumePermitted':False",t)
        self.assertIn("'positiveEpsilonSubstitutionAllowed':False",t)
        self.assertIn("'postResultFloorBackSelectionAuthorized':False",t)
        self.assertIn("'postResultRetuningAuthorized':False",t)
        self.assertIn("'refractionAppliedInRadiativeTransfer':False",t)
        self.assertIn("'mysticState0077ResidualsUsed':False",t)
        self.assertIn("'inadmissibleExec001NumericalResultsUsed':False",t)
        self.assertIn("'taylorOrJerusalemUsed':False",t)
        self.assertNotIn('workflow_dispatch:',t)

    def test_old_inadmissible_chain_absent(self):
        t=self.text
        for forbidden in (
            '33310723749','33311205702','33311467254','9732025874',
            '2ab71a13dee10374d7ebba854bd46cedb61e77d293d0d24804ea75dcd2a33ea3',
            '0.34375','0.59375','0.84375','4.6875'):
            self.assertNotIn(forbidden,t)

    def test_exact_controller_and_geometry_guards(self):
        t=self.text
        self.assertIn('run_protected_v2_validation_v1.py',t)
        self.assertIn("v['solver']=='sdisort' and v['solverGeometry']=='pseudo-spherical'",t)
        self.assertIn("v['refractionAppliedInRadiativeTransfer'] is False",t)
        self.assertIn("v['solverInvocationCount']==176",t)
        self.assertIn("v['freshProtectedJohnsonVComparisonCount']==528",t)
        self.assertIn('test ! -e protected-v2-output',t)


if __name__ == '__main__':
    unittest.main()
