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

STAGE_ID = "twilight-surrogate-tier-1-analysis-v2"
SOURCE_STAGE = "twilight-surrogate-tier-1-execution-v1"
NODES = 15


class AnalysisError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise AnalysisError(f"expected object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(root: Path) -> list[dict[str, Any]]:
    return [load(path) for path in sorted(root.rglob("case-result.json"))]


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def summarize(values: list[float], node_rows: list[list[float]]) -> dict[str, Any]:
    count = len(values)
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values) if count > 1 else 0.0
    zero_hit_count = sum(value == 0.0 for value in values)
    if zero_hit_count:
        rsem = None
        rsem_status = "NOT_COMPUTED_ZERO_HIT_PRESENT"
    elif mean == 0.0:
        rsem = None
        rsem_status = "NOT_COMPUTED_ZERO_MEAN"
    else:
        rsem = (sample_std / math.sqrt(count)) / mean
        rsem_status = "COMPUTED"
    return {
        "blockCount": count,
        "valuesCdM2": values,
        "meanCdM2": mean,
        "sampleStdCdM2": sample_std,
        "relativeStandardErrorOfMean": rsem,
        "relativeStandardErrorStatus": rsem_status,
        "zeroHitBlockCount": zero_hit_count,
        "zeroHitBlockFraction": zero_hit_count / count,
        "nonzeroBlockValuesCdM2": [value for value in values if value != 0.0],
        "nodeMeanRadiance": [statistics.fmean(row[index] for row in node_rows) for index in range(NODES)],
    }


