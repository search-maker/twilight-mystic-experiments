from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'air-lusi-toa-validation-contract-v1.json'


class LunarToaAirLusiValidationContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_reference_identity_is_frozen(self):
        c = self.c
        self.assertEqual(c['contractId'], 'lunar-rolo311g-air-lusi-toa-validation-v1')
        self.assertEqual(c['referenceDataset']['doi'], '10.18434/mds2-3397')
        self.assertEqual(c['referenceDataset']['githubRepository'], 'usnistgov/air-lusi')
        self.assertEqual(c['referenceDataset']['githubMainCommitObservedAtFreeze'], '91f100a161bdf4205c8bbfef5dd5c30e33cbe995')
        self.assertEqual(c['referenceDataset']['gitLfsOidSha256'], 'ab428b8e91ca02cbcd4f154cb5e524dada87514447bb3384af318d255bb9459a')
        self.assertEqual(c['referenceDataset']['gitLfsSizeBytes'], 471191)
        self.assertEqual(c['referenceDataset']['wavelengthScale'], 'vacuum')

    def test_residual_blind_all_case_admission(self):
        admission = self.c['sourceAdmission']
        self.assertTrue(admission['resultBlindSelection'])
        self.assertTrue(admission['manualCaseDroppingForbidden'])
        self.assertIn('ALL_FOUR_PUBLIC_2022_CAMPAIGN_SPECTRA', admission['caseSelection'])
        self.assertIn('dataset-authored quality/validity flags', admission['qualityExclusions'])
        self.assertIn('absolute geometric phase angle', admission['phaseConvention'])

    def test_no_fit_and_no_posthoc_threshold(self):
        model = self.c['modelUnderTest']
        self.assertTrue(model['noParameterRefit'])
        self.assertTrue(model['noMultiplicativeScaleFit'])
        self.assertTrue(model['noSpectralShapeFit'])
        plan = self.c['comparisonPlan']
        self.assertEqual(plan['absoluteScaleFitting'], 'FORBIDDEN')
        self.assertEqual(plan['spectralTiltFitting'], 'FORBIDDEN')
        self.assertEqual(plan['phaseOrLibrationFitting'], 'FORBIDDEN')
        self.assertIsNone(plan['passFailThreshold'])
        self.assertIn('before inspecting these residuals', plan['thresholdPolicy'])

    def test_known_upstream_issues_are_not_silently_ignored(self):
        issues = {x['githubIssue']: x for x in self.c['upstreamKnownIssuesFrozenBeforeNumericComparison']}
        self.assertIn('usnistgov/air-lusi#5', issues)
        self.assertIn('usnistgov/air-lusi#4', issues)
        self.assertIn('divide by distance_correction_factor', issues['usnistgov/air-lusi#5']['rule'])
        self.assertIn('0.46-0.57 degree', issues['usnistgov/air-lusi#4']['rule'])
        self.assertTrue(issues['usnistgov/air-lusi#5']['mustRemainExplicitInAnalysis'])
        self.assertTrue(issues['usnistgov/air-lusi#4']['mustRemainExplicitInAnalysis'])

    def test_execution_fails_closed_until_artifacts_and_semantics_are_bound(self):
        gate = self.c['executionGate']
        self.assertFalse(gate['airLusiBinarySha256Verified'])
        self.assertFalse(gate['airLusiVariableSemanticsAudited'])
        self.assertFalse(gate['knownIssue5DistanceRuleAppliedAndRecorded'])
        self.assertFalse(gate['exactSolarSpectrumArtifactSha256Bound'])
        self.assertFalse(gate['numericReferenceValuesOpenedByThisContract'])
        self.assertFalse(gate['mayExecuteNumericComparison'])
        self.assertFalse(self.c['sourceAdmission']['solarSpectrumBytesBoundBeforeResiduals'])

    def test_claims_remain_narrow(self):
        boundary = self.c['claimBoundary']
        for key in (
            'validatesRoloCoefficientTranscriptionIfAgreementObserved',
            'independentlyValidatesFullRoloPhaseEvolution',
            'validatesAtmosphericScatteredMoonlight',
            'validatesFiniteMoonDiskTreatment',
            'validatesTotalSky',
            'authorizesStarsvisibilityIntegration',
            'productionAuthorized',
        ):
            self.assertFalse(boundary[key])
        self.assertIn('within-flight ROLO normalization dependency disclosed', boundary['permittedClaim'])


if __name__ == '__main__':
    unittest.main()
