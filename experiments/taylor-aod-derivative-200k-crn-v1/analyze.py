#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2, 3, 4, 5, 6]
STAGE = 'taylor-aod-derivative-200k-crn-v1'
AOD_SIGMA = 0.049232200070782176


def stats(values):
    vals = [float(v) for v in values]
    if len(vals) != 6 or any(not math.isfinite(v) for v in vals):
        raise RuntimeError('expected exactly six finite replicate values')
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals)
    return {'values': vals, 'n': 6, 'mean': mean, 'sampleSd': sd, 'se': sd / math.sqrt(6.0), 'min': min(vals), 'max': max(vals)}


def load_results(root: Path):
    out = {}
    for p in root.rglob('row-replicate-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != STAGE or x.get('status') != 'COMPLETED':
            continue
        key = (int(x['row']), int(x['replicate']))
        if key in out:
            raise RuntimeError(f'duplicate result {key}')
        out[key] = x
    expected = {(r, q) for r in ROWS for q in REPLICATES}
    if set(out) != expected:
        raise RuntimeError(f'exact result universe mismatch: {sorted(out)}')
    return out


def load_legacy(root: Path):
    found = list(root.rglob('comparison.csv'))
    if len(found) != 1:
        raise RuntimeError(f'expected one Taylor-v1 comparison.csv, got {len(found)}')
    with found[0].open(newline='') as f:
        rows = {int(r['row']): r for r in csv.DictReader(f)}
    if set(rows) != set(range(1, 33)):
        raise RuntimeError('legacy Taylor comparison universe not exact 1..32')
    return rows


def ray_map(x, field):
    rays = {int(r['rayIndex']): r for r in x[field]}
    if set(rays) != set(range(1, 65)):
        raise RuntimeError(f'{field}: wrong ray universe')
    return rays


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-root', type=Path, required=True)
    ap.add_argument('--legacy-analysis-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)

    results = load_results(a.results_root)
    legacy = load_legacy(a.legacy_analysis_root)
    row_records = []
    ray_records = []
    details = {}

    for row in ROWS:
        reps = [results[(row, rep)] for rep in REPLICATES]
        if any(x['aodConditions'] != [0.3, 0.4] for x in reps):
            raise RuntimeError(f'row {row}: AOD condition drift')
        if any(int(x['photonsPerRayPerCondition']) != 200_000 or int(x['rayCount']) != 64 for x in reps):
            raise RuntimeError(f'row {row}: photon/ray metadata drift')

        deriv = stats([x['finiteDifferenceDerivativeMagPerAod'] for x in reps])
        delta = stats([x['deltaMag040Minus030'] for x in reps])
        implied_aod_sigma = abs(deriv['mean']) * AOD_SIGMA
        derivative_se_aod_sigma = deriv['se'] * AOD_SIGMA
        legacy_derivative = float(legacy[row]['aod_derivative_mag_per_aod'])
        legacy_aod_sigma = float(legacy[row]['sigma_aod_local'])
        signal_to_sd = None if deriv['sampleSd'] == 0 else abs(deriv['mean']) / deriv['sampleSd']

        per_rep_rays = {}
        for rep, x in zip(REPLICATES, reps):
            lo = ray_map(x, 'rays030')
            hi = ray_map(x, 'rays040')
            per_rep_rays[rep] = (lo, hi)
            for idx in range(1, 65):
                if int(lo[idx]['seed']) != int(hi[idx]['seed']):
                    raise RuntimeError(f'row {row} rep {rep} ray {idx}: CRN mismatch')

        ray_sds = []
        for idx in range(1, 65):
            dvals = []
            for rep in REPLICATES:
                lo, hi = per_rep_rays[rep]
                qlo = float(lo[idx]['q']); qhi = float(hi[idx]['q'])
                if qlo <= 0 or qhi <= 0:
                    raise RuntimeError(f'row {row} ray {idx}: nonpositive Q')
                dvals.append((-2.5 * math.log10(qhi / qlo)) / 0.10)
            ds = stats(dvals)
            ray_sds.append(ds['sampleSd'])
            ray_records.append({'row': row, 'rayIndex': idx, 'derivativeMeanMagPerAod': ds['mean'], 'derivativeSampleSdMagPerAod': ds['sampleSd'], 'derivativeMin': ds['min'], 'derivativeMax': ds['max']})
        ordered = sorted(ray_sds)
        ray_summary = {'medianDerivativeSd': statistics.median(ordered), 'p90DerivativeSd': ordered[int(0.9 * (len(ordered) - 1))], 'maxDerivativeSd': max(ordered)}

        rec = {
            'row': row,
            'sunAltGeometricDeg': float(reps[0]['sunAltGeometricDeg']),
            'frozenPrimaryAod550': float(reps[0]['frozenPrimaryAod550']),
            'derivativeMeanMagPerAod': deriv['mean'],
            'derivativeSampleSdMagPerAod': deriv['sampleSd'],
            'derivativeSeMagPerAod': deriv['se'],
            'derivativeMinMagPerAod': deriv['min'],
            'derivativeMaxMagPerAod': deriv['max'],
            'derivativeSignalToBetweenSeedSd': signal_to_sd,
            'deltaMagMean040Minus030': delta['mean'],
            'deltaMagSampleSd040Minus030': delta['sampleSd'],
            'impliedLocalAodSigmaMag': implied_aod_sigma,
            'numericalSeContributionToAodSigmaMag': derivative_se_aod_sigma,
            'legacyDerivativeMagPerAod': legacy_derivative,
            'legacyLocalAodSigmaMag': legacy_aod_sigma,
            'newMinusLegacyDerivativeMagPerAod': deriv['mean'] - legacy_derivative,
            'rayDerivativeSdMedian': ray_summary['medianDerivativeSd'],
            'rayDerivativeSdP90': ray_summary['p90DerivativeSd'],
            'rayDerivativeSdMax': ray_summary['maxDerivativeSd'],
        }
        row_records.append(rec)
        details[str(row)] = {'derivative': deriv, 'deltaMag040Minus030': delta, 'impliedLocalAodSigmaMag': implied_aod_sigma, 'numericalSeContributionToAodSigmaMag': derivative_se_aod_sigma, 'legacyDerivativeMagPerAod': legacy_derivative, 'legacyLocalAodSigmaMag': legacy_aod_sigma, 'rayDerivativeSd': ray_summary}

    with (a.output / 'row-summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row_records[0].keys())); w.writeheader(); w.writerows(row_records)
    with (a.output / 'ray-summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(ray_records[0].keys())); w.writeheader(); w.writerows(ray_records)

    result = {'schemaVersion': 1, 'stageId': STAGE, 'status': 'AOD_DERIVATIVE_EMPIRICAL_AUDIT_COMPLETE', 'rows': details, 'aodSigmaFrozen': AOD_SIGMA, 'boundary': 'Numerical reconvergence of the already-declared 0.30-to-0.40 AOD finite difference only. Legacy derivative comparison is orientation-only; no AOD fitting, atmosphere revision, Taylor residual scoring, Level-B/F/tau/production/human conclusion.'}
    (a.output / 'metrics.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')

    lines = ['# Taylor late-primary AOD derivative 200k CRN audit', '', 'Six independent common-random-number pairs at AOD550 0.30 and 0.40 per row; 200k photons/ray/condition.', '', '|row|legacy D|six-seed mean D|SD(D)|SE(D)|new local AOD sigma|legacy AOD sigma|signal/SD|ray SD median / p90 / max|', '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in row_records:
        lines.append(f"|{r['row']}|{r['legacyDerivativeMagPerAod']:+.4f}|{r['derivativeMeanMagPerAod']:+.4f}|{r['derivativeSampleSdMagPerAod']:.4f}|{r['derivativeSeMagPerAod']:.4f}|{r['impliedLocalAodSigmaMag']:.4f}|{r['legacyLocalAodSigmaMag']:.4f}|{r['derivativeSignalToBetweenSeedSd']:.2f}|{r['rayDerivativeSdMedian']:.2f} / {r['rayDerivativeSdP90']:.2f} / {r['rayDerivativeSdMax']:.2f}|")
    lines += ['', '**Boundary:** this audit does not choose or fit AOD. It only reconverges the finite-difference slope already declared in Taylor-v1.']
    (a.output / 'report.md').write_text('\n'.join(lines) + '\n'); print((a.output / 'report.md').read_text())


if __name__ == '__main__':
    main()
