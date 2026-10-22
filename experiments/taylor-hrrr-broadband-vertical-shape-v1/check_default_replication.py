#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2]
NEW_STAGE = 'taylor-hrrr-broadband-vertical-shape-v1'
OLD_STAGE = 'taylor-ann-arbor-sqm-mystic-v1'
Z_MAX = 5.0


def load_new(root: Path):
    found = {}
    for p in root.rglob('row-replicate-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != NEW_STAGE or x.get('status') != 'COMPLETED':
            continue
        key = (int(x['row']), int(x['replicate']))
        if key in found:
            raise RuntimeError(f'duplicate new result {key}')
        found[key] = x
    expected = {(r, q) for r in ROWS for q in REPLICATES}
    if set(found) != expected:
        raise RuntimeError(f'new result universe mismatch: {sorted(found)}')
    return found


def load_old(root: Path):
    found = {}
    for p in root.rglob('row-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != OLD_STAGE or x.get('status') != 'COMPLETED':
            continue
        row = int(x['row'])
        if row not in ROWS:
            continue
        if row in found:
            raise RuntimeError(f'duplicate immutable Taylor-v1 row {row}')
        found[row] = x
    if set(found) != set(ROWS):
        raise RuntimeError(f'immutable Taylor-v1 result universe mismatch: {sorted(found)}')
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--new-results-root', type=Path, required=True)
    ap.add_argument('--taylor-v1-results-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)

    new = load_new(a.new_results_root)
    old = load_old(a.taylor_v1_results_root)
    checks = []
    all_pass = True
    for row in ROWS:
        oq = float(old[row]['primaryQ'])
        os = float(old[row]['primaryQStdConservative'])
        if not all(math.isfinite(x) for x in (oq, os)) or oq <= 0 or os < 0:
            raise RuntimeError(f'row {row}: invalid immutable Taylor-v1 Q/sigma')
        for rep in REPLICATES:
            n = new[(row, rep)]
            nq = float(n['defaultQ'])
            ns = float(n['defaultQStdConservative'])
            if not all(math.isfinite(x) for x in (nq, ns)) or nq <= 0 or ns < 0:
                raise RuntimeError(f'row {row} rep {rep}: invalid fresh default Q/sigma')
            denom = math.sqrt(os*os + ns*ns)
            if denom <= 0:
                raise RuntimeError('zero combined MC sigma')
            z = abs(nq - oq) / denom
            ok = z <= Z_MAX
            all_pass = all_pass and ok
            checks.append({
                'row': row,
                'replicate': rep,
                'freshDefaultQ': nq,
                'freshDefaultSigma': ns,
                'immutableTaylorV1Q': oq,
                'immutableTaylorV1Sigma': os,
                'combinedSigma': denom,
                'zCombinedMcSigma': z,
                'gateMaxZ': Z_MAX,
                'pass': ok,
            })

    result = {
        'schemaVersion': 1,
        'stageId': NEW_STAGE,
        'status': 'DEFAULT_SELF_REPLICATION_PASS' if all_pass else 'DEFAULT_SELF_REPLICATION_FAIL',
        'gateMaxCombinedMcSigma': Z_MAX,
        'allSixPass': all_pass,
        'checks': checks,
    }
    (a.output / 'default-replication.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'maxZ': max(x['zCombinedMcSigma'] for x in checks)}, sort_keys=True))
    if not all_pass:
        raise SystemExit('fresh default failed frozen 5-combined-MC-sigma Taylor-v1 replication gate')


if __name__ == '__main__':
    main()
