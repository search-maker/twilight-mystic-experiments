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
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

STAGE = 'taylor-paired-profile-crn-v1'
EXECUTION_KEY = 'taylor-paired-profile-crn-v1:scientific:46'
ROWS = list(range(18, 28))
PAIR_BASES = [1511000000, 1512000000, 1513000000, 1514000000, 1515000000, 1516000000]
PHOTONS = 200000
ZENITH_OFFSET = 900
SITE_KM = 0.262
T0 = datetime(2025, 8, 8, 0, tzinfo=timezone.utc)
T3 = datetime(2025, 8, 8, 3, tzinfo=timezone.utc)
CAMS_PROFILE_SHA = '6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359'


class Failure(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Failure(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_manifest(path: Path):
    m = json.loads(path.read_text())
    if m.get('stageId') != STAGE or m.get('executionKey') != EXECUTION_KEY:
        raise Failure('wrong manifest identity')
    if m['frozenRows'] != ROWS:
        raise Failure('row universe changed')
    if m['mystic']['photonsPerRayPerCase'] != PHOTONS:
        raise Failure('photon budget changed')
    if m['mystic']['pairSeedBases'] != PAIR_BASES:
        raise Failure('pair seed bases changed')
    if m['profileCase']['profileSha256'] != CAMS_PROFILE_SHA:
        raise Failure('profile provenance changed')
    if not all(m['analysis'][k] is False for k in ('fitOffset', 'fitAod', 'fitProfile', 'fitAnyParameter')):
        raise Failure('fitting prohibition changed')
    return m


def parse_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)


def load_cams_profile(path: Path):
    if sha(path) != CAMS_PROFILE_SHA:
        raise Failure('CAMS profile checksum mismatch')
    rows = list(csv.DictReader(path.open(newline='')))
    by = {T0: [], T3: []}
    for r in rows:
        lead = int(r['leadHour'])
        if lead == 12:
            t = T0
        elif lead == 15:
            t = T3
        else:
            continue
        by[t].append((int(r['modelLevel']), float(r['heightAGL_m']), float(r['extinction532_m-1'])))
    profiles = {}
    sanity = {}
    for t in (T0, T3):
        rr = by[t]
        if len(rr) != 137 or sorted(x[0] for x in rr) != list(range(1, 138)):
            raise Failure(f'CAMS level universe invalid at {t}: {len(rr)}')
        pts = sorted((h, beta) for _, h, beta in rr)
        z = np.array([p[0] for p in pts], float)
        beta = np.array([p[1] for p in pts], float)
        if np.any(np.diff(z) <= 0) or np.any(beta < 0) or z[0] < 0:
            raise Failure('invalid CAMS height/extinction profile')
        z = np.concatenate(([0.0], z))
        beta = np.concatenate(([beta[0]], beta))
        integ = float(np.trapezoid(beta, z))
        if not integ > 0:
            raise Failure('non-positive CAMS extinction integral')
        profiles[t] = [(float(a), float(b)) for a, b in zip(z, beta)]
        sanity[t.isoformat()] = {
            'levelCount': 137,
            'firstFullLevelAGLM': float(z[1]),
            'topAGLM': float(z[-1]),
            'integratedTau532Discrete': integ,
            'peakExtinctionM1': float(beta.max()),
        }
    return profiles, sanity


def beta_at(points, z_m):
    x = np.array([p[0] for p in points], float)
    y = np.array([p[1] for p in points], float)
    return float(np.interp(z_m, x, y, left=y[0], right=0.0))


def time_beta(profiles, t, z_m):
    if not T0 <= t <= T3:
        raise Failure(f'observation outside CAMS interpolation interval: {t}')
    w = (t - T0).total_seconds() / (T3 - T0).total_seconds()
    return (1 - w) * beta_at(profiles[T0], z_m) + w * beta_at(profiles[T3], z_m)


def layer_tau_raw(profiles, t, lo_abs_km, hi_abs_km):
    if hi_abs_km <= lo_abs_km:
        return 0.0
    lo = (lo_abs_km - SITE_KM) * 1000.0
    hi = (hi_abs_km - SITE_KM) * 1000.0
    anchors = {lo, hi}
    for pts in profiles.values():
        for z, _ in pts:
            if lo < z < hi:
                anchors.add(z)
    zz = np.array(sorted(anchors), float)
    bb = np.array([time_beta(profiles, t, float(v)) for v in zz], float)
    return float(np.trapezoid(bb, zz))


def write_tau_profile(base, atmosphere: Path, profiles, t, out: Path):
    grid = base.atmosphere_grid(atmosphere, SITE_KM)
    layer = [layer_tau_raw(profiles, t, grid[i], grid[i + 1]) for i in range(len(grid) - 1)]
    total = sum(layer)
    if not total > 0:
        raise Failure('zero above-site CAMS extinction integral')
    tau = {grid[i]: layer[i] / total for i in range(len(layer))}
    tau[grid[-1]] = 0.0
    if abs(sum(tau.values()) - 1.0) > 1e-10:
        raise Failure('CAMS tau profile not normalized')
    out.write_text(
        '# independently retrieved CAMS 532-nm vertical extinction shape; normalized layer tau sum=1; proxy profile, not exact measured atmosphere\n'
        + '\n'.join(f'{z:.6f} {tau[z]:.15e}' for z in reversed(grid))
        + '\n'
    )
    return {
        'gridBottomKm': grid[0],
        'gridTopKm': grid[-1],
        'layerCount': len(grid) - 1,
        'interpolatedAboveSiteTau532BeforeNormalization': total,
        'tauSum': sum(tau.values()),
        'tauFileSha256': sha(out),
    }


def render_profile(base, data_dir: Path, atmosphere: Path, case_dir: Path, obs, ray, aod, seed, tau_file: Path):
    grid = base.atmosphere_grid(atmosphere, SITE_KM)
    sza = 90.0 - float(obs['sun_alt_geometric_deg'])
    umu = -math.cos(math.radians(ray['thetaDeg']))
    pressure = float(obs['surface_pressure_hpa'])
    solar = data_dir / 'solar_flux/atlas_plus_modtran'
    lines = [
        f'data_files_path {data_dir}',
        f'atmosphere_file {atmosphere}',
        f'source solar {solar}',
        'mol_abs_param crs',
        'wavelength 380 780',
        'day_of_year 220',
        f'sza {sza:.8f}',
        'phi0 0.0',
        'rte_solver mystic',
        'mc_spherical 1D',
        f'mc_photons {PHOTONS}',
        'mc_vroom off',
        'mc_std',
        f'mc_randomseed {seed}',
        f'mc_basename {case_dir / "mc"}',
        'mc_spectral_is 550.0',
        'albedo 0.150000',
        'aerosol_default',
        f'aerosol_file tau {tau_file.resolve()}',
        f'aerosol_set_tau_at_wvl 550 {aod:.8f}',
        f'pressure {pressure:.4f}',
        'atm_z_grid ' + ' '.join(f'{z:.6f}' for z in grid),
        'zout 0.000000',
        f'umu {umu:.10f}',
        f'phi {ray["relativeAzimuthDeg"]:.8f}',
        'quiet',
    ]
    return '\n'.join(lines) + '\n'


def execute_text(base, uvspec: Path, text: str, case_dir: Path, theta: float, tables):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / 'input-resolved.txt').write_text(text)
    syntax_s = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_s = base.run_process(uvspec, text, case_dir, syntax=False)
    rad = case_dir / 'mc.rad.spc'
    std = case_dir / 'mc.rad.std.spc'
    if not rad.is_file() or not std.is_file():
        raise Failure(f'missing MYSTIC spectra in {case_dir}')
    q, qstd, n, w0, w1 = base.integrate_ray(rad, std, theta, tables)
    if q < 0 or qstd < 0 or not math.isfinite(q) or not math.isfinite(qstd):
        raise Failure('invalid integrated SQM response')
    rec = {
        'q': q,
        'qStdConservativeNotUsedAsBetweenSeedEstimator': qstd,
        'syntaxSeconds': syntax_s,
        'solverSeconds': solver_s,
        'spectrumRows': n,
        'wavelengthStartNm': w0,
        'wavelengthEndNm': w1,
        'inputSha256': hashlib.sha256(text.encode()).hexdigest(),
        'radianceSha256': sha(rad),
        'stdSha256': sha(std),
    }
    shutil.rmtree(case_dir, ignore_errors=True)
    return rec


