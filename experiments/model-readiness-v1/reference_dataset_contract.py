#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

EXPECTED_GROUPS = {
    "g01-reference-bridge",
    "g02-early-near-low",
    "g03-early-perpendicular-high",
    "g04-mid-perpendicular",
    "g05-mid-opposite-low",
    "g06-late-opposite-high-aerosol",
}
METHODS = ("reference-vroom", "alis")
GEOMETRY_FIELDS = (
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthDeg",
    "observerElevationM",
    "aod550",
)


class ContractError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ContractError(f"expected JSON object: {path}")
    return value


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def finite(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ContractError(f"{name} must be finite")
    return result


def validate_geometry(group: str, geometry: Any) -> dict[str, float]:
    if not isinstance(geometry, dict):
        raise ContractError(f"geometry missing for {group}")
    if geometry.get("geometryId") != group:
        raise ContractError(f"geometryId mismatch for {group}")
    result = {field: finite(geometry.get(field), f"{group}.{field}") for field in GEOMETRY_FIELDS}
    if not 0.0 <= result["sunDepressionDeg"] <= 20.0:
        raise ContractError(f"sun depression outside contract for {group}")
    if not 0.0 <= result["targetAltitudeDeg"] <= 90.0:
        raise ContractError(f"target altitude outside contract for {group}")
    if not 0.0 <= result["relativeAzimuthDeg"] <= 180.0:
        raise ContractError(f"relative azimuth outside contract for {group}")
    if not 0.0 <= result["observerElevationM"] <= 5000.0:
        raise ContractError(f"observer elevation outside contract for {group}")
    if not 0.0 < result["aod550"] <= 1.0:
        raise ContractError(f"AOD outside contract for {group}")
    return result


def validate_method(group: str, method: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"method statistics missing: {group} {method}")
    block_count = value.get("blockCount")
    if not isinstance(block_count, int) or block_count < 2:
        raise ContractError(f"at least two independent blocks required: {group} {method}")
    mean = finite(value.get("meanCdM2"), f"{group}.{method}.meanCdM2")
    rsem = finite(value.get("relativeStandardErrorOfMean"), f"{group}.{method}.RSEM")
    if mean <= 0.0:
        raise ContractError(f"nonpositive mean: {group} {method}")
    if not 0.0 <= rsem <= 0.10:
        raise ContractError(f"RSEM exceeds anchor contract: {group} {method}: {rsem}")
    nodes = value.get("nodeMeanRadiance")
    if not isinstance(nodes, list) or len(nodes) != 15:
        raise ContractError(f"expected 15 spectral nodes: {group} {method}")
    node_values = [finite(node, f"{group}.{method}.node[{index}]") for index, node in enumerate(nodes)]
    if any(node < 0.0 for node in node_values):
        raise ContractError(f"negative spectral node: {group} {method}")
    return {
        "blockCount": block_count,
        "meanCdM2": mean,
        "relativeStandardErrorOfMean": rsem,
        "nodeMeanRadiance": node_values,
    }


def validate(dataset: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    required_dataset = {
        "schemaVersion": 1,
        "status": "AUDITED_COMPUTATIONAL_REFERENCE_DATASET",
        "sourceStageId": "cross-geometry-held-out-confirmation-timeout-continuation-v1",
        "screeningOnly": True,
        "observationValidationRequired": True,
    }
    stale = {key: (dataset.get(key), expected) for key, expected in required_dataset.items() if dataset.get(key) != expected}
    if stale:
        raise ContractError(f"dataset boundary changed: {stale}")
    required_readiness = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE",
        "computationalReferenceScreeningComplete": True,
        "acceptedReferenceGeometryCount": 6,
        "heldOutConfirmationFailureCount": 0,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
    }
    stale = {key: (readiness.get(key), expected) for key, expected in required_readiness.items() if readiness.get(key) != expected}
    if stale:
        raise ContractError(f"readiness boundary changed: {stale}")
    if readiness.get("technicalDiagnosisRequiredGeometryIds") != []:
        raise ContractError("technical diagnosis remains required")

    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ContractError("reference dataset must contain exactly six geometries")
    seen: set[str] = set()
    anchors: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ContractError("reference record must be an object")
        group = record.get("groupId")
        if group not in EXPECTED_GROUPS or group in seen:
            raise ContractError(f"unexpected or duplicate group: {group}")
        seen.add(group)
        geometry = validate_geometry(group, record.get("geometry"))
        methods_raw = record.get("methodStatistics")
        if not isinstance(methods_raw, dict):
            raise ContractError(f"methodStatistics missing for {group}")
        methods = {method: validate_method(group, method, methods_raw.get(method)) for method in METHODS}
        ratio = finite(record.get("meanRatioAlisToVroom"), f"{group}.meanRatioAlisToVroom")
        fraction = finite(record.get("nodeAgreementFraction"), f"{group}.nodeAgreementFraction")
        if not 0.5 <= ratio <= 2.0:
            raise ContractError(f"integrated method ratio outside contract for {group}")
        if fraction < 0.80:
            raise ContractError(f"spectral agreement outside contract for {group}")
        origins = record.get("methodOrigins")
        if not isinstance(origins, dict) or set(origins) != set(METHODS):
            raise ContractError(f"method provenance missing for {group}")
        anchors.append({
            "groupId": group,
            "geometry": geometry,
            "methods": methods,
            "methodOrigins": origins,
            "meanRatioAlisToVroom": ratio,
            "nodeAgreementFraction": fraction,
            "role": "external-computational-validation-anchor",
            "eligibleForTraining": False,
            "observationValidationRequired": True,
        })
    if seen != EXPECTED_GROUPS:
        raise ContractError(f"geometry universe mismatch: {sorted(EXPECTED_GROUPS - seen)}")
    anchors.sort(key=lambda item: item["groupId"])
    return {
        "schemaVersion": 1,
        "stageId": "twilight-model-readiness-v1",
        "status": "REFERENCE_ANCHORS_VALIDATED",
        "anchorCount": len(anchors),
        "anchors": anchors,
        "trainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "boundary": "six audited computational anchors; not a training set and not observational validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = validate(load(args.dataset), load(args.readiness))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(output))
        print(dump(output), end="")
        return 0
    except Exception as exc:
        print(dump({"status": "REFUSED", "stageId": "twilight-model-readiness-v1", "reason": str(exc)}), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
