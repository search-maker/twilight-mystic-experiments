#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE_REL = Path('review/level-b-v3-future-fresh-validation-source-v1/contract-v1.json')
BASE_EVAL_REL = Path('review/level-b-v2-densified58-fresh-validation-implementation-v1/fresh_validation_v1.py')
ENGINE_REL = Path('review/level-b-v3-training-only-implementation-v1/engine_v1.py')
TRAINER_REL = Path('review/level-b-v2-training-implementation-v2/train_v2.py')
CONTRACT_ID = 'level-b-v3-fresh-protected-validation-ordinal28-v1'
MODEL_SHA = 'c4902eb3c2ba67b12dc4ef2b9cefb67c5963a6abc104708a73b2aab5dd0163b9'
MODEL_ARTIFACT_SHA = 'd7f77416c782dd6226be0898f722fb880096638156517177cf1252b96b66f015'
BASE_MODEL_SHA = '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7'
REP_SHA = '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'
SOURCE_BLOB = '105b1560dbb1dacaba891a6828ca04a28d756e6b'


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    req(spec is not None and spec.loader is not None, f'cannot load module: {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_blob(repo_root: Path, rel: Path) -> str:
    import subprocess
    return subprocess.check_output(['git', 'rev-parse', 'HEAD:' + rel.as_posix()], cwd=repo_root, text=True).strip()


def validate_contract(p: dict[str, Any], repo_root: Path | None = None) -> None:
    req((p.get('schemaVersion'), p.get('contractId'), p.get('status'), p.get('governance')) == (
        1, CONTRACT_ID, 'REVIEW_ONLY_FROZEN_FRESH_VALIDATION_IMPLEMENTATION_NO_AUTHORIZATION_NO_VALUES_OPENED', 'MYSTIC-STATE-0072'
    ), 'contract identity drift')
    req(p.get('sourceMainAtFreeze') == '6df161627dacdf8592ae3226e8f366e0e507e195', 'source main drift')
    sb = p['sourceBindings']
    req(sb['futureSourceGitBlobSha'] == SOURCE_BLOB, 'future source blob binding drift')
    req(sb['modelCanonicalSha256'] == MODEL_SHA and sb['modelArtifactCanonicalSha256'] == MODEL_ARTIFACT_SHA, 'v3 model binding drift')
    req(sb['baseModelCanonicalSha256'] == BASE_MODEL_SHA, 'base model binding drift')
    req(sb['representationPackageSha256'] == REP_SHA, 'representation binding drift')
    gs = p['geometrySelection']
    req(gs['selectedGeometryCount'] == 6 and len(gs['selectedGeometries']) == 6, 'geometry count drift')
    req(gs['targetValuesMayInfluenceSelection'] is False and gs['modelPredictionsMayInfluenceSelection'] is False and gs['ordinal27ValuesMayInfluenceSelection'] is False, 'selection leakage boundary opened')
    req(gs['individualPointReplacementAllowed'] is False and gs['repositoryWideCollisionAuditRequiredBeforeAuthorization'] is True, 'freshness boundary drift')
    env = p['executionEnvelope']
    req((env['candidateScientificOrdinal'], env['geometryCount'], env['blocksPerGeometry'], env['caseCount'], env['photonHistoriesPerBlock'], env['configuredPhotonHistories']) == (28,6,4,24,40_000_000,960_000_000), 'execution envelope drift')
    req(env['reservedSeeds'] == list(range(2110000001,2110000025)), 'seed range/order drift')
    req(env['scientificOrdinalAllocated'] is False, 'ordinal already allocated in review contract')
    for k in ('githubRerunAllowed','retryAllowed','resumeAllowed','adaptiveExtraBlocksAllowed','adaptivePointReplacementAllowed'):
        req(env[k] is False, f'execution continuation opened: {k}')
    me = p['modelAndEvaluation']
    req(me['selectedCandidateId'] == 'resid-V1_IDW_COS_COORDINATES-r1e-05-k6-p1-a1' and me['selectedModelKind'] == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'selected v3 model spec drift')
    req((me['positiveChannelAbsoluteMeanSignedLogBiasMax'], me['positiveChannelMedianAbsoluteLogErrorMax'], me['positiveChannelWorstAbsoluteLogErrorMax'], me['positiveChannelWorstUncertaintyNormalizedErrorMax']) == (0.08,0.15,0.35,3.0), 'primary DoD drift')
    req((me['shapeMedianPerCaseNrmseMax'], me['shapeWorstPerCaseNrmseMax'], me['shapeWorstSingleCoefficientNormalizedErrorMax']) == (0.75,1.25,3.0), 'shape DoD drift')
    req(me['surrogateLogErrorBudgetOneSigma'] == 0.12 and me['validatedSupportNearestDistanceMaxInclusive'] == 0.6, 'support/uncertainty drift')
    req(me['aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline'] == 0.7, 'baseline threshold drift')
    req(me['frozenTrainingMeanBaselineTransformedPrimary'] == [0.3993901995212697,1.7062844994448103,-3.8475190646906268], 'baseline vector drift')
    req(me['p90OrP95PrincipalMetricAllowed'] is False and me['noRetuningAfterHoldoutOpening'] is True and me['epsilonSubstitutionAllowed'] is False and me['exactZeroSemanticsPreserved'] is True and me['ordinal27MayInfluenceEvaluatorOrThresholds'] is False, 'evaluation boundary drift')
    for k, v in p['boundaries'].items():
        req(v is False, f'review boundary opened: {k}')
    if repo_root is not None:
        req(git_blob(repo_root, SOURCE_REL) == SOURCE_BLOB, 'future source Git blob drift')
        source = load(repo_root / SOURCE_REL)
        rows = source['geometrySelection']['selectedGeometries']
        req(len(rows) == 6, 'source row count drift')
        for i, (a, b) in enumerate(zip(gs['selectedGeometries'], rows), start=1):
            req(a['sourceId'] == b['sourceId'] == f'future-fresh-source-{i:02d}', f'source id drift {i}')
            req(a['normalizedCoordinates'] == b['normalizedCoordinates'] and a['geometry'] == b['geometry'], f'source geometry drift {i}')
            req(abs(float(a['nearestTrainingDistance']) - float(b['nearestTrainingDistance'])) <= 1e-15, f'source distance drift {i}')


def expected_cases(p: dict[str, Any]) -> list[dict[str, Any]]:
    validate_contract(p)
    out = []
    seeds = p['executionEnvelope']['reservedSeeds']
    cursor = 0
    for g in p['geometrySelection']['selectedGeometries']:
        for block in range(1,5):
            out.append({
                'caseId': f"{g['geometryId']}-b{block}",
                'geometryId': g['geometryId'],
                'block': block,
                'seed': int(seeds[cursor]),
                'photonHistories': 40_000_000,
                'alisSpectralImportanceSamplingNm': 550.0,
            })
            cursor += 1
    req(len(out) == 24 and [x['seed'] for x in out] == list(range(2110000001,2110000025)), 'case construction drift')
    return out


def verify_artifacts(materialized: dict[str, Any], base: dict[str, Any]) -> None:
    req(materialized.get('artifactCanonicalSha256') == MODEL_ARTIFACT_SHA, 'materialized artifact canonical SHA drift')
    req(materialized.get('status') == 'TRAINING_ONLY_CHANGED_MODEL_FROZEN_PENDING_SEPARATE_FRESH_VALIDATION_GOVERNANCE', 'materialized status drift')
    req(materialized.get('trainingGeometryCount') == 58 and materialized.get('protectedValidationAuthorized') is False, 'materialized boundary drift')
    model = materialized.get('model') or {}
    stored = model.get('modelCanonicalSha256')
    body = copy.deepcopy(model); body.pop('modelCanonicalSha256', None)
    req(stored == MODEL_SHA and canon(body) == MODEL_SHA, 'hybrid model canonical SHA drift')
    req(model.get('kind') == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'hybrid model kind drift')
    req((model.get('residualCoordinateSystem'),model.get('residualNeighbors'),model.get('residualPower'),model.get('residualShrinkage')) == ('V1_IDW_COS_COORDINATES',6,1.0,1.0), 'residual predictor drift')
    req(len(model.get('residualCoordinates') or []) == 58 and len(model.get('residualTargets') or []) == 58, 'residual training universe drift')
    req(base.get('modelSha256') == BASE_MODEL_SHA and base.get('trainingGeometryCount') == 58, 'base model identity drift')
    req(base.get('model') == model.get('baseModel'), 'materialized base model differs from frozen densified58 base model')
    scales = np.asarray(base.get('nullspaceCoefficientScales'), dtype=np.float64)
    req(scales.shape == (10,) and np.all(np.isfinite(scales)) and np.all(scales > 0), 'shape scale drift')


def compatibility_model(materialized: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    verify_artifacts(materialized, base)
    hybrid = copy.deepcopy(materialized['model'])
    hybrid['shapeFitX'] = copy.deepcopy(base['model']['shape']['coordinates'])
    return {
        'modelSha256': MODEL_SHA,
        'model': hybrid,
        'nullspaceCoefficientScales': copy.deepcopy(base['nullspaceCoefficientScales']),
        'status': materialized['status'],
        'trainingGeometryCount': 58,
        'protectedHoldoutRecordCount': 0,
        'ordinal22ValuesRead': False,
        'protectedValidationAuthorized': False,
    }


def verify_compat_model(model: dict[str, Any], p: dict[str, Any]) -> None:
    req(model.get('modelSha256') == MODEL_SHA == p['sourceBindings']['modelCanonicalSha256'], 'compat model SHA drift')
    m = model.get('model') or {}
    req(m.get('kind') == 'RIDGE_PRIMARY_RESIDUAL_IDW_SHAPE_IDW', 'compat model kind drift')
    req(m.get('baseModel', {}).get('kind') == 'RIDGE_PRIMARY_IDW_SHAPE', 'compat base model kind drift')
    x = np.asarray(m.get('shapeFitX'), dtype=np.float64)
    req(x.shape == (58,5) and np.all(np.isfinite(x)), 'support coordinate compatibility drift')
    scales = np.asarray(model.get('nullspaceCoefficientScales'), dtype=np.float64)
    req(scales.shape == (10,) and np.all(scales > 0), 'compat scales drift')


def predict_compat(model: dict[str, Any], geometry: dict[str, Any], repo_root: Path) -> np.ndarray:
    engine = module('level_b_v3_engine_for_validation', repo_root / ENGINE_REL)
    trainer = module('level_b_v2_trainer_for_base_prediction', repo_root / TRAINER_REL)
    pred = np.asarray(engine.predict_hybrid(model['model'], geometry, trainer.predict), dtype=np.float64)
    req(pred.shape == (13,) and np.all(np.isfinite(pred)), 'hybrid prediction drift')
    return pred


def evaluate(p: dict[str, Any], cases_root: Path, materialized_dir: Path, base_model_dir: Path, representation_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    validate_contract(p, repo_root)
    materialized = load(materialized_dir / 'model-artifact-materialization-v1.json')
    base_model = load(base_model_dir / 'model-artifact-v3-densified58.json')
    compat = compatibility_model(materialized, base_model)
    base_eval = module('frozen_v0070_evaluation_math_for_v3', repo_root / BASE_EVAL_REL)
    base_eval.CONTRACT_ID = CONTRACT_ID
    base_eval.MODEL_SHA = MODEL_SHA
    base_eval.validate_contract = lambda pp: validate_contract(pp)
    base_eval.expected_cases = expected_cases
    base_eval.verify_model = verify_compat_model
    base_eval.predict = predict_compat
    with tempfile.TemporaryDirectory() as td:
        compat_dir = Path(td)
        write(compat_dir / 'model-artifact-v3-densified58.json', compat)
        tmp_out = compat_dir / 'raw-result.json'
        result = base_eval.evaluate(p, cases_root, compat_dir, representation_dir, repo_root, tmp_out)
    result['stageId'] = 'LEVEL_B_V3_FRESH_PROTECTED_VALIDATION_EVALUATION_V1_ORDINAL28'
    result['governance'] = 'MYSTIC-STATE-0072'
    result['scientificOrdinal'] = 28
    result['modelSha256'] = MODEL_SHA
    result['sourceProtocolId'] = 'level-b-v3-future-fresh-validation-source-v1'
    result['ordinal27ValuesRead'] = False
    result['ordinal27MayInfluenceResult'] = False
    result['retuningPerformed'] = False
    result.pop('resultSha256', None)
    result['resultSha256'] = canon(result)
    write(output, result)
    return result


def training_parity(p: dict[str, Any], materialized_dir: Path, base_model_dir: Path, repo_root: Path) -> dict[str, Any]:
    validate_contract(p, repo_root)
    materialized = load(materialized_dir / 'model-artifact-materialization-v1.json')
    base = load(base_model_dir / 'model-artifact-v3-densified58.json')
    verify_artifacts(materialized, base)
    dataset = load(base_model_dir / 'training-representation-dataset-v3-densified58.json')
    req(dataset.get('geometryCount') == 58 and len(dataset.get('records') or []) == 58, 'training dataset count drift')
    trainer = module('level_b_v2_trainer_for_training_parity', repo_root / TRAINER_REL)
    engine = module('level_b_v3_engine_for_training_parity', repo_root / ENGINE_REL)
    scales = np.asarray(base['nullspaceCoefficientScales'], dtype=np.float64)
    max_primary = 0.0
    max_shape = 0.0
    for rec in dataset['records']:
        truth, _ = trainer.targets_and_shape_se(rec, scales)
        base_pred = np.asarray(trainer.predict(base['model'], rec['geometry']), dtype=np.float64)
        pred = np.asarray(engine.predict_hybrid(materialized['model'], rec['geometry'], trainer.predict), dtype=np.float64)
        max_primary = max(max_primary, float(np.max(np.abs(pred[:3] - truth[:3]))))
        max_shape = max(max_shape, float(np.max(np.abs(pred[3:] - base_pred[3:]))))
    req(max_primary <= 1e-12, f'training exact-match primary parity failed: {max_primary}')
    req(max_shape == 0.0, f'shape invariance failed: {max_shape}')
    baseline = np.mean(np.vstack([trainer.targets_and_shape_se(r, scales)[0][:3] for r in dataset['records']]), axis=0)
    frozen = np.asarray(p['modelAndEvaluation']['frozenTrainingMeanBaselineTransformedPrimary'], dtype=np.float64)
    req(np.max(np.abs(baseline - frozen)) <= 1e-14, 'frozen training-mean baseline drift')
    source_shape = 0.0
    X = np.asarray(base['model']['shape']['coordinates'], dtype=np.float64)
    for g in p['geometrySelection']['selectedGeometries']:
        base_pred = np.asarray(trainer.predict(base['model'], g['geometry']), dtype=np.float64)
        pred = np.asarray(engine.predict_hybrid(materialized['model'], g['geometry'], trainer.predict), dtype=np.float64)
        source_shape = max(source_shape, float(np.max(np.abs(pred[3:] - base_pred[3:]))))
        q = np.asarray(trainer.idw_coords(g['geometry']), dtype=np.float64)
        d = float(np.min(np.linalg.norm(X - q, axis=1)))
        req(abs(d - float(g['nearestTrainingDistance'])) <= 1e-12 and d <= 0.6, f'source support-distance drift: {g["geometryId"]}')
    req(source_shape == 0.0, 'source shape invariance failed')
    return {'status':'PASS','maxTrainingExactMatchPrimaryAbsoluteLogError':max_primary,'maxTrainingShapePredictionChange':max_shape,'maxSourceShapePredictionChange':source_shape,'protectedValuesRead':False,'ordinal27ValuesRead':False}


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate'); v.add_argument('--contract', type=Path, required=True); v.add_argument('--repo-root', type=Path, required=True); v.add_argument('--materialized-dir', type=Path, required=True); v.add_argument('--base-model-dir', type=Path, required=True)
    c = sub.add_parser('cases'); c.add_argument('--contract', type=Path, required=True)
    e = sub.add_parser('evaluate'); e.add_argument('--contract', type=Path, required=True); e.add_argument('--cases-root', type=Path, required=True); e.add_argument('--materialized-dir', type=Path, required=True); e.add_argument('--base-model-dir', type=Path, required=True); e.add_argument('--representation-dir', type=Path, required=True); e.add_argument('--repo-root', type=Path, required=True); e.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    try:
        p = load(a.contract)
        if a.cmd == 'validate':
            result = training_parity(p, a.materialized_dir, a.base_model_dir, a.repo_root)
            print(json.dumps(result, sort_keys=True))
        elif a.cmd == 'cases':
            print(json.dumps(expected_cases(p), sort_keys=True, separators=(',', ':')))
        else:
            evaluate(p, a.cases_root, a.materialized_dir, a.base_model_dir, a.representation_dir, a.repo_root, a.output)
        return 0
    except Exception as error:
        print(json.dumps({'status':'REFUSED','reason':str(error)}, sort_keys=True), file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
