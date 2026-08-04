#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
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
SOFT_DIAGNOSTIC_GROUP = "g01-reference-bridge"
METHODS = ("reference-vroom", "alis")
GEOMETRY_FIELDS = (
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthDeg",
    "observerElevationM",
    "aod550",
)
ALLOWED_SOURCE_STAGES = {
    "cross-geometry-held-out-confirmation-timeout-continuation-v1",
    "g01-fixed-precision-diagnosis-execution-v1",
}


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
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ContractError(f"{name} must be finite numeric")
    return float(value)


def validate_geometry(group: str, geometry: Any) -> dict[str, float]:
    if not isinstance(geometry, dict) or geometry.get("geometryId") != group:
        raise ContractError(f"geometry missing/mismatched for {group}")
    result = {
        field: finite(geometry.get(field), f"{group}.{field}")
        for field in GEOMETRY_FIELDS
    }
    if (
        not 0 <= result["sunDepressionDeg"] <= 20
        or not 0 <= result["targetAltitudeDeg"] <= 90
        or not 0 <= result["relativeAzimuthDeg"] <= 180
        or not 0 <= result["observerElevationM"] <= 5000
        or not 0 < result["aod550"] <= 1
    ):
        raise ContractError(f"geometry outside contract for {group}")
    return result


def validate_method(
    group: str,
    method: str,
    value: Any,
    *,
    maximum_rsem: float = 0.10,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"method statistics missing: {group} {method}")
    nodes = value.get("nodeMeanRadiance")
    if not isinstance(nodes, list) or len(nodes) != 15:
        raise ContractError(f"expected 15 spectral nodes: {group} {method}")
    node_values = [finite(item, f"{group}.{method}.node") for item in nodes]
    if any(item < 0 for item in node_values):
        raise ContractError(f"negative spectral node: {group} {method}")

    values = value.get("valuesCdM2")
    if isinstance(values, list) and len(values) >= 2:
        vals = [finite(item, f"{group}.{method}.value") for item in values]
        if any(item <= 0 for item in vals):
            raise ContractError(f"nonpositive block value: {group} {method}")
        block_count = len(vals)
        mean = statistics.mean(vals)
        sample_sd = statistics.stdev(vals)
        coefficient_of_variation = sample_sd / mean
        rsem = coefficient_of_variation / math.sqrt(block_count)
        supplied_mean = value.get("meanCdM2")
        if supplied_mean is not None and abs(finite(supplied_mean, "mean") - mean) > max(
            1e-15, abs(mean) * 1e-12
        ):
            raise ContractError(f"mean inconsistent with values: {group} {method}")
        supplied_count = value.get("blockCount")
        if supplied_count is not None and supplied_count != block_count:
            raise ContractError(f"blockCount inconsistent: {group} {method}")
        supplied_rsem = value.get("relativeStandardErrorOfMean")
        if supplied_rsem is not None and abs(finite(supplied_rsem, "RSEM") - rsem) > 1e-12:
            raise ContractError(f"RSEM inconsistent: {group} {method}")
    else:
        block_count = value.get("blockCount")
        mean = finite(value.get("meanCdM2"), f"{group}.{method}.mean")
        rsem = finite(value.get("relativeStandardErrorOfMean"), f"{group}.{method}.RSEM")
        vals = None
        if not isinstance(block_count, int) or block_count < 2:
            raise ContractError(f"at least two blocks required: {group} {method}")
        if mean <= 0:
            raise ContractError(f"nonpositive mean: {group} {method}")
        sample_sd_raw = value.get("sampleStandardDeviationCdM2")
        coefficient_raw = value.get("coefficientOfVariation")
        sample_sd = None if sample_sd_raw is None else finite(sample_sd_raw, "sd")
        coefficient_of_variation = (
            None if coefficient_raw is None else finite(coefficient_raw, "cv")
        )

    if not 0 <= rsem <= maximum_rsem:
        raise ContractError(
            f"RSEM exceeds anchor contract: {group} {method}: {rsem} > {maximum_rsem}"
        )
    result: dict[str, Any] = {
        "blockCount": block_count,
        "meanCdM2": mean,
        "relativeStandardErrorOfMean": rsem,
        "nodeMeanRadiance": node_values,
    }
    if vals is not None:
        result.update(
            {
                "valuesCdM2": vals,
                "sampleStandardDeviationCdM2": sample_sd,
                "coefficientOfVariation": coefficient_of_variation,
            }
        )
    return result


def validate_compatibility(group: str, ratio_raw: Any, fraction_raw: Any) -> tuple[float, float]:
    ratio = finite(ratio_raw, f"{group}.ratio")
    fraction = finite(fraction_raw, f"{group}.fraction")
    if not 0.5 <= ratio <= 2.0 or fraction < 0.80:
        raise ContractError(f"method compatibility outside contract: {group}")
    return ratio, fraction


