from __future__ import annotations
import json
import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'review' / 'night-background-source-admission-v1' / 'artificial-directional-provider-candidate-hierarchy-v1.json'


class ArtificialDirectionalProviderCandidateHierarchyV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_prediction_quantity_is_directional_and_not_inferred_spectrally_from_viirs(self):
        q = self.c['requiredPredictionQuantity']
        self.assertEqual(q['quantity'], 'directional observer-level artificial-sky radiance')
        self.assertTrue(q['photopicScotopicOrSpectralClaimsRequireSourceSpdEvidence'])
        self.assertFalse(q['viirsDnbAloneMayDefineVisibleSpectrum'])
        self.assertFalse(q['zenithOnlyQuantityMayBeUsedForArbitraryTarget'])

    def test_kocifaj_candidate_is_directional_but_not_automatically_admitted(self):
        k = self.c['candidateHierarchy']['KOCIFAJ_BARA_FALCHI_2022_ALL_SKY_KERNEL']
        self.assertEqual(k['doi'], '10.1093/mnrasl/slac029')
        self.assertEqual(k['role'], 'PRIMARY_RESEARCH_CANDIDATE_FOR_DIRECTIONAL_TRANSFER_KERNEL')
        self.assertFalse(k['automaticProviderAdmission'])
        self.assertIn('bind_upward_angular_emission_function', k['requiredBeforeImplementation'])
        self.assertIn('map_atmosphere_parameters_to_frozen_project_atmosphere_without_residual_tuning', k['requiredBeforeImplementation'])

    def test_other_models_keep_their_actual_scope(self):
        c = self.c['candidateHierarchy']
        self.assertEqual(c['ILLUMINA_V2']['doi'], '10.1016/j.jqsrt.2018.02.033')
        self.assertTrue(c['ILLUMINA_V2']['supportsHyperspectralModeling'])
        self.assertFalse(c['ILLUMINA_V2']['automaticProviderAdmission'])
        self.assertEqual(c['KOLLATH_ET_AL_2021_MONTE_CARLO_VIIRS']['doi'], '10.3390/rs13183653')
        self.assertEqual(c['DURISCOE_ET_AL_2018_SIMPLIFIED_VIIRS']['doi'], '10.1016/j.jqsrt.2018.04.028')
        self.assertFalse(c['DURISCOE_ET_AL_2018_SIMPLIFIED_VIIRS']['eligibleForArbitraryTargetDirection'])
        self.assertFalse(c['WORLD_ATLAS_2016']['eligibleForArbitraryTargetDirection'])
        self.assertFalse(c['WORLD_ATLAS_2016']['eligibleAsCurrentSameAtmosphereProvider'])

    def test_viirs_source_map_does_not_define_emission_function_or_spectrum(self):
        s = self.c['satelliteSourceBoundary']
        self.assertTrue(s['viirsDnbUsefulAsUpwardRadianceSourceMap'])
        self.assertTrue(s['viirsDnbIsNotGroundLightingInventory'])
        self.assertTrue(s['viirsDnbDoesNotUniquelyDetermineUpwardAngularEmissionFunction'])
        self.assertTrue(s['viirsDnbDoesNotUniquelyDetermineVisibleSpectralPowerDistribution'])
        self.assertFalse(s['sourceMapMayBeSelectedOrScaledFromStarVisibilityResiduals'])

    def test_first_provider_scope_is_clear_sky_and_fail_closed_on_missing_spd_or_obstacles(self):
        s = self.c['firstImplementationScope']
        self.assertTrue(s['clearSkyOnly'])
        self.assertFalse(s['cloudsSupported'])
        self.assertFalse(s['cloudAmplificationMayBeIgnoredWhileStillClaimingGeneralAllWeatherProvider'])
        self.assertTrue(s['directionalVBandResearchProviderMayPrecedeSpectralProvider'])
        self.assertTrue(s['spectralOrHumanVisionChannelsRequireIndependentSpdEvidence'])
        self.assertTrue(s['terrainAndObstacleTreatmentMustBeExplicit'])
        self.assertFalse(s['unknownTerrainOrObstacleTreatmentMayBeHidden'])

    def test_validation_is_residual_blind_and_requires_directional_measurement(self):
        v = self.c['residualBlindValidationProtocol']
        self.assertFalse(v['caseSelectionMayUseModelMeasurementAgreement'])
        self.assertIn('direction map', v['requiredObservation'])
        self.assertTrue(v['naturalBackgroundMustBeSubtractedWithUncertainty'])
        self.assertTrue(v['lunarBackgroundMustBeAbsentOrSubtractedWithUncertainty'])
        self.assertTrue(v['independentAtmosphereStateRequired'])
        self.assertTrue(v['validationMustIncludeMoreThanOneArtificialBurdenOrSourceConfiguration'])
        self.assertTrue(v['fitOfGlobalScaleAngularFunctionOrAodToValidationResidualsForbidden'])
        self.assertFalse(v['passFailThresholdInventedBeforeEmpiricalUncertaintyBudget'])

    def test_claims_remain_closed(self):
        c = self.c['claimBoundary']
        self.assertTrue(c['physicalDirectionalCandidateIdentified'])
        self.assertFalse(c['implementationFrozen'])
        self.assertFalse(c['sameAtmosphereAdapterValidated'])
        self.assertFalse(c['empiricallyValidatedByThisProject'])
        self.assertFalse(c['productionAuthorized'])
        self.assertTrue(c['TaylorJerusalemResidualTuningForbidden'])


if __name__ == '__main__':
    unittest.main()
