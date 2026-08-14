#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EVAL_RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-ordinal27-evaluation-recovery-v1/recovery-v1.json')
SCI_RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v4/recovery-v4.json')
V4_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v4/fresh_validation_v4.py')
TRAINER_REL = Path('review/level-b-v2-training-implementation-v3-densified58/train_v3.py')
MODEL_SHA = '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7'
RECOVERY_ID = 'level-b-v2-densified58-fresh-validation-ordinal27-evaluation-recovery-v1'

class Refusal(RuntimeError):
    pass

def req(c: bool, m: str) -> None:
    if not c:
        raise Refusal(m)

def canon(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def load(p: Path) -> dict[str, Any]:
    v = json.loads(p.read_text(encoding='utf-8'))
    req(isinstance(v, dict), f'object required: {p}')
    return v

def write(p: Path, v: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')

def module(name: str, p: Path):
    spec = importlib.util.spec_from_file_location(name, p)
    req(spec is not None and spec.loader is not None, f'cannot load {p}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def validate_eval_recovery(r: dict[str, Any]) -> None:
    req((r.get('schemaVersion'), r.get('recoveryId'), r.get('status'), r.get('governance'), r.get('sourceMainAtRecoveryFreeze')) == (
        1, RECOVERY_ID,
        'REVIEW_ONLY_POST_EXPOSURE_EVALUATION_LAYER_RECOVERY_NO_PROTECTED_ARTIFACT_READ_NO_SOLVER_NO_DOD_RESULT',
        'MYSTIC-STATE-0070', '4dc38cf791be3aee9448fc1ff01322d00bc6c489'), 'evaluation recovery identity drift')
    run = r['originalScientificRun']
    req((run['runId'], run['runAttempt'], run['headSha'], run['authorizationPullRequest'], run['authorizationReviewRunId']) == (
        31848052825, 1, '44ef4dee635745a8d9cabab25a5e01638307bdc9', 204, 31847790099), 'source run identity drift')
    req(run['preflightConclusion'] == 'success' and run['caseCount'] == run['successfulCaseCount'] == 24, 'source case success drift')
    req(run['syntaxCheckCount'] == run['solverInvocationCount'] == 24 and run['protectedValuesOpened'] is True and run['ordinal22ValuesOpened'] is False, 'source exposure accounting drift')
    req(run['evaluationJobId'] == 94920097388 and run['evaluationRefusal'] == 'model object kind drift' and run['runConclusion'] == 'failure' and run['evaluationArtifactWritten'] is False and run['artifactCount'] == 25, 'source evaluator refusal drift')
    req(run['scientificOrdinal'] == 27 and run['consumedSeeds'] == list(range(2101000073, 2101000097)), 'consumed identity drift')
    arts = r['immutableCaseArtifacts']
    req(len(arts) == 24 and len({x['caseId'] for x in arts}) == 24 and len({x['artifactId'] for x in arts}) == 24, 'case artifact universe drift')
    req({x['caseId'] for x in arts} == {f'v0070-o27-holdout-{g:02d}-b{b}' for g in range(1, 7) for b in range(1, 5)}, 'case artifact IDs drift')
    req(all(isinstance(x['artifactId'], int) and str(x['digest']).startswith('sha256:') and len(str(x['digest'])) == 71 for x in arts), 'case artifact binding malformed')
    f = r['frozenBindings']
    req((f['modelArtifactId'], f['modelArtifactDigest'], f['modelCanonicalSha256']) == (9229229366, 'sha256:f4c8c68a622f7c6bdc1b9177ad31d22f673becb1f286436d54b876ceece3668a', MODEL_SHA), 'frozen model binding drift')
    req((f['representationArtifactId'], f['representationArtifactDigest'], f['representationPackageSha256']) == (9208203541, 'sha256:2fe50ed674155f440322c92d28877f5c022f0cc5fa13e1e601596a9902482815', '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'), 'frozen representation binding drift')
    req(f['baseEvaluatorGitBlobSha'] == '085f040caa6aec53aace00381035115358b21239' and f['ordinal27EvaluatorGitBlobSha'] == 'fccabb0aa3d780573843be11a79f76bf50f4261b', 'evaluator binding drift')
    req(f['trainerGitBlobSha'] == '013768b9cb32050e698bc7b884921cbd5f1674e2' and f['trainingEngineGitBlobSha'] == 'bd0d20ebaaf77a8780dbfa021cfaa49bf3e2d0be', 'trainer binding drift')
    root = r['rootCause']
    req(root['kind'] == 'EVALUATOR_SCHEMA_VERIFICATION_BUG_ONLY' and root['discoveredWithoutConsultingProtectedNumericValues'] is True, 'root-cause boundary drift')
    req(root['frozenModelObjectKind'] == 'RIDGE_PRIMARY_IDW_SHAPE' and root['preRegisteredPredictionSemantics'] == 'EXACT_V3_TRAINER_V2_PREDICT_ON_FROZEN_MODEL_OBJECT', 'prediction semantics drift')
    scope = r['recoveryScope']
    req(scope['allowedChange'] == 'VERIFY_ALREADY_FROZEN_NESTED_MODEL_OBJECT_SCHEMA_THEN_REUSE_UNCHANGED_V4_EVALUATION_MATH', 'recovery scope drift')
    req(all(scope[k] is False for k in ('caseArtifactUniverseMayChange','modelMayChange','representationMayChange','geometryMayChange','definitionOfDoneMayChange','supportRuleMayChange','physicsMayChange','runtimeMayChange','solverMayRun','syntaxCheckMayRun','scientificRerun','scientificRetry','scientificResume','retuningAllowed')), 'forbidden recovery scope opened')
    req(all(v is False for v in r['reviewSurface'].values()), 'review surface opened')

def verify_nested_model(model: dict[str, Any], p: dict[str, Any]) -> None:
    req(model.get('modelSha256') == MODEL_SHA == p['sourceBindings']['modelCanonicalSha256'], 'model canonical identity drift')
    body = dict(model); body.pop('modelSha256', None)
    req(canon(body) == MODEL_SHA, 'model canonical self-hash drift')
    req(model.get('status') == 'TRAINING_ONLY_DENSIFIED58_MODEL_FROZEN_PENDING_FRESH_VALIDATION_SOURCE', 'model status drift')
    req(model.get('trainingGeometryCount') == 58 and model.get('protectedHoldoutRecordCount') == 0, 'model training universe drift')
    req(model.get('ordinal22ValuesRead') is False and model.get('protectedValidationAuthorized') is False, 'model protected boundary drift')
    spec = model.get('selectedSpec') or {}
    req((spec.get('familyId'), spec.get('kind'), spec.get('primaryBasis'), spec.get('primaryRidge'), spec.get('neighbors'), spec.get('power')) == (
        'ridge-primary-physical-compact-shape-idw-cos', 'RIDGE_PRIMARY_IDW_SHAPE', 'PHYSICAL_COMPACT_16_TERMS', 1e-05, 4, 1.0), 'selected model spec drift')
    m = model.get('model') or {}; primary = m.get('primary') or {}; shape = m.get('shape') or {}
    req(m.get('kind') == 'RIDGE_PRIMARY_IDW_SHAPE', 'model object kind drift')
    req((primary.get('kind'), primary.get('basis'), primary.get('ridge')) == ('RIDGE_PRIMARY', 'PHYSICAL_COMPACT_16_TERMS', 1e-05), 'primary predictor drift')
    req((shape.get('kind'), shape.get('neighbors'), shape.get('power')) == ('IDW_SHAPE', 4, 1.0), 'shape predictor drift')
    x = np.asarray(shape.get('coordinates'), dtype=np.float64)
    y = np.asarray(shape.get('targets'), dtype=np.float64)
    coef = np.asarray(primary.get('coefficients'), dtype=np.float64)
    scales = np.asarray(model.get('nullspaceCoefficientScales'), dtype=np.float64)
    req(x.shape == (58, 5) and y.shape == (58, 10) and coef.shape == (16, 3) and scales.shape == (10,), 'model array dimension drift')
    req(np.all(np.isfinite(x)) and np.all(np.isfinite(y)) and np.all(np.isfinite(coef)) and np.all(scales > 0), 'nonfinite model arrays')

def prepare_v4(eval_recovery: dict[str, Any], science_recovery: dict[str, Any], repo_root: Path):
    validate_eval_recovery(eval_recovery)
    v4 = module('ordinal27_v4_evaluator_recovery_base', repo_root / V4_REL)
    original = v4.patched_base
    def patched(r: dict[str, Any], rr: Path):
        b = original(r, rr)
        b.verify_model = verify_nested_model
        return b
    v4.patched_base = patched
    p = v4.effective_contract(science_recovery, repo_root)
    return v4, p

def validate_model_only(eval_recovery: dict[str, Any], science_recovery: dict[str, Any], model_dir: Path, repo_root: Path) -> dict[str, Any]:
    v4, p = prepare_v4(eval_recovery, science_recovery, repo_root)
    model = load(model_dir / 'model-artifact-v3-densified58.json')
    verify_nested_model(model, p)
    trainer = module('densified58_v3_model_schema_probe', repo_root / TRAINER_REL)
    geometry = p['geometrySelection']['selectedGeometries'][0]['geometry']
    pred = np.asarray(trainer.v2.predict(model['model'], geometry), dtype=np.float64)
    req(pred.shape == (13,) and np.all(np.isfinite(pred)), 'frozen model prediction probe failed')
    return {'status':'PASS','recoveryId':RECOVERY_ID,'modelSha256':MODEL_SHA,'modelObjectKind':model['model']['kind'],'predictionEngine':'EXACT_V3_TRAINER_V2_PREDICT_ON_FROZEN_MODEL_OBJECT','predictionFeatureCount':13,'protectedCaseArtifactsRead':False,'solverExecutionCount':0}

def evaluate(eval_recovery: dict[str, Any], science_recovery: dict[str, Any], cases_root: Path, model_dir: Path, representation_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    v4, _ = prepare_v4(eval_recovery, science_recovery, repo_root)
    result = v4.evaluate(science_recovery, cases_root, model_dir, representation_dir, repo_root, output)
    result.pop('resultSha256', None)
    result['evaluationRecoveryId'] = RECOVERY_ID
    result['sourceScientificRunId'] = 31848052825
    result['sourceScientificRunAttempt'] = 1
    result['sourceCaseArtifactCount'] = 24
    result['sourceSolverInvocationCount'] = 24
    result['additionalSolverInvocationCount'] = 0
    result['scientificRerunPerformed'] = False
    result['scientificRetryPerformed'] = False
    result['scientificResumePerformed'] = False
    result['modelRetuningPerformed'] = False
    result['resultSha256'] = canon(result)
    write(output, result)
    return result

def main() -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate-model'); v.add_argument('--evaluation-recovery', type=Path, required=True); v.add_argument('--scientific-recovery', type=Path, required=True); v.add_argument('--model-dir', type=Path, required=True); v.add_argument('--repo-root', type=Path, default=ROOT)
    e = sub.add_parser('evaluate'); e.add_argument('--evaluation-recovery', type=Path, required=True); e.add_argument('--scientific-recovery', type=Path, required=True); e.add_argument('--cases-root', type=Path, required=True); e.add_argument('--model-dir', type=Path, required=True); e.add_argument('--representation-dir', type=Path, required=True); e.add_argument('--repo-root', type=Path, required=True); e.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    try:
        er = load(a.evaluation_recovery); sr = load(a.scientific_recovery)
        if a.cmd == 'validate-model':
            print(json.dumps(validate_model_only(er, sr, a.model_dir, a.repo_root), sort_keys=True))
        else:
            evaluate(er, sr, a.cases_root, a.model_dir, a.representation_dir, a.repo_root, a.output)
        return 0
    except Exception as exc:
        print(json.dumps({'status':'REFUSED','reason':str(exc)}, sort_keys=True), file=__import__('sys').stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
