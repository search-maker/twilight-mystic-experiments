import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = ROOT / "review" / "aerosol-production-domain-v1" / "domain.review.json"
POLICY_PATH = ROOT / "review" / "aerosol-production-uncertainty-v1" / "policy.review.json"
LEVEL_B_PATH = ROOT / "review" / "level-b-v3-validated-surrogate-package-v1" / "package-v1.json"
AFPF_PROTOCOL_PATH = ROOT / "experiments" / "aerosol-full-phase-function-sensitivity-v1" / "protocol.review.json"
AFPF_REPORT_PATH = ROOT / "evidence" / "aerosol-full-phase-function-sensitivity-v1" / "ordinal38-results-report.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    payload = f"blob {len(raw)}\0".encode("ascii") + raw
    return hashlib.sha1(payload).hexdigest()


def test_aerosol_production_domain_v1_is_bound_and_fail_closed():
    domain = _load(DOMAIN_PATH)
    policy = _load(POLICY_PATH)
    level_b = _load(LEVEL_B_PATH)
    afpf = _load(AFPF_PROTOCOL_PATH)

    assert domain["status"] == "REVIEW_ONLY_DOMAIN_FREEZE_NO_PRODUCTION_AUTHORIZATION"
    assert domain["sourceBindings"]["exactReviewParentMain"] == "1a1517e6be0a18a4cc7814657cb21139b42bfb56"

    bindings = domain["sourceBindings"]
    assert _git_blob_sha1(POLICY_PATH) == bindings["aerosolUncertaintyPolicy"]["gitBlobSha1"]
    assert _git_blob_sha1(LEVEL_B_PATH) == bindings["levelBV3ValidatedSurrogatePackage"]["gitBlobSha1"]
    assert _git_blob_sha1(AFPF_PROTOCOL_PATH) == bindings["afpfProtocol"]["gitBlobSha1"]
    assert _git_blob_sha1(AFPF_REPORT_PATH) == bindings["afpfOrdinal38Report"]["gitBlobSha1"]

    base = domain["targetOperationalComputationalDomain"]
    package_box = level_b["geometryInputContract"]["validatedPhysicalDesignBox"]
    assert base["sunDepressionDeg"] == package_box["sunDepressionDeg"]
    assert base["targetAltitudeDeg"] == package_box["targetAltitudeDeg"]
    assert base["relativeAzimuthDeg"] == package_box["relativeAzimuthDeg"]
    assert base["observerElevationM"] == package_box["observerElevationM"]
    assert base["aod550"] == package_box["aod550"]
    assert base["wavelengthDomainNm"] == level_b["representation"]["wavelengthDomainNm"]
    assert base["validatedSupportRule"] == level_b["geometryInputContract"]["validatedSupportRule"]
    assert base["silentExtrapolationAllowed"] is False

    direct = domain["directAfpfAerosolEvidenceDomain"]
    frozen = afpf["fixedNumericalAndPhysicalDesign"]
    assert direct["sunDepressionDeg"] == frozen["sunDepressionDeg"]
    assert direct["aod550"] == frozen["aod550"]
    assert direct["observerElevationM"] == [frozen["observerElevationM"]]
    assert direct["geometries"] == frozen["geometries"]
    assert direct["scenarioStates"] == [state["stateId"] for state in afpf["aerosolStates"]]
    assert direct["analysisCellCount"] == 4 * 2 * 3 == afpf["caseCardinality"]["analysisCells"]
    assert direct["interpolationBetweenDirectCellsValidated"] is False
    assert direct["extrapolationFromDirectCellsValidated"] is False

    classes = domain["coverageClassification"]
    assert set(classes) == {"DIRECT_AEROSOL_EVIDENCE", "AEROSOL_COVERAGE_GAP", "BASE_MODEL_OOD"}
    assert classes["AEROSOL_COVERAGE_GAP"]["mayInterpolateScenarioEnvelope"] is False
    assert classes["AEROSOL_COVERAGE_GAP"]["mayChooseNearestAfpfCellAsTruth"] is False
    assert classes["BASE_MODEL_OOD"]["silentExtrapolationAllowed"] is False

    assert policy["productionUncertaintyPolicy"]["defaultRepresentationWhenAerosolFamilyIsNotIndependentlyValidated"] == "SET_VALUED_SCENARIO_ENVELOPE"
    assert policy["productionUncertaintyPolicy"]["singleBestAerosolFamilySelectionFromAodAloneAllowed"] is False
    assert policy["productionUncertaintyPolicy"]["equalWeightingOfScenarioStatesAllowed"] is False

    progress = domain["policyActivationProgress"]
    assert progress["productionAodDomainFrozenByThisReview"] is True
    assert progress["productionSunDepressionDomainFrozenByThisReview"] is True
    assert progress["productionViewingGeometryDomainFrozenByThisReview"] is True
    assert progress["scenarioTransportEvaluatorOrTableFrozen"] is False
    assert progress["interpolationPolicyValidated"] is False
    assert progress["productionActivationAuthorized"] is False

    next_gate = domain["ordinal39DesignImplication"]
    assert next_gate["scientificOrdinalRequested"] is False
    assert next_gate["ordinal39Allocated"] is False
    assert next_gate["solverExecutionAuthorized"] is False
    assert next_gate["mustTargetCoverageGapsRatherThanRepeatAfpfLattice"] is True
    assert next_gate["mustIncludeOffLatticeGeometry"] is True
    assert next_gate["mustIncludeObserverElevationAboveZero"] is True
    assert next_gate["exactCaseMatrixFrozen"] is False
    assert next_gate["automaticDispatchAllowed"] is False

    auth = domain["authorization"]
    assert all(value is False for value in auth.values())