def hard_anchor(record: dict[str, Any]) -> dict[str, Any]:
    group = record.get("groupId")
    if group not in EXPECTED_GROUPS:
        raise ContractError(f"unexpected group: {group}")
    geometry = validate_geometry(group, record.get("geometry"))
    methods_raw = record.get("methodStatistics")
    if not isinstance(methods_raw, dict):
        raise ContractError(f"method stats missing: {group}")
    methods = {
        method: validate_method(group, method, methods_raw.get(method))
        for method in METHODS
    }
    ratio, fraction = validate_compatibility(
        group, record.get("meanRatioAlisToVroom"), record.get("nodeAgreementFraction")
    )
    origins = record.get("methodOrigins")
    if not isinstance(origins, dict) or set(origins) != set(METHODS):
        raise ContractError(f"method provenance missing: {group}")
    return {
        "groupId": group,
        "geometry": geometry,
        "methods": methods,
        "methodOrigins": origins,
        "meanRatioAlisToVroom": ratio,
        "nodeAgreementFraction": fraction,
        "role": "external-computational-validation-anchor",
        "anchorStrength": "hard",
        "eligibleForTraining": False,
        "eligibleForModelAcceptance": True,
        "observationValidationRequired": True,
    }


def pilot_geometry(pilot: dict[str, Any], group: str) -> dict[str, float]:
    if pilot.get("stageId") != "cross-geometry-pilot-v1":
        raise ContractError("pilot manifest boundary changed")
    geometries = pilot.get("geometries")
    if not isinstance(geometries, list):
        raise ContractError("pilot geometries missing")
    matches = [item for item in geometries if isinstance(item, dict) and item.get("geometryId") == group]
    if len(matches) != 1:
        raise ContractError(f"expected one pilot geometry for {group}")
    return validate_geometry(group, matches[0])


def soft_diagnostic_anchor(analysis: dict[str, Any], pilot: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schemaVersion": 1,
        "stageId": "g01-fixed-precision-diagnosis-execution-v1",
        "status": "G01_FIXED_PRECISION_EXECUTION_ANALYZED",
        "classification": "G01_PERSISTENT_HIGH_VARIANCE",
        "computationalReferenceScreeningComplete": False,
        "noAutomaticAdditionalBlocks": True,
        "screeningOnly": True,
        "successDoesNotAuthorizeProduction": True,
    }
    stale = {
        key: (analysis.get(key), expected)
        for key, expected in required.items()
        if analysis.get(key) != expected
    }
    if stale:
        raise ContractError(f"soft diagnostic analysis boundary changed: {stale}")
    result = analysis.get("g01Result")
    if not isinstance(result, dict) or result.get("classification") != "G01_PERSISTENT_HIGH_VARIANCE":
        raise ContractError("g01 diagnostic result missing")
    methods_raw = result.get("methodStatistics")
    if not isinstance(methods_raw, dict):
        raise ContractError("g01 diagnostic method statistics missing")
    methods = {
        method: validate_method(SOFT_DIAGNOSTIC_GROUP, method, methods_raw.get(method))
        for method in METHODS
    }
    alis_rsem = methods["alis"]["relativeStandardErrorOfMean"]
    if not 0.08 < alis_rsem <= 0.10:
        raise ContractError(f"g01 is not the exact bounded precision near-miss: {alis_rsem}")
    ratio, fraction = validate_compatibility(
        SOFT_DIAGNOSTIC_GROUP,
        result.get("meanRatioAlisToVroom"),
        result.get("vroomPhotopicWeightFractionNodeRatioInsideInterval"),
    )
    return {
        "groupId": SOFT_DIAGNOSTIC_GROUP,
        "geometry": pilot_geometry(pilot, SOFT_DIAGNOSTIC_GROUP),
        "methods": methods,
        "methodOrigins": {
            "reference-vroom": "frozen-final-convergence-reference",
            "alis": "eight-independent-held-out-blocks-final-precision-endpoint",
        },
        "meanRatioAlisToVroom": ratio,
        "nodeAgreementFraction": fraction,
        "sourceClassification": "G01_PERSISTENT_HIGH_VARIANCE",
        "failedAcceptanceGate": "alis-relative-standard-error-of-mean<=0.08",
        "role": "external-computational-diagnostic-anchor",
        "anchorStrength": "soft-diagnostic",
        "eligibleForTraining": False,
        "eligibleForModelAcceptance": False,
        "observationValidationRequired": True,
    }


