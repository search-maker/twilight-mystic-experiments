from __future__ import annotations
import json
import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'review' / 'night-background-source-admission-v1' / 'total-sky-runtime-atmosphere-treatment-handoff-v1.json'


class TotalSkyRuntimeAtmosphereTreatmentHandoffV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_runtime_target_is_review_only_and_unpromoted(self):
        target = self.c['runtimeTarget']
        self.assertEqual(target['repository'], 'search-maker/starsvisibility')
        self.assertEqual(target['draftPr'], 123)
        self.assertFalse(target['runtimeGuardMergedToMain'])
        self.assertFalse(target['providerPromotionAuthorized'])

    def test_final_compositor_input_must_already_be_observer_level(self):
        rule = self.c['finalCompositorInputRule']
        self.assertTrue(rule['nonSolarComponentMustBeObserverLevelDirectionalRadiance'])
        self.assertFalse(rule['sourceOnlyOrVolumeEmissionMayEnterCompositorDirectly'])
        self.assertFalse(rule['atmosphereIdentityStringAloneIsSufficient'])
        self.assertTrue(rule['atmosphereTreatmentRecordRequired'])
        self.assertTrue(rule['additionalAtmosphericPropagationRequiredMustBeFalse'])
        self.assertFalse(rule['componentMayBeModeledAtmosphericallyPropagatedMoreThanOnce'])
        self.assertTrue(rule['residualBasedTreatmentSelectionForbidden'])

    def test_source_only_path_maps_to_one_shared_propagation(self):
        item = self.c['sourceAdmissionToRuntimeMapping']['SOURCE_ONLY_SHARED_RT']
        self.assertFalse(item['sourceStateMayEnterCompositorDirectly'])
        self.assertEqual(item['finalRuntimeAtmosphereTreatmentMode'], 'SHARED_ATMOSPHERE_PROPAGATED')
        self.assertEqual(item['finalPropagationCount'], 1)
        self.assertTrue(item['finalPropagationAtmosphereIdentityMustEqualRequestedAtmosphere'])
        self.assertEqual(item['finalOutputLevel'], 'OBSERVER_LEVEL_RADIANCE')

    def test_full_forward_path_maps_to_one_provider_internal_propagation(self):
        item = self.c['sourceAdmissionToRuntimeMapping']['FULL_FORWARD_MATCHED_ATMOSPHERE']
        self.assertTrue(item['sourceStateMayEnterCompositorDirectly'])
        self.assertEqual(item['finalRuntimeAtmosphereTreatmentMode'], 'PROVIDER_INTERNAL_PROPAGATED')
        self.assertEqual(item['finalPropagationCount'], 1)
        self.assertTrue(item['finalPropagationAtmosphereIdentityMustEqualRequestedAtmosphere'])
        self.assertTrue(item['proofOfExactAtmosphereEquivalenceStillRequired'])

    def test_reference_template_cannot_be_relabeled_to_current_atmosphere(self):
        item = self.c['sourceAdmissionToRuntimeMapping']['REFERENCE_TEMPLATE_DIFFERENT_ATMOSPHERE']
        self.assertFalse(item['sourceStateMayEnterValidatedSameAtmosphereCompositor'])
        self.assertTrue(item['mayBeUsedAsResearchTemplateOrUncertaintyPrior'])
        self.assertFalse(item['mayBeRelabeledToRequestedAtmosphere'])

    def test_empirical_observer_level_path_has_zero_modeled_propagations(self):
        item = self.c['sourceAdmissionToRuntimeMapping']['EMPIRICAL_OBSERVER_LEVEL_DIRECTIONAL']
        self.assertTrue(item['sourceStateMayEnterCompositorDirectly'])
        self.assertEqual(item['finalRuntimeAtmosphereTreatmentMode'], 'EMPIRICAL_OBSERVER_LEVEL')
        self.assertEqual(item['finalPropagationCount'], 0)
        self.assertTrue(item['observationAtmosphereIdentityMustEqualRequestedAtmosphere'])
        self.assertTrue(item['secondModeledPropagationForbidden'])

    def test_examples_preserve_gambons_palace_atlas_boundaries(self):
        examples = self.c['componentExamples']
        self.assertFalse(examples['gambonsPublishedObserverLevel']['maySimplyCopyRequestedAtmosphereIdentity'])
        self.assertFalse(examples['gambonsPublishedObserverLevel']['mayPassThroughSharedAtmosphereAgain'])
        self.assertFalse(examples['palaceVolumeEmissionWithoutInternalPropagation']['mayEnterCompositorBeforeEmissionLayerTransport'])
        self.assertTrue(examples['palaceVolumeEmissionWithoutInternalPropagation']['sharedRtMustPreserveEmissionLayerGeometry'])
        self.assertFalse(examples['palaceObserverLevelWithInternalPropagation']['mayPassThroughSharedAtmosphereAgain'])
        self.assertFalse(examples['worldAtlas2016ZenithPrior']['arbitraryTargetDirectionEligible'])
        self.assertFalse(examples['worldAtlas2016ZenithPrior']['sameAtmosphereDynamicProviderEligible'])

    def test_lunar_source_still_requires_rt_before_composition(self):
        lunar = self.c['lunarComponentHandoff']
        self.assertFalse(lunar['roloExtraterrestrialSourceMayEnterCompositorDirectly'])
        self.assertEqual(lunar['mysticScatteredMoonlightAfterFrozenAtmospherePropagationWouldMapTo'], 'SHARED_ATMOSPHERE_PROPAGATED')
        self.assertFalse(lunar['atmosphericScatteredMoonlightValidatedByThisProject'])
        self.assertFalse(lunar['physicalFiniteDiskProviderAuthorized'])

    def test_claim_boundaries_remain_closed(self):
        claim = self.c['claimBoundary']
        self.assertTrue(claim['computationalGuardImplementedOnDraftBranch'])
        self.assertTrue(claim['runtimeExactHeadCiRequiredBeforeMerge'])
        self.assertTrue(claim['runtimeGuardMergeIsNotProviderValidation'])
        self.assertTrue(claim['providerValidationIsNotProductionAuthorization'])
        self.assertTrue(claim['jointTotalSkyValidationProtocolStillRequired'])
        self.assertTrue(claim['TaylorJerusalemResidualTuningForbidden'])
        self.assertFalse(claim['productionAuthorized'])


if __name__ == '__main__':
    unittest.main()
