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

STAGE = 'taylor-cams-broadband-vertical-shape-v1'
ROWS = [23, 24, 25]
PHOTONS = 50_000
SITE_KM = 0.262
T0 = datetime(2025, 8, 8, 0, 0, tzinfo=timezone.utc)
T3 = datetime(2025, 8, 8, 3, 0, tzinfo=timezone.utc)
SEED_BASE = {1: 951_000_000, 2: 952_000_000}
ENDPOINTS = ('analysis00', 'forecast03')
RATIO_MIN = 0.95
RATIO_MAX = 1.05


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
        raise Failure('cannot import frozen Taylor-v1 runner')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def load_and_gate_summary(path: Path) -> dict:
    data = json.loads(path.read_text())
    rows = data.get('endpoints')
    if not isinstance(rows, list):
        raise Failure('CAMS summary endpoints missing')
    by = {str(r.get('endpoint')): r for r in rows}
    if set(by) != set(ENDPOINTS):
        raise Failure(f'wrong CAMS endpoint universe: {sorted(by)}')
    for name in ENDPOINTS:
        r = by[name]
        required = (
            'integratedExtinctionTau532',
            'directCamsAOD532',
            'directCamsAOD550',
            'surfacePressure_Pa',
            'nonzeroLevelCount',
        )
        if any(k not in r for k in required):
            raise Failure(f'{name}: summary field missing')
        if any(not _finite(r[k]) for k in required[:-1]):
            raise Failure(f'{name}: nonfinite summary field')
        tau = float(r['integratedExtinctionTau532'])
        aod532 = float(r['directCamsAOD532'])
        pressure = float(r['surfacePressure_Pa'])
        nonzero = int(r['nonzeroLevelCount'])
        if tau <= 0 or aod532 <= 0 or pressure <= 0 or nonzero <= 0:
            raise Failure(f'{name}: nonpositive endpoint evidence')
        ratio = tau / aod532
        if not RATIO_MIN <= ratio <= RATIO_MAX:
            raise Failure(f'{name}: integrated tau/AOD532 ratio {ratio:.9f} outside frozen gate')
        if 'integrationToDirectAOD532Ratio' in r:
            stated = float(r['integrationToDirectAOD532Ratio'])
            if not math.isfinite(stated) or abs(stated - ratio) > 1e-10:
                raise Failure(f'{name}: stated integration ratio mismatch')
    return {'raw': data, 'byEndpoint': by}


def load_profile_csv(path: Path) -> dict[str, list[tuple[float, float, int]]]:
    rows = list(csv.DictReader(path.open(newline='')))
    by: dict[str, list[tuple[float, float, int]]] = {k: [] for k in ENDPOINTS}
    for r in rows:
        endpoint = r.get('endpoint', '')
        if endpoint not in by:
            continue
        try:
            level = int(r['modelLevel'])
            altitude_km = float(r['siteAnchoredAltitude_m']) / 1000.0
            beta = float(r['extinction532_m-1'])
        except Exception as exc:
            raise Failure(f'{endpoint}: malformed profile row') from exc
        if not math.isfinite(altitude_km) or not math.isfinite(beta) or beta < 0:
            raise Failure(f'{endpoint}: invalid height/extinction value')
        by[endpoint].append((altitude_km, beta, level))

    for endpoint in ENDPOINTS:
        p = by[endpoint]
        if len(p) != 137:
            raise Failure(f'{endpoint}: expected 137 profile rows, got {len(p)}')
        if {x[2] for x in p} != set(range(1, 138)):
            raise Failure(f'{endpoint}: wrong model-level universe')
        p.sort(key=lambda x: x[0])
        z = np.asarray([x[0] for x in p], float)
        beta = np.asarray([x[1] for x in p], float)
        if np.any(np.diff(z) <= 0):
            raise Failure(f'{endpoint}: reconstructed height grid not strictly increasing')
        if not np.any(beta > 0):
            raise Failure(f'{endpoint}: all extinction values are zero')
    return by


