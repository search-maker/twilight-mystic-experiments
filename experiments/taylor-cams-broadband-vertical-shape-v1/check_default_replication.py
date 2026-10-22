#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROWS = [23, 24, 25]
REPLICATES = [1, 2]
Z_MAX = 5.0
NEW_STAGE = 'taylor-cams-broadband-vertical-shape-v1'
OLD_STAGE = 'taylor-ann-arbor-sqm-mystic-v1'


def load_new(root: Path):
    out = {}
    for p in root.rglob('row-replicate-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != NEW_STAGE or x.get('status') != 'COMPLETED':
            continue
        key = (int(x['row']), int(x['replicate']))
        if key in out:
            raise RuntimeError(f'duplicate new result {key}')
        out[key] = x
    expected = {(r, q) for r in ROWS for q in REPLICATES}
    if set(out) != expected:
        raise RuntimeError(f'new result universe mismatch: {sorted(out)}')
    return out


def load_old(root: Path):
    out = {}
    for p in root.rglob('row-result.json'):
        x = json.loads(p.read_text())
        if x.get('stageId') != OLD_STAGE or x.get('status') != 'COMPLETED':
            continue
        row = int(x['row'])
        if row not in ROWS:
            continue
        if row in out:
            raise RuntimeError(f'duplicate Taylor-v1 row result {row}')
        out[row] = x
    if set(out) != set(ROWS):
        raise RuntimeError(f'Taylor-v1 result universe mismatch: {sorted(out)}')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--new-results-root', type=Path, required=True)
    ap.add_argument('--taylor-v1-results-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)

    new = load_new(a.new_results_root)
    old = load_old(a.taylor_v1_results_root)
    checks = []
    passed = True

    for row in ROWS:
        o = old[row]
        oq = float(o['primaryQ'])
        os = float(o['primaryQStdConservative'])
        if not all(math.isfinite(v) for v in (oq, os)) or oq <= 0 or os < 0:
            raise RuntimeError(f'row {row}: invalid immutable Taylor-v1 Q/sigma')
        for rep in REPLICATES:
            n = new[(row, rep)]
            nq = float(n['defaultQ'])
            ns = float(n['defaultQStdConservative'])
            if not all(math.isfinite(v) for v in (nq, ns)) or nq <= 0 or ns < 0:
                raise RuntimeError(f'row {row} rep {rep}: invalid fresh default Q/sigma')
            denom = math.sqrt(ns * ns + os * os)
            if denom <= 0:
                raise RuntimeError(f'row {row} rep {rep}: zero combined MC sigma')
            z = abs(nq - oq) / denom
            ok = z <= Z_MAX
            passed = passed and ok
            checks.append({
                'row': row,
                'replicate': rep,
                'freshDefaultQ': nq,
                'freshDefaultSigma': ns,
                'immutableTaylorV1Q': oq,
                'immutableTaylorV1Sigma': os,
                'combinedSigma': denom,
                'absoluteDifferenceQ': abs(nq - oq),
                'zCombinedMcSigma': z,
                'gateMaxZ': Z_MAX,
                'pass': ok,
            })

    result = {
        'schemaVersion': 1,
        'stageId': NEW_STAGE,
        'status': 'DEFAULT_SELF_REPLICATION_PASS' if passed else 'DEFAULT_SELF_REPLICATION_FAIL',
        'gateMaxCombinedMcSigma': Z_MAX,
        'checks': checks,
        'allSixPass': passed,
    }
    (a.output / 'default-replication.json').write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'maxZ': max(x['zCombinedMcSigma'] for x in checks)}, sort_keys=True))
    if not passed:
        raise SystemExit('fresh default failed frozen 5-combined-MC-sigma Taylor-v1 replication gate')


if __name__ == '__main__':
    main()
