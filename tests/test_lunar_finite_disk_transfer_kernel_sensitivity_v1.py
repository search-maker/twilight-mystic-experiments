from __future__ import annotations

import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1'
CONTRACT = HERE / 'lunar-finite-disk-transfer-kernel-sensitivity-v1.json'
MODULE = HERE / 'lunar_finite_disk_transfer_kernel_sensitivity.py'


def load_module():
    spec = importlib.util.spec_from_file_location('lunar_finite_disk_transfer_kernel_sensitivity_tested', MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load finite-disk module')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LunarFiniteDiskTransferKernelSensitivityV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()
        cls.c = json.loads(CONTRACT.read_text(encoding='utf-8'))
        cls.cases = cls.m.frozen_cases(cls.c)

    def test_radius_is_derived_from_frozen_distance_and_iau_reference_radius(self):
        physical = self.c['physicalGeometry']
        self.assertEqual(physical['moonReferenceRadiusKm'], 1737.4)
        self.assertEqual(physical['observerMoonDistanceKm'], 384400.0)
        self.assertEqual(physical['moonReferenceRadiusSource']['doi'], '10.1007/s10569-017-9805-5')
        radius = self.m.lunar_angular_radius_deg(
            moon_radius_km=physical['moonReferenceRadiusKm'],
            observer_moon_distance_km=physical['observerMoonDistanceKm'],
        )
        self.assertAlmostEqual(radius, 0.25896468848728504, places=12)
        self.assertAlmostEqual(radius, physical['expectedAngularRadiusDeg'], places=12)
        self.assertTrue(physical['fixedAngularRadiusIndependentOfDistanceForbidden'])

    def test_frozen_case_universe_is_exact_33_by_6_with_fresh_candidate_seeds(self):
        self.assertEqual(len(self.cases), 198)
        self.assertEqual(len({row['caseId'] for row in self.cases}), 198)
        seeds = [row['randomSeed'] for row in self.cases]
        self.assertEqual(seeds, list(range(32910001, 32910199)))
        by_geometry = {}
        for row in self.cases:
            by_geometry.setdefault(row['geometryKey'], []).append(row)
        self.assertEqual(len(by_geometry), 6)
        for rows in by_geometry.values():
            self.assertEqual(len(rows), 33)
            radii = [row['radiusFraction'] for row in rows]
            self.assertEqual(radii.count(0.0), 1)
            self.assertEqual(radii.count(0.5), 16)
            self.assertEqual(radii.count(1.0), 16)
            self.assertEqual(len({row['positionAngleDeg'] for row in rows if row['radiusFraction'] == 1.0}), 16)

    def test_offset_geometry_matches_frozen_lunar_radius_without_planar_final_geometry_shortcut(self):
        radius = self.cases[0]['lunarAngularRadiusDeg']
        for row in self.cases:
            self.assertAlmostEqual(row['angularOffsetDeg'], radius * row['radiusFraction'], places=8)
            self.assertGreaterEqual(row['sourceZenithDeg'], 0.0)
            self.assertLessEqual(row['sourceZenithDeg'], 120.0)
            self.assertGreaterEqual(row['targetRelativeAzimuthToSampleSourceDeg'], 0.0)
            self.assertLess(row['targetRelativeAzimuthToSampleSourceDeg'], 360.0)
            self.assertIsNone(row['physicalResolvedDiskWeight'])
            self.assertTrue(row['sameFullDiskIntegratedRoloIrradianceRequired'])
            self.assertFalse(row['finiteMoonDiskModeled'])

    def _records(self, std=0.001):
        return [
            {
                'caseId': row['caseId'],
                'solverExitCode': 0,
                'radiance': 1.0,
                'stdRadiance': std,
            }
            for row in self.cases
        ]

    def test_equal_directional_kernel_yields_zero_observed_deviation_but_not_finite_disk_validation(self):
        result = self.m.evaluate_records(self._records(), self.c)
        self.assertTrue(result['executionComplete'])
        self.assertEqual(result['classification'], 'COMPLETE_550NM_SAMPLED_DIRECTIONAL_SENSITIVITY_DIAGNOSTIC')
        self.assertEqual(result['caseCountObserved'], 198)
        self.assertEqual(len(result['geometryReports']), 6)
        for report in result['geometryReports']:
            self.assertAlmostEqual(report['maximumAbsoluteSampledDeviationFractionOfCentral'], 0.0, places=15)
            self.assertTrue(report['uncertaintyExpandedRatioDiagnosticAvailable'])
            self.assertFalse(report['simultaneousCoverageCalibrated'])
        self.assertFalse(result['acceptanceThresholdApplied'])
        self.assertFalse(result['finiteMoonDiskValidated'])
        self.assertFalse(result['continuousDiskBoundProven'])
        self.assertFalse(result['physicalResolvedDiskIntegrationImplemented'])
        self.assertTrue(result['mandatorySpectralFollowOnRequiredBeforeBroadbandFiniteDiskClaim'])
        self.assertFalse(result['productionAuthorized'])

    def test_observed_directional_deviation_is_reported_without_pass_fail_threshold(self):
        records = self._records(std=0.0)
        records[-1]['radiance'] = 1.02
        result = self.m.evaluate_records(records, self.c)
        geometry = next(r for r in result['geometryReports'] if r['geometryKey'] == self.cases[-1]['geometryKey'])
        self.assertAlmostEqual(geometry['maximumAbsoluteSampledDeviationFractionOfCentral'], 0.02, places=12)
        self.assertAlmostEqual(geometry['sampledRatioToCentralMaximum'], 1.02, places=12)
        self.assertFalse(result['acceptanceThresholdApplied'])
        self.assertFalse(result['finiteMoonDiskValidated'])

    def test_missing_or_invalid_case_fails_closed_as_execution_incomplete(self):
        missing = self.m.evaluate_records(self._records()[:-1], self.c)
        self.assertEqual(missing['classification'], 'EXECUTION_INCOMPLETE')
        self.assertFalse(missing['executionComplete'])
        bad = self._records()
        bad[0]['radiance'] = 0.0
        zero = self.m.evaluate_records(bad, self.c)
        self.assertEqual(zero['classification'], 'EXECUTION_INCOMPLETE')
        self.assertFalse(zero['finiteMoonDiskValidated'])
        duplicate = self._records()
        duplicate[-1]['caseId'] = duplicate[0]['caseId']
        repeated = self.m.evaluate_records(duplicate, self.c)
        self.assertEqual(repeated['classification'], 'EXECUTION_INCOMPLETE')

    def test_large_mc_uncertainty_is_reported_as_unresolved_not_silently_accepted(self):
        result = self.m.evaluate_records(self._records(std=0.30), self.c)
        self.assertTrue(result['executionComplete'])
        self.assertEqual(result['classification'], 'COMPLETE_550NM_SAMPLED_DIRECTIONAL_SENSITIVITY_MC_UNRESOLVED')
        self.assertTrue(any(not r['uncertaintyExpandedRatioDiagnosticAvailable'] for r in result['geometryReports']))
        self.assertFalse(result['finiteMoonDiskValidated'])

    def test_broadband_follow_on_is_mandatory_and_cannot_be_selected_from_550_result(self):
        follow = self.c['mandatorySpectralFollowOn']
        self.assertTrue(follow['requiredBeforeAnyBroadbandFiniteDiskAdequacyClaim'])
        self.assertEqual(follow['wavelengthsNm'], [450.0, 650.0, 750.0])
        self.assertTrue(follow['allSixAtmosphereTargetConfigurationsRequired'])
        self.assertTrue(follow['directionSamplingMustRemainTheSameFrozen33DirectionGrid'])
        self.assertTrue(follow['selectionOfFollowOnWavelengthOrGeometryFrom550ResultForbidden'])

    def test_no_empirical_residual_tuning_or_resolved_disk_truth_claim(self):
        protected = self.c['protectedBoundaries']
        self.assertFalse(protected['taylorResidualUsed'])
        self.assertFalse(protected['jerusalemResidualUsed'])
        self.assertFalse(protected['xshooterResidualUsed'])
        self.assertFalse(protected['airLusiResidualUsed'])
        self.assertFalse(protected['parameterFitOrTuningAllowed'])
        self.assertFalse(protected['finiteDiskValidationClaimAllowed'])
        self.assertFalse(protected['productionAuthorized'])
        resolved = self.c['resolvedDiskBoundary']
        self.assertIsNone(resolved['currentAdmittedResolvedBrightnessModel'])
        self.assertFalse(resolved['uniformDiskMayBeDeclaredPhysicalTruth'])
        self.assertFalse(resolved['physicalExtendedDiskProviderAuthorized'])
        self.assertFalse(resolved['sampledDirectionalEnvelopeMayBeUsedAsResolvedDiskSolution'])

    def test_review_contract_does_not_authorize_solver_or_result_opening(self):
        gate = self.c['executionOpeningGate']
        self.assertTrue(gate['candidateSeedsMustBeRepositoryGloballyCollisionCheckedBeforeExecution'])
        self.assertTrue(gate['separateOneShotScientificExecutionIdentityRequired'])
        self.assertFalse(gate['solverExecutionAuthorizedByThisFile'])
        self.assertFalse(gate['resultOpeningAuthorizedByThisFile'])
        summary = self.m.validate_plan(self.cases, self.c)
        self.assertEqual(summary['caseCount'], 198)
        self.assertEqual(summary['geometryCount'], 6)
        self.assertFalse(summary['solverExecutionAuthorized'])
        self.assertFalse(summary['resultOpeningAuthorized'])


if __name__ == '__main__':
    unittest.main()
