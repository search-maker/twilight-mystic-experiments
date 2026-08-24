import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "ABSOLUTE_RADIANCE_TRACEABILITY_GATE.review.json"
REQUEST_PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "PGN_METADATA_REQUEST.md"


class EmpiricalAbsoluteRadianceTraceabilityGateV1Tests(unittest.TestCase):
    def test_gate_exists_and_target_values_remain_closed(self):
        self.assertTrue(GATE_PATH.is_file())
        doc = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        self.assertFalse(doc["candidate"]["targetRadianceOpened"])
        self.assertFalse(doc["pandora209CurrentDisposition"]["absoluteSkyRadianceTraceabilityProvenFromReviewedPublicEvidence"])
        self.assertFalse(doc["pandora209CurrentDisposition"]["strictAbsoluteValidationSourceAdmitted"])

    def test_type2_units_are_necessary_but_not_sufficient(self):
        doc = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        strict = doc["strictAdmissionDefinition"]
        self.assertTrue(strict["l1Type2RadianceUnitsNecessary"])
        self.assertFalse(strict["l1Type2RadianceUnitsSufficient"])
        not_sufficient = "\n".join(strict["notSufficient"])
        self.assertIn("irradiance calibration", not_sufficient)
        self.assertIn("relative", not_sufficient)
        self.assertIn("normalized", not_sufficient)
        self.assertIn("twilight", not_sufficient)

    def test_twilight_rt_derived_absolute_scale_is_not_independent_validation(self):
        doc = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        field = doc["fieldRadianceCalibrationBoundary"]
        self.assertTrue(field["usableAsGeneralInstrumentMethodEvidence"])
        self.assertFalse(field["usableAsIndependentAbsoluteCalibrationForThisSpecificMysticRealSkyValidation"])
        self.assertIn("radiative-transfer", field["method"])

    def test_unclear_traceability_fails_closed(self):
        doc = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        pre = doc["preValueRule"]
        self.assertFalse(pre["targetRadianceMayBeOpenedToDetermineWhetherCalibrationIsAbsolute"])
        self.assertTrue(pre["calibrationDocumentationAndCertificatesMayBeReviewed"])
        self.assertTrue(pre["metadataMayBeReviewed"])
        self.assertFalse(pre["mayInferAbsoluteTraceabilityFromUnitsAlone"])
        self.assertFalse(pre["mayInferAbsoluteTraceabilityFromGenericNetworkStatementThatDataAreCalibrated"])
        self.assertEqual(pre["unclearTraceabilityDisposition"], "HOLD_OR_REJECT_STRICT_SOURCE_NOT_OPEN_TARGET_VALUES")

    def test_no_gate_weakening_or_model_calibration_is_authorized(self):
        doc = json.loads(GATE_PATH.read_text(encoding="utf-8"))
        auth = doc["authorization"]
        self.assertTrue(all(value is False for value in auth.values()))
        disposition = doc["pandora209CurrentDisposition"]
        self.assertEqual(
            disposition["ifNoIndependentTraceabilityEvidenceExists"],
            "downgrade Pandora209 to relative spectral-shape/angular diagnostic or benchmark status and identify a different absolute-radiance source; do not weaken the gate",
        )

    def test_unsent_pgn_request_asks_the_traceability_question_without_target_values(self):
        text = REQUEST_PATH.read_text(encoding="utf-8")
        self.assertIn("draft only; not sent", text)
        self.assertIn("what establishes the absolute radiance scale", text)
        self.assertIn("integrating sphere", text)
        self.assertIn("STAIRS", text)
        self.assertIn("radiative-transfer simulation", text)
        self.assertIn("No selected target spectral values", text)


if __name__ == "__main__":
    unittest.main()
