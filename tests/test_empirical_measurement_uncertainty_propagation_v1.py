import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "MEASUREMENT_UNCERTAINTY_PROPAGATION.review.json"


class EmpiricalMeasurementUncertaintyPropagationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_target_and_uncertainty_values_remain_closed(self):
        self.assertFalse(self.doc["targetRadianceOpened"])
        self.assertFalse(self.doc["targetUncertaintyArraysOpened"])
        self.assertFalse(self.doc["protectedArrayBoundary"]["selectedLEVEL1UncertaintyValuesMayBeReadBeforeOpening"])
        self.assertFalse(self.doc["protectedArrayBoundary"]["selectedLEVEL1InstrumentUncertaintyValuesMayBeReadBeforeOpening"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))

    def test_full_covariance_and_unknown_correlation_rules_are_frozen(self):
        dispatch = self.doc["propagationDispatch"]
        self.assertEqual(dispatch["documentedFullCovariance"]["rule"], "sigma_channel = sqrt(w^T C w)")
        self.assertTrue(dispatch["documentedFullCovariance"]["preserveOffDiagonalTerms"])
        unknown = dispatch["perPixelOneSigmaWithNoCorrelationDocumentation"]
        self.assertEqual(unknown["rule"], "sigma_channel_upper = sum_i(abs(w_i) * sigma_i)")
        self.assertIn("do not use sqrt", unknown["interpretation"])
        self.assertFalse(dispatch["documentedComponentCovariance"]["undocumentedInterBlockIndependenceAllowed"])

    def test_unknown_coverage_cannot_be_guessed(self):
        unknown = self.doc["propagationDispatch"]["unknownUncertaintyCoverageOrNotOneSigma"]
        self.assertEqual(unknown["rule"], "HOLD_SOURCE_SEMANTICS_UNRESOLVED_BEFORE_OPENING")
        self.assertFalse(unknown["mayRelabelAsOneSigma"])
        self.assertFalse(unknown["mayConvertCoverageFactorByGuess"])

    def test_cross_spectrometer_unknown_correlation_is_not_zero(self):
        cross = self.doc["crossSpectrometerRule"]
        self.assertFalse(cross["unknownS1S2CorrelationMayBeAssumedZero"])
        self.assertIn("L1 maximum-correlation upper bound", cross["ifOnlyPerPixelOneSigmaAndNoCrossCorrelationDocumentation"])
        self.assertTrue(cross["johnsonVS2OnlyLaneAvoidsCrossSpectrometerUncertainty"])

    def test_log_sigma_and_acceptance_gate_binding_are_frozen(self):
        conversion = self.doc["channelRelativeAndLogConversion"]
        self.assertEqual(conversion["logSigmaUpper"], "sqrt(log(1 + relativeOneSigmaUpper^2))")
        gate = self.doc["relationshipToAcceptanceGate"]
        self.assertEqual(gate["externalSigmaLogMaximum"], 0.06)
        self.assertFalse(gate["rowMayBeDroppedAfterOpeningBecauseItsUncertaintyExceedsMaximum"])
        self.assertFalse(gate["aodIntervalUncertaintyIncludedAgainAsMeasurementSigma"])
        self.assertFalse(gate["aerosolScenarioSpreadIncludedAsMeasurementSigma"])
        self.assertFalse(gate["asivValidationErrorIncludedAsIndependentMeasurementSigma"])


if __name__ == "__main__":
    unittest.main()
