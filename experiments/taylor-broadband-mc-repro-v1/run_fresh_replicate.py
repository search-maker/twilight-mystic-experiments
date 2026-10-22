#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

STAGE = 'taylor-broadband-mc-repro-v1'
FROZEN_STAGE = 'taylor-hrrr-broadband-vertical-shape-v1'
ROWS = [23, 24, 25]
REPLICATES = [3, 4, 5, 6]
SEED_BASE = {
    3: 957_000_000,
    4: 958_000_000,
    5: 959_000_000,
    6: 960_000_000,
}
EXPECTED_PHOTONS = 50_000


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location('frozen_broadband_runner', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot import frozen runner {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--frozen-runner', type=Path, required=True)
    ap.add_argument('--replicate', type=int, choices=REPLICATES, required=True)
    known, rest = ap.parse_known_args()

    frozen = load_module(known.frozen_runner)
    if frozen.STAGE != FROZEN_STAGE:
        raise RuntimeError(f'unexpected frozen runner stage: {frozen.STAGE}')
    if list(frozen.ROWS) != ROWS:
        raise RuntimeError(f'unexpected frozen row universe: {frozen.ROWS}')
    if list(frozen.REPLICATES) != [1, 2]:
        raise RuntimeError(f'unexpected frozen replicate universe: {frozen.REPLICATES}')
    if int(frozen.PHOTONS) != EXPECTED_PHOTONS:
        raise RuntimeError(f'unexpected frozen photon budget: {frozen.PHOTONS}')
    if dict(frozen.SEED_BASE) != {1: 955_000_000, 2: 956_000_000}:
        raise RuntimeError(f'unexpected frozen seed namespace: {frozen.SEED_BASE}')

    # Change only execution identity and fresh seed namespaces. All physical,
    # spectral, instrument, and HRRR-shape code remains the reviewed runner.
    frozen.STAGE = STAGE
    frozen.REPLICATES = list(REPLICATES)
    frozen.SEED_BASE = dict(SEED_BASE)

    sys.argv = [
        str(known.frozen_runner),
        '--replicate', str(known.replicate),
        *rest,
    ]
    frozen.main()


if __name__ == '__main__':
    main()
