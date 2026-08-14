#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_REL = Path('review/level-b-v2-densified58-fresh-validation-v1/contract-v1.json')
OLD_STAGE2_REL = Path('review/tier2-stage2-protected-holdout-v1/stage2_v1.py')
V3_TRAINER_REL = Path('review/level-b-v2-training-implementation-v3-densified58/train_v3.py')
CONTRACT_ID = 'level-b-v2-densified58-fresh-protected-validation-v1'
MODEL_SHA = '91ae5811e55b3d4ef872ab672f006c4b383c6581a53de67cd018b6eb2666f9a7'
REP_SHA = '2491ac91ed924f2ba69b37ea20f48d63f51d41146cd9fe50e0bd63bfb315a763'
GRID_SHA = 'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
CHANNELS = ('photopicLuminanceCdM2','scotopicLuminanceScotCdM2','johnsonVEffectiveRadiance_mW_m2_nm_sr')


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def canon(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def validate_contract(p: dict[str, Any]) -> None:
    req((p.get('schemaVersion'), p.get('contractId'), p.get('status'), p.get('governance')) == (
        1,
        CONTRACT_ID,
        'REVIEW_ONLY_FRESH_PROTECTED_VALIDATION_PREREGISTRATION_NO_AUTHORIZATION_NO_VALUES_OPENED',
        'MYSTIC-STATE-0070',
    ), 'contract identity drift')
    req(p.get('sourceMainAtFreeze') == '147eaca24e51fe7e2e0d8c3fb329055f28d1c586', 'contract source-main drift')
    gs = p['geometrySelection']
    req(gs['selectedGeometryCount'] == 6 and len(gs['selectedGeometries']) == 6, 'geometry count drift')
    req(gs['targetValuesMayInfluenceSelection'] is False and gs['modelPredictionsMayInfluenceSelection'] is False and gs['openedOrdinal22TargetValuesMayInfluenceSelection'] is False, 'geometry-only selection boundary opened')
    env = p['executionEnvelope']
    req((env['candidateScientificOrdinal'], env['geometryCount'], env['blocksPerGeometry'], env['caseCount'], env['photonHistoriesPerBlock'], env['configuredPhotonHistories']) == (24, 6, 4, 24, 40_000_000, 960_000_000), 'execution envelope drift')
    req(env['reservedSeeds'] == list(range(2101000001, 2101000025)), 'reserved seed drift')
    req(env['scientificOrdinalAllocated'] is False, 'preregistration unexpectedly allocated ordinal')
    for key in ('githubRerunAllowed','retryAllowed','resumeAllowed','adaptiveExtraBlocksAllowed','adaptivePointReplacementAllowed'):
        req(env[key] is False, f'continuation boundary opened: {key}')
    me = p['modelAndEvaluation']
    req(me['frozenTrainingMeanBaselineTransformedPrimary'] == [0.3993901995212697,1.7062844994448103,-3.8475190646906268], 'frozen baseline vector drift')
    req(me['aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline'] == 0.7, 'baseline ratio threshold drift')
    req((me['positiveChannelAbsoluteMeanSignedLogBiasMax'],me['positiveChannelMedianAbsoluteLogErrorMax'],me['positiveChannelWorstAbsoluteLogErrorMax'],me['positiveChannelWorstUncertaintyNormalizedErrorMax']) == (0.08,0.15,0.35,3.0), 'primary DoD drift')
    req((me['shapeMedianPerCaseNrmseMax'],me['shapeWorstPerCaseNrmseMax'],me['shapeWorstSingleCoefficientNormalizedErrorMax']) == (0.75,1.25,3.0), 'shape DoD drift')
    req(me['surrogateLogErrorBudgetOneSigma'] == 0.12 and me['validatedSupportNearestDistanceMaxInclusive'] == 0.6, 'support/uncertainty drift')
    req(me['p90OrP95PrincipalMetricAllowed'] is False and me['noRetuningAfterHoldoutOpening'] is True and me['epsilonSubstitutionAllowed'] is False and me['exactZeroSemanticsPreserved'] is True, 'evaluation semantics drift')
    sb = p['sourceBindings']
    req((sb['modelArtifactId'], sb['modelCanonicalSha256']) == (9229229366, MODEL_SHA), 'model binding drift')
    req(sb['trainingSelectionCanonicalSha256'] == 'bed37ced8faa837b7adbd532fe7358e447aea76a1a4f064d4bdcef7cb6326a8a', 'selection binding drift')
    for key, value in p['boundaries'].items():
        req(value is False, f'closed prereg boundary opened: {key}')


def expected_cases(p: dict[str, Any]) -> list[dict[str, Any]]:
    validate_contract(p)
    geoms = p['geometrySelection']['selectedGeometries']
    seeds = p['executionEnvelope']['reservedSeeds']
    out: list[dict[str, Any]] = []
    cursor = 0
    for g in geoms:
        for block in range(1, 5):
            seed = int(seeds[cursor]); cursor += 1
            out.append({
                'caseId': f"v0070-{g['geometryId']}-b{block}",
                'geometryId': g['geometryId'],
                'block': block,
                'seed': seed,
                'photonHistories': 40_000_000,
                'alisSpectralImportanceSamplingNm': 550.0,
            })
    req(cursor == 24 and len(out) == 24, 'case construction drift')
    req([x['seed'] for x in out] == list(range(2101000001, 2101000025)), 'case seed order drift')
    return out


def verify_model(model: dict[str, Any], p: dict[str, Any]) -> None:
    req(model.get('modelSha256') == MODEL_SHA == p['sourceBindings']['modelCanonicalSha256'], 'model canonical identity drift')
    body = dict(model); body.pop('modelSha256', None)
    req(canon(body) == MODEL_SHA, 'model canonical self-hash drift')
    req(model.get('status') == 'TRAINING_ONLY_DENSIFIED58_MODEL_FROZEN_PENDING_FRESH_VALIDATION_SOURCE', 'model status drift')
    req(model.get('trainingGeometryCount') == 58 and model.get('protectedHoldoutRecordCount') == 0, 'model training universe drift')
    req(model.get('ordinal22ValuesRead') is False and model.get('protectedValidationAuthorized') is False, 'model protected boundary drift')
    spec = model.get('selectedSpec') or {}
    req((spec.get('familyId'),spec.get('kind'),spec.get('primaryBasis'),spec.get('primaryRidge'),spec.get('neighbors'),spec.get('power')) == (
        'ridge-primary-physical-compact-shape-idw-cos','RIDGE_PRIMARY_IDW_SHAPE','PHYSICAL_COMPACT_16_TERMS',1e-05,4,1.0
    ), 'selected model spec drift')
    m = model.get('model') or {}
    req(m.get('kind') == 'RIDGE_PRIMARY_IDW_SHAPE' and m.get('primaryBasis') == 'PHYSICAL_COMPACT_16_TERMS', 'model object kind drift')
    req(m.get('shapeKind') == 'IDW_COS' and m.get('shapeNeighbors') == 4 and m.get('shapePower') == 1.0, 'shape predictor drift')
    x = np.asarray(m.get('shapeFitX'), dtype=np.float64)
    y = np.asarray(m.get('shapeFitY'), dtype=np.float64)
    coef = np.asarray(m.get('primaryCoef'), dtype=np.float64)
    scales = np.asarray(model.get('nullspaceCoefficientScales'), dtype=np.float64)
    req(x.shape == (58,5) and y.shape == (58,10) and coef.shape == (16,3) and scales.shape == (10,), 'model array dimension drift')
    req(np.all(np.isfinite(x)) and np.all(np.isfinite(y)) and np.all(np.isfinite(coef)) and np.all(scales > 0), 'nonfinite model arrays')


def predict(model: dict[str, Any], geometry: dict[str, Any], repo_root: Path) -> np.ndarray:
    trainer = module('densified58_v3_predictor', repo_root / V3_TRAINER_REL)
    pred = np.asarray(trainer.v2.predict(model['model'], geometry), dtype=np.float64)
    req(pred.shape == (13,) and np.all(np.isfinite(pred)), 'nonfinite/wrong-size frozen prediction')
    return pred


def locate_cases(root: Path, p: dict[str, Any]) -> dict[str, Path]:
    wanted = {x['caseId'] for x in expected_cases(p)}
    found: dict[str, Path] = {}
    for f in root.rglob('case-result.json'):
        try:
            r = load(f)
        except Exception:
            continue
        cid = r.get('caseId')
        if cid in wanted:
            req(cid not in found, f'duplicate case artifact: {cid}')
            found[cid] = f.parent
    req(set(found) == wanted, f'case artifact universe drift missing={sorted(wanted-set(found))}')
    return found


def summarize_records(records: list[dict[str, Any]], p: dict[str, Any]) -> dict[str, Any]:
    req(len(records) == 6, 'exact six geometry records required')
    me = p['modelAndEvaluation']
    channel_summary: dict[str, Any] = {}
    all_abs: list[float] = []
    all_baseline_abs: list[float] = []
    all_channel_pass = True
    for channel in CHANNELS:
        rows = [r['channelErrors'][channel] for r in records]
        if any(x['absoluteLogError'] is None or x['uncertaintyNormalizedError'] is None or x['baselineAbsoluteLogError'] is None for x in rows):
            channel_summary[channel] = {
                'absoluteMeanSignedLogBias': None,
                'medianAbsoluteLogError': None,
                'worstAbsoluteLogError': None,
                'worstUncertaintyNormalizedError': None,
                'passes': False,
            }
            all_channel_pass = False
            continue
        signed = np.asarray([x['signedLogError'] for x in rows], dtype=np.float64)
        absolute = np.asarray([x['absoluteLogError'] for x in rows], dtype=np.float64)
        uncertainty = np.asarray([x['uncertaintyNormalizedError'] for x in rows], dtype=np.float64)
        baseline = np.asarray([x['baselineAbsoluteLogError'] for x in rows], dtype=np.float64)
        summary = {
            'absoluteMeanSignedLogBias': abs(float(np.mean(signed))),
            'medianAbsoluteLogError': float(np.median(absolute)),
            'worstAbsoluteLogError': float(np.max(absolute)),
            'worstUncertaintyNormalizedError': float(np.max(uncertainty)),
        }
        summary['passes'] = (
            summary['absoluteMeanSignedLogBias'] <= me['positiveChannelAbsoluteMeanSignedLogBiasMax'] and
            summary['medianAbsoluteLogError'] <= me['positiveChannelMedianAbsoluteLogErrorMax'] and
            summary['worstAbsoluteLogError'] <= me['positiveChannelWorstAbsoluteLogErrorMax'] and
            summary['worstUncertaintyNormalizedError'] <= me['positiveChannelWorstUncertaintyNormalizedErrorMax']
        )
        all_channel_pass = all_channel_pass and summary['passes']
        channel_summary[channel] = summary
        all_abs.extend(absolute.tolist())
        all_baseline_abs.extend(baseline.tolist())
    support_pass = all(bool(r['insideValidatedSupport']) for r in records)
    shape_values = [float(r['shapePerCaseNrmse']) for r in records]
    shape_single = [float(r['shapeWorstSingleCoefficientNormalizedError']) for r in records]
    shape_median = float(np.median(np.asarray(shape_values)))
    shape_worst = max(shape_values)
    single_worst = max(shape_single)
    shape_pass = (
        shape_median <= me['shapeMedianPerCaseNrmseMax'] and
        shape_worst <= me['shapeWorstPerCaseNrmseMax'] and
        single_worst <= me['shapeWorstSingleCoefficientNormalizedErrorMax']
    )
    aggregate = float(np.mean(np.asarray(all_abs))) if len(all_abs) == 18 else None
    baseline = float(np.mean(np.asarray(all_baseline_abs))) if len(all_baseline_abs) == 18 else None
    baseline_ratio = (aggregate / baseline) if aggregate is not None and baseline is not None and baseline > 0 else None
    baseline_pass = baseline_ratio is not None and baseline_ratio <= me['aggregatePrimaryMeanAbsoluteLogErrorMustBeAtMostFractionOfFrozenTrainingMeanBaseline']
    passed = support_pass and all_channel_pass and shape_pass and baseline_pass
    return {
        'channelSummary': channel_summary,
        'aggregatePrimaryMeanAbsoluteLogError': aggregate,
        'frozenTrainingMeanBaselinePrimaryMeanAbsoluteLogErrorOnHoldout': baseline,
        'aggregateToBaselineFraction': baseline_ratio,
        'supportPass': support_pass,
        'shapeMedianPerCaseNrmse': shape_median,
        'shapeWorstPerCaseNrmse': shape_worst,
        'shapeWorstSingleCoefficientNormalizedError': single_worst,
        'shapePass': shape_pass,
        'baselinePass': baseline_pass,
        'definitionOfDonePassed': passed,
    }


def evaluate(p: dict[str, Any], cases_root: Path, model_dir: Path, representation_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    validate_contract(p)
    model = load(model_dir / 'model-artifact-v3-densified58.json')
    verify_model(model, p)
    npz = representation_dir / 'spectral-representation-v2.npz'
    req(sha_file(npz) == REP_SHA, 'representation package SHA drift')
    with np.load(npz, allow_pickle=False) as z:
        W = np.asarray(z['integration_weights'], dtype=np.float64)
        components = np.asarray(z['selected_nullspace_pca_components'], dtype=np.float64)
        grand = np.asarray(z['grand_mean_nullspace_residual'], dtype=np.float64)
    req(W.shape == (3,8001) and components.shape == (10,8001) and grand.shape == (8001,), 'representation array shape drift')
    scales = np.asarray(model['nullspaceCoefficientScales'], dtype=np.float64)
    old = module('frozen_stage2_truth_math', repo_root / OLD_STAGE2_REL)
    case_dirs = locate_cases(cases_root, p)
    expected = {x['caseId']: x for x in expected_cases(p)}
    grouped: dict[str, list[tuple[int,np.ndarray]]] = {g['geometryId']: [] for g in p['geometrySelection']['selectedGeometries']}
    for cid, case in expected.items():
        d = case_dirs[cid]
        result = load(d / 'case-result.json')
        got_hash = result.get('contentSha256'); body = dict(result); body.pop('contentSha256', None)
        req(got_hash == canon(body), f'case result self-hash drift: {cid}')
        req(result.get('status') == 'COMPLETED' and result.get('caseId') == cid and result.get('workflowRunAttempt') == 1, f'case completion drift: {cid}')
        req(result.get('retryPerformed') is False and result.get('resumePerformed') is False and result.get('githubRerun') is False, f'case retry/resume drift: {cid}')
        req(result.get('protectedHoldoutValueExposed') is True, f'case protected-value marker drift: {cid}')
        wl, radiance, _ = old.parse_spectrum(d / 'mc.rad.spc')
        swl, _, _ = old.parse_spectrum(d / 'mc.rad.std.spc')
        req(np.array_equal(wl, swl), f'radiance/std wavelength mismatch: {cid}')
        grouped[case['geometryId']].append((int(case['block']), radiance))
    model_x = np.asarray(model['model']['shapeFitX'], dtype=np.float64)
    baseline_vector = np.asarray(p['modelAndEvaluation']['frozenTrainingMeanBaselineTransformedPrimary'], dtype=np.float64)
    records: list[dict[str, Any]] = []
    geometry_map = {g['geometryId']: g['geometry'] for g in p['geometrySelection']['selectedGeometries']}
    for gid in [g['geometryId'] for g in p['geometrySelection']['selectedGeometries']]:
        rows = sorted(grouped[gid], key=lambda x: x[0])
        req([x[0] for x in rows] == [1,2,3,4], f'exact four blocks required: {gid}')
        channels: list[np.ndarray] = []
        coeffs: list[np.ndarray] = []
        for _, y in rows:
            residual, channel = old.projection_residual(y, W)
            coeff = (residual - grand) @ components.T
            req(coeff.shape == (10,) and np.all(np.isfinite(coeff)), f'direct PCA drift: {gid}')
            channels.append(channel)
            coeffs.append(coeff)
        ca = np.vstack(channels); pa = np.vstack(coeffs)
        channel_stats = {CHANNELS[j]: old.stats(ca[:,j]) for j in range(3)}
        coeff_stats = [old.stats(pa[:,j]) for j in range(10)]
        geometry = geometry_map[gid]
        pred = predict(model, geometry, repo_root)
        coord = np.asarray(old.support_coords(geometry), dtype=np.float64)
        nearest = float(np.min(np.linalg.norm(model_x - coord, axis=1)))
        in_box = bool(old.in_box(geometry))
        zero_primary = any(float(channel_stats[k]['mean']) <= 0.0 for k in CHANNELS)
        inside = in_box and nearest <= p['modelAndEvaluation']['validatedSupportNearestDistanceMaxInclusive'] and not zero_primary
        channel_errors: dict[str, Any] = {}
        for j, channel in enumerate(CHANNELS):
            truth_mean = float(channel_stats[channel]['mean'])
            rse = channel_stats[channel]['relativeStandardError']
            if truth_mean <= 0.0 or rse is None:
                channel_errors[channel] = {'signedLogError':None,'absoluteLogError':None,'uncertaintyNormalizedError':None,'baselineAbsoluteLogError':None}
                continue
            truth_log = math.log(truth_mean)
            signed = float(pred[j] - truth_log)
            absolute = abs(signed)
            denom = math.sqrt(math.log1p(float(rse))**2 + p['modelAndEvaluation']['surrogateLogErrorBudgetOneSigma']**2)
            channel_errors[channel] = {
                'signedLogError': signed,
                'absoluteLogError': absolute,
                'uncertaintyNormalizedError': absolute / denom,
                'baselineAbsoluteLogError': abs(float(baseline_vector[j]) - truth_log),
            }
        shape_errors: list[float] = []
        for j in range(10):
            direct_mean = float(coeff_stats[j]['mean']); direct_se = float(coeff_stats[j]['standardError'])
            scale = float(scales[j])
            truth_norm = direct_mean / scale
            se_norm = direct_se / scale
            shape_errors.append(abs(float(pred[3+j]) - truth_norm) / math.sqrt(1.0 + se_norm*se_norm))
        shape_arr = np.asarray(shape_errors, dtype=np.float64)
        record = {
            'geometryId': gid,
            'geometry': geometry,
            'nearestFrozenTrainingSupportDistance': nearest,
            'insideDesignBox': in_box,
            'exactZeroPrimaryTruthObserved': zero_primary,
            'insideValidatedSupport': inside,
            'directIntegratedChannels': channel_stats,
            'directNullspacePcaCoefficients': coeff_stats,
            'predictedTransformedTargets': pred.tolist(),
            'channelErrors': channel_errors,
            'shapePerCaseNrmse': float(np.sqrt(np.mean(shape_arr*shape_arr))),
            'shapeWorstSingleCoefficientNormalizedError': float(np.max(shape_arr)),
        }
        records.append(record)
    summary = summarize_records(records, p)
    passed = bool(summary['definitionOfDonePassed'])
    result = {
        'schemaVersion': 1,
        'stageId': 'LEVEL_B_V2_DENSIFIED58_FRESH_PROTECTED_VALIDATION_EVALUATION_V1',
        'status': 'PASS_FROZEN_FRESH_DOD' if passed else 'FAIL_FROZEN_FRESH_DOD_NO_RETUNING',
        'governance': 'MYSTIC-STATE-0070',
        'contractId': p['contractId'],
        'modelSha256': model['modelSha256'],
        'representationPackageSha256': REP_SHA,
        'geometryCount': 6,
        'caseCount': 24,
        'configuredPhotonHistories': 960_000_000,
        'records': records,
        **summary,
        'frozenTrainingMeanBaselineTransformedPrimary': baseline_vector.tolist(),
        'p90OrP95Used': False,
        'retuningPerformed': False,
        'protectedHoldoutValuesRead': True,
        'ordinal22ValuesRead': False,
        'modelChangedAfterHoldoutOpening': False,
        'productionPromotionAuthorized': False,
        'workerBLaneReactivated': False,
        'workerCLaneReactivated': False,
        'freshValidationSourceMayBeReusedAfterRetuningIfFailed': False,
    }
    result['resultSha256'] = canon(result)
    write(output, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('validate'); v.add_argument('--contract', type=Path, required=True)
    c = sub.add_parser('cases'); c.add_argument('--contract', type=Path, required=True)
    e = sub.add_parser('evaluate'); e.add_argument('--contract', type=Path, required=True); e.add_argument('--cases-root', type=Path, required=True); e.add_argument('--model-dir', type=Path, required=True); e.add_argument('--representation-dir', type=Path, required=True); e.add_argument('--repo-root', type=Path, required=True); e.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    try:
        p = load(args.contract)
        if args.cmd == 'validate':
            validate_contract(p); print(json.dumps({'status':'PASS','caseCount':len(expected_cases(p)),'protectedValuesRead':False}, sort_keys=True))
        elif args.cmd == 'cases':
            print(json.dumps(expected_cases(p), sort_keys=True, separators=(',', ':')))
        else:
            evaluate(p, args.cases_root, args.model_dir, args.representation_dir, args.repo_root, args.output)
        return 0
    except Exception as error:
        print(json.dumps({'status':'REFUSED','reason':str(error)}, sort_keys=True), file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
