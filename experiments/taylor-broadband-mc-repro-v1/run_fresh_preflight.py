#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

STAGE = 'taylor-broadband-mc-repro-v1'
ROWS = [23, 24, 25]
REPLICATES = [3, 4, 5, 6]
SEED_BASE = {
    3: 957_000_000,
    4: 958_000_000,
    5: 959_000_000,
    6: 960_000_000,
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--frozen-preflight', type=Path, required=True)
    ap.add_argument('--frozen-runner', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    known, rest = ap.parse_known_args()

    pre = load_module('frozen_broadband_preflight', known.frozen_preflight)
    if list(pre.ROWS) != ROWS:
        raise RuntimeError(f'unexpected frozen row universe: {pre.ROWS}')
    if list(pre.REPLICATES) != [1, 2]:
        raise RuntimeError(f'unexpected frozen replicate universe: {pre.REPLICATES}')
    if dict(pre.SEED_BASE) != {1: 955_000_000, 2: 956_000_000}:
        raise RuntimeError(f'unexpected frozen preflight seeds: {pre.SEED_BASE}')

    pre.REPLICATES = list(REPLICATES)
    pre.SEED_BASE = dict(SEED_BASE)

    sys.argv = [
        str(known.frozen_preflight),
        '--runner', str(known.frozen_runner),
        '--output', str(known.output),
        *rest,
    ]
    pre.main()

    evidence = known.output / 'preflight.json'
    data = json.loads(evidence.read_text())
    if data.get('status') != 'TAU_ONLY_INPUT_DELTA_PASS':
        raise RuntimeError('frozen dry preflight did not pass')
    if int(data.get('auditCount', -1)) != len(ROWS) * len(REPLICATES) * 64:
        raise RuntimeError(f'unexpected dry audit count: {data.get("auditCount")}')
    data['sourceStageId'] = data.get('stageId')
    data['stageId'] = STAGE
    data['freshReplicateUniverse'] = REPLICATES
    data['freshSeedBase'] = SEED_BASE
    evidence.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': data['status'], 'stageId': STAGE, 'auditCount': data['auditCount']}, sort_keys=True))


if __name__ == '__main__':
    main()
