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

DATASET_STAGE = "twilight-surrogate-tier-1-analysis-v1"
DATASET_STATUS = "TIER_1_NUMERICAL_DATASET_COMPLETE"
ENVELOPE_STAGE = "twilight-surrogate-tier-1-dataset-envelope-v1"
REFERENCE_STAGE = "twilight-model-readiness-v1"
SOURCE_GEOMETRY_COUNT = 48
CONTINUATION_GEOMETRY_COUNT = 20
WAVE1_CASE_COUNT = 40
WAVE2_CASE_COUNT = 32
TARGET_RSEM = 0.05
ACCEPTED_MAX_RSEM = 0.08
CIE = [0.09098,0.13902,0.20802,0.323,0.503,0.71,0.862,0.954,0.995,0.87,0.757,0.631,0.503,0.175,0.061]


class HandoffRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise HandoffRefusal(f"expected object: {path}")
    return value


def finite(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise HandoffRefusal(f"{label} must be finite")
    number = float(value)
    if positive and number <= 0:
        raise HandoffRefusal(f"{label} must be positive")
    if nonnegative and number < 0:
        raise HandoffRefusal(f"{label} must be non-negative")
    return number


def require_sha(value: Any, label: str, length: int = 64) -> str:
    if not isinstance(value, str) or len(value) != length or any(ch not in "0123456789abcdef" for ch in value):
        raise HandoffRefusal(f"{label} must be lowercase hex length {length}")
    return value


def photopic(nodes: list[float]) -> float:
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(nodes, CIE, strict=True))


def stats(values: list[float], node_rows: list[list[float]]) -> dict[str, Any]:
    if len(values) != len(node_rows) or len(values) < 2:
        raise HandoffRefusal("statistics evidence cardinality invalid")
    parsed_values = [finite(value, "block value", nonnegative=True) for value in values]
    parsed_nodes: list[list[float]] = []
    for row in node_rows:
        if not isinstance(row, list) or len(row) != 15:
            raise HandoffRefusal("selected-node row invalid")
        parsed_nodes.append([finite(value, "selected node", nonnegative=True) for value in row])
    zero_count = sum(value == 0.0 for value in parsed_values)
    mean = statistics.fmean(parsed_values)
    if zero_count or mean <= 0:
        raise HandoffRefusal("final eligible point contains zero-hit evidence")
    sample_std = statistics.stdev(parsed_values)
    rsem = sample_std / math.sqrt(len(parsed_values)) / mean
    nodes = [statistics.fmean(row[index] for row in parsed_nodes) for index in range(15)]
    if any(value <= 0 for value in nodes):
        raise HandoffRefusal("final eligible point has non-positive node mean")
    return {
        "blockCount": len(parsed_values),
        "valuesCdM2": parsed_values,
        "nonzeroBlockValuesCdM2": parsed_values,
        "meanCdM2": mean,
        "sampleStdCdM2": sample_std,
        "relativeStandardErrorOfMean": rsem,
        "relativeStandardErrorStatus": "COMPUTED",
        "zeroHitBlockCount": 0,
        "zeroHitBlockFraction": 0.0,
        "nodeMeanRadiance": nodes,
    }


def classification(rsem: float) -> str:
    return "PRECISION_TARGET_MET" if rsem <= TARGET_RSEM else "PRECISION_ACCEPTED" if rsem <= ACCEPTED_MAX_RSEM else "ADAPTIVE_CONTINUATION_REQUIRED"


