from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

STAGE_ID = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
SOURCE_STAGE_ID = "aerosol-family-challenge-v2-r8"
SOURCE_MANIFEST_RAW_SHA256 = "c031d6daf6a0e37240b93786394036d12bebecbba7894b6aebbad62b45a2016f"
SOURCE_RUN_ID = 32447101887
SOURCE_AUTHORIZATION_HEAD = "cca5194a5b81ea28ca9cc8417b5887936afa1fd6"
SOURCE_SCIENTIFIC_ORDINAL = 34
SOURCE_FAILED_JOB_ID = 96669314294
FAILED_GROUP_ID = "afc2-d04-g06-late-opposite-high-aerosol-aod10-r2"
FAILED_CASE_ID = FAILED_GROUP_ID + "-rural-fall-winter"
SOURCE_GROUP_SEED = 798398324
SOURCE_OBSERVER_BRANCH = "status/r8-cancel-observer-v2-result"
SOURCE_OBSERVER_SUMMARY_PATH = "observer-result-v2/summary.json"
SOURCE_OBSERVER_SUMMARY_GIT_BLOB_SHA1 = "83eb8e7210d993e9ca6cc034f3a89027c8a0dc3e"
SOURCE_CANCELLED_JOB_DETAIL_PATH = "observer-result-v2/cancelled-job-detail.json"
SOURCE_CANCELLED_JOB_DETAIL_GIT_BLOB_SHA1 = "597d62e6fb13919fa74191eaceafcc65f5ede2be"
SOURCE_CANCELLED_JOB_ANNOTATIONS_PATH = "observer-result-v2/cancelled-job-annotations.json"
SOURCE_CANCELLED_JOB_ANNOTATIONS_GIT_BLOB_SHA1 = "09bff57b4f02a5a5270013a8e4b2874d1bc5a661"
SOURCE_TIMEOUT_ANNOTATION = "The job has exceeded the maximum execution time of 45m0s"
SOURCE_ANALYSIS_CONTRACT_RAW_SHA256 = "9221fe6dee3450073ea77eac801b9bc1fb71c92a9bd4589201a474e0467e733a"
SOURCE_ANALYSIS_IMPLEMENTATION_RAW_SHA256 = "4fce489c2fb326ebbc9bba65d4163f26e406b3e190b7bfba87cd2797786de2aa"
SOURCE_DERIVED_CHANNELS_RAW_SHA256 = "1e36fb42815be1b646f713087a4c9ff72109e71f8a68fc8797c495978ee54bd4"
RECOVERY_SEED_LEDGER_RAW_SHA256 = "e3817c8d2e354c0e2f84bc00a41f40a841ef5263abb1cf91fa1f330ea9064c20"
RECOVERY_SEED_NAMESPACE = "aerosol-family-challenge-v2|r8-timeout-recovery|group-seed|sha256-v1"
RECOVERY_SEED = 371960104
RECOVERY_SEED_COUNTER = 0
EXPECTED_STATE_COUNT = 8
EXPECTED_RETAINED_CASE_COUNT = 568
EXPECTED_EFFECTIVE_CASE_COUNT = 576
EXPECTED_PHOTON_HISTORIES_PER_CASE = 20_000_000
RECOVERY_SOLVER_TIMEOUT_SECONDS = 7200
RECOVERY_JOB_TIMEOUT_MINUTES = 150

FAMILIES = ("rural", "maritime", "urban", "tropospheric")
SEASONS = ("spring-summer", "fall-winter")


class RecoveryRefusal(RuntimeError):
    pass


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def derive_recovery_seed(counter: int = RECOVERY_SEED_COUNTER) -> tuple[int, str, str]:
    material = f"{RECOVERY_SEED_NAMESPACE}|groupId={FAILED_GROUP_ID}|counter={counter}"
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    seed = (int.from_bytes(digest[:8], "big") % (2_147_483_647 - 1)) + 1
    return seed, material, hashlib.sha256(material.encode("utf-8")).hexdigest()


def protocol_self_hash(protocol: dict[str, Any]) -> str:
    value = copy.deepcopy(protocol)
    value["reviewSelfSha256"] = None
    return canonical_sha256(value)


