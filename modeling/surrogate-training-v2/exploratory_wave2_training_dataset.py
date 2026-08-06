#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any

SOURCE_DATASET_RAW_SHA256 = "81db9f2c418d4b078c23586513c5ba4591f3f3a496367bd818c8701d26136c00"
SOURCE_AUDIT_RAW_SHA256 = "a3b427bbd345e310f851d8839da4ff92931f9b747e6981700eb5a3878a38882b"
ORDINAL12_ANALYSIS_RAW_SHA256 = "c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237"

SOURCE_STAGE = "twilight-surrogate-tier-1-analysis-v2"
SOURCE_STATUS = "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION"
ANALYSIS_STAGE = "tier1-precision-continuation-wave2-analysis-v1"
OUTPUT_STAGE = "surrogate-training-v2-wave2-training-only-dataset-v1"
OUTPUT_STATUS = "AUDITED_B1_B6_TRAINING_ONLY_DATASET_HOLDOUT_UNOPENED"
WAVE1_RESULT_STAGE = "tier1-precision-continuation-wave1-ordinal11-execution-v5"
WAVE2_RESULT_STAGE = "tier1-precision-continuation-wave2-ordinal12-execution-v1"

TRAINING_IDS = tuple(f"train-{index:04d}" for index in range(1, 49) if index % 5 != 0)
HOLDOUT_IDS = tuple(f"train-{index:04d}" for index in range(1, 49) if index % 5 == 0)
ALL_IDS = tuple(f"train-{index:04d}" for index in range(1, 49))
CONTINUATION_IDS = (
    "train-0003", "train-0007", "train-0009", "train-0011", "train-0013",
    "train-0015", "train-0017", "train-0019", "train-0023", "train-0027",
    "train-0029", "train-0031", "train-0033", "train-0035", "train-0039",
    "train-0041", "train-0043", "train-0045", "train-0046", "train-0047",
)
WAVE1_TRAINING_IDS = tuple(gid for gid in CONTINUATION_IDS if gid in TRAINING_IDS)
WAVE2_TRAINING_IDS = (
    "train-0003", "train-0007", "train-0009", "train-0011", "train-0013",
    "train-0019", "train-0023", "train-0027", "train-0029", "train-0031",
    "train-0039", "train-0041", "train-0043", "train-0047",
)
WAVE1_ONLY_TRAINING_IDS = tuple(gid for gid in WAVE1_TRAINING_IDS if gid not in WAVE2_TRAINING_IDS)
CIE = [0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.71, 0.862, 0.954, 0.995, 0.87, 0.757, 0.631, 0.503, 0.175, 0.061]
ELIGIBLE = {"PRECISION_TARGET_MET", "PRECISION_ACCEPTED"}

if len(TRAINING_IDS) != 39 or len(HOLDOUT_IDS) != 9:
    raise RuntimeError("frozen 39/9 role map changed")
if len(WAVE1_TRAINING_IDS) != 17 or len(WAVE2_TRAINING_IDS) != 14:
    raise RuntimeError("frozen wave-one/wave-two training universe changed")


class Refusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Refusal(f"expected object: {path}")
    return value


def _array_bounds(text: str, key: str) -> tuple[int, int, list[str]]:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if match is None:
        raise Refusal(f"array missing: {key}")
    open_index = text.find("[", match.start())
    index = open_index + 1
    in_string = False
    escaped = False
    depth = 0
    start: int | None = None
    objects: list[str] = []
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char == "{":
                if depth == 0:
                    start = index
                depth += 1
            elif char == "}":
                depth -= 1
                if depth < 0 or (depth == 0 and start is None):
                    raise Refusal(f"malformed object array: {key}")
                if depth == 0:
                    objects.append(text[start:index + 1])
                    start = None
            elif char == "]" and depth == 0:
                return open_index, index, objects
        index += 1
    raise Refusal(f"unterminated array: {key}")


def _identity(raw: str, label: str) -> str:
    match = re.search(r'"geometryId"\s*:\s*"([^"]+)"', raw)
    if match is None:
        raise Refusal(f"{label} identity missing")
    return match.group(1)


