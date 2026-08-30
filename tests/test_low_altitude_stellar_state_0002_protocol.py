import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'review/low-altitude-stellar-transport-v2/low_altitude_state_0002_protocol.py'
SPEC = importlib.util.spec_from_file_location('lowalt_state_0002_protocol_test', P)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class State0002ProtocolTests(unittest.TestCase):
    def test_frozen_counts_and_support(self):
        d = m.validate_protocol()
        self.assertEqual(d['scientificState'], 'LOWALT-STELLAR-STATE-0002')
        self.assertEqual(d['trainingSpectrumCount'], 2090)
        self.assertEqual(d['inheritedFiveDegreeSeamSpectrumCount'], 55)
        self.assertEqual(d['protectedAtmosphericSpectrumCount'], 220)
        self.assertEqual(d['protectedJohnsonVComparisonCount'], 660)
        self.assertEqual(d['candidateMinGeometricAltitudeDeg'], 0.25)
        self.assertFalse(d['exactHorizonSupported'])
        self.assertFalse(d['applicationSupportChanged'])
        self.assertFalse(d['productionAuthorized'])
        self.assertFalse(d['protectedResultsOpened'])

    def test_representation_is_dense_tau_not_csc_or_fitted_chapman(self):
        d = m.validate_protocol()['representation']
        self.assertEqual(d['quantity'], 'direct-optical-depth')
        self.assertEqual(d['targetAltitudeBasis'], 'topocentric-vacuum-geometric')
        self.assertEqual(d['sourceZenithAngleRelation'], 'sza=90deg-targetGeometricAltitudeDeg')
        self.assertEqual(d['pseudoSphericalReferenceSolver'], 'sdisort')
        self.assertFalse(d['cscExtrapolationBelow5Deg'])
        self.assertFalse(d['fittedChapmanFormula'])
        self.assertFalse(d['refractionAppliedInRadiativeTransfer'])

    def test_mesh_is_a_priori_dense_on_spherical_and_scale_height_scales(self):
        d = m.validate_protocol()['meshRationale']
        self.assertLess(d['altitudeStepFractionOfCharacteristicScale'], 0.05)
        self.assertLessEqual(d['elevationStepFractionOfReferenceScaleHeight'], 0.03125)
        self.assertEqual(d['altitudeStepDeg'], 0.125)
        self.assertEqual(d['elevationStepM'], 250.0)

    def test_fresh_protected_axes_do_not_reuse_opened_state_0001_axes(self):
        self.assertFalse(set(m.PROTECTED_ALTITUDE_DEG) & m.OPENED_STATE_0001_PROTECTED_ALTITUDES)
        self.assertFalse(set(m.PROTECTED_ELEVATION_M) & m.OPENED_STATE_0001_PROTECTED_ELEVATIONS)
        self.assertFalse(set(m.PROTECTED_AOD550) & m.OPENED_STATE_0001_PROTECTED_AODS)
        training = set(m._cases(m.TRAINING_ALTITUDE_DEG, m.ELEVATION_KNOTS_M, m.AOD_KNOTS))
        protected = set(m._cases(m.PROTECTED_ALTITUDE_DEG, m.PROTECTED_ELEVATION_M, m.PROTECTED_AOD550))
        self.assertFalse(training & protected)

    def test_anti_fitting_and_fail_closed_contract(self):
        d = m.validate_protocol()
        self.assertFalse(d['predecessorProtectedResidualsMayInformDesign'])
        self.assertFalse(d['taylorJerusalemOrHalachicTimesMayInformDesign'])
        self.assertFalse(d['avpsAerosolProfileScienceMixedIntoThisState'])
        self.assertEqual(d['zeroOrUnderflowTransmissionSemantics'], 'NUMERICALLY_UNRESOLVED_FAIL_CLOSED')
        self.assertFalse(d['positiveEpsilonSubstitutionAllowed'])
        self.assertFalse(d['sameIdentityRetryAllowed'])
        self.assertFalse(d['githubRerunAllowed'])
        self.assertFalse(d['postProtectedResultFloorSelectionAllowed'])
        self.assertFalse(d['postProtectedResultRetuningAllowed'])
        self.assertTrue(d['fiveDegreeSeamContentIdentityRequired'])
        self.assertTrue(d['globalAndEveryAltitudeProtectedSliceMustPass'])

    def test_opened_predecessor_numeric_residuals_are_not_embedded(self):
        text = P.read_text(encoding='utf-8')
        for forbidden in (
            '0.20750414925067062', '0.044561710921862445',
            '0.010802886158554112', '0.015863226012807097',
            '0.012279708245117149',
        ):
            self.assertNotIn(forbidden, text)
        self.assertNotIn('AnnArbor.csv', text)
        self.assertNotIn('first-seeing', text.lower())


if __name__ == '__main__':
    unittest.main()
