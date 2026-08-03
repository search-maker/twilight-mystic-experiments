#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

FEATURES = (
    "sunDepressionDeg",
    "targetAltitudeDeg",
    "relativeAzimuthDeg",
    "aod550",
    "observerElevationM",
)

DEFAULT_DOMAIN = {
    "sunDepressionDeg": (3.0, 18.0),
    "targetAltitudeDeg": (5.0, 75.0),
    "relativeAzimuthDeg": (0.0, 180.0),
    "aod550": (0.02, 0.50),
    "observerElevationM": (0.0, 3000.0),
}

# Frozen sensitivity multipliers. They prevent a numerically large coordinate,
# such as observer elevation in metres, from dominating the distance metric.
DEFAULT_DISTANCE_WEIGHTS = {
    "sunDepressionDeg": 2.0,
    "targetAltitudeDeg": 1.2,
    "relativeAzimuthDeg": 0.7,
    "aod550": 1.5,
    "observerElevationM": 0.35,
}


class SurrogateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Prediction:
    value: float
    log_value: float
    uncertainty_log: float
    nearest_distance: float
    out_of_domain: bool
    neighbor_ids: tuple[str, ...]


def dump_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def validate_point(point: dict[str, Any], domain: dict[str, tuple[float, float]] = DEFAULT_DOMAIN) -> None:
    for feature in FEATURES:
        value = point.get(feature)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise SurrogateError(f"{feature} must be finite")
        low, high = domain[feature]
        if float(value) < low or float(value) > high:
            raise SurrogateError(f"{feature} outside declared domain")


def validate_record(record: dict[str, Any], require_target: bool = True) -> None:
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id:
        raise SurrogateError("record id must be a non-empty string")
    validate_point(record)
    if require_target:
        target = record.get("targetRadiance")
        if not isinstance(target, (int, float)) or isinstance(target, bool) or not math.isfinite(float(target)) or target <= 0:
            raise SurrogateError("targetRadiance must be positive and finite")
        sigma = record.get("targetSigma", 0.0)
        if not isinstance(sigma, (int, float)) or isinstance(sigma, bool) or not math.isfinite(float(sigma)) or sigma < 0:
            raise SurrogateError("targetSigma must be finite and non-negative")


def normalized_vector(
    point: dict[str, Any],
    domain: dict[str, tuple[float, float]] = DEFAULT_DOMAIN,
    weights: dict[str, float] = DEFAULT_DISTANCE_WEIGHTS,
) -> tuple[float, ...]:
    validate_point(point, domain)
    values: list[float] = []
    for feature in FEATURES:
        low, high = domain[feature]
        span = high - low
        if span <= 0:
            raise SurrogateError(f"invalid domain span for {feature}")
        weight = weights.get(feature)
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise SurrogateError(f"invalid distance weight for {feature}")
        values.append(((float(point[feature]) - low) / span) * float(weight))
    return tuple(values)


def euclidean(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right, strict=True)))


