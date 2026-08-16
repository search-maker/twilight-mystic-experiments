#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

CONTROL = 'v2-frozen-control-ridge-primary-compact-shape-idw-k4-p1'
CHANGED = 'ridge-primary-local-residual-idw-shape-fixed-idw'
EXPECTED_DATASET = '58c977acf84b6ce17717765c2052f7f9fd64e2965e5bf447eba5cc4accb30435'
EXPECTED_PROTOCOL = '8e3928634c3d297974c07533bed3bbfa24783f14ed55391fd318f817282d9a8e'
EXPECTED_GATES = {
    'looMeanPrimaryMaleMax': 0.25,
    'looWorstSinglePrimaryLogErrorMax': 0.9,
    'looMeanRawShapeNrmseMax': 1.0,
    'looWorstUncertaintyAdjustedShapeNrmseMax': 1.45,
    'looWorstUncertaintyAdjustedSingleCoefficientErrorMax': 3.0,
    'boundaryWorstPrimaryMaleMax': 0.3,
    'boundaryWorstRawShapeNrmseMax': 1.45,
    'looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction': 0.15,
}
SHAPE_AGG = (
    'looMeanRawShapeNrmse', 'looWorstRawShapeNrmseReportOnly',
    'looWorstUncertaintyAdjustedShapeNrmse', 'looWorstUncertaintyAdjustedSingleCoefficientError',
    'boundaryWorstRawShapeNrmse',
)
SHAPE_FOLD = ('rawShapeNrmse', 'uncertaintyAdjustedShapeNrmse', 'worstUncertaintyAdjustedSingleCoefficientError')


