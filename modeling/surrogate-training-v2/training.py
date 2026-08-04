#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

FEATURES = ("sunDepressionDeg", "targetAltitudeDeg", "relativeAzimuthDeg", "observerElevationM", "aod550")
SEED = 240804


class TrainingRefusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def target(record: dict[str, Any]) -> float:
    value = float(record["statistics"]["meanCdM2"])
    if not math.isfinite(value) or value <= 0:
        raise TrainingRefusal("target must be positive and finite")
    return math.log(value)


def feature_vector(record: dict[str, Any]) -> list[float]:
    geometry = record["geometry"]
    values = [float(geometry[key]) for key in FEATURES]
    if any(not math.isfinite(value) for value in values):
        raise TrainingRefusal("features must be finite")
    return values


def normalizer(records: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    rows = [feature_vector(item) for item in records]
    lows = [min(row[i] for row in rows) for i in range(len(FEATURES))]
    highs = [max(row[i] for row in rows) for i in range(len(FEATURES))]
    if any(high <= low for low, high in zip(lows, highs, strict=True)):
        raise TrainingRefusal("constant feature range")
    return lows, highs


def normalize(row: list[float], lows: list[float], highs: list[float]) -> list[float]:
    return [(value - low) / (high - low) for value, low, high in zip(row, lows, highs, strict=True)]


def distance(left: list[float], right: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    augmented = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-14:
            raise TrainingRefusal("singular candidate fit")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        scale = augmented[col][col]
        augmented[col] = [value / scale for value in augmented[col]]
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[col], strict=True)]
    return [augmented[i][-1] for i in range(n)]


def basis(row: list[float]) -> list[float]:
    s, a, z, e, d = row
    return [1.0, s, a, z, e, d, s * s, a * a, s * a, s * d]


@dataclass
class Model:
    candidate_id: str
    hyperparameters: dict[str, Any]
    lows: list[float]
    highs: list[float]
    state: dict[str, Any]
    residual_rmse: float

    def predict(self, record: dict[str, Any]) -> dict[str, Any]:
        raw = feature_vector(record)
        row = normalize(raw, self.lows, self.highs)
        outside = any(value < 0 or value > 1 for value in row)
        if self.candidate_id == "transparent-log-mean-baseline":
            log_value = float(self.state["mean"])
            nearest = min(distance(row, item) for item in self.state["rows"])
            uncertainty = self.residual_rmse
        elif self.candidate_id == "fixed-basis-log-ridge":
            log_value = sum(weight * value for weight, value in zip(self.state["coefficients"], basis(row), strict=True))
            nearest = min(distance(row, item) for item in self.state["rows"])
            uncertainty = self.residual_rmse + 0.10 * nearest
        else:
            ranked = sorted((distance(row, item[0]), item[1], item[2]) for item in self.state["rows"])
            selected = ranked[: int(self.hyperparameters["neighbors"])]
            if selected[0][0] < 1e-14:
                log_value = selected[0][2]
                uncertainty = self.residual_rmse
            else:
                weights = [1 / max(item[0], 1e-12) ** float(self.hyperparameters["power"]) for item in selected]
                total = sum(weights)
                log_value = sum(weight * item[2] for weight, item in zip(weights, selected, strict=True)) / total
                spread = sum(weight * (item[2] - log_value) ** 2 for weight, item in zip(weights, selected, strict=True)) / total
                uncertainty = math.sqrt(max(spread, 0.0)) + 0.10 * selected[0][0]
            nearest = selected[0][0]
        return {"logPrediction": log_value, "predictionCdM2": math.exp(log_value), "uncertaintyLog": uncertainty, "nearestTrainingDistance": nearest, "outOfDomain": outside or nearest > 0.80}


def fit(candidate_id: str, params: dict[str, Any], records: list[dict[str, Any]]) -> Model:
    lows, highs = normalizer(records)
    rows = [normalize(feature_vector(item), lows, highs) for item in records]
    ys = [target(item) for item in records]
    if candidate_id == "transparent-log-mean-baseline":
        mean = sum(ys) / len(ys)
        predictions = [mean] * len(ys)
        state = {"mean": mean, "rows": rows}
    elif candidate_id == "fixed-basis-log-ridge":
        design = [basis(row) for row in rows]
        size = len(design[0])
        ridge = float(params["ridge"])
        matrix = [[sum(row[i] * row[j] for row in design) + (ridge if i == j and i else 0.0) for j in range(size)] for i in range(size)]
        vector = [sum(row[i] * y for row, y in zip(design, ys, strict=True)) for i in range(size)]
        coefficients = solve(matrix, vector)
        predictions = [sum(weight * value for weight, value in zip(coefficients, row, strict=True)) for row in design]
        state = {"coefficients": coefficients, "rows": rows}
    elif candidate_id == "local-log-idw":
        predictions = []
        for index, row in enumerate(rows):
            others = sorted((distance(row, candidate), j, ys[j]) for j, candidate in enumerate(rows) if j != index)
            selected = others[: min(int(params["neighbors"]), len(others))]
            weights = [1 / max(item[0], 1e-12) ** float(params["power"]) for item in selected]
            predictions.append(sum(weight * item[2] for weight, item in zip(weights, selected, strict=True)) / sum(weights))
        state = {"rows": [(row, records[i]["geometryId"], ys[i]) for i, row in enumerate(rows)]}
    else:
        raise TrainingRefusal(f"unknown candidate: {candidate_id}")
    rmse = math.sqrt(sum((prediction - truth) ** 2 for prediction, truth in zip(predictions, ys, strict=True)) / len(ys))
    return Model(candidate_id, dict(params), lows, highs, state, rmse)


