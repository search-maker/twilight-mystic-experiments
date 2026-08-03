#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "twilight-surrogate-v1"
FEATURES = [
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthCos",
    "relativeAzimuthSin",
    "observerElevationKm",
    "aod550",
    "albedo",
]


class SurrogateRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise SurrogateRefusal(f"expected JSON object: {path}")
    return value


def finite_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise SurrogateRefusal(f"{name} must be finite")
    return float(value)


def feature_vector(row: dict[str, Any]) -> list[float]:
    azimuth = math.radians(finite_number(row.get("relativeAzimuthDeg"), "relativeAzimuthDeg"))
    values = {
        "sunDepressionDeg": finite_number(row.get("sunDepressionDeg"), "sunDepressionDeg"),
        "targetAltitudeDeg": finite_number(row.get("targetAltitudeDeg"), "targetAltitudeDeg"),
        "relativeAzimuthCos": math.cos(azimuth),
        "relativeAzimuthSin": math.sin(azimuth),
        "observerElevationKm": finite_number(row.get("observerElevationM"), "observerElevationM") / 1000.0,
        "aod550": finite_number(row.get("aod550"), "aod550"),
        "albedo": finite_number(row.get("albedo"), "albedo"),
    }
    return [values[name] for name in FEATURES]


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[index][:] + [vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-14:
            raise SurrogateRefusal("singular regression system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    left - factor * right
                    for left, right in zip(augmented[row], augmented[column])
                ]
    return [augmented[row][-1] for row in range(size)]


def basis(vector: list[float]) -> list[float]:
    result = [1.0, *vector]
    result.extend(value * value for value in vector)
    result.extend(
        [
            vector[0] * vector[1],
            vector[0] * vector[2],
            vector[0] * vector[3],
            vector[0] * vector[5],
            vector[1] * vector[5],
            vector[4] * vector[0],
        ]
    )
    return result


def fit(rows: list[dict[str, Any]], ridge: float = 1e-6) -> dict[str, Any]:
    train = [row for row in rows if row.get("split") == "train"]
    if len(train) < 4:
        raise SurrogateRefusal("at least four training rows are required")
    raw = [feature_vector(row) for row in train]
    minima = [min(vector[index] for vector in raw) for index in range(len(FEATURES))]
    maxima = [max(vector[index] for vector in raw) for index in range(len(FEATURES))]
    scales = [
        maximum - minimum if maximum > minimum else 1.0
        for minimum, maximum in zip(minima, maxima)
    ]

    design: list[list[float]] = []
    targets: list[float] = []
    weights: list[float] = []
    normalized_train: list[list[float]] = []
    for row, vector in zip(train, raw):
        normalized = [
            (value - minimum) / scale
            for value, minimum, scale in zip(vector, minima, scales)
        ]
        normalized_train.append(normalized)
        design.append(basis(normalized))
        luminance = finite_number(row.get("photopicLuminanceCdM2"), "photopicLuminanceCdM2")
        if luminance <= 0:
            raise SurrogateRefusal("photopic luminance must be positive")
        targets.append(math.log(luminance))
        log_se = finite_number(row.get("logStandardError", 0.05), "logStandardError")
        if log_se <= 0:
            raise SurrogateRefusal("logStandardError must be positive")
        weights.append(1.0 / (log_se * log_se))

    parameter_count = len(design[0])
    normal = [[0.0] * parameter_count for _ in range(parameter_count)]
    rhs = [0.0] * parameter_count
    for row, target, weight in zip(design, targets, weights):
        for i in range(parameter_count):
            rhs[i] += weight * row[i] * target
            for j in range(parameter_count):
                normal[i][j] += weight * row[i] * row[j]
    for index in range(1, parameter_count):
        normal[index][index] += ridge
    coefficients = solve(normal, rhs)
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "modelType": "weighted-ridge-polynomial-log-luminance-v1",
        "features": FEATURES,
        "minima": minima,
        "maxima": maxima,
        "scales": scales,
        "coefficients": coefficients,
        "ridge": ridge,
        "trainingRows": len(train),
        "normalizedTrainingFeatures": normalized_train,
        "outOfDomainDistanceThreshold": 0.65,
    }


def predict(model: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    vector = feature_vector(row)
    minima = model["minima"]
    maxima = model["maxima"]
    scales = model["scales"]
    normalized = [
        (value - minimum) / scale
        for value, minimum, scale in zip(vector, minima, scales)
    ]
    outside_features = [
        FEATURES[index]
        for index, value in enumerate(vector)
        if value < minima[index] - 1e-12 or value > maxima[index] + 1e-12
    ]
    distances = [
        math.sqrt(sum((left - right) ** 2 for left, right in zip(normalized, training)))
        for training in model["normalizedTrainingFeatures"]
    ]
    nearest_distance = min(distances)
    out_of_domain = (
        bool(outside_features)
        or nearest_distance > model["outOfDomainDistanceThreshold"]
    )
    predicted_log = sum(
        coefficient * value
        for coefficient, value in zip(model["coefficients"], basis(normalized))
    )
    return {
        "predictedLogLuminance": predicted_log,
        "predictedPhotopicLuminanceCdM2": math.exp(predicted_log),
        "outOfDomain": out_of_domain,
        "outsideFeatureRanges": outside_features,
        "nearestNormalizedTrainingDistance": nearest_distance,
    }


def metrics(model: dict[str, Any], rows: list[dict[str, Any]], split: str) -> dict[str, Any]:
    selected = [row for row in rows if row.get("split") == split]
    errors: list[float] = []
    out_of_domain_count = 0
    for row in selected:
        result = predict(model, row)
        actual = finite_number(row.get("photopicLuminanceCdM2"), "photopicLuminanceCdM2")
        errors.append(result["predictedLogLuminance"] - math.log(actual))
        out_of_domain_count += int(result["outOfDomain"])
    if not selected:
        return {"split": split, "rowCount": 0, "available": False}
    mean_absolute = sum(abs(error) for error in errors) / len(errors)
    root_mean_squared = math.sqrt(sum(error * error for error in errors) / len(errors))
    maximum = max(abs(error) for error in errors)
    return {
        "split": split,
        "rowCount": len(selected),
        "available": True,
        "meanAbsoluteLogError": mean_absolute,
        "rootMeanSquaredLogError": root_mean_squared,
        "maximumAbsoluteLogError": maximum,
        "worstMultiplicativeErrorFactor": math.exp(maximum),
        "outOfDomainCount": out_of_domain_count,
    }


def train_and_evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schemaVersion") != 1 or payload.get("stageId") != STAGE_ID:
        raise SurrogateRefusal("wrong schemaVersion or stageId")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise SurrogateRefusal("rows must be an array")
    model = fit(rows, finite_number(payload.get("ridge", 1e-6), "ridge"))
    return {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "TRAINED_SYNTHETIC_OR_IMPORTED_DATA",
        "scientificExecution": False,
        "model": model,
        "validation": metrics(model, rows, "validation"),
        "withheld": metrics(model, rows, "withheld"),
        "boundary": "harness result only; a model is not accepted until withheld real MYSTIC cases satisfy a separately frozen contract",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = train_and_evaluate(load_json(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result))
        print(dump(result), end="")
        return 0
    except Exception as exc:
        print(
            dump({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}),
            end="",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
