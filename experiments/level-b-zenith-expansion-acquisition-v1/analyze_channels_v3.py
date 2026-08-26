#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path
from typing import Any

GRID_SHA = 'b5fae53c1cc88c7f3de6e3689bc25e4a36c54033d1d1bfd6169482f30cc5b477'
COMMON_PATH = Path('review/tier2-stage1-ordinal20-artifact-salvage-v1/common_v1.py')
CHANNELS = (
    'photopicLuminanceCdM2',
    'scotopicLuminanceScotCdM2',
    'johnsonVEffectiveRadiance_mW_m2_nm_sr',
)


class Refusal(RuntimeError):
    pass


def req(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal(message)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    req(isinstance(value, dict), f'object required: {path}')
    return value


def load_common(repo_root: Path):
    path = repo_root / COMMON_PATH
    spec = importlib.util.spec_from_file_location('level_b_channel_common', path)
    req(spec is not None and spec.loader is not None, 'common_v1 module load failed')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_spectrum(path: Path) -> tuple[list[float], list[float], str]:
    raw = path.read_bytes()
    tokens: list[str] = []
    wavelengths: list[float] = []
    values: list[float] = []
    for line in raw.decode('utf-8', errors='strict').splitlines():
        parts = line.split()
        if not parts:
            continue
        req(len(parts) >= 2, f'spectrum row too short: {path}')
        req(len(parts[0].split('.')) == 2 and len(parts[0].split('.')[1]) == 5, f'wavelength token serialization drift: {path}')
        row = [float(x) for x in parts]
        req(all(math.isfinite(x) for x in row), f'nonfinite spectrum value: {path}')
        req(all(x >= 0.0 for x in row[1:]), f'negative spectrum value: {path}')
        tokens.append(parts[0])
        wavelengths.append(row[0])
        values.append(row[-1])
    req(len(tokens) == 8001, f'8001 spectrum nodes required: {path}')
    req(tokens[0] == '380.00000' and tokens[-1] == '780.00000', f'spectrum endpoint drift: {path}')
    req(all(wavelengths[i + 1] > wavelengths[i] for i in range(len(wavelengths) - 1)), f'spectrum ordering drift: {path}')
    token_sha = sha256_bytes(('\n'.join(tokens) + '\n').encode('utf-8'))
    req(token_sha == GRID_SHA, f'wavelength token grid drift: {path}: {token_sha}')
    return wavelengths, values, sha256_bytes(raw)


def stats4(values: list[float]) -> dict[str, Any]:
    req(len(values) == 4 and all(math.isfinite(x) and x > 0.0 for x in values), 'exactly four positive finite blocks required')
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    se = sd / math.sqrt(4.0)
    return {
        'blockValues': values,
        'mean': mean,
        'sampleStd': sd,
        'standardError': se,
        'relativeStandardError': abs(se / mean),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', type=Path, required=True)
    ap.add_argument('--results-root', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()

    repo_root = args.repo_root.resolve()
    common = load_common(repo_root)
    manifest = load_json(args.manifest)
    req(manifest.get('manifestId') == 'level-b-zenith-expansion-acquisition-v1', 'manifest identity drift')
    req(manifest.get('caseCount') == 72 and manifest.get('geometryCount') == 18, 'manifest accounting drift')
    req((manifest.get('closedBoundaries') or {}).get('holdoutExecutionAuthorized') is False, 'source holdout boundary opened')

    geometry_by_id = {g['geometryId']: g for g in manifest['geometries']}
    rows: list[dict[str, Any]] = []
    for result_path in sorted(args.results_root.rglob('case-result.json')):
        result = load_json(result_path)
        if result.get('status') != 'COMPLETED':
            continue
        spectrum_path = result_path.with_name('mc.rad.spc')
        req(spectrum_path.is_file(), f'raw spectrum missing beside {result_path}')
        wl, radiance, raw_sha = parse_spectrum(spectrum_path)
        req(raw_sha == result.get('radianceOutputSha256'), f'raw spectrum hash drift: {result.get("caseId")}')
        gid = str(result['geometryId'])
        req(gid in geometry_by_id, f'unknown geometry id: {gid}')
        channels = common.channels(wl, radiance)
        req(set(channels) == set(CHANNELS), f'channel implementation drift: {gid}')
        rows.append({
            'caseId': result['caseId'],
            'geometryId': gid,
            'role': result['role'],
            'block': int(result['block']),
            'seed': int(result['seed']),
            'rawSpectrumSha256': raw_sha,
            'integratedChannels': {k: float(channels[k]) for k in CHANNELS},
            'legacy15NodePhotopicDiagnosticCdM2': float(result['selectedPhotopicContributionCdM2']),
        })

    req(len(rows) == 72, f'exactly 72 completed case spectra required, got {len(rows)}')
    req(len({r['caseId'] for r in rows}) == 72 and len({r['seed'] for r in rows}) == 72, 'case or seed duplication')
    by_geometry: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_geometry.setdefault(row['geometryId'], []).append(row)
    req(set(by_geometry) == set(geometry_by_id), 'geometry universe drift')
    req(all(len(v) == 4 for v in by_geometry.values()), 'every geometry must have exactly four independent blocks')

    summaries: dict[str, Any] = {}
    training_records: list[dict[str, Any]] = []
    for gid in sorted(by_geometry):
        block_rows = sorted(by_geometry[gid], key=lambda x: x['block'])
        req([r['block'] for r in block_rows] == [1, 2, 3, 4], f'block identity drift: {gid}')
        channel_stats = {
            name: stats4([r['integratedChannels'][name] for r in block_rows])
            for name in CHANNELS
        }
        legacy_stats = stats4([r['legacy15NodePhotopicDiagnosticCdM2'] for r in block_rows])
        g = geometry_by_id[gid]
        summary = {
            'geometry': {k: g[k] for k in ('sunDepressionDeg', 'targetAltitudeDeg', 'relativeAzimuthDeg', 'observerElevationM', 'aod550')},
            'role': g['role'],
            'integratedChannels': channel_stats,
            'legacy15NodePhotopicDiagnosticCdM2': legacy_stats,
            'caseIds': [r['caseId'] for r in block_rows],
            'seeds': [r['seed'] for r in block_rows],
            'rawSpectrumSha256ByBlock': [r['rawSpectrumSha256'] for r in block_rows],
        }
        summaries[gid] = summary
        if g['role'] != 'zenith-azimuth-invariance-diagnostic':
            training_records.append({'geometryId': gid, **summary})

    req(len(training_records) == 16, 'exactly 16 non-diagnostic training geometries required')
    base = summaries['zenith-train-90-b']['integratedChannels']
    diagnostics: list[dict[str, Any]] = []
    for gid in ('zenith-invariance-90-az90', 'zenith-invariance-90-az180'):
        channel_checks = {}
        for name in CHANNELS:
            candidate = summaries[gid]['integratedChannels'][name]
            reference = base[name]
            delta = abs(math.log(candidate['mean'] / reference['mean']))
            combined_rel_se = math.sqrt(
                (candidate['standardError'] / candidate['mean']) ** 2
                + (reference['standardError'] / reference['mean']) ** 2
            )
            limit = max(0.01, 4.0 * combined_rel_se)
            channel_checks[name] = {
                'absLogDifference': delta,
                'combinedEmpiricalRelativeSe': combined_rel_se,
                'fourSigmaOrOnePercentLimit': limit,
                'pass': delta <= limit,
            }
        diagnostics.append({
            'geometryId': gid,
            'pairedWith': 'zenith-train-90-b',
            'channelChecks': channel_checks,
            'allThreeChannelsPass': all(x['pass'] for x in channel_checks.values()),
        })

    output = {
        'schemaVersion': 3,
        'analysisId': 'level-b-zenith-expansion-three-channel-representation-analysis-v3',
        'analysisMethod': 'FROZEN_LEVEL_B_FULL_8001_NODE_CHANNEL_INTEGRATION_WITH_FOUR_BLOCK_EMPIRICAL_SE',
        'status': 'TRAINING_REPRESENTATION_COMPLETE' if all(x['allThreeChannelsPass'] for x in diagnostics) else 'TRAINING_REPRESENTATION_COMPLETE_THREE_CHANNEL_ZENITH_INVARIANCE_DIAGNOSTIC_FAILED',
        'sourceRunId': 33021339197,
        'sourceDispatchSha': '366be0cfd0f506ed57646ad4c66631194f3fc6a0',
        'caseCount': 72,
        'geometryCount': 18,
        'trainingGeometryCount': 16,
        'diagnosticGeometryCount': 2,
        'wavelengthNodeCount': 8001,
        'wavelengthTokenGridSha256': GRID_SHA,
        'channelDefinitionSource': str(COMMON_PATH),
        'channelNames': list(CHANNELS),
        'trainingRecords': training_records,
        'allGeometrySummaries': summaries,
        'extensionReadinessThreeChannelZenithInvarianceDiagnostics': diagnostics,
        'noteOnLegacyDiagnostic': 'selectedPhotopicContributionCdM2 is a 15-node acquisition diagnostic and is not the frozen Level-B 8001-node integrated photopic channel',
        'scientificSolverExecutionPerformedByThisAnalysis': False,
        'modelRefitAuthorized': False,
        'holdoutExecutionAuthorized': False,
        'supportExpansionAuthorized': False,
        'productionAuthorized': False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'three-channel-training-representation-v3.json').write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8'
    )
    print(json.dumps({
        'status': output['status'],
        'trainingGeometryCount': output['trainingGeometryCount'],
        'diagnostics': diagnostics,
        'productionAuthorized': False,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