def validate_result(row: dict[str, Any], case: dict[str, Any], expected_stage: str) -> None:
    expected = {
        "stageId": expected_stage,
        "status": "COMPLETED",
        "caseId": case["caseId"],
        "groupId": case["groupId"],
        "block": case["block"],
        "role": case["role"],
        "seed": case["seed"],
        "photonHistories": case["photonHistories"],
        "syntaxCheckCount": 1,
        "solverExecutionCount": 1,
        "fittingSurfaceExposed": False,
        "retryAllowed": False,
        "resumeAllowed": False,
    }
    stale = {key: (row.get(key), value) for key, value in expected.items() if row.get(key) != value}
    if stale:
        raise HandoffRefusal(f"case result provenance changed: {stale}")
    supplied = row.get("contentSha256")
    require_sha(supplied, f"{case['caseId']}.contentSha256")
    payload = {key: value for key, value in row.items() if key != "contentSha256"}
    if supplied != canonical_sha256(payload):
        raise HandoffRefusal(f"case result content hash changed: {case['caseId']}")
    for key in ("inputSha256", "radianceOutputSha256", "stdOutputSha256", "runtimeReportSha256"):
        require_sha(row.get(key), f"{case['caseId']}.{key}")
    nodes = row.get("selectedNodeRadiance")
    if not isinstance(nodes, list) or len(nodes) != 15:
        raise HandoffRefusal(f"case selected nodes invalid: {case['caseId']}")
    parsed = [finite(value, f"{case['caseId']}.node", nonnegative=True) for value in nodes]
    value = finite(row.get("selectedPhotopicContributionCdM2"), f"{case['caseId']}.value", nonnegative=True)
    if not math.isclose(photopic(parsed), value, rel_tol=1e-12, abs_tol=1e-18):
        raise HandoffRefusal(f"case photopic value differs from selected nodes: {case['caseId']}")
    zero = value == 0.0 and all(item == 0.0 for item in parsed)
    if row.get("zeroHit") is not zero:
        raise HandoffRefusal(f"case zero-hit semantics changed: {case['caseId']}")


def load_results(root: Path, manifest: dict[str, Any], expected_stage: str, count: int) -> dict[str, dict[str, Any]]:
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != count:
        raise HandoffRefusal(f"manifest must contain exactly {count} cases")
    expected = {case.get("caseId"): case for case in cases if isinstance(case, dict)}
    if len(expected) != count or None in expected:
        raise HandoffRefusal("manifest case IDs duplicated or missing")
    paths = sorted(root.rglob("case-result.json"))
    if len(paths) != count:
        raise HandoffRefusal(f"expected {count} case-result files, found {len(paths)}")
    results: dict[str, dict[str, Any]] = {}
    for path in paths:
        row = load(path)
        case_id = row.get("caseId")
        if case_id not in expected or case_id in results:
            raise HandoffRefusal(f"unplanned or duplicate result: {case_id}")
        validate_result(row, expected[case_id], expected_stage)
        results[case_id] = row
    return results


