import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "review" / "koomen-direct-mystic-confirmation-v1" / "DIRECT_MYSTIC_CONFIRMATION_PRECONTRACT.review.json"


def test_review_only_direct_mystic_confirmation_design_is_frozen_and_unauthorized():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schemaVersion"] == 1
    assert data["stageId"] == "koomen-direct-mystic-confirmation-v1"
    assert data["status"] == "REVIEW_ONLY_NOT_AUTHORIZED_FOR_SCIENTIFIC_EXECUTION"

    source = data["source"]
    assert source["publishedValuesAlreadyOpen"] is True
    assert source["untouchedHoldout"] is False
    assert source["pandoraTargetDataUsed"] is False

    selection = data["selection"]
    assert selection["selectedBeforeCertifiedShapeOutcomeIsKnown"] is True
    assert selection["selectionUsesObservedResidualMagnitude"] is False
    assert selection["sunDepressionDeg"] == [3.0, 6.0]
    assert selection["targetAltitudeDeg"] == [30.0, 70.0]
    assert selection["relativeAzimuthDeg"] == [90.0, 180.0]
    assert selection["observerElevationM"] == 30.0
    assert selection["geometryCaseCountPerAodScenario"] == 8

    atmosphere = data["atmosphereGrid"]
    assert atmosphere["aod550"] == [0.05, 0.15, 0.40]
    assert atmosphere["aerosolScenarios"] == [
        "native", "continental", "maritime", "desert", "desert_spheroids"
    ]
    assert atmosphere["pairedSameAodAndScenarioAcross3And6Deg"] is True

    execution = data["proposedExecution"]
    assert execution["caseCount"] == 120
    assert execution["photonHistoriesPerCase"] == 20_000_000
    assert execution["totalPhotonHistories"] == 2_400_000_000
    assert execution["replicatesPerCase"] == 1
    assert execution["mcStandardDeviationRequired"] is True
    assert execution["precisionGateForInterpretation"]["pairedLogRatioMcSigmaMax"] == 0.02

    diagnostic = data["primaryDiagnostic"]
    assert diagnostic["sameAodRequired"] is True
    assert diagnostic["sameAerosolScenarioRequired"] is True

    limits = data["claimLimits"]
    assert limits["modernStrictRealSkyValidationAuthorized"] is False
    assert limits["historicalDiagnosticOnly"] is True
    assert limits["modelRetuningAuthorized"] is False
    assert limits["pandoraOpeningAuthorized"] is False
    assert limits["productionActivationAuthorized"] is False

    authorization = data["authorization"]
    assert authorization == {
        "scientificExecutionAuthorized": False,
        "ordinalAssigned": False,
        "seedLedgerFrozen": False,
        "executionManifestFrozen": False,
        "runtimeReverified": False,
    }
