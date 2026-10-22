#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else 'atmosphere-artifact')
OUT.mkdir(parents=True, exist_ok=True)

OBS_START = datetime(2025, 8, 8, 0, 30, tzinfo=timezone.utc)
OBS_END = datetime(2025, 8, 8, 1, 30, tzinfo=timezone.utc)
OBS_MID = OBS_START + (OBS_END - OBS_START) / 2
QUALIFY = timedelta(hours=3)
AOD_MEAS_SIGMA = 0.01
SITES = [
    {'name': 'Windsor_B', 'lat': 42.283, 'lon': -83.083, 'elev_m': 200.0, 'distance_km': 51.6},
    {'name': 'Windsor_M', 'lat': 42.170, 'lon': -82.870, 'elev_m': 190.0, 'distance_km': 69.8},
]
AOD_SENSITIVITY = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'twilight-mystic-experiments/1.0 scientific-validation'})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def aeronet_url(site: str) -> str:
    params = {
        'site': site,
        'year': '2025', 'month': '8', 'day': '7',
        'year2': '2025', 'month2': '8', 'day2': '9',
        'AOD20': '1', 'AVG': '10', 'lunar_merge': '1', 'if_no_html': '1',
    }
    return 'https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v3?' + urllib.parse.urlencode(params)


def parse_float(value: str | None):
    if value is None:
        return None
    value = value.strip()
    if not value or value.startswith('-999') or value.lower() in {'nan', 'n/a'}:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_aeronet(raw: bytes, site: str):
    text = raw.decode('utf-8-sig', errors='replace')
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_i = None
    for i, line in enumerate(lines):
        if 'Date(dd:mm:yyyy)' in line and 'Time(hh:mm:ss)' in line:
            header_i = i
            break
    if header_i is None:
        return [], {'error': 'header-not-found', 'preview': lines[:12]}
    reader = csv.DictReader(io.StringIO('\n'.join(lines[header_i:])))
    rows = []
    for row in reader:
        ds = (row.get('Date(dd:mm:yyyy)') or '').strip()
        ts = (row.get('Time(hh:mm:ss)') or '').strip()
        try:
            dt = datetime.strptime(ds + ' ' + ts, '%d:%m:%Y %H:%M:%S').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        taus = {}
        for nm in (340, 380, 400, 440, 500, 551, 550, 675, 870, 1020, 1640):
            for key in (f'AOD_{nm}nm', f'AOD_{nm}nm-Total'):
                if key in row:
                    value = parse_float(row.get(key))
                    if value is not None and value > 0:
                        taus[nm] = value
                        break
        tau550 = None
        method = None
        if 550 in taus:
            tau550, method = taus[550], 'direct_550'
        elif 551 in taus:
            tau550, method = taus[551], 'direct_551_as_550'
        else:
            for a, b in ((500, 675), (440, 675), (440, 870), (500, 870)):
                if a in taus and b in taus:
                    alpha = -math.log(taus[b] / taus[a]) / math.log(b / a)
                    tau550 = taus[a] * (550.0 / a) ** (-alpha)
                    method = f'angstrom_log_interp_{a}_{b}'
                    break
        if tau550 is None or not math.isfinite(tau550) or tau550 <= 0:
            continue
        rows.append({'site': site, 'time_utc': dt, 'aod550': tau550, 'method': method, 'spectral': taus})
    return rows, {'header_index': header_i, 'record_count': len(rows)}


def estimate_at(rows, when: datetime):
    rows = sorted(rows, key=lambda item: item['time_utc'])
    before = [row for row in rows if row['time_utc'] <= when and when - row['time_utc'] <= QUALIFY]
    after = [row for row in rows if row['time_utc'] >= when and row['time_utc'] - when <= QUALIFY]
    if before and after and before[-1]['time_utc'] != after[0]['time_utc']:
        a, b = before[-1], after[0]
        fraction = (when - a['time_utc']).total_seconds() / (b['time_utc'] - a['time_utc']).total_seconds()
        return a['aod550'] + fraction * (b['aod550'] - a['aod550']), 'linear_bracket', [a, b]
    candidates = [row for row in rows if abs((row['time_utc'] - when).total_seconds()) <= QUALIFY.total_seconds()]
    if not candidates:
        return None, 'unavailable', []
    nearest = min(candidates, key=lambda item: abs((item['time_utc'] - when).total_seconds()))
    return nearest['aod550'], 'nearest_within_3h', [nearest]


def temporal_sigma(rows):
    values = [row['aod550'] for row in rows if abs((row['time_utc'] - OBS_MID).total_seconds()) <= QUALIFY.total_seconds()]
    if len(values) < 2:
        return 0.0
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    return 1.4826 * mad


def iem_url():
    params = [
        ('station', 'ARB'), ('data', 'all'),
        ('year1', '2025'), ('month1', '8'), ('day1', '7'),
        ('year2', '2025'), ('month2', '8'), ('day2', '9'),
        ('tz', 'Etc/UTC'), ('format', 'onlycomma'), ('latlon', 'yes'), ('elev', 'yes'),
        ('missing', 'empty'), ('trace', 'empty'), ('direct', 'no'),
        ('report_type', '3'), ('report_type', '4'),
    ]
    return 'https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?' + urllib.parse.urlencode(params)


