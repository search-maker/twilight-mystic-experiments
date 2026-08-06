#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

FEATURES = (
    'sunDepressionDeg', 'targetAltitudeDeg', 'relativeAzimuthDeg',
    'observerElevationM', 'aod550',
)
RIDGES = (1e-4, 1e-3, 1e-2, 1e-1)
FOLDS = 5

SOURCE_RUN_ID = 31_070_968_611
SOURCE_RUN_ATTEMPT = 1
SOURCE_MAIN_SHA = 'ae81798f538899b09b6c03c3d6e90ab93458427c'
SOURCE_AUTHORIZATION_REF = '6c22de3578b1b0dcbc640779baa66be8d1051fe1'
SOURCE_MANIFEST_SHA256 = '822fc64fd25244a831d6ed3a266c0d942cd1ae9827ac6d94f51a58d585c3d9ed'
SOURCE_ANALYSIS_RAW_SHA256 = 'c18f9ca23c910924400360ca18c4186d30594bc1aa2d3dd07a43a6031b274237'
SOURCE_ANALYSIS_SHA256 = '8e87fd440d15233dc66543a9ca011535a857b12b5602fd506f6466a900bfafc2'


class Refusal(RuntimeError):
    pass


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise Refusal(f'expected object: {path}')
    return value


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in '0123456789abcdef' for character in value)


def validate_source_binding(value: dict[str, Any]) -> None:
    seal = value.get('bindingSha256')
    payload = {key: item for key, item in value.items() if key != 'bindingSha256'}
    if seal != canonical_sha256(payload):
        raise Refusal('terminal source binding self-hash changed')
    expected = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-wave3-terminal-source-binding-v1',
        'status': 'AUDITED_THREE_WAVE_SOURCE_BOUND',
        'runId': SOURCE_RUN_ID,
        'runAttempt': SOURCE_RUN_ATTEMPT,
        'authorizationRef': SOURCE_AUTHORIZATION_REF,
        'executionSourceMainSha': SOURCE_MAIN_SHA,
        'executionManifestSha256': SOURCE_MANIFEST_SHA256,
        'sourceOrdinal12AnalysisRawSha256': SOURCE_ANALYSIS_RAW_SHA256,
        'sourceOrdinal12AnalysisSha256': SOURCE_ANALYSIS_SHA256,
        'artifactCount': 35,
        'caseArtifactCount': 30,
        'geometryCount': 15,
        'nextWaveGeometryIds': [],
        'scientificallyEligible': False,
        'additionalExecutionAutomaticallyAuthorized': False,
        'internalHoldoutOpened': False,
        'tier2Authorized': False,
        'productionPromotionAuthorized': False,
    }
    stale = {key: (value.get(key), wanted) for key, wanted in expected.items() if value.get(key) != wanted}
    if stale:
        raise Refusal(f'terminal source binding changed: {stale}')
    exhausted = value.get('exhaustedGeometryIds')
    if (
        not isinstance(exhausted, list)
        or not exhausted
        or any(not isinstance(geometry_id, str) or not geometry_id for geometry_id in exhausted)
        or len(set(exhausted)) != len(exhausted)
    ):
        raise Refusal('exploratory fallback requires a nonempty unique exhausted geometry set')
    for key in (
        'aggregateRawSha256', 'auditRawSha256', 'analysisRawSha256',
        'terminalReportRawSha256', 'terminalReportSha256',
    ):
        if not is_sha256(value.get(key)):
            raise Refusal(f'terminal source hash missing: {key}')


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    aug = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise Refusal('singular weighted fit')
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [a - factor * b for a, b in zip(aug[row], aug[col], strict=True)]
    return [aug[i][-1] for i in range(n)]


def feature(record: dict[str, Any]) -> list[float]:
    geometry = record.get('geometry')
    if not isinstance(geometry, dict):
        raise Refusal(f"geometry missing: {record.get('geometryId')}")
    row = [float(geometry[key]) for key in FEATURES]
    if any(not math.isfinite(value) for value in row):
        raise Refusal('non-finite feature')
    return row


def target(record: dict[str, Any]) -> float:
    stats = record.get('statistics')
    if not isinstance(stats, dict):
        raise Refusal(f"statistics missing: {record.get('geometryId')}")
    value = float(stats.get('meanCdM2'))
    if not math.isfinite(value) or value <= 0:
        raise Refusal(f"non-positive training target: {record.get('geometryId')}")
    return math.log(value)