def validate_reference(reference: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    expected = {
        "schemaVersion": 1,
        "stageId": REFERENCE_STAGE,
        "status": "REFERENCE_ANCHORS_VALIDATED",
        "anchorCount": 6,
        "trainingAutomaticallyAuthorized": False,
    }
    stale = {key: (reference.get(key), value) for key, value in expected.items() if reference.get(key) != value}
    if stale:
        raise HandoffRefusal(f"reference anchors changed: {stale}")
    hard = reference.get("hardValidationAnchorIds")
    soft = reference.get("softDiagnosticAnchorIds")
    anchors = reference.get("anchors")
    if not isinstance(hard, list) or len(hard) != 5 or len(set(hard)) != 5:
        raise HandoffRefusal("hard anchor partition changed")
    if not isinstance(soft, list) or len(soft) != 1 or len(set(soft)) != 1 or set(hard) & set(soft):
        raise HandoffRefusal("soft anchor partition changed")
    if not isinstance(anchors, list) or len(anchors) != 6:
        raise HandoffRefusal("reference anchors incomplete")
    external = []
    seen = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise HandoffRefusal("reference anchor malformed")
        gid = anchor.get("groupId")
        if not isinstance(gid, str) or gid in seen:
            raise HandoffRefusal("reference anchor ID invalid")
        seen.add(gid)
        geometry = anchor.get("geometry")
        if not isinstance(geometry, dict):
            raise HandoffRefusal("reference geometry missing")
        for key in ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550"):
            finite(geometry.get(key), f"{gid}.{key}", nonnegative=True)
        methods = anchor.get("methods")
        alis = methods.get("alis") if isinstance(methods, dict) else None
        if not isinstance(alis, dict):
            raise HandoffRefusal("reference ALIS statistics missing")
        mean = finite(alis.get("meanCdM2"), f"{gid}.mean", positive=True)
        nodes = alis.get("nodeMeanRadiance")
        if not isinstance(nodes, list) or len(nodes) != 15:
            raise HandoffRefusal("reference nodes missing")
        parsed_nodes = [finite(value, f"{gid}.node", nonnegative=True) for value in nodes]
        strength = anchor.get("anchorStrength")
        if gid in hard and strength != "hard":
            raise HandoffRefusal("hard anchor strength changed")
        if gid in soft and strength != "soft-diagnostic":
            raise HandoffRefusal("soft anchor strength changed")
        if anchor.get("eligibleForTraining") is not False:
            raise HandoffRefusal("reference anchor became training eligible")
        external.append({
            "geometryId": gid,
            "geometry": geometry,
            "meanCdM2": mean,
            "nodeMeanRadiance": parsed_nodes,
            "sourceMethod": "alis",
            "anchorStrength": strength,
            "eligibleForTraining": False,
            "eligibleForHyperparameterSelection": False,
            "reportOnly": gid in soft,
        })
    if seen != set(hard) | set(soft):
        raise HandoffRefusal("reference anchor universe changed")
    return sorted(hard), sorted(soft), sorted(external, key=lambda item: item["geometryId"])


def build(
    source_dataset_path: Path,
    wave1_manifest_path: Path,
    wave1_results_root: Path,
    wave2_manifest_path: Path,
    wave2_results_root: Path,
    wave1_aggregate_path: Path,
    wave1_audit_path: Path,
    wave2_aggregate_path: Path,
    wave2_audit_path: Path,
    final_analysis_path: Path,
    terminal_report_path: Path,
    reference_path: Path,
    source_run_path: Path,
    source_artifacts_path: Path,
    output_dir: Path,
    *,
    exact_main_sha: str,
) -> dict[str, Path]:
    require_sha(exact_main_sha, "exact main SHA", 40)
    source = load(source_dataset_path)
    records = source.get("records")
    adaptive = source.get("adaptiveContinuationRequiredGeometryIds")
    if not isinstance(records, list) or len(records) != SOURCE_GEOMETRY_COUNT:
        raise HandoffRefusal("source dataset must contain 48 records")
    if not isinstance(adaptive, list) or len(adaptive) != CONTINUATION_GEOMETRY_COUNT or len(set(adaptive)) != CONTINUATION_GEOMETRY_COUNT:
        raise HandoffRefusal("source continuation universe changed")
    source_by_id = {record.get("geometryId"): record for record in records if isinstance(record, dict)}
    if len(source_by_id) != SOURCE_GEOMETRY_COUNT or None in source_by_id:
        raise HandoffRefusal("source geometry IDs duplicated or missing")
    if set(adaptive) != {gid for gid, record in source_by_id.items() if record.get("classification") == "ADAPTIVE_CONTINUATION_REQUIRED"}:
        raise HandoffRefusal("source adaptive list differs from record classifications")

    wave1_manifest = load(wave1_manifest_path)
    wave2_manifest = load(wave2_manifest_path)
    wave1_results = load_results(wave1_results_root, wave1_manifest, "tier1-precision-continuation-wave1-ordinal11-execution-v5", WAVE1_CASE_COUNT)
    wave2_results = load_results(wave2_results_root, wave2_manifest, "tier1-precision-continuation-wave2-ordinal12-execution-v1", WAVE2_CASE_COUNT)
    if {case["groupId"] for case in wave1_manifest["cases"]} != set(adaptive):
        raise HandoffRefusal("wave-one geometry universe differs from source adaptive set")
    wave2_ids = {case["groupId"] for case in wave2_manifest["cases"]}
    if len(wave2_ids) != 16 or not wave2_ids < set(adaptive):
        raise HandoffRefusal("wave-two geometry universe invalid")

    final_wrapper = load(final_analysis_path)
    analysis = final_wrapper.get("analysis")
    if not isinstance(analysis, dict) or analysis.get("status") != "CONTINUATION_ANALYZED":
        raise HandoffRefusal("terminal two-wave analysis missing")
    if analysis.get("nextWaveGeometryIds") != [] or analysis.get("exhaustedGeometryIds") != [] or analysis.get("scientificallyEligible") is not True:
        raise HandoffRefusal("terminal two-wave analysis is not fully eligible")
    points = analysis.get("points")
    point_by_id = {point.get("geometryId"): point for point in points if isinstance(point, dict)} if isinstance(points, list) else {}
    if len(point_by_id) != CONTINUATION_GEOMETRY_COUNT or set(point_by_id) != set(adaptive):
        raise HandoffRefusal("terminal analysis point universe changed")
    terminal = load(terminal_report_path)
    if terminal.get("status") != "AUDITED_TWO_WAVE_ANALYSIS_COMPLETE" or terminal.get("scientificallyEligible") is not True or terminal.get("nextWaveGeometryIds") != [] or terminal.get("exhaustedGeometryIds") != []:
        raise HandoffRefusal("terminal report is not fully eligible")
    if terminal.get("runAttempt") != 1 or terminal.get("caseCount") != WAVE2_CASE_COUNT:
        raise HandoffRefusal("terminal report identity changed")

    wave1_cases_by_gid: dict[str, list[dict[str, Any]]] = {gid: [] for gid in adaptive}
    for case in wave1_manifest["cases"]:
        wave1_cases_by_gid[case["groupId"]].append(case)
    wave2_cases_by_gid: dict[str, list[dict[str, Any]]] = {gid: [] for gid in wave2_ids}
    for case in wave2_manifest["cases"]:
        wave2_cases_by_gid[case["groupId"]].append(case)

    final_records = []
    aggregate_rows = []
    audit_hashes: dict[str, str] = {}
    for gid in sorted(source_by_id):
        original = source_by_id[gid]
        record = dict(original)
        role = record.get("role")
        if role not in {"surrogate-training", "internal-holdout"}:
            raise HandoffRefusal(f"source role invalid: {gid}")
        original_stats = record.get("statistics")
        if not isinstance(original_stats, dict):
            raise HandoffRefusal(f"source statistics missing: {gid}")
        original_values = original_stats.get("valuesCdM2")
        original_nodes = original_stats.get("nodeMeanRadiance")
        if not isinstance(original_values, list) or len(original_values) != 2 or not isinstance(original_nodes, list) or len(original_nodes) != 15:
            raise HandoffRefusal(f"source b1-b2 evidence invalid: {gid}")
        values = [finite(value, f"{gid}.source-value", nonnegative=True) for value in original_values]
        source_node = [finite(value, f"{gid}.source-node", nonnegative=True) for value in original_nodes]
        node_rows = [source_node[:], source_node[:]]
        continuation_ids: list[str] = []
        if gid in set(adaptive):
            for case in sorted(wave1_cases_by_gid[gid], key=lambda item: item["block"]):
                result = wave1_results[case["caseId"]]
                values.append(float(result["selectedPhotopicContributionCdM2"]))
                node_rows.append([float(value) for value in result["selectedNodeRadiance"]])
                continuation_ids.append(case["caseId"])
                audit_hashes[case["caseId"]] = result["contentSha256"]
            for case in sorted(wave2_cases_by_gid.get(gid, []), key=lambda item: item["block"]):
                result = wave2_results[case["caseId"]]
                values.append(float(result["selectedPhotopicContributionCdM2"]))
                node_rows.append([float(value) for value in result["selectedNodeRadiance"]])
                continuation_ids.append(case["caseId"])
                audit_hashes[case["caseId"]] = result["contentSha256"]
            computed = stats(values, node_rows)
            point = point_by_id[gid]
            if point.get("classification") not in {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"} or point.get("scientificallyEligible") is not True:
                raise HandoffRefusal(f"terminal point is not eligible: {gid}")
            if classification(computed["relativeStandardErrorOfMean"]) != point["classification"]:
                raise HandoffRefusal(f"terminal classification differs from raw results: {gid}")
            point_values = point.get("valuesCdM2")
            if not isinstance(point_values, list) or len(point_values) != len(values) or any(not math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-18) for a, b in zip(point_values, values, strict=True)):
                raise HandoffRefusal(f"terminal values differ from raw results: {gid}")
            record["statistics"] = computed
            record["classification"] = point["classification"]
            record["numericalStatus"] = "NUMERICALLY_CONVERGED"
            record["scientificallyEligible"] = True
            record["eligibleForProvisionalFit"] = role == "surrogate-training"
            record["eligibleForInternalHoldout"] = role == "internal-holdout"
            record["zeroHitCaseIds"] = []
            record["continuationCaseIds"] = continuation_ids
            record["allEvidenceCaseIds"] = list(record["caseIds"]) + continuation_ids
        else:
            computed = stats(values, node_rows)
            source_classification = record.get("classification")
            if source_classification not in {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"} or record.get("scientificallyEligible") is not True:
                raise HandoffRefusal(f"non-continuation source record is not eligible: {gid}")
            if classification(computed["relativeStandardErrorOfMean"]) != source_classification:
                raise HandoffRefusal(f"non-continuation classification differs from source values: {gid}")
            record["statistics"] = computed
            record["continuationCaseIds"] = []
            record["allEvidenceCaseIds"] = list(record["caseIds"])
        aggregate_rows.append({
            "geometryId": gid,
            "role": role,
            "classification": record["classification"],
            "statistics": record["statistics"],
            "sourceCaseIds": list(record["caseIds"]),
            "continuationCaseIds": list(record["continuationCaseIds"]),
        })
        final_records.append(record)

    if len(final_records) != SOURCE_GEOMETRY_COUNT or any(record["classification"] not in {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"} for record in final_records):
        raise HandoffRefusal("final 48-geometry dataset is not fully precise")
    training_ids = sorted(record["geometryId"] for record in final_records if record["role"] == "surrogate-training")
    holdout_ids = sorted(record["geometryId"] for record in final_records if record["role"] == "internal-holdout")
    if set(training_ids) & set(holdout_ids) or set(training_ids) | set(holdout_ids) != set(source_by_id):
        raise HandoffRefusal("final role partition invalid")
    hard_ids, soft_ids, external = validate_reference(load(reference_path))

    input_paths = {
        "sourceDataset": source_dataset_path,
        "wave1Manifest": wave1_manifest_path,
        "wave2Manifest": wave2_manifest_path,
        "wave1Aggregate": wave1_aggregate_path,
        "wave1Audit": wave1_audit_path,
        "wave2Aggregate": wave2_aggregate_path,
        "wave2Audit": wave2_audit_path,
        "finalAnalysis": final_analysis_path,
        "terminalReport": terminal_report_path,
        "referenceAnchors": reference_path,
        "sourceRun": source_run_path,
        "sourceArtifacts": source_artifacts_path,
    }
    evidence = {
        "schemaVersion": 1,
        "stageId": "tier1-continuation-final-dataset-evidence-v1",
        "status": "SOURCE_EVIDENCE_BOUND",
        "exactMainSha": exact_main_sha,
        "inputRawSha256": {name: raw_sha256(path) for name, path in input_paths.items()},
        "wave1CaseResultSha256ByCaseId": {case_id: row["contentSha256"] for case_id, row in sorted(wave1_results.items())},
        "wave2CaseResultSha256ByCaseId": {case_id: row["contentSha256"] for case_id, row in sorted(wave2_results.items())},
        "sourceGeometryCount": SOURCE_GEOMETRY_COUNT,
        "continuationGeometryCount": CONTINUATION_GEOMETRY_COUNT,
        "wave1CaseCount": WAVE1_CASE_COUNT,
        "wave2CaseCount": WAVE2_CASE_COUNT,
        "scientificExecution": True,
        "surrogateTrainingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    evidence["evidenceSha256"] = canonical_sha256(evidence)
    aggregate = {
        "schemaVersion": 1,
        "stageId": "tier1-continuation-final-dataset-aggregate-v1",
        "status": "FINAL_48_GEOMETRY_AGGREGATE_COMPLETE",
        "geometryCount": SOURCE_GEOMETRY_COUNT,
        "trainingGeometryCount": len(training_ids),
        "internalHoldoutGeometryCount": len(holdout_ids),
        "precisionTargetGeometryCount": sum(row["classification"] == "PRECISION_TARGET_MET" for row in aggregate_rows),
        "precisionAcceptedGeometryCount": len(aggregate_rows),
        "records": aggregate_rows,
        "scientificallyEligible": True,
    }
    aggregate["aggregateSha256"] = canonical_sha256(aggregate)
    audit = {
        "schemaVersion": 1,
        "stageId": "tier1-continuation-final-dataset-independent-audit-v1",
        "status": "PASSED",
        "failures": [],
        "geometryCount": SOURCE_GEOMETRY_COUNT,
        "continuationCaseResultCount": WAVE1_CASE_COUNT + WAVE2_CASE_COUNT,
        "caseResultHashes": audit_hashes,
        "aggregateSha256": aggregate["aggregateSha256"],
        "independentlyRecomputedFromRawSelectedNodeRadiance": True,
        "scientificallyEligible": True,
    }
    audit["auditSha256"] = canonical_sha256(audit)

    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "final-evidence-manifest.json"
    aggregate_path = output_dir / "final-aggregate.json"
    audit_path = output_dir / "final-independent-audit.json"
    evidence_path.write_text(dump(evidence), encoding="utf-8", newline="\n")
    aggregate_path.write_text(dump(aggregate), encoding="utf-8", newline="\n")
    audit_path.write_text(dump(audit), encoding="utf-8", newline="\n")
    bindings = {
        "manifestRawSha256": raw_sha256(evidence_path),
        "aggregateRawSha256": raw_sha256(aggregate_path),
        "auditRawSha256": raw_sha256(audit_path),
    }
    for record in final_records:
        record["sourceBindings"] = {
            **bindings,
            "sourceDatasetRawSha256": raw_sha256(source_dataset_path),
            "continuationCaseResultRawSha256ByCaseId": {case_id: audit_hashes[case_id] for case_id in record["continuationCaseIds"]},
        }

    boundary = {
        "syntheticOnly": False,
        "scientificExecution": True,
        "observationallyValidated": False,
        "productionModelReady": False,
        "successDoesNotAuthorizeProduction": True,
    }
    design = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-frozen-role-map-v1",
        **boundary,
        "rolesByGeometryId": {record["geometryId"]: record["role"] for record in final_records},
    }
    design_path = output_dir / "frozen-design.json"
    design_path.write_text(dump(design), encoding="utf-8", newline="\n")
    dataset = {
        "schemaVersion": 2,
        "stageId": DATASET_STAGE,
        "status": DATASET_STATUS,
        **boundary,
        "records": sorted(final_records, key=lambda item: item["geometryId"]),
        "trainingGeometryIds": training_ids,
        "internalHoldoutGeometryIds": holdout_ids,
        "hardExternalAnchorIds": hard_ids,
        "softDiagnosticIds": soft_ids,
    }
    dataset_path = output_dir / "tier1-numerical-dataset.json"
    dataset_path.write_text(dump(dataset), encoding="utf-8", newline="\n")
    source_run = load(source_run_path)
    source_artifacts = load(source_artifacts_path)
    envelope = {
        "schemaVersion": 1,
        "stageId": ENVELOPE_STAGE,
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "precisionClassificationComplete": True,
        "provenanceValidated": True,
        **boundary,
        "exactMainSha": exact_main_sha,
        "sourceRunId": source_run.get("id"),
        "sourceRunHeadSha": source_run.get("head_sha"),
        "sourceArtifactCount": len(source_artifacts.get("artifacts", [])),
        "datasetRawSha256": raw_sha256(dataset_path),
        "bindings": {
            **bindings,
            "analysisRawSha256": raw_sha256(final_analysis_path),
            "terminalReportRawSha256": raw_sha256(terminal_report_path),
            "designRawSha256": raw_sha256(design_path),
            "evidenceSelfSha256": evidence["evidenceSha256"],
            "aggregateSelfSha256": aggregate["aggregateSha256"],
            "auditSelfSha256": audit["auditSha256"],
            "referenceAnchorsRawSha256": raw_sha256(reference_path),
        },
        "externalRecords": external,
        "authorizationPermitted": False,
        "tier2AutomaticallyPermitted": False,
        "productionPromotionAuthorized": False,
        "boundary": "deterministic audited 48-geometry continuation handoff only; model fitting, holdout opening, Tier-2 and production remain separate",
    }
    envelope_path = output_dir / "dataset-envelope.json"
    envelope_path.write_text(dump(envelope), encoding="utf-8", newline="\n")
    return {
        "evidence": evidence_path,
        "aggregate": aggregate_path,
        "audit": audit_path,
        "dataset": dataset_path,
        "design": design_path,
        "envelope": envelope_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dataset", type=Path, required=True)
    parser.add_argument("--wave1-manifest", type=Path, required=True)
    parser.add_argument("--wave1-results-root", type=Path, required=True)
    parser.add_argument("--wave2-manifest", type=Path, required=True)
    parser.add_argument("--wave2-results-root", type=Path, required=True)
    parser.add_argument("--wave1-aggregate", type=Path, required=True)
    parser.add_argument("--wave1-audit", type=Path, required=True)
    parser.add_argument("--wave2-aggregate", type=Path, required=True)
    parser.add_argument("--wave2-audit", type=Path, required=True)
    parser.add_argument("--final-analysis", type=Path, required=True)
    parser.add_argument("--terminal-report", type=Path, required=True)
    parser.add_argument("--reference-anchors", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--source-artifacts", type=Path, required=True)
    parser.add_argument("--main-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        outputs = build(
            args.source_dataset,
            args.wave1_manifest,
            args.wave1_results_root,
            args.wave2_manifest,
            args.wave2_results_root,
            args.wave1_aggregate,
            args.wave1_audit,
            args.wave2_aggregate,
            args.wave2_audit,
            args.final_analysis,
            args.terminal_report,
            args.reference_anchors,
            args.source_run,
            args.source_artifacts,
            args.output_dir,
            exact_main_sha=args.main_sha,
        )
        print(dump({"status": "TIER1_CONTINUATION_FINAL_HANDOFF_COMPLETE", "outputs": {key: str(value) for key, value in outputs.items()}}), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