def analyze(
    manifest_path: Path,
    cases_root: Path,
    batch_summary_path: Path,
    audit_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, batch, audit = load(manifest_path), load(batch_summary_path), load(audit_path)
    if (
        manifest.get("stageId") != SOURCE_STAGE
        or len(manifest.get("geometries", [])) != 48
        or len(manifest.get("cases", [])) != 96
    ):
        raise AnalysisError("manifest invalid")
    if (
        batch.get("schemaVersion") != 2
        or batch.get("status") != "COMPLETED"
        or batch.get("executionComplete") is not True
        or batch.get("classification") not in {"BATCH_NUMERICALLY_COMPLETE", "SCIENTIFICALLY_INELIGIBLE"}
        or batch.get("caseCountCompleted") != 96
        or batch.get("configuredMcPhotonsSum") != 6_960_000_000
    ):
        raise AnalysisError("aggregate execution incomplete")
    if (
        audit.get("schemaVersion") != 2
        or audit.get("stageId") != "mystic-batch-v1"
        or audit.get("status") != "PASSED"
        or audit.get("batchClassification") != batch.get("classification")
        or audit.get("executionComplete") is not True
        or audit.get("scientificallyEligible") is not False
        or audit.get("caseResultCount") != 96
        or audit.get("failures") != []
        or audit.get("successDoesNotAuthorizeProduction") is not True
        or audit.get("incompleteGeometryEnteredTrainingEligibility") is not False
    ):
        raise AnalysisError("independent audit failed")
    manifest_hash = raw_sha256(manifest_path)
    aggregate_hash = raw_sha256(batch_summary_path)
    audit_hash = raw_sha256(audit_path)
    if (
        batch.get("manifestRawSha256") != manifest_hash
        or audit.get("manifestRawSha256") != manifest_hash
        or audit.get("aggregateRawSha256") != aggregate_hash
    ):
        raise AnalysisError("manifest, aggregate, or audit binding changed")
    result_paths = sorted(cases_root.rglob("case-result.json"))
    if len(result_paths) != 96:
        raise AnalysisError(f"expected 96 case rows, found {len(result_paths)}")
    all_rows: list[dict[str, Any]] = []
    case_result_hashes: dict[str, str] = {}
    for path in result_paths:
        row = load(path)
        case_id = row.get("caseId")
        if not isinstance(case_id, str) or case_id in case_result_hashes:
            raise AnalysisError(f"duplicate or invalid case {case_id}")
        case_result_hashes[case_id] = raw_sha256(path)
        all_rows.append(row)
    expected = {case["caseId"]: case for case in manifest["cases"]}
    if set(case_result_hashes) != set(expected):
        raise AnalysisError("case result universe differs from manifest")
    if audit.get("caseResultHashes") != case_result_hashes:
        raise AnalysisError("case result hashes differ from independent audit")
    source_bindings = {
        "manifestRawSha256": manifest_hash,
        "aggregateRawSha256": aggregate_hash,
        "auditRawSha256": audit_hash,
        "caseResultRawSha256ByCaseId": case_result_hashes,
    }
    by_group: dict[str, list[dict[str, Any]]] = {}
    for row in all_rows:
        case_id = row.get("caseId")
        expected_case = expected.get(case_id)
        if (
            expected_case is None
            or row.get("status") != "COMPLETED"
            or row.get("solver", {}).get("exitCode") != 0
            or row.get("solver", {}).get("timedOut") is not False
        ):
            raise AnalysisError(f"invalid case {case_id}")
        value = row.get("selectedPhotopicContributionCdM2")
        nodes = row.get("selectedNodeRadiance")
        if (
            row.get("seed") != expected_case["seed"]
            or row.get("photonHistories") != expected_case["photonHistories"]
            or not finite_number(value)
            or float(value) < 0.0
            or not isinstance(nodes, list)
            or len(nodes) != NODES
            or not all(finite_number(node) and float(node) >= 0.0 for node in nodes)
        ):
            raise AnalysisError(f"case invariant changed {case_id}")
        zero_value = float(value) == 0.0
        zero_nodes = all(float(node) == 0.0 for node in nodes)
        if zero_value != zero_nodes:
            raise AnalysisError(f"inconsistent zero estimator {case_id}")
        by_group.setdefault(expected_case["groupId"], []).append(row)

    geometry_map = {geometry["geometryId"]: geometry for geometry in manifest["geometries"]}
    points: list[dict[str, Any]] = []
    continuation: list[str] = []
    target: list[str] = []
    zero_hit_geometry_ids: list[str] = []
    for geometry_id in sorted(geometry_map):
        group = by_group.get(geometry_id, [])
        if len(group) != 2:
            raise AnalysisError(f"expected two blocks for {geometry_id}")
        values = [float(row["selectedPhotopicContributionCdM2"]) for row in group]
        stats = summarize(values, [[float(value) for value in row["selectedNodeRadiance"]] for row in group])
        if stats["zeroHitBlockCount"]:
            classification = "ADAPTIVE_CONTINUATION_REQUIRED"
            numerical_status = "NUMERICAL_ZERO_HIT_UNDERCONVERGED"
            zero_hit_geometry_ids.append(geometry_id)
        else:
            rsem = stats["relativeStandardErrorOfMean"]
            assert isinstance(rsem, float)
            classification = (
                "PRECISION_TARGET_MET"
                if rsem <= 0.05
                else "PRECISION_ACCEPTED"
                if rsem <= 0.08
                else "ADAPTIVE_CONTINUATION_REQUIRED"
            )
            numerical_status = "NUMERICALLY_CONVERGED" if classification != "ADAPTIVE_CONTINUATION_REQUIRED" else "NUMERICAL_PRECISION_INSUFFICIENT"
        if classification == "PRECISION_TARGET_MET":
            target.append(geometry_id)
        if classification == "ADAPTIVE_CONTINUATION_REQUIRED":
            continuation.append(geometry_id)
        group_cases = [case for case in manifest["cases"] if case["groupId"] == geometry_id]
        roles = {case["role"] for case in group_cases}
        if len(group_cases) != 2 or len(roles) != 1:
            raise AnalysisError(f"role or block contract changed for {geometry_id}")
        role = next(iter(roles))
        eligible = classification != "ADAPTIVE_CONTINUATION_REQUIRED"
        points.append(
            {
                "geometryId": geometry_id,
                "geometry": geometry_map[geometry_id],
                "role": role,
                "classification": classification,
                "numericalStatus": numerical_status,
                "executionComplete": True,
                "scientificallyEligible": eligible,
                "statistics": stats,
                "caseIds": sorted(row["caseId"] for row in group),
                "zeroHitCaseIds": sorted(
                    row["caseId"]
                    for row in group
                    if float(row["selectedPhotopicContributionCdM2"]) == 0.0
                ),
                "eligibleForProvisionalFit": eligible and role == "surrogate-training",
                "eligibleForInternalHoldout": eligible and role == "internal-holdout",
            }
        )

    accepted = 48 - len(continuation)
    scientifically_eligible = not continuation
    analysis = {
        "schemaVersion": 2,
        "stageId": STAGE_ID,
        "status": "TIER_1_ANALYZED" if scientifically_eligible else "TIER_1_ANALYZED_WITH_CONTINUATION_REQUIRED",
        "executionComplete": True,
        "scientificallyEligible": scientifically_eligible,
        "geometryCount": 48,
        "caseCount": 96,
        "configuredMcPhotonsSum": 6_960_000_000,
        "precisionTargetGeometryCount": len(target),
        "precisionAcceptedGeometryCount": accepted,
        "zeroHitGeometryIds": zero_hit_geometry_ids,
        "adaptiveContinuationRequiredGeometryIds": continuation,
        "allPointsWithinMaximumRsem": not continuation,
        "points": points,
        "sourceBindings": source_bindings,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "boundary": "Monte Carlo precision and zero-hit analysis only; no surrogate fit, physical validation, or production claim",
    }
    dataset = {
        "schemaVersion": 2,
        "stageId": STAGE_ID,
        "status": "TIER_1_NUMERICAL_DATASET_COMPLETE" if scientifically_eligible else "TIER_1_NUMERICAL_DATASET_PARTIAL_PRECISION",
        "executionComplete": True,
        "scientificallyEligible": scientifically_eligible,
        "records": points,
        "trainingRecordCount": sum(point["eligibleForProvisionalFit"] for point in points),
        "internalHoldoutRecordCount": sum(point["eligibleForInternalHoldout"] for point in points),
        "zeroHitGeometryIds": zero_hit_geometry_ids,
        "adaptiveContinuationRequiredGeometryIds": continuation,
        "sourceBindings": source_bindings,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "observationValidationRequired": True,
    }
    return analysis, dataset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cases-root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        analysis, dataset = analyze(args.manifest, args.cases_root, args.summary, args.audit)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "tier1-analysis.json").write_text(dump(analysis))
        (args.output_dir / "tier1-numerical-dataset.json").write_text(dump(dataset))
        print(dump(analysis), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
