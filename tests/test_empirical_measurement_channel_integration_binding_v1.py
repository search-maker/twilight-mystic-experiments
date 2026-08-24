import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "MEASUREMENT_CHANNEL_INTEGRATION_BINDING.review.json"


class EmpiricalMeasurementChannelIntegrationBindingV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_exact_historical_integrator_bytes_are_bound(self):
        binding = self.doc["historicalFrozenBinding"]
        self.assertEqual(binding["integrateVisualResponse"]["gitBlobSha1"], "85646e2412ad2b53e7b08d24bd4f778f99f32e6d")
        self.assertEqual(binding["johnsonV"]["gitBlobSha1"], "4ac7b419f8efec2c87ce71161d945ed0609ee852")
        self.assertEqual(binding["johnsonV"]["passbandGitBlobSha1"], "eced08e8e126d59c9e4cfc52fea314711b3cea9c")
        self.assertEqual(binding["johnsonV"]["passbandRawSha256"], "20e8d89346b5bc71f848ff3eee054a92e1ba53872fb048ac670151b52dac99a1")

    def test_pandora_unit_conversion_and_no_resampling_are_frozen(self):
        contract = self.doc["pandoraInputContract"]
        self.assertEqual(contract["requiredL1DataType"], 2)
        self.assertEqual(contract["requiredPublishedUnit"], "W/m2/nm/sr")
        self.assertIn("exactly 1000", contract["unitConversionBeforeFrozenIntegrators"])
        self.assertFalse(contract["interpolateTargetRadianceOntoConvenientGridAllowed"])

    def test_s2_johnson_v_partial_lane_does_not_expand_photopic_scotopic(self):
        channels = self.doc["channelRules"]
        self.assertEqual(channels["johnsonV"]["requiredMeasurementCoverageNm"], [470.0, 700.0])
        self.assertTrue(channels["johnsonV"]["s2OnlyPartialStrictLaneAllowed"])
        self.assertFalse(channels["photopic"]["maySilentlyDrop380To400NmForS2Only"])
        self.assertFalse(channels["scotopic"]["maySilentlyDrop380To400NmForS2Only"])

    def test_dual_fov_background_and_uncertainty_are_fail_closed(self):
        dual = self.doc["dualSpectrometerBoundary"]
        self.assertFalse(dual["twoDifferentTrueSkyFovsMayBeCollapsedIntoOneMeasuredSpectrumForStrictPassFailWithoutCompatibilityProof"])

        background = self.doc["backgroundBoundary"]
        self.assertTrue(background["astrophysicalBackgroundTreatmentFrozen"])
        self.assertEqual(background["currentPandoraDisposition"], "ABSOLUTE_REAL_SKY_NO_ASTROPHYSICAL_SUBTRACTION_V1")
        self.assertFalse(background["subtractMatchedDeepNightSpectrumForPrimaryPassFail"])
        self.assertFalse(background["fitConstantOrSpectralOffsetToResiduals"])
        self.assertFalse(background["mayChooseBackgroundSubtractionAfterSeeingResiduals"])

        uncertainty = self.doc["uncertaintyContract"]
        self.assertTrue(uncertainty["numericPropagationAlgorithmFrozen"])
        self.assertTrue(uncertainty["numericExecutionStillRequiresPandora209ProductSemantics"])
        self.assertFalse(uncertainty["wavelengthSamplesIndependentByDefault"])
        self.assertIn("sum(abs(w_i)*sigma_i)", uncertainty["undocumentedCorrelationFallback"])
        self.assertEqual(uncertainty["unknownCoverageOrNonOneSigmaSemanticsDisposition"], "HOLD_SOURCE_SEMANTICS_UNRESOLVED_BEFORE_OPENING")

        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))


if __name__ == "__main__":
    unittest.main()