def load_training_source(path: Path, *, expected_raw_sha256: str = SOURCE_DATASET_RAW_SHA256) -> list[dict[str, Any]]:
    if raw_sha256(path) != expected_raw_sha256:
        raise Refusal("source corrected dataset raw hash changed")
    text = path.read_text(encoding="utf-8")
    left, right, objects = _array_bounds(text, "records")
    skeleton = json.loads(text[:left] + "[]" + text[right + 1:])
    if not isinstance(skeleton, dict):
        raise Refusal("source corrected dataset top level malformed")
    expected = {
        "schemaVersion": 2,
        "stageId": SOURCE_STAGE,
        "status": SOURCE_STATUS,
        "executionComplete": True,
        "scientificallyEligible": False,
        "surrogateTrainingAutomaticallyAuthorized": False,
    }
    stale = {key: (skeleton.get(key), wanted) for key, wanted in expected.items() if skeleton.get(key) != wanted}
    if stale:
        raise Refusal(f"source corrected dataset boundary changed: {stale}")
    identities = [_identity(raw, "source record") for raw in objects]
    if tuple(identities) != ALL_IDS or len(set(identities)) != 48:
        raise Refusal("source geometry order or universe changed")
    records: list[dict[str, Any]] = []
    for raw, geometry_id in zip(objects, identities, strict=True):
        role_match = re.search(r'"role"\s*:\s*"([^"]+)"', raw)
        role = role_match.group(1) if role_match else None
        expected_role = "surrogate-training" if geometry_id in TRAINING_IDS else "internal-holdout"
        if role != expected_role:
            raise Refusal(f"source role map changed: {geometry_id}")
        if geometry_id in TRAINING_IDS:
            record = json.loads(raw)
            if not isinstance(record, dict) or record.get("geometryId") != geometry_id:
                raise Refusal(f"source training record malformed: {geometry_id}")
            records.append(record)
    if tuple(row.get("geometryId") for row in records) != TRAINING_IDS:
        raise Refusal("source training subset changed")
    return records


def load_training_points(path: Path, *, expected_raw_sha256: str = ORDINAL12_ANALYSIS_RAW_SHA256) -> dict[str, dict[str, Any]]:
    if raw_sha256(path) != expected_raw_sha256:
        raise Refusal("ordinal-12 analysis raw hash changed")
    text = path.read_text(encoding="utf-8")
    left, right, objects = _array_bounds(text, "points")
    skeleton = json.loads(text[:left] + "[]" + text[right + 1:])
    body = skeleton.get("analysis") if isinstance(skeleton, dict) else None
    expected_top = {
        "schemaVersion": 1,
        "stageId": ANALYSIS_STAGE,
        "additionalExecutionAutomaticallyAuthorized": False,
        "internalHoldoutOpened": False,
        "productionPromotionAuthorized": False,
        "surrogateFitAuthorized": False,
        "tier2Authorized": False,
    }
    stale_top = {key: (skeleton.get(key), wanted) for key, wanted in expected_top.items() if skeleton.get(key) != wanted}
    if stale_top:
        raise Refusal(f"ordinal-12 analysis boundary changed: {stale_top}")
    expected_body = {
        "schemaVersion": 2,
        "stageId": "tier1-precision-continuation-analysis-v2",
        "status": "CONTINUATION_ANALYZED",
        "scientificallyEligible": False,
        "surrogateFitAuthorized": False,
        "additionalExecutionAutomaticallyAuthorized": False,
        "productionPromotionAuthorized": False,
    }
    if not isinstance(body, dict):
        raise Refusal("ordinal-12 analysis body missing")
    stale_body = {key: (body.get(key), wanted) for key, wanted in expected_body.items() if body.get(key) != wanted}
    if stale_body:
        raise Refusal(f"ordinal-12 analysis body changed: {stale_body}")
    identities = [_identity(raw, "analysis point") for raw in objects]
    if tuple(identities) != CONTINUATION_IDS or len(set(identities)) != 20:
        raise Refusal("ordinal-12 continuation point order or universe changed")
    selected: dict[str, dict[str, Any]] = {}
    for raw, geometry_id in zip(objects, identities, strict=True):
        if geometry_id in WAVE1_TRAINING_IDS:
            point = json.loads(raw)
            if not isinstance(point, dict):
                raise Refusal(f"analysis training point malformed: {geometry_id}")
            selected[geometry_id] = point
    if tuple(selected) != WAVE1_TRAINING_IDS:
        raise Refusal("ordinal-12 training point subset changed")
    return selected


