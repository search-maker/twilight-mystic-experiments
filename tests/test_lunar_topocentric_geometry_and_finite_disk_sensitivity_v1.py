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

    def test_primary_sources_distinguish_operational_irradiance_from_unqualified_resolved_models(self):
        p = self.c['primarySourceEvidence']
        self.assertEqual(p['kiefferStone2005']['doi'], '10.1086/430185')
        self.assertEqual(p['stoneKiefferBecker2003']['doi'], '10.1117/12.506117')
        self.assertEqual(p['satoEtAl2014LrocWac']['doi'], '10.1002/2013JE004580')
        self.assertIn('disk-integrated irradiance', p['kiefferStone2005']['relevance'])
        self.assertIn('experimental', p['stoneKiefferBecker2003']['relevance'])
        self.assertIn('reliable radiance model is operational', p['usgsInstrumentTeamsCurrent']['relevance'])
        self.assertIn('seven bands', p['satoEtAl2014LrocWac']['relevance'])

    def test_result_blind_33_direction_sensitivity_grid_is_frozen(self):
        q = self.c['preregisteredSensitivitySampling']
        self.assertEqual(q['sampleRadiiInLunarRadius'], [0.0, 0.5, 1.0])
        self.assertEqual(q['azimuthSamplesPerNonzeroRing'], 16)
        self.assertEqual(q['azimuthStepDeg'], 22.5)
        self.assertEqual(q['azimuthOriginDefinition'], 'tangent direction from Moon center toward local zenith')
        self.assertTrue(q['targetDirectionHeldFixedInOriginalMoonCenterLocalFrame'])
        self.assertTrue(q['targetRelativeAzimuthRecomputedForEveryOffsetSource'])
        self.assertTrue(q['sourceAzimuthRotatedBackToZeroBeforeMYSTICRendering'])
        self.assertTrue(q['angularRadiusInputMustBeDerivedFromFrozenObserverMoonDistanceBeforeSampling'])
        self.assertEqual(q['totalDirectionalRunsPerAtmosphereTargetWavelengthConfiguration'], 33)
        self.assertTrue(q['sameAtmosphereTargetAndSpectralSourceRequiredAcrossAllDirections'])
        self.assertTrue(q['samePhotonBudgetPerDirectionRequired'])
        self.assertTrue(q['freshIndependentSeedsRequired'])
        self.assertTrue(q['noDirectionMayBeAddedOrRemovedFromObservedResiduals'])
        self.assertFalse(q['acceptanceThresholdInventedHere'])

    def test_transfer_kernel_bound_does_not_assume_uniform_disk(self):
        k = self.c['transferKernelBound']
        self.assertTrue(k['nonnegativeSourceMeasureRequired'])
        self.assertFalse(k['requiresAssumptionOfUniformLunarDisk'])
        self.assertFalse(k['requiresAssumptionOfResolvedLunarBrightnessPattern'])
        self.assertTrue(k['sampledDiscreteSupportConvexHullExact'])
        self.assertFalse(k['thirtyThreeSampleEnvelopeIsExactContinuousDiskBound'])
        self.assertFalse(k['observationalResidualRequiredToComputeKernelBound'])
        self.assertFalse(k['postHocDirectionSelectionAllowed'])
        self.assertIn('min_disk(K)', k['exactContinuousSupportBoundIfKernelExtremaKnown'])
        self.assertIn('max_disk(K)', k['exactContinuousSupportBoundIfKernelExtremaKnown'])

    def test_resolved_disk_model_remains_unadmitted_and_may_only_supply_qualified_normalized_weights(self):
        r = self.c['resolvedDiskWeightingPath']
        self.assertIsNone(r['currentAdmittedResolvedBrightnessModel'])
        self.assertEqual(
            r['historicalUsgsRoloResolvedRadianceClassification'],
            'EXPERIMENTAL_NOT_ADMITTED_AS_PHYSICAL_DISK_TRUTH',
        )
        self.assertFalse(r['historicalUsgsRoloResolvedRadianceOperational'])
        self.assertIn('experimental', r['historicalUsgsRoloResolvedRadianceReason'])
        self.assertIn('reliable operational radiance model', r['historicalUsgsRoloResolvedRadianceReason'])
        self.assertEqual(
            r['lrocWacSato2014Classification'],
            'RESEARCH_CANDIDATE_REQUIRES_SPECTRAL_GEOMETRIC_AND_ABSOLUTE_NORMALIZATION_QUALIFICATION',
        )
        self.assertFalse(r['lrocWacSato2014MayBeUsedAsPhysicalWeightsWithoutQualification'])
        self.assertFalse(r['candidateAbsoluteScaleMayReplaceDiskIntegratedRolo'])
        self.assertTrue(r['candidateUsedForRelativeAngularWeightsOnly'])
        self.assertFalse(r['negativeResolvedWeightsAllowed'])
        self.assertTrue(r['phaseAndLibrationMustMatchSourceGeometry'])
        self.assertTrue(r['wavelengthInterpolationMustBeFrozenBeforeValidationResiduals'])
        self.assertFalse(r['resolvedMapSelectionOrSmoothingFromXshooterResidualsAllowed'])
        self.assertFalse(r['uniformDiskFallbackMayBeLabeledPhysicalTruth'])
        self.assertFalse(r['upstreamResolvedModelBytesAcquiredAndHashBound'])
        self.assertFalse(r['resolvedWeightAlgorithmImplementedAndAudited'])
        self.assertFalse(r['physicalExtendedDiskProviderAuthorized'])

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
        self.assertFalse(gate['transferKernelBoundAudited'])
        self.assertFalse(gate['resolvedLunarRadianceBytesHashBound'])
        self.assertFalse(gate['physicalResolvedDiskIntegrationImplemented'])
        self.assertFalse(gate['mysticResidualsOpened'])
        self.assertFalse(gate['atmosphericScatteredMoonlightValidated'])
        self.assertFalse(gate['productionAuthorized'])


if __name__ == '__main__':
    unittest.main()
