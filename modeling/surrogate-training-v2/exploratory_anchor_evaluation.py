#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

EXPECTED_MODEL_RAW_SHA256 = '2497c0b78f552a03564565e44d2b633828428eda0bc967954f646cfdf1dd0cb5'
EXPECTED_MODEL_HASH = 'c75971120e778e9ca85ffec81cdd8aa362fd46be364b436c54ef6cdf2a82bcac'
EXPECTED_PROTOCOL_SHA256 = '7ddeb3d0c4e29a8e419513339e50925d09a340d8fe86c651ea7f0e7b277b8a77'
EXPECTED_HARD_IDS = (
    'g02-early-near-low',
    'g03-early-perpendicular-high',
    'g04-mid-perpendicular',
    'g05-mid-opposite-low',
    'g06-late-opposite-high-aerosol',
)
EXPECTED_SOFT_IDS = ('g01-reference-bridge',)
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
FACTOR_TWO_LOG_ERROR = math.log(2.0)


class AnchorRefusal(RuntimeError):
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
        raise AnchorRefusal(f'invalid JSON: {path}') from exc
    if not isinstance(value, dict):
        raise AnchorRefusal(f'expected object: {path}')
    return value


def validate_protocol(protocol: dict[str, Any]) -> None:
    supplied = protocol.get('protocolSha256')
    payload = {key: value for key, value in protocol.items() if key != 'protocolSha256'}
    if supplied != canonical_sha256(payload) or supplied != EXPECTED_PROTOCOL_SHA256:
        raise AnchorRefusal('anchor protocol self-hash changed')
    expected = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-exploratory-external-anchor-protocol-v2',
        'status': 'FROZEN_BEFORE_EXTERNAL_ANCHOR_OPENING',
        'sourceModelArtifactId': 8969169714,
        'sourceModelArtifactZipSha256': 'b5d64aab87066eea029ef57dcfcfb1e50753a54a848c73641adc2a308ad18a3e',
        'sourceModelHeadSha': 'ca6da420cd7acfbcfad77c4f55eecc78b4e1bdfe',
        'sourceModelRunId': 31105103370,
        'sourceModelMergedCommitSha': 'ae178bb94ddbc3d88a2a9f9e24cebe1a365a1170',
        'sourceModelArtifactRawSha256': EXPECTED_MODEL_RAW_SHA256,
        'sourceModelHash': EXPECTED_MODEL_HASH,
    }
    stale = {key: (protocol.get(key), wanted) for key, wanted in expected.items()
             if protocol.get(key) != wanted}
    if stale:
        raise AnchorRefusal(f'anchor protocol identity changed: {stale}')
    external = protocol.get('externalSource')
    if external != {
        'artifactId': 8890906227,
        'artifactName': 'twilight-surrogate-tier-1-proposal-v1',
        'artifactZipSha256': '899507d315ae25db88babb3f610587fca24238e7a7000038eed009c7a14af9a0',
        'expectedMember': 'validated-reference-anchors.json',
        'headSha': '9ab74efabfd34799aeeb5c9220a84639861f739d',
        'runId': 30905632743,
    }:
        raise AnchorRefusal('external anchor source changed')
    if protocol.get('acceptanceCriteria') != {
        'hardAnchorCount': 5,
        'maximumAbsoluteLogErrorMaximum': 1.801199122096379,
        'meanAbsoluteLogErrorMaximum': 0.5010632228267312,
        'minimumWithinFactorTwoCount': 4,
        'nonFiniteOrNonPositivePredictionMaximumCount': 0,
        'outOfProposalRangeMaximumCount': 0,
    }:
        raise AnchorRefusal('anchor acceptance criteria changed')
    if protocol.get('thresholdDerivation') != {
        'relativeMultiplier': 1.5,
        'selectedTrainingOnlyMeanFoldMeanAbsoluteLogError': 0.33404214855115416,
        'selectedTrainingOnlyWorstPointAbsoluteLogError': 1.2007994147309193,
    }:
        raise AnchorRefusal('anchor threshold derivation changed')
    if protocol.get('anchorPolicy') != {
        'hardAnchorIds': list(EXPECTED_HARD_IDS),
        'primaryTarget': 'geometric-mean-of-alis-and-reference-vroom-photopic-means',
        'softDiagnosticIds': list(EXPECTED_SOFT_IDS),
        'softDiagnosticsCannotCompensate': True,
        'softDiagnosticsReportOnly': True,
    }:
        raise AnchorRefusal('anchor policy changed')
    if protocol.get('openingRules') != {
        'anchorValuesOpenExactlyOnce': True,
        'failedValidationMustRemainImmutable': True,
        'featureOrPreprocessingChangeAfterOpeningForbidden': True,
        'modelFrozenBeforeOpening': True,
        'selectionFromAnchorsForbidden': True,
        'thresholdTuningFromAnchorsForbidden': True,
    }:
        raise AnchorRefusal('anchor opening rules changed')
    if protocol.get('claimBoundary') != {
        'computationallyValidated': False,
        'generalizationValidated': False,
        'observationallyValidated': False,
        'productionModelReady': False,
        'productionPromotionAuthorized': False,
        'scientificEligibilityClaimed': False,
        'tier2Authorized': False,
    }:
        raise AnchorRefusal('anchor claim boundary changed')