def _photopic(nodes: list[float]) -> float:
    if len(nodes) != 15:
        raise Refusal("selected-node vector must contain 15 values")
    return 683.002 * 10.0 * sum((value / 1000.0) * weight for value, weight in zip(nodes, CIE, strict=True))


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-11, abs_tol=1e-30)


def _validated_result(path: Path, expected_stage: str, expected_blocks: set[int]) -> dict[str, Any]:
    row = load(path)
    case_id = row.get("caseId")
    group_id = row.get("groupId")
    block = row.get("block")
    payload = {key: item for key, item in row.items() if key != "contentSha256"}
    if row.get("contentSha256") != canonical_sha256(payload):
        raise Refusal(f"continuation result content hash changed: {case_id}")
    nodes = row.get("selectedNodeRadiance")
    value = row.get("selectedPhotopicContributionCdM2")
    if (
        group_id not in WAVE1_TRAINING_IDS
        or block not in expected_blocks
        or row.get("stageId") != expected_stage
        or row.get("status") != "COMPLETED"
        or row.get("role") != "surrogate-training"
        or row.get("syntaxCheckCount") != 1
        or row.get("solverExecutionCount") != 1
        or row.get("retryAllowed") is not False
        or row.get("resumeAllowed") is not False
        or row.get("fittingSurfaceExposed") is not False
        or not isinstance(nodes, list)
        or len(nodes) != 15
        or any(isinstance(node, bool) or not isinstance(node, (int, float)) or not math.isfinite(float(node)) or float(node) < 0 for node in nodes)
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise Refusal(f"continuation execution proof changed: {case_id}")
    parsed_nodes = [float(node) for node in nodes]
    if not _close(float(value), _photopic(parsed_nodes)):
        raise Refusal(f"continuation photopic value differs from selected nodes: {case_id}")
    zero_hit = float(value) == 0.0 and all(node == 0.0 for node in parsed_nodes)
    if row.get("zeroHit") is not zero_hit:
        raise Refusal(f"continuation zero-hit semantics changed: {case_id}")
    return row


def load_results(root: Path, expected_ids: tuple[str, ...], expected_stage: str, expected_blocks: set[int]) -> dict[str, dict[int, dict[str, Any]]]:
    paths = sorted(root.rglob("case-result.json"))
    expected_count = len(expected_ids) * len(expected_blocks)
    if len(paths) != expected_count:
        raise Refusal(f"expected {expected_count} continuation training results, found {len(paths)}")
    grouped: dict[str, dict[int, dict[str, Any]]] = {}
    for path in paths:
        row = _validated_result(path, expected_stage, expected_blocks)
        geometry_id = row["groupId"]
        block = int(row["block"])
        if geometry_id not in expected_ids:
            raise Refusal(f"unplanned continuation training result: {row.get('caseId')}")
        if block in grouped.setdefault(geometry_id, {}):
            raise Refusal(f"duplicate continuation training block: {geometry_id} b{block}")
        grouped[geometry_id][block] = row
    if tuple(sorted(grouped)) != tuple(sorted(expected_ids)) or any(set(pair) != expected_blocks for pair in grouped.values()):
        raise Refusal("continuation training result matrix incomplete")
    return grouped


def _statistics(values: list[float], point: dict[str, Any], node_mean: list[float], geometry_id: str) -> dict[str, Any]:
    if len(values) not in {4, 6}:
        raise Refusal(f"wave-two block count invalid: {geometry_id}")
    point_values = point.get("valuesCdM2")
    if not isinstance(point_values, list) or len(point_values) != len(values):
        raise Refusal(f"analysis values incomplete: {geometry_id}")
    if any(not _close(left, float(right)) for left, right in zip(values, point_values, strict=True)):
        raise Refusal(f"analysis/result value mismatch: {geometry_id}")
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values)
    zero_count = sum(value == 0.0 for value in values)
    if zero_count:
        rsem: float | None = None
        rsem_status = "NOT_COMPUTED_ZERO_HIT_PRESENT"
    else:
        rsem = sample_std / math.sqrt(len(values)) / mean
        rsem_status = "COMPUTED"
    point_rsem = point.get("relativeStandardErrorOfMean")
    if (rsem is None) != (point_rsem is None) or (rsem is not None and not _close(rsem, float(point_rsem))):
        raise Refusal(f"analysis RSEM mismatch: {geometry_id}")
    if point.get("relativeStandardErrorStatus") != rsem_status:
        raise Refusal(f"analysis RSEM status mismatch: {geometry_id}")
    if point.get("zeroHitBlockCount") != zero_count or not _close(float(point.get("zeroHitBlockFraction")), zero_count / len(values)):
        raise Refusal(f"analysis zero-hit count mismatch: {geometry_id}")
    nonzero = [value for value in values if value != 0.0]
    point_nonzero = point.get("nonzeroBlockValuesCdM2")
    if not isinstance(point_nonzero, list) or len(point_nonzero) != len(nonzero) or any(not _close(left, float(right)) for left, right in zip(nonzero, point_nonzero, strict=True)):
        raise Refusal(f"analysis nonzero value mismatch: {geometry_id}")
    return {
        "blockCount": len(values),
        "valuesCdM2": values,
        "meanCdM2": mean,
        "sampleStdCdM2": sample_std,
        "relativeStandardErrorOfMean": rsem,
        "relativeStandardErrorStatus": rsem_status,
        "zeroHitBlockCount": zero_count,
        "zeroHitBlockFraction": zero_count / len(values),
        "nonzeroBlockValuesCdM2": nonzero,
        "nodeMeanRadiance": node_mean,
    }


