#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2]
STAGE = 'taylor-cams-broadband-vertical-shape-v1'


def load_results(root: Path):
    found = {}
    for p in root.rglob('row-replicate-result.json'):
        x = json.loads(p.read_text())
        if x.get('status') != 'COMPLETED' or x.get('stageId') != STAGE:
            continue
        key = (int(x['row']), int(x['replicate']))
        if key in found:
            raise RuntimeError(f'duplicate scientific result {key}')
        found[key] = x
    expected = {(r, q) for r in ROWS for q in REPLICATES}
    if set(found) != expected:
        raise RuntimeError(f'need exact result universe {sorted(expected)}, got {sorted(found)}')
    return found


def load_baseline(path: Path):
    rows = {}
    with path.open(newline='') as f:
        for r in csv.DictReader(f):
            n = int(r['row'])
            if n in ROWS:
                rows[n] = r
    if set(rows) != set(ROWS):
        raise RuntimeError(f'baseline missing rows: have {sorted(rows)}')
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-root', type=Path, required=True)
    ap.add_argument('--baseline-comparison', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)

    results = load_results(a.results_root)
    baseline = load_baseline(a.baseline_comparison)
    rows = []

    for row in ROWS:
        reps = [results[(row, rep)] for rep in REPLICATES]
        deltas = [float(x['deltaMagCamsMinusDefault']) for x in reps]
        mean = statistics.mean(deltas)
        sd = statistics.stdev(deltas)
        se = sd / math.sqrt(2.0)
        b = baseline[row]
        baseline_residual = float(b['residual'])
        baseline_model = float(b['model'])
        observed = float(b['observed'])
        revised_model_orientation = baseline_model + mean
        revised_residual_orientation = baseline_residual - mean
        rows.append({
            'row': row,
            'utc': b['utc'],
            'sun_alt_geometric_deg': float(b['sun_alt_geometric_deg']),
            'aod550': float(b['aod550']),
            'observed_sqm': observed,
            'frozen_baseline_model_sqm': baseline_model,
            'frozen_baseline_observed_minus_model': baseline_residual,
            'replicate1_delta_mag_cams_minus_default': deltas[0],
            'replicate2_delta_mag_cams_minus_default': deltas[1],
            'mean_delta_mag_cams_minus_default': mean,
            'paired_replicate_sd_mag': sd,
            'paired_replicate_se_mag': se,
            'orientation_only_revised_model_sqm': revised_model_orientation,
            'orientation_only_observed_minus_revised_model': revised_residual_orientation,
            'replicate1_default_q': float(reps[0]['defaultQ']),
            'replicate1_cams_q': float(reps[0]['camsShapeQ']),
            'replicate2_default_q': float(reps[1]['defaultQ']),
            'replicate2_cams_q': float(reps[1]['camsShapeQ']),
        })

    fields = list(rows[0].keys())
    with (a.output / 'comparison.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    baseline_residuals = [r['frozen_baseline_observed_minus_model'] for r in rows]
    revised_residuals = [r['orientation_only_observed_minus_revised_model'] for r in rows]
    shifts = [r['mean_delta_mag_cams_minus_default'] for r in rows]
    summary = {
        'schemaVersion': 1,
        'stageId': STAGE,
        'status': 'ANALYSIS_COMPLETE',
        'rowUniverse': ROWS,
        'replicateUniverse': REPLICATES,
        'meanBroadbandCamsMinusDefaultMag': statistics.mean(shifts),
        'rangeBroadbandCamsMinusDefaultMag': [min(shifts), max(shifts)],
        'directionDarkerCount': sum(x > 0 for x in shifts),
        'baselineResidualMeanMag': statistics.mean(baseline_residuals),
        'baselineResidualRmsMag': math.sqrt(statistics.mean(x * x for x in baseline_residuals)),
        'orientationResidualMeanAfterIndependentShiftMag': statistics.mean(revised_residuals),
        'orientationResidualRmsAfterIndependentShiftMag': math.sqrt(statistics.mean(x * x for x in revised_residuals)),
        'rows': rows,
        'boundary': (
            'The revised residual is orientation-only: it adds an independently computed vertical-shape model shift '
            'to the already-frozen Taylor-v1 broadband model. This analysis does not refit AOD, offset, response, '
            'human parameters, or any production model.'
        ),
    }
    (a.output / 'analysis.json').write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + '\n')

    table = '\n'.join(
        f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['frozen_baseline_observed_minus_model']:+.4f}|"
        f"{r['replicate1_delta_mag_cams_minus_default']:+.4f}|{r['replicate2_delta_mag_cams_minus_default']:+.4f}|"
        f"{r['mean_delta_mag_cams_minus_default']:+.4f}|{r['paired_replicate_se_mag']:.4f}|"
        f"{r['orientation_only_observed_minus_revised_model']:+.4f}|"
        for r in rows
    )
    report = f'''# Taylor CAMS broadband vertical-shape v1 result

Frozen universe: Taylor primary rows 23-25 only; two paired common-random-number replicates; full 380-780 nm original-SQM forward operator; unchanged Taylor-v1 row AOD550 and unchanged `aerosol_default` optical-property family.

- mean broadband CAMS-shape minus default shift: **{summary['meanBroadbandCamsMinusDefaultMag']:+.4f} mag**
- range: **{summary['rangeBroadbandCamsMinusDefaultMag'][0]:+.4f} to {summary['rangeBroadbandCamsMinusDefaultMag'][1]:+.4f} mag**
- darker direction: **{summary['directionDarkerCount']}/3 rows**
- frozen baseline residual mean: **{summary['baselineResidualMeanMag']:+.4f} mag**
- orientation-only residual mean after independent shift: **{summary['orientationResidualMeanAfterIndependentShiftMag']:+.4f} mag**
- frozen baseline residual RMS: **{summary['baselineResidualRmsMag']:.4f} mag**
- orientation-only residual RMS after independent shift: **{summary['orientationResidualRmsAfterIndependentShiftMag']:.4f} mag**

|row|Sun alt|baseline obs-model|rep1 shift|rep2 shift|mean shift|paired SE|orientation residual|
|---:|---:|---:|---:|---:|---:|---:|---:|
{table}

## Boundary

The last column is not a fitted reanalysis. It applies the independently computed CAMS vertical-shape broadband shift to the already-frozen Taylor-v1 prediction only to show direction and scale. No AOD, SQM zero point, response curve, row selection, F, tau, or human parameter is fit or changed. This test does not validate human first-seeing and does not promote Level-B or any production default.
'''
    (a.output / 'report.md').write_text(report)
    print(report)


if __name__ == '__main__':
    main()