def integrate_layer(profile: list[tuple[float, float, int]], lo_km: float, hi_km: float) -> float:
    if hi_km <= lo_km:
        raise Failure('nonpositive atmosphere layer thickness')
    xp = np.asarray([x[0] for x in profile], float)
    yp = np.asarray([x[1] for x in profile], float)
    anchors = [lo_km, hi_km]
    anchors.extend(float(z) for z in xp if lo_km < z < hi_km)
    x = np.asarray(sorted(set(anchors)), float)
    # The CAMS full-level center nearest the surface is used down to the exact
    # 0.262-km site boundary; above the highest CAMS level aerosol extinction is zero.
    y = np.interp(x, xp, yp, left=float(yp[0]), right=0.0)
    # beta is m^-1 while x is km.
    return float(np.trapezoid(y, x) * 1000.0)


def endpoint_layer_fractions(base, atmosphere: Path, profile) -> dict:
    grid = base.atmosphere_grid(atmosphere, SITE_KM)
    tau = [integrate_layer(profile, grid[i], grid[i + 1]) for i in range(len(grid) - 1)]
    total = float(sum(tau))
    if not total > 0:
        raise Failure('zero above-site CAMS optical depth')
    fractions = np.asarray(tau, float) / total
    if np.any(fractions < 0) or abs(float(fractions.sum()) - 1.0) > 1e-12:
        raise Failure('endpoint layer fractions failed normalization')
    return {
        'gridKm': [float(x) for x in grid],
        'aboveSiteTau532FromProfile': total,
        'fractions': fractions,
    }


def interpolate_layer_fractions(endpoint_data: dict, when: datetime) -> tuple[np.ndarray, float]:
    if not T0 <= when <= T3:
        raise Failure('Taylor row outside frozen 00Z-03Z CAMS interpolation interval')
    a = endpoint_data['analysis00']['fractions']
    b = endpoint_data['forecast03']['fractions']
    if len(a) != len(b):
        raise Failure('CAMS endpoint layer grids differ')
    w = (when - T0).total_seconds() / (T3 - T0).total_seconds()
    f = (1.0 - w) * a + w * b
    total = float(f.sum())
    if not total > 0:
        raise Failure('interpolated profile has zero optical depth')
    f = f / total
    if np.any(f < 0) or abs(float(f.sum()) - 1.0) > 1e-12:
        raise Failure('interpolated layer fractions failed normalization')
    return f, float(w)


def write_tau_file(grid: list[float], fractions: np.ndarray, path: Path) -> dict:
    if len(grid) != len(fractions) + 1:
        raise Failure('tau/grid dimension mismatch')
    tau_at_lower = {float(grid[i]): float(fractions[i]) for i in range(len(fractions))}
    tau_at_lower[float(grid[-1])] = 0.0
    descending = list(reversed([float(x) for x in grid]))
    text = '# Same-cycle CAMS normalized vertical aerosol optical-depth shape; layer tau sum=1\n'
    text += '\n'.join(f'{z:.6f} {tau_at_lower[z]:.15e}' for z in descending) + '\n'
    path.write_text(text)
    return {
        'tauFileSha256': sha(path),
        'layerCount': len(fractions),
        'tauSum': float(fractions.sum()),
        'gridBottomKm': float(grid[0]),
        'gridTopKm': float(grid[-1]),
    }


def insert_tau_line(default_text: str, tau_file: Path) -> str:
    lines = default_text.splitlines()
    positions = [i for i, x in enumerate(lines) if x.strip() == 'aerosol_default']
    if positions != [lines.index('aerosol_default')] if 'aerosol_default' in lines else []:
        raise Failure('ambiguous aerosol_default line')
    if len(positions) != 1:
        raise Failure('expected exactly one aerosol_default line')
    i = positions[0]
    lines.insert(i + 1, f'aerosol_file tau {tau_file.resolve()}')
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


def render_pair(base, data_dir, atmosphere, default_dir, cams_dir, obs, ray, aod, seed, tau_file):
    default_text = base.render(data_dir, atmosphere, default_dir, obs, ray, aod, PHOTONS, seed)
    cams_base = base.render(data_dir, atmosphere, cams_dir, obs, ray, aod, PHOTONS, seed)
    cams_text = insert_tau_line(cams_base, tau_file)
    if normalized_render_lines(default_text) != normalized_render_lines(cams_text):
        raise Failure('CAMS condition changed a Taylor-v1 input other than aerosol_file tau / mc_basename')
    if 'aerosol_file tau ' in default_text:
        raise Failure('default Taylor-v1 condition unexpectedly contains aerosol_file tau')
    if cams_text.count('aerosol_file tau ') != 1:
        raise Failure('CAMS condition tau line count is not one')
    return default_text, cams_text


