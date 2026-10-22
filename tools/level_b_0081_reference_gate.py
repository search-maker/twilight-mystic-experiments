#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ALT = [
    5.333333, 7.333333, 9.333333, 12.333333, 14.333333, 18.333333,
    23.333333, 28.333333, 36.666667, 46.666667, 56.666667, 71.666667,
]
ELEV = [166.666667, 750.0, 1500.0, 2166.666667]
AOD = [0.066666667, 0.133333333, 0.233333333, 0.333333333]

LUT_ALT = [
    5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    17.5, 20, 22.5, 25, 27.5, 30,
    35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
]
LUT_ELEV = [0, 500, 1250, 2000, 2500]
LUT_AOD = [0.05, 0.10, 0.20, 0.30, 0.40]

MAX_LIMIT = 0.025
RMS_LIMIT = 0.010
PROTOCOL_NAME = 'STELLAR_TRANSPORT_VALIDATION_PROTOCOL_V2.md'


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def import_reference(app: Path):
    path = app / 'scientific-tools/visibility-v3/stellar_transmission_libradtran_v3.py'
    spec = importlib.util.spec_from_file_location('stellar_ref_v2', path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules['stellar_ref_v2'] = module
    spec.loader.exec_module(module)
    return module


def identity_coordinate(value: float) -> float:
    return float(value)


def cosecant_altitude_coordinate(altitude_deg: float) -> float:
    mu = math.sin(math.radians(float(altitude_deg)))
    if not mu > 0:
        raise ValueError('target altitude must be above the geometric horizon')
    return 1.0 / mu


def bracket(axis, value, coordinate=identity_coordinate):
    if value < axis[0] or value > axis[-1]:
        raise ValueError('outside LUT support')
    if value == axis[-1]:
        return len(axis) - 2, len(axis) - 1, 1.0
    for hi in range(1, len(axis)):
        if value < axis[hi]:
            lo = hi - 1
            c_lo = coordinate(axis[lo])
            c_hi = coordinate(axis[hi])
            c_value = coordinate(value)
            return lo, hi, (c_value - c_lo) / (c_hi - c_lo)
    raise AssertionError('failed to bracket value')


def interp_tau(lut, altitude, elevation, aod):
    alt_axis = lut['axes']['targetAltitudeDeg']
    elev_axis = lut['axes']['observerElevationM']
    aod_axis = lut['axes']['aod550']
    ab = bracket(alt_axis, altitude, cosecant_altitude_coordinate)
    eb = bracket(elev_axis, elevation)
    ob = bracket(aod_axis, aod)
    n_elev = len(elev_axis)
    n_aod = len(aod_axis)

    def case_index(ai, ei, oi):
        return ((ai * n_elev) + ei) * n_aod + oi

    def lerp(x, y, fraction):
        return x + (y - x) * fraction

    out = []
    for wavelength_index in range(len(lut['wavelengthNm'])):
        def value(ai, ei, oi):
            return float(lut['directOpticalDepth'][case_index(ai, ei, oi)][wavelength_index])

        c000 = value(ab[0], eb[0], ob[0])
        c001 = value(ab[0], eb[0], ob[1])
        c010 = value(ab[0], eb[1], ob[0])
        c011 = value(ab[0], eb[1], ob[1])
        c100 = value(ab[1], eb[0], ob[0])
        c101 = value(ab[1], eb[0], ob[1])
        c110 = value(ab[1], eb[1], ob[0])
        c111 = value(ab[1], eb[1], ob[1])
        c00 = lerp(c000, c001, ob[2])
        c01 = lerp(c010, c011, ob[2])
        c10 = lerp(c100, c101, ob[2])
        c11 = lerp(c110, c111, ob[2])
        c0 = lerp(c00, c01, eb[2])
        c1 = lerp(c10, c11, eb[2])
        out.append(lerp(c0, c1, ab[2]))
    return out


def extinction(flux, response, transmission):
    denominator = sum(float(f) * float(r) for f, r in zip(flux, response))
    numerator = sum(float(f) * float(r) * float(t)
                    for f, r, t in zip(flux, response, transmission))
    if not (denominator > 0 and numerator > 0):
        raise ValueError('non-positive Johnson-V integral')
    return -2.5 * math.log10(numerator / denominator)


def choose_templates(bundle):
    normal = [template for template in bundle['templates'] if template.get('abundance') == 'normal']
    if not normal:
        raise ValueError('no normal-abundance templates')
    blue = min(normal, key=lambda t: (float(t['bMinusVLandoltBmVc']), int(t['libraryNumber'])))
    solar = min(normal, key=lambda t: (abs(float(t['bMinusVLandoltBmVc']) - 0.65),
                                       int(t['libraryNumber'])))
    red = max(normal, key=lambda t: (float(t['bMinusVLandoltBmVc']),
                                     -int(t['libraryNumber'])))
    return [blue, solar, red]


def require_v2_lut(lut):
    axes = lut.get('axes', {})
    if axes.get('targetAltitudeDeg') != LUT_ALT:
        raise SystemExit('v2 LUT target-altitude axis does not match preregistered protocol')
    if axes.get('observerElevationM') != LUT_ELEV:
        raise SystemExit('v2 LUT observer-elevation axis does not match preregistered protocol')
    if axes.get('aod550') != LUT_AOD:
        raise SystemExit('v2 LUT AOD550 axis does not match preregistered protocol')
    if len(lut.get('directOpticalDepth', [])) != 675:
        raise SystemExit('v2 LUT must contain exactly 675 spectra')
    representation = lut.get('representation', {})
    if representation.get('directive') != 'MYSTIC-STATE-0081':
        raise SystemExit('v2 LUT directive binding mismatch')
    if representation.get('targetAltitudeCoordinate') != 'cosecant-altitude-1-over-sin-h':
        raise SystemExit('v2 LUT altitude interpolation binding mismatch')
    if representation.get('coefficientFitting') is not False:
        raise SystemExit('v2 LUT must declare coefficientFitting=false')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-dir', type=Path, required=True)
    parser.add_argument('--sed-bundle', type=Path, required=True)
    parser.add_argument('--lut', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    app = args.app_dir.resolve()
    bundle = load_json(args.sed_bundle)
    lut = load_json(args.lut)
    require_v2_lut(lut)

    band_path = app / 'scientific-tools/visibility-v3/generated/johnson-v-1nm.json'
    band = load_json(band_path)
    grid = list(range(380, 781))
    if bundle['wavelengthNm'] != grid or lut['wavelengthNm'] != grid or band['wavelengthNm'] != grid:
        raise SystemExit('wavelength grid mismatch')

    protocol_path = app / 'scientific-tools/visibility-v3' / PROTOCOL_NAME
    protocol_sha = sha256_file(protocol_path)
    if lut.get('provenance', {}).get('validationProtocolSha256') != protocol_sha:
        raise SystemExit('LUT protocol hash does not match exact v2 protocol bytes')

    templates = choose_templates(bundle)
    reference = import_reference(app)
    rows = []
    atmospheric_case_count = 0

    for altitude in ALT:
        for elevation in ELEV:
            for aod in AOD:
                atmospheric_case_count += 1
                reference_result = reference.run_reference(
                    target_altitude_deg=altitude,
                    aod550=aod,
                    observer_elevation_m=elevation,
                )
                reference_transmission = reference_result['spectrum']['lineOfSightDirectTransmission']
                tau = interp_tau(lut, altitude, elevation, aod)
                runtime_transmission = [math.exp(-value) for value in tau]
                for template in templates:
                    reference_av = extinction(template['fluxRelative'], band['response'], reference_transmission)
                    runtime_av = extinction(template['fluxRelative'], band['response'], runtime_transmission)
                    delta = runtime_av - reference_av
                    rows.append({
                        'targetAltitudeDeg': altitude,
                        'observerElevationM': elevation,
                        'aod550': aod,
                        'templateId': template['templateId'],
                        'bMinusV': template['bMinusVLandoltBmVc'],
                        'referenceAvMag': reference_av,
                        'runtimeAvMag': runtime_av,
                        'deltaAvMag': delta,
                        'absDeltaAvMag': abs(delta),
                    })

    if atmospheric_case_count != 192:
        raise SystemExit(f'expected 192 atmospheric cases, got {atmospheric_case_count}')
    if len(rows) != 576:
        raise SystemExit(f'expected 576 band comparisons, got {len(rows)}')

    max_error = max(row['absDeltaAvMag'] for row in rows)
    rms_error = math.sqrt(sum(row['deltaAvMag'] ** 2 for row in rows) / len(rows))
    passed = max_error <= MAX_LIMIT and rms_error <= RMS_LIMIT
    worst = sorted(rows, key=lambda row: row['absDeltaAvMag'], reverse=True)[:20]

    result = {
        'schemaVersion': 1,
        'gate': 'MYSTIC-STATE-0081-stellar-transport-v2-fresh-reference',
        'freshValidation': True,
        'predecessor0077AcceptanceCasesExcluded': True,
        'caseCount': len(rows),
        'atmosphericCaseCount': atmospheric_case_count,
        'validationAxes': {
            'targetAltitudeDeg': ALT,
            'observerElevationM': ELEV,
            'aod550': AOD,
        },
        'templates': [
            {
                'templateId': template['templateId'],
                'libraryNumber': template['libraryNumber'],
                'bMinusV': template['bMinusVLandoltBmVc'],
            }
            for template in templates
        ],
        'limits': {
            'maxAbsDeltaAvMag': MAX_LIMIT,
            'rmsDeltaAvMag': RMS_LIMIT,
        },
        'statistics': {
            'maxAbsDeltaAvMag': max_error,
            'rmsDeltaAvMag': rms_error,
        },
        'pass': passed,
        'protocolSha256': protocol_sha,
        'interpolation': {
            'quantity': 'directOpticalDepth',
            'targetAltitudeCoordinate': 'cosecant-altitude-1-over-sin-h',
            'observerElevationCoordinate': 'linear-meters',
            'aod550Coordinate': 'linear',
            'storedSpectrumCount': 675,
        },
        'hashes': {
            'sedBundleSha256': sha256_file(args.sed_bundle),
            'lutSha256': sha256_file(args.lut),
            'johnsonVGridSha256': sha256_file(band_path),
        },
        'worstCases': worst,
        'rows': rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    public_summary = {key: result[key] for key in (
        'gate', 'freshValidation', 'caseCount', 'atmosphericCaseCount', 'templates',
        'limits', 'statistics', 'pass', 'protocolSha256', 'interpolation', 'hashes', 'worstCases')}
    print(json.dumps(public_summary, sort_keys=True))
    raise SystemExit(0 if passed else 2)


if __name__ == '__main__':
    main()
