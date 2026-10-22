#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np

STAGE = 'taylor-hrrr-broadband-vertical-shape-v1'
ROWS = [23, 24, 25]
REPLICATES = [1, 2]
PHOTONS = 50_000
SEED_BASE = {1: 955_000_000, 2: 956_000_000}
HRRR_RAW_SHA256 = '929e787c15f8d689bf63a732152eb552e621542325e4942d4d48bf91eb6d75a9'


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


def insert_tau_line(default_text: str, tau_file: Path) -> str:
    lines = default_text.splitlines()
    positions = [i for i, line in enumerate(lines) if line.strip() == 'aerosol_default']
    if len(positions) != 1:
        raise Failure(f'expected exactly one aerosol_default line, got {len(positions)}')
    lines.insert(positions[0] + 1, f'aerosol_file tau {tau_file.resolve()}')
    return '\n'.join(lines) + '\n'


def normalized_render_lines(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('mc_basename '):
            out.append('mc_basename <CONDITION_DIR>')
        elif s.startswith('aerosol_file tau '):
            continue
        else:
            out.append(line)
    return out


def run_condition(base, uvspec: Path, text: str, case_dir: Path, theta: float, tables):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / 'input-resolved.txt').write_text(text)
    syntax_seconds = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_seconds = base.run_process(uvspec, text, case_dir, syntax=False)
    rad = case_dir / 'mc.rad.spc'
    std = case_dir / 'mc.rad.std.spc'
    if not rad.is_file() or not std.is_file():
        raise Failure('MYSTIC spectral output missing')
    wl, spectrum = base.parse_spectrum(rad)
    wl_std, sigma_spectrum = base.parse_spectrum(std)
    if len(wl) != len(wl_std) or np.max(np.abs(wl - wl_std)) > 1e-8:
        raise Failure('radiance/std wavelength grids differ')
    q, qstd, n, w0, w1 = base.integrate_ray(rad, std, theta, tables)
    rec = {
        'q': float(q),
        'qStdConservative': float(qstd),
        'spectrumRows': int(n),
        'wavelengthStartNm': float(w0),
        'wavelengthEndNm': float(w1),
        'syntaxSeconds': float(syntax_seconds),
        'solverSeconds': float(solver_seconds),
        'inputSha256': hashlib.sha256(text.encode()).hexdigest(),
        'radianceSha256': sha(rad),
        'stdSha256': sha(std),
    }
    return rec, wl, spectrum, sigma_spectrum


