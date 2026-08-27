#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

STAGE = 'taylor-broadband-photon-scaling-200k-v1'
ROWS = [23, 24, 25]
REPLICATES = [1, 2, 3, 4, 5, 6]
PHOTONS = 200_000
SEED_BASE = {
    1: 961_000_000,
    2: 962_000_000,
    3: 963_000_000,
    4: 964_000_000,
    5: 965_000_000,
    6: 966_000_000,
}
FROZEN_BROADBAND_STAGE = 'taylor-hrrr-broadband-vertical-shape-v1'


class Failure(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Failure(f'cannot import {path}')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--row', type=int, required=True)
    ap.add_argument('--replicate', type=int, choices=REPLICATES, required=True)
    ap.add_argument('--frozen-broadband-runner', type=Path, required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--uvspec', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args()

    if a.row not in ROWS:
        raise Failure('row outside frozen 200k universe')

    frozen = load_module('frozen_reviewed_broadband', a.frozen_broadband_runner)
    if frozen.STAGE != FROZEN_BROADBAND_STAGE:
        raise Failure(f'unexpected reviewed broadband stage {frozen.STAGE}')
    if list(frozen.ROWS) != ROWS or int(frozen.PHOTONS) != 50_000:
        raise Failure('reviewed broadband constants changed')
    if dict(frozen.SEED_BASE) != {1: 955_000_000, 2: 956_000_000}:
        raise Failure('reviewed broadband seed constants changed')

    base = load_module('frozen_taylor_v1', a.baseline_runner)
    obs = base.load_observation(a.observations, a.row)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise Failure(f'expected 64 Taylor-v1 rays, got {len(rays)}')

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'work'
    data_dir = a.data_dir.resolve()
    atmosphere = (data_dir / 'atmmod/afglus.dat').resolve()
    uvspec = a.uvspec.resolve()
    aod = float(obs['aod550_primary_frozen'])
    seed_base = SEED_BASE[a.replicate]

    records = []
    wl_ref = None
    aggregate_spec = aggregate_sigma2 = None

    for ray in rays:
        ray_index = int(ray['rayIndex'])
        seed = seed_base + a.row * 1000 + ray_index
        case_dir = work / f'ray-{ray_index:02d}'
        text = base.render(data_dir, atmosphere, case_dir, obs, ray, aod, PHOTONS, seed)
        if 'aerosol_file tau ' in text:
            raise Failure('default-only 200k input unexpectedly contains aerosol_file tau')
        rec, wl, spectrum, sigma_spectrum = frozen.run_condition(
            base, uvspec, text, case_dir, float(ray['thetaDeg']), tables
        )
        if wl_ref is None:
            wl_ref = wl.copy()
        elif len(wl_ref) != len(wl) or np.max(np.abs(wl_ref - wl)) > 1e-8:
            raise Failure('wavelength grid drift between rays')
        weight = float(ray['normalizedWeight'])
        aggregate_spec, aggregate_sigma2 = frozen.accumulate(
            aggregate_spec, aggregate_sigma2, weight, spectrum, sigma_spectrum
        )
        records.append({
            'rayIndex': ray_index,
            'thetaDeg': float(ray['thetaDeg']),
            'relativeAzimuthDeg': float(ray['relativeAzimuthDeg']),
            'normalizedWeight': weight,
            'seed': seed,
            'q': float(rec['q']),
            'qStdConservative': float(rec['qStdConservative']),
            'inputSha256': rec['inputSha256'],
            'radianceSha256': rec['radianceSha256'],
            'stdSha256': rec['stdSha256'],
            'spectrumRows': int(rec['spectrumRows']),
            'wavelengthStartNm': float(rec['wavelengthStartNm']),
            'wavelengthEndNm': float(rec['wavelengthEndNm']),
        })

    q = sum(r['normalizedWeight'] * r['q'] for r in records)
    qstd = math.sqrt(sum((r['normalizedWeight'] * r['qStdConservative']) ** 2 for r in records))
    if not math.isfinite(q) or q <= 0 or not math.isfinite(qstd) or qstd < 0:
        raise Failure('invalid aggregate Q or propagated sigma')
    if wl_ref is None or aggregate_spec is None or aggregate_sigma2 is None:
        raise Failure('aggregate spectral state missing')

    shutil.rmtree(work, ignore_errors=True)

    result = {
        'schemaVersion': 1,
        'stageId': STAGE,
        'status': 'COMPLETED',
        'row': a.row,
        'replicate': a.replicate,
        'utc': obs['utc'],
        'sunAltGeometricDeg': float(obs['sun_alt_geometric_deg']),
        'aod550Frozen': aod,
        'surfacePressureHpa': float(obs['surface_pressure_hpa']),
        'photonsPerRay': PHOTONS,
        'rayCount': len(rays),
        'seedBase': seed_base,
        'defaultQ': q,
        'defaultQStdConservative': qstd,
        'baselineRunnerSha256': sha(a.baseline_runner),
        'frozenBroadbandRunnerSha256': sha(a.frozen_broadband_runner),
        'observationsSha256': sha(a.observations),
        'responseSha256': sha(a.response),
        'rays': records,
        'boundary': 'Default-atmosphere broadband photon-count convergence audit only; no Taylor residual scoring or atmosphere/human-model conclusion.',
    }
    (out / 'row-replicate-result.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({
        'status': result['status'],
        'row': a.row,
        'replicate': a.replicate,
        'photonsPerRay': PHOTONS,
        'defaultQ': q,
        'defaultQStdConservative': qstd,
    }, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'stageId': STAGE, 'error': str(exc)}), file=sys.stderr)
        raise
