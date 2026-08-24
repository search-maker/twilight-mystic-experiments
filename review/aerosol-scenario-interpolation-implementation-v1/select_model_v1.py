#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

STAGE_ID = 'aerosol-scenario-interpolation-validation-v1'
EXPECTED_ORDINAL = 38
EXPECTED_CELLS = 24
CHANNELS = (
    'photopicLuminanceCdM2',
    'scotopicLuminanceScotCdM2',
    'johnsonVEffectiveRadiance_mW_m2_nm_sr',
)
CONTRASTS = (
    'continental_vs_native',
    'maritime_vs_native',
    'desert_vs_native',
    'desert_spheroids_vs_native',
)
TARGET_NAMES = tuple(f'{contrast}|{channel}' for contrast in CONTRASTS for channel in CHANNELS)


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def canonical_sha(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def load_json_bytes(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw.decode('utf-8'))
    req(isinstance(value, dict), 'JSON object required')
    return value


def coordinate(geometry: dict[str, Any]) -> np.ndarray:
    return np.asarray([
        (float(geometry['sunDepressionDeg']) - 2.0) / 8.5,
        (float(geometry['targetAltitudeDeg']) - 5.0) / 75.0,
        (math.cos(math.radians(float(geometry['relativeAzimuthDeg']))) + 1.0) / 2.0,
        (float(geometry['aod550']) - 0.05) / 0.35,
    ], dtype=np.float64)


def extract_training(index: dict[str, Any]) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray]:
    req(index.get('scientificOrdinal') == EXPECTED_ORDINAL, 'ordinal drift')
    req(index.get('analysisCellCount') == EXPECTED_CELLS, 'cell-count drift')
    cells = index.get('cells')
    req(isinstance(cells, list) and len(cells) == EXPECTED_CELLS, 'exact 24 cells required')
    records: list[dict[str, Any]] = []
    X: list[np.ndarray] = []
    Y: list[list[float]] = []
    seen: set[str] = set()
    for cell in cells:
        cid = str(cell['analysisCellId'])
        req(cid not in seen, 'duplicate analysis cell')
        seen.add(cid)
        geom = {
            'sunDepressionDeg': float(cell['sunDepressionDeg']),
            'targetAltitudeDeg': float(cell['targetAltitudeDeg']),
            'relativeAzimuthDeg': float(cell['relativeAzimuthDeg']),
            'aod550': float(cell['aod550']),
        }
        row: list[float] = []
        for contrast in CONTRASTS:
            for channel in CHANNELS:
                entry = cell['primary'][channel][contrast]
                req(entry.get('status') == 'FINITE_THREE_REPLICATES', f'nonfinite training row: {cid}/{contrast}/{channel}')
                values = entry.get('replicateValues')
                req(isinstance(values, list) and len(values) == 3 and all(math.isfinite(float(v)) for v in values), 'three finite replicates required')
                mean = float(entry['mean'])
                req(math.isfinite(mean), 'finite mean required')
                req(abs(mean - sum(float(v) for v in values) / 3.0) <= 5e-13, 'mean/replicate mismatch')
                row.append(mean)
        records.append({'analysisCellId': cid, 'geometry': geom})
        X.append(coordinate(geom))
        Y.append(row)
    order = sorted(range(len(records)), key=lambda i: records[i]['analysisCellId'])
    records = [records[i] for i in order]
    Xa = np.vstack([X[i] for i in order])
    Ya = np.asarray([Y[i] for i in order], dtype=np.float64)
    req(Xa.shape == (24, 4) and Ya.shape == (24, 12), 'training matrix shape drift')
    req(np.isfinite(Xa).all() and np.isfinite(Ya).all(), 'nonfinite training matrix')
    return records, Xa, Ya