def run_one(base, uvspec: Path, text: str, case_dir: Path, theta: float, tables):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / 'input-resolved.txt').write_text(text)
    syntax_seconds = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_seconds = base.run_process(uvspec, text, case_dir, syntax=False)
    rad = case_dir / 'mc.rad.spc'
    std = case_dir / 'mc.rad.std.spc'
    if not rad.is_file() or not std.is_file():
        raise Failure('MYSTIC output spectra missing')
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
    # Per-ray raw spectra are not retained. The exact input and raw-output hashes
    # plus paired aggregate spectra are retained instead.
    for p in case_dir.glob('mc*'):
        p.unlink(missing_ok=True)
    return rec, wl, spectrum, sigma_spectrum


def weighted_spectrum_accumulate(total, sigma2, weight, spectrum, sigma_spectrum):
    if total is None:
        total = np.zeros_like(spectrum, dtype=float)
        sigma2 = np.zeros_like(sigma_spectrum, dtype=float)
    total += weight * spectrum
    sigma2 += (weight * sigma_spectrum) ** 2
    return total, sigma2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--row', type=int, required=True)
    ap.add_argument('--replicate', type=int, choices=(1, 2), required=True)
    ap.add_argument('--baseline-runner', type=Path, required=True)
    ap.add_argument('--observations', type=Path, required=True)
    ap.add_argument('--response', type=Path, required=True)
    ap.add_argument('--cams-profile', type=Path, required=True)
    ap.add_argument('--cams-summary', type=Path, required=True)
    ap.add_argument('--uvspec', type=Path, required=True)
    ap.add_argument('--data-dir', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args()

    if a.row not in ROWS:
        raise Failure('row outside frozen broadband universe')

    base = load_module(a.baseline_runner)
    obs = base.load_observation(a.observations, a.row)
    tables = base.load_response(a.response)
    rays = base.quadrature(tables)
    if len(rays) != 64:
        raise Failure('Taylor-v1 ray universe changed')

    summary = load_and_gate_summary(a.cams_summary)
    profiles = load_profile_csv(a.cams_profile)
    data_dir = a.data_dir.resolve()
    atmosphere = (data_dir / 'atmmod/afglus.dat').resolve()
    uvspec = a.uvspec.resolve()

    endpoint_data = {}
    for endpoint in ENDPOINTS:
        endpoint_data[endpoint] = endpoint_layer_fractions(base, atmosphere, profiles[endpoint])
    if endpoint_data['analysis00']['gridKm'] != endpoint_data['forecast03']['gridKm']:
        raise Failure('endpoint site grids differ')

    when = parse_utc(obs['utc'])
    fractions, time_weight = interpolate_layer_fractions(endpoint_data, when)
    grid = endpoint_data['analysis00']['gridKm']

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tau_file = out / 'cams-site-grid-tau.dat'
    tau_meta = write_tau_file(grid, fractions, tau_file)
    (out / 'layer-fractions.json').write_text(json.dumps({
        'analysis00AboveSiteTau532': endpoint_data['analysis00']['aboveSiteTau532FromProfile'],
        'forecast03AboveSiteTau532': endpoint_data['forecast03']['aboveSiteTau532FromProfile'],
        'timeInterpolationWeightForecast03': time_weight,
        'gridKm': grid,
        'analysis00Fractions': endpoint_data['analysis00']['fractions'].tolist(),
        'forecast03Fractions': endpoint_data['forecast03']['fractions'].tolist(),
        'rowFractions': fractions.tolist(),
    }, indent=2, sort_keys=True, allow_nan=False) + '\n')

    aod = float(obs['aod550_primary_frozen'])
    seed_base = SEED_BASE[a.replicate]
    records = []
    wl_ref = None
    default_spec = default_sigma2 = cams_spec = cams_sigma2 = None

    for ray in rays:
        seed = seed_base + a.row * 1000 + int(ray['rayIndex'])
        default_dir = out / 'work' / f"ray-{int(ray['rayIndex']):02d}" / 'default'
        cams_dir = out / 'work' / f"ray-{int(ray['rayIndex']):02d}" / 'cams'
        default_text, cams_text = render_pair(
            base, data_dir, atmosphere, default_dir, cams_dir, obs, ray, aod, seed, tau_file
        )
        drec, dwl, dspec, dsig = run_one(base, uvspec, default_text, default_dir, float(ray['thetaDeg']), tables)
        crec, cwl, cspec, csig = run_one(base, uvspec, cams_text, cams_dir, float(ray['thetaDeg']), tables)
        if len(dwl) != len(cwl) or np.max(np.abs(dwl - cwl)) > 1e-8:
            raise Failure('paired default/CAMS wavelength grids differ')
        if wl_ref is None:
            wl_ref = dwl.copy()
        elif len(wl_ref) != len(dwl) or np.max(np.abs(wl_ref - dwl)) > 1e-8:
            raise Failure('ray wavelength grid drift')
        weight = float(ray['normalizedWeight'])
        default_spec, default_sigma2 = weighted_spectrum_accumulate(default_spec, default_sigma2, weight, dspec, dsig)
        cams_spec, cams_sigma2 = weighted_spectrum_accumulate(cams_spec, cams_sigma2, weight, cspec, csig)
        records.append({
            'rayIndex': int(ray['rayIndex']),
            'thetaDeg': float(ray['thetaDeg']),
            'relativeAzimuthDeg': float(ray['relativeAzimuthDeg']),
            'normalizedWeight': weight,
            'seed': seed,
            'default': drec,
            'camsShape': crec,
        })

    shutil.rmtree(out / 'work', ignore_errors=True)

    default_q = sum(r['normalizedWeight'] * r['default']['q'] for r in records)
    cams_q = sum(r['normalizedWeight'] * r['camsShape']['q'] for r in records)
    default_qstd = math.sqrt(sum((r['normalizedWeight'] * r['default']['qStdConservative']) ** 2 for r in records))
    cams_qstd = math.sqrt(sum((r['normalizedWeight'] * r['camsShape']['qStdConservative']) ** 2 for r in records))
    if default_q <= 0 or cams_q <= 0:
        raise Failure('nonpositive aggregate SQM-response integral')
    delta_mag = -2.5 * math.log10(cams_q / default_q)

    if wl_ref is None or default_spec is None or cams_spec is None:
        raise Failure('aggregate spectra missing')
    with (out / 'aggregate-spectrum.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['wavelength_nm', 'default_weighted_radiance', 'default_weighted_mc_std',
                    'cams_weighted_radiance', 'cams_weighted_mc_std'])
        for i in range(len(wl_ref)):
            w.writerow([
                f'{float(wl_ref[i]):.8f}',
                f'{float(default_spec[i]):.15e}',
                f'{math.sqrt(float(default_sigma2[i])):.15e}',
                f'{float(cams_spec[i]):.15e}',
                f'{math.sqrt(float(cams_sigma2[i])):.15e}',
            ])

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
        'defaultQ': default_q,
        'defaultQStdConservative': default_qstd,
        'camsShapeQ': cams_q,
        'camsShapeQStdConservative': cams_qstd,
        'deltaMagCamsMinusDefault': delta_mag,
        'camsEndpointSummary': summary['byEndpoint'],
        'profileInterpolationWeightForecast03': time_weight,
        'tauProfile': tau_meta,
        'camsProfileSha256': sha(a.cams_profile),
        'camsSummarySha256': sha(a.cams_summary),
        'baselineRunnerSha256': sha(a.baseline_runner),
        'observationsSha256': sha(a.observations),
        'responseSha256': sha(a.response),
        'aggregateSpectrumSha256': sha(out / 'aggregate-spectrum.csv'),
        'rays': records,
        'boundary': 'Paired broadband vertical-shape diagnostic only; no AOD fit, parameter tuning, production promotion, or human first-seeing claim.',
    }
    (out / 'row-replicate-result.json').write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
    )
    print(json.dumps({
        'status': result['status'],
        'row': a.row,
        'replicate': a.replicate,
        'sunAltGeometricDeg': result['sunAltGeometricDeg'],
        'aod550Frozen': aod,
        'defaultQ': default_q,
        'camsShapeQ': cams_q,
        'deltaMagCamsMinusDefault': delta_mag,
    }, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'stageId': STAGE, 'error': str(exc)}), file=sys.stderr)
        raise