def validate_model(model: dict[str, Any], path: Path) -> None:
    if raw_sha256(path) != EXPECTED_MODEL_RAW_SHA256:
        raise AnchorRefusal('v2 model artifact raw hash changed')
    supplied = model.get('modelHash')
    payload = {key: value for key, value in model.items() if key != 'modelHash'}
    if supplied != canonical_sha256(payload) or supplied != EXPECTED_MODEL_HASH:
        raise AnchorRefusal('v2 model self-hash changed')
    expected = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-exploratory-noisy-label-model-v2',
        'status': 'EXPLORATORY_MODEL_V2_FROZEN_TRAINING_ONLY_AWAITING_INDEPENDENT_VALIDATION',
        'basis': 'poly2-cos',
        'selectedRidge': 0.001,
        'modelFrozen': True,
        'modelRestorationVerified': True,
        'openedInternalHoldoutUsedForSelection': False,
        'openedInternalHoldoutUsedForFitting': False,
        'openedInternalHoldoutUsedForPreprocessing': False,
        'openedInternalHoldoutUsedForThresholds': False,
        'internalHoldoutV1Reused': False,
        'independentValidationOpened': False,
        'hardAnchorsOpened': False,
        'softDiagnosticsOpened': False,
        'generalizationValidated': False,
        'observationallyValidated': False,
        'scientificEligibilityClaimed': False,
        'tier2Authorized': False,
        'productionModelReady': False,
        'productionPromotionAuthorized': False,
    }
    stale = {key: (model.get(key), wanted) for key, wanted in expected.items()
             if model.get(key) != wanted}
    if stale:
        raise AnchorRefusal(f'v2 model boundary changed: {stale}')
    coefficients = model.get('modelState', {}).get('coefficients')
    if not isinstance(coefficients, list) or len(coefficients) != 21:
        raise AnchorRefusal('v2 model coefficient universe changed')
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(float(value)) for value in coefficients):
        raise AnchorRefusal('v2 model contains non-finite coefficients')


def _finite_positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnchorRefusal(f'{label} must be numeric')
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise AnchorRefusal(f'{label} must be positive finite')
    return result