def req(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def canonical_without(value: dict[str, Any], field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def checks(row: dict[str, Any]) -> dict[str, bool]:
    g = EXPECTED_GATES
    return {
        'looMeanPrimary': float(row['looMeanPrimaryMale']) <= g['looMeanPrimaryMaleMax'],
        'looWorstSinglePrimary': float(row['looWorstSinglePrimaryLogError']) <= g['looWorstSinglePrimaryLogErrorMax'],
        'looMeanRawShape': float(row['looMeanRawShapeNrmse']) <= g['looMeanRawShapeNrmseMax'],
        'looWorstUncertaintyAdjustedShape': float(row['looWorstUncertaintyAdjustedShapeNrmse']) <= g['looWorstUncertaintyAdjustedShapeNrmseMax'],
        'looWorstUncertaintyAdjustedSingleCoefficient': float(row['looWorstUncertaintyAdjustedSingleCoefficientError']) <= g['looWorstUncertaintyAdjustedSingleCoefficientErrorMax'],
        'boundaryWorstPrimary': float(row['boundaryWorstPrimaryMale']) <= g['boundaryWorstPrimaryMaleMax'],
        'boundaryWorstRawShape': float(row['boundaryWorstRawShapeNrmse']) <= g['boundaryWorstRawShapeNrmseMax'],
        'looPrimaryBaselineImprovement': float(row['looPrimaryImprovementVsBaselineFraction']) >= g['looPrimaryMustBeatFoldMatchedTrainingMeanBaselineByFraction'],
    }


def primary_score(row: dict[str, Any]) -> float:
    m = float(row['looMeanPrimaryMale']) / 0.25
    w = float(row['looWorstSinglePrimaryLogError']) / 0.9
    b = float(row['boundaryWorstPrimaryMale']) / 0.3
    return float(max(m, w, b) + 0.10 * m)


def overall_score(row: dict[str, Any]) -> float:
    mp = float(row['looMeanPrimaryMale']) / 0.25
    wp = float(row['looWorstSinglePrimaryLogError']) / 0.9
    ms = float(row['looMeanRawShapeNrmse']) / 1.0
    us = float(row['looWorstUncertaintyAdjustedShapeNrmse']) / 1.45
    uc = float(row['looWorstUncertaintyAdjustedSingleCoefficientError']) / 3.0
    bp = float(row['boundaryWorstPrimaryMale']) / 0.3
    bs = float(row['boundaryWorstRawShapeNrmse']) / 1.45
    return float(max(mp, wp, ms, us, uc, bp, bs) + 0.10 * (mp + ms))


def hp(row: dict[str, Any]) -> tuple[Any, ...]:
    if row['familyId'] == CONTROL:
        return ('', float(row.get('primaryRidge', 1e-5)), 0, 0.0, 0.0)
    req(row['familyId'] == CHANGED, 'unknown family in audit')
    return (str(row['residualCoordinateSystem']), float(row['primaryRidge']), int(row['residualNeighbors']), float(row['residualPower']), float(row['residualShrinkage']))


def rank(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        float(row['primaryStressScore']), float(row['legacyOverallSelectionScore']),
        float(row['boundaryWorstPrimaryMale']), float(row['looWorstSinglePrimaryLogError']),
        float(row['looMeanPrimaryMale']), int(row['complexityRank']), str(row['familyId']), hp(row),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--protocol', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    protocol = load(args.protocol)
    req(protocol['protocolSha256'] == EXPECTED_PROTOCOL, 'protocol identity drift')
    req(protocol['trainingOnlyReadinessGates'] == {'definition': 'COPY_EXACT_LEVEL_B_V2_GENERATION2_GATES_WITHOUT_RELAXATION', **EXPECTED_GATES}, 'gate drift')
    out = args.output_dir
    selection = load(out / 'training-selection-v1.json')
    result = load(out / 'training-result-v1.json')
    req(selection['selectionSha256'] == canonical_without(selection, 'selectionSha256'), 'selection self-hash drift')
    req(result['resultSha256'] == canonical_without(result, 'resultSha256'), 'result self-hash drift')
    req(selection['governance'] == result['governance'] == 'MYSTIC-STATE-0071', 'governance drift')
    req(selection['protocolSha256'] == EXPECTED_PROTOCOL, 'selection protocol drift')
    req(selection['sourceExpandedDatasetSha256'] == result['sourceExpandedDatasetSha256'] == EXPECTED_DATASET, 'dataset provenance drift')
    req((selection['trainingGeometryCount'], selection['cvFoldCount'], selection['candidateCount']) == (58, 73, 145), 'selection dimensions drift')
    candidates = selection['candidates']
    req(len(candidates) == 145, '145 candidate rows required')
    req(len({r['candidateId'] for r in candidates}) == 145, 'candidate id uniqueness drift')
    req(sum(r['familyId'] == CONTROL for r in candidates) == 1, 'one control required')
    req(sum(r['familyId'] == CHANGED for r in candidates) == 144, '144 changed candidates required')
    control = next(r for r in candidates if r['familyId'] == CONTROL)
    control_folds = {f['fold']: f for f in control['foldMetrics']}
    req(len(control_folds) == 73, 'control 73 fold metrics required')
    for row in candidates:
        req(row['gateChecks'] == checks(row), f'gate-check drift: {row["candidateId"]}')
        req(bool(row['eligible']) == all(checks(row).values()), f'eligibility drift: {row["candidateId"]}')
        req(math.isclose(float(row['primaryStressScore']), primary_score(row), rel_tol=0.0, abs_tol=1e-15), f'primary score drift: {row["candidateId"]}')
        req(math.isclose(float(row['legacyOverallSelectionScore']), overall_score(row), rel_tol=0.0, abs_tol=1e-15), f'overall score drift: {row["candidateId"]}')
        for key in SHAPE_AGG:
            req(row[key] == control[key], f'shape aggregate changed: {row["candidateId"]} {key}')
        folds = {f['fold']: f for f in row['foldMetrics']}
        req(folds.keys() == control_folds.keys(), f'fold universe drift: {row["candidateId"]}')
        for name in folds:
            for key in SHAPE_FOLD:
                req(folds[name][key] == control_folds[name][key], f'shape fold changed: {row["candidateId"]} {name} {key}')
    eligible = sorted([r for r in candidates if r['eligible']], key=rank)
    req(selection['eligibleCandidateCount'] == len(eligible), 'eligible count drift')
    if not eligible:
        expected_status = 'NO_ELIGIBLE_LEVEL_B_V3_TRAINING_ONLY_MODEL_NO_NEW_VALIDATION'
        expected_best = None
    else:
        expected_best = eligible[0]
        expected_status = 'NO_TRAINING_ONLY_EVIDENCE_FOR_CHANGED_MODEL_NO_NEW_VALIDATION' if expected_best['familyId'] == CONTROL else 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE'
        if expected_best['familyId'] == CHANGED:
            req(rank(expected_best) < rank(control), 'changed winner did not strictly outrank control')
    req(selection['status'] == expected_status, 'selection status drift')
    if expected_best is None:
        req(selection['selectedCandidate'] is None, 'selected candidate must be null')
    else:
        req(selection['selectedCandidate']['candidateId'] == expected_best['candidateId'], 'selected candidate identity drift')
    req(result['status'] == expected_status, 'result status drift')
    req(result['trainingSelectionSha256'] == selection['selectionSha256'], 'result/selection binding drift')
    req(selection['protectedValidationOpened'] is False and selection['newMysticSolverExecutionPerformed'] is False, 'selection opened forbidden surface')
    for key in ('protectedValidationAuthorized', 'newMysticSolverExecutionPerformed', 'productionPromotionAuthorized', 'workerBLaneReactivated', 'workerCLaneReactivated'):
        req(result[key] is False, f'result opened forbidden boundary: {key}')
    req(result['futureFreshValidationGovernanceRequired'] is True, 'future governance requirement drift')
    model_path = out / 'model-artifact-v1.json'
    if expected_status == 'FREEZE_CHANGED_MODEL_TRAINING_ONLY_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE':
        req(result['changedModelArtifactWritten'] is True and model_path.is_file(), 'changed winner must write model')
        model = load(model_path)
        req(model['artifactCanonicalSha256'] == canonical_without(model, 'artifactCanonicalSha256'), 'model artifact self-hash drift')
        req(model['governance'] == 'MYSTIC-STATE-0071' and model['sourceExpandedDatasetSha256'] == EXPECTED_DATASET, 'model provenance drift')
        req(model['trainingSelectionSha256'] == selection['selectionSha256'], 'model selection binding drift')
        req(model['protectedValidationAuthorized'] is False and model['futureFreshValidationGovernanceRequired'] is True and model['productionPromotionAuthorized'] is False, 'model opened forbidden boundary')
        req(model['model']['kind'] == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'changed model kind drift')
        req(len(model['model']['fitGeometryIdsInStableOrder']) == 58 and len(model['model']['residualCoordinates']) == 58 and len(model['model']['residualTargets']) == 58, 'changed model training support drift')
        req(result['modelArtifactCanonicalSha256'] == model['artifactCanonicalSha256'], 'result/model artifact binding drift')
        req(result['modelCanonicalSha256'] == model['model']['modelCanonicalSha256'], 'result/model canonical binding drift')
    else:
        req(result['changedModelArtifactWritten'] is False and not model_path.exists(), 'terminal unchanged outcome must not write model')
    print(json.dumps({'status': 'PASS', 'selectionStatus': expected_status, 'eligibleCandidateCount': len(eligible), 'selectedCandidateId': None if expected_best is None else expected_best['candidateId']}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
