import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = (
    ROOT
    / "review"
    / "empirical-twilight-radiance-source-admission-v1"
    / "PGN_PANDORA209_CURRENT_CALIBRATION_REPORT_EVIDENCE.review.json"
)


class PgnPandora209CurrentCalibrationReportV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_current_s2_izana_1_9_5_rows_are_bound(self):
        rows = {row["reportId"]: row for row in self.doc["pandora209CurrentRows"]}
        self.assertEqual(rows["ID1801"]["panId"], 209)
        self.assertEqual(rows["ID1801"]["spectrometer"], 2)
        self.assertEqual(rows["ID1801"]["location"], "Izana")
        self.assertEqual(rows["ID1801"]["purpose"], "AnaLab")
        self.assertEqual(rows["ID1801"]["softwareVersion"], "1.9.5")
        self.assertEqual(rows["ID1806"]["spectrometer"], 2)
        self.assertEqual(rows["ID1806"]["location"], "Izana")
        self.assertEqual(rows["ID1806"]["purpose"], "AnaFld")
        self.assertEqual(rows["ID1806"]["softwareVersion"], "1.9.5")

    def test_missing_fields_cannot_be_reinterpreted_as_completed_cf_steps(self):
        rows = {row["reportId"]: row for row in self.doc["pandora209CurrentRows"]}
        id1801 = rows["ID1801"]
        self.assertIn("NewCF", id1801["missingStep4FieldsInclude"])
        self.assertIn("CFapproved", id1801["missingStep5FieldsInclude"])
        self.assertIn("CFavailable", id1801["missingStep5FieldsInclude"])
        strict = self.doc["strictInterpretation"]
        self.assertFalse(strict["provesACompletedOperationalS2CalibrationFileExists"])
        self.assertFalse(strict["provesNewCfWasGeneratedForId1801"])
        self.assertFalse(strict["provesCfApprovedForId1801"])
        self.assertFalse(strict["provesCfAvailableForId1801"])

    def test_current_activity_does_not_close_scientific_traceability_gates(self):
        strict = self.doc["strictInterpretation"]
        self.assertTrue(strict["provesCurrentPandora209Spectrometer2CalibrationAnalysisExistsAtIzana"])
        self.assertTrue(strict["provesCurrentPandora209Spectrometer2UsesBlick1_9_5InThoseCalibrationSessions"])
        self.assertTrue(strict["supportsSafeP1_8BackendBeingIncompleteOrStaleForCurrentS2CalibrationWork"])
        self.assertFalse(strict["provesS2AbsoluteSkyRadianceTraceability"])
        self.assertFalse(strict["provesS2AbsoluteSensitivityUncertainty"])
        self.assertFalse(strict["provesS2CalibratedWavelengthValidity"])
        self.assertFalse(strict["provesAnS2CfIsBoundToTheUnopenedTwilightTargetData"])
        self.assertFalse(strict["mayAuthorizeTargetOpening"])

    def test_blindness_boundary_remains_closed(self):
        boundary = self.doc["blindnessBoundary"]
        self.assertTrue(boundary["publicCalibrationStatusReportRead"])
        self.assertFalse(boundary["measurementFileOpened"])
        self.assertFalse(boundary["targetMetadataWholeResponseOpened"])
        self.assertFalse(boundary["targetRadianceOpened"])
        self.assertFalse(boundary["targetUncertaintyArrayOpened"])
        self.assertFalse(boundary["targetChannelDerived"])
        self.assertFalse(boundary["targetResidualInspected"])


if __name__ == "__main__":
    unittest.main()
