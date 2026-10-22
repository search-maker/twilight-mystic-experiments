#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def exact_insert_audit(default_text: str, cams_text: str, expected_tau_line: str):
    d = default_text.splitlines()
    c = cams_text.splitlines()
    if len(c) != len(d) + 1:
        raise RuntimeError('CAMS dry input does not contain exactly one added line')
    idx = [i for i, line in enumerate(c) if line == expected_tau_line]
    if len(idx) != 1:
        raise RuntimeError('expected tau line absent or duplicated')
    i = idx[0]
    if i == 0 or c[i - 1].strip() != 'aerosol_default':
        raise RuntimeError('tau line is not immediately after aerosol_default')
    if c[:i] + c[i + 1:] != d:
        raise RuntimeError('dry CAMS input differs from default beyond one inserted tau line')
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner', type=Path, required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--cams-profile', type=Path, required=True)
    ap.add_argument('--cams-summary', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)

    runner = load_module('cams_broadband_runner', a.runner)
    base = load_module('frozen_taylor_v1', a.baseline_runner)
    runner.load_and_gate_summary(a.cams_summary)
    profiles = runner.load_profile_csv(a.cams_profile)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise RuntimeError('unexpected Taylor-v1 ray count')

    data_dir = a.data_dir.resolve()
    atmosphere = (data_dir / 'atmmod/afglus.dat').resolve()
    endpoint_data = {
        name: runner.endpoint_layer_fractions(base, atmosphere, profiles[name])
        for name in runner.ENDPOINTS
    }
    if endpoint_data['analysis00']['gridKm'] != endpoint_data['forecast03']['gridKm']:
        raise RuntimeError('endpoint site grids differ')
    grid = endpoint_data['analysis00']['gridKm']

    audits = []
    for row in runner.ROWS:
        obs = base.load_observation(a.observations, row)
        fractions, w = runner.interpolate_layer_fractions(endpoint_data, runner.parse_utc(obs['utc']))
        row_dir = a.output / f'row-{row}'
        row_dir.mkdir(parents=True, exist_ok=True)
        tau = row_dir / 'cams-site-grid-tau.dat'
        tau_meta = runner.write_tau_file(grid, fractions, tau)
        aod = float(obs['aod550_primary_frozen'])
        for rep in (1, 2):
            for ray in rays:
                seed = runner.SEED_BASE[rep] + row * 1000 + int(ray['rayIndex'])
                # Same exact dry path and same seed on both sides. The CAMS input
                # must be byte-identical except for the one inserted tau line.
                audit_case = row_dir / f"rep-{rep}-ray-{int(ray['rayIndex']):02d}" / 'same-case'
                default_text = base.render(
                    data_dir, atmosphere, audit_case, obs, ray, aod,
                    runner.PHOTONS, seed,
                )
                cams_text = runner.insert_tau_line(default_text, tau)
                expected = f'aerosol_file tau {tau.resolve()}'
                position = exact_insert_audit(default_text, cams_text, expected)
                audits.append({
                    'row': row,
                    'replicate': rep,
                    'rayIndex': int(ray['rayIndex']),
                    'seed': seed,
                    'tauInsertionLineIndexZeroBased': position,
                    'defaultInputSha256': sha_text(default_text),
                    'camsInputSha256': sha_text(cams_text),
                    'timeInterpolationWeightForecast03': w,
                    'tauFileSha256': tau_meta['tauFileSha256'],
                })

    expected_count = len(runner.ROWS) * 2 * 64
    if len(audits) != expected_count:
        raise RuntimeError(f'wrong dry audit count {len(audits)} != {expected_count}')
    result = {
        'schemaVersion': 1,
        'stageId': runner.STAGE,
        'status': 'TAU_ONLY_INPUT_DELTA_PASS',
        'auditCount': len(audits),
        'rows': runner.ROWS,
        'replicates': [1, 2],
        'raysPerRowReplicate': 64,
        'audits': audits,
    }
    (a.output / 'preflight.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'auditCount', 'rows', 'replicates')}, sort_keys=True))


if __name__ == '__main__':
    main()
