import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "GEOMETRY_PAIRING_STITCH_PRECONTRACT.review.json"


class EmpiricalGeometryPairingStitchV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_target_values_remain_closed(self):
        self.assertFalse(self.doc["targetRadianceOpened"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))

    def test_geometry_uses_true_per_spectrometer_pointing(self):
        geometry = self.doc["geometryConvention"]
        self.assertIn("true per-spectrometer", geometry["targetDirection"])
        self.assertTrue(geometry["perSpectrometerPredictionRequired"])
        self.assertFalse(geometry["mayFitPointingToRadiance"])
        self.assertFalse(geometry["mayChooseAlternativeAzimuthConventionFromResiduals"])
        self.assertEqual(geometry["mysticDomain"]["targetAltitudeDeg"], [5.0, 80.0])

    def test_pairing_is_metadata_only_and_fail_closed(self):
        pairing = self.doc["pairingAlgorithm"]
        self.assertEqual(pairing["id"], "METADATA_IDENTITY_AND_EXPOSURE_INTERVAL_PAIRING_V1")
        self.assertFalse(pairing["pairByNearestBrightnessAllowed"])
        self.assertFalse(pairing["pairBySpectralShapeAllowed"])
        self.assertFalse(pairing["pairByModelAgreementAllowed"])
        self.assertFalse(pairing["pairByUnboundedNearestTimestampAllowed"])
        self.assertIn("HOLD_OR_REJECT", pairing["fallbackWhenNoAuthoritativePairingKey"])

    def test_stitch_is_metadata_defined_without_overlap_fit(self):
        stitch = self.doc["stitchAlgorithm"]
        self.assertEqual(stitch["id"], "METADATA_RANGE_MIDPOINT_HARD_SPLICE_V1")
        self.assertIn("arithmetic midpoint", stitch["crossoverRule"])
        self.assertFalse(stitch["interpolateAcrossCrossover"])
        self.assertFalse(stitch["fitOverlapGainOrOffset"])
        self.assertFalse(stitch["averageOverlapUsingObservedAgreement"])
        self.assertFalse(stitch["chooseCrossoverFromTargetSmoothness"])

    def test_ambiguity_cannot_be_resolved_from_validation_values(self):
        rules = self.doc["failClosedRules"]
        self.assertTrue(all(value is False for key, value in rules.items() if key != "metadataAmbiguityDisposition"))
        self.assertEqual(rules["metadataAmbiguityDisposition"], "HOLD_OR_REJECT_BEFORE_VALUE_OPENING")


if __name__ == "__main__":
    unittest.main()
