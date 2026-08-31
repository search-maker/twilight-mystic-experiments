from __future__ import annotations
import json
import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'review' / 'night-background-source-admission-v1' / 'natural-night-atmosphere-interface-v1.json'


class NaturalNightAtmosphereInterfaceV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_same_identity_string_is_not_physical_equivalence(self):
        r = self.c['coreRule']
        self.assertFalse(r['sameAtmosphereIdentityStringAloneIsSufficient'])
        self.assertTrue(r['atmosphereTreatmentMustBeExplicit'])
        self.assertTrue(r['componentMayBeAtmosphericallyPropagatedExactlyOnce'])
        self.assertTrue(r['doubleAttenuationOrScatteringForbidden'])
        self.assertTrue(r['residualBasedChoiceOfAtmosphereTreatmentForbidden'])

    def test_only_two_same_atmosphere_provider_modes_are_admissible(self):
        modes = self.c['admissibleProviderModes']
        self.assertFalse(modes['SOURCE_ONLY_SHARED_RT']['alreadyAtmosphericallyAttenuatedInputAllowed'])
        self.assertTrue(modes['FULL_FORWARD_MATCHED_ATMOSPHERE']['mustBypassSecondAtmosphericPropagation'])
        template = modes['REFERENCE_TEMPLATE_DIFFERENT_ATMOSPHERE']
        self.assertFalse(template['eligibleForSameAtmosphereTotalSkyProvider'])
        self.assertTrue(template['eligibleForResearchTemplateOrUncertaintyPrior'])
        self.assertFalse(template['mayBeRelabeledWithCurrentAtmosphereIdentity'])

    def test_gambons_cannot_be_double_propagated_or_relabelled(self):
        g = self.c['gambonsBoundary']
        self.assertTrue(g['publishedV1IncludesAtmosphericAttenuationAndScattering'])
        self.assertFalse(g['publishedV1OutputMayBeFedThroughSharedAtmosphereAgain'])
        self.assertFalse(g['publishedDefaultAtmosphereMayBeRelabeledAsCurrentMeasuredAtmosphere'])
        self.assertTrue(g['admissionAsFullForwardProviderRequiresExactAtmosphereEquivalence'])
        self.assertTrue(g['admissionAsSourceOnlyProviderRequiresDocumentedExtractionOfPreAtmosphereComponents'])
        self.assertTrue(g['constantAirglowRemainsSessionStateUncertainty'])

    def test_palace_preserves_volume_emission_semantics(self):
        p = self.c['palaceBoundary']
        self.assertTrue(p['airglowIsVolumeEmissionNotTopOfAtmospherePointSource'])
        self.assertTrue(p['emissionLayerGeometryMustBePreserved'])
        self.assertIn('do not apply', p['ifPalaceAtmosphericAbsorptionScatteringEnabled'])
        self.assertIn('emission-layer path', p['ifPalaceAtmosphericAbsorptionScatteringDisabled'])
        self.assertFalse(p['paranalAirglowMayBeRelabeledAsOtherSiteMeasuredAirglow'])

    def test_future_compositor_must_enforce_treatment_provenance(self):
        x = self.c['compositorImplication']
        self.assertTrue(x['futureRuntimeMustRejectMissingAtmosphereTreatmentModeForNaturalNight'])
        self.assertTrue(x['futureRuntimeMustRejectReferenceTemplateDifferentAtmosphereAsValidatedSameAtmosphere'])
        self.assertTrue(x['futureRuntimeMustRejectDoubleAtmosphericPropagation'])
        self.assertTrue(x['currentTotalSkyCompositorAtmosphereIdentityCheckAloneDoesNotEstablishPhysicalEquivalence'])
        self.assertTrue(x['runtimeStrengtheningRequiredBeforeProviderPromotion'])

    def test_empirical_and_production_gates_stay_closed(self):
        v = self.c['validationGate']
        self.assertTrue(v['moonlessDirectionalMeasurementsAcrossMultipleNightsRequired'])
        self.assertTrue(v['sessionAirglowOrExplicitLatentUncertaintyRequired'])
        self.assertTrue(v['noTaylorJerusalemResidualTuning'])
        self.assertFalse(v['validatedByThisProject'])
        self.assertFalse(v['productionAuthorized'])


if __name__ == '__main__':
    unittest.main()
