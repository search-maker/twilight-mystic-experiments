#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

FEATURES = (
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthDeg",
    "observerElevationM",
    "aod550",
)
EXPECTED_PROTOCOL_STAGE = "surrogate-training-v2-exploratory-internal-holdout-protocol-v1"
EXPECTED_PROTOCOL_STATUS = "FROZEN_BEFORE_INTERNAL_HOLDOUT_OPENING"
EXPECTED_DATASET_STAGE = "surrogate-training-v2-exploratory-internal-holdout-dataset-v1"
EXPECTED_DATASET_STATUS = "INTERNAL_HOLDOUT_VALUES_OPENED_EXACTLY_ONCE"
EXPECTED_MODEL_RAW_SHA256 = "ce575bcd2c40acfa4b1ade48fd70d41cd58cb7d632815db33def079ab172a0fa"
EXPECTED_MODEL_HASH = "381323604143498619cec494d221747d0d32f37a7e7cbb811b0154b6b4f68848"
EXPECTED_TRAINING_DATASET_SHA256 = "eb4a5e13bb31d2eec32204574547847cb03c0723cd5cab5538ff2e12b468ded1"
EXPECTED_HOLDOUT_IDS = tuple(f"train-{index:04d}" for index in range(5, 46, 5))
FACTOR_TWO_LOG_ERROR = math.log(2.0)


class HoldoutRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HoldoutRefusal(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise HoldoutRefusal(f"expected object: {path}")
    return value


def _validate_self_hash(value: dict[str, Any], field: str, label: str) -> None:
    supplied = value.get(field)
    payload = {key: item for key, item in value.items() if key != field}
    if supplied != canonical_sha256(payload):
        raise HoldoutRefusal(f"{label} self-hash changed")


def validate_protocol(protocol: dict[str, Any]) -> None:
    _validate_self_hash(protocol, "protocolSha256", "holdout protocol")
    expected = {
        "schemaVersion": 1,
        "stageId": EXPECTED_PROTOCOL_STAGE,
        "status": EXPECTED_PROTOCOL_STATUS,
        "sourcePr": 99,
        "sourceHeadSha": "2bd645464e05c4d9533c499a080ca6db8cd190a9",
        "sourceModelArtifactRawSha256": EXPECTED_MODEL_RAW_SHA256,
        "sourceModelHash": EXPECTED_MODEL_HASH,
        "sourceTrainingDatasetSha256": EXPECTED_TRAINING_DATASET_SHA256,
        "holdoutGeometryIds": list(EXPECTED_HOLDOUT_IDS),
        "targetTransformation": "natural-log-positive-photopic-luminance",
        "metrics": [
            "mean-absolute-log-error",
            "maximum-absolute-log-error",
            "count-within-factor-two",
            "out-of-domain-count",
        ],
    }
    stale = {
        key: (protocol.get(key), wanted)
        for key, wanted in expected.items()
        if protocol.get(key) != wanted
    }
    if stale:
        raise HoldoutRefusal(f"holdout protocol identity changed: {stale}")

    criteria = protocol.get("acceptanceCriteria")
    if not isinstance(criteria, dict):
        raise HoldoutRefusal("acceptance criteria missing")
    exact_criteria = {
        "meanAbsoluteLogErrorMaximum": 0.4151818512948229,
        "maximumAbsoluteLogErrorMaximum": 1.5248898203500163,
        "minimumWithinFactorTwoCount": 7,
        "outOfDomainMaximumCount": 0,
        "nonFiniteOrNonPositivePredictionMaximumCount": 0,
    }
    if criteria != exact_criteria:
        raise HoldoutRefusal("acceptance criteria changed after freeze")

    derivation = protocol.get("thresholdDerivation")
    if derivation != {
        "selectedTrainingWeightedMeanAbsoluteLogError": 0.27678790086321525,
        "selectedTrainingMaximumAbsoluteLogError": 1.0165932135666775,
        "relativeMultiplier": 1.5,
        "factorTwoAbsoluteLogError": FACTOR_TWO_LOG_ERROR,
    }:
        raise HoldoutRefusal("threshold derivation changed")

    opening = protocol.get("openingRules")
    if opening != {
        "modelFrozenBeforeOpening": True,
        "openExactlyOnce": True,
        "selectionFromHoldoutForbidden": True,
        "thresholdTuningFromHoldoutForbidden": True,
        "featureOrPreprocessingChangeAfterOpeningForbidden": True,
        "failedHoldoutMustRemainImmutable": True,
    }:
        raise HoldoutRefusal("one-time opening rules changed")

    boundary = protocol.get("claimBoundary")
    if boundary != {
        "scientificEligibilityClaimed": False,
        "observationallyValidated": False,
        "tier2Authorized": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
    }:
        raise HoldoutRefusal("claim boundary changed")


def validate_model(model: dict[str, Any], model_path: Path) -> None:
    if raw_sha256(model_path) != EXPECTED_MODEL_RAW_SHA256:
        raise HoldoutRefusal("frozen model artifact raw hash changed")
    supplied_hash = model.get("modelHash")
    payload = {key: item for key, item in model.items() if key != "modelHash"}
    if supplied_hash != canonical_sha256(payload) or supplied_hash != EXPECTED_MODEL_HASH:
        raise HoldoutRefusal("frozen model self-hash changed")
    expected = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-exploratory-noisy-label-model-v1",
        "status": "EXPLORATORY_MODEL_FROZEN_TRAINING_ONLY_NOT_SCIENTIFICALLY_VALIDATED",
        "trainingDatasetSha256": EXPECTED_TRAINING_DATASET_SHA256,
        "featureList": list(FEATURES),
        "targetTransformation": "natural-log-positive-photopic-luminance",
        "candidateId": "weighted-fixed-basis-log-ridge",
        "selectedRidge": 0.0001,
        "internalHoldoutGeometryIdsExcludedAndUnopened": list(EXPECTED_HOLDOUT_IDS),
        "holdoutRecordCount": 0,
        "modelFrozen": True,
        "modelRestorationVerified": True,
        "internalHoldoutOpened": False,
        "holdoutValuesRead": False,
        "hardAnchorsOpened": False,
        "softDiagnosticsOpened": False,
        "observationallyValidated": False,
        "scientificallyEligibleModelClaimed": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
        "tier2Authorized": False,
    }
    stale = {
        key: (model.get(key), wanted)
        for key, wanted in expected.items()
        if model.get(key) != wanted
    }
    if stale:
        raise HoldoutRefusal(f"frozen model boundary changed: {stale}")
    normalizer = model.get("normalizationConstants")
    state = model.get("modelState")
    if not isinstance(normalizer, dict) or not isinstance(state, dict):
        raise HoldoutRefusal("frozen model state missing")
    lows = normalizer.get("minimums")
    highs = normalizer.get("maximums")
    coefficients = state.get("coefficients")
    if (
        not isinstance(lows, list)
        or not isinstance(highs, list)
        or len(lows) != len(FEATURES)
        or len(highs) != len(FEATURES)
        or not isinstance(coefficients, list)
        or len(coefficients) != 10
    ):
        raise HoldoutRefusal("frozen model dimensions changed")
    numeric = [*lows, *highs, *coefficients]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in numeric):
        raise HoldoutRefusal("frozen model contains non-finite state")
    if any(float(high) <= float(low) for low, high in zip(lows, highs, strict=True)):
        raise HoldoutRefusal("frozen model normalization range changed")