def validate_anchors(value: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected = {
        'schemaVersion': 1,
        'stageId': 'twilight-model-readiness-v1',
        'status': 'REFERENCE_ANCHORS_VALIDATED',
        'anchorCount': 6,
        'hardValidationAnchorCount': 5,
        'softDiagnosticAnchorCount': 1,
        'hardValidationAnchorIds': list(EXPECTED_HARD_IDS),
        'softDiagnosticAnchorIds': list(EXPECTED_SOFT_IDS),
        'trainingAutomaticallyAuthorized': False,
        'productionModelReady': False,
        'observationValidationRequired': True,
    }
    stale = {key: (value.get(key), wanted) for key, wanted in expected.items()
             if value.get(key) != wanted}
    if stale:
        raise AnchorRefusal(f'validated anchor envelope changed: {stale}')
    anchors = value.get('anchors')
    if not isinstance(anchors, list) or len(anchors) != 6:
        raise AnchorRefusal('validated anchor record count changed')
    by_id: dict[str, dict[str, Any]] = {}
    for anchor in anchors:
        if not isinstance(anchor, dict):
            raise AnchorRefusal('anchor record must be object')
        group = anchor.get('groupId')
        if group in by_id or group not in set(EXPECTED_HARD_IDS) | set(EXPECTED_SOFT_IDS):
            raise AnchorRefusal(f'anchor identity changed: {group}')
        geometry = anchor.get('geometry')
        methods = anchor.get('methods')
        if not isinstance(geometry, dict) or not isinstance(methods, dict):
            raise AnchorRefusal(f'anchor geometry/methods missing: {group}')
        if geometry.get('geometryId') != group:
            raise AnchorRefusal(f'anchor geometry identity changed: {group}')
        for feature_name in FEATURES:
            raw = geometry.get(feature_name)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
                raise AnchorRefusal(f'anchor feature invalid: {group} {feature_name}')
        for method in ('alis', 'reference-vroom'):
            method_value = methods.get(method)
            if not isinstance(method_value, dict):
                raise AnchorRefusal(f'anchor method missing: {group} {method}')
            _finite_positive(method_value.get('meanCdM2'), f'{group}.{method}.meanCdM2')
            rsem = method_value.get('relativeStandardErrorOfMean')
            if isinstance(rsem, bool) or not isinstance(rsem, (int, float)) or not 0 <= float(rsem) <= 0.10:
                raise AnchorRefusal(f'anchor RSEM invalid: {group} {method}')
        hard = group in EXPECTED_HARD_IDS
        required = {
            'eligibleForTraining': False,
            'eligibleForModelAcceptance': hard,
            'observationValidationRequired': True,
            'anchorStrength': 'hard' if hard else 'soft-diagnostic',
        }
        if any(anchor.get(key) != wanted for key, wanted in required.items()):
            raise AnchorRefusal(f'anchor policy changed: {group}')
        by_id[str(group)] = anchor
    hard_rows = [by_id[group] for group in EXPECTED_HARD_IDS]
    soft_rows = [by_id[group] for group in EXPECTED_SOFT_IDS]
    return hard_rows, soft_rows


def _proposal_features(geometry: dict[str, Any]) -> tuple[list[float], bool]:
    raw_values: list[float] = []
    out_of_range = False
    for name in FEATURES:
        raw = geometry[name]
        value = float(raw)
        low, high = PROPOSAL_RANGES[name]
        out_of_range = out_of_range or value < low or value > high
        raw_values.append(value)
    sun, altitude, azimuth, elevation, aerosol = raw_values
    values = [
        (sun - 2.0) / 16.0,
        (altitude - 5.0) / 75.0,
        math.cos(math.radians(azimuth)),
        elevation / 2500.0,
        (aerosol - 0.05) / 0.35,
    ]
    return values, out_of_range


def _basis(values: list[float]) -> list[float]:
    result = [1.0, *values]
    for left in range(len(values)):
        for right in range(left, len(values)):
            result.append(values[left] * values[right])
    if len(result) != 21:
        raise AnchorRefusal('v2 basis dimension changed')
    return result


def predict(model: dict[str, Any], anchor: dict[str, Any]) -> dict[str, Any]:
    values, out_of_range = _proposal_features(anchor['geometry'])
    coefficients = [float(value) for value in model['modelState']['coefficients']]
    log_prediction = sum(coefficient * term
                         for coefficient, term in zip(coefficients, _basis(values), strict=True))
    prediction = math.exp(log_prediction)
    valid = math.isfinite(prediction) and prediction > 0
    return {
        'logPrediction': log_prediction,
        'predictionCdM2': prediction,
        'outOfProposalRange': out_of_range,
        'validPositivePrediction': valid,
    }


def _row(model: dict[str, Any], anchor: dict[str, Any]) -> dict[str, Any]:
    prediction = predict(model, anchor)
    methods = anchor['methods']
    alis = _finite_positive(methods['alis']['meanCdM2'], 'alis mean')
    vroom = _finite_positive(methods['reference-vroom']['meanCdM2'], 'vroom mean')
    consensus_log = 0.5 * (math.log(alis) + math.log(vroom))
    if prediction['validPositivePrediction']:
        consensus_error = abs(float(prediction['logPrediction']) - consensus_log)
        alis_error = abs(float(prediction['logPrediction']) - math.log(alis))
        vroom_error = abs(float(prediction['logPrediction']) - math.log(vroom))
    else:
        consensus_error = alis_error = vroom_error = math.inf
    return {
        'groupId': anchor['groupId'],
        'anchorStrength': anchor['anchorStrength'],
        **prediction,
        'alisMeanCdM2': alis,
        'referenceVroomMeanCdM2': vroom,
        'computationalConsensusCdM2': math.sqrt(alis * vroom),
        'absoluteLogErrorToConsensus': consensus_error,
        'absoluteLogErrorToAlis': alis_error,
        'absoluteLogErrorToReferenceVroom': vroom_error,
        'withinFactorTwoOfConsensus': consensus_error <= FACTOR_TWO_LOG_ERROR,
    }


def evaluate(model_path: Path, protocol_path: Path, anchors_path: Path) -> dict[str, Any]:
    model = load(model_path)
    protocol = load(protocol_path)
    anchors = load(anchors_path)
    validate_model(model, model_path)
    validate_protocol(protocol)
    hard, soft = validate_anchors(anchors)
    hard_rows = [_row(model, anchor) for anchor in hard]
    soft_rows = [_row(model, anchor) for anchor in soft]
    errors = [float(row['absoluteLogErrorToConsensus']) for row in hard_rows]
    invalid_count = sum(not row['validPositivePrediction'] for row in hard_rows)
    out_of_range_count = sum(row['outOfProposalRange'] for row in hard_rows)
    if any(not math.isfinite(error) for error in errors):
        mean_error = maximum_error = math.inf
    else:
        mean_error = sum(errors) / len(errors)
        maximum_error = max(errors)
    within_factor_two = sum(row['withinFactorTwoOfConsensus'] for row in hard_rows)
    criteria = protocol['acceptanceCriteria']
    checks = {
        'hardAnchorCount': len(hard_rows) == int(criteria['hardAnchorCount']),
        'meanAbsoluteLogError': mean_error <= float(criteria['meanAbsoluteLogErrorMaximum']),
        'maximumAbsoluteLogError': maximum_error <= float(criteria['maximumAbsoluteLogErrorMaximum']),
        'withinFactorTwoCount': within_factor_two >= int(criteria['minimumWithinFactorTwoCount']),
        'outOfProposalRangeCount': out_of_range_count <= int(criteria['outOfProposalRangeMaximumCount']),
        'nonFiniteOrNonPositivePredictionCount': invalid_count <= int(criteria['nonFiniteOrNonPositivePredictionMaximumCount']),
    }
    passed = all(checks.values())
    result: dict[str, Any] = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-exploratory-external-anchor-result-v2',
        'status': 'EXTERNAL_COMPUTATIONAL_ANCHOR_VALIDATION_PASSED' if passed else 'EXTERNAL_COMPUTATIONAL_ANCHOR_VALIDATION_FAILED',
        'protocolSha256': protocol['protocolSha256'],
        'modelArtifactRawSha256': raw_sha256(model_path),
        'modelHash': model['modelHash'],
        'anchorsRawSha256': raw_sha256(anchors_path),
        'hardAnchorIds': list(EXPECTED_HARD_IDS),
        'softDiagnosticIds': list(EXPECTED_SOFT_IDS),
        'hardAnchorCount': len(hard_rows),
        'softDiagnosticCount': len(soft_rows),
        'meanAbsoluteLogErrorToConsensus': mean_error,
        'maximumAbsoluteLogErrorToConsensus': maximum_error,
        'withinFactorTwoOfConsensusCount': within_factor_two,
        'outOfProposalRangeCount': out_of_range_count,
        'nonFiniteOrNonPositivePredictionCount': invalid_count,
        'acceptanceCriteria': criteria,
        'acceptanceChecks': checks,
        'computationallyValidated': passed,
        'generalizationValidated': passed,
        'selectionFromAnchorsForbidden': True,
        'thresholdTuningFromAnchorsForbidden': True,
        'modelOrPreprocessingChangeAfterOpeningForbidden': True,
        'externalAnchorsOpenedExactlyOnce': True,
        'softDiagnosticsReportOnly': True,
        'softDiagnosticsCannotCompensate': True,
        'observationallyValidated': False,
        'scientificEligibilityClaimed': False,
        'tier2Authorized': False,
        'productionModelReady': False,
        'productionPromotionAuthorized': False,
        'hardAnchorRows': hard_rows,
        'softDiagnosticRows': soft_rows,
    }
    result['resultSha256'] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-artifact', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--anchors', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = evaluate(args.model_artifact, args.protocol, args.anchors)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding='utf-8', newline='\n')
        return 0 if result['computationallyValidated'] else 3
    except Exception as exc:
        print(dump({'status': 'REFUSED', 'reason': str(exc)}), end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
