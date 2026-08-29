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

    def test_official_notebook_semantics_are_hash_bound(self):
        audit = self.c['officialNotebookSemanticAudit']
        self.assertEqual(audit['repositoryCommit'], '91f100a161bdf4205c8bbfef5dd5c30e33cbe995')
        self.assertEqual(audit['path'], 'example_usage/using_air_lusi_data.ipynb')
        self.assertEqual(audit['gitBlobSha'], '14b602efea9db9eb97520b3462b2d13e3e25c5d4')
        self.assertTrue(audit['auditedBeforeModelResidualCalculation'])
        self.assertIn('Divide standardized Irradiance', audit['auditedVariables']['distance_correction_factor'])
        self.assertIn('compatible with ROLO/GIRO', audit['auditedVariables']['Lunar_Disk_Reflectance'])
        solar = audit['officialSolarSpectrum']
        self.assertEqual(solar['family'], 'TSIS-1 Hybrid Solar Reference Spectrum Version 2')
        self.assertEqual(solar['doi'], '10.1029/2022EA002637')
        self.assertIn('hybrid_reference_spectrum_p1nm_resolution_c2022-11-30_with_unc.nc', solar['urlRecordedByNotebook'])
        self.assertFalse(solar['bytesSha256Bound'])

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
        self.assertIn('before inspecting model-reference residuals', plan['thresholdPolicy'])

    def test_reflectance_arm_is_independent_of_external_solar_file(self):
        arm = self.c['comparisonPlan']['armA_diskReflectanceDirect']
        self.assertEqual(arm['referenceVariable'], 'Lunar_Disk_Reflectance')
        self.assertFalse(arm['externalSolarSpectrumRequired'])
        self.assertFalse(arm['distanceCorrectionRequired'])
        self.assertIn('original published ROLO effective wavelengths', arm['modelQuantity'])
        self.assertIn('immediately bracketing Air-LUSI channel centroids', arm['wavelengthMapping'])
        self.assertIn('No extrapolation', arm['wavelengthMapping'])
        self.assertIn('Does not validate Eq.7', arm['claimLimit'])

    def test_irradiance_arm_keeps_distance_modes_separate(self):
        arm = self.c['comparisonPlan']['armB_fullToaIrradiance']
        self.assertEqual(arm['referenceVariable'], 'Irradiance')
        self.assertTrue(arm['externalSolarSpectrumRequired'])
        self.assertIn('divide by distance_correction_factor', arm['distanceCorrectionRule'])
        self.assertIn('Never mix these two distance conventions', arm['distanceCorrectionRule'])
        self.assertIn('no between-band interpolation', arm['primaryBandNodeComparison'])

    def test_known_upstream_issues_are_not_silently_ignored(self):
        issues = {x['githubIssue']: x for x in self.c['upstreamKnownIssuesFrozenBeforeNumericComparison']}
        self.assertIn('usnistgov/air-lusi#5', issues)
        self.assertIn('usnistgov/air-lusi#4', issues)
        self.assertIn('divide by distance_correction_factor', issues['usnistgov/air-lusi#5']['rule'])
        self.assertIn('0.46-0.57 degree', issues['usnistgov/air-lusi#4']['rule'])
        self.assertTrue(issues['usnistgov/air-lusi#5']['mustRemainExplicitInAnalysis'])
        self.assertTrue(issues['usnistgov/air-lusi#4']['mustRemainExplicitInAnalysis'])

    def test_execution_fails_closed_with_split_gates(self):
        gate = self.c['executionGate']
        self.assertFalse(gate['airLusiBinarySha256Verified'])
        self.assertTrue(gate['officialNotebookVariableSemanticsAudited'])
        self.assertTrue(gate['knownIssue5DistanceRuleFrozen'])
        self.assertFalse(gate['exactSolarSpectrumArtifactSha256Bound'])
        self.assertFalse(gate['numericModelReferenceResidualsOpenedByThisContract'])
        self.assertFalse(gate['mayExecuteDiskReflectanceComparison'])
        self.assertFalse(gate['mayExecuteIrradianceComparison'])
        self.assertIn('no external solar-spectrum artifact is required', gate['gateLogic']['diskReflectance'])
        self.assertIn('exact TSIS-1 HSRS v2 artifact SHA-256', gate['gateLogic']['irradiance'])
        self.assertFalse(self.c['sourceAdmission']['solarSpectrumBytesBoundBeforeIrradianceResiduals'])

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
