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
            "COMPARISON_METRIC_SKELETON.review.json",
            "MODEL_FORM_ATMOSPHERE_BOUNDARY.review.json",
            "PGN_METADATA_ACQUISITION_BOUNDARY.review.json",
            "PGN_METADATA_REQUEST.md",
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
        self.assertEqual(geometry["equivalentAllowedPointingZenithAngleDeg"], [10.0, 85.0])
        self.assertFalse(geometry["zenithSkyAltitude90Accepted"])
        self.assertFalse(geometry["geometryMayBeSelectedByRadianceBrightness"])

        pairing = candidate["dualSpectrometerPairingGate"]
        self.assertTrue(pairing["requiredForFullVisibleStrictTarget"])
        self.assertTrue(pairing["pairingMustUseMetadataOnly"])
        self.assertFalse(pairing["pairBySpectralShapeOrRadianceAgreementAllowed"])
        self.assertFalse(pairing["overlapScaleFitOnValidationRadianceAllowed"])
        self.assertTrue(pairing["stitchRuleMustBeFrozenBeforeTargetValues"])

        auth = doc["authorization"]
        self.assertTrue(auth)
        self.assertTrue(all(value is False for value in auth.values()))
        next_step = doc["nextSafeTransition"]
        self.assertFalse(next_step["mayReadTargetSkyRadianceValues"])
        self.assertTrue(next_step["mayReadCalibrationAndFileHeaderMetadata"])

    def test_external_aod_and_cloud_contract_remains_independent_of_target_radiance(self):
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

        lidar = doc["coLocatedLidarEvidence"]
        self.assertEqual(lidar["site"], "Izana")
        self.assertTrue(lidar["continuousDayNight"])
        self.assertFalse(lidar["levelPreference"]["level15MayBeCalledIndependentAbsoluteAodTruth"])
        self.assertIn("AERONET", lidar["dependencyCaveat"])

        lunar = doc["nighttimeAodEvidence"]["aeronetLunarV3"]
        self.assertFalse(lunar["soleStrictAodAnchorAllowed"])

        temporal = doc["temporalLinkageGate"]
        self.assertTrue(temporal["status"].startswith("OPEN_"))
        forbidden = "\n".join(temporal["forbidden"])
        self.assertIn("model-predicted radiance", forbidden)
        self.assertIn("after seeing model residuals", forbidden)

        auth = doc["authorization"]
        self.assertTrue(all(value is False for value in auth.values()))

    def test_comparison_metrics_are_value_free_and_nonprobabilistic(self):
        doc = load_json("COMPARISON_METRIC_SKELETON.review.json")
        self.assertFalse(doc["targetRadianceOpened"])
        self.assertFalse(doc["numericAcceptanceGatesFrozen"])
        self.assertFalse(doc["numericAcceptanceGatesMayBeChosenFromObservedResiduals"])

        self.assertEqual(
            set(doc["primaryMeasuredTargets"]),
            {"photopic", "scotopic", "johnsonV"},
        )
        spectral = doc["spectralBoundary"]
        self.assertFalse(spectral["perWavelengthAerosolScenarioPassFailAllowed"])
        self.assertFalse(spectral["spectralDiagnosticMayChangePrimaryPassFailOrRetuneModel"])
        self.assertFalse(spectral["epsilonSubstitutionAllowed"])

        atmosphere = doc["atmosphereInputRepresentation"]
        self.assertEqual(atmosphere["aodSupportMustRemainWithinFrozenAsivDomain"], [0.05, 0.40])
        self.assertFalse(atmosphere["familyProbabilityWeightsAllowed"])
        self.assertFalse(atmosphere["singleFamilySelectionFromAodAloneAllowed"])
        self.assertFalse(atmosphere["fitAodOrFamilyToTargetRadianceAllowed"])

        model_set = doc["modelPredictionSet"]
        self.assertFalse(model_set["modelSetMinMaxMayBeCalledConfidenceInterval"])
        self.assertFalse(model_set["modelSetMinMaxMayBeCalledProbabilityInterval"])
        self.assertFalse(model_set["extremaRule"]["adaptiveSearchUsingObservedRadianceAllowed"])

        aggregate = doc["aggregateMetrics"]
        self.assertEqual(aggregate["unitOfPrimaryAggregation"], "session")
        self.assertFalse(aggregate["rowWeightedPrimaryAggregateAllowed"])
        self.assertTrue(aggregate["sessionFirstThenAcrossSessions"])
        self.assertFalse(aggregate["additionalDistributionSummariesMayBeAddedAfterOpening"])

        prereq = doc["passFailGatePrerequisites"]
        self.assertTrue(prereq["numericGatesMustFreezeBeforeTargetRadianceOpening"])
        self.assertFalse(prereq["numericGatesMayUsePandoraModelResidualsFromTheSelectedValidationUniverse"])
        self.assertTrue(prereq["failureAfterOpeningMustBePreserved"])
        self.assertFalse(prereq["failedValidationMayBeRetunedOnSameOpenedSessions"])

        auth = doc["authorization"]
        self.assertTrue(all(value is False for value in auth.values()))

    def test_current_model_form_is_frozen_and_not_posthoc_conditioned(self):
        doc = load_json("MODEL_FORM_ATMOSPHERE_BOUNDARY.review.json")
        runtime = doc["currentSkySurrogateRuntimeAxes"]
        self.assertTrue(runtime["sunDepressionDeg"])
        self.assertTrue(runtime["targetAltitudeDeg"])
        self.assertTrue(runtime["relativeAzimuthDeg"])
        self.assertTrue(runtime["observerElevationM"])
        self.assertTrue(runtime["aod550"])
        self.assertFalse(runtime["angstromExponentUsedByValidatedSkyPrediction"])
        self.assertFalse(runtime["precipitableWaterUsedByValidatedSkyPrediction"])
        self.assertFalse(runtime["ozoneUsedByValidatedSkyPrediction"])
        self.assertFalse(runtime["surfacePressureUsedByValidatedSkyPrediction"])
        self.assertFalse(runtime["surfaceAlbedoUsedAsRuntimeAxis"])

        frozen = doc["frozenMysticModelForm"]
        self.assertEqual(frozen["atmosphereProfile"], "AFGLUS / libRadtran atmmod/afglus.dat")
        self.assertEqual(frozen["surfaceAlbedo"], 0.15)
        self.assertEqual(frozen["molecularAbsorption"], "crs")
        self.assertEqual(frozen["solarFlux"], "libRadtran solar_flux/atlas_plus_modtran")
        self.assertEqual(frozen["aerosolBase"], "aerosol_default")
        self.assertEqual(frozen["wavelengthDomainNm"], [380.0, 780.0])

        interpretation = doc["empiricalValidationInterpretation"]
        self.assertFalse(interpretation["mayReplaceAfglusWithMeasuredAtmosphericProfileAfterSeeingResiduals"])
        self.assertFalse(interpretation["mayReplaceAlbedo015WithLocalMeasuredAlbedoAfterSeeingResiduals"])
        self.assertFalse(interpretation["mayScaleWaterVaporOrOzoneToImproveFitAfterSeeingResiduals"])
        self.assertFalse(interpretation["mayChangeAerosolVerticalProfileOrFamilyOutsideFrozenScenarioMechanismAfterSeeingResiduals"])
        self.assertTrue(interpretation["residualsCausedByFixedModelFormRemainPartOfEmpiricalError"])

        future = doc["futureModelGenerationBoundary"]
        self.assertFalse(future["sameOpenedSessionsMayTrainOrTuneReplacementModel"])
        self.assertTrue(future["replacementModelRequiresNewUntouchedHoldout"])

        auth = doc["authorization"]
        self.assertTrue(all(value is False for value in auth.values()))

    def test_pgn_metadata_acquisition_boundary_forbids_data_download(self):
        doc = load_json("PGN_METADATA_ACQUISITION_BOUNDARY.review.json")
        allowed = {row["endpointFamily"] for row in doc["allowedPreValueOperations"]}
        self.assertEqual(
            allowed,
            {"/v1/calibrationfiles", "/v1/operationfiles", "/v1/files", "/v1/metadata", "/v1/tutorial"},
        )
        forbidden = doc["forbiddenBeforeSeparateOpeningAuthorization"]
        self.assertTrue(any(row.get("endpointFamily") == "/v1/download" for row in forbidden))
        forbidden_text = "\n".join(row.get("action", "") + " " + row.get("reason", "") for row in forbidden)
        self.assertIn("LEVEL1.DATA", forbidden_text)
        self.assertIn("model agreement", forbidden_text)
        selection = doc["selectionRules"]
        self.assertTrue(selection["mayNotInspectTargetValuesToResolveMetadataAmbiguity"])
        self.assertEqual(selection["metadataAmbiguityDisposition"], "REJECT_OR_HOLD_UNRESOLVED_NOT_OPEN_VALUES")
        auth = doc["authorization"]
        self.assertTrue(auth["metadataLookupAuthorized"])
        self.assertFalse(auth["targetFileDownloadAuthorized"])
        self.assertFalse(auth["targetRadianceOpeningAuthorized"])
        self.assertFalse(auth["scientificExecutionAuthorized"])
        self.assertFalse(auth["modelRetuningAuthorized"])
        self.assertFalse(auth["productionActivationAuthorized"])

    def test_pgn_request_is_unsent_and_value_free(self):
        text = (REVIEW / "PGN_METADATA_REQUEST.md").read_text(encoding="utf-8")
        self.assertIn("draft only; not sent", text)
        self.assertIn("metadata-only", text)
        self.assertIn("Level 1 data type", text)
        self.assertIn("simultaneous or otherwise traceably paired", text)
        self.assertIn("No selected target spectral values", text)


if __name__ == "__main__":
    unittest.main()
