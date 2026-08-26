import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1" / "PGN_L1_GEOMS_METADATA_SEMANTICS.review.json"


class PgnL1GeomsMetadataSemanticsV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_target_values_remain_closed(self):
        self.assertFalse(self.doc["targetRadianceOpened"])
        fields = self.doc["documentedFields"]
        self.assertTrue(fields["LEVEL1.DATA"]["targetArray"])
        self.assertFalse(fields["LEVEL1.DATA"]["openingBeforeSeparateAuthorizationAllowed"])
        self.assertFalse(fields["LEVEL1.UNCERTAINTY"]["openingBeforeSeparateAuthorizationAllowed"])
        self.assertFalse(fields["LEVEL1.UNCERTAINTY.INSTRUMENT"]["openingBeforeSeparateAuthorizationAllowed"])
        self.assertTrue(all(value is False for value in self.doc["authorization"].values()))

    def test_documented_level1_type_codes_are_exact(self):
        codes = self.doc["documentedFields"]["LEVEL1.DATA.TYPE"]["codes"]
        self.assertEqual(codes["1"], "corrected count rate [s^-1]")
        self.assertEqual(codes["2"], "radiance [W/m2/nm/sr]")
        self.assertEqual(codes["3"], "irradiance [W/m2/nm]")

    def test_documented_time_and_pointing_fields_are_frozen(self):
        fields = self.doc["documentedFields"]
        self.assertEqual(fields["DATETIME.START"]["encoding"], "fractional days since 2000-01-01")
        self.assertEqual(fields["DURATION"]["unit"], "s")
        self.assertEqual(fields["POINTING.AZIMUTH.ANGLE"]["unit"], "deg")
        self.assertEqual(fields["POINTING.ZENITH.ANGLE"]["unit"], "deg")
        self.assertEqual(fields["POINTING.AZIMUTH.MODE"]["documentedCodes"], {
            "0": "absolute",
            "1": "relative to sun",
            "2": "relative to moon",
        })
        self.assertEqual(fields["POINTING.ZENITH.MODE"]["documentedCodes"], {
            "0": "absolute",
            "1": "relative to sun",
            "2": "relative to moon",
        })

    def test_unknown_conversion_pairing_and_calibration_remain_fail_closed(self):
        unresolved = "\n".join(self.doc["stillUnresolvedAndMustFailClosed"])
        self.assertIn("sign/reference convention", unresolved)
        self.assertIn("true per-spectrometer pointing", unresolved)
        self.assertIn("pairing key", unresolved)
        self.assertIn("absolute sky-radiance calibration chain", unresolved)
        boundary = self.doc["selectionBoundary"]
        self.assertFalse(boundary["mayResolveUnknownPointingConventionByTryingAlternativesAgainstRadiance"])
        self.assertFalse(boundary["mayResolveS1S2PairingBySpectralAgreement"])


if __name__ == "__main__":
    unittest.main()