def updated_record(source: dict[str, Any], point: dict[str, Any], wave1: dict[int, dict[str, Any]], wave2: dict[int, dict[str, Any]] | None, source_hashes: dict[str, str]) -> dict[str, Any]:
    geometry_id = source["geometryId"]
    expected_blocks = 6 if geometry_id in WAVE2_TRAINING_IDS else 4
    if point.get("blockCount") != expected_blocks or point.get("role") != "surrogate-training":
        raise Refusal(f"analysis training point block/role changed: {geometry_id}")
    rows = [wave1[3], wave1[4]]
    if wave2 is not None:
        rows.extend([wave2[5], wave2[6]])
    source_stats = source.get("statistics")
    source_values = source_stats.get("valuesCdM2") if isinstance(source_stats, dict) else None
    source_nodes = source_stats.get("nodeMeanRadiance") if isinstance(source_stats, dict) else None
    source_cases = source.get("caseIds")
    if (
        not isinstance(source_values, list) or len(source_values) != 2
        or not isinstance(source_nodes, list) or len(source_nodes) != 15
        or not isinstance(source_cases, list) or len(source_cases) != 2
        or source_stats.get("blockCount") != 2
    ):
        raise Refusal(f"source b1-b2 training evidence changed: {geometry_id}")
    values = [float(value) for value in source_values] + [float(row["selectedPhotopicContributionCdM2"]) for row in rows]
    node_mean = [
        (2.0 * float(old) + sum(float(row["selectedNodeRadiance"][index]) for row in rows)) / expected_blocks
        for index, old in enumerate(source_nodes)
    ]
    classification = point.get("classification")
    scientifically_eligible = classification in ELIGIBLE
    if point.get("scientificallyEligible") is not scientifically_eligible:
        raise Refusal(f"analysis eligibility mismatch: {geometry_id}")
    record = copy.deepcopy(source)
    record["caseIds"] = list(source_cases) + [row["caseId"] for row in rows]
    record["classification"] = classification
    record["numericalStatus"] = point.get("numericalStatus")
    record["scientificallyEligible"] = scientifically_eligible
    record["eligibleForProvisionalFit"] = scientifically_eligible
    record["eligibleForInternalHoldout"] = False
    record["statistics"] = _statistics(values, point, node_mean, geometry_id)
    record["zeroHitCaseIds"] = list(source.get("zeroHitCaseIds") or []) + [row["caseId"] for row in rows if row.get("zeroHit")]
    bindings = dict(record.get("sourceBindings") or {})
    bindings.update(source_hashes)
    bindings["continuationCaseContentSha256ByCaseId"] = {row["caseId"]: row["contentSha256"] for row in rows}
    record["sourceBindings"] = bindings
    return record


