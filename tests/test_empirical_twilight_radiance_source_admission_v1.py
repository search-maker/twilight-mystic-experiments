import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "empirical-twilight-radiance-source-admission-v1"


def load_json(name):
    return json.loads((REVIEW / name).read_text(encoding="utf-8"))


class EmpiricalTwilightRadianceSourceAdmissionV1Tests(unittest.TestCase):
    def test_review_package_files_exist(self):
        for name in (
            "source-admission.review.json",
            "AOD_QC_PRECONTRACT.review.json",
            "AOD_QC_NUMERIC_LINKAGE_V1.review.json",
            "BASE_MODEL_SUPPORT_PREVALUE_GATE.review.json",
            "COMPARISON_METRIC_SKELETON.review.json",
            "SET_VALUED_ACCEPTANCE_GATES.review.json",
            "MEASUREMENT_CHANNEL_INTEGRATION_BINDING.review.json",
            "GEOMETRY_PAIRING_STITCH_PRECONTRACT.review.json",
            "MODEL_FORM_ATMOSPHERE_BOUNDARY.review.json",
            "PGN_METADATA_ACQUISITION_BOUNDARY.review.json",
            "PGN_METADATA_REQUEST.md",
            "PGN_METADATA_REQUEST_DISPATCH.review.json",
            "certified_aod_scenario_extrema_v1.py",
            "exact_aod_interval_support_v1.py",
            "README.md",
        ):
            self.assertTrue((REVIEW / name).is_file(), name)

    def test_source_admission_remains_fail_closed(self):
        doc = load_json("source-admission.review.json")
        candidate = doc["primaryCandidate"]
        self.assertFalse(candidate["targetRadianceValuesOpenedForThisValidation"])
        gate = candidate["absoluteRadianceAdmissionGate"]
        self.assertEqual(gate["requiredL1DataTypeCode"], 2)
        self.assertEqual(gate["requiredMeaning"], "radiance")
        self.assertEqual(gate["requiredUnits"], "W/m2/nm/sr")
        self.assertFalse(gate["correctedCountRateTypeCode1AcceptedForStrictValidation"])
        self.assertFalse(gate["irradianceTypeCode3AcceptedForDirectionalSkyRadianceValidation"])
        geometry = candidate["geometryAdmissionGate"]
        self.assertEqual(geometry["requiredSunDepressionDeg"], [2.0, 10.5])
        self.assertEqual(geometry["requiredTargetAltitudeDeg"], [5.0, 80.0])
        self.assertFalse(geometry["zenithSkyAltitude90Accepted"])
        self.assertFalse(geometry["geometryMayBeSelectedByRadianceBrightness"])
        self.assertTrue(all(value is False for value in doc["authorization"].values()))
        self.assertFalse(doc["nextSafeTransition"]["mayReadTargetSkyRadianceValues"])
        self.assertTrue(doc["nextSafeTransition"]["mayReadCalibrationAndFileHeaderMetadata"])

    def test_external_aod_contract_remains_value_independent(self):
        doc = load_json("AOD_QC_PRECONTRACT.review.json")
        self.assertFalse(doc["targetRadianceOpened"])
        self.assertFalse(doc["aod550MayBeFitFromTargetRadiance"])
        support = doc["frozenAsivAodSupport"]
        self.assertEqual(support["minimumAod550"], 0.05)
        self.assertEqual(support["maximumAod550"], 0.40)
        self.assertFalse(support["maySelectSessionsByPandoraResidualOrBrightness"])
        anchor = doc["primaryQuantitativeAodAnchor"]
        self.assertEqual(anchor["qualityLevelRequired"], "Level 2.0")
        self.assertFalse(anchor["nearRealTimeLevel15MayReplaceLevel2"])
        self.assertTrue(anchor["aod550Derivation"]["noRadianceFitting"])
        self.assertTrue(all(value is False for value in doc["authorization"].values()))

    def test_exact_base_model_support_is_required_before_value_opening(self):
        doc = load_json("BASE_MODEL_SUPPORT_PREVALUE_GATE.review.json")
        binding = doc["applicationBinding"]
        self.assertEqual(binding["providerId"], "level-b-v3-validated-primary")
        self.assertEqual(binding["runtimeDataSha256"], "6a927bd702ebbf1b1913ebe51731f3b92f967f2ae95edf090280b8370ea091e4")
        rule = doc["validatedSupportRule"]
        self.assertEqual(rule["maxNearestFrozenTrainingDistance"], 0.60)
        self.assertFalse(rule["nominalInBoxAloneSufficient"])
        selection = doc["preValueSelection"]
        self.assertFalse(selection["targetRadianceMayBeUsed"])
        self.assertTrue(selection["supportMustHoldAcrossEntireAodInterval"])
        self.assertFalse(selection["endpointOnlyCheckAllowedWithoutProof"])
        self.assertIn("EXACT_PAIRWISE_LOWER_ENVELOPE_V1", selection["aodIntervalSupportAlgorithm"])

    def test_comparison_metrics_and_numeric_gates_are_frozen_value_free(self):
        doc = load_json("COMPARISON_METRIC_SKELETON.review.json")
        self.assertFalse(doc["targetRadianceOpened"])
        self.assertTrue(doc["numericAcceptanceGatesFrozen"])
        self.assertFalse(doc["numericAcceptanceGatesMayBeChosenFromObservedResiduals"])
        atmosphere = doc["atmosphereInputRepresentation"]
        self.assertFalse(atmosphere["familyProbabilityWeightsAllowed"])
        self.assertFalse(atmosphere["singleFamilySelectionFromAodAloneAllowed"])
        self.assertFalse(atmosphere["fitAodOrFamilyToTargetRadianceAllowed"])
        extrema = doc["modelPredictionSet"]["extremaRule"]
        self.assertEqual(extrema["algorithmId"], "CERTIFIED_AOD_SCENARIO_EXTREMA_INTERVAL_BNB_V1")
        self.assertFalse(extrema["adaptiveSearchUsingObservedRadianceAllowed"])
        self.assertFalse(extrema["endpointOnlyExtremaAssumptionAllowed"])
        self.assertFalse(extrema["epsilonSubstitutionAllowed"])
        gates = doc["numericGates"]
        self.assertEqual(gates["perChannelEqualSessionP95SessionMeanConservativeSetMissMagMaximum"], 0.20)
        self.assertEqual(gates["worstMarginalStratumChannelP90ConservativeSetMissMagMaximum"], 0.25)
        self.assertEqual(gates["maximumSingleObservationChannelConservativeSetMissMagMaximum"], 0.60)
        self.assertEqual(gates["biasUpper95StyleSignedSetMissLogMaximum"], 0.12)
        self.assertEqual(gates["externalSigmaLogMaximum"], 0.06)
        self.assertFalse(doc["nextSafeWork"]["targetRadianceOpeningAllowed"])
        self.assertTrue(all(value is False for value in doc["authorization"].values()))

    def test_current_model_form_is_frozen_and_not_posthoc_conditioned(self):
        doc = load_json("MODEL_FORM_ATMOSPHERE_BOUNDARY.review.json")
        runtime = doc["currentSkySurrogateRuntimeAxes"]
        self.assertTrue(runtime["sunDepressionDeg"])
        self.assertTrue(runtime["targetAltitudeDeg"])
        self.assertTrue(runtime["relativeAzimuthDeg"])
        self.assertTrue(runtime["observerElevationM"])
        self.assertTrue(runtime["aod550"])
        self.assertFalse(runtime["angstromExponentUsedByValidatedSkyPrediction"])
        frozen = doc["frozenMysticModelForm"]
        self.assertEqual(frozen["surfaceAlbedo"], 0.15)
        self.assertEqual(frozen["wavelengthDomainNm"], [380.0, 780.0])
        interpretation = doc["empiricalValidationInterpretation"]
        self.assertFalse(interpretation["mayReplaceAfglusWithMeasuredAtmosphericProfileAfterSeeingResiduals"])
        self.assertTrue(interpretation["residualsCausedByFixedModelFormRemainPartOfEmpiricalError"])
        self.assertFalse(doc["futureModelGenerationBoundary"]["sameOpenedSessionsMayTrainOrTuneReplacementModel"])

    def test_pgn_metadata_boundary_forbids_data_download(self):
        doc = load_json("PGN_METADATA_ACQUISITION_BOUNDARY.review.json")
        forbidden = doc["forbiddenBeforeSeparateOpeningAuthorization"]
        self.assertTrue(any(row.get("endpointFamily") == "/v1/download" for row in forbidden))
        forbidden_text = "\n".join(row.get("action", "") + " " + row.get("reason", "") for row in forbidden)
        self.assertIn("LEVEL1.DATA", forbidden_text)
        self.assertIn("model agreement", forbidden_text)
        auth = doc["authorization"]
        self.assertTrue(auth["metadataLookupAuthorized"])
        self.assertFalse(auth["targetFileDownloadAuthorized"])
        self.assertFalse(auth["targetRadianceOpeningAuthorized"])

    def test_pgn_question_set_was_frozen_then_sent_without_target_values(self):
        text = (REVIEW / "PGN_METADATA_REQUEST.md").read_text(encoding="utf-8")
        self.assertIn("draft only; not sent", text)
        self.assertIn("metadata-only", text)
        self.assertIn("No selected target spectral values", text)
        dispatch = load_json("PGN_METADATA_REQUEST_DISPATCH.review.json")
        self.assertTrue(dispatch["requestArtifact"]["frozenBeforeDispatch"])
        self.assertTrue(dispatch["dispatch"]["userExplicitlyAuthorizedSend"])
        self.assertEqual(dispatch["requestArtifact"]["gitBlobSha1AtDispatch"], "4dfb2edb4d80c4cf91022016ebb6abe7f4cef036")
        self.assertFalse(dispatch["blindnessBoundary"]["selectedTargetSpectraAttached"])
        self.assertFalse(dispatch["blindnessBoundary"]["targetLevel1DataOpenedForThisValidation"])
        self.assertFalse(dispatch["replyHandling"]["replyMayAuthorizeTargetOpeningByItself"])


if __name__ == "__main__":
    unittest.main()
