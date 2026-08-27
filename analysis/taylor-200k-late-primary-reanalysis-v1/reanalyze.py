#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROWS = [23, 24, 25]
MAG_FACTOR = 2.5 / math.log(10.0)


def find_one(root: Path, name: str) -> Path:
    found = list(root.rglob(name))
    if len(found) != 1:
        raise RuntimeError(f'expected exactly one {name} under {root}, got {len(found)}')
    return found[0]


def load_comparison(root: Path):
    with find_one(root, 'comparison.csv').open(newline='') as f:
        rows = {int(r['row']): r for r in csv.DictReader(f)}
    if set(rows) != set(range(1, 33)):
        raise RuntimeError('Taylor-v1 comparison universe is not exact rows 1..32')
    return rows


def load_old_q(root: Path):
    data = json.loads(find_one(root, 'default-replication.json').read_text())
    if data.get('stageId') != 'taylor-hrrr-broadband-vertical-shape-v1':
        raise RuntimeError('wrong default-gate stage')
    checks = data.get('checks')
    if not isinstance(checks, list):
        raise RuntimeError('default gate checks missing')
    by = {r: set() for r in ROWS}
    for x in checks:
        row = int(x['row'])
        if row in by:
            by[row].add(float(x['immutableTaylorV1Q']))
    out = {}
    for row in ROWS:
        if len(by[row]) != 1:
            raise RuntimeError(f'row {row}: immutable Taylor-v1 Q is not unique')
        out[row] = next(iter(by[row]))
    return out


def load_200k(root: Path):
    data = json.loads(find_one(root, 'metrics.json').read_text())
    if data.get('stageId') != 'taylor-broadband-photon-scaling-200k-v1':
        raise RuntimeError('wrong 200k analysis stage')
    if data.get('status') != 'PHOTON_SCALING_50K_TO_200K_COMPLETE':
        raise RuntimeError('200k analysis is not complete')
    if int(data.get('freshPhotonBudgetPerRay', -1)) != 200_000:
        raise RuntimeError('wrong 200k photon budget')
    if int(data.get('reference50kArtifactId', -1)) != 9634873751:
        raise RuntimeError('wrong frozen 50k reference in 200k artifact')
    rows = data.get('rows', {})
    if set(rows) != {'23', '24', '25'}:
        raise RuntimeError('wrong 200k row universe')
    return data


