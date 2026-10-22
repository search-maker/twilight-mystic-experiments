import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = (
    ROOT
    / "review"
    / "empirical-twilight-radiance-source-admission-v1"
    / "PGN_PANDORA209S1_CALIBRATION_CONFIGURATION_EVIDENCE.review.json"
)


class PgnPandora209S1CalibrationConfigurationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_exact_static_availability_is_preserved(self):
        rows = {item["filename"]: item for item in self.doc["exactStaticAvailability"]}
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows["Pandora209s1_CF_v1d20220309.txt"]["httpStatus"], 200)
        self.assertEqual(rows["Pandora209s1_CF_v1d20220324.txt"]["httpStatus"], 200)
        self.assertEqual(rows["Pandora209s1_CF_v4d20221111.txt"]["httpStatus"], 200)
        self.assertEqual(rows["Pandora209s1_CF_v5d20220720.txt"]["httpStatus"], 200)
        self.assertEqual(rows["Pandora209s1_CF_v8d20230220.txt"]["httpStatus"], 404)
        self.assertTrue(rows["Pandora209s1_CF_v8d20230220.txt"]["apiIdentityStillPubliclyListed"])
        self.assertFalse(
            rows["Pandora209s1_CF_v8d20230220.txt"][
                "scientificAdmissionMayInterpretStatic404AsCalibrationInvalidity"
            ]
        )

    def test_open_open_is_absolute_unit_sensitivity_but_not_traceability_proof(self):
        semantics = self.doc["sensitivitySemantics"]
        self.assertEqual(semantics["uniqueSensitivityTypes"], [0, 101, 102, 103, 104, 105, 106])
        self.assertTrue(semantics["allNonzeroSensitivityTypesHaveAbsoluteValueAbove100"])
        open_open = semantics["openOpenFilterCombination"]
        self.assertEqual(open_open["filterwheel2Position"], 1)
        self.assertEqual(open_open["filterwheel1Position"], 1)
        self.assertEqual(open_open["operationConfigurationLabels"], ["OPEN", "OPEN"])
        self.assertEqual(open_open["sensitivityType"], 101)
        self.assertEqual(open_open["usesSensitivityIndex"], 1)
        self.assertTrue(open_open["configuredForAbsoluteUnitSensitivity"])
        strict = semantics["strictInterpretation"]
        self.assertTrue(strict["provesS1IcfIsConfiguredWithAbsoluteUnitSensitivityForOpenOpen"])
        self.assertFalse(strict["provesIndependentTraceabilityChainOrCertificateIdentity"])
        self.assertFalse(strict["provesAbsoluteSensitivityUncertaintyOrCovariance"])

    def test_safe_l1_metadata_binds_actual_cf_usage_without_version_guessing(self):
        binding = self.doc["safeL1MetadataBinding"]
        self.assertEqual(binding["s1MetadataRowCount"], 1471)
        self.assertEqual(binding["code"], "smca1")
        self.assertEqual(binding["blickpVersion"], "p1-8")
        usage = binding["actualCfUsageByMetadata"]
        self.assertEqual(
            [(row["cfVersion"], row["cfDate"], row["rowCount"]) for row in usage],
            [(5, "2022-07-20", 114), (4, "2022-11-11", 94), (8, "2023-02-20", 1263)],
        )
        self.assertFalse(binding["mayInferUsageByHighestVersionOrLatestStaticFile"])
        self.assertTrue(binding["authoritativeSafeMetadataShowsV8UsedThroughLatestListedS1L1Date"])

    def test_s1_visible_range_does_not_close_full_visible_channels(self):
        consequences = self.doc["visibleBandConsequences"]
        self.assertEqual(consequences["widestRetrievedS1OpenSensitivityUpperLimitNm"], 538.6)
        self.assertFalse(consequences["s1AloneCanCoverFrozen380To780FullVisibleIntegration"])
        self.assertFalse(consequences["s1AloneCanClosePhotopicScotopicOrJohnsonVFullPassbands"])
        self.assertTrue(consequences["fullVisibleLaneStillRequiresS2OrAnotherAuthoritativelyCalibratedLongWavelengthSource"])

    def test_admission_and_blindness_gates_remain_closed(self):
        consequences = self.doc["strictAdmissionConsequences"]
        self.assertTrue(consequences["s1AbsoluteUnitConfigurationEvidenceNowStrong"])
        self.assertFalse(consequences["s1IndependentAbsoluteSkyRadianceTraceabilityClosed"])
        self.assertFalse(consequences["s1AbsoluteSensitivityUncertaintyClosed"])
        self.assertFalse(consequences["s1CurrentV8CalibrationContentClosed"])
        self.assertFalse(consequences["s2CalibrationTraceabilityOrValidityClosed"])
        self.assertFalse(consequences["mayUseS1ConfigurationToInferS2Calibration"])
        self.assertFalse(consequences["targetOpeningAuthorized"])
        boundary = self.doc["blindnessBoundary"]
        self.assertTrue(boundary["publicCalibrationConfigurationOpened"])
        self.assertTrue(boundary["safeL1FileListMetadataOpened"])
        self.assertFalse(boundary["measurementFileOpened"])
        self.assertFalse(boundary["targetRadianceOpened"])
        self.assertFalse(boundary["targetUncertaintyArrayOpened"])
        self.assertFalse(boundary["targetChannelDerived"])
        self.assertFalse(boundary["targetResidualInspected"])


if __name__ == "__main__":
    unittest.main()
