import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = (
    ROOT
    / "review"
    / "empirical-twilight-radiance-source-admission-v1"
    / "PGN_BLICK_FILE_CHAIN_SEMANTICS.review.json"
)


class PgnBlickFileChainSemanticsV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_documented_chain_fields_are_frozen(self):
        fields = self.doc["documentedFields"]
        self.assertEqual(fields["Spectrometer number"]["meaning"], "1 for spectrometer 1 and 2 for spectrometer 2")
        self.assertTrue(fields["Instrument operation file used"]["thereforePresentInL0"])
        self.assertTrue(fields["Instrument operation file used"]["thereforePresentInL1"])
        self.assertTrue(fields["Instrument calibration file used"]["thereforePresentInL1"])
        self.assertTrue(fields["Level 0 file used"]["thereforePresentInL1"])

    def test_file_chain_may_not_be_guessed_from_dates_or_versions(self):
        consequences = self.doc["preValueConsequences"]
        self.assertFalse(consequences["mayInferActiveOperationFileByLatestFilenameDate"])
        self.assertFalse(consequences["mayInferActiveOperationFileByHighestPublicVersion"])
        self.assertFalse(consequences["mayInferActiveCalibrationFileByLatestPublicCalibrationFilename"])
        self.assertTrue(consequences["authoritativeProductCarriesExactOperationFileIdentity"])
        self.assertTrue(consequences["authoritativeL1CarriesExactCalibrationFileIdentity"])
        self.assertTrue(consequences["authoritativeL1CarriesExactSourceL0Identity"])
        self.assertTrue(consequences["doNotUseTargetRadianceToResolveFileChain"])

    def test_current_pandora209_values_remain_unopened(self):
        boundary = self.doc["currentPandora209Boundary"]
        self.assertTrue(boundary["operationConfigurationFilesThemselvesHaveBeenOpenedAsPublicConfiguration"])
        self.assertFalse(boundary["exactPerObservationInstrumentOperationFileUsedValueOpened"])
        self.assertFalse(boundary["exactPerObservationInstrumentCalibrationFileUsedValueOpened"])
        self.assertFalse(boundary["exactPerObservationLevel0FileUsedValueOpened"])
        self.assertFalse(boundary["wholeV1MetadataEndpointAllowed"])
        self.assertFalse(boundary["mayOpenL0OrL1MeasurementFileToRecoverOnlyTheseFields"])
        self.assertIn("column_sums", boundary["wholeV1MetadataEndpointReason"])


if __name__ == "__main__":
    unittest.main()