def central_metrics(comparison, replacements, lo, hi):
    vals = []
    for row in range(lo, hi + 1):
        residual = replacements[row]['revisedResidualMag'] if row in replacements else float(comparison[row]['residual'])
        vals.append(residual)
    n = len(vals)
    return {
        'n': n,
        'meanResidualMag': sum(vals) / n,
        'rmsMag': math.sqrt(sum(x * x for x in vals) / n),
        'maeMag': sum(abs(x) for x in vals) / n,
        'maxAbsMag': max(abs(x) for x in vals),
        'statisticalClassificationReissued': False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--taylor-v1-analysis-root', type=Path, required=True)
    ap.add_argument('--default-gate-root', type=Path, required=True)
    ap.add_argument('--analysis-200k-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)

    comparison = load_comparison(a.taylor_v1_analysis_root)
    old_q = load_old_q(a.default_gate_root)
    m200 = load_200k(a.analysis_200k_root)

    revised = {}
    table = []
    for row in ROWS:
        legacy = comparison[row]
        r200 = m200['rows'][str(row)]
        q_new = float(r200['fresh200k']['mean'])
        q_sd = float(r200['fresh200k']['sampleSd'])
        q_se = float(r200['fresh200k']['se'])
        if q_new <= 0 or q_sd < 0 or q_se < 0:
            raise RuntimeError(f'row {row}: invalid 200k empirical Q state')

        delta_model = -2.5 * math.log10(q_new / old_q[row])
        legacy_model = float(legacy['model'])
        observed = float(legacy['observed'])
        revised_model = legacy_model + delta_model
        revised_residual = observed - revised_model
        single_run_sd_mag = MAG_FACTOR * q_sd / q_new
        mean_se_mag = MAG_FACTOR * q_se / q_new

        # Cross-check the already-frozen magnitude-equivalent 200k scatter.
        admitted_mag_sd = float(r200['magnitudeEquivalentEmpiricalSd200k'])
        if abs(single_run_sd_mag - admitted_mag_sd) > 1e-12:
            raise RuntimeError(f'row {row}: magnitude-equivalent scatter mismatch')

        rec = {
            'row': row,
            'utc': legacy['utc'],
            'sunAltGeometricDeg': float(legacy['sun_alt_geometric_deg']),
            'observedSqmMagArcsec2': observed,
            'legacySingleSeedQ': old_q[row],
            'legacyModelMagArcsec2': legacy_model,
            'legacyResidualObsMinusModelMag': float(legacy['residual']),
            'legacyReportedSpectralStdSigmaMagDeprecatedForBroadbandMc': float(legacy['sigma_mc']),
            'sixSeed200kMeanQ': q_new,
            'sixSeed200kSampleSdQ': q_sd,
            'sixSeed200kSeQ': q_se,
            'modelShiftFromQEstimatorMag': delta_model,
            'revisedModelMagArcsec2': revised_model,
            'revisedResidualMag': revised_residual,
            'empiricalNumericalScatterSingle200kRunMag': single_run_sd_mag,
            'numericalSeOfSixRunMeanMag': mean_se_mag,
        }
        revised[row] = rec
        table.append(rec)

    old_late = [float(comparison[r]['residual']) for r in ROWS]
    new_late = [revised[r]['revisedResidualMag'] for r in ROWS]
    late_summary = {
        'rows': ROWS,
        'legacyMeanResidualMag': sum(old_late) / len(old_late),
        'revisedMeanResidualMag': sum(new_late) / len(new_late),
        'legacyRmsMag': math.sqrt(sum(x*x for x in old_late) / len(old_late)),
        'revisedRmsMag': math.sqrt(sum(x*x for x in new_late) / len(new_late)),
        'legacyMaxAbsMag': max(abs(x) for x in old_late),
        'revisedMaxAbsMag': max(abs(x) for x in new_late),
    }

    out = {
        'schemaVersion': 1,
        'stageId': 'taylor-200k-late-primary-reanalysis-v1',
        'status': 'ANALYSIS_ONLY_COMPLETE',
        'rows': table,
        'latePrimaryRows23to25CentralOnly': late_summary,
        'primaryRows1to25CentralOnly': central_metrics(comparison, revised, 1, 25),
        'nominalRows8to25CentralOnly': central_metrics(comparison, revised, 8, 25),
        'boundary': (
            'Deterministic analysis-only replacement of rows23-25 legacy single-seed broadband Q by the frozen six-seed '
            '200k mean Q. No solver, atmosphere change, fit, or residual-driven parameter choice. Central residual metrics '
            'are recomputed only. Taylor-v1 covariance chi-square, timing derivative, AOD derivative/uncertainty, and '
            'ABSOLUTE_CONSISTENT/SHAPE_CONSISTENT classifications are NOT reissued because those legacy broadband '
            'derivatives/uncertainties have not yet received equivalent multi-seed convergence treatment.'
        ),
    }
    (a.output / 'metrics.json').write_text(json.dumps(out, indent=2, sort_keys=True, allow_nan=False) + '\n')

    fields = list(table[0].keys())
    with (a.output / 'rows23-25.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(table)

    lines = [
        '# Taylor late-primary reanalysis using six-seed 200k broadband means',
        '',
        'This is analysis-only. The Taylor atmosphere, AOD, geometry, original-SQM response, Vega calibration, and observations are unchanged.',
        '',
        '|row|legacy residual|200k mean model shift|revised residual|single-run empirical numerical SD|SE of six-run mean|',
        '|---:|---:|---:|---:|---:|---:|',
    ]
    for r in table:
        lines.append(
            f"|{r['row']}|{r['legacyResidualObsMinusModelMag']:+.4f}|{r['modelShiftFromQEstimatorMag']:+.4f}|"
            f"{r['revisedResidualMag']:+.4f}|{r['empiricalNumericalScatterSingle200kRunMag']:.4f}|"
            f"{r['numericalSeOfSixRunMeanMag']:.4f}|"
        )
    lines += [
        '',
        f"Rows23-25 max |residual|: **{late_summary['legacyMaxAbsMag']:.4f} -> {late_summary['revisedMaxAbsMag']:.4f} mag**.",
        f"Rows23-25 RMS: **{late_summary['legacyRmsMag']:.4f} -> {late_summary['revisedRmsMag']:.4f} mag**.",
        f"Primary rows1-25 central-only RMS after replacing only rows23-25: **{out['primaryRows1to25CentralOnly']['rmsMag']:.4f} mag** (legacy 0.1325 mag).",
        '',
        '**Important:** no updated Taylor validation classification is issued here. The legacy AOD/timing/MC uncertainty machinery used broadband ALIS quantities that have not all been re-converged with the new empirical between-seed method.',
    ]
    (a.output / 'report.md').write_text('\n'.join(lines) + '\n')
    print((a.output / 'report.md').read_text())


if __name__ == '__main__':
    main()
