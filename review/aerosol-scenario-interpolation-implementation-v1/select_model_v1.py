#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path
from typing import Any

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


def coordinate(geometry: dict[str, Any]) -> list[float]:
    return [
        (float(geometry['sunDepressionDeg']) - 2.0) / 8.5,
        (float(geometry['targetAltitudeDeg']) - 5.0) / 75.0,
        (math.cos(math.radians(float(geometry['relativeAzimuthDeg']))) + 1.0) / 2.0,
        (float(geometry['aod550']) - 0.05) / 0.35,
    ]


def extract_training(index: dict[str, Any]) -> tuple[list[dict[str, Any]], list[list[float]], list[list[float]]]:
    req(index.get('scientificOrdinal') == EXPECTED_ORDINAL, 'ordinal drift')
    req(index.get('analysisCellCount') == EXPECTED_CELLS, 'cell-count drift')
    cells = index.get('cells')
    req(isinstance(cells, list) and len(cells) == EXPECTED_CELLS, 'exact 24 cells required')
    rows: list[tuple[str, dict[str, Any], list[float], list[float]]] = []
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
        y: list[float] = []
        for contrast in CONTRASTS:
            for channel in CHANNELS:
                entry = cell['primary'][channel][contrast]
                req(entry.get('status') == 'FINITE_THREE_REPLICATES', f'nonfinite training row: {cid}/{contrast}/{channel}')
                values = entry.get('replicateValues')
                req(isinstance(values, list) and len(values) == 3, 'three replicates required')
                vals = [float(v) for v in values]
                req(all(math.isfinite(v) for v in vals), 'three finite replicates required')
                mean = float(entry['mean'])
                req(math.isfinite(mean), 'finite mean required')
                req(abs(mean - sum(vals) / 3.0) <= 5e-13, 'mean/replicate mismatch')
                y.append(mean)
        rows.append((cid, geom, coordinate(geom), y))
    rows.sort(key=lambda r: r[0])
    records = [{'analysisCellId': cid, 'geometry': geom} for cid, geom, _, _ in rows]
    X = [x for _, _, x, _ in rows]
    Y = [y for _, _, _, y in rows]
    req(len(X) == 24 and all(len(x) == 4 for x in X), 'training coordinate shape drift')
    req(len(Y) == 24 and all(len(y) == 12 for y in Y), 'training target shape drift')
    req(all(math.isfinite(v) for row in X for v in row), 'nonfinite training coordinates')
    req(all(math.isfinite(v) for row in Y for v in row), 'nonfinite training targets')
    return records, X, Y


