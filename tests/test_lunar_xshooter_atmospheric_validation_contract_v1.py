from __future__ import annotations
import json
import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'review' / 'lunar-scattered-light-source-contract-v1' / 'xshooter-atmospheric-moonlight-validation-contract-v1.json'

class LunarXshooterAtmosphericValidationContractV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_observational_reference_and_design_are_frozen(self):
        o = self.c['observationalReference']
        self.assertEqual(o['doi'], '10.1051/0004-6361/201833759')
        self.assertEqual(o['esoProposalId'], '491.L-0659')
        self.assertEqual(o['instrument'], 'VLT/X-Shooter')
        self.assertEqual(o['publishedBlankSkyDesign']['nights'], 3)
        self.assertEqual(o['publishedBlankSkyDesign']['targetMoonSeparationsDeg'], [7, 13, 20, 45, 90, 110])
        self.assertEqual(o['publishedBlankSkyDesign']['observationsPerNominalNight'], 6)

    def test_primary_and_stress_strata_are_predeclared(self):
        a = self.c['caseAdmission']
        self.assertTrue(a['archiveIdentityMustBeFrozenBeforeResiduals'])
        self.assertTrue(a['rawAndReducedProductHashesRequired'])
        self.assertEqual(a['primaryClearSkyStratum']['separationsDeg'], [13, 20, 45, 90, 110])
        self.assertIn('thin cirrus', a['primaryClearSkyStratum']['externalQcExclusions'][0])
        self.assertIn('7-deg observations', a['primaryClearSkyStratum']['reasonForExcluding7Deg'])
        self.assertTrue(a['secondaryStressStratum']['mayBePlottedAndDiagnosed'])
        self.assertFalse(a['secondaryStressStratum']['mayDrivePrimaryPassFail'])
        self.assertTrue(a['secondaryStressStratum']['mustRemainReported'])
        self.assertTrue(a['selectionMayNotDependOnOurMysticResiduals'])

    def test_same_sky_aerosol_fit_is_forbidden_for_independent_validation(self):
        a = self.c['atmosphereIndependence']
        joined = ' '.join(a['forbiddenAsIndependentInputs'])
        self.assertIn('same X-Shooter moonlit-sky spectra', joined)
        self.assertIn('per-run optimal aerosol size distributions', joined)
        self.assertIn('post-hoc aerosol/AOD/profile/SSA/phase-function', joined)
        self.assertIn('F=1.2', joined)
        self.assertGreaterEqual(len(a['admissibleAbsoluteValidationAtmosphere']), 3)
        self.assertIn('ATMOSPHERE_UNCONSTRAINED_GEOMETRY_SPECTRAL_DIAGNOSTIC', a['ifNoIndependentAerosolStateExists'])

    def test_model_and_background_are_not_allowed_to_fit_validation_spectra(self):
        m = self.c['modelFreeze']
        self.assertTrue(m['lunarSourceNoScaleFit'])
        self.assertTrue(m['lunarSourceNoSpectralTiltFit'])
        self.assertTrue(m['sameReviewedElevatedSiteGeometryRequired'])
        self.assertIn('atm_z_grid', m['observerElevationSemantics'])
        b = self.c['backgroundSeparation']
        self.assertFalse(b['mayUseJonesModelSubtractionAsIndependentTruth'])
        self.assertFalse(b['mayUseOurTotalSkyResidualToFitNaturalBackground'])
        self.assertIn('does not justify setting other components to zero', b['ifLunarFractionDominates'])

    def test_comparison_is_linear_and_unrenormalized(self):
        p = self.c['comparisonPlan']
        self.assertEqual(p['primaryRangeNm'], [380.0, 780.0])
        self.assertEqual(p['comparisonSpace'], 'linear spectral radiance')
        self.assertTrue(p['noMultiplicativeRenormalization'])
        self.assertTrue(p['noResidualDrivenAerosolSelection'])
        self.assertTrue(p['noPostHocWavelengthMaskExceptInstrumentOrArchiveAuthoredBadDataFlags'])
        self.assertIsNone(p['passFailThreshold'])
        self.assertIn('before residual opening', p['thresholdPolicy'])

    def test_execution_and_claims_fail_closed(self):
        g = self.c['executionGate']
        for key in (
            'esoArchiveProductsAcquiredAndHashed',
            'exactPrimaryAndStressCaseLedgerFrozen',
            'instrumentCalibrationSemanticsAudited',
            'independentAtmosphereLedgerFrozen',
            'nonLunarBackgroundTreatmentFrozen',
            'modelObservationResolutionTransformFrozen',
            'mysticResidualsOpened',
            'absoluteValidationExecutionAuthorized',
        ):
            self.assertFalse(g[key])
        c = self.c['claimBoundary']
        for key in (
            'validatesLunarToaSource',
            'validatesAtmosphericScatteredMoonlight',
            'validatesNaturalNight',
            'validatesArtificialSkyglow',
            'validatesTotalSky',
            'productionAuthorized',
        ):
            self.assertFalse(c[key])

if __name__ == '__main__':
    unittest.main()
