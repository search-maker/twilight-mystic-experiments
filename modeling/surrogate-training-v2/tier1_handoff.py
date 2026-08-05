#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

SOURCE_STAGE = "twilight-surrogate-tier-1-execution-v1"
PLAN_STAGE = "mystic-batch-v1"
ANALYSIS_STAGE = "twilight-surrogate-tier-1-analysis-v1"
ANALYSIS_STAGE_V2 = "twilight-surrogate-tier-1-analysis-v2"
REFERENCE_STAGE = "twilight-model-readiness-v1"
ENVELOPE_STAGE = "twilight-surrogate-tier-1-dataset-envelope-v1"
GEOMETRY_COUNT = 48
CASE_COUNT = 96
PHOTON_COUNT = 6_960_000_000
TARGET_RSEM = 0.05
ACCEPTED_MAX_RSEM = 0.08
ALLOWED_ROLES = {"surrogate-training", "internal-holdout"}
ALLOWED_IMPORTANCE_NM = {500.0, 550.0, 600.0}
GEOMETRY_FIELDS = (
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthDeg",
    "observerElevationM",
    "aod550",
)
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


class HandoffRefusal(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise HandoffRefusal(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_raw_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise HandoffRefusal(f"{label} must be lowercase raw sha256")
    return value


def require_git_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise HandoffRefusal(f"{label} must be lowercase 40-character git sha")
    return value


def finite(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise HandoffRefusal(f"{label} must be finite numeric")
    number = float(value)
    if positive and number <= 0:
        raise HandoffRefusal(f"{label} must be positive")
    if nonnegative and number < 0:
        raise HandoffRefusal(f"{label} must be non-negative")
    return number


def exact(value: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    changed = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if changed:
        raise HandoffRefusal(f"{label} boundary changed: {changed}")


def numerically_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-30)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(numerically_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(numerically_equal(left[key], right[key]) for key in left)
    return left == right


def v2_statistics_from_audit(case_ids: list[str], audit: dict[str, Any]) -> dict[str, Any]:
    raw_evidence = audit.get("rawCaseEvidence")
    if not isinstance(raw_evidence, dict):
        raise HandoffRefusal("audit v2 raw case evidence missing")
    node_rows: list[list[float]] = []
    values: list[float] = []
    for case_id in case_ids:
        evidence = raw_evidence.get(case_id)
        radiance = evidence.get("radiance") if isinstance(evidence, dict) else None
        nodes = radiance.get("selectedNodeValues") if isinstance(radiance, dict) else None
        if not isinstance(nodes, list) or len(nodes) != 15:
            raise HandoffRefusal(f"audit v2 raw selected nodes missing: {case_id}")
        parsed = [finite(node, f"audit.{case_id}.node", nonnegative=True) for node in nodes]
        node_rows.append(parsed)
        values.append(683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(parsed, CIE)))
    count = len(values)
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values) if count > 1 else 0.0
    zero_count = sum(value == 0.0 for value in values)
    if zero_count or mean == 0.0:
        raise HandoffRefusal("eligible v2 point contains raw zero-hit evidence")
    return {
        "blockCount": count,
        "valuesCdM2": values,
        "meanCdM2": mean,
        "sampleStdCdM2": sample_std,
        "relativeStandardErrorOfMean": (sample_std / math.sqrt(count)) / mean,
        "relativeStandardErrorStatus": "COMPUTED",
        "zeroHitBlockCount": 0,
        "zeroHitBlockFraction": 0.0,
        "nonzeroBlockValuesCdM2": values,
        "nodeMeanRadiance": [statistics.fmean(row[index] for row in node_rows) for index in range(15)],
    }


def validate_geometry(value: Any, label: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise HandoffRefusal(f"{label} geometry missing")
    result = {key: finite(value.get(key), f"{label}.{key}", nonnegative=True) for key in GEOMETRY_FIELDS}
    if result["targetAltitudeDeg"] > 90 or result["relativeAzimuthDeg"] > 180:
        raise HandoffRefusal(f"{label} geometry outside frozen domain")
    return result


def validate_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str]]:
    exact(
        manifest,
        {
            "schemaVersion": 1,
            "stageId": SOURCE_STAGE,
            "proposalOnly": True,
            "scientificExecution": False,
            "successDoesNotAuthorizeProduction": True,
            "surrogateTrainingAutomaticallyAuthorized": False,
            "productionModelReady": False,
        },
        "manifest",
    )
    geometries = manifest.get("geometries")
    cases = manifest.get("cases")
    training_ids = manifest.get("trainingGeometryIds")
    holdout_ids = manifest.get("internalHoldoutGeometryIds")
    if not isinstance(geometries, list) or len(geometries) != GEOMETRY_COUNT:
        raise HandoffRefusal("manifest geometry count changed")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise HandoffRefusal("manifest case count changed")
    if not isinstance(training_ids, list) or not isinstance(holdout_ids, list):
        raise HandoffRefusal("manifest partition missing")
    if len(training_ids) != 39 or len(holdout_ids) != 9:
        raise HandoffRefusal("manifest 39/9 partition changed")
    if len(set(training_ids)) != 39 or len(set(holdout_ids)) != 9 or set(training_ids) & set(holdout_ids):
        raise HandoffRefusal("manifest partition duplicated or overlapping")

    geometry_by_id: dict[str, Any] = {}
    for item in geometries:
        if not isinstance(item, dict) or not isinstance(item.get("geometryId"), str):
            raise HandoffRefusal("manifest geometry ID missing")
        geometry_id = item["geometryId"]
        if geometry_id in geometry_by_id:
            raise HandoffRefusal(f"duplicate manifest geometry: {geometry_id}")
        validate_geometry(item, geometry_id)
        geometry_by_id[geometry_id] = item
    if set(geometry_by_id) != set(training_ids) | set(holdout_ids):
        raise HandoffRefusal("manifest geometry universe differs from partition")

    case_by_id: dict[str, Any] = {}
    seeds: set[int] = set()
    photons = 0
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in cases:
        if not isinstance(item, dict):
            raise HandoffRefusal("manifest case must be object")
        case_id = item.get("caseId")
        group_id = item.get("groupId")
        seed = item.get("seed")
        photon_histories = item.get("photonHistories")
        importance = item.get("alisSpectralImportanceSamplingNm")
        role = item.get("role")
        if not isinstance(case_id, str) or not case_id or case_id in case_by_id:
            raise HandoffRefusal(f"manifest case ID duplicated or missing: {case_id}")
        if group_id not in geometry_by_id:
            raise HandoffRefusal(f"manifest case geometry missing: {case_id}")
        expected_role = "surrogate-training" if group_id in set(training_ids) else "internal-holdout"
        if role not in ALLOWED_ROLES or role != expected_role:
            raise HandoffRefusal(f"manifest role drift: {case_id}")
        if not isinstance(seed, int) or isinstance(seed, bool) or seed in seeds:
            raise HandoffRefusal(f"manifest seed duplicated or invalid: {case_id}")
        if not isinstance(photon_histories, int) or isinstance(photon_histories, bool) or photon_histories <= 0:
            raise HandoffRefusal(f"manifest photons invalid: {case_id}")
        if float(importance) not in ALLOWED_IMPORTANCE_NM:
            raise HandoffRefusal(f"manifest ALIS wavelength changed: {case_id}")
        seeds.add(seed)
        photons += photon_histories
        case_by_id[case_id] = item
        grouped.setdefault(group_id, []).append(item)
    if photons != PHOTON_COUNT:
        raise HandoffRefusal(f"manifest photon accounting changed: {photons}")
    if any(len(items) != 2 or {item.get("block") for item in items} != {1, 2} for items in grouped.values()):
        raise HandoffRefusal("manifest must contain exactly two immutable blocks per geometry")
    return geometry_by_id, case_by_id, list(training_ids), list(holdout_ids)


def validate_plan(plan: dict[str, Any], manifest_path: Path, case_by_id: dict[str, Any]) -> None:
    exact(
        plan,
        {
            "schemaVersion": 1,
            "stageId": PLAN_STAGE,
            "scientificExecution": True,
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "caseCount": CASE_COUNT,
            "configuredMcPhotonsSum": PHOTON_COUNT,
        },
        "plan",
    )
    if plan.get("manifestRawSha256") != raw_sha256(manifest_path):
        raise HandoffRefusal("plan manifest hash mismatch")
    cases = plan.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise HandoffRefusal("plan cases missing")
    if {item.get("caseId") for item in cases if isinstance(item, dict)} != set(case_by_id):
        raise HandoffRefusal("plan case universe changed")
    for item in cases:
        if not isinstance(item, dict):
            raise HandoffRefusal("plan case invalid")
        source = case_by_id[item["caseId"]]
        for key in (
            "ordinal",
            "groupId",
            "method",
            "block",
            "seed",
            "photonHistories",
            "alisSpectralImportanceSamplingNm",
            "role",
            "executionTierId",
        ):
            if item.get(key) != source.get(key):
                raise HandoffRefusal(f"plan/manifest mismatch: {item['caseId']}.{key}")


def validate_summary(summary: dict[str, Any], manifest_path: Path) -> None:
    schema_version = summary.get("schemaVersion")
    exact(
        summary,
        {
            "schemaVersion": schema_version,
            "stageId": PLAN_STAGE,
            "status": "COMPLETED",
            "classification": "BATCH_NUMERICALLY_COMPLETE",
            "scientificDiagnostic": True,
            "successDoesNotAuthorizeProduction": True,
            "caseCountPlanned": CASE_COUNT,
            "caseCountCompleted": CASE_COUNT,
            "caseCountFailed": 0,
            "syntaxCheckCount": CASE_COUNT,
            "solverExecutionCount": CASE_COUNT,
            "configuredMcPhotonsSum": PHOTON_COUNT,
            "completedConfiguredMcPhotonsSum": PHOTON_COUNT,
        },
        "aggregate",
    )
    if schema_version not in {1, 2}:
        raise HandoffRefusal("aggregate schema unsupported")
    if schema_version == 2:
        exact(
            summary,
            {
                "executionComplete": True,
                "scientificallyEligible": False,
                "scientificEligibilityPendingPrecisionAnalysis": True,
                "zeroHitCaseCount": 0,
                "zeroHitDiagnostics": [],
                "continuationRequiredGeometryIds": [],
            },
            "aggregate v2 eligibility",
        )
    if summary.get("manifestRawSha256") != raw_sha256(manifest_path):
        raise HandoffRefusal("aggregate manifest hash mismatch")
    if summary.get("structuralFailures") != [] or summary.get("failedCases") != []:
        raise HandoffRefusal("aggregate contains failures")
    index = summary.get("caseIndex")
    if not isinstance(index, list) or len(index) != CASE_COUNT:
        raise HandoffRefusal("aggregate case index incomplete")
    ids = [item.get("caseId") for item in index if isinstance(item, dict)]
    if len(ids) != CASE_COUNT or len(set(ids)) != CASE_COUNT:
        raise HandoffRefusal("aggregate case index duplicated")
    for item in index:
        if not isinstance(item, dict):
            raise HandoffRefusal("aggregate case index invalid")
        require_raw_sha(item.get("caseResultSha256"), f"aggregate.{item.get('caseId')}.caseResultSha256")


def validate_audit(audit: dict[str, Any], plan_path: Path, summary_path: Path, case_ids: set[str]) -> None:
    schema_version = audit.get("schemaVersion")
    exact(
        audit,
        {
            "schemaVersion": schema_version,
            "stageId": PLAN_STAGE,
            "status": "PASSED",
            "batchClassification": "BATCH_NUMERICALLY_COMPLETE",
            "successDoesNotAuthorizeProduction": True,
            "caseResultCount": CASE_COUNT,
        },
        "audit",
    )
    if schema_version not in {1, 2}:
        raise HandoffRefusal("audit schema unsupported")
    if schema_version == 2:
        exact(
            audit,
            {
                "executionComplete": True,
                "scientificallyEligible": False,
                "zeroHitDiagnostics": [],
                "incompleteGeometryEnteredTrainingEligibility": False,
            },
            "audit v2 eligibility",
        )
        raw_evidence = audit.get("rawCaseEvidence")
        if not isinstance(raw_evidence, dict) or set(raw_evidence) != case_ids:
            raise HandoffRefusal("audit v2 raw evidence universe mismatch")
    if audit.get("planRawSha256") != raw_sha256(plan_path):
        raise HandoffRefusal("audit plan hash mismatch")
    if audit.get("aggregateRawSha256") != raw_sha256(summary_path):
        raise HandoffRefusal("audit aggregate hash mismatch")
    if audit.get("failures") != []:
        raise HandoffRefusal("audit contains failures")
    hashes = audit.get("caseResultHashes")
    if not isinstance(hashes, dict) or set(hashes) != case_ids:
        raise HandoffRefusal("audit case hash universe mismatch")
    for case_id, value in hashes.items():
        require_raw_sha(value, f"audit.{case_id}")


def validate_analysis_and_v1_dataset(
    analysis: dict[str, Any],
    dataset: dict[str, Any],
    geometry_by_id: dict[str, Any],
    case_by_id: dict[str, Any],
    source_bindings: dict[str, Any] | None = None,
    audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    schema_version = analysis.get("schemaVersion")
    analysis_stage = analysis.get("stageId")
    expected_stage = ANALYSIS_STAGE if schema_version == 1 else ANALYSIS_STAGE_V2
    exact(
        analysis,
        {
            "schemaVersion": schema_version,
            "stageId": expected_stage,
            "status": "TIER_1_ANALYZED",
            "geometryCount": GEOMETRY_COUNT,
            "caseCount": CASE_COUNT,
            "configuredMcPhotonsSum": PHOTON_COUNT,
            "allPointsWithinMaximumRsem": True,
            "surrogateTrainingAutomaticallyAuthorized": False,
            "productionModelReady": False,
            "observationValidationRequired": True,
        },
        "analysis",
    )
    if schema_version not in {1, 2}:
        raise HandoffRefusal("analysis schema unsupported")
    if analysis_stage != expected_stage:
        raise HandoffRefusal("analysis stage/schema mismatch")
    if schema_version == 2:
        exact(
            analysis,
            {
                "executionComplete": True,
                "scientificallyEligible": True,
                "zeroHitGeometryIds": [],
            },
            "analysis v2 eligibility",
        )
        if analysis.get("sourceBindings") != source_bindings:
            raise HandoffRefusal("analysis v2 source bindings changed")
    if analysis.get("adaptiveContinuationRequiredGeometryIds") != []:
        raise HandoffRefusal("analysis still requires adaptive continuation")
    exact(
        dataset,
        {
            "schemaVersion": schema_version,
            "stageId": expected_stage,
            "status": "TIER_1_NUMERICAL_DATASET_COMPLETE",
            "surrogateTrainingAutomaticallyAuthorized": False,
            "observationValidationRequired": True,
        },
        "v1 dataset",
    )
    if schema_version == 2:
        exact(
            dataset,
            {
                "executionComplete": True,
                "scientificallyEligible": True,
                "zeroHitGeometryIds": [],
            },
            "v2 source dataset eligibility",
        )
        if dataset.get("sourceBindings") != source_bindings:
            raise HandoffRefusal("v2 source dataset bindings changed")
    if dataset.get("adaptiveContinuationRequiredGeometryIds") != []:
        raise HandoffRefusal("v1 dataset still requires adaptive continuation")
    points = analysis.get("points")
    records = dataset.get("records")
    if not isinstance(points, list) or len(points) != GEOMETRY_COUNT:
        raise HandoffRefusal("analysis points incomplete")
    if records != points:
        raise HandoffRefusal("v1 dataset records differ from audited analysis points")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_case_ids: set[str] = set()
    target_count = 0
    accepted_count = 0
    training_count = 0
    holdout_count = 0
    for point in points:
        if not isinstance(point, dict):
            raise HandoffRefusal("analysis point invalid")
        geometry_id = point.get("geometryId")
        if geometry_id not in geometry_by_id or geometry_id in seen:
            raise HandoffRefusal(f"analysis geometry duplicated or unknown: {geometry_id}")
        if point.get("geometry") != geometry_by_id[geometry_id]:
            raise HandoffRefusal(f"analysis geometry changed: {geometry_id}")
        classification = point.get("classification")
        if classification not in {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"}:
            raise HandoffRefusal(f"analysis precision incomplete: {geometry_id}")
        if schema_version == 2:
            if point.get("numericalStatus") != "NUMERICALLY_CONVERGED":
                raise HandoffRefusal(f"analysis numerical status incomplete: {geometry_id}")
            if point.get("executionComplete") is not True or point.get("scientificallyEligible") is not True:
                raise HandoffRefusal(f"analysis eligibility incomplete: {geometry_id}")
            if point.get("zeroHitCaseIds") != []:
                raise HandoffRefusal(f"analysis zero hit unresolved: {geometry_id}")
        expected_role = next(item["role"] for item in case_by_id.values() if item["groupId"] == geometry_id)
        if point.get("role") != expected_role:
            raise HandoffRefusal(f"analysis role drift: {geometry_id}")
        expected_fit_eligibility = expected_role == "surrogate-training"
        expected_holdout_eligibility = expected_role == "internal-holdout"
        if (
            point.get("eligibleForProvisionalFit") is not expected_fit_eligibility
            or point.get("eligibleForInternalHoldout") is not expected_holdout_eligibility
        ):
            raise HandoffRefusal(f"analysis role eligibility differs from manifest: {geometry_id}")
        training_count += int(expected_fit_eligibility)
        holdout_count += int(expected_holdout_eligibility)
        case_ids = point.get("caseIds")
        expected_cases = sorted(item["caseId"] for item in case_by_id.values() if item["groupId"] == geometry_id)
        if not isinstance(case_ids, list) or sorted(case_ids) != expected_cases:
            raise HandoffRefusal(f"analysis case IDs changed: {geometry_id}")
        if all_case_ids & set(case_ids):
            raise HandoffRefusal("analysis case IDs duplicated")
        all_case_ids.update(case_ids)
        statistics = point.get("statistics")
        if not isinstance(statistics, dict):
            raise HandoffRefusal(f"analysis statistics missing: {geometry_id}")
        finite(statistics.get("meanCdM2"), f"{geometry_id}.meanCdM2", positive=True)
        finite(statistics.get("sampleStdCdM2"), f"{geometry_id}.sampleStdCdM2", nonnegative=True)
        finite(statistics.get("relativeStandardErrorOfMean"), f"{geometry_id}.rsem", nonnegative=True)
        nodes = statistics.get("nodeMeanRadiance")
        if not isinstance(nodes, list) or len(nodes) != 15:
            raise HandoffRefusal(f"analysis spectral nodes missing: {geometry_id}")
        for index, node in enumerate(nodes):
            finite(node, f"{geometry_id}.node[{index}]", positive=True)
        if schema_version == 2:
            if not isinstance(audit, dict):
                raise HandoffRefusal("audit v2 required for numerical recomputation")
            expected_statistics = v2_statistics_from_audit(sorted(case_ids), audit)
            if not numerically_equal(statistics, expected_statistics):
                raise HandoffRefusal(f"analysis values differ from raw audit evidence: {geometry_id}")
            recomputed_rsem = expected_statistics["relativeStandardErrorOfMean"]
            recomputed_classification = (
                "PRECISION_TARGET_MET"
                if recomputed_rsem <= TARGET_RSEM
                else "PRECISION_ACCEPTED"
                if recomputed_rsem <= ACCEPTED_MAX_RSEM
                else "ADAPTIVE_CONTINUATION_REQUIRED"
            )
            if classification != recomputed_classification:
                raise HandoffRefusal(
                    f"analysis precision classification differs from raw audit evidence: {geometry_id}"
                )
        if classification == "PRECISION_TARGET_MET":
            target_count += 1
        if classification in {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"}:
            accepted_count += 1
        seen.add(geometry_id)
        result.append(dict(point))
    if seen != set(geometry_by_id) or all_case_ids != set(case_by_id):
        raise HandoffRefusal("analysis universe incomplete")
    if schema_version == 2:
        exact(
            analysis,
            {
                "precisionTargetGeometryCount": target_count,
                "precisionAcceptedGeometryCount": accepted_count,
            },
            "analysis v2 precision counts",
        )
        exact(
            dataset,
            {
                "trainingRecordCount": training_count,
                "internalHoldoutRecordCount": holdout_count,
            },
            "dataset v2 role counts",
        )
    return result


def validate_reference(reference: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    exact(
        reference,
        {
            "schemaVersion": 1,
            "stageId": REFERENCE_STAGE,
            "status": "REFERENCE_ANCHORS_VALIDATED",
            "anchorCount": 6,
            "trainingAutomaticallyAuthorized": False,
        },
        "reference anchors",
    )
    hard_ids = reference.get("hardValidationAnchorIds")
    soft_ids = reference.get("softDiagnosticAnchorIds")
    anchors = reference.get("anchors")
    if not isinstance(hard_ids, list) or len(hard_ids) != 5 or len(set(hard_ids)) != 5:
        raise HandoffRefusal("hard anchor partition changed")
    if not isinstance(soft_ids, list) or len(soft_ids) != 1 or len(set(soft_ids)) != 1:
        raise HandoffRefusal("soft diagnostic partition changed")
    if set(hard_ids) & set(soft_ids):
        raise HandoffRefusal("reference anchor partitions overlap")
    if not isinstance(anchors, list) or len(anchors) != 6:
        raise HandoffRefusal("reference anchors incomplete")
    by_id: dict[str, Any] = {}
    external: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise HandoffRefusal("reference anchor invalid")
        anchor_id = anchor.get("groupId")
        if not isinstance(anchor_id, str) or anchor_id in by_id:
            raise HandoffRefusal("reference anchor ID duplicated or missing")
        geometry = validate_geometry(anchor.get("geometry"), anchor_id)
        methods = anchor.get("methods")
        alis = methods.get("alis") if isinstance(methods, dict) else None
        if not isinstance(alis, dict):
            raise HandoffRefusal(f"ALIS anchor statistics missing: {anchor_id}")
        mean = finite(alis.get("meanCdM2"), f"{anchor_id}.alis.meanCdM2", positive=True)
        nodes = alis.get("nodeMeanRadiance")
        if not isinstance(nodes, list) or len(nodes) != 15:
            raise HandoffRefusal(f"ALIS anchor nodes missing: {anchor_id}")
        for index, node in enumerate(nodes):
            finite(node, f"{anchor_id}.alis.node[{index}]", nonnegative=True)
        strength = anchor.get("anchorStrength")
        if anchor_id in set(hard_ids) and strength != "hard":
            raise HandoffRefusal(f"hard anchor strength changed: {anchor_id}")
        if anchor_id in set(soft_ids) and strength != "soft-diagnostic":
            raise HandoffRefusal(f"soft anchor strength changed: {anchor_id}")
        if anchor.get("eligibleForTraining") is not False:
            raise HandoffRefusal(f"anchor became training eligible: {anchor_id}")
        external.append(
            {
                "geometryId": anchor_id,
                "geometry": geometry,
                "meanCdM2": mean,
                "nodeMeanRadiance": [float(item) for item in nodes],
                "sourceMethod": "alis",
                "anchorStrength": strength,
                "eligibleForTraining": False,
                "eligibleForHyperparameterSelection": False,
                "reportOnly": anchor_id in set(soft_ids),
            }
        )
        by_id[anchor_id] = anchor
    if set(by_id) != set(hard_ids) | set(soft_ids):
        raise HandoffRefusal("reference anchor universe mismatch")
    return sorted(hard_ids), sorted(soft_ids), sorted(external, key=lambda item: item["geometryId"])


def validate_source_run_and_artifacts(source_run: dict[str, Any], artifacts: dict[str, Any]) -> None:
    exact(source_run, {"status": "completed", "conclusion": "success", "run_attempt": 1}, "source run")
    if not isinstance(source_run.get("id"), int) or source_run["id"] < 1:
        raise HandoffRefusal("source run ID invalid")
    require_git_sha(source_run.get("head_sha"), "source run head SHA")
    values = artifacts.get("artifacts")
    if not isinstance(values, list) or not values:
        raise HandoffRefusal("source artifact list missing")
    ids: set[int] = set()
    names: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise HandoffRefusal("source artifact invalid")
        artifact_id = item.get("id")
        name = item.get("name")
        digest = item.get("digest")
        if not isinstance(artifact_id, int) or artifact_id < 1 or artifact_id in ids:
            raise HandoffRefusal("source artifact ID duplicated or invalid")
        if not isinstance(name, str) or not name or name in names:
            raise HandoffRefusal("source artifact name duplicated or invalid")
        if item.get("expired") is not False or not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
            raise HandoffRefusal(f"source artifact digest invalid: {name}")
        ids.add(artifact_id)
        names.add(name)


def validate_source_guard(
    guard: dict[str, Any], plan: dict[str, Any], plan_path: Path, manifest_path: Path,
    artifact_list_path: Path, source_run: dict[str, Any]
) -> None:
    exact(
        guard,
        {
            "schemaVersion": 2,
            "stageId": "surrogate-training-v2-real-tier1-handoff-guard-v2",
            "status": "REAL_TIER1_HANDOFF_SOURCE_ACCEPTED",
            "sourceRunId": source_run.get("id"),
            "sourceRunHeadSha": source_run.get("head_sha"),
            "sourceExecutionKey": plan.get("executionKey"),
            "sourceAuthorizationOrdinal": plan.get("authorizationOrdinal"),
            "sourceAuthorizationRef": plan.get("authorizationRef"),
            "sourcePlanRawSha256": raw_sha256(plan_path),
            "sourceManifestRawSha256": raw_sha256(manifest_path),
            "sourceArtifactListRawSha256": raw_sha256(artifact_list_path),
            "sourceRunAttempt": 1,
            "sourceArtifactCount": 100,
            "caseArtifactCount": 96,
            "surrogateTrainingAuthorized": False,
            "internalHoldoutOpeningAuthorized": False,
            "tier2Authorized": False,
            "productionPromotionAuthorized": False,
        },
        "accepted real-source guard",
    )
    require_raw_sha(guard.get("sourceDescriptorRawSha256"), "source descriptor hash")


def build(
    manifest_path: Path,
    plan_path: Path,
    summary_path: Path,
    audit_path: Path,
    analysis_path: Path,
    v1_dataset_path: Path,
    reference_path: Path,
    source_run_path: Path,
    artifact_list_path: Path,
    output_dir: Path,
    *,
    exact_main_sha: str,
    synthetic_only: bool = False,
    source_guard_path: Path | None = None,
) -> dict[str, Path]:
    require_git_sha(exact_main_sha, "exact main SHA")
    manifest = load(manifest_path)
    plan = load(plan_path)
    summary = load(summary_path)
    audit = load(audit_path)
    analysis = load(analysis_path)
    v1_dataset = load(v1_dataset_path)
    reference = load(reference_path)
    source_run = load(source_run_path)
    artifacts = load(artifact_list_path)
    source_guard = load(source_guard_path) if source_guard_path is not None else None

    geometry_by_id, case_by_id, training_ids, holdout_ids = validate_manifest(manifest)
    validate_plan(plan, manifest_path, case_by_id)
    validate_summary(summary, manifest_path)
    if {item.get("caseId") for item in summary["caseIndex"]} != set(case_by_id):
        raise HandoffRefusal("aggregate case universe differs from manifest")
    validate_audit(audit, plan_path, summary_path, set(case_by_id))
    source_bindings = {
        "manifestRawSha256": raw_sha256(manifest_path),
        "aggregateRawSha256": raw_sha256(summary_path),
        "auditRawSha256": raw_sha256(audit_path),
        "caseResultRawSha256ByCaseId": audit.get("caseResultHashes"),
    }
    points = validate_analysis_and_v1_dataset(
        analysis, v1_dataset, geometry_by_id, case_by_id, source_bindings, audit
    )
    hard_ids, soft_ids, external = validate_reference(reference)
    validate_source_run_and_artifacts(source_run, artifacts)
    if not synthetic_only:
        if source_guard is None or source_guard_path is None:
            raise HandoffRefusal("accepted real-source guard is required")
        if source_run.get("head_sha") != exact_main_sha:
            raise HandoffRefusal("real source run head differs from exact main SHA")
        validate_source_guard(source_guard, plan, plan_path, manifest_path, artifact_list_path, source_run)

    hashes = {
        "manifestRawSha256": raw_sha256(manifest_path),
        "planRawSha256": raw_sha256(plan_path),
        "aggregateRawSha256": raw_sha256(summary_path),
        "independentAuditRawSha256": raw_sha256(audit_path),
        "analysisRawSha256": raw_sha256(analysis_path),
        "v1DatasetRawSha256": raw_sha256(v1_dataset_path),
        "referenceAnchorsRawSha256": raw_sha256(reference_path),
        "sourceRunRawSha256": raw_sha256(source_run_path),
        "artifactListRawSha256": raw_sha256(artifact_list_path),
    }
    if source_guard is not None and source_guard_path is not None:
        hashes.update(
            {
                "sourceGuardRawSha256": raw_sha256(source_guard_path),
                "sourceDescriptorRawSha256": source_guard["sourceDescriptorRawSha256"],
                "sourcePlanRawSha256": source_guard["sourcePlanRawSha256"],
                "sourceArtifactListGuardRawSha256": source_guard["sourceArtifactListRawSha256"],
            }
        )
    audit_hashes = audit["caseResultHashes"]
    records: list[dict[str, Any]] = []
    for point in sorted(points, key=lambda item: item["geometryId"]):
        case_ids = sorted(point["caseIds"])
        record = dict(point)
        record["caseIds"] = case_ids
        record["sourceBindings"] = {
            "manifestRawSha256": hashes["manifestRawSha256"],
            "aggregateRawSha256": hashes["aggregateRawSha256"],
            "auditRawSha256": hashes["independentAuditRawSha256"],
            "caseResultRawSha256ByCaseId": {case_id: audit_hashes[case_id] for case_id in case_ids},
        }
        records.append(record)

    boundary = {
        "syntheticOnly": bool(synthetic_only),
        "scientificExecution": not synthetic_only,
        "observationallyValidated": False,
        "productionModelReady": False,
        "successDoesNotAuthorizeProduction": True,
    }
    design = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-frozen-role-map-v1",
        **boundary,
        "rolesByGeometryId": {
            geometry_id: "surrogate-training" if geometry_id in set(training_ids) else "internal-holdout"
            for geometry_id in sorted(geometry_by_id)
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    design_path = output_dir / "frozen-design.json"
    design_path.write_text(dump(design))

    dataset = {
        "schemaVersion": 2,
        "stageId": ANALYSIS_STAGE,
        "status": "TIER_1_NUMERICAL_DATASET_COMPLETE",
        **boundary,
        "records": records,
        "trainingGeometryIds": list(training_ids),
        "internalHoldoutGeometryIds": list(holdout_ids),
        "hardExternalAnchorIds": hard_ids,
        "softDiagnosticIds": soft_ids,
    }
    dataset_path = output_dir / "tier1-numerical-dataset.json"
    dataset_path.write_text(dump(dataset))

    envelope = {
        "schemaVersion": 1,
        "stageId": ENVELOPE_STAGE,
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "precisionClassificationComplete": True,
        "provenanceValidated": True,
        **boundary,
        "exactMainSha": exact_main_sha,
        "sourceRunId": source_run["id"],
        "sourceRunHeadSha": source_run["head_sha"],
        "datasetRawSha256": raw_sha256(dataset_path),
        "bindings": {**hashes, "designRawSha256": raw_sha256(design_path)},
        "externalRecords": external,
        "authorizationPermitted": False,
        "tier2AutomaticallyPermitted": False,
        "productionPromotionAuthorized": False,
        "boundary": "deterministic Tier-1 v1-to-v2 handoff only; no radiance reinterpretation, model fitting, holdout opening, Tier-2 activation, or production promotion",
    }
    envelope_path = output_dir / "dataset-envelope.json"
    envelope_path.write_text(dump(envelope))
    return {"dataset": dataset_path, "design": design_path, "envelope": envelope_path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--v1-dataset", type=Path, required=True)
    parser.add_argument("--reference-anchors", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--artifact-list", type=Path, required=True)
    parser.add_argument("--source-guard", type=Path)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()
    try:
        paths = build(
            args.manifest,
            args.plan,
            args.summary,
            args.audit,
            args.analysis,
            args.v1_dataset,
            args.reference_anchors,
            args.source_run,
            args.artifact_list,
            args.output_dir,
            exact_main_sha=args.main_sha,
            synthetic_only=args.synthetic_only,
            source_guard_path=args.source_guard,
        )
        print(dump({"status": "TIER_1_V2_HANDOFF_COMPLETE", "outputs": {key: str(value) for key, value in paths.items()}}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": ENVELOPE_STAGE, "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
