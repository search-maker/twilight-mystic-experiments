import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "AOD_QC_NUMERIC_LINKAGE_V1.review.json"


class EmpiricalAodQcNumericLinkageV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_aeronet_is_absolute_anchor_and_not_residual_selected(self):
        anchor = self.doc["absoluteAodAnchor"]
        self.assertEqual(anchor["requiredQualityLevel"], "2.0")
        self.assertFalse(anchor["otherDayAnchorAllowed"])
        self.assertFalse(anchor["chooseAnchorByModelAgreementAllowed"])
        self.assertIn("never fit", anchor["aod550Conversion"])

    def test_mplnet_is_temporal_bridge_not_independent_truth(self):
        bridge = self.doc["temporalBridge"]
        self.assertIn("without treating MPLNET as an independent", bridge["role"])
        self.assertIn("must not be combined", bridge["dependency"])
        self.assertIn("two times the nominal averaging interval", bridge["continuityRule"])
        self.assertFalse(bridge["chooseSamplesByPandoraResidualAllowed"])

    def test_interval_propagation_is_conservative_and_value_free(self):
        interval = self.doc["intervalPropagation"]
        self.assertIn("aeronetAnchorCentral + (mplTargetCentral - mplAnchorCentral)", interval["bridgeCentral"])
        self.assertIn("conservative interval arithmetic", interval["bridgeUncertainty"])
        self.assertFalse(interval["postHocResidualBasedInflationAllowed"])
        self.assertFalse(interval["postHocResidualBasedNarrowingAllowed"])

    def test_final_interval_must_fit_domain_and_exact_support(self):
        admission = self.doc["admission"]
        self.assertEqual(admission["aodPhysicalDomain"], [0.05, 0.40])
        self.assertTrue(admission["entireFinalIntervalMustRemainInsidePhysicalDomain"])
        self.assertEqual(admission["entireFinalIntervalMustPassExactBaseSupportAlgorithm"], "EXACT_PAIRWISE_LOWER_ENVELOPE_V1")
        self.assertFalse(admission["clampingAllowed"])

    def test_cloud_qc_is_fail_closed_and_independent(self):
        cloud = self.doc["cloudQc"]
        self.assertFalse(cloud["mplnet"]["absenceAloneProvesWholeSkyClear"])
        self.assertTrue(cloud["sona"]["targetDirectionMustBeAssessable"])
        self.assertFalse(cloud["pandoraBrightnessOrResidualMayDetermineCloudState"])
        self.assertIn("missing/ambiguous", cloud["combined"])

    def test_target_radiance_and_fitting_remain_unauthorized(self):
        self.assertFalse(self.doc["targetRadianceOpened"])
        auth = self.doc["authorization"]
        self.assertTrue(auth["metadataAcquisitionAuthorized"])
        self.assertFalse(auth["targetRadianceOpeningAuthorized"])
        self.assertFalse(auth["scientificExecutionAuthorized"])
        self.assertFalse(auth["fitAodToTargetRadianceAuthorized"])
        self.assertFalse(auth["modelRetuningAuthorized"])
        self.assertFalse(auth["productionActivationAuthorized"])


if __name__ == "__main__":
    unittest.main()
