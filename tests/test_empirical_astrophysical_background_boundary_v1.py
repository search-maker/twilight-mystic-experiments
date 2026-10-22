import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "ASTROPHYSICAL_BACKGROUND_BOUNDARY.review.json"


class EmpiricalAstrophysicalBackgroundBoundaryV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_primary_real_sky_rule_does_not_fit_or_subtract_background(self):
        rule = self.doc["currentClaimChoice"]
        self.assertEqual(rule["id"], "ABSOLUTE_REAL_SKY_NO_ASTROPHYSICAL_SUBTRACTION_V1")
        self.assertFalse(rule["subtractMatchedDeepNightSpectrumForPrimaryPassFail"])
        self.assertFalse(rule["fitConstantOrSpectralOffsetToResiduals"])
        self.assertFalse(rule["chooseBackgroundModeFromResiduals"])
        self.assertFalse(rule["chooseBackgroundModeFromSunDepthPerformance"])

    def test_deep_night_evidence_is_diagnostic_only(self):
        diagnostic = self.doc["diagnosticDeepNightEvidence"]
        self.assertTrue(diagnostic["mayCaptureIfAvailable"])
        self.assertTrue(diagnostic["selectionMustBeMetadataOnly"])
        self.assertFalse(diagnostic["mayBeSubtractedFromPrimaryObservedChannelAfterOpening"])
        self.assertTrue(diagnostic["mayExplainFailureWithoutChangingFailure"])

    def test_late_background_cannot_drop_bad_rows(self):
        late = self.doc["lateTwilightInterpretation"]
        self.assertFalse(late["mayDropDeepRowsAfterOpeningBecauseBackgroundIsLarge"])
        self.assertIn("future model generation", late["futureFix"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))


if __name__ == "__main__":
    unittest.main()