class LogIdwSurrogate:
    def __init__(
        self,
        records: Iterable[dict[str, Any]],
        *,
        neighbors: int = 8,
        distance_power: float = 2.0,
        ood_distance: float = 0.62,
        domain: dict[str, tuple[float, float]] = DEFAULT_DOMAIN,
        weights: dict[str, float] = DEFAULT_DISTANCE_WEIGHTS,
    ) -> None:
        self.domain = domain
        self.weights = weights
        self.neighbors = int(neighbors)
        self.distance_power = float(distance_power)
        self.ood_distance = float(ood_distance)
        if self.neighbors < 2:
            raise SurrogateError("neighbors must be at least two")
        if self.distance_power <= 0 or self.ood_distance <= 0:
            raise SurrogateError("distance parameters must be positive")
        prepared: list[tuple[dict[str, Any], tuple[float, ...], float, float]] = []
        ids: set[str] = set()
        for record in records:
            validate_record(record)
            if record["id"] in ids:
                raise SurrogateError(f"duplicate training id: {record['id']}")
            ids.add(record["id"])
            log_value = math.log(float(record["targetRadiance"]))
            relative_sigma = float(record.get("targetSigma", 0.0)) / float(record["targetRadiance"])
            prepared.append((record, normalized_vector(record, domain, weights), log_value, relative_sigma))
        if len(prepared) < self.neighbors:
            raise SurrogateError("training set smaller than neighbors")
        self.prepared = prepared

    def predict(self, point: dict[str, Any]) -> Prediction:
        vector = normalized_vector(point, self.domain, self.weights)
        ranked = sorted(
            ((euclidean(vector, train_vector), record, log_value, relative_sigma)
             for record, train_vector, log_value, relative_sigma in self.prepared),
            key=lambda item: (item[0], item[1]["id"]),
        )
        nearest_distance = ranked[0][0]
        selected = ranked[: self.neighbors]
        if nearest_distance <= 1e-14:
            distance, record, log_value, relative_sigma = selected[0]
            return Prediction(
                value=math.exp(log_value),
                log_value=log_value,
                uncertainty_log=max(relative_sigma, 1e-9),
                nearest_distance=distance,
                out_of_domain=False,
                neighbor_ids=(record["id"],),
            )
        raw_weights = [1.0 / max(distance, 1e-12) ** self.distance_power for distance, *_ in selected]
        total_weight = sum(raw_weights)
        normalized_weights = [weight / total_weight for weight in raw_weights]
        log_prediction = sum(weight * item[2] for weight, item in zip(normalized_weights, selected, strict=True))
        local_variance = sum(
            weight * (item[2] - log_prediction) ** 2
            for weight, item in zip(normalized_weights, selected, strict=True)
        )
        measurement_variance = sum(
            weight * item[3] ** 2 for weight, item in zip(normalized_weights, selected, strict=True)
        )
        distance_penalty = 0.08 * nearest_distance
        uncertainty = math.sqrt(max(local_variance + measurement_variance, 0.0)) + distance_penalty
        return Prediction(
            value=math.exp(log_prediction),
            log_value=log_prediction,
            uncertainty_log=uncertainty,
            nearest_distance=nearest_distance,
            out_of_domain=nearest_distance > self.ood_distance,
            neighbor_ids=tuple(item[1]["id"] for item in selected),
        )


def evaluate(model: Any, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[float] = []
    covered = 0
    total = 0
    ood_count = 0
    for record in records:
        validate_record(record)
        prediction = model.predict(record)
        truth_log = math.log(float(record["targetRadiance"]))
        error = abs(prediction.log_value - truth_log)
        errors.append(error)
        total += 1
        if error <= max(2.0 * prediction.uncertainty_log, 1e-9):
            covered += 1
        if prediction.out_of_domain:
            ood_count += 1
        rows.append(
            {
                "id": record["id"],
                "truth": record["targetRadiance"],
                "prediction": prediction.value,
                "absoluteLogError": error,
                "uncertaintyLog": prediction.uncertainty_log,
                "nearestDistance": prediction.nearest_distance,
                "outOfDomain": prediction.out_of_domain,
            }
        )
    if total == 0:
        raise SurrogateError("evaluation set is empty")
    return {
        "count": total,
        "meanAbsoluteLogError": statistics.fmean(errors),
        "medianAbsoluteLogError": statistics.median(errors),
        "maximumAbsoluteLogError": max(errors),
        "twoSigmaCoverage": covered / total,
        "outOfDomainCount": ood_count,
        "rows": rows,
    }


def select_adaptive_cases(
    model: Any,
    candidates: Iterable[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise SurrogateError("limit must be positive")
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for candidate in candidates:
        validate_record(candidate, require_target=False)
        prediction = model.predict(candidate)
        score = (
            prediction.uncertainty_log
            + 0.55 * prediction.nearest_distance
            + (0.35 if prediction.out_of_domain else 0.0)
        )
        scored.append((score, candidate["id"], {**candidate, "selectionScore": score}))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:limit]]


def allocate_two_stage(
    stage_one: Iterable[dict[str, Any]],
    *,
    low_relative_uncertainty: float = 0.03,
    high_relative_uncertainty: float = 0.08,
    one_extra_blocks: int = 2,
    two_extra_blocks: int = 4,
) -> list[dict[str, Any]]:
    if not (0 < low_relative_uncertainty < high_relative_uncertainty):
        raise SurrogateError("uncertainty thresholds must be positive and ordered")
    output: list[dict[str, Any]] = []
    for record in stage_one:
        case_id = record.get("caseId")
        value = record.get("value")
        sigma = record.get("sigma")
        if not isinstance(case_id, str) or not case_id:
            raise SurrogateError("stage-one caseId is required")
        if not isinstance(value, (int, float)) or value <= 0:
            raise SurrogateError("stage-one value must be positive")
        if not isinstance(sigma, (int, float)) or sigma < 0:
            raise SurrogateError("stage-one sigma must be non-negative")
        relative = float(sigma) / float(value)
        if relative <= low_relative_uncertainty:
            extra = 0
            band = "sufficient"
        elif relative <= high_relative_uncertainty:
            extra = one_extra_blocks
            band = "moderate"
        else:
            extra = two_extra_blocks
            band = "high"
        output.append(
            {
                "caseId": case_id,
                "relativeUncertainty": relative,
                "allocationBand": band,
                "additionalIndependentBlocks": extra,
            }
        )
    return output


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise SurrogateError(f"line {line_number} is not an object")
        records.append(value)
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, sort_keys=True, allow_nan=False) + "\n" for record in records))


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-14:
            raise SurrogateError("surrogate normal equations are singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0:
                continue
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[index][-1] for index in range(size)]