def candidate_specs(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for family in protocol['trainingOnlyInterpolatorSelection']['candidateFamilies']:
        if family['family'] == 'IDW_COS_4D':
            for k in family['neighbors']:
                for power in family['powers']:
                    specs.append({
                        'candidateId': f'idw-k{int(k)}-p{float(power):g}',
                        'family': 'IDW_COS_4D',
                        'neighbors': int(k),
                        'power': float(power),
                        'complexityRank': int(family['complexityRank']),
                    })
        elif family['family'] == 'QUADRATIC_RIDGE_COS_4D':
            for ridge in family['ridge']:
                specs.append({
                    'candidateId': f'quad-ridge-{float(ridge):.12g}',
                    'family': 'QUADRATIC_RIDGE_COS_4D',
                    'ridge': float(ridge),
                    'complexityRank': int(family['complexityRank']),
                })
        else:
            raise Refusal(f'unknown candidate family: {family["family"]}')
    req(len(specs) == 17, 'candidate cardinality drift')
    req(len({s['candidateId'] for s in specs}) == len(specs), 'duplicate candidate id')
    return specs


def quadratic_design_row(x: list[float]) -> list[float]:
    req(len(x) == 4, '4D coordinate required')
    row = [1.0]
    row.extend(x)
    row.extend(v * v for v in x)
    row.extend(x[i] * x[j] for i in range(4) for j in range(i + 1, 4))
    req(len(row) == 15, 'quadratic basis cardinality drift')
    return row


def dot(a: list[float], b: list[float]) -> float:
    req(len(a) == len(b), 'dot dimension mismatch')
    return sum(x * y for x, y in zip(a, b))


def distance(a: list[float], b: list[float]) -> float:
    req(len(a) == len(b), 'distance dimension mismatch')
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def cholesky(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    req(n > 0 and all(len(row) == n for row in a), 'square matrix required')
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                pivot = a[i][i] - s
                req(math.isfinite(pivot) and pivot > 1e-15, 'ridge normal matrix not positive definite')
                L[i][j] = math.sqrt(pivot)
            else:
                req(L[j][j] > 0.0, 'zero Cholesky pivot')
                L[i][j] = (a[i][j] - s) / L[j][j]
    return L


def solve_cholesky_multi(L: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    n = len(L)
    req(len(b) == n and n > 0, 'rhs row mismatch')
    m = len(b[0])
    req(m > 0 and all(len(row) == m for row in b), 'rhs column mismatch')
    z = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for c in range(m):
            z[i][c] = (b[i][c] - sum(L[i][k] * z[k][c] for k in range(i))) / L[i][i]
    x = [[0.0] * m for _ in range(n)]
    for i in range(n - 1, -1, -1):
        for c in range(m):
            x[i][c] = (z[i][c] - sum(L[k][i] * x[k][c] for k in range(i + 1, n))) / L[i][i]
    req(all(math.isfinite(v) for row in x for v in row), 'nonfinite linear solve')
    return x


def fit_model(spec: dict[str, Any], X: list[list[float]], Y: list[list[float]]) -> dict[str, Any]:
    req(len(X) == len(Y) and len(X) > 0, 'fit row mismatch')
    if spec['family'] == 'IDW_COS_4D':
        return {'spec': dict(spec), 'X': [row[:] for row in X], 'Y': [row[:] for row in Y]}
    if spec['family'] == 'QUADRATIC_RIDGE_COS_4D':
        n_basis = 15
        n_targets = 12
        A = [[0.0] * n_basis for _ in range(n_basis)]
        B = [[0.0] * n_targets for _ in range(n_basis)]
        for x, y in zip(X, Y):
            d = quadratic_design_row(x)
            req(len(y) == n_targets, 'target width drift')
            for i in range(n_basis):
                di = d[i]
                for j in range(n_basis):
                    A[i][j] += di * d[j]
                for c in range(n_targets):
                    B[i][c] += di * y[c]
        ridge = float(spec['ridge'])
        req(ridge > 0 and math.isfinite(ridge), 'positive finite ridge required')
        for j in range(1, n_basis):
            A[j][j] += ridge
        coef = solve_cholesky_multi(cholesky(A), B)
        return {'spec': dict(spec), 'coef': coef}
    raise Refusal('unknown family')


def predict(model: dict[str, Any], x: list[float]) -> list[float]:
    spec = model['spec']
    if spec['family'] == 'IDW_COS_4D':
        X = model['X']; Y = model['Y']
        ranked = sorted(((distance(row, x), i) for i, row in enumerate(X)), key=lambda t: (t[0], t[1]))
        if ranked[0][0] <= 1e-15:
            return Y[ranked[0][1]][:]
        k = min(int(spec['neighbors']), len(ranked))
        chosen = ranked[:k]
        weights = [1.0 / (d ** float(spec['power'])) for d, _ in chosen]
        denom = sum(weights)
        req(math.isfinite(denom) and denom > 0.0, 'invalid IDW weight sum')
        pred = [sum(w * Y[idx][c] for w, (_, idx) in zip(weights, chosen)) / denom for c in range(12)]
        req(all(math.isfinite(v) for v in pred), 'nonfinite IDW prediction')
        return pred
    if spec['family'] == 'QUADRATIC_RIDGE_COS_4D':
        d = quadratic_design_row(x)
        coef = model['coef']
        pred = [sum(d[i] * coef[i][c] for i in range(15)) for c in range(12)]
        req(all(math.isfinite(v) for v in pred), 'nonfinite ridge prediction')
        return pred
    raise Refusal('unknown family')


def percentile_linear(values: list[float], q: float) -> float:
    req(values and 0.0 <= q <= 1.0, 'nonempty values and valid quantile required')
    a = sorted(float(v) for v in values)
    pos = (len(a) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return a[lo]
    frac = pos - lo
    return a[lo] * (1.0 - frac) + a[hi] * frac


def metrics(truth: list[list[float]], pred: list[list[float]]) -> dict[str, Any]:
    req(len(truth) == len(pred) and truth, 'metric row mismatch')
    req(all(len(row) == 12 for row in truth) and all(len(row) == 12 for row in pred), 'metric target width drift')
    errors = [[p - t for p, t in zip(prow, trow)] for trow, prow in zip(truth, pred)]
    abs_errors = [abs(v) for row in errors for v in row]
    field_bias = [sum(row[c] for row in errors) / len(errors) for c in range(12)]
    return {
        'aggregateMeanAbsoluteLogContrastError': sum(abs_errors) / len(abs_errors),
        'medianAbsoluteLogContrastError': percentile_linear(abs_errors, 0.5),
        'p90AbsoluteLogContrastError': percentile_linear(abs_errors, 0.9),
        'worstAbsoluteLogContrastError': max(abs_errors),
        'maxOver12FieldsAbsoluteMeanSignedBias': max(abs(v) for v in field_bias),
        'fieldMeanSignedBias': {TARGET_NAMES[i]: field_bias[i] for i in range(12)},
    }


def leave_one_out_predictions(spec: dict[str, Any], X: list[list[float]], Y: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(len(X)):
        train_x = [row for j, row in enumerate(X) if j != i]
        train_y = [row for j, row in enumerate(Y) if j != i]
        out.append(predict(fit_model(spec, train_x, train_y), X[i]))
    req(all(math.isfinite(v) for row in out for v in row), 'nonfinite LOO prediction')
    return out


def nearest_loo_predictions(X: list[list[float]], Y: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for i, x in enumerate(X):
        ranked = sorted((distance(x, X[j]), j) for j in range(len(X)) if j != i)
        out.append(Y[ranked[0][1]][:])
    return out


def zero_predictions(Y: list[list[float]]) -> list[list[float]]:
    return [[0.0] * 12 for _ in Y]


def eligible(candidate: dict[str, Any], nearest_mae: float, gates: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    m = candidate['metrics']
    req(nearest_mae > 0.0, 'nearest-cell baseline MAE must be positive')
    improvement = 1.0 - m['aggregateMeanAbsoluteLogContrastError'] / nearest_mae
    checks: dict[str, Any] = {
        'aggregateMeanAbsoluteLogContrastError': m['aggregateMeanAbsoluteLogContrastError'] <= float(gates['aggregateMeanAbsoluteLogContrastErrorMax']),
        'medianAbsoluteLogContrastError': m['medianAbsoluteLogContrastError'] <= float(gates['medianAbsoluteLogContrastErrorMax']),
        'p90AbsoluteLogContrastError': m['p90AbsoluteLogContrastError'] <= float(gates['p90AbsoluteLogContrastErrorMax']),
        'worstAbsoluteLogContrastError': m['worstAbsoluteLogContrastError'] <= float(gates['worstAbsoluteLogContrastErrorMax']),
        'maxOver12FieldsAbsoluteMeanSignedBias': m['maxOver12FieldsAbsoluteMeanSignedBias'] <= float(gates['maxOver12FieldsAbsoluteMeanSignedBiasMax']),
        'improvementVsNearestCell': improvement >= float(gates['meanErrorImprovementVsNearestCellBaselineMinFraction']),
        'allPredictionsFinite': True,
        'improvementVsNearestCellFraction': improvement,
    }
    pass_keys = [k for k in checks if k != 'improvementVsNearestCellFraction']
    return all(bool(checks[k]) for k in pass_keys), checks


def materialize(index: dict[str, Any], protocol: dict[str, Any], source_zip_sha256: str, protocol_file_sha256: str) -> dict[str, Any]:
    req(protocol.get('stageId') == STAGE_ID, 'protocol stage drift')
    req(protocol['authorization']['ordinal39Allocated'] is False, 'ordinal39 must remain unallocated during training selection')
    req(protocol['trainingOnlyInterpolatorSelection']['holdoutValuesMayInfluenceSelection'] is False, 'holdout isolation drift')
    records, X, Y = extract_training(index)
    nearest_metrics = metrics(Y, nearest_loo_predictions(X, Y))
    zero_metrics = metrics(Y, zero_predictions(Y))
    nearest_mae = nearest_metrics['aggregateMeanAbsoluteLogContrastError']
    gates = protocol['trainingOnlyInterpolatorSelection']['trainingEligibilityGates']
    table: list[dict[str, Any]] = []
    for candidate in candidate_specs(protocol):
        row = {'spec': candidate, 'metrics': metrics(Y, leave_one_out_predictions(candidate, X, Y))}
        ok, checks = eligible(row, nearest_mae, gates)
        row['eligible'] = ok
        row['gateChecks'] = checks
        table.append(row)
    eligible_rows = [row for row in table if row['eligible']]
    req(eligible_rows, protocol['trainingOnlyInterpolatorSelection']['ifNoCandidateEligible'])
    selected = sorted(
        eligible_rows,
        key=lambda row: (
            row['metrics']['aggregateMeanAbsoluteLogContrastError'],
            row['metrics']['p90AbsoluteLogContrastError'],
            row['metrics']['worstAbsoluteLogContrastError'],
            row['spec']['complexityRank'],
            row['spec']['candidateId'],
        ),
    )[0]
    final_model = fit_model(selected['spec'], X, Y)
    if selected['spec']['family'] == 'IDW_COS_4D':
        params: dict[str, Any] = {'trainingCoordinates': X, 'trainingTargets': Y}
    else:
        params = {'coefficients15x12': final_model['coef']}
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
        'ridgeSolverDefinition': 'DETERMINISTIC_FLOAT64_STYLE_PYTHON_BINARY64_CHOLESKY_NO_EXTERNAL_NUMERICAL_LIBRARY',
        'idwTieBreak': 'ASCENDING_DISTANCE_THEN_ASCENDING_TRAINING_ROW_INDEX_AFTER_ANALYSIS_CELL_ID_SORT',
        'trainingRows': records,
        'trainingMatrixCanonicalSha256': canonical_sha({'records': records, 'X': X, 'Y': Y, 'targetNames': list(TARGET_NAMES)}),
        'baselines': {
            'nearestOrdinal38CellLeaveOneOut': nearest_metrics,
            'zeroAerosolContrast': zero_metrics,
        },
        'candidateTable': table,
        'selectedCandidate': selected,
        'materializedParameters': params,
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
