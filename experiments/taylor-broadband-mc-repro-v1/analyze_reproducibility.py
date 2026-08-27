#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ROWS = [23, 24, 25]
OLD_STAGE = 'taylor-hrrr-broadband-vertical-shape-v1'
NEW_STAGE = 'taylor-broadband-mc-repro-v1'
OLD_REPLICATES = [1, 2]
NEW_REPLICATES = [3, 4, 5, 6]
ALL_REPLICATES = [1, 2, 3, 4, 5, 6]


def sample_stats(values):
    vals = [float(x) for x in values]
    if len(vals) < 2 or any(not math.isfinite(x) for x in vals):
        raise RuntimeError('sample_stats requires at least two finite values')
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals)
    return {
        'n': len(vals),
        'values': vals,
        'mean': mean,
        'sampleSd': sd,
        'se': sd / math.sqrt(len(vals)),
        'cv': None if mean == 0 else sd / abs(mean),
        'min': min(vals),
        'max': max(vals),
    }


def median(values):
    vals = [float(x) for x in values]
    if not vals or any(not math.isfinite(x) for x in vals):
        raise RuntimeError('median requires finite values')
    return statistics.median(vals)


def load_results(root: Path, stage: str, allowed_reps):
    found = {}
    for p in root.rglob('row-replicate-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != stage or x.get('status') != 'COMPLETED':
            continue
        row = int(x['row'])
        rep = int(x['replicate'])
        if row not in ROWS or rep not in allowed_reps:
            raise RuntimeError(f'unexpected result identity {(row, rep)} in stage {stage}')
        key = (row, rep)
        if key in found:
            raise RuntimeError(f'duplicate result {key} for stage {stage}')
        found[key] = x
    expected = {(r, q) for r in ROWS for q in allowed_reps}
    if set(found) != expected:
        raise RuntimeError(f'{stage}: exact result universe required {sorted(expected)}, got {sorted(found)}')
    return found


def nearest_rank_p90(values):
    vals = sorted(float(x) for x in values)
    if not vals:
        raise RuntimeError('p90 requires nonempty values')
    return vals[int(0.9 * (len(vals) - 1))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old-results-root', type=Path, required=True)
    ap.add_argument('--new-results-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)

    old = load_results(a.old_results_root, OLD_STAGE, OLD_REPLICATES)
    new = load_results(a.new_results_root, NEW_STAGE, NEW_REPLICATES)
    all_results = {**old, **new}
    expected = {(r, q) for r in ROWS for q in ALL_REPLICATES}
    if set(all_results) != expected:
        raise RuntimeError('combined six-seed universe mismatch')

    row_records = []
    ray_records = []
    detailed = {}

    for row in ROWS:
        reps = [all_results[(row, rep)] for rep in ALL_REPLICATES]
        if any(int(x['rayCount']) != 64 for x in reps):
            raise RuntimeError(f'row {row}: ray count changed')
        if any(int(x['photonsPerRayPerCondition']) != 50_000 for x in reps):
            raise RuntimeError(f'row {row}: photon budget changed')

        default_q = [float(x['defaultQ']) for x in reps]
        default_sigma = [float(x['defaultQStdConservative']) for x in reps]
        delta = [float(x['deltaMagHrrrMinusDefault']) for x in reps]
        delta_sigma = [float(x['deltaMagIndependentMcSigmaConservative']) for x in reps]
        if any(x <= 0 or not math.isfinite(x) for x in default_q):
            raise RuntimeError(f'row {row}: invalid default Q')
        if any(x < 0 or not math.isfinite(x) for x in default_sigma + delta_sigma):
            raise RuntimeError(f'row {row}: invalid reported sigma')
        if any(not math.isfinite(x) for x in delta):
            raise RuntimeError(f'row {row}: invalid paired delta')

        q_stats = sample_stats(default_q)
        d_stats = sample_stats(delta)
        med_q_sigma = median(default_sigma)
        med_d_sigma = median(delta_sigma)
        q_ratio = None if med_q_sigma == 0 else q_stats['sampleSd'] / med_q_sigma
        d_ratio = None if med_d_sigma == 0 else d_stats['sampleSd'] / med_d_sigma

        by_rep_rays = {}
        for rep, x in zip(ALL_REPLICATES, reps):
            rays = {int(r['rayIndex']): r for r in x['rays']}
            if set(rays) != set(range(1, 65)):
                raise RuntimeError(f'row {row} rep {rep}: ray universe changed')
            by_rep_rays[rep] = rays

        ray_ratios = []
        for ray in range(1, 65):
            qs = [float(by_rep_rays[rep][ray]['default']['q']) for rep in ALL_REPLICATES]
            sigmas = [float(by_rep_rays[rep][ray]['default']['qStdConservative']) for rep in ALL_REPLICATES]
            q_ray_stats = sample_stats(qs)
            med_ray_sigma = median(sigmas)
            ratio = None if med_ray_sigma == 0 else q_ray_stats['sampleSd'] / med_ray_sigma
            if ratio is not None:
                ray_ratios.append(ratio)
            ray_records.append({
                'row': row,
                'rayIndex': ray,
                'thetaDeg': float(by_rep_rays[1][ray]['thetaDeg']),
                'relativeAzimuthDeg': float(by_rep_rays[1][ray]['relativeAzimuthDeg']),
                'defaultQMeanSixSeeds': q_ray_stats['mean'],
                'defaultQSampleSdSixSeeds': q_ray_stats['sampleSd'],
                'medianReportedQStdConservative': med_ray_sigma,
                'empiricalSdToMedianReportedSigma': ratio,
            })

        if len(ray_ratios) != 64:
            raise RuntimeError(f'row {row}: expected 64 finite ray sigma ratios')
        ray_ratio_summary = {
            'median': statistics.median(ray_ratios),
            'p90NearestRank': nearest_rank_p90(ray_ratios),
            'max': max(ray_ratios),
        }

        rec = {
            'row': row,
            'sunAltGeometricDeg': float(reps[0]['sunAltGeometricDeg']),
            'aod550Frozen': float(reps[0]['aod550Frozen']),
            'defaultQMeanSixSeeds': q_stats['mean'],
            'defaultQSampleSdSixSeeds': q_stats['sampleSd'],
            'defaultQSeSixSeeds': q_stats['se'],
            'defaultQCvSixSeeds': q_stats['cv'],
            'defaultQMinSixSeeds': q_stats['min'],
            'defaultQMaxSixSeeds': q_stats['max'],
            'medianReportedDefaultQStdConservative': med_q_sigma,
            'defaultEmpiricalSdToMedianReportedSigma': q_ratio,
            'pairedDeltaMeanMagSixSeeds': d_stats['mean'],
            'pairedDeltaSampleSdMagSixSeeds': d_stats['sampleSd'],
            'pairedDeltaSeMagSixSeeds': d_stats['se'],
            'pairedDeltaMinMagSixSeeds': d_stats['min'],
            'pairedDeltaMaxMagSixSeeds': d_stats['max'],
            'medianReportedDeltaSigmaMag': med_d_sigma,
            'deltaEmpiricalSdToMedianReportedSigma': d_ratio,
            'rayRatioMedian': ray_ratio_summary['median'],
            'rayRatioP90': ray_ratio_summary['p90NearestRank'],
            'rayRatioMax': ray_ratio_summary['max'],
        }
        row_records.append(rec)
        detailed[str(row)] = {
            'replicates': ALL_REPLICATES,
            'defaultQ': q_stats,
            'reportedDefaultQStdConservative': default_sigma,
            'defaultEmpiricalSdToMedianReportedSigma': q_ratio,
            'pairedDeltaMag': d_stats,
            'reportedDeltaSigmaMag': delta_sigma,
            'deltaEmpiricalSdToMedianReportedSigma': d_ratio,
            'rayDefaultSdToReportedSigma': ray_ratio_summary,
        }

    with (a.output / 'row-summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row_records[0].keys()))
        w.writeheader(); w.writerows(row_records)
    with (a.output / 'ray-summary.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(ray_records[0].keys()))
        w.writeheader(); w.writerows(ray_records)

    result = {
        'schemaVersion': 1,
        'stageId': NEW_STAGE,
        'status': 'EMPIRICAL_BETWEEN_SEED_AUDIT_COMPLETE',
        'rowUniverse': ROWS,
        'replicateUniverse': ALL_REPLICATES,
        'photonBudgetPerRayPerCondition': 50_000,
        'rows': detailed,
        'interpretationBoundary': (
            'Numerical reproducibility audit only. Empirical between-seed variability is compared with the existing '
            'spectral-std propagation; this does not establish MYSTIC bias, validate HRRR physics, score Taylor '
            'observations, or authorize atmosphere/Level-B/F/tau/production changes.'
        ),
    }
    (a.output / 'metrics.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')

    lines = [
        '# Taylor broadband Monte Carlo reproducibility audit v1',
        '',
        'Six independent 50k-photon paired seeds per row: immutable prior replicates 1-2 plus fresh replicates 3-6.',
        'No Taylor observed-minus-model residual is used in this analysis.',
        '',
        '|row|default Q mean|default Q sample SD|CV|SD / median reported Q sigma|paired delta mean (mag)|paired delta sample SD (mag)|SD / median reported delta sigma|ray ratio median / p90 / max|',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in row_records:
        lines.append(
            f"|{r['row']}|{r['defaultQMeanSixSeeds']:.6g}|{r['defaultQSampleSdSixSeeds']:.6g}|"
            f"{100*r['defaultQCvSixSeeds']:.3f}%|{r['defaultEmpiricalSdToMedianReportedSigma']:.2f}|"
            f"{r['pairedDeltaMeanMagSixSeeds']:+.5f}|{r['pairedDeltaSampleSdMagSixSeeds']:.5f}|"
            f"{r['deltaEmpiricalSdToMedianReportedSigma']:.2f}|"
            f"{r['rayRatioMedian']:.1f} / {r['rayRatioP90']:.1f} / {r['rayRatioMax']:.1f}|"
        )
    lines += [
        '',
        '**Boundary:** the empirical SDs are between-seed diagnostics at one fixed 50k photon budget. They are not yet a photon-count convergence law. Any photon-scaling experiment requires a separate frozen identity.',
    ]
    (a.output / 'report.md').write_text('\n'.join(lines) + '\n')
    print((a.output / 'report.md').read_text())


if __name__ == '__main__':
    main()