def log_basis(point: dict[str, Any]) -> tuple[float, ...]:
    validate_point(point)
    d = (float(point["sunDepressionDeg"]) - 10.5) / 7.5
    h = (float(point["targetAltitudeDeg"]) - 40.0) / 35.0
    az = math.radians(float(point["relativeAzimuthDeg"]))
    aod = (float(point["aod550"]) - 0.26) / 0.24
    elev = (float(point["observerElevationM"]) - 1500.0) / 1500.0
    return (
        1.0,
        d,
        h,
        math.cos(az),
        math.sin(az),
        aod,
        elev,
        d * d,
        h * h,
        aod * aod,
        elev * elev,
        d * aod,
        d * h,
        h * aod,
        math.sin(0.55 * float(point["sunDepressionDeg"])),
        math.cos(math.radians(2.0 * float(point["targetAltitudeDeg"]))),
    )


class LogRidgeSurrogate:
    def __init__(
        self,
        records: Iterable[dict[str, Any]],
        *,
        ridge: float = 1e-8,
        ood_distance: float = 0.62,
    ) -> None:
        prepared: list[tuple[dict[str, Any], tuple[float, ...], tuple[float, ...], float]] = []
        ids: set[str] = set()
        for record in records:
            validate_record(record)
            if record["id"] in ids:
                raise SurrogateError(f"duplicate training id: {record['id']}")
            ids.add(record["id"])
            prepared.append(
                (
                    record,
                    normalized_vector(record),
                    log_basis(record),
                    math.log(float(record["targetRadiance"])),
                )
            )
        if len(prepared) < 24:
            raise SurrogateError("ridge surrogate requires at least 24 training records")
        feature_count = len(prepared[0][2])
        gram = [[0.0] * feature_count for _ in range(feature_count)]
        rhs = [0.0] * feature_count
        for _, _, basis, target in prepared:
            for i in range(feature_count):
                rhs[i] += basis[i] * target
                for j in range(feature_count):
                    gram[i][j] += basis[i] * basis[j]
        for i in range(feature_count):
            gram[i][i] += ridge if i else ridge * 0.01
        self.coefficients = tuple(_solve_linear_system(gram, rhs))
        self.prepared = prepared
        residuals = []
        for _, _, basis, target in prepared:
            fitted = sum(coefficient * value for coefficient, value in zip(self.coefficients, basis, strict=True))
            residuals.append(target - fitted)
        self.residual_std = statistics.stdev(residuals) if len(residuals) > 1 else 0.0
        self.ood_distance = float(ood_distance)

    def predict(self, point: dict[str, Any]) -> Prediction:
        vector = normalized_vector(point)
        basis = log_basis(point)
        log_prediction = sum(
            coefficient * value for coefficient, value in zip(self.coefficients, basis, strict=True)
        )
        ranked = sorted(
            ((euclidean(vector, train_vector), record["id"]) for record, train_vector, _, _ in self.prepared),
            key=lambda item: (item[0], item[1]),
        )
        nearest_distance = ranked[0][0]
        uncertainty = max(self.residual_std, 1e-6) + 0.06 * nearest_distance
        return Prediction(
            value=math.exp(log_prediction),
            log_value=log_prediction,
            uncertainty_log=uncertainty,
            nearest_distance=nearest_distance,
            out_of_domain=nearest_distance > self.ood_distance,
            neighbor_ids=tuple(item[1] for item in ranked[:8]),
        )
