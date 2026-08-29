from __future__ import annotations
import json
import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar-topocentric-geometry-and-finite-disk-sensitivity-v1.json'


class LunarTopocentricGeometryAndFiniteDiskSensitivityV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_geometry_is_topocentric_vacuum_and_residual_blind(self):
        g = self.c['geometryBoundary']
        self.assertEqual(g['sourceDirection'], 'TOPOCENTRIC_VACUUM_MOON_CENTER_DIRECTION_AT_OBSERVER')
        self.assertFalse(g['geocentricMoonDirectionAllowedForAtmosphericValidation'])
        self.assertTrue(g['observerLocationMustIncludeLatitudeLongitudeElevation'])
        self.assertFalse(g['atmosphericRefractionAppliedToSourceDirection'])
        self.assertTrue(g['archiveTimestampSemanticsMustBeConfirmedBeforeEvaluation'])
        self.assertTrue(g['targetPointingSemanticsMustBeConfirmedBeforeEvaluation'])
        self.assertTrue(g['noTimeOrDirectionAdjustmentFromMysticResiduals'])

    def test_published_nominal_separation_is_not_final_geometry(self):
        s = self.c['separationBoundary']
        self.assertTrue(s['publishedNominalMoonSeparationUsedForCaseLabelsOnly'])
        self.assertTrue(s['validationSeparationMustBeRecomputedFromFrozenVacuumDirections'])
        self.assertTrue(s['sphericalAngularSeparationRequired'])
        self.assertFalse(s['smallAnglePlanarApproximationAllowedForFinalSeparation'])

    def test_rolo_irradiance_is_not_multiplied_by_lunar_solid_angle(self):
        d = self.c['finiteDiskBoundary']
        self.assertEqual(d['roloSourceQuantity'], 'DISK_INTEGRATED_EXTRATERRESTRIAL_LUNAR_IRRADIANCE')
        self.assertTrue(d['centralCollimatedRunUsesFullDiskIntegratedIrradiance'])
        self.assertFalse(d['multiplySourceByLunarSolidAngle'])
        self.assertFalse(d['centralCollimatedRunMayClaimFiniteDiskModeled'])
        self.assertTrue(d['resolvedLunarRadianceMapRequiredForPhysicalDiskIntegration'])
        self.assertFalse(d['uniformDiskMayBeUsedAsPhysicalTruthWithoutSeparateJustification'])

    def test_result_blind_33_direction_sensitivity_grid_is_frozen(self):
        q = self.c['preregisteredSensitivitySampling']
        self.assertEqual(q['sampleRadiiInLunarRadius'], [0.0, 0.5, 1.0])
        self.assertEqual(q['azimuthSamplesPerNonzeroRing'], 16)
        self.assertEqual(q['azimuthStepDeg'], 22.5)
        self.assertEqual(q['totalDirectionalRunsPerAtmosphereTargetWavelengthConfiguration'], 33)
        self.assertTrue(q['sameAtmosphereTargetAndSpectralSourceRequiredAcrossAllDirections'])
        self.assertTrue(q['samePhotonBudgetPerDirectionRequired'])
        self.assertTrue(q['freshIndependentSeedsRequired'])
        self.assertTrue(q['noDirectionMayBeAddedOrRemovedFromObservedResiduals'])
        self.assertFalse(q['acceptanceThresholdInventedHere'])

    def test_sampled_envelope_is_not_misrepresented_as_exact_disk_solution(self):
        e = self.c['extendedSourceLogic']
        self.assertTrue(e['radiativeTransferLinearityMayBeUsed'])
        self.assertTrue(e['nonnegativeResolvedDiskRadianceWouldFormWeightedDirectionalCombination'])
        self.assertTrue(e['sampledEnvelopeMayBeUsedAsSensitivityDiagnostic'])
        self.assertFalse(e['sampledEnvelopeMayBeCalledRigorousContinuousDiskBound'])
        self.assertFalse(e['physicalExtendedDiskProviderAuthorized'])

    def test_claim_gates_remain_closed(self):
        x = self.c['xshooterUse']
        self.assertEqual(x['primaryClearStratumMinimumNominalSeparationDeg'], 13)
        self.assertTrue(x['sevenDegreeCasesRemainStressStratum'])
        self.assertTrue(x['finiteDiskSensitivityMustBeReportedSeparatelyForStressAndPrimaryStrata'])
        gate = self.c['openingGate']
        self.assertFalse(gate['ephemerisImplementationFrozenAndAudited'])
        self.assertFalse(gate['finiteDiskSensitivityExecuted'])
        self.assertFalse(gate['physicalResolvedDiskIntegrationImplemented'])
        self.assertFalse(gate['mysticResidualsOpened'])
        self.assertFalse(gate['atmosphericScatteredMoonlightValidated'])
        self.assertFalse(gate['productionAuthorized'])


if __name__ == '__main__':
    unittest.main()
