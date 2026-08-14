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
EVAL_V1_REL = Path('review/level-b-v2-densified58-fresh-validation-ordinal27-evaluation-recovery-v1/fresh_validation_evaluation_recovery_v1.py')
EVAL_V1_RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-ordinal27-evaluation-recovery-v1/recovery-v1.json')
SCI_RECOVERY_REL = Path('review/level-b-v2-densified58-fresh-validation-recovery-v4/recovery-v4.json')
TRAINER_REL = Path('review/level-b-v2-training-implementation-v3-densified58/train_v3.py')
STAGE2_REL = Path('review/tier2-stage2-protected-holdout-v1/stage2_v1.py')
MODEL_SHA = '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7'
RECOVERY_ID = 'level-b-v2-densified58-fresh-validation-ordinal27-evaluation-recovery-v3'
COMPATIBILITY_ID = 'VIRTUAL_SHAPEFITX_TO_FROZEN_NESTED_SHAPE_COORDINATES_ONLY'


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


class FrozenNestedModelCompatibilityView(dict):
    """Expose one legacy lookup without changing the serialized frozen model."""

    def __getitem__(self, key):
        if key == 'shapeFitX':
            shape = dict.__getitem__(self, 'shape')
            req(isinstance(shape, dict), 'nested shape object required')
            return shape['coordinates']
        return dict.__getitem__(self, key)


def compatibility_view(model: dict[str, Any]) -> dict[str, Any]:
    req(model.get('modelSha256') == MODEL_SHA, 'model identity drift before compatibility view')
    nested = model.get('model')
    req(isinstance(nested, dict), 'nested frozen model object required')
    shape = nested.get('shape') or {}
    req((shape.get('kind'), shape.get('neighbors'), shape.get('power')) == ('IDW_SHAPE', 4, 1.0), 'nested shape predictor drift')
    coords = np.asarray(shape.get('coordinates'), dtype=np.float64)
    req(coords.shape == (58, 5) and np.all(np.isfinite(coords)), 'nested support-coordinate shape drift')
    out = dict(model)
    out['model'] = FrozenNestedModelCompatibilityView(nested)
    req('shapeFitX' not in out['model'], 'compatibility lookup became serialized model field')
    req(np.array_equal(np.asarray(out['model']['shapeFitX'], dtype=np.float64), coords), 'virtual support coordinate mismatch')
    body = dict(out); got = body.pop('modelSha256', None)
    req(got == MODEL_SHA and canon(body) == MODEL_SHA, 'compatibility view changed canonical frozen model')
    return out


def prepare_v4(eval_v1_recovery: dict[str, Any], science_recovery: dict[str, Any], repo_root: Path):
    v1 = module('ordinal27_eval_recovery_v1', repo_root / EVAL_V1_REL)
    v1.validate_eval_recovery(eval_v1_recovery)
    v4, p = v1.prepare_v4(eval_v1_recovery, science_recovery, repo_root)
    prior_patched_base = v4.patched_base

    def patched_base(r: dict[str, Any], rr: Path):
        base = prior_patched_base(r, rr)
        original_load = base.load

        def load_with_frozen_model_compatibility(path: Path):
            obj = original_load(path)
            if Path(path).name == 'model-artifact-v3-densified58.json':
                return compatibility_view(obj)
            return obj

        base.load = load_with_frozen_model_compatibility
        return base

    v4.patched_base = patched_base
    return v1, v4, p