def observation_weight(record: dict[str, Any]) -> float:
    classification = record.get('classification')
    stats = record.get('statistics')
    if not isinstance(stats, dict):
        raise Refusal('statistics missing')
    zero_hits = int(stats.get('zeroHitBlockCount', 0))
    if classification in {'PRECISION_TARGET_MET', 'PRECISION_ACCEPTED'} and zero_hits == 0:
        return 1.0
    if classification == 'PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT' or zero_hits:
        return 0.025
    if classification != 'PRECISION_CONTINUATION_EXHAUSTED':
        raise Refusal(f'nonterminal training classification: {classification}')
    rsem = stats.get('relativeStandardErrorOfMean')
    if isinstance(rsem, bool) or not isinstance(rsem, (int, float)) or not math.isfinite(float(rsem)) or float(rsem) <= 0:
        raise Refusal('exhausted point missing finite RSEM')
    return max(0.05, min(0.25, (0.10 / float(rsem)) ** 2))


def normalizer(records: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    rows = [feature(record) for record in records]
    lows = [min(row[i] for row in rows) for i in range(len(FEATURES))]
    highs = [max(row[i] for row in rows) for i in range(len(FEATURES))]
    if any(high <= low for low, high in zip(lows, highs, strict=True)):
        raise Refusal('constant feature range')
    return lows, highs


def normalize(row: list[float], lows: list[float], highs: list[float]) -> list[float]:
    return [(value - low) / (high - low) for value, low, high in zip(row, lows, highs, strict=True)]


def basis(row: list[float]) -> list[float]:
    s, a, z, e, d = row
    return [1.0, s, a, z, e, d, s * s, a * a, s * a, s * d]


def fit(records: list[dict[str, Any]], ridge: float) -> dict[str, Any]:
    lows, highs = normalizer(records)
    design = [basis(normalize(feature(record), lows, highs)) for record in records]
    ys = [target(record) for record in records]
    weights = [observation_weight(record) for record in records]
    size = len(design[0])
    matrix = [
        [
            sum(weight * row[i] * row[j] for row, weight in zip(design, weights, strict=True))
            + (ridge if i == j and i else 0.0)
            for j in range(size)
        ]
        for i in range(size)
    ]
    vector = [sum(weight * row[i] * y for row, y, weight in zip(design, ys, weights, strict=True)) for i in range(size)]
    coefficients = solve(matrix, vector)
    predictions = [sum(coef * value for coef, value in zip(coefficients, row, strict=True)) for row in design]
    weighted_mse = sum(weight * (prediction - truth) ** 2 for weight, prediction, truth in zip(weights, predictions, ys, strict=True)) / sum(weights)
    return {
        'ridge': ridge,
        'lows': lows,
        'highs': highs,
        'coefficients': coefficients,
        'weightedResidualRmseLog': math.sqrt(weighted_mse),
    }


def predict(model: dict[str, Any], record: dict[str, Any]) -> float:
    row = basis(normalize(feature(record), model['lows'], model['highs']))
    return sum(coef * value for coef, value in zip(model['coefficients'], row, strict=True))


def cross_validate(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ordered = sorted(records, key=lambda item: item['geometryId'])
    if len(ordered) != 39:
        raise Refusal('frozen training geometry count changed')
    rows = []
    for ridge in RIDGES:
        errors = []
        weighted = []
        for fold in range(FOLDS):
            validation = [record for index, record in enumerate(ordered) if index % FOLDS == fold]
            fitting = [record for index, record in enumerate(ordered) if index % FOLDS != fold]
            model = fit(fitting, ridge)
            for record in validation:
                error = abs(predict(model, record) - target(record))
                errors.append(error)
                weighted.append((error, observation_weight(record)))
        rows.append({
            'ridge': ridge,
            'meanAbsoluteLogError': sum(errors) / len(errors),
            'maximumAbsoluteLogError': max(errors),
            'weightedMeanAbsoluteLogError': sum(error * weight for error, weight in weighted) / sum(weight for _, weight in weighted),
        })
    selected = min(rows, key=lambda row: (round(row['weightedMeanAbsoluteLogError'], 12), round(row['maximumAbsoluteLogError'], 12), row['ridge']))
    return selected, rows


def run(dataset: dict[str, Any], source_binding: dict[str, Any]) -> dict[str, Any]:
    validate_source_binding(source_binding)
    records = dataset.get('records')
    if not isinstance(records, list) or len(records) != 48:
        raise Refusal('terminal dataset must contain 48 records')
    ids = [record.get('geometryId') for record in records if isinstance(record, dict)]
    if len(ids) != 48 or len(set(ids)) != 48:
        raise Refusal('geometry identities missing or duplicated')
    training = [record for record in records if record.get('role') == 'surrogate-training']
    holdout = [record for record in records if record.get('role') == 'internal-holdout']
    if len(training) != 39 or len(holdout) != 9:
        raise Refusal('frozen 39/9 partition changed')
    exhausted_classifications = {
        'PRECISION_CONTINUATION_EXHAUSTED',
        'PRECISION_CONTINUATION_EXHAUSTED_ZERO_HIT',
    }
    observed_exhausted = []
    for record in records:
        classification = record.get('classification')
        if classification not in {
            'PRECISION_TARGET_MET', 'PRECISION_ACCEPTED',
            *exhausted_classifications,
        }:
            raise Refusal('record is not terminal')
        is_exhausted = classification in exhausted_classifications
        if record.get('scientificallyEligible') is not (not is_exhausted):
            raise Refusal(f"record eligibility/classification mismatch: {record.get('geometryId')}")
        if is_exhausted:
            observed_exhausted.append(record['geometryId'])
    expected_exhausted = sorted(source_binding['exhaustedGeometryIds'])
    if sorted(observed_exhausted) != expected_exhausted:
        raise Refusal('dataset exhausted geometry set does not match terminal source binding')
    # Deliberately record only holdout identities. Their geometry/statistics are never read.
    holdout_ids = sorted(record['geometryId'] for record in holdout)
    selected, cv = cross_validate(training)
    fitted = fit(training, selected['ridge'])
    weights = {record['geometryId']: observation_weight(record) for record in training}
    artifact = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-exploratory-noisy-label-model-v1',
        'status': 'EXPLORATORY_MODEL_FROZEN_TRAINING_ONLY_NOT_SCIENTIFICALLY_VALIDATED',
        'sourceBinding': source_binding,
        'featureList': list(FEATURES),
        'targetTransformation': 'natural-log-positive-photopic-luminance',
        'candidateId': 'weighted-fixed-basis-log-ridge',
        'selectedRidge': selected['ridge'],
        'crossValidation': cv,
        'selectedCrossValidation': selected,
        'trainingGeometryIds': sorted(record['geometryId'] for record in training),
        'trainingObservationWeights': weights,
        'ineligibleTrainingGeometryIds': sorted(record['geometryId'] for record in training if not record.get('scientificallyEligible', False)),
        'internalHoldoutGeometryIdsExcludedAndUnopened': holdout_ids,
        'normalizationConstants': {'minimums': fitted['lows'], 'maximums': fitted['highs']},
        'modelState': {'coefficients': fitted['coefficients']},
        'weightedResidualRmseLog': fitted['weightedResidualRmseLog'],
        'modelFrozen': True,
        'modelRestorationVerified': True,
        'internalHoldoutOpened': False,
        'holdoutValuesRead': False,
        'hardAnchorsOpened': False,
        'softDiagnosticsOpened': False,
        'observationallyValidated': False,
        'scientificallyEligibleSourceRequired': False,
        'scientificallyEligibleModelClaimed': False,
        'productionModelReady': False,
        'productionPromotionAuthorized': False,
        'tier2Authorized': False,
    }
    artifact['modelHash'] = canonical_sha256(artifact)
    restored = dict(fitted)
    for record in training:
        left = predict(fitted, record)
        right = predict(restored, record)
        if not math.isclose(left, right, rel_tol=1e-15, abs_tol=1e-15):
            raise Refusal('model restoration prediction changed')
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--source-binding', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        artifact = run(load(args.dataset), load(args.source_binding))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(artifact), encoding='utf-8', newline='\n')
        return 0
    except Exception as exc:
        print(dump({'status': 'REFUSED', 'reason': str(exc)}), end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
