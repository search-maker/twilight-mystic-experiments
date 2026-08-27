#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2]
SEED_BASE = {1: 955_000_000, 2: 956_000_000}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def exact_insert_audit(default_text: str, hrrr_text: str, expected_tau_line: str):
    d = default_text.splitlines()
    h = hrrr_text.splitlines()
    if len(h) != len(d) + 1:
        raise RuntimeError('HRRR dry input does not contain exactly one extra line')
    hits = [i for i, line in enumerate(h) if line == expected_tau_line]
    if len(hits) != 1:
        raise RuntimeError('expected tau line missing or duplicated')
    i = hits[0]
    if i == 0 or h[i - 1].strip() != 'aerosol_default':
        raise RuntimeError('tau line not immediately after aerosol_default')
    if h[:i] + h[i + 1:] != d:
        raise RuntimeError('HRRR dry input differs from default beyond one tau line')
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', type=Path, required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--hrrr-shape-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--hrrr-raw', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)

    runner = load_module('review_runner', a.runner)
    base = load_module('frozen_taylor_v1', a.baseline_runner)
    hrrr = load_module('frozen_hrrr_v3', a.hrrr_shape_runner)
    if runner.sha(a.hrrr_raw) != runner.HRRR_RAW_SHA256:
        raise RuntimeError('HRRR raw hash mismatch')
    profiles, sanity = hrrr.load_hrrr_raw(a.hrrr_raw)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise RuntimeError('Taylor-v1 ray universe changed')
    data_dir = a.data_dir.resolve()
    atmosphere = (data_dir / 'atmmod/afglus.dat').resolve()

    audits = []
    for row in ROWS:
        obs = base.load_observation(a.observations, row)
        t = hrrr.parse_utc(obs['utc'])
        row_dir = a.output / f'row-{row}'
        row_dir.mkdir(parents=True, exist_ok=True)
        tau = row_dir / 'hrrr-site-grid-tau.dat'
        tau_meta = hrrr.write_tau_profile(base, atmosphere, profiles, t, tau)
        aod = float(obs['aod550_primary_frozen'])
        for rep in REPLICATES:
            for ray in rays:
                ray_index = int(ray['rayIndex'])
                seed = SEED_BASE[rep] + row * 1000 + ray_index
                same_case = row_dir / f'rep-{rep}-ray-{ray_index:02d}' / 'same-case'
                default_text = base.render(data_dir, atmosphere, same_case, obs, ray, aod, runner.PHOTONS, seed)
                hrrr_text = runner.insert_tau_line(default_text, tau)
                expected = f'aerosol_file tau {tau.resolve()}'
                position = exact_insert_audit(default_text, hrrr_text, expected)
                audits.append({
                    'row': row,
                    'replicate': rep,
                    'rayIndex': ray_index,
                    'seed': seed,
                    'tauInsertionLineIndexZeroBased': position,
                    'defaultInputSha256': hashlib.sha256(default_text.encode()).hexdigest(),
                    'hrrrInputSha256': hashlib.sha256(hrrr_text.encode()).hexdigest(),
                    'tauFileSha256': tau_meta['tauFileSha256'],
                })

    expected_count = len(ROWS) * len(REPLICATES) * 64
    if len(audits) != expected_count:
        raise RuntimeError(f'wrong audit count {len(audits)} != {expected_count}')
    result = {
        'schemaVersion': 1,
        'stageId': runner.STAGE,
        'status': 'TAU_ONLY_INPUT_DELTA_PASS',
        'auditCount': len(audits),
        'hrrrColumnSanity': sanity,
        'audits': audits,
    }
    (a.output / 'preflight.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'auditCount': result['auditCount']}, sort_keys=True))


if __name__ == '__main__':
    main()