def evaluate(model: Model, records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        prediction = model.predict(record)
        error = abs(prediction["logPrediction"] - target(record))
        rows.append({"geometryId": record["geometryId"], "absoluteLogError": error, **prediction})
    return {"count": len(rows), "meanAbsoluteLogError": sum(item["absoluteLogError"] for item in rows) / len(rows), "maximumAbsoluteLogError": max(item["absoluteLogError"] for item in rows), "rows": rows}


def cross_validate(protocol: dict[str, Any], training: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(training) < 10:
        raise TrainingRefusal("fewer than ten training geometries")
    ordered = sorted(training, key=lambda item: item["geometryId"])
    results = []
    for candidate in protocol["candidates"]:
        for params in candidate["hyperparameters"]:
            fold_rows = []
            for fold in range(5):
                validation = [item for index, item in enumerate(ordered) if index % 5 == fold]
                fitting = [item for index, item in enumerate(ordered) if index % 5 != fold]
                fold_rows.extend(evaluate(fit(candidate["candidateId"], params, fitting), validation)["rows"])
            results.append({"candidateId": candidate["candidateId"], "family": candidate["family"], "complexityRank": candidate["complexityRank"], "hyperparameters": params, "meanAbsoluteLogError": sum(item["absoluteLogError"] for item in fold_rows) / len(fold_rows), "maximumAbsoluteLogError": max(item["absoluteLogError"] for item in fold_rows)})
    selected = min(results, key=lambda item: (round(item["meanAbsoluteLogError"], 12), round(item["maximumAbsoluteLogError"], 12), item["complexityRank"], item["candidateId"], dump(item["hyperparameters"])))
    return selected, results


def freeze_artifact(protocol: dict[str, Any], partitioned: Any, source_code_hashes: dict[str, str]) -> tuple[Model, dict[str, Any]]:
    selected, cv = cross_validate(protocol, list(partitioned.training))
    model = fit(selected["candidateId"], selected["hyperparameters"], list(partitioned.training))
    artifact = {
        "schemaVersion": 1,
        "stageId": "surrogate-training-v2-model-artifact-v1",
        "status": "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT",
        "sourceDatasetHash": partitioned.source_dataset_hash,
        "sourceCodeHashes": source_code_hashes,
        "exactMainSha": partitioned.exact_main_sha,
        "featureList": list(FEATURES),
        "transformations": {"target": "natural-log", "basis": protocol["candidates"][[item["candidateId"] for item in protocol["candidates"]].index(selected["candidateId"])]["basis"]},
        "normalizationConstants": {"minimums": model.lows, "maximums": model.highs},
        "modelFamily": selected["family"],
        "candidateId": selected["candidateId"],
        "hyperparameters": selected["hyperparameters"],
        "trainingIds": sorted(item["geometryId"] for item in partitioned.training),
        "excludedIds": list(partitioned.excluded_ids),
        "holdoutIds": sorted(item["geometryId"] for item in partitioned.internal_holdout),
        "anchorIds": sorted(item["geometryId"] for item in partitioned.hard_anchors),
        "softDiagnosticIds": sorted(item["geometryId"] for item in partitioned.soft_diagnostics),
        "uncertaintyMethod": next(item["uncertaintyRule"] for item in protocol["candidates"] if item["candidateId"] == selected["candidateId"]),
        "outOfDomainRule": next(item["outOfDomainRule"] for item in protocol["candidates"] if item["candidateId"] == selected["candidateId"]),
        "softwareVersions": {"python": sys.version, "platform": platform.platform()},
        "deterministicSeed": SEED,
        "trainingCrossValidation": cv,
        "selectedCrossValidation": selected,
        "internalHoldoutOpened": False,
        "hardAnchorsOpened": False,
        "productionBoundary": {"productionModelReady": False, "productionPromotionAuthorized": False, "observationalValidationRequired": True}
    }
    artifact["generatedModelHash"] = sha256_text(dump(artifact))
    return model, artifact


def open_internal_holdout_once(model: Model, artifact: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    if artifact.get("status") != "MODEL_FROZEN_BEFORE_INTERNAL_HOLDOUT" or artifact.get("internalHoldoutOpened") is not False:
        raise TrainingRefusal("holdout opened before freeze or more than once")
    result = evaluate(model, records)
    return {"stageId": "surrogate-training-v2-internal-holdout-v1", "modelHash": artifact["generatedModelHash"], "selectionForbidden": True, "thresholdTuningForbidden": True, **result}


def evaluate_external(model: Model, artifact: dict[str, Any], hard: list[dict[str, Any]], soft: list[dict[str, Any]]) -> dict[str, Any]:
    hard_rows = []
    for item in hard:
        record = {"geometryId": item["geometryId"], "geometry": item["geometry"], "statistics": {"meanCdM2": item["meanCdM2"]}}
        hard_rows.append(evaluate(model, [record])["rows"][0])
    soft_rows = []
    for item in soft:
        record = {"geometryId": item["geometryId"], "geometry": item["geometry"], "statistics": {"meanCdM2": item["meanCdM2"]}}
        soft_rows.append(evaluate(model, [record])["rows"][0])
    return {"stageId": "surrogate-training-v2-external-evaluation-v1", "modelHash": artifact["generatedModelHash"], "hardAnchors": hard_rows, "softDiagnostics": soft_rows, "softDiagnosticsReportOnly": True, "softDiagnosticCannotAlonePassOrFail": True, "productionPromotionAuthorized": False}