def candidate_specs(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    selection = protocol['trainingOnlyInterpolatorSelection']
    specs: list[dict[str, Any]] = []
    for family in selection['candidateFamilies']:
        if family['family'] == 'IDW_COS_4D':
            for k in family['neighbors']:
                for p in family['powers']:
                    specs.append({'candidateId': f'idw-k{int(k)}-p{float(p):g}', 'family': 'IDW_COS_4D', 'neighbors': int(k), 'power': float(p), 'complexityRank': int(family['complexityRank'])})
        elif family['family'] == 'QUADRATIC_RIDGE_COS_4D':
            for ridge in family['ridge']:
                specs.append({'candidateId': f'quad-ridge-{float(ridge):.12g}', 'family': 'QUADRATIC_RIDGE_COS_4D', 'ridge': float(ridge), 'complexityRank': int(family['complexityRank'])})
        else:
            raise Refusal(f'unknown candidate family: {family["family"]}')
    req(len(specs) == 17, 'candidate cardinality drift')
    req(len({s['candidateId'] for s in specs}) == len(specs), 'duplicate candidate id')
    return specs


def quadratic_design(X: np.ndarray) -> np.ndarray:
    req(X.ndim == 2 and X.shape[1] == 4, '4D matrix required')
    cols = [np.ones(X.shape[0], dtype=np.float64)]
    cols += [X[:, j] for j in range(4)]
    cols += [X[:, j] ** 2 for j in range(4)]
    cols += [X[:, i] * X[:, j] for i in range(4) for j in range(i + 1, 4)]
    out = np.column_stack(cols)
    req(out.shape[1] == 15, 'quadratic basis cardinality drift')
    return out


def fit_model(spec: dict[str, Any], X: np.ndarray, Y: np.ndarray) -> dict[str, Any]:
    if spec['family'] == 'IDW_COS_4D':
        return {'spec': dict(spec), 'X': X.copy(), 'Y': Y.copy()}
    if spec['family'] == 'QUADRATIC_RIDGE_COS_4D':
        D = quadratic_design(X)
        penalty = np.eye(D.shape[1], dtype=np.float64)
        penalty[0, 0] = 0.0
        a = D.T @ D + float(spec['ridge']) * penalty
        b = D.T @ Y
        coef = np.linalg.solve(a, b)
        req(np.isfinite(coef).all(), 'nonfinite ridge coefficients')
        return {'spec': dict(spec), 'coef': coef}
    raise Refusal('unknown family')


def predict(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    spec = model['spec']
    if spec['family'] == 'IDW_COS_4D':
        X = model['X']; Y = model['Y']
        dist = np.linalg.norm(X - x[None, :], axis=1)
        req(np.isfinite(dist).all(), 'nonfinite distance')
        zero = np.flatnonzero(dist <= 1e-15)
        if len(zero):
            return Y[int(zero[0])].copy()
        k = min(int(spec['neighbors']), len(dist))
        order = np.lexsort((np.arange(len(dist), dtype=np.int64), dist))[:k]
        weights = 1.0 / np.power(dist[order], float(spec['power']))
        pred = np.sum(Y[order] * weights[:, None], axis=0) / float(np.sum(weights))
        req(np.isfinite(pred).all(), 'nonfinite IDW prediction')
        return pred
    if spec['family'] == 'QUADRATIC_RIDGE_COS_4D':
        d = quadratic_design(x.reshape(1, -1))[0]
        pred = d @ model['coef']
        req(np.isfinite(pred).all(), 'nonfinite ridge prediction')
        return pred
    raise Refusal('unknown family')


def percentile_linear(values: np.ndarray, q: float) -> float:
    req(values.ndim == 1 and len(values) > 0, 'nonempty vector required')
    a = np.sort(values.astype(np.float64, copy=False))
    pos = (len(a) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return float(a[lo])
    frac = pos - lo
    return float(a[lo] * (1.0 - frac) + a[hi] * frac)


def metrics(truth: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    req(truth.shape == pred.shape and truth.ndim == 2 and truth.shape[1] == 12, 'metric matrix shape drift')
    err = pred - truth
    ae = np.abs(err).ravel()
    field_bias = np.mean(err, axis=0)
    return {
        'aggregateMeanAbsoluteLogContrastError': float(np.mean(ae)),
        'medianAbsoluteLogContrastError': percentile_linear(ae, 0.5),
        'p90AbsoluteLogContrastError': percentile_linear(ae, 0.9),
        'worstAbsoluteLogContrastError': float(np.max(ae)),
        'maxOver12FieldsAbsoluteMeanSignedBias': float(np.max(np.abs(field_bias))),
        'fieldMeanSignedBias': {TARGET_NAMES[i]: float(field_bias[i]) for i in range(12)},
    }


def leave_one_out_predictions(spec: dict[str, Any], X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    preds = np.zeros_like(Y)
    for i in range(len(X)):
        mask = np.arange(len(X)) != i
        model = fit_model(spec, X[mask], Y[mask])
        preds[i] = predict(model, X[i])
    req(np.isfinite(preds).all(), 'nonfinite LOO predictions')
    return preds


def nearest_loo_predictions(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    preds = np.zeros_like(Y)
    for i in range(len(X)):
        candidates = [j for j in range(len(X)) if j != i]
        ranked = sorted(candidates, key=lambda j: (float(np.linalg.norm(X[j] - X[i])), j))
        preds[i] = Y[ranked[0]]
    return preds


def eligible(candidate: dict[str, Any], nearest_mae: float, gates: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    m = candidate['metrics']
    improvement = 1.0 - m['aggregateMeanAbsoluteLogContrastError'] / nearest_mae
    checks = {
        'aggregateMeanAbsoluteLogContrastError': m['aggregateMeanAbsoluteLogContrastError'] <= float(gates['aggregateMeanAbsoluteLogContrastErrorMax']),
        'medianAbsoluteLogContrastError': m['medianAbsoluteLogContrastError'] <= float(gates['medianAbsoluteLogContrastErrorMax']),
        'p90AbsoluteLogContrastError': m['p90AbsoluteLogContrastError'] <= float(gates['p90AbsoluteLogContrastErrorMax']),
        'worstAbsoluteLogContrastError': m['worstAbsoluteLogContrastError'] <= float(gates['worstAbsoluteLogContrastErrorMax']),
        'maxOver12FieldsAbsoluteMeanSignedBias': m['maxOver12FieldsAbsoluteMeanSignedBias'] <= float(gates['maxOver12FieldsAbsoluteMeanSignedBiasMax']),
        'improvementVsNearestCell': improvement >= float(gates['meanErrorImprovementVsNearestCellBaselineMinFraction']),
        'allPredictionsFinite': bool(gates['allPredictionsFinite']),
    }
    return all(checks.values()), {**checks, 'improvementVsNearestCellFraction': improvement}


def materialize(index: dict[str, Any], protocol: dict[str, Any], source_zip_sha256: str, protocol_file_sha256: str) -> dict[str, Any]:
    req(protocol.get('stageId') == STAGE_ID, 'protocol stage drift')
    req(protocol['authorization']['ordinal39Allocated'] is False, 'ordinal39 must remain unallocated during training selection')
    req(protocol['trainingOnlyInterpolatorSelection']['holdoutValuesMayInfluenceSelection'] is False, 'holdout isolation drift')
    records, X, Y = extract_training(index)
    nearest_pred = nearest_loo_predictions(X, Y)
    zero_pred = np.zeros_like(Y)
    nearest_metrics = metrics(Y, nearest_pred)
    zero_metrics = metrics(Y, zero_pred)
    nearest_mae = nearest_metrics['aggregateMeanAbsoluteLogContrastError']
    table: list[dict[str, Any]] = []
    gates = protocol['trainingOnlyInterpolatorSelection']['trainingEligibilityGates']
    for spec in candidate_specs(protocol):
        pred = leave_one_out_predictions(spec, X, Y)
        row = {'spec': spec, 'metrics': metrics(Y, pred)}
        ok, checks = eligible(row, nearest_mae, gates)
        row['eligible'] = ok
        row['gateChecks'] = checks
        table.append(row)
    eligible_rows = [r for r in table if r['eligible']]
    req(eligible_rows, protocol['trainingOnlyInterpolatorSelection']['ifNoCandidateEligible'])
    selected = sorted(eligible_rows, key=lambda r: (
        r['metrics']['aggregateMeanAbsoluteLogContrastError'],
        r['metrics']['p90AbsoluteLogContrastError'],
        r['metrics']['worstAbsoluteLogContrastError'],
        r['spec']['complexityRank'],
        r['spec']['candidateId'],
    ))[0]
    final_model = fit_model(selected['spec'], X, Y)
    if selected['spec']['family'] == 'IDW_COS_4D':
        parameters: dict[str, Any] = {
            'trainingCoordinates': X.tolist(),
            'trainingTargets': Y.tolist(),
        }
    else:
        parameters = {'coefficients15x12': final_model['coef'].tolist()}
    output: dict[str, Any] = {
        'schemaVersion': 1,
        'modelId': 'aerosol-scenario-interpolator-v1',
        'status': 'TRAINING_ONLY_SELECTED_AND_MATERIALIZED_NO_HOLDOUT_OPENING_NO_SCIENTIFIC_EXECUTION',
        'sourceBindings': {
            'scientificOrdinal': EXPECTED_ORDINAL,
            'analysisRecoveryArtifactDigest': f'sha256:{source_zip_sha256}',
            'protocolFileSha256': protocol_file_sha256,
        },
        'targetNamesInOrder': list(TARGET_NAMES),
        'coordinateOrder': ['s', 'a', 'cosAz', 'aod'],
        'coordinateDefinition': 's=(sun-2)/8.5; a=(alt-5)/75; cosAz=(cos(relativeAzDeg)+1)/2; aod=(aod550-.05)/.35',
        'observerElevationTreatment': 'NOT_IN_FIT_ZERO_ORDER_INVARIANCE_HYPOTHESIS_ONLY',
        'quantileDefinition': 'LINEAR_INTERPOLATION_AT_(N-1)*Q_AFTER_ASCENDING_SORT',
        'ridgePenaltyDefinition': 'L2_ON_ALL_14_NONINTERCEPT_BASIS_TERMS_INTERCEPT_UNPENALIZED',
        'idwTieBreak': 'ASCENDING_DISTANCE_THEN_ASCENDING_TRAINING_ROW_INDEX_AFTER_ANALYSIS_CELL_ID_SORT',
        'trainingRows': records,
        'trainingMatrixCanonicalSha256': canonical_sha({'records': records, 'X': X.tolist(), 'Y': Y.tolist(), 'targetNames': list(TARGET_NAMES)}),
        'baselines': {
            'nearestOrdinal38CellLeaveOneOut': nearest_metrics,
            'zeroAerosolContrast': zero_metrics,
        },
        'candidateTable': table,
        'selectedCandidate': selected,
        'materializedParameters': parameters,
        'holdoutValuesRead': False,
        'scientificExecutionPerformed': False,
        'solverExecutionPerformed': False,
        'ordinal39Allocated': False,
        'postSelectionRetuningAuthorized': False,
    }
    output['selfHashDefinition'] = 'SHA256_OF_CANONICAL_OBJECT_WITH_selfSha256_AND_selfHashDefinition_OMITTED'
    hashable = dict(output)
    hashable.pop('selfHashDefinition', None)
    output['selfSha256'] = canonical_sha(hashable)
    return output


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--artifact-zip', required=True)
    ap.add_argument('--protocol', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    artifact_path = Path(args.artifact_zip)
    protocol_path = Path(args.protocol)
    raw_zip = artifact_path.read_bytes()
    protocol_raw = protocol_path.read_bytes()
    protocol = load_json_bytes(protocol_raw)
    expected = str(protocol['sourceBindings']['afpfOrdinal38RecoveryArtifactDigest'])
    actual_sha = sha256_bytes(raw_zip)
    req(expected == f'sha256:{actual_sha}', 'bound ordinal38 recovery artifact digest mismatch')
    with zipfile.ZipFile(artifact_path, 'r') as zf:
        names = zf.namelist()
        req(names.count('analysis-index.json') == 1, 'exactly one analysis-index.json required')
        index = load_json_bytes(zf.read('analysis-index.json'))
    result = materialize(index, protocol, actual_sha, sha256_bytes(protocol_raw))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    print(result['status'])
    print('selected=' + result['selectedCandidate']['spec']['candidateId'])
    print('selfSha256=' + result['selfSha256'])
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Refusal as exc:
        print('REFUSAL: ' + str(exc))
        raise SystemExit(2)