def validate_model_only(eval_v1_recovery: dict[str, Any], science_recovery: dict[str, Any], model_dir: Path, repo_root: Path) -> dict[str, Any]:
    v1, _, p = prepare_v4(eval_v1_recovery, science_recovery, repo_root)
    original = v1.load(model_dir / 'model-artifact-v3-densified58.json')
    v1.verify_nested_model(original, p)
    compat = compatibility_view(original)
    req(canon({k: v for k, v in compat.items() if k != 'modelSha256'}) == MODEL_SHA, 'compatibility canonical-hash proof failed')

    trainer = module('densified58_v3_model_schema_probe_v2', repo_root / TRAINER_REL)
    stage2 = module('frozen_stage2_support_coordinate_probe_v2', repo_root / STAGE2_REL)
    for entry in p['geometrySelection']['selectedGeometries']:
        geometry = entry['geometry']
        a = np.asarray(trainer.v2.idw_coords(geometry), dtype=np.float64)
        b = np.asarray(stage2.support_coords(geometry), dtype=np.float64)
        req(a.shape == b.shape == (5,) and np.array_equal(a, b), f'support-coordinate semantic drift: {entry["geometryId"]}')
        pred = np.asarray(trainer.v2.predict(original['model'], geometry), dtype=np.float64)
        req(pred.shape == (13,) and np.all(np.isfinite(pred)), f'frozen prediction probe failed: {entry["geometryId"]}')
    support = np.asarray(compat['model']['shapeFitX'], dtype=np.float64)
    req(np.array_equal(support, np.asarray(original['model']['shape']['coordinates'], dtype=np.float64)), 'legacy support lookup not exact nested coordinates')
    return {
        'status': 'PASS',
        'recoveryId': RECOVERY_ID,
        'compatibilityId': COMPATIBILITY_ID,
        'modelSha256': MODEL_SHA,
        'serializedModelChanged': False,
        'virtualLegacyKeyPresentInSerializedKeys': False,
        'supportCoordinateCount': int(support.shape[0]),
        'supportCoordinateDimension': int(support.shape[1]),
        'predictionEngine': 'EXACT_V3_TRAINER_V2_PREDICT_ON_ORIGINAL_FROZEN_NESTED_MODEL_OBJECT',
        'supportCoordinateSemantics': 'EXACT_STAGE2_SUPPORT_COORDS_EQUALS_V2_IDW_COORDS',
        'protectedCaseArtifactsRead': False,
        'solverExecutionCount': 0,
    }


def evaluate(eval_v1_recovery: dict[str, Any], science_recovery: dict[str, Any], cases_root: Path, model_dir: Path, representation_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    _, v4, _ = prepare_v4(eval_v1_recovery, science_recovery, repo_root)
    result = v4.evaluate(science_recovery, cases_root, model_dir, representation_dir, repo_root, output)
    result.pop('resultSha256', None)
    result['evaluationRecoveryId'] = RECOVERY_ID
    result['evaluationCompatibilityId'] = COMPATIBILITY_ID
    result['previousEvaluationRecoveryId'] = 'level-b-v2-densified58-fresh-validation-ordinal27-evaluation-recovery-v1'
    result['previousEvaluationRecoveryV1RunId'] = 31849706647
    result['previousEvaluationRecoveryV2RunId'] = 31850828379
    result['sourceScientificRunId'] = 31848052825
    result['sourceScientificRunAttempt'] = 1
    result['sourceCaseArtifactCount'] = 24
    result['sourceSolverInvocationCount'] = 24
    result['additionalSolverInvocationCount'] = 0
    result['scientificRerunPerformed'] = False
    result['scientificRetryPerformed'] = False
    result['scientificResumePerformed'] = False
    result['modelRetuningPerformed'] = False
    result['serializedFrozenModelChanged'] = False
    result['resultSha256'] = canon(result)
    write(output, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate-model'); v.add_argument('--evaluation-recovery-v1', type=Path, required=True); v.add_argument('--scientific-recovery', type=Path, required=True); v.add_argument('--model-dir', type=Path, required=True); v.add_argument('--repo-root', type=Path, default=ROOT)
    e = sub.add_parser('evaluate'); e.add_argument('--evaluation-recovery-v1', type=Path, required=True); e.add_argument('--scientific-recovery', type=Path, required=True); e.add_argument('--cases-root', type=Path, required=True); e.add_argument('--model-dir', type=Path, required=True); e.add_argument('--representation-dir', type=Path, required=True); e.add_argument('--repo-root', type=Path, required=True); e.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    try:
        er = load(a.evaluation_recovery_v1); sr = load(a.scientific_recovery)
        if a.cmd == 'validate-model':
            print(json.dumps(validate_model_only(er, sr, a.model_dir, a.repo_root), sort_keys=True))
        else:
            evaluate(er, sr, a.cases_root, a.model_dir, a.representation_dir, a.repo_root, a.output)
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True), file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