def validate_holdout_dataset(dataset: dict[str, Any], protocol: dict[str, Any]) -> list[dict[str, Any]]:
    _validate_self_hash(dataset, "holdoutDatasetSha256", "holdout dataset")
    expected = {
        "schemaVersion": 1,
        "stageId": EXPECTED_DATASET_STAGE,
        "status": EXPECTED_DATASET_STATUS,
        "protocolSha256": protocol["protocolSha256"],
        "sourceModelHash": EXPECTED_MODEL_HASH,
        "sourceTrainingDatasetSha256": EXPECTED_TRAINING_DATASET_SHA256,
        "holdoutGeometryIds": list(EXPECTED_HOLDOUT_IDS),
        "holdoutRecordCount": 9,
        "holdoutValuesIncluded": True,
        "internalHoldoutOpenedExactlyOnce": True,
        "selectionFromHoldoutForbidden": True,
        "thresholdTuningFromHoldoutForbidden": True,
    }
    stale = {
        key: (dataset.get(key), wanted)
        for key, wanted in expected.items()
        if dataset.get(key) != wanted
    }
    if stale:
        raise HoldoutRefusal(f"holdout dataset identity changed: {stale}")
    records = dataset.get("records")
    if not isinstance(records, list) or len(records) != len(EXPECTED_HOLDOUT_IDS):
        raise HoldoutRefusal("holdout dataset must contain exactly nine records")
    ids = [record.get("geometryId") for record in records if isinstance(record, dict)]
    if ids != list(EXPECTED_HOLDOUT_IDS) or len(set(ids)) != len(EXPECTED_HOLDOUT_IDS):
        raise HoldoutRefusal("holdout geometry order or identities changed")
    for record in records:
        if record.get("role") != "internal-holdout":
            raise HoldoutRefusal("holdout dataset contains a non-holdout record")
        geometry = record.get("geometry")
        statistics = record.get("statistics")
        if not isinstance(geometry, dict) or not isinstance(statistics, dict):
            raise HoldoutRefusal(f"holdout record incomplete: {record.get('geometryId')}")
        features = [geometry.get(key) for key in FEATURES]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in features):
            raise HoldoutRefusal(f"holdout feature invalid: {record.get('geometryId')}")
        target = statistics.get("meanCdM2")
        if isinstance(target, bool) or not isinstance(target, (int, float)) or not math.isfinite(float(target)) or float(target) <= 0:
            raise HoldoutRefusal(f"holdout target invalid: {record.get('geometryId')}")
    return records


def _basis(row: list[float]) -> list[float]:
    s, a, z, e, d = row
    return [1.0, s, a, z, e, d, s * s, a * a, s * a, s * d]