def parse_iem(raw: bytes):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig', errors='replace')))
    rows = []
    for row in reader:
        valid = (row.get('valid') or '').strip()
        dt = None
        for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.strptime(valid, fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                pass
        if dt is None:
            continue
        if OBS_START - timedelta(hours=3) <= dt <= OBS_END + timedelta(hours=3):
            keep = {'time_utc': dt.isoformat().replace('+00:00', 'Z')}
            for key in ('tmpf', 'dwpf', 'relh', 'mslp', 'alti', 'vsby', 'skyc1', 'skyc2', 'skyc3', 'wxcodes', 'p01i', 'feel'):
                keep[key] = row.get(key, '')
            rows.append(keep)
    return rows


def main():
    all_rows = {}
    source = {}
    for site in SITES:
        url = aeronet_url(site['name'])
        raw = fetch(url)
        path = OUT / f"aeronet_{site['name']}_2025-08-07_09_L2_raw.txt"
        path.write_bytes(raw)
        rows, metadata = parse_aeronet(raw, site['name'])
        all_rows[site['name']] = rows
        source[site['name']] = {'url': url, 'raw_sha256': sha256(raw), **metadata}

    qualifying = []
    for site in SITES:
        value, mode, support = estimate_at(all_rows[site['name']], OBS_MID)
        if value is not None:
            qualifying.append((site['distance_km'], site, value, mode, support))

    if not qualifying:
        freeze = {
            'schemaVersion': 1,
            'status': 'AERONET_PRIMARY_UNAVAILABLE_REANALYSIS_REQUIRED',
            'observationWindowUTC': [OBS_START.isoformat(), OBS_END.isoformat()],
            'selectionRule': 'nearest AERONET V3 Level-2 site <=75 km with AOD550 support within +/-3 h of observation midpoint; otherwise reanalysis',
            'sources': source,
            'aodSensitivity550': AOD_SENSITIVITY,
        }
    else:
        qualifying.sort(key=lambda item: item[0])
        _, primary_site, mid_aod, mid_mode, _ = qualifying[0]
        primary_rows = all_rows[primary_site['name']]
        spatial = 0.0
        secondary_mid = None
        if len(qualifying) > 1:
            secondary_mid = qualifying[1][2]
            spatial = abs(mid_aod - secondary_mid)
        temp_sig = temporal_sigma(primary_rows)
        sigma = math.sqrt(AOD_MEAS_SIGMA ** 2 + spatial ** 2 + temp_sig ** 2)
        freeze = {
            'schemaVersion': 1,
            'status': 'AERONET_LEVEL2_PRIMARY_FROZEN',
            'observationWindowUTC': [OBS_START.isoformat(), OBS_END.isoformat()],
            'observationMidpointUTC': OBS_MID.isoformat(),
            'selectionRule': 'nearest AERONET V3 Level-2 site <=75 km with AOD550 support within +/-3 h of observation midpoint; otherwise reanalysis',
            'primarySite': primary_site,
            'primaryAOD550AtMidpoint': mid_aod,
            'primaryInterpolation': mid_mode,
            'measurementSigmaAOD': AOD_MEAS_SIGMA,
            'temporalRobustSigmaAOD': temp_sig,
            'spatialCrossSiteAbsDifferenceAOD': spatial,
            'combinedConservativeSigmaAOD': sigma,
            'secondarySiteMidpointAOD550': secondary_mid,
            'aodSensitivity550': AOD_SENSITIVITY,
            'sources': source,
            'qualityBoundary': 'Atmosphere selected without reading Taylor SQM values or MYSTIC residuals.',
        }

        observation_times = [OBS_START + timedelta(minutes=2 * i) for i in range(31)]
        observation_times.insert(9, datetime(2025, 8, 8, 0, 47, tzinfo=timezone.utc))
        assert len(observation_times) == 32 and observation_times[-1] == OBS_END
        per_times = []
        for index, when in enumerate(observation_times, 1):
            value, mode, support = estimate_at(primary_rows, when)
            per_times.append({
                'row': index,
                'time_utc': when.isoformat().replace('+00:00', 'Z'),
                'aod550': value,
                'method': mode,
                'support_times': [item['time_utc'].isoformat().replace('+00:00', 'Z') for item in support],
            })
        (OUT / 'aod_per_observation.json').write_text(json.dumps(per_times, indent=2, sort_keys=True) + '\n')

    met_url = iem_url()
    met_raw = fetch(met_url)
    (OUT / 'karb_asos_2025-08-07_09_raw.csv').write_bytes(met_raw)
    met_rows = parse_iem(met_raw)
    (OUT / 'karb_window.json').write_text(json.dumps(met_rows, indent=2, sort_keys=True) + '\n')
    freeze['surfaceMeteorology'] = {
        'station': 'KARB/ARB',
        'source': 'Iowa Environmental Mesonet ASOS archive',
        'url': met_url,
        'raw_sha256': sha256(met_raw),
        'windowRows': len(met_rows),
        'parsedFile': 'karb_window.json',
    }
    (OUT / 'atmosphere.freeze.json').write_text(json.dumps(freeze, indent=2, sort_keys=True, allow_nan=False) + '\n')

    with (OUT / 'aeronet_derived_aod550.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['site', 'time_utc', 'aod550', 'derivation'])
        for site in SITES:
            for row in sorted(all_rows[site['name']], key=lambda item: item['time_utc']):
                writer.writerow([site['name'], row['time_utc'].isoformat().replace('+00:00', 'Z'), f"{row['aod550']:.9f}", row['method']])

    print(json.dumps(freeze, indent=2, sort_keys=True, allow_nan=False))
    if freeze['status'] != 'AERONET_LEVEL2_PRIMARY_FROZEN':
        return 42
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
