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

STAGE = 'taylor-aod-derivative-200k-crn-v1'
ROWS = [23, 24, 25]
REPLICATES = [1, 2, 3, 4, 5, 6]
AODS = [0.30, 0.40]
PHOTONS = 200_000
SEED_BASE = {
    1: 967_000_000,
    2: 968_000_000,
    3: 969_000_000,
    4: 970_000_000,
    5: 971_000_000,
    6: 972_000_000,
}


class Failure(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location('frozen_taylor_v1', path)
    if spec is None or spec.loader is None:
        raise Failure(f'cannot import Taylor-v1 runner {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def aggregate(records):
    q = sum(float(r['normalizedWeight']) * float(r['q']) for r in records)
    qstd = math.sqrt(sum((float(r['normalizedWeight']) * float(r['qStdConservative'])) ** 2 for r in records))
    return q, qstd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--row', type=int, required=True)
    ap.add_argument('--replicate', type=int, choices=REPLICATES, required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--uvspec', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args()

    if a.row not in ROWS:
        raise Failure('row outside frozen AOD derivative universe')

    base = load_module(a.baseline_runner)
    obs = base.load_observation(a.observations, a.row)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise Failure(f'expected exact 64-ray Taylor quadrature, got {len(rays)}')

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    atmosphere = (a.data_dir / 'atmmod/afglus.dat').resolve()
    data_dir = a.data_dir.resolve()
    uvspec = a.uvspec.resolve()
    seed_base = SEED_BASE[a.replicate]

    by_aod = {}
    for aod in AODS:
        records = []
        condition = f'aod-{aod:.2f}'
        for ray in rays:
            idx = int(ray['rayIndex'])
            seed = seed_base + a.row * 1000 + idx
            case_dir = out / condition / f'ray-{idx:02d}'
            rec = base.execute_one(
                uvspec,
                data_dir,
                atmosphere,
                obs,
                ray,
                aod,
                PHOTONS,
                seed,
                case_dir,
                tables,
                False,
            )
            records.append(rec)
        q, qstd = aggregate(records)
        if not math.isfinite(q) or q <= 0 or not math.isfinite(qstd) or qstd < 0:
            raise Failure(f'invalid aggregate broadband result at AOD {aod}')
        by_aod[f'{aod:.2f}'] = {
            'aod550': aod,
            'q': q,
            'qStdConservative': qstd,
            'rays': records,
        }

    low = by_aod['0.30']['q']
    high = by_aod['0.40']['q']
    delta_mag = -2.5 * math.log10(high / low)
    derivative = delta_mag / 0.10

    # CRN identity is binding: every corresponding low/high ray must use the same seed.
    for lo, hi in zip(by_aod['0.30']['rays'], by_aod['0.40']['rays']):
        if int(lo['rayIndex']) != int(hi['rayIndex']) or int(lo['seed']) != int(hi['seed']):
            raise Failure('paired CRN ray identity mismatch')

    shutil.rmtree(out / 'aod-0.30', ignore_errors=True)
    shutil.rmtree(out / 'aod-0.40', ignore_errors=True)

    result = {
        'schemaVersion': 1,
        'stageId': STAGE,
        'status': 'COMPLETED',
        'row': a.row,
        'replicate': a.replicate,
        'utc': obs['utc'],
        'sunAltGeometricDeg': float(obs['sun_alt_geometric_deg']),
        'frozenPrimaryAod550': float(obs['aod550_primary_frozen']),
        'surfacePressureHpa': float(obs['surface_pressure_hpa']),
        'aodConditions': AODS,
        'photonsPerRayPerCondition': PHOTONS,
        'rayCount': len(rays),
        'seedBase': seed_base,
        'q030': low,
        'q040': high,
        'q030StdConservative': by_aod['0.30']['qStdConservative'],
        'q040StdConservative': by_aod['0.40']['qStdConservative'],
        'deltaMag040Minus030': delta_mag,
        'finiteDifferenceDerivativeMagPerAod': derivative,
        'baselineRunnerSha256': sha(a.baseline_runner),
        'observationsSha256': sha(a.observations),
        'responseSha256': sha(a.response),
        'rays030': by_aod['0.30']['rays'],
        'rays040': by_aod['0.40']['rays'],
        'boundary': 'Paired common-random-number numerical convergence audit of the preregistered Taylor-v1 AOD 0.30-to-0.40 broadband finite difference only; no residual fitting or atmosphere revision.',
    }
    (out / 'row-replicate-result.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({
        'status': result['status'],
        'row': a.row,
        'replicate': a.replicate,
        'q030': low,
        'q040': high,
        'deltaMag040Minus030': delta_mag,
        'finiteDifferenceDerivativeMagPerAod': derivative,
    }, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'stageId': STAGE, 'error': str(exc)}), file=sys.stderr)
        raise