def predict(model: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    geometry = record["geometry"]
    lows = [float(value) for value in model["normalizationConstants"]["minimums"]]
    highs = [float(value) for value in model["normalizationConstants"]["maximums"]]
    raw = [float(geometry[key]) for key in FEATURES]
    normalized = [
        (value - low) / (high - low)
        for value, low, high in zip(raw, lows, highs, strict=True)
    ]
    out_of_domain = any(value < 0.0 or value > 1.0 for value in normalized)
    coefficients = [float(value) for value in model["modelState"]["coefficients"]]
    log_prediction = sum(
        coefficient * value
        for coefficient, value in zip(coefficients, _basis(normalized), strict=True)
    )
    prediction = math.exp(log_prediction)
    if not math.isfinite(prediction) or prediction <= 0:
        return {
            "logPrediction": log_prediction,
            "predictionCdM2": prediction,
            "outOfDomain": out_of_domain,
            "validPositivePrediction": False,
        }
    return {
        "logPrediction": log_prediction,
        "predictionCdM2": prediction,
        "outOfDomain": out_of_domain,
        "validPositivePrediction": True,
    }


def evaluate(
    *,
    model_path: Path,
    protocol_path: Path,
    holdout_dataset_path: Path,
) -> dict[str, Any]:
    protocol = load_object(protocol_path)
    model = load_object(model_path)
    holdout_dataset = load_object(holdout_dataset_path)
    validate_protocol(protocol)
    validate_model(model, model_path)
    records = validate_holdout_dataset(holdout_dataset, protocol)

    rows: list[dict[str, Any]] = []
    non_positive_or_non_finite = 0
    for record in records:
        prediction = predict(model, record)
        target_value = float(record["statistics"]["meanCdM2"])
        valid = prediction["validPositivePrediction"]
        if not valid:
            non_positive_or_non_finite += 1
            absolute_log_error = math.inf
            factor_error = math.inf
        else:
            absolute_log_error = abs(float(prediction["logPrediction"]) - math.log(target_value))
            factor_error = math.exp(absolute_log_error)
        rows.append(
            {
                "geometryId": record["geometryId"],
                "targetCdM2": target_value,
                **prediction,
                "absoluteLogError": absolute_log_error,
                "factorError": factor_error,
                "withinFactorTwo": valid and absolute_log_error <= FACTOR_TWO_LOG_ERROR,
            }
        )

    finite_errors = [float(row["absoluteLogError"]) for row in rows if math.isfinite(float(row["absoluteLogError"]))]
    if len(finite_errors) != len(rows):
        mean_error = math.inf
        maximum_error = math.inf
    else:
        mean_error = sum(finite_errors) / len(finite_errors)
        maximum_error = max(finite_errors)
    within_factor_two = sum(bool(row["withinFactorTwo"]) for row in rows)
    out_of_domain_count = sum(bool(row["outOfDomain"]) for row in rows)

    criteria = protocol["acceptanceCriteria"]
    checks = {
        "meanAbsoluteLogError": mean_error <= float(criteria["meanAbsoluteLogErrorMaximum"]),
        "maximumAbsoluteLogError": maximum_error <= float(criteria["maximumAbsoluteLogErrorMaximum"]),
        "withinFactorTwoCount": within_factor_two >= int(criteria["minimumWithinFactorTwoCount"]),
        "outOfDomainCount": out_of_domain_count <= int(criteria["outOfDomainMaximumCount"]),
        "nonFiniteOrNonPositivePredictionCount": non_positive_or_non_finite
        <= int(criteria["nonFiniteOrNonPositivePredictionMaximumCount"]),
    }
    passed = all(checks.values())
    result = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-exploratory-internal-holdout-result-v1",
        "status": "INTERNAL_HOLDOUT_GENERALIZATION_PASSED" if passed else "INTERNAL_HOLDOUT_GENERALIZATION_FAILED",
        "protocolSha256": protocol["protocolSha256"],
        "modelArtifactRawSha256": raw_sha256(model_path),
        "modelHash": model["modelHash"],
        "trainingDatasetSha256": model["trainingDatasetSha256"],
        "holdoutDatasetRawSha256": raw_sha256(holdout_dataset_path),
        "holdoutDatasetSha256": holdout_dataset["holdoutDatasetSha256"],
        "holdoutGeometryIds": list(EXPECTED_HOLDOUT_IDS),
        "count": len(rows),
        "meanAbsoluteLogError": mean_error,
        "maximumAbsoluteLogError": maximum_error,
        "withinFactorTwoCount": within_factor_two,
        "outOfDomainCount": out_of_domain_count,
        "nonFiniteOrNonPositivePredictionCount": non_positive_or_non_finite,
        "acceptanceCriteria": criteria,
        "acceptanceChecks": checks,
        "generalizationValidated": passed,
        "selectionFromHoldoutForbidden": True,
        "thresholdTuningFromHoldoutForbidden": True,
        "modelOrPreprocessingChangeAfterOpeningForbidden": True,
        "internalHoldoutOpenedExactlyOnce": True,
        "scientificEligibilityClaimed": False,
        "observationallyValidated": False,
        "hardAnchorsOpened": False,
        "softDiagnosticsOpened": False,
        "tier2Authorized": False,
        "productionModelReady": False,
        "productionPromotionAuthorized": False,
        "rows": rows,
    }
    result["resultSha256"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--holdout-dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(
            model_path=args.model_artifact,
            protocol_path=args.protocol,
            holdout_dataset_path=args.holdout_dataset,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding="utf-8", newline="\n")
        return 0 if result["generalizationValidated"] else 3
    except Exception as exc:
        print(dump({"status": "REFUSED", "reason": str(exc)}), end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
