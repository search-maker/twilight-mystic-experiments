#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

STAGE='taylor-primary-mc-screen-50k-v1'
ROWS=[1,5,9,13,17,21]
REPLICATES=[1,2,3,4,5,6]
PHOTONS=50_000
SEED_BASE={1:979_000_000,2:980_000_000,3:981_000_000,4:982_000_000,5:983_000_000,6:984_000_000}


def load(path:Path):
    s=importlib.util.spec_from_file_location('reviewed_default_runner',path)
    if s is None or s.loader is None: raise RuntimeError(f'cannot import {path}')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def main():
    ap=argparse.ArgumentParser(add_help=False)
    ap.add_argument('--reviewed-default-runner',type=Path,required=True)
    ap.add_argument('--row',type=int,required=True)
    ap.add_argument('--replicate',type=int,choices=REPLICATES,required=True)
    known,rest=ap.parse_known_args()
    if known.row not in ROWS: raise RuntimeError('row outside frozen anchor universe')
    m=load(known.reviewed_default_runner)
    if m.STAGE!='taylor-broadband-photon-scaling-200k-v1': raise RuntimeError(f'unexpected reviewed runner stage {m.STAGE}')
    if list(m.ROWS)!=[23,24,25] or list(m.REPLICATES)!=[1,2,3,4,5,6] or int(m.PHOTONS)!=200_000: raise RuntimeError('reviewed default-runner constants changed')
    if dict(m.SEED_BASE)!={1:961_000_000,2:962_000_000,3:963_000_000,4:964_000_000,5:965_000_000,6:966_000_000}: raise RuntimeError('reviewed default-runner seed identity changed')
    m.STAGE=STAGE; m.ROWS=list(ROWS); m.PHOTONS=PHOTONS; m.SEED_BASE=dict(SEED_BASE)
    sys.argv=[str(known.reviewed_default_runner),'--row',str(known.row),'--replicate',str(known.replicate),*rest]
    m.main()

if __name__=='__main__': main()