def complete_mode(dataset: dict[str, Any], readiness: dict[str, Any]) -> list[dict[str, Any]]:
    required = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_COMPLETE",
        "computationalReferenceScreeningComplete": True,
        "acceptedReferenceGeometryCount": 6,
        "heldOutConfirmationFailureCount": 0,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
    }
    stale = {
        key: (readiness.get(key), expected)
        for key, expected in required.items()
        if readiness.get(key) != expected
    }
    if stale or readiness.get("technicalDiagnosisRequiredGeometryIds") != []:
        raise ContractError(f"readiness boundary changed: {stale}")
    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != 6:
        raise ContractError("complete reference dataset must contain exactly six geometries")
    anchors = [hard_anchor(record) for record in records if isinstance(record, dict)]
    seen = {anchor["groupId"] for anchor in anchors}
    if len(anchors) != 6 or seen != EXPECTED_GROUPS:
        raise ContractError(f"geometry universe mismatch: {sorted(EXPECTED_GROUPS - seen)}")
    return anchors


def partial_mode(
    dataset: dict[str, Any],
    readiness: dict[str, Any],
    analysis: dict[str, Any] | None,
    pilot: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if analysis is None or pilot is None:
        raise ContractError("partial five-plus-one contract requires analysis and pilot manifest")
    required = {
        "schemaVersion": 1,
        "status": "COMPUTATIONAL_REFERENCE_SCREENING_REQUIRES_DIAGNOSIS",
        "computationalReferenceScreeningComplete": False,
        "acceptedReferenceGeometryCount": 5,
        "heldOutConfirmationFailureCount": 1,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "surrogateTrainingAutomaticallyAuthorized": False,
        "noAutomaticAdditionalBlocks": True,
    }
    stale = {
        key: (readiness.get(key), expected)
        for key, expected in required.items()
        if readiness.get(key) != expected
    }
    if stale or readiness.get("technicalDiagnosisRequiredGeometryIds") != [SOFT_DIAGNOSTIC_GROUP]:
        raise ContractError(f"partial readiness boundary changed: {stale}")
    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != 5:
        raise ContractError("partial reference dataset must contain exactly five hard records")
    anchors = [hard_anchor(record) for record in records if isinstance(record, dict)]
    seen = {anchor["groupId"] for anchor in anchors}
    expected_hard = EXPECTED_GROUPS - {SOFT_DIAGNOSTIC_GROUP}
    if len(anchors) != 5 or seen != expected_hard:
        raise ContractError(f"hard anchor universe mismatch: {sorted(expected_hard - seen)}")
    anchors.append(soft_diagnostic_anchor(analysis, pilot))
    return anchors


def validate(
    dataset: dict[str, Any],
    readiness: dict[str, Any],
    analysis: dict[str, Any] | None = None,
    pilot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        dataset.get("schemaVersion") != 1
        or dataset.get("screeningOnly") is not True
        or dataset.get("observationValidationRequired") is not True
    ):
        raise ContractError("dataset boundary changed")
    if dataset.get("sourceStageId") not in ALLOWED_SOURCE_STAGES:
        raise ContractError(f"unsupported source stage: {dataset.get('sourceStageId')}")

    status = dataset.get("status")
    if status == "AUDITED_COMPUTATIONAL_REFERENCE_DATASET":
        anchors = complete_mode(dataset, readiness)
    elif status == "INCOMPLETE_COMPUTATIONAL_REFERENCE_DATASET":
        anchors = partial_mode(dataset, readiness, analysis, pilot)
    else:
        raise ContractError(f"unsupported dataset status: {status}")

    anchors.sort(key=lambda item: item["groupId"])
    hard_ids = [item["groupId"] for item in anchors if item["anchorStrength"] == "hard"]
    soft_ids = [
        item["groupId"] for item in anchors if item["anchorStrength"] == "soft-diagnostic"
    ]
    if set(hard_ids) | set(soft_ids) != EXPECTED_GROUPS or set(hard_ids) & set(soft_ids):
        raise ContractError("anchor partition does not cover the frozen six-point universe")
    return {
        "schemaVersion": 1,
        "stageId": "twilight-model-readiness-v1",
        "status": "REFERENCE_ANCHORS_VALIDATED",
        "sourceStageId": dataset["sourceStageId"],
        "anchorCount": 6,
        "hardValidationAnchorCount": len(hard_ids),
        "softDiagnosticAnchorCount": len(soft_ids),
        "hardValidationAnchorIds": hard_ids,
        "softDiagnosticAnchorIds": soft_ids,
        "anchors": anchors,
        "trainingAutomaticallyAuthorized": False,
        "productionModelReady": False,
        "observationValidationRequired": True,
        "boundary": (
            "all six computational points remain excluded from fitting; hard anchors may gate "
            "computational model acceptance, while soft diagnostic anchors are report-only and "
            "cannot compensate for failed precision or observational validation"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--analysis", type=Path)
    parser.add_argument("--source-pilot-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(
            load(args.dataset),
            load(args.readiness),
            None if args.analysis is None else load(args.analysis),
            None if args.source_pilot_manifest is None else load(args.source_pilot_manifest),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump(
                {
                    "status": "REFUSED",
                    "stageId": "twilight-model-readiness-v1",
                    "reason": str(exc),
                }
            ),
            file=sys.stderr,
            end="",
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