def baseline_text(base, data_dir, atmosphere, case_dir, obs, ray, aod, seed):
    return base.render(data_dir, atmosphere, case_dir, obs, ray, aod, PHOTONS, seed)


def aggregate(records):
    q = sum(r['normalizedWeight'] * r['q'] for r in records)
    if not q > 0:
        raise Failure('non-positive angular aggregate')
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--row', type=int, required=True)
    ap.add_argument('--pair', type=int, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--cams-profile', type=Path, required=True)
    ap.add_argument('--uvspec', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args()

    load_manifest(a.manifest)
    if a.row not in ROWS:
        raise Failure('row outside frozen universe')
    if not 1 <= a.pair <= len(PAIR_BASES):
        raise Failure('pair outside frozen universe')

    base = load_module(a.baseline_runner, 'taylor_v1')
    obs = base.load_observation(a.observations, a.row)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise Failure('expected exact 64-ray original SQM quadrature')

    profiles, sanity = load_cams_profile(a.cams_profile)
    t = parse_utc(obs['utc'])
    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    data = a.data_dir.resolve()
    atmosphere = (data / 'atmmod/afglus.dat').resolve()
    uvspec = a.uvspec.resolve()
    tau_path = out / 'cams-site-grid-tau.dat'
    tau_meta = write_tau_profile(base, atmosphere, profiles, t, tau_path)

    aod = float(obs['aod550_primary_frozen'])
    pair_base = PAIR_BASES[a.pair - 1]
    baseline_records = []
    profile_records = []
    for ray in rays:
        seed = pair_base + a.row * 1000 + ray['rayIndex']
        bdir = out / 'work' / 'baseline' / f'ray-{ray["rayIndex"]:02d}'
        pdir = out / 'work' / 'profile' / f'ray-{ray["rayIndex"]:02d}'
        btext = baseline_text(base, data, atmosphere, bdir, obs, ray, aod, seed)
        ptext = render_profile(base, data, atmosphere, pdir, obs, ray, aod, seed, tau_path)
        br = execute_text(base, uvspec, btext, bdir, ray['thetaDeg'], tables)
        pr = execute_text(base, uvspec, ptext, pdir, ray['thetaDeg'], tables)
        common = {
            'rayIndex': ray['rayIndex'],
            'thetaDeg': ray['thetaDeg'],
            'relativeAzimuthDeg': ray['relativeAzimuthDeg'],
            'normalizedWeight': ray['normalizedWeight'],
            'seed': seed,
        }
        baseline_records.append({**common, **br})
        profile_records.append({**common, **pr})

    baseline_q = aggregate(baseline_records)
    profile_q = aggregate(profile_records)

    zenith_ray = {'thetaDeg': 0.0, 'relativeAzimuthDeg': 0.0}
    zseed = pair_base + a.row * 1000 + ZENITH_OFFSET
    bzdir = out / 'work' / 'baseline-zenith'
    pzdir = out / 'work' / 'profile-zenith'
    bztext = baseline_text(base, data, atmosphere, bzdir, obs, zenith_ray, aod, zseed)
    pztext = render_profile(base, data, atmosphere, pzdir, obs, zenith_ray, aod, zseed, tau_path)
    bz = execute_text(base, uvspec, bztext, bzdir, 0.0, tables)
    pz = execute_text(base, uvspec, pztext, pzdir, 0.0, tables)

    result = {
        'schemaVersion': 1,
        'stageId': STAGE,
        'executionKey': EXECUTION_KEY,
        'status': 'COMPLETED',
        'row': a.row,
        'pair': a.pair,
        'pairSeedBase': pair_base,
        'utc': obs['utc'],
        'comparisonRole': obs['comparison_role'],
        'observedSQM': float(obs['observed_sqm_mag_arcsec2']),
        'sunAltGeometricDeg': float(obs['sun_alt_geometric_deg']),
        'aod550FrozenIdenticalBetweenCases': aod,
        'surfacePressureHpaFrozenIdenticalBetweenCases': float(obs['surface_pressure_hpa']),
        'photonsPerRayPerCase': PHOTONS,
        'rayCountWideSQM': 64,
        'spectralMode': 'MYSTIC ALIS 380-780 nm; mc_spectral_is 550 nm',
        'commonRandomNumbers': True,
        'baseline': {'wideQ': baseline_q, 'zenithQ': bz['q']},
        'profile': {'wideQ': profile_q, 'zenithQ': pz['q']},
        'camsProfileProvenance': {
            'classification': 'independently retrieved proxy vertical extinction shape; not exact measured atmosphere',
            'profileSha256': sha(a.cams_profile),
            'wavelengthNm': 532,
            'endpointSanity': sanity,
            'tauProfile': tau_meta,
        },
        'solverCalls': 130,
        'configuredPhotonHistories': 26000000,
        'mcStdFilesNotUsedAsBetweenSeedEstimator': True,
        'scientificExecution': True,
        'successDoesNotAuthorizeProduction': True,
    }
    (out / 'pair-result.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    shutil.rmtree(out / 'work', ignore_errors=True)
    print(json.dumps({
        'status': 'COMPLETED',
        'row': a.row,
        'pair': a.pair,
        'sunAltGeometricDeg': result['sunAltGeometricDeg'],
        'baselineWideQ': baseline_q,
        'profileWideQ': profile_q,
    }, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'stageId': STAGE, 'error': str(exc)}), file=sys.stderr)
        raise
