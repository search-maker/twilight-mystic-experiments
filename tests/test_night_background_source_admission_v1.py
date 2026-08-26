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
        self.assertTrue(c['providerAdmission']['sameAtmosphereIdentityRequired'])
        self.assertTrue(c['providerAdmission']['sameGeometryDirectionRequired'])
        self.assertTrue(c['providerAdmission']['validatedSupportRequiredBeforeDefaultTotalSky'])
        self.assertTrue(c['providerAdmission']['jointCovarianceMayNotBeAssumedZeroWithoutEvidence'])
        self.assertTrue(c['providerAdmission']['failClosedOnMissingComponent'])

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

    def test_artificial_model_must_be_directional_or_explicitly_zenith_only(self):
        a = self.c['artificialSkyglow']
        self.assertTrue(a['directionalTargetModelRequired'])
        self.assertFalse(a['constantSiteFloorAllowed'])
        self.assertTrue(a['naturalBackgroundSubtractionRequiredWhenCalibratingFromTotalSkyMeasurements'])
        self.assertTrue(a['moonlightSubtractionRequiredWhenCalibratingFromMoonlitMeasurements'])
        tiers = a['admissibleTiers']
        self.assertIn('MEASURED_DIRECTIONAL_ALL_SKY', tiers)
        self.assertIn('PHYSICAL_DIRECTIONAL_PROPAGATION', tiers)
        self.assertFalse(tiers['ZENITH_ATLAS_ONLY']['eligibleForArbitraryTargetDirection'])
        self.assertTrue(tiers['ZENITH_ATLAS_ONLY']['eligibleForZenithOnlyResearch'])
        self.assertFalse(a['validatedByThisProject'])
        self.assertFalse(a['productionAuthorized'])

if __name__ == '__main__':
    unittest.main()