def accumulate(total, sigma2, weight: float, spectrum, sigma_spectrum):
    if total is None:
        total = np.zeros_like(spectrum, dtype=float)
        sigma2 = np.zeros_like(sigma_spectrum, dtype=float)
    total += weight * spectrum
    sigma2 += (weight * sigma_spectrum) ** 2
    return total, sigma2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--row', type=int, required=True)
    ap.add_argument('--replicate', type=int, choices=REPLICATES, required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--hrrr-shape-runner', type=Path, required=True)
    ap.add_argument('--derived-channels', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--hrrr-raw', type=Path, required=True)
    ap.add_argument('--uvspec', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args()

    if a.row not in ROWS:
        raise Failure('row outside frozen broadband universe')
    if sha(a.hrrr_raw) != HRRR_RAW_SHA256:
        raise Failure('HRRR raw profile checksum mismatch before source helper')

    base = load_module('frozen_taylor_v1', a.baseline_runner)
    hrrr = load_module('frozen_hrrr_v3_shape', a.hrrr_shape_runner)
    derived = load_module('frozen_derived_channels', a.derived_channels)
    obs = base.load_observation(a.observations, a.row)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise Failure(f'expected 64 Taylor-v1 rays, got {len(rays)}')

    profiles, hrrr_sanity = hrrr.load_hrrr_raw(a.hrrr_raw)
    when = hrrr.parse_utc(obs['utc'])

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'work'
    data_dir = a.data_dir.resolve()
    atmosphere = (data_dir / 'atmmod/afglus.dat').resolve()
    uvspec = a.uvspec.resolve()
    tau_file = out / 'hrrr-site-grid-tau.dat'
    tau_meta = hrrr.write_tau_profile(base, atmosphere, profiles, when, tau_file)
    aod = float(obs['aod550_primary_frozen'])
    seed_base = SEED_BASE[a.replicate]

    records = []
    wl_ref = None
    default_spec = default_sigma2 = hrrr_spec = hrrr_sigma2 = None

    for ray in rays:
        ray_index = int(ray['rayIndex'])
        seed = seed_base + a.row * 1000 + ray_index
        default_dir = work / f'ray-{ray_index:02d}' / 'default'
        hrrr_dir = work / f'ray-{ray_index:02d}' / 'hrrr'
        default_text = base.render(data_dir, atmosphere, default_dir, obs, ray, aod, PHOTONS, seed)
        hrrr_base_text = base.render(data_dir, atmosphere, hrrr_dir, obs, ray, aod, PHOTONS, seed)
        hrrr_text = insert_tau_line(hrrr_base_text, tau_file)
        if normalized_render_lines(default_text) != normalized_render_lines(hrrr_text):
            raise Failure('HRRR condition changed Taylor-v1 input beyond tau line / mc_basename')
        if default_text.count('aerosol_file tau ') != 0 or hrrr_text.count('aerosol_file tau ') != 1:
            raise Failure('unexpected tau-line count')

        drec, dwl, dspec, dsig = run_condition(base, uvspec, default_text, default_dir, float(ray['thetaDeg']), tables)
        hrec, hwl, hspec, hsig = run_condition(base, uvspec, hrrr_text, hrrr_dir, float(ray['thetaDeg']), tables)
        if len(dwl) != len(hwl) or np.max(np.abs(dwl - hwl)) > 1e-8:
            raise Failure('paired default/HRRR wavelength grids differ')
        if wl_ref is None:
            wl_ref = dwl.copy()
        elif len(wl_ref) != len(dwl) or np.max(np.abs(wl_ref - dwl)) > 1e-8:
            raise Failure('wavelength grid drift between rays')
        weight = float(ray['normalizedWeight'])
        default_spec, default_sigma2 = accumulate(default_spec, default_sigma2, weight, dspec, dsig)
        hrrr_spec, hrrr_sigma2 = accumulate(hrrr_spec, hrrr_sigma2, weight, hspec, hsig)
        records.append({
            'rayIndex': ray_index,
            'thetaDeg': float(ray['thetaDeg']),
            'relativeAzimuthDeg': float(ray['relativeAzimuthDeg']),
            'normalizedWeight': weight,
            'seed': seed,
            'default': drec,
            'hrrrShape': hrec,
        })

    default_q = sum(r['normalizedWeight'] * r['default']['q'] for r in records)
    hrrr_q = sum(r['normalizedWeight'] * r['hrrrShape']['q'] for r in records)
    default_qstd = math.sqrt(sum((r['normalizedWeight'] * r['default']['qStdConservative']) ** 2 for r in records))
    hrrr_qstd = math.sqrt(sum((r['normalizedWeight'] * r['hrrrShape']['qStdConservative']) ** 2 for r in records))
    if not all(math.isfinite(v) and v > 0 for v in (default_q, hrrr_q)):
        raise Failure('nonpositive aggregate original-SQM response')
    delta_mag = -2.5 * math.log10(hrrr_q / default_q)
    conservative_delta_sigma = (2.5 / math.log(10.0)) * math.sqrt((default_qstd/default_q)**2 + (hrrr_qstd/hrrr_q)**2)

    if wl_ref is None or default_spec is None or hrrr_spec is None:
        raise Failure('aggregate spectral state missing')
    wavelengths = [float(x) for x in wl_ref]
    default_radiance = [float(x) for x in default_spec]
    hrrr_radiance = [float(x) for x in hrrr_spec]
    default_std = [math.sqrt(float(x)) for x in default_sigma2]
    hrrr_std = [math.sqrt(float(x)) for x in hrrr_sigma2]
    default_channels = derived.derive_channels(wavelengths, default_radiance)
    hrrr_channels = derived.derive_channels(wavelengths, hrrr_radiance)
    default_mc_diag = derived.marginal_mc_std_diagnostics(wavelengths, default_radiance, default_std)
    hrrr_mc_diag = derived.marginal_mc_std_diagnostics(wavelengths, hrrr_radiance, hrrr_std)

    with (out / 'aggregate-spectrum.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            'wavelength_nm',
            'default_weighted_radiance', 'default_weighted_mc_std',
            'hrrr_weighted_radiance', 'hrrr_weighted_mc_std',
        ])
        for i, wl in enumerate(wavelengths):
            w.writerow([
                f'{wl:.8f}',
                f'{default_radiance[i]:.15e}', f'{default_std[i]:.15e}',
                f'{hrrr_radiance[i]:.15e}', f'{hrrr_std[i]:.15e}',
            ])

    # Keep exact per-ray input/output hashes and the paired aggregate spectrum,
    # but discard bulky raw per-ray spectra after all calculations succeed.
    shutil.rmtree(work, ignore_errors=True)

    result = {
        'schemaVersion': 1,
        'stageId': STAGE,
        'status': 'COMPLETED',
        'row': a.row,
        'replicate': a.replicate,
        'utc': obs['utc'],
        'comparisonRole': obs['comparison_role'],
        'observedSQM': float(obs['observed_sqm_mag_arcsec2']),
        'sunAltGeometricDeg': float(obs['sun_alt_geometric_deg']),
        'aod550Frozen': aod,
        'surfacePressureHpa': float(obs['surface_pressure_hpa']),
        'photonsPerRayPerCondition': PHOTONS,
        'rayCount': len(rays),
        'seedBase': seed_base,
        'hrrrRawSha256': sha(a.hrrr_raw),
        'hrrrColumnSanity': hrrr_sanity,
        'hrrrTauProfile': tau_meta,
        'defaultQ': default_q,
        'defaultQStdConservative': default_qstd,
        'hrrrShapeQ': hrrr_q,
        'hrrrShapeQStdConservative': hrrr_qstd,
        'deltaMagHrrrMinusDefault': delta_mag,
        'deltaMagIndependentMcSigmaConservative': conservative_delta_sigma,
        'defaultDerivedChannels': default_channels,
        'hrrrShapeDerivedChannels': hrrr_channels,
        'defaultMarginalMcDiagnostics': default_mc_diag,
        'hrrrShapeMarginalMcDiagnostics': hrrr_mc_diag,
        'aggregateSpectrumSha256': sha(out / 'aggregate-spectrum.csv'),
        'baselineRunnerSha256': sha(a.baseline_runner),
        'hrrrShapeRunnerSha256': sha(a.hrrr_shape_runner),
        'derivedChannelsSha256': sha(a.derived_channels),
        'observationsSha256': sha(a.observations),
        'responseSha256': sha(a.response),
        'rays': records,
        'boundary': 'Broadband spectral-robustness test of a normalized HRRR vertical-shape proxy only; no AOD fit, atmosphere replacement, production promotion, or human first-seeing claim.',
    }
    (out / 'row-replicate-result.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({
        'status': result['status'],
        'row': a.row,
        'replicate': a.replicate,
        'sunAltGeometricDeg': result['sunAltGeometricDeg'],
        'aod550Frozen': aod,
        'defaultQ': default_q,
        'hrrrShapeQ': hrrr_q,
        'deltaMagHrrrMinusDefault': delta_mag,
    }, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'stageId': STAGE, 'error': str(exc)}), file=sys.stderr)
        raise
