from __future__ import annotations
import json
import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'review' / 'night-background-source-admission-v1' / 'source-admission-contract.json'

class NightBackgroundSourceAdmissionV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_linear_composition_and_fail_closed_boundary(self):
        c = self.c
        self.assertTrue(c['linearCompositionOnly'])
        self.assertTrue(c['magnitudeOrSqmSpaceAdditionForbidden'])
        p = c['providerAdmission']
        self.assertTrue(p['sameAtmosphereIdentityRequired'])
        self.assertTrue(p['sameGeometryDirectionRequired'])
        self.assertTrue(p['validatedSupportRequiredBeforeDefaultTotalSky'])
        self.assertTrue(p['jointCovarianceMayNotBeAssumedZeroWithoutEvidence'])
        self.assertTrue(p['failClosedOnMissingComponent'])
        self.assertTrue(p['spectralClaimsRequireSpectralEvidence'])
        self.assertTrue(p['computationalCapabilityIsNotEmpiricalValidation'])
        self.assertTrue(p['empiricalValidationIsNotProductionAuthorization'])

    def test_natural_model_is_directional_dynamic_and_excludes_other_components(self):
        n = self.c['naturalNight']
        self.assertEqual(n['preferredModelFamily'], 'GAMBONS')
        self.assertEqual(set(n['requiredOutputChannels']), {'johnsonV', 'photopic', 'scotopic'})
        self.assertIn('target_direction', n['requiredInputs'])
        self.assertIn('observation_time', n['requiredInputs'])
        self.assertIn('atmosphere_identity', n['requiredInputs'])
        self.assertIn('airglow_state_or_explicit_uncertainty', n['requiredInputs'])
        self.assertTrue(n['moonlightMustBeExcluded'])
        self.assertTrue(n['artificialSkyglowMustBeExcluded'])
        self.assertFalse(n['constantDarkSkyFloorAllowed'])
        self.assertFalse(n['paranalSkyCalcMayBeSilentlyTreatedAsGlobalModel'])
        self.assertFalse(n['validatedByThisProject'])
        self.assertFalse(n['productionAuthorized'])

    def test_gambons_constant_airglow_is_not_promoted_to_session_truth(self):
        n = self.c['naturalNight']
        g = n['sourceSemantics']['gambons2021']
        self.assertEqual(g['citation'], 'Masana et al. 2021, MNRAS 501, 5443-5456, DOI 10.1093/mnras/staa4005')
        self.assertIn('constant airglow radiance', g['criticalAirglowBoundary'])
        self.assertFalse(g['constantAirglowMayBeTreatedAsMeasuredSessionState'])
        self.assertFalse(g['constantAirglowMayBeUsedWithoutExplicitUncertainty'])
        a = n['airglowAdmission']
        self.assertTrue(a['sessionSpecificStatePreferred'])
        self.assertIn('explicit uncertainty', a['ifSessionSpecificStateUnavailable'])
        self.assertFalse(a['mayTuneFromTaylorOrJerusalemResiduals'])
        self.assertTrue(a['validationRequiresMoonlessDirectionalMeasurementsAcrossMultipleNights'])

    def test_palace_is_dynamic_spectral_paranal_airglow_not_global_or_toa_truth(self):
        p = self.c['naturalNight']['sourceSemantics']['palace2025']
        self.assertIn('10.5194/gmd-18-4353-2025', p['citation'])
        self.assertEqual(p['releaseDoi'], '10.5281/zenodo.14064022')
        self.assertEqual(p['validWavelengthRangeUm'], [0.3, 2.5])
        self.assertEqual(p['modelContents']['chemicalSpecies'], 9)
        self.assertEqual(p['modelContents']['emissionLines'], 26541)
        self.assertEqual(p['modelContents']['continuumComponents'], 3)
        self.assertEqual(p['modelContents']['variabilityClasses'], 23)
        self.assertEqual(p['xshooterCentered27DayF107TrainingRangeSfu'], [67, 166])
        self.assertEqual(set(p['dynamicInputs']), {'month', 'local_mean_solar_time', 'centered_27_day_F10_7', 'zenith_angle', 'pwv'})
        self.assertTrue(p['providesResidualVariability'])
        self.assertTrue(p['atmosphericAbsorptionAndScatteringOptional'])
        self.assertTrue(p['doubleAtmosphericAttenuationForbidden'])
        self.assertTrue(p['emissionLayerGeometryMustBePreserved'])
        self.assertFalse(p['mayBeTreatedAsTopOfAtmospherePointSource'])
        self.assertFalse(p['sameSessionMeasuredAirglowState'])
        self.assertFalse(p['mayBeSilentlyAppliedOutsideParanal'])
        self.assertIn('ESO Sky Model', p['validationIndependenceBoundary'])
        self.assertTrue(p['exactReleaseAssetsMustBeFrozenBeforeImplementation'])
        self.assertFalse(p['automaticPromotionFromPaperOrRelease'])

    def test_band_only_natural_model_cannot_claim_spectral_total_sky(self):
        s = self.c['naturalNight']['spectralTotalSkyRule']
        self.assertFalse(s['bandOnlyProviderMayClaimSpectralChannel'])
        self.assertTrue(s['spectralChannelRequiresSeparatelyAdmittedSpectralComponentModelOrMeasurement'])
        self.assertTrue(s['paranalSkyCalcSpectrumMayBeUsedAsReferenceTemplateOnly'])
        self.assertFalse(s['paranalSpectrumMayBeSilentlyAppliedAsGlobalSiteState'])
        skycalc = self.c['naturalNight']['sourceSemantics']['esoSkyCalc']
        self.assertTrue(skycalc['mayProvideSpectralReference'])
        self.assertFalse(skycalc['mayBeSilentlyTreatedAsGlobalAirglowOrAtmosphere'])
        self.assertIn('airglow_residual_continuum', skycalc['separableRadianceComponents'])

    def test_artificial_model_must_be_directional_or_explicitly_zenith_only(self):
        a = self.c['artificialSkyglow']
        self.assertTrue(a['directionalTargetModelRequired'])
        self.assertFalse(a['constantSiteFloorAllowed'])
        self.assertTrue(a['naturalBackgroundSubtractionRequiredWhenCalibratingFromTotalSkyMeasurements'])
        self.assertTrue(a['moonlightSubtractionRequiredWhenCalibratingFromMoonlitMeasurements'])
        tiers = a['admissibleTiers']
        self.assertIn('MEASURED_DIRECTIONAL_ALL_SKY', tiers)
        self.assertIn('PHYSICAL_DIRECTIONAL_PROPAGATION', tiers)
        atlas = tiers['ZENITH_ATLAS_ONLY']
        self.assertFalse(atlas['eligibleForArbitraryTargetDirection'])
        self.assertTrue(atlas['eligibleForZenithOnlyResearch'])
        self.assertFalse(atlas['eligibleAsSameAtmosphereDynamicProvider'])
        self.assertTrue(atlas['mustPreserveAtlasAtmosphereAssumptions'])
        self.assertFalse(a['validatedByThisProject'])
        self.assertFalse(a['productionAuthorized'])

    def test_world_atlas_is_a_zenith_prior_not_same_atmosphere_directional_truth(self):
        w = self.c['artificialSkyglow']['worldAtlas2016Boundary']
        self.assertIn('10.1126/sciadv.1600377', w['citation'])
        self.assertEqual(w['publishedQuantity'], 'zenith artificial night sky brightness')
        self.assertEqual(w['band'], 'Johnson-Cousins V')
        self.assertIn('US62', w['modelAtmosphere'])
        self.assertIn('tau=0.31', w['publishedAerosolClarity'])
        self.assertEqual(w['sourceIntegrationRadiusKm'], 195)
        self.assertFalse(w['mountainScreeningIncluded'])
        self.assertFalse(w['mayBeReinterpretedAsMeasuredDirectionalAllSky'])
        self.assertFalse(w['mayReplaceSameAtmospherePropagation'])

    def test_validation_opening_remains_residual_blind(self):
        v = self.c['validationOpeningPolicy']
        self.assertTrue(v['caseSelectionMustBeResidualBlind'])
        self.assertTrue(v['componentMeasurementsMustBeOpenedBeforeAnyTotalSkyJointClaim'])
        self.assertTrue(v['noPostHocBackgroundScalingToTaylorOrJerusalem'])
        self.assertTrue(v['jointTotalSkyValidationRequiresSeparatelyFrozenProtocol'])
        av = self.c['artificialSkyglow']['validation']
        self.assertTrue(av['requiresDirectionalAllSkyMeasurementsAtMoreThanOneArtificialBurdenLevel'])
        self.assertTrue(av['requiresLocalLightingStateOrEmissionContext'])
        self.assertTrue(av['requiresNaturalAndApplicableLunarSubtractionWithUncertainty'])
        self.assertFalse(av['mayTuneFromTaylorOrJerusalemResiduals'])

if __name__ == '__main__':
    unittest.main()