def validate_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    if protocol.get("schemaVersion") != 1 or protocol.get("stageId") != STAGE_ID:
        raise RecoveryRefusal("recovery protocol identity drift")
    if protocol.get("status") != "REVIEW_ONLY_PREREGISTERED_NO_EXECUTION":
        raise RecoveryRefusal("recovery protocol is not review-only")
    for key in (
        "scientificExecutionAuthorized",
        "solverExecutionAuthorized",
        "dispatchAuthorized",
        "resultsOpened",
    ):
        if protocol.get(key) is not False:
            raise RecoveryRefusal(f"review protocol opened forbidden boundary: {key}")
    if protocol.get("reviewSelfSha256") != protocol_self_hash(protocol):
        raise RecoveryRefusal("recovery protocol self hash mismatch")

    source = protocol.get("sourceFailure")
    expected_source = {
        "stageId": SOURCE_STAGE_ID,
        "runId": SOURCE_RUN_ID,
        "workflowRunAttempt": 1,
        "authorizationHead": SOURCE_AUTHORIZATION_HEAD,
        "scientificOrdinal": SOURCE_SCIENTIFIC_ORDINAL,
        "manifestRawSha256": SOURCE_MANIFEST_RAW_SHA256,
        "failedJobId": SOURCE_FAILED_JOB_ID,
        "failedCaseId": FAILED_CASE_ID,
        "failedGroupId": FAILED_GROUP_ID,
        "sourceGroupSeed": SOURCE_GROUP_SEED,
        "classification": "EXECUTION_FAILURE_PLATFORM_JOB_TIMEOUT_AFTER_INTERNAL_PROCESS_TREE_TIMEOUT_FAILED_TO_CONTAIN_DESCENDANTS",
        "successfulCaseArtifacts": 575,
        "failedOrMissingCaseArtifacts": 1,
        "scientificChannelsOpened": False,
    }
    if source != expected_source:
        raise RecoveryRefusal("source failure binding drift")

    expected_evidence = {
        "observerResultBranch": SOURCE_OBSERVER_BRANCH,
        "observerSummaryPath": SOURCE_OBSERVER_SUMMARY_PATH,
        "observerSummaryGitBlobSha1": SOURCE_OBSERVER_SUMMARY_GIT_BLOB_SHA1,
        "cancelledJobDetailPath": SOURCE_CANCELLED_JOB_DETAIL_PATH,
        "cancelledJobDetailGitBlobSha1": SOURCE_CANCELLED_JOB_DETAIL_GIT_BLOB_SHA1,
        "cancelledJobAnnotationsPath": SOURCE_CANCELLED_JOB_ANNOTATIONS_PATH,
        "cancelledJobAnnotationsGitBlobSha1": SOURCE_CANCELLED_JOB_ANNOTATIONS_GIT_BLOB_SHA1,
        "githubTimeoutAnnotationMessage": SOURCE_TIMEOUT_ANNOTATION,
    }
    if protocol.get("sourceEvidenceBindings") != expected_evidence:
        raise RecoveryRefusal("source evidence binding drift")

    expected_source_analysis = {
        "analysisContractRawSha256": SOURCE_ANALYSIS_CONTRACT_RAW_SHA256,
        "analysisImplementationRawSha256": SOURCE_ANALYSIS_IMPLEMENTATION_RAW_SHA256,
        "derivedChannelsRawSha256": SOURCE_DERIVED_CHANNELS_RAW_SHA256,
    }
    if protocol.get("sourceAnalysisBindings") != expected_source_analysis:
        raise RecoveryRefusal("source analysis binding drift")

    expected_authorization_boundary = {
        "attempt1Only": True,
        "authorizationPrMustRemainDraftOpenUnmerged": True,
        "freshAuthorizationCommitRequired": True,
        "freshIndependentSeedGlobalAuditRequired": True,
        "freshMonotonicScientificOrdinalRequired": True,
        "sourceArtifactsImmutable": True,
        "sourceOrdinal34NeverReusable": True,
    }
    if protocol.get("authorizationBoundary") != expected_authorization_boundary:
        raise RecoveryRefusal("authorization boundary drift")

    retention = protocol.get("retentionAndReplacement")
    expected_retention = {
        "retainRule": f"source ordinal 34 case artifact iff groupId != {FAILED_GROUP_ID}",
        "retainedSourceCaseCount": EXPECTED_RETAINED_CASE_COUNT,
        "excludedSourceGroupCount": 1,
        "excludedSourceCaseCount": EXPECTED_STATE_COUNT,
        "excludedCompletedSourceCaseCount": 7,
        "excludedMissingSourceCaseCount": 1,
        "freshReplacementCaseCount": EXPECTED_STATE_COUNT,
        "effectiveCombinedCaseCount": EXPECTED_EFFECTIVE_CASE_COUNT,
        "reuseSourceResultsFromAffectedGroup": False,
    }
    if retention != expected_retention:
        raise RecoveryRefusal("retention/replacement rule drift")

    recovery = protocol.get("recoveryGroup")
    derived_seed, material, material_sha = derive_recovery_seed()
    if derived_seed != RECOVERY_SEED:
        raise RecoveryRefusal("hard-coded recovery seed no longer matches derivation")
    expected_recovery = {
        "groupId": FAILED_GROUP_ID,
        "analysisCellId": "afc2-d04-g06-late-opposite-high-aerosol-aod10",
        "replicate": 2,
        "freshGroupSeed": RECOVERY_SEED,
        "seedDerivationNamespace": RECOVERY_SEED_NAMESPACE,
        "seedCollisionCounter": RECOVERY_SEED_COUNTER,
        "seedDerivationMaterial": material,
        "seedDerivationMaterialSha256": material_sha,
        "candidateSeedLedgerRawSha256": RECOVERY_SEED_LEDGER_RAW_SHA256,
        "caseCount": EXPECTED_STATE_COUNT,
        "photonHistoriesPerCase": EXPECTED_PHOTON_HISTORIES_PER_CASE,
        "sunDepressionDeg": 4.0,
        "targetAltitudeDeg": 45.0,
        "relativeAzimuthDeg": 180.0,
        "observerElevationM": 0.0,
        "aod550": 0.1,
        "albedo": 0.15,
        "physicsChange": "NONE",
    }
    if recovery != expected_recovery:
        raise RecoveryRefusal("recovery group drift")

    timeout = protocol.get("timeoutPolicy")
    expected_timeout = {
        "sourceSolverTimeoutSeconds": 1800,
        "sourceGithubJobTimeoutMinutes": 45,
        "recoverySolverTimeoutSeconds": RECOVERY_SOLVER_TIMEOUT_SECONDS,
        "recoveryGithubJobTimeoutMinutes": RECOVERY_JOB_TIMEOUT_MINUTES,
        "processGroupIsolationRequired": True,
        "timeoutMustTerminateDescendantProcessGroup": True,
        "sigtermGraceSeconds": 5,
        "sigkillFallbackRequired": True,
        "timeoutIsExecutionFailureNotScientificResult": True,
        "noRetryNoResumeNoGithubRerun": True,
    }
    if timeout != expected_timeout:
        raise RecoveryRefusal("timeout policy drift")

    analysis = protocol.get("combinedAnalysisPlan")
    if not isinstance(analysis, dict):
        raise RecoveryRefusal("combined analysis plan missing")
    expected_analysis = {
        "sourceRetainedCaseCount": 568,
        "freshReplacementCaseCount": 8,
        "effectiveCaseCount": 576,
        "comparisonGroupCount": 72,
        "analysisCellCount": 24,
        "replicateCountPerCell": 3,
        "replacementOccupiesOriginalReplicateSlot": 2,
        "baseline": {"aerosolFamily": "rural", "aerosolSeason": "spring-summer"},
        "pairedCommonRandomNumbersWithinReplacementGroup": True,
        "primaryContrasts": "UNCHANGED_R8_LOG_RATIOS",
        "uncertainty": "UNCHANGED_R8_THREE_REPLICATE_MEAN_SAMPLE_SD_SE",
        "nonpositiveHandling": "NUMERICALLY_UNRESOLVED_NO_EPSILON",
        "pValuesOrConfidenceIntervalsPermitted": False,
        "postResultRuleChangePermitted": False,
    }
    if analysis != expected_analysis:
        raise RecoveryRefusal("combined analysis rule drift")
    return protocol


