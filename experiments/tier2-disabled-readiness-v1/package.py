from __future__ import annotations

import hashlib
import json
import math
import statistics
from typing import Any

TARGET_RSEM = 0.05
ACCEPTED_MAX_RSEM = 0.08
TIER_ID = "tier-2-completion"
EXPECTED_GEOMETRIES = 48
EXPECTED_CASES = 96
EXPECTED_PHOTONS = 7_320_000_000
ALLOWED_ROLES = {"surrogate-training", "internal-holdout"}
ALLOWED_IMPORTANCE_NM = {500.0, 550.0, 600.0}
TIMEOUTS = {20_000_000: 900, 50_000_000: 1200, 100_000_000: 1800, 200_000_000: 2400}
HEX = set("0123456789abcdef")


class Refusal(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def finite_positive(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise Refusal(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise Refusal(f"{name} must be finite and positive")
    return result


def classify_rsem(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise Refusal("invalid RSEM")
    rsem = float(value)
    if not math.isfinite(rsem) or rsem < 0:
        raise Refusal("invalid RSEM")
    if rsem <= TARGET_RSEM:
        return "PRECISION_TARGET_MET"
    if rsem <= ACCEPTED_MAX_RSEM:
        return "PRECISION_ACCEPTED"
    return "ADAPTIVE_CONTINUATION_REQUIRED"


def compute_rsem(values: list[float]) -> float:
    rows = [finite_positive(item, "case value") for item in values]
    if len(rows) != 2:
        raise Refusal("exactly two Tier-2 blocks are required")
    mean = statistics.fmean(rows)
    return statistics.stdev(rows) / math.sqrt(2) / mean


def validate_runtime(runtime: dict[str, Any]) -> None:
    required = {
        "schemaVersion": 1,
        "stageId": "mystic-runtime-lock-v1",
        "solver": "uvspec",
        "libRadtranVersion": "2.0.6",
        "scientificSolverExecuted": False,
        "syntaxCheckExecuted": False,
    }
    if any(runtime.get(key) != value for key, value in required.items()):
        raise Refusal("runtime identity changed")
    hashes = runtime.get("hashes")
    expected_hashes = {
        "uvspecSha256",
        "uvspecHelpSha256",
        "libRadtranDataTreeSha256",
        "atmosphereSha256",
        "runtimeLockRawSha256",
    }
    if (
        not isinstance(hashes, dict)
        or set(hashes) != expected_hashes
        or any(not is_sha256(value) for value in hashes.values())
    ):
        raise Refusal("runtime binding incomplete")


def _validate_full_design(
    full_design: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    required = {
        "schemaVersion": 1,
        "stageId": "twilight-surrogate-training-design-v1",
        "proposalOnly": True,
        "scientificExecution": False,
        "successDoesNotAuthorizeProduction": True,
        "observationValidationRequired": True,
        "geometryCount": 96,
        "caseCount": 192,
        "blocksPerGeometry": 2,
    }
    stale = {
        key: (full_design.get(key), value)
        for key, value in required.items()
        if full_design.get(key) != value
    }
    if stale:
        raise Refusal(f"full design changed: {stale}")
    tiers = full_design.get("executionTiers")
    matches = (
        [item for item in tiers if isinstance(item, dict) and item.get("tierId") == TIER_ID]
        if isinstance(tiers, list)
        else []
    )
    if len(matches) != 1:
        raise Refusal("Tier-2 summary missing or duplicated")
    tier = matches[0]
    required_tier = {
        "geometryCount": EXPECTED_GEOMETRIES,
        "caseCount": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "scientificExecution": False,
    }
    if any(tier.get(key) != value for key, value in required_tier.items()):
        raise Refusal("Tier-2 frozen summary changed")
    geometry_ids = tier.get("geometryIds")
    case_ids = tier.get("caseIds")
    if (
        not isinstance(geometry_ids, list)
        or len(geometry_ids) != EXPECTED_GEOMETRIES
        or len(set(geometry_ids)) != EXPECTED_GEOMETRIES
    ):
        raise Refusal("Tier-2 geometry IDs changed")
    if (
        not isinstance(case_ids, list)
        or len(case_ids) != EXPECTED_CASES
        or len(set(case_ids)) != EXPECTED_CASES
    ):
        raise Refusal("Tier-2 case IDs changed")
    geometry_set = set(geometry_ids)
    case_set = set(case_ids)
    geometries = [
        item for item in full_design.get("geometries", []) if item.get("geometryId") in geometry_set
    ]
    cases = [item for item in full_design.get("cases", []) if item.get("caseId") in case_set]
    if len(geometries) != EXPECTED_GEOMETRIES or len(cases) != EXPECTED_CASES:
        raise Refusal("Tier-2 selection is incomplete")
    if {item["geometryId"] for item in geometries} != geometry_set or {
        item["caseId"] for item in cases
    } != case_set:
        raise Refusal("Tier-2 selection mismatch")
    return tier, geometries, cases


def _validate_partition(
    full_design: dict[str, Any], geometries: list[dict[str, Any]], cases: list[dict[str, Any]]
) -> None:
    geometry_ids = {item["geometryId"] for item in geometries}
    training = set(full_design.get("trainingGeometryIds", [])) & geometry_ids
    holdout = set(full_design.get("internalHoldoutGeometryIds", [])) & geometry_ids
    if training & holdout or training | holdout != geometry_ids:
        raise Refusal("Tier-2 holdout split changed")
    grouped: dict[str, list[dict[str, Any]]] = {}
    seeds: set[int] = set()
    photon_sum = 0
    ordinals: list[int] = []
    for case in cases:
        if (
            case.get("executionTierId") != TIER_ID
            or case.get("role") not in ALLOWED_ROLES
            or case.get("method") != "alis"
        ):
            raise Refusal("Tier-2 role, method, or tier changed")
        group_id = case.get("groupId")
        if group_id not in geometry_ids:
            raise Refusal("Tier-2 case references another geometry")
        expected_role = "internal-holdout" if group_id in holdout else "surrogate-training"
        if case.get("role") != expected_role:
            raise Refusal("Tier-2 role differs from frozen split")
        if case.get("block") not in {1, 2}:
            raise Refusal("Tier-2 block changed")
        seed = case.get("seed")
        if not isinstance(seed, int) or seed <= 910_096 or seed in seeds:
            raise Refusal("Tier-2 seed boundary changed")
        photons = case.get("photonHistories")
        if photons not in TIMEOUTS:
            raise Refusal("Tier-2 photon allocation changed")
        importance = float(case.get("alisSpectralImportanceSamplingNm", -1))
        if importance not in ALLOWED_IMPORTANCE_NM:
            raise Refusal("Tier-2 importance wavelength changed")
        ordinal = case.get("ordinal")
        if not isinstance(ordinal, int):
            raise Refusal("Tier-2 ordinal missing")
        seeds.add(seed)
        photon_sum += photons
        ordinals.append(ordinal)
        grouped.setdefault(group_id, []).append(case)
    if photon_sum != EXPECTED_PHOTONS:
        raise Refusal("Tier-2 photon accounting changed")
    if len(grouped) != EXPECTED_GEOMETRIES or any(
        sorted(case["block"] for case in rows) != [1, 2] for rows in grouped.values()
    ):
        raise Refusal("Tier-2 two-block contract changed")
    if ordinals != sorted(ordinals) or len(set(ordinals)) != EXPECTED_CASES:
        raise Refusal("Tier-2 ordinal order changed")


def build(full_design: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    validate_runtime(runtime)
    tier, geometries, cases = _validate_full_design(full_design)
    _validate_partition(full_design, geometries, cases)
    sorted_geometries = sorted(geometries, key=lambda item: item["geometryId"])
    sorted_cases = sorted(cases, key=lambda item: item["ordinal"])
    matrix = [
        {
            "case_id": case["caseId"],
            "ordinal": case["ordinal"],
            "seed": case["seed"],
            "photon_histories": case["photonHistories"],
            "timeout_seconds": TIMEOUTS[case["photonHistories"]],
            "role": case["role"],
            "alis_importance_nm": case["alisSpectralImportanceSamplingNm"],
        }
        for case in sorted_cases
    ]
    geometry_ids = {geometry["geometryId"] for geometry in geometries}
    package = {
        "schemaVersion": 1,
        "stageId": "tier2-disabled-readiness-v1",
        "status": "READY_DISABLED_PENDING_SEPARATE_SCIENTIFIC_DECISION",
        "proposalOnly": True,
        "scientificExecution": False,
        "automaticTrigger": False,
        "automaticTier2Decision": False,
        "authorizationEnabled": False,
        "authorizationOrdinalAllocated": False,
        "geometryCount": EXPECTED_GEOMETRIES,
        "caseCount": EXPECTED_CASES,
        "blocksPerGeometry": 2,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "maximumParallel": 8,
        "executionTierId": TIER_ID,
        "purpose": tier.get("purpose"),
        "runtimeBindingSha256": canonical_sha256(runtime),
        "sourceDesignSha256": canonical_sha256(full_design),
        "sourceSpecBinding": full_design.get("sourceSpecBinding"),
        "parameterRanges": full_design.get("parameterRanges"),
        "photonSchedule": full_design.get("photonSchedule"),
        "importanceSamplingPolicy": full_design.get("importanceSamplingPolicy"),
        "trainingGeometryIds": sorted(
            set(full_design.get("trainingGeometryIds", [])) & geometry_ids
        ),
        "internalHoldoutGeometryIds": sorted(
            set(full_design.get("internalHoldoutGeometryIds", [])) & geometry_ids
        ),
        "geometries": sorted_geometries,
        "cases": sorted_cases,
        "matrix": matrix,
        "perCaseContract": {
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
            "artifactRequired": True,
            "runtimeHashRequired": True,
            "inputHashRequired": True,
            "outputHashRequired": True,
            "firstAttemptOnly": True,
        },
        "precisionThresholds": {
            "targetMaximum": TARGET_RSEM,
            "acceptedMaximum": ACCEPTED_MAX_RSEM,
            "classifications": [
                "PRECISION_TARGET_MET",
                "PRECISION_ACCEPTED",
                "ADAPTIVE_CONTINUATION_REQUIRED",
            ],
        },
        "continuationAutomaticallyAuthorized": False,
        "modelFittingAuthorized": False,
        "productionPromotionAuthorized": False,
        "observationValidationRequired": True,
        "boundary": "disabled execution readiness only; Tier-2 remains contingent on a separate post-Tier-1 scientific decision",
    }
    package["packageSha256"] = canonical_sha256(package)
    return package


def regenerate(full_design: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    first = build(full_design, runtime)
    second = build(json.loads(json.dumps(full_design)), json.loads(json.dumps(runtime)))
    if first != second:
        raise Refusal("Tier-2 regeneration is not deterministic")
    return first


def source_audit(
    full_design: dict[str, Any], runtime: dict[str, Any], package: dict[str, Any]
) -> dict[str, Any]:
    rebuilt = regenerate(full_design, runtime)
    if rebuilt != package:
        raise Refusal("Tier-2 package does not match frozen sources")
    return {
        "schemaVersion": 1,
        "stageId": "tier2-disabled-readiness-source-audit-v1",
        "status": "PASSED",
        "sourceDesignSha256": canonical_sha256(full_design),
        "runtimeBindingSha256": canonical_sha256(runtime),
        "packageSha256": package["packageSha256"],
        "geometryCount": EXPECTED_GEOMETRIES,
        "caseCount": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "deterministicRegenerationPassed": True,
        "automaticTier2Decision": False,
        "authorizationEnabled": False,
        "productionPromotionAuthorized": False,
    }


def authorization_template(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "stageId": "tier2-disabled-authorization-template-v1",
        "enabled": False,
        "authorizationOrdinal": None,
        "executionKey": None,
        "authorizationCommit": None,
        "packageSha256": package.get("packageSha256", canonical_sha256(package)),
        "automaticTrigger": False,
        "tier2DecisionRecorded": False,
        "onePurposeCommitRequired": True,
        "firstAttemptOnly": True,
        "githubRerunAllowed": False,
    }


def authorization_proposal(
    package: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    required = {
        "status": "TIER_2_EXECUTION_SEPARATELY_APPROVED",
        "tier1DatasetComplete": True,
        "requiredContinuationComplete": True,
        "surrogateFitFrozen": True,
        "internalHoldoutReviewed": True,
        "hardAnchorReportReviewed": True,
        "independentScientificReviewComplete": True,
        "automaticDecision": False,
    }
    if any(decision.get(key) != value for key, value in required.items()):
        raise Refusal("separate Tier-2 decision prerequisites not met")
    if not is_sha256(decision.get("decisionDocumentSha256")):
        raise Refusal("Tier-2 decision document hash missing")
    return {
        "schemaVersion": 1,
        "stageId": "tier2-authorization-proposal-v1",
        "status": "PROPOSAL_ONLY_NOT_ACTIVE_AUTHORIZATION",
        "packageSha256": package["packageSha256"],
        "decisionDocumentSha256": decision["decisionDocumentSha256"],
        "authorizationEnabled": False,
        "authorizationOrdinalAllocated": False,
        "onePurposeAuthorizationCommitRequired": True,
        "automaticDispatch": False,
        "githubRerunAllowed": False,
        "productionPromotionAuthorized": False,
    }


def refuse_duplicate_execution(
    package: dict[str, Any], prior_runs: list[dict[str, Any]]
) -> None:
    for run in prior_runs:
        if not isinstance(run, dict):
            raise Refusal("invalid prior run")
        if run.get("packageSha256") == package.get("packageSha256"):
            raise Refusal("duplicate Tier-2 package execution")
        requested = run.get("requestedOrdinal")
        if requested is not None and requested == run.get("authorizationOrdinal"):
            raise Refusal("Tier-2 authorization ordinal already consumed")


def aggregate(
    package: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, Any]:
    expected = {case["caseId"]: case for case in package.get("cases", [])}
    if len(expected) != EXPECTED_CASES:
        raise Refusal("Tier-2 package case universe invalid")
    seen: set[str] = set()
    values: dict[str, list[float]] = {}
    index: list[dict[str, str]] = []
    completed_photons = 0
    for result in results:
        if not isinstance(result, dict):
            raise Refusal("invalid Tier-2 result")
        case_id = result.get("caseId")
        case = expected.get(case_id)
        if case is None or case_id in seen:
            raise Refusal("duplicate or unplanned Tier-2 result")
        seen.add(case_id)
        required = {
            "seed": case["seed"],
            "role": case["role"],
            "photonHistories": case["photonHistories"],
            "alisSpectralImportanceSamplingNm": case[
                "alisSpectralImportanceSamplingNm"
            ],
            "status": "COMPLETED",
            "syntaxCheckCount": 1,
            "solverExecutionCount": 1,
        }
        if any(result.get(key) != value for key, value in required.items()):
            raise Refusal("Tier-2 per-case invariant changed")
        syntax = result.get("syntax")
        solver = result.get("solver")
        if (
            not isinstance(syntax, dict)
            or syntax.get("exitCode") != 0
            or syntax.get("timedOut") is not False
        ):
            raise Refusal("Tier-2 syntax check failed")
        if (
            not isinstance(solver, dict)
            or solver.get("exitCode") != 0
            or solver.get("timedOut") is not False
        ):
            raise Refusal("Tier-2 solver failed")
        for name in (
            "artifactSha256",
            "inputSha256",
            "outputSha256",
            "runtimeSha256",
        ):
            if not is_sha256(result.get(name)):
                raise Refusal("Tier-2 artifact contract failed")
        value = finite_positive(result.get("valueCdM2"), "Tier-2 result value")
        values.setdefault(case["groupId"], []).append(value)
        completed_photons += case["photonHistories"]
        index.append(
            {"caseId": case_id, "artifactSha256": result["artifactSha256"]}
        )
    if seen != set(expected):
        raise Refusal("missing Tier-2 results")
    if completed_photons != EXPECTED_PHOTONS:
        raise Refusal("Tier-2 completed photon accounting failed")
    if len(values) != EXPECTED_GEOMETRIES or any(
        len(group) != 2 for group in values.values()
    ):
        raise Refusal("Tier-2 result block contract failed")
    return {
        "schemaVersion": 1,
        "stageId": "tier2-disabled-aggregate-v1",
        "status": "COMPLETED",
        "classification": "TIER_2_NUMERICALLY_COMPLETE_UNCLASSIFIED",
        "packageSha256": package["packageSha256"],
        "caseCountPlanned": EXPECTED_CASES,
        "caseCountCompleted": EXPECTED_CASES,
        "configuredMcPhotonsSum": EXPECTED_PHOTONS,
        "completedConfiguredMcPhotonsSum": completed_photons,
        "valuesByGeometry": {key: values[key] for key in sorted(values)},
        "caseIndex": sorted(index, key=lambda item: item["caseId"]),
        "modelFittingAuthorized": False,
        "productionPromotionAuthorized": False,
    }


def independent_audit(
    package: dict[str, Any],
    aggregate_result: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    rebuilt = aggregate(package, results)
    if rebuilt != aggregate_result:
        raise Refusal("Tier-2 aggregate does not reproduce independently")
    return {
        "schemaVersion": 1,
        "stageId": "tier2-disabled-independent-audit-v1",
        "status": "PASSED",
        "packageSha256": package["packageSha256"],
        "aggregateSha256": canonical_sha256(aggregate_result),
        "caseResultCount": EXPECTED_CASES,
        "seedValidationPassed": True,
        "hashValidationPassed": True,
        "photonAccountingPassed": True,
        "duplicateRefusalPassed": True,
        "firstAttemptRequired": True,
        "modelFittingAuthorized": False,
        "productionPromotionAuthorized": False,
    }


def precision_analysis(
    package: dict[str, Any], aggregate_result: dict[str, Any], audit: dict[str, Any]
) -> dict[str, Any]:
    if aggregate_result.get("status") != "COMPLETED" or audit.get("status") != "PASSED":
        raise Refusal("Tier-2 aggregate or audit failed")
    if (
        aggregate_result.get("packageSha256") != package.get("packageSha256")
        or audit.get("packageSha256") != package.get("packageSha256")
    ):
        raise Refusal("Tier-2 analysis provenance mismatch")
    roles = {case["groupId"]: case["role"] for case in package["cases"]}
    rows = []
    for geometry_id, values in sorted(
        aggregate_result["valuesByGeometry"].items()
    ):
        value = compute_rsem(values)
        rows.append(
            {
                "geometryId": geometry_id,
                "role": roles[geometry_id],
                "blockCount": 2,
                "relativeStandardErrorOfMean": value,
                "classification": classify_rsem(value),
            }
        )
    return {
        "schemaVersion": 1,
        "stageId": "tier2-disabled-precision-analysis-v1",
        "status": "TIER_2_PRECISION_ANALYZED_NO_AUTOMATIC_ACTION",
        "thresholds": package["precisionThresholds"],
        "points": rows,
        "adaptiveContinuationRequiredGeometryIds": [
            row["geometryId"]
            for row in rows
            if row["classification"] == "ADAPTIVE_CONTINUATION_REQUIRED"
        ],
        "automaticContinuation": False,
        "automaticTier2Expansion": False,
        "modelFittingAuthorized": False,
        "productionPromotionAuthorized": False,
    }
