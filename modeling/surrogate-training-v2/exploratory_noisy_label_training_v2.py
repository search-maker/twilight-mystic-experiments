#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Any


def _sibling(name: str):
    path = Path(__file__).with_name(name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


core = _sibling('_exploratory_v2_core')
selection = _sibling('_exploratory_v2_selection')
Refusal = core.Refusal
dump = core.dump
canonical_sha256 = core.canonical_sha256
raw_sha256 = core.raw_sha256
load = core.load
feature = core.feature
target = core.target
observation_weight = core.observation_weight
proposal_cos = core.proposal_cos
predict_log = core.predict_log
PROPOSAL_RANGES = core.PROPOSAL_RANGES

EXPECTED_DATASET_RAW_SHA256 = 'd08df9100b6e806b5ac0056ee07f3e91e1ca78ec54ea3e7705c35de94bfef026'
EXPECTED_DATASET_SHA256 = 'eb4a5e13bb31d2eec32204574547847cb03c0723cd5cab5538ff2e12b468ded1'
EXPECTED_SOURCE_MODEL_RAW_SHA256 = 'ce575bcd2c40acfa4b1ade48fd70d41cd58cb7d632815db33def079ab172a0fa'
EXPECTED_SOURCE_MODEL_HASH = '381323604143498619cec494d221747d0d32f37a7e7cbb811b0154b6b4f68848'
EXPECTED_SOURCE_BINDING_SHA256 = 'fccdf0d31301b2aa3fe11b5523516070600650f234435ed7a870690296dab004'
TRAINING_IDS = tuple(f'train-{index:04d}' for index in range(1, 49) if index % 5)
RESERVED_VALIDATION_IDS = tuple(f'train-{index:04d}' for index in range(5, 46, 5))
MODEL_STAGE = 'surrogate-training-v2-exploratory-noisy-label-model-v2'
MODEL_STATUS = 'EXPLORATORY_MODEL_V2_FROZEN_TRAINING_ONLY_AWAITING_INDEPENDENT_VALIDATION'


def validate_training_dataset(dataset: dict[str, Any],
                              dataset_path: Path | None = None) -> list[dict[str, Any]]:
    if dataset_path is not None and raw_sha256(dataset_path) != EXPECTED_DATASET_RAW_SHA256:
        raise Refusal('training dataset raw hash changed')
    supplied = dataset.get('datasetSha256')
    payload = {key: value for key, value in dataset.items() if key != 'datasetSha256'}
    if supplied != canonical_sha256(payload) or supplied != EXPECTED_DATASET_SHA256:
        raise Refusal('training dataset self-hash changed')
    expected = {
        'schemaVersion': 1,
        'stageId': 'surrogate-training-v2-exploratory-terminal-training-dataset-v1',
        'status': 'TERMINAL_TRAINING_ONLY_DATASET_HOLDOUT_UNOPENED',
        'sourceBindingSha256': EXPECTED_SOURCE_BINDING_SHA256,
        'trainingGeometryIds': list(TRAINING_IDS),
        'internalHoldoutGeometryIdsExcludedAndUnopened': list(RESERVED_VALIDATION_IDS),
        'holdoutRecordCount': 0,
        'holdoutValuesIncluded': False,
    }
    stale = {key: (dataset.get(key), wanted) for key, wanted in expected.items()
             if dataset.get(key) != wanted}
    if stale:
        raise Refusal(f'training dataset boundary changed: {stale}')
    records = dataset.get('records')
    if not isinstance(records, list) or len(records) != 39:
        raise Refusal('training dataset must contain exactly 39 records')
    identities = [record.get('geometryId') for record in records if isinstance(record, dict)]
    if identities != list(TRAINING_IDS) or len(set(identities)) != 39:
        raise Refusal('training geometry identity/order changed')
    if any(record.get('role') != 'surrogate-training' for record in records):
        raise Refusal('training dataset contains a non-training record')
    for record in records:
        feature(record); target(record); observation_weight(record)
    return records


def freeze(dataset: dict[str, Any], source_model: dict[str, Any], *,
           dataset_path: Path | None = None,
           source_model_path: Path | None = None) -> dict[str, Any]:
    records = validate_training_dataset(dataset, dataset_path)
    if source_model_path is not None and raw_sha256(source_model_path) != EXPECTED_SOURCE_MODEL_RAW_SHA256:
        raise Refusal('source model raw hash changed')
    source_hash = source_model.get('modelHash')
    source_payload = {key: value for key, value in source_model.items() if key != 'modelHash'}
    if source_hash != canonical_sha256(source_payload) or source_hash != EXPECTED_SOURCE_MODEL_HASH:
        raise Refusal('source model self-hash changed')
    if source_model.get('trainingDatasetSha256') != EXPECTED_DATASET_SHA256:
        raise Refusal('source model training dataset changed')
    selected, candidates = selection.select(records, core)
    fitted = core.fit(records, selection.SELECTED_BASIS, selection.SELECTED_RIDGE)
    predictions = {record['geometryId']: predict_log(fitted, record) for record in records}
    restored = dict(fitted)
    if predictions != {record['geometryId']: predict_log(restored, record) for record in records}:
        raise Refusal('model restoration changed training predictions')
    artifact: dict[str, Any] = {
        'schemaVersion': 1, 'stageId': MODEL_STAGE, 'status': MODEL_STATUS,
        'candidateId': 'weighted-quadratic-cosine-ridge',
        'basis': selection.SELECTED_BASIS, 'selectedRidge': selection.SELECTED_RIDGE,
        'selectionRule': selection.SELECTION_RULE,
        'featureList': list(core.FEATURES),
        'basisDefinition': {
            'baseFeatures': [
                '(sunDepressionDeg-2)/16', '(targetAltitudeDeg-5)/75',
                'cos(relativeAzimuthDeg*pi/180)', 'observerElevationM/2500',
                '(aod550-0.05)/0.35',
            ],
            'polynomialDegree': 2, 'includeBias': True,
            'proposalRanges': {key: list(value) for key, value in PROPOSAL_RANGES.items()},
        },
        'sourceTrainingDatasetRawSha256': EXPECTED_DATASET_RAW_SHA256,
        'trainingDatasetSha256': EXPECTED_DATASET_SHA256,
        'sourceModelV1RawSha256': EXPECTED_SOURCE_MODEL_RAW_SHA256,
        'sourceModelV1Hash': EXPECTED_SOURCE_MODEL_HASH,
        'trainingGeometryIds': list(TRAINING_IDS),
        'trainingObservationWeights': {
            record['geometryId']: observation_weight(record) for record in records
        },
        'trainingOnlyFoldIds': [name for name, _, _ in selection.folds(records, core)],
        'selectedTrainingOnlyEvaluation': selected,
        'trainingOnlyCandidateRanking': [
            {key: value for key, value in candidate.items() if key != 'folds'}
            for candidate in candidates
        ],
        'trainingOnlyCandidateRankingSha256': canonical_sha256(candidates),
        'modelState': {'coefficients': fitted['coefficients'],
                       'columnCount': fitted['columnCount']},
        'weightedResidualRmseLog': fitted['weightedResidualRmseLog'],
        'modelFrozen': True, 'modelRestorationVerified': True,
        'openedInternalHoldoutUsedForSelection': False,
        'openedInternalHoldoutUsedForFitting': False,
        'openedInternalHoldoutUsedForPreprocessing': False,
        'openedInternalHoldoutUsedForThresholds': False,
        'internalHoldoutV1Reused': False, 'independentValidationOpened': False,
        'hardAnchorsOpened': False, 'softDiagnosticsOpened': False,
        'generalizationValidated': False, 'observationallyValidated': False,
        'scientificEligibilityClaimed': False, 'tier2Authorized': False,
        'productionModelReady': False, 'productionPromotionAuthorized': False,
    }
    artifact['modelHash'] = canonical_sha256(artifact)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--training-dataset', type=Path, required=True)
    parser.add_argument('--source-model-v1', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = freeze(load(args.training_dataset), load(args.source_model_v1),
                        dataset_path=args.training_dataset,
                        source_model_path=args.source_model_v1)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(dump(result), encoding='utf-8', newline='\n')
        print(dump({'status': result['status'], 'modelHash': result['modelHash'],
                    'basis': result['basis'], 'selectedRidge': result['selectedRidge'],
                    'selectionScore': result['selectedTrainingOnlyEvaluation']['selectionScore']}),
              end='')
        return 0
    except Exception as exc:
        print(dump({'status': 'REFUSED', 'reason': str(exc)}), end='')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