def build_recovery_manifest(protocol: dict[str, Any], source_manifest: dict[str, Any]) -> dict[str, Any]:
    validate_protocol(protocol)
    if source_manifest.get("stageId") != SOURCE_STAGE_ID or source_manifest.get("caseCount") != 576:
        raise RecoveryRefusal("source R8 manifest identity/cardinality drift")
    cases = source_manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 576:
        raise RecoveryRefusal("source R8 manifest case universe drift")
    source_group = [copy.deepcopy(row) for row in cases if row.get("groupId") == FAILED_GROUP_ID]
    if len(source_group) != EXPECTED_STATE_COUNT:
        raise RecoveryRefusal("source failed CRN group must contain exactly eight states")
    states = {(row.get("aerosolFamily"), row.get("aerosolSeason")) for row in source_group}
    if states != {(family, season) for family in FAMILIES for season in SEASONS}:
        raise RecoveryRefusal("source failed group state universe drift")
    if {row.get("seed") for row in source_group} != {SOURCE_GROUP_SEED}:
        raise RecoveryRefusal("source failed group seed drift")
    if {row.get("photonHistories") for row in source_group} != {EXPECTED_PHOTON_HISTORIES_PER_CASE}:
        raise RecoveryRefusal("source failed group photon budget drift")

    recovery_cases: list[dict[str, Any]] = []
    for row in sorted(source_group, key=lambda x: str(x["caseId"])):
        original_case_id = str(row["caseId"])
        row["sourceOrdinal34CaseId"] = original_case_id
        row["sourceOrdinal34Seed"] = SOURCE_GROUP_SEED
        row["seed"] = RECOVERY_SEED
        row["recoveryStageId"] = STAGE_ID
        row["recoveryReason"] = "ORDINAL34_SINGLE_CASE_PLATFORM_TIMEOUT_REPLACE_ENTIRE_CRN_GROUP"
        recovery_cases.append(row)

    retained = [row for row in cases if row.get("groupId") != FAILED_GROUP_ID]
    if len(retained) != EXPECTED_RETAINED_CASE_COUNT:
        raise RecoveryRefusal("retained source case count drift")

    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FROZEN_TARGETED_TIMEOUT_RECOVERY_MANIFEST_NOT_AUTHORIZED",
        "sourceStageId": SOURCE_STAGE_ID,
        "sourceRunId": SOURCE_RUN_ID,
        "sourceScientificOrdinal": SOURCE_SCIENTIFIC_ORDINAL,
        "sourceAuthorizationHead": SOURCE_AUTHORIZATION_HEAD,
        "sourceManifestRawSha256": SOURCE_MANIFEST_RAW_SHA256,
        "failedGroupId": FAILED_GROUP_ID,
        "sourceGroupSeed": SOURCE_GROUP_SEED,
        "freshGroupSeed": RECOVERY_SEED,
        "caseCount": EXPECTED_STATE_COUNT,
        "groupCount": 1,
        "retainedSourceCaseCountForFutureCombinedAnalysis": EXPECTED_RETAINED_CASE_COUNT,
        "effectiveCombinedCaseCount": EXPECTED_EFFECTIVE_CASE_COUNT,
        "solverTimeoutSeconds": RECOVERY_SOLVER_TIMEOUT_SECONDS,
        "githubJobTimeoutMinutes": RECOVERY_JOB_TIMEOUT_MINUTES,
        "cases": recovery_cases,
        "sourceBindings": {
            "r8AnalysisContractRawSha256": SOURCE_ANALYSIS_CONTRACT_RAW_SHA256,
            "r8AnalysisImplementationRawSha256": SOURCE_ANALYSIS_IMPLEMENTATION_RAW_SHA256,
            "r8DerivedChannelsRawSha256": SOURCE_DERIVED_CHANNELS_RAW_SHA256,
            "runtimeLock": copy.deepcopy(source_manifest.get("sourceBindings", {}).get("runtimeLock")),
        },
        "boundary": {
            "scientificExecutionAuthorized": False,
            "solverExecutionAuthorized": False,
            "dispatchAuthorized": False,
            "resultsOpened": False,
            "freshScientificOrdinalRequired": True,
            "freshAuthorizationRequired": True,
            "githubRerunRetryResumeAllowed": False,
        },
    }
