from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

FEATURES = (
    'sunDepressionDeg', 'targetAltitudeDeg', 'relativeAzimuthDeg',
    'observerElevationM', 'aod550',
)
PROPOSAL_RANGES = {
    'sunDepressionDeg': (2.0, 18.0),
    'targetAltitudeDeg': (5.0, 80.0),
    'relativeAzimuthDeg': (0.0, 180.0),
    'observerElevationM': (0.0, 2500.0),
    'aod550': (0.05, 0.4),
}


class Refusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(f'invalid JSON: {path}') from exc
    if not isinstance(value, dict):
        raise Refusal(f'expected object: {path}')
    return value


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    if len(matrix) != size or any(len(row) != size for row in matrix):
        raise Refusal('linear system dimensions changed')
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-14:
            raise Refusal('singular weighted fit')
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    left - factor * right
                    for left, right in zip(augmented[row], augmented[column], strict=True)
                ]
    result = [augmented[index][-1] for index in range(size)]
    if any(not math.isfinite(value) for value in result):
        raise Refusal('non-finite weighted fit')
    return result


def feature(record: dict[str, Any]) -> list[float]:
    geometry = record.get('geometry')
    if not isinstance(geometry, dict):
        raise Refusal(f"geometry missing: {record.get('geometryId')}")
    values: list[float] = []
    for name in FEATURES:
        raw = geometry.get(name)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise Refusal(f"feature missing: {record.get('geometryId')} {name}")
        value = float(raw)
        low, high = PROPOSAL_RANGES[name]
        if not math.isfinite(value) or not low <= value <= high:
            raise Refusal(f"feature outside frozen proposal: {record.get('geometryId')} {name}")
        values.append(value)
    return values


def target(record: dict[str, Any]) -> float:
    statistics = record.get('statistics')
    raw = statistics.get('meanCdM2') if isinstance(statistics, dict) else None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise Refusal(f"target missing: {record.get('geometryId')}")
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise Refusal(f"non-positive target: {record.get('geometryId')}")
    return math.log(value)


def observation_weight(record: dict[str, Any]) -> float:
    classification = record.get('classification')
    statistics = record.get('statistics')
    if not isinstance(statistics, dict):
        raise Refusal('statistics missing')
    zero_hits = int(statistics.get('zeroHitBlockCount', 0))
    if classification in {'PRECISION_TARGET_MET', 'PRECISION_ACCEPTED'} and zero_hits == 0:
        return 1.0
    if classification == 'PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT' or zero_hits:
        return 0.025
    if classification != 'PRECISION_CONTINUATION_EXHAUSTED':
        raise Refusal(f'nonterminal training classification: {classification}')
    raw = statistics.get('relativeStandardErrorOfMean')
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise Refusal('exhausted point missing finite RSEM')
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise Refusal('exhausted point missing finite RSEM')
    return max(0.05, min(0.25, (0.10 / value) ** 2))


def proposal_raw(values: list[float]) -> list[float]:
    return [
        (values[0] - 2.0) / 16.0, (values[1] - 5.0) / 75.0,
        values[2] / 180.0, values[3] / 2500.0, (values[4] - 0.05) / 0.35,
    ]


def proposal_cos(values: list[float]) -> list[float]:
    return [
        (values[0] - 2.0) / 16.0, (values[1] - 5.0) / 75.0,
        math.cos(math.radians(values[2])), values[3] / 2500.0,
        (values[4] - 0.05) / 0.35,
    ]


def proposal_physical(values: list[float]) -> list[float]:
    return [
        (values[0] - 2.0) / 16.0, math.sin(math.radians(values[1])),
        math.cos(math.radians(values[2])), values[3] / 2500.0,
        math.log(values[4] / 0.05) / math.log(0.4 / 0.05),
    ]


