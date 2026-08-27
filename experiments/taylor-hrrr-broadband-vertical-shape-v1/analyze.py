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
STAGE = 'taylor-hrrr-broadband-vertical-shape-v1'
CHANNEL_KEYS = [
    'photopicLuminanceCdM2',
    'scotopicLuminanceScotCdM2',
    'johnsonVEffectiveRadiance_mW_m2_nm_sr',
]


def exact_results(root: Path):
    found = {}
    for p in root.rglob('row-replicate-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != STAGE or x.get('status') != 'COMPLETED':
            continue
        key = (int(x['row']), int(x['replicate']))
        if key in found:
            raise RuntimeError(f'duplicate result {key}')
        found[key] = x
    expected = {(r, q) for r in ROWS for q in REPLICATES}
    if set(found) != expected:
        raise RuntimeError(f'exact result universe required {sorted(expected)}, got {sorted(found)}')
    return found


def read_unique_csv(root: Path, filename: str):
    paths = list(root.rglob(filename))
    if len(paths) != 1:
        raise RuntimeError(f'expected one {filename} under {root}, got {len(paths)}')
    with paths[0].open(newline='') as f:
        return list(csv.DictReader(f))


def mag_shift(after: float, before: float) -> float:
    if not (math.isfinite(after) and math.isfinite(before) and after > 0 and before > 0):
        raise RuntimeError('nonpositive channel value')
    return -2.5 * math.log10(after / before)


def sample_stats(values):
    vals = [float(x) for x in values]
    return {
        'mean': statistics.mean(vals),
        'sampleSd': statistics.stdev(vals),
        'se': statistics.stdev(vals) / math.sqrt(len(vals)),
        'min': min(vals),
        'max': max(vals),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results-root', type=Path, required=True)
    ap.add_argument('--baseline-root', type=Path, required=True)
    ap.add_argument('--mono550-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)

    results = exact_results(a.results_root)
    baseline_rows = {int(r['row']): r for r in read_unique_csv(a.baseline_root, 'comparison.csv')}
    mono_rows = {int(r['row']): r for r in read_unique_csv(a.mono550_root, 'comparison.csv')}
    if any(r not in baseline_rows or r not in mono_rows for r in ROWS):
        raise RuntimeError('baseline or mono550 comparison missing frozen row')

    rec = []
    for row in ROWS:
        reps = [results[(row, q)] for q in REPLICATES]
        primary = [float(x['deltaMagHrrrMinusDefault']) for x in reps]
        pstats = sample_stats(primary)
        b = baseline_rows[row]
        m = mono_rows[row]
        baseline_residual = float(b['residual'])
        mono550 = float(m['delta_mag_550_hrrr_minus_default'])
        channel_stats = {}
        for key in CHANNEL_KEYS:
            vals = [mag_shift(float(x['hrrrShapeDerivedChannels'][key]), float(x['defaultDerivedChannels'][key])) for x in reps]
            channel_stats[key] = sample_stats(vals)
        rec.append({
            'row': row,
            'utc': b['utc'],
            'sun_alt_geometric_deg': float(b['sun_alt_geometric_deg']),
            'aod550': float(b['aod550']),
            'observed_sqm_mag': float(b['observed']),
            'frozen_baseline_model_sqm_mag': float(b['model']),
            'frozen_baseline_residual_obs_minus_model': baseline_residual,
            'replicate1_broadband_delta_mag': primary[0],
            'replicate2_broadband_delta_mag': primary[1],
            'mean_broadband_delta_mag': pstats['mean'],
            'broadband_sample_sd_mag': pstats['sampleSd'],
            'broadband_se_mag': pstats['se'],
            'frozen_mono550_delta_mag': mono550,
            'broadband_minus_mono550_mag': pstats['mean'] - mono550,
            'orientation_only_residual_after_broadband_shift': baseline_residual - pstats['mean'],
            'mean_photopic_delta_mag': channel_stats['photopicLuminanceCdM2']['mean'],
            'mean_scotopic_delta_mag': channel_stats['scotopicLuminanceScotCdM2']['mean'],
            'mean_johnson_v_delta_mag': channel_stats['johnsonVEffectiveRadiance_mW_m2_nm_sr']['mean'],
            'replicate1_default_q': float(reps[0]['defaultQ']),
            'replicate1_hrrr_q': float(reps[0]['hrrrShapeQ']),
            'replicate2_default_q': float(reps[1]['defaultQ']),
            'replicate2_hrrr_q': float(reps[1]['hrrrShapeQ']),
        })

    with (a.output / 'comparison.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rec[0].keys()))
        w.writeheader(); w.writerows(rec)

    broad = [r['mean_broadband_delta_mag'] for r in rec]
    mono = [r['frozen_mono550_delta_mag'] for r in rec]
    base_res = [r['frozen_baseline_residual_obs_minus_model'] for r in rec]
    orient = [r['orientation_only_residual_after_broadband_shift'] for r in rec]
    metrics = {
        'schemaVersion': 1,
        'stageId': STAGE,
        'status': 'ANALYSIS_COMPLETE',
        'rowUniverse': ROWS,
        'replicateUniverse': REPLICATES,
        'broadbandDeltaMag': {
            'meanAcrossRows': statistics.mean(broad),
            'range': [min(broad), max(broad)],
            'positiveDarkerRows': sum(x > 0 for x in broad),
        },
        'mono550FrozenDeltaMag': {
            'meanAcrossRows': statistics.mean(mono),
            'range': [min(mono), max(mono)],
        },
        'broadbandMinusMono550': {
            'meanAcrossRows': statistics.mean([x-y for x,y in zip(broad, mono)]),
            'maxAbsolute': max(abs(x-y) for x,y in zip(broad, mono)),
        },
        'baselineResidual': {
            'mean': statistics.mean(base_res),
            'rms': math.sqrt(statistics.mean(x*x for x in base_res)),
        },
        'orientationResidualAfterBroadbandShift': {
            'mean': statistics.mean(orient),
            'rms': math.sqrt(statistics.mean(x*x for x in orient)),
        },
        'rows': rec,
        'boundary': 'Broadband test of HRRR smoke mass as a normalized vertical-shape proxy only. Orientation residual is not a fitted reanalysis and does not establish the exact aerosol solution.',
    }
    (a.output / 'metrics.json').write_text(json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False) + '\n')

    lines = [
        '# Taylor HRRR broadband vertical-shape v1', '',
        'Full 380-780 nm original-SQM paired MYSTIC test of the independently frozen HRRR vertical-shape proxy, with Taylor-v1 row AOD550 and aerosol-default optical properties unchanged.', '',
        f"- mean broadband HRRR-shape minus default shift, rows 23-25: **{metrics['broadbandDeltaMag']['meanAcrossRows']:+.4f} mag**",
        f"- broadband range: **{metrics['broadbandDeltaMag']['range'][0]:+.4f} to {metrics['broadbandDeltaMag']['range'][1]:+.4f} mag**; darker direction **{metrics['broadbandDeltaMag']['positiveDarkerRows']}/3**",
        f"- frozen monochromatic-550 mean over the same rows: **{metrics['mono550FrozenDeltaMag']['meanAcrossRows']:+.4f} mag**",
        f"- mean broadband-minus-550 difference: **{metrics['broadbandMinusMono550']['meanAcrossRows']:+.4f} mag**; max absolute row difference **{metrics['broadbandMinusMono550']['maxAbsolute']:.4f} mag**",
        f"- frozen baseline obs-model residual mean: **{metrics['baselineResidual']['mean']:+.4f} mag**; orientation-only mean after broadband shape shift: **{metrics['orientationResidualAfterBroadbandShift']['mean']:+.4f} mag**",
        '',
        '|row|Sun alt|baseline obs-model|rep1 broadband|rep2 broadband|mean broadband|SE|mono550|broad-550|orientation residual|photopic|scotopic|Johnson V|',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in rec:
        lines.append(
            f"|{r['row']}|{r['sun_alt_geometric_deg']:.3f}|{r['frozen_baseline_residual_obs_minus_model']:+.3f}|"
            f"{r['replicate1_broadband_delta_mag']:+.3f}|{r['replicate2_broadband_delta_mag']:+.3f}|"
            f"{r['mean_broadband_delta_mag']:+.3f}|{r['broadband_se_mag']:.3f}|{r['frozen_mono550_delta_mag']:+.3f}|"
            f"{r['broadband_minus_mono550_mag']:+.3f}|{r['orientation_only_residual_after_broadband_shift']:+.3f}|"
            f"{r['mean_photopic_delta_mag']:+.3f}|{r['mean_scotopic_delta_mag']:+.3f}|{r['mean_johnson_v_delta_mag']:+.3f}|"
        )
    lines += [
        '',
        '**Boundary:** HRRR smoke mass is still only an independently observed vertical-shape proxy. This result can establish spectral robustness of the vertical-shape sensitivity; it cannot identify the exact Taylor aerosol extinction profile, replace the frozen Taylor-v1 atmosphere, validate Level-B, tune F/tau, or validate human first-seeing.',
    ]
    (a.output / 'report.md').write_text('\n'.join(lines) + '\n')
    print((a.output / 'report.md').read_text())


if __name__ == '__main__':
    main()
