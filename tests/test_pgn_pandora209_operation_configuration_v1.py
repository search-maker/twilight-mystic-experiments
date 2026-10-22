import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = (
    ROOT
    / "review"
    / "empirical-twilight-radiance-source-admission-v1"
    / "PGN_PANDORA209_OPERATION_CONFIGURATION_EVIDENCE.review.json"
)


class PgnPandora209OperationConfigurationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_exact_public_operation_files_and_hashes_are_bound(self):
        files = {item["filename"]: item for item in self.doc["files"]}
        self.assertEqual(
            set(files),
            {
                "Pandora209_OF_v0d20210806.txt",
                "Pandora209_OF_v1d20210806.txt",
                "Pandora209_OF_v2d20210806.txt",
                "Pandora209_OF_v3d20210806.txt",
            },
        )
        self.assertEqual(
            files["Pandora209_OF_v0d20210806.txt"]["sha256"],
            "53a008a47cf587265cdc5016aa12ec2cc879c3538ce611b050346b050c623540",
        )
        self.assertEqual(
            files["Pandora209_OF_v1d20210806.txt"]["sha256"],
            "4c3fd8d0733dcc4c076839d9156959ec32d975df82162b681f527106a313a491",
        )
        self.assertEqual(
            files["Pandora209_OF_v2d20210806.txt"]["sha256"],
            "5377a75c16db2295f0542cbce8288e91481d58016d61583e37cd5cf20aad3bba",
        )
        self.assertEqual(
            files["Pandora209_OF_v3d20210806.txt"]["sha256"],
            "201b3327b0f1f6c66002d859bc1a7a485caf146711ba24f1f27acb03155e0fd8",
        )

    def test_two_spectrometer_hardware_identity_is_exact(self):
        mapping = self.doc["stableInstrumentMappingAcrossAllFourFiles"]
        self.assertEqual(mapping["instrumentNumber"], 209)
        self.assertEqual(mapping["spectrometer1"]["unitId"], "2106511U1")
        self.assertEqual(mapping["spectrometer2"]["unitId"], "2106510U1")
        self.assertEqual(mapping["spectrometer1"]["pixelCount"], 2048)
        self.assertEqual(mapping["spectrometer2"]["pixelCount"], 2048)
        self.assertNotEqual(
            mapping["spectrometer1"]["unitId"], mapping["spectrometer2"]["unitId"]
        )

    def test_nominal_fov_tracker_and_filterwheel_configuration_is_exact(self):
        mapping = self.doc["stableInstrumentMappingAcrossAllFourFiles"]
        self.assertEqual(mapping["spectrometer1"]["referenceSkyFov"]["fwhmDegrees"], 1.5)
        self.assertEqual(mapping["spectrometer2"]["referenceSkyFov"]["fwhmDegrees"], 1.5)
        self.assertEqual(mapping["headSensorTracker"]["trackerResolutionDegreesPerStep"], 0.01)
        self.assertEqual(mapping["skyFovCutoffAngleDegrees"], [8.0, 8.0])
        self.assertEqual(
            mapping["filterwheel1Positions"],
            {
                "1": "OPEN",
                "2": "OPEN",
                "3": "POL0",
                "4": "OPEN",
                "5": "ND2",
                "6": "POL240",
                "7": "OPAQUE",
                "8": "ND3",
                "9": "POL120",
            },
        )
        self.assertEqual(
            mapping["filterwheel2Positions"],
            {
                "1": "OPEN",
                "2": "DIFF",
                "3": "OPEN",
                "4": "OPEN",
                "5": "DIFF",
                "6": "OPAQUE",
                "7": "U340",
                "8": "U340+DIFF",
                "9": "BP300",
            },
        )

    def test_filename_v2_internal_version_one_is_preserved_not_corrected(self):
        files = {item["filename"]: item for item in self.doc["files"]}
        v2 = files["Pandora209_OF_v2d20210806.txt"]
        self.assertEqual(v2["internalDataFileVersion"], "1")
        self.assertTrue(v2["filenameVersionInternalVersionMismatchPreserved"])
        interpretation = self.doc["strictInterpretation"]
        self.assertFalse(interpretation["filenameVersionInternalVersionMismatchMayBeSilentlyCorrected"])
        self.assertIn("Data file version -> 1", interpretation["v2MismatchExactSourceFact"])

    def test_operation_configuration_does_not_close_observation_or_calibration_gates(self):
        interpretation = self.doc["strictInterpretation"]
        self.assertTrue(interpretation["closesInstrumentHasTwoDistinctSpectrometerHardwareIdentities"])
        self.assertTrue(interpretation["closesNominalReferenceFovAndTrackerHardwareConfiguration"])
        self.assertFalse(interpretation["closesPerObservationTrueSkyFovPointing"])
        self.assertFalse(interpretation["closesPerObservationFilterPositionOrRoutine"])
        self.assertFalse(interpretation["closesWhichOperationFileWasActiveForEachObservation"])
        self.assertFalse(interpretation["closesS1S2ExposurePairing"])
        self.assertFalse(interpretation["closesS2AbsoluteSkyRadianceCalibrationTraceability"])
        self.assertFalse(interpretation["closesCurrentCalibratedWavelengthValidity"])
        self.assertFalse(interpretation["closesMeasurementUncertaintySemantics"])
        self.assertFalse(interpretation["nominalFovMaySubstituteForTruePerObservationPointing"])

    def test_blindness_boundary_remains_closed(self):
        boundary = self.doc["blindnessBoundary"]
        self.assertTrue(boundary["publicOperationConfigurationContentOpened"])
        self.assertFalse(boundary["measurementFileOpened"])
        self.assertFalse(boundary["targetMetadataWholeResponseOpened"])
        self.assertFalse(boundary["targetRadianceOpened"])
        self.assertFalse(boundary["targetUncertaintyArrayOpened"])
        self.assertFalse(boundary["targetChannelDerived"])
        self.assertFalse(boundary["targetResidualInspected"])


if __name__ == "__main__":
    unittest.main()