def polynomial_terms(values: list[float], degree: int) -> list[float]:
    if degree not in (2, 3):
        raise Refusal('unsupported polynomial degree')
    result = [1.0, *values]
    for left in range(len(values)):
        for right in range(left, len(values)):
            result.append(values[left] * values[right])
    if degree == 3:
        for first in range(len(values)):
            for second in range(first, len(values)):
                for third in range(second, len(values)):
                    result.append(values[first] * values[second] * values[third])
    return result


def basis_v1(values: list[float]) -> list[float]:
    sun, altitude, azimuth, elevation, aerosol = proposal_raw(values)
    return [1.0, sun, altitude, azimuth, elevation, aerosol,
            sun * sun, altitude * altitude, sun * altitude, sun * aerosol]


def basis_cos_compact(values: list[float]) -> list[float]:
    sun, altitude, cosine, elevation, aerosol = proposal_cos(values)
    return [1.0, sun, altitude, cosine, elevation, aerosol,
            sun * sun, altitude * altitude, cosine * cosine,
            sun * altitude, sun * cosine, sun * aerosol, altitude * cosine]


def basis_physical_compact(values: list[float]) -> list[float]:
    sun, altitude, cosine, elevation, aerosol = proposal_physical(values)
    return [1.0, sun, altitude, cosine, elevation, aerosol,
            sun * sun, altitude * altitude, cosine * cosine, aerosol * aerosol,
            sun * altitude, sun * cosine, sun * aerosol,
            altitude * cosine, altitude * aerosol, cosine * aerosol]


BASIS_FUNCTIONS: dict[str, Callable[[list[float]], list[float]]] = {
    'v1-design': basis_v1,
    'cos-compact': basis_cos_compact,
    'physical-compact': basis_physical_compact,
    'poly2-raw': lambda values: polynomial_terms(proposal_raw(values), 2),
    'poly2-cos': lambda values: polynomial_terms(proposal_cos(values), 2),
    'poly2-physical': lambda values: polynomial_terms(proposal_physical(values), 2),
    'poly3-physical': lambda values: polynomial_terms(proposal_physical(values), 3),
}


def fit(records: list[dict[str, Any]], basis_name: str, ridge: float) -> dict[str, Any]:
    function = BASIS_FUNCTIONS.get(basis_name)
    if function is None:
        raise Refusal(f'unknown basis: {basis_name}')
    design = [function(feature(record)) for record in records]
    truths = [target(record) for record in records]
    weights = [observation_weight(record) for record in records]
    size = len(design[0])
    if any(len(row) != size for row in design):
        raise Refusal('basis dimension changed')
    matrix = [[
        sum(weight * row[left] * row[right]
            for row, weight in zip(design, weights, strict=True))
        + (ridge if left == right else 0.0)
        for right in range(size)
    ] for left in range(size)]
    vector = [
        sum(weight * row[column] * truth
            for row, truth, weight in zip(design, truths, weights, strict=True))
        for column in range(size)
    ]
    coefficients = solve(matrix, vector)
    predictions = [sum(coefficient * value
                       for coefficient, value in zip(coefficients, row, strict=True))
                   for row in design]
    weighted_mse = sum(weight * (prediction - truth) ** 2
                       for weight, prediction, truth
                       in zip(weights, predictions, truths, strict=True)) / sum(weights)
    return {'basis': basis_name, 'ridge': ridge, 'coefficients': coefficients,
            'weightedResidualRmseLog': math.sqrt(weighted_mse), 'columnCount': size}


def predict_log(model: dict[str, Any], record: dict[str, Any]) -> float:
    function = BASIS_FUNCTIONS.get(str(model.get('basis')))
    coefficients = model.get('coefficients')
    if function is None or not isinstance(coefficients, list):
        raise Refusal('model state missing')
    row = function(feature(record))
    if len(row) != len(coefficients):
        raise Refusal('model state dimension changed')
    result = sum(float(coefficient) * value
                 for coefficient, value in zip(coefficients, row, strict=True))
    if not math.isfinite(result):
        raise Refusal('non-finite prediction')
    return result
