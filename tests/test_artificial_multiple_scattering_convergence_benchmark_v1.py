import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "review" / "night-background-source-admission-v1" / "artificial-multiple-scattering-convergence-benchmark-v1.json"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_external_reference_identity_and_nonpromotion_boundary():
    data = load_contract()
    assert data["schemaVersion"] == 1
    assert data["contractId"] == "artificial-multiple-scattering-convergence-benchmark-v1"
    artifact = data["externalReferenceArtifact"]
    assert artifact["record"] == 8251646
    assert artifact["doi"] == "10.5281/zenodo.8251646"
    assert artifact["file"] == "MSOS_LP1_WIN.zip"
    assert artifact["publishedMd5"] == "a1890a5da0ae9a1704c77cffba73007c"
    assert artifact["sourceCodePubliclyAuditableFromThisRecord"] is False
    assert artifact["publishedMd5IsEquivalentToProjectVerifiedByteSha256"] is False
    assert artifact["projectVerifiedByteSha256"] is None
    assert artifact["projectRuntimeReproduced"] is False
    assert data["providerAdmissionBoundary"]["msosExecutableMayBecomeProductionProvider"] is False
    assert data["providerAdmissionBoundary"]["productionAuthorized"] is False


def test_published_baseline_scene_is_bound_exactly():
    data = load_contract()
    scene = data["publishedBaselineScene"]
    aerosol = scene["aerosol"]
    assert aerosol == {
        "asymmetryParameter": 0.75,
        "singleScatteringAlbedo": 0.95,
        "aod500": 0.3,
        "angstromExponent": 1.3,
        "scaleHeightKm": 1.5,
    }
    assert scene["groundAlbedo"] == 0.15
    assert scene["directUpwardEmissionFraction"] == 0.1
    assert scene["publishedSourceAzimuthDeg"] == 294.0
    assert scene["principalWavelengthsNm"] == [450, 550]
    assert scene["publishedDistanceAnchorsKm"] == [20, 60]
    assert scene["publishedAllSkyMorphologyDistanceKm"] == 3.8
    assert scene["planeParallelCloudlessAtmosphere"] is True


def test_common_scene_and_residual_blind_matrix_rules_are_fail_closed():
    data = load_contract()
    stages = data["benchmarkStages"]
    stage_b = stages["B_COMMON_SCENE_INTERSECTION"]
    assert stage_b["mustCompleteBeforeIlluminaErrorCalculation"] is True
    assert any("NONCOMPARABLE" in rule for rule in stage_b["requirements"])
    stage_c = stages["C_PUBLISHED_STRESS_ANCHORS"]
    assert stage_c["residualBlind"] is True
    assert stage_c["wavelengthsNm"] == [450, 550]
    assert stage_c["sourceDistancesKm"] == [20, 60]
    assert stage_c["viewingDirections"] == ["ZENITH"]
    assert "all_available_higher_order_terms" in stage_c["requiredOutputs"]
    stage_d = stages["D_INTENDED_DOMAIN_ENVELOPE"]
    assert stage_d["mayUseTaylorJerusalemResidualsForCellSelection"] is False
    assert "Freeze the full matrix before opening any cross-solver difference" in stage_d["rule"]


def test_reference_convergence_does_not_promote_fixed_order_as_truth():
    data = load_contract()
    conv = data["referenceConvergenceSemantics"]
    assert conv["tenOrdersAutomaticallyCalledExactTruth"] is False
    assert conv["eightOrdersAutomaticallyCalledUniversalTruth"] is False
    assert "REFERENCE_NOT_CONVERGED" in conv["referenceMayBeCalledConvergedOnlyAfter"]
    assert "I1 + I2" in conv["twoOrderErrorDefinition"]
    assert "no epsilon substitution" in conv["zeroOrNonfiniteReferenceTreatment"]


def test_no_post_result_threshold_or_residual_tuning_is_authorized():
    data = load_contract()
    basis = data["scientificBasis"]["convergenceAssessment"]
    assert basis["projectMayConvertPublishedTenPercentExampleIntoFinalProviderAcceptanceThreshold"] is False
    boundary = data["providerAdmissionBoundary"]
    assert boundary["illuminaTwoOrderAutomaticallyRejectedForEveryCondition"] is False
    assert boundary["illuminaTwoOrderAutomaticallyAcceptedForLowAod"] is False
    assert boundary["finalNumericalToleranceFrozenHere"] is False
    assert "independent uncertainty budget" in boundary["reasonFinalNumericalToleranceNotFrozenHere"]
    prohibited = data["prohibitions"]
    assert prohibited["TaylorResidualTuning"] is True
    assert prohibited["JerusalemResidualTuning"] is True
    assert prohibited["artificialSkyMeasurementResidualTuning"] is True
    assert prohibited["postResultMatrixEditing"] is True
    assert prohibited["epsilonSubstitutionForZeroReference"] is True
    assert prohibited["callingPublishedMd5AProjectByteVerification"] is True
    assert prohibited["callingBlackBoxExecutableSourceAudited"] is True
