#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path
from typing import Any

SOURCE_DATASET_STAGE = "twilight-surrogate-tier-1-analysis-v2"
SOURCE_DATASET_STATUS = "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION"
FINAL_DATASET_STAGE = "twilight-surrogate-tier-1-analysis-v1"
FINAL_DATASET_STATUS = "TIER_1_NUMERICAL_DATASET_COMPLETE"
FINAL_ANALYSIS_STAGE = "tier1-precision-continuation-wave2-analysis-v1"
ENVELOPE_STAGE = "twilight-surrogate-tier-1-dataset-envelope-v1"
GEOMETRY_COUNT = 48
TRAINING_COUNT = 39
HOLDOUT_COUNT = 9
CONTINUATION_GEOMETRY_COUNT = 20
ALLOWED_FINAL_BLOCK_COUNTS = {2, 4, 6, 8}
ALLOWED_RESULT_STAGES = {
    "tier1-precision-continuation-wave1-ordinal11-execution-v5",
    "tier1-precision-continuation-wave2-ordinal12-execution-v1",
}
ELIGIBLE_CLASSIFICATIONS = {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"}
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]


class HandoffRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise HandoffRefusal(f"expected JSON object: {path}")
    return value


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise HandoffRefusal(f"module unavailable: {path}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def _sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise HandoffRefusal(f"{label} must be lowercase sha256")
    return value


def _git_sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise HandoffRefusal(f"{label} must be lowercase git sha")
    return value


def _finite(
    value: Any,
    label: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HandoffRefusal(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise HandoffRefusal(f"{label} must be finite")
    if positive and number <= 0:
        raise HandoffRefusal(f"{label} must be positive")
    if nonnegative and number < 0:
        raise HandoffRefusal(f"{label} must be nonnegative")
    return number


def _photopic(nodes: list[float]) -> float:
    if len(nodes) != 15:
        raise HandoffRefusal("selected-node vector must contain 15 values")
    return 683.002 * 10.0 * sum(
        (value / 1000.0) * weight for value, weight in zip(nodes, CIE)
    )


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-11, abs_tol=1e-30)


def _load_case_results(*roots: Path) -> list[dict[str, Any]]:
    paths: list[Path] = []
    for root in roots:
        paths.extend(sorted(root.rglob("case-result.json")))
    rows = [load(path) for path in paths]
    seen: set[str] = set()
    for row in rows:
        case_id = row.get("caseId")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise HandoffRefusal(f"continuation case ID duplicated or missing: {case_id}")
        seen.add(case_id)
        if row.get("stageId") not in ALLOWED_RESULT_STAGES:
            raise HandoffRefusal(f"continuation result stage changed: {case_id}")
        if (
            row.get("status") != "COMPLETED"
            or row.get("syntaxCheckCount") != 1
            or row.get("solverExecutionCount") != 1
            or row.get("retryAllowed") is not False
            or row.get("resumeAllowed") is not False
            or row.get("fittingSurfaceExposed") is not False
        ):
            raise HandoffRefusal(f"continuation result execution proof changed: {case_id}")
        supplied = row.get("contentSha256")
        payload = {key: item for key, item in row.items() if key != "contentSha256"}
        if supplied != canonical_sha256(payload):
            raise HandoffRefusal(f"continuation result content hash changed: {case_id}")
        nodes = row.get("selectedNodeRadiance")
        if not isinstance(nodes, list) or len(nodes) != 15:
            raise HandoffRefusal(f"continuation selected nodes missing: {case_id}")
        parsed = [
            _finite(value, f"{case_id}.node[{index}]", nonnegative=True)
            for index, value in enumerate(nodes)
        ]
        value = _finite(
            row.get("selectedPhotopicContributionCdM2"),
            f"{case_id}.selectedPhotopicContributionCdM2",
            nonnegative=True,
        )
        if not _close(value, _photopic(parsed)):
            raise HandoffRefusal(f"continuation photopic value differs from raw nodes: {case_id}")
        zero_hit = value == 0.0 and all(node == 0.0 for node in parsed)
        if row.get("zeroHit") is not zero_hit:
            raise HandoffRefusal(f"continuation zero-hit semantics changed: {case_id}")
    return rows


def _source_nodes(source_audit: dict[str, Any], case_id: str) -> list[float]:
    raw = source_audit.get("rawCaseEvidence")
    evidence = raw.get(case_id) if isinstance(raw, dict) else None
    radiance = evidence.get("radiance") if isinstance(evidence, dict) else None
    nodes = radiance.get("selectedNodeValues") if isinstance(radiance, dict) else None
    if not isinstance(nodes, list) or len(nodes) != 15:
        raise HandoffRefusal(f"source raw selected nodes missing: {case_id}")
    return [
        _finite(value, f"source.{case_id}.node[{index}]", nonnegative=True)
        for index, value in enumerate(nodes)
    ]


def _statistics(node_rows: list[list[float]]) -> dict[str, Any]:
    if len(node_rows) not in ALLOWED_FINAL_BLOCK_COUNTS:
        raise HandoffRefusal("final block count is not an audited wave boundary")
    values = [_photopic(row) for row in node_rows]
    if any(value <= 0.0 for value in values):
        raise HandoffRefusal("final eligible geometry contains zero or negative block evidence")
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values)
    rsem = sample_std / math.sqrt(len(values)) / mean
    return {
        "blockCount": len(values),
        "valuesCdM2": values,
        "meanCdM2": mean,
        "sampleStdCdM2": sample_std,
        "relativeStandardErrorOfMean": rsem,
        "relativeStandardErrorStatus": "COMPUTED",
        "zeroHitBlockCount": 0,
        "zeroHitBlockFraction": 0.0,
        "nonzeroBlockValuesCdM2": values,
        "nodeMeanRadiance": [
            statistics.fmean(row[index] for row in node_rows) for index in range(15)
        ],
    }


def _point_map(final_analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if final_analysis.get("stageId") != FINAL_ANALYSIS_STAGE:
        raise HandoffRefusal("final continuation analysis stage changed")
    body = final_analysis.get("analysis")
    if not isinstance(body, dict) or body.get("status") != "CONTINUATION_ANALYZED":
        raise HandoffRefusal("final continuation analysis is incomplete")
    points = body.get("points")
    if not isinstance(points, list) or len(points) != CONTINUATION_GEOMETRY_COUNT:
        raise HandoffRefusal("final continuation point universe changed")
    if body.get("nextWaveGeometryIds") != [] or body.get("exhaustedGeometryIds") != []:
        raise HandoffRefusal("final continuation still requires execution or is exhausted")
    if body.get("scientificallyEligible") is not True:
        raise HandoffRefusal("final continuation is not scientifically eligible")
    if final_analysis.get("surrogateFitAuthorized") is not False:
        raise HandoffRefusal("analysis unexpectedly authorized fitting")
    result: dict[str, dict[str, Any]] = {}
    for point in points:
        if not isinstance(point, dict):
            raise HandoffRefusal("final continuation point is malformed")
        geometry_id = point.get("geometryId")
        if not isinstance(geometry_id, str) or not geometry_id or geometry_id in result:
            raise HandoffRefusal("final continuation geometry duplicated or missing")
        if (
            point.get("classification") not in ELIGIBLE_CLASSIFICATIONS
            or point.get("scientificallyEligible") is not True
            or point.get("zeroHitBlockCount") != 0
        ):
            raise HandoffRefusal(f"final continuation geometry is ineligible: {geometry_id}")
        block_count = point.get("blockCount")
        if block_count not in {4, 6, 8}:
            raise HandoffRefusal(f"final continuation block count invalid: {geometry_id}")
        values = point.get("valuesCdM2")
        if not isinstance(values, list) or len(values) != block_count:
            raise HandoffRefusal(f"final continuation values incomplete: {geometry_id}")
        result[geometry_id] = point
    return result


def build(
    *,
    source_dataset_path: Path,
    source_audit_path: Path,
    wave1_results_root: Path,
    wave2_results_root: Path,
    final_analysis_path: Path,
    reference_anchors_path: Path,
    final_manifest_path: Path,
    final_aggregate_path: Path,
    final_audit_path: Path,
    exact_main_sha: str,
    output_dir: Path,
) -> dict[str, Path]:
    _git_sha(exact_main_sha, "exact main sha")
    source_dataset = load(source_dataset_path)
    source_audit = load(source_audit_path)
    final_analysis = load(final_analysis_path)
    final_manifest = load(final_manifest_path)
    final_aggregate = load(final_aggregate_path)
    final_audit = load(final_audit_path)
    if (
        source_dataset.get("stageId") != SOURCE_DATASET_STAGE
        or source_dataset.get("status") != SOURCE_DATASET_STATUS
        or source_dataset.get("executionComplete") is not True
    ):
        raise HandoffRefusal("source corrected dataset boundary changed")
    source_records = source_dataset.get("records")
    if not isinstance(source_records, list) or len(source_records) != GEOMETRY_COUNT:
        raise HandoffRefusal("source corrected dataset geometry count changed")
    by_id: dict[str, dict[str, Any]] = {}
    training_ids: list[str] = []
    holdout_ids: list[str] = []
    for record in source_records:
        if not isinstance(record, dict):
            raise HandoffRefusal("source record is malformed")
        geometry_id = record.get("geometryId")
        role = record.get("role")
        if not isinstance(geometry_id, str) or geometry_id in by_id:
            raise HandoffRefusal("source geometry duplicated or missing")
        if role == "surrogate-training":
            training_ids.append(geometry_id)
        elif role == "internal-holdout":
            holdout_ids.append(geometry_id)
        else:
            raise HandoffRefusal(f"source role changed: {geometry_id}")
        by_id[geometry_id] = record
    if len(training_ids) != TRAINING_COUNT or len(holdout_ids) != HOLDOUT_COUNT:
        raise HandoffRefusal("source 39/9 role partition changed")

    points = _point_map(final_analysis)
    continuation_rows = _load_case_results(wave1_results_root, wave2_results_root)
    grouped: dict[str, dict[int, dict[str, Any]]] = {}
    for row in continuation_rows:
        group_id = row.get("groupId")
        block = row.get("block")
        if group_id not in points or block not in {3, 4, 5, 6, 7, 8}:
            raise HandoffRefusal(f"unplanned continuation result: {row.get('caseId')}")
        if block in grouped.setdefault(group_id, {}):
            raise HandoffRefusal(f"duplicate continuation block: {group_id} b{block}")
        grouped[group_id][block] = row

    manifest_sha = raw_sha256(final_manifest_path)
    aggregate_sha = raw_sha256(final_aggregate_path)
    audit_sha = raw_sha256(final_audit_path)
    analysis_sha = raw_sha256(final_analysis_path)
    source_dataset_sha = raw_sha256(source_dataset_path)
    source_audit_sha = raw_sha256(source_audit_path)
    records: list[dict[str, Any]] = []
    all_case_ids: set[str] = set()
    case_hashes: dict[str, str] = {}
    for geometry_id in sorted(by_id):
        source = by_id[geometry_id]
        point = points.get(geometry_id)
        if point is None:
            if (
                source.get("classification") not in ELIGIBLE_CLASSIFICATIONS
                or source.get("scientificallyEligible") is not True
            ):
                raise HandoffRefusal(
                    f"non-continuation source geometry is ineligible: {geometry_id}"
                )
            record = copy.deepcopy(source)
            case_ids = record.get("caseIds")
            statistics_value = record.get("statistics")
            if (
                not isinstance(case_ids, list)
                or len(case_ids) != 2
                or not isinstance(statistics_value, dict)
                or statistics_value.get("blockCount") != 2
            ):
                raise HandoffRefusal(f"source eligible geometry evidence changed: {geometry_id}")
        else:
            source_case_ids = source.get("caseIds")
            if not isinstance(source_case_ids, list) or len(source_case_ids) != 2:
                raise HandoffRefusal(f"source continuation case IDs changed: {geometry_id}")
            expected_blocks = list(range(3, point["blockCount"] + 1))
            observed = grouped.get(geometry_id, {})
            if sorted(observed) != expected_blocks:
                raise HandoffRefusal(f"continuation blocks incomplete: {geometry_id}")
            node_rows = [_source_nodes(source_audit, case_id) for case_id in source_case_ids]
            continuation_case_ids: list[str] = []
            for block in expected_blocks:
                row = observed[block]
                nodes = [float(value) for value in row["selectedNodeRadiance"]]
                node_rows.append(nodes)
                continuation_case_ids.append(row["caseId"])
                case_hashes[row["caseId"]] = row["contentSha256"]
            statistics_value = _statistics(node_rows)
            point_values = [
                _finite(value, f"{geometry_id}.point.value", positive=True)
                for value in point["valuesCdM2"]
            ]
            if len(point_values) != len(statistics_value["valuesCdM2"]) or any(
                not _close(left, right)
                for left, right in zip(point_values, statistics_value["valuesCdM2"])
            ):
                raise HandoffRefusal(
                    f"final analysis differs from independently recomputed raw evidence: {geometry_id}"
                )
            if not _close(
                point["relativeStandardErrorOfMean"],
                statistics_value["relativeStandardErrorOfMean"],
            ):
                raise HandoffRefusal(f"final RSEM differs from raw evidence: {geometry_id}")
            record = {
                "geometryId": geometry_id,
                "geometry": copy.deepcopy(source["geometry"]),
                "role": source["role"],
                "classification": point["classification"],
                "numericalStatus": point["numericalStatus"],
                "scientificallyEligible": True,
                "executionComplete": True,
                "eligibleForProvisionalFit": source["role"] == "surrogate-training",
                "eligibleForInternalHoldout": source["role"] == "internal-holdout",
                "caseIds": list(source_case_ids) + continuation_case_ids,
                "statistics": statistics_value,
                "zeroHitCaseIds": [],
            }
            case_ids = record["caseIds"]
        for case_id in case_ids:
            if not isinstance(case_id, str) or not case_id or case_id in all_case_ids:
                raise HandoffRefusal(f"final case ID duplicated or missing: {case_id}")
            all_case_ids.add(case_id)
        record["sourceBindings"] = {
            "manifestRawSha256": manifest_sha,
            "aggregateRawSha256": aggregate_sha,
            "auditRawSha256": audit_sha,
            "analysisRawSha256": analysis_sha,
            "sourceDatasetRawSha256": source_dataset_sha,
            "sourceAuditRawSha256": source_audit_sha,
            "continuationCaseResultContentSha256ByCaseId": {
                case_id: case_hashes[case_id]
                for case_id in record["caseIds"]
                if case_id in case_hashes
            },
        }
        if (
            record.get("classification") not in ELIGIBLE_CLASSIFICATIONS
            or record.get("scientificallyEligible") is not True
            or record["statistics"].get("blockCount") not in ALLOWED_FINAL_BLOCK_COUNTS
        ):
            raise HandoffRefusal(f"final record is not training eligible: {geometry_id}")
        records.append(record)

    tier1 = _module(
        Path(__file__).with_name("tier1_handoff.py"),
        "surrogate_training_v2_continuation_reference",
    )
    hard_ids, soft_ids, external = tier1.validate_reference(load(reference_anchors_path))
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
        "rolesByGeometryId": {
            geometry_id: by_id[geometry_id]["role"] for geometry_id in sorted(by_id)
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    design_path = output_dir / "frozen-design.json"
    design_path.write_text(dump(design), encoding="utf-8", newline="\n")
    dataset = {
        "schemaVersion": 2,
        "stageId": FINAL_DATASET_STAGE,
        "status": FINAL_DATASET_STATUS,
        **boundary,
        "records": records,
        "trainingGeometryIds": sorted(training_ids),
        "internalHoldoutGeometryIds": sorted(holdout_ids),
        "hardExternalAnchorIds": hard_ids,
        "softDiagnosticIds": soft_ids,
    }
    dataset_path = output_dir / "tier1-numerical-dataset.json"
    dataset_path.write_text(dump(dataset), encoding="utf-8", newline="\n")
    bindings = {
        "manifestRawSha256": manifest_sha,
        "aggregateRawSha256": aggregate_sha,
        "independentAuditRawSha256": audit_sha,
        "analysisRawSha256": analysis_sha,
        "designRawSha256": raw_sha256(design_path),
        "sourceDatasetRawSha256": source_dataset_sha,
        "sourceAuditRawSha256": source_audit_sha,
        "referenceAnchorsRawSha256": raw_sha256(reference_anchors_path),
    }
    envelope = {
        "schemaVersion": 1,
        "stageId": ENVELOPE_STAGE,
        "aggregatePassed": True,
        "independentAuditPassed": True,
        "precisionClassificationComplete": True,
        "provenanceValidated": True,
        **boundary,
        "exactMainSha": exact_main_sha,
        "datasetRawSha256": raw_sha256(dataset_path),
        "bindings": bindings,
        "externalRecords": external,
        "authorizationPermitted": False,
        "tier2AutomaticallyPermitted": False,
        "productionPromotionAuthorized": False,
        "modelFittingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "boundary": "post-continuation numerical dataset handoff only; no fitting, holdout opening, Tier-2 action, observational-validity claim, or production promotion",
    }
    envelope_path = output_dir / "dataset-envelope.json"
    envelope_path.write_text(dump(envelope), encoding="utf-8", newline="\n")
    report = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-continuation-handoff-v1",
        "status": "FINAL_NUMERICAL_DATASET_READY_FOR_SEPARATE_TRAINING_REVIEW",
        "exactMainSha": exact_main_sha,
        "geometryCount": len(records),
        "trainingGeometryCount": len(training_ids),
        "internalHoldoutGeometryCount": len(holdout_ids),
        "caseCount": len(all_case_ids),
        "datasetRawSha256": raw_sha256(dataset_path),
        "envelopeRawSha256": raw_sha256(envelope_path),
        "designRawSha256": raw_sha256(design_path),
        "modelFittingAuthorized": False,
        "internalHoldoutOpeningAuthorized": False,
        "tier2Authorized": False,
        "productionPromotionAuthorized": False,
    }
    report["reportSha256"] = canonical_sha256(report)
    report_path = output_dir / "handoff-report.json"
    report_path.write_text(dump(report), encoding="utf-8", newline="\n")
    return {
        "dataset": dataset_path,
        "design": design_path,
        "envelope": envelope_path,
        "report": report_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dataset", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--wave1-results-root", type=Path, required=True)
    parser.add_argument("--wave2-results-root", type=Path, required=True)
    parser.add_argument("--final-analysis", type=Path, required=True)
    parser.add_argument("--reference-anchors", type=Path, required=True)
    parser.add_argument("--final-manifest", type=Path, required=True)
    parser.add_argument("--final-aggregate", type=Path, required=True)
    parser.add_argument("--final-audit", type=Path, required=True)
    parser.add_argument("--exact-main-sha", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(
            source_dataset_path=args.source_dataset,
            source_audit_path=args.source_audit,
            wave1_results_root=args.wave1_results_root,
            wave2_results_root=args.wave2_results_root,
            final_analysis_path=args.final_analysis,
            reference_anchors_path=args.reference_anchors,
            final_manifest_path=args.final_manifest,
            final_aggregate_path=args.final_aggregate,
            final_audit_path=args.final_audit,
            exact_main_sha=args.exact_main_sha,
            output_dir=args.output_dir,
        )
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