def build(
    source_dataset_path: Path,
    source_audit_path: Path,
    ordinal12_analysis_path: Path,
    wave1_results_root: Path,
    wave2_results_root: Path,
    *,
    expected_source_dataset_sha256: str = SOURCE_DATASET_RAW_SHA256,
    expected_source_audit_sha256: str = SOURCE_AUDIT_RAW_SHA256,
    expected_analysis_sha256: str = ORDINAL12_ANALYSIS_RAW_SHA256,
) -> dict[str, Any]:
    if raw_sha256(source_audit_path) != expected_source_audit_sha256:
        raise Refusal("source corrected audit raw hash changed")
    source_rows = load_training_source(source_dataset_path, expected_raw_sha256=expected_source_dataset_sha256)
    points = load_training_points(ordinal12_analysis_path, expected_raw_sha256=expected_analysis_sha256)
    wave1 = load_results(wave1_results_root, WAVE1_TRAINING_IDS, WAVE1_RESULT_STAGE, {3, 4})
    wave2 = load_results(wave2_results_root, WAVE2_TRAINING_IDS, WAVE2_RESULT_STAGE, {5, 6})
    source_hashes = {
        "sourceCorrectedDatasetRawSha256": expected_source_dataset_sha256,
        "sourceCorrectedAuditRawSha256": expected_source_audit_sha256,
        "ordinal12AnalysisRawSha256": expected_analysis_sha256,
    }
    output_rows: list[dict[str, Any]] = []
    for source in source_rows:
        geometry_id = source["geometryId"]
        if geometry_id in WAVE1_TRAINING_IDS:
            output_rows.append(updated_record(source, points[geometry_id], wave1[geometry_id], wave2.get(geometry_id), source_hashes))
        else:
            record = copy.deepcopy(source)
            bindings = dict(record.get("sourceBindings") or {})
            bindings.update(source_hashes)
            record["sourceBindings"] = bindings
            output_rows.append(record)
    block_counts = {2: 0, 4: 0, 6: 0}
    for row in output_rows:
        count = row.get("statistics", {}).get("blockCount")
        if count not in block_counts:
            raise Refusal(f"unexpected b1-b6 training block count: {row.get('geometryId')}")
        block_counts[count] += 1
    if block_counts != {2: 22, 4: 3, 6: 14}:
        raise Refusal(f"b1-b6 training block-count distribution changed: {block_counts}")
    value: dict[str, Any] = {
        "schemaVersion": 1,
        "stageId": OUTPUT_STAGE,
        "status": OUTPUT_STATUS,
        "sourceCorrectedDatasetRawSha256": expected_source_dataset_sha256,
        "sourceCorrectedAuditRawSha256": expected_source_audit_sha256,
        "ordinal12AnalysisRawSha256": expected_analysis_sha256,
        "trainingGeometryIds": list(TRAINING_IDS),
        "internalHoldoutGeometryIdsExcludedAndUnopened": list(HOLDOUT_IDS),
        "holdoutRecordCount": 0,
        "holdoutValuesIncluded": False,
        "blockCountDistribution": {str(key): count for key, count in sorted(block_counts.items())},
        "records": output_rows,
    }
    value["datasetSha256"] = canonical_sha256(value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dataset", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--ordinal12-analysis", type=Path, required=True)
    parser.add_argument("--wave1-results-root", type=Path, required=True)
    parser.add_argument("--wave2-results-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = build(args.source_dataset, args.source_audit, args.ordinal12_analysis, args.wave1_results_root, args.wave2_results_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(value), encoding="utf-8", newline="\n")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
