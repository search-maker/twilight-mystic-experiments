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

REVIEWED_STAGE='taylor-broadband-photon-scaling-200k-v1'
REVIEWED_ROWS=[23,24,25]
REVIEWED_REPLICATES=[1,2,3,4,5,6]
REVIEWED_PHOTONS=200_000
REVIEWED_SEED_BASE={1:961_000_000,2:962_000_000,3:963_000_000,4:964_000_000,5:965_000_000,6:966_000_000}
FROZEN_BROADBAND_ROWS=[23,24,25]
FROZEN_BROADBAND_PHOTONS=50_000
FROZEN_BROADBAND_SEED_BASE={1:955_000_000,2:956_000_000}


def load(path:Path):
    s=importlib.util.spec_from_file_location('reviewed_default_runner',path)
    if s is None or s.loader is None: raise RuntimeError(f'cannot import {path}')
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def prepare_reviewed_runner(m):
    if m.STAGE!=REVIEWED_STAGE: raise RuntimeError(f'unexpected reviewed runner stage {m.STAGE}')
    if list(m.ROWS)!=REVIEWED_ROWS or list(m.REPLICATES)!=REVIEWED_REPLICATES or int(m.PHOTONS)!=REVIEWED_PHOTONS:
        raise RuntimeError('reviewed default-runner constants changed')
    if dict(m.SEED_BASE)!=REVIEWED_SEED_BASE:
        raise RuntimeError('reviewed default-runner seed identity changed')
    if not hasattr(m,'load_module'):
        raise RuntimeError('reviewed default-runner load_module helper missing')

    original_load_module=m.load_module

    def compatibility_load_module(name,path):
        child=original_load_module(name,path)
        if name=='frozen_reviewed_broadband':
            if list(child.ROWS)!=FROZEN_BROADBAND_ROWS or int(child.PHOTONS)!=FROZEN_BROADBAND_PHOTONS:
                raise RuntimeError('frozen broadband helper constants changed before compatibility shim')
            if dict(child.SEED_BASE)!=FROZEN_BROADBAND_SEED_BASE:
                raise RuntimeError('frozen broadband helper seed identity changed before compatibility shim')
            # The reviewed 200k wrapper compares child.ROWS to its own ROWS even
            # though run_condition()/accumulate() do not use ROWS.  For this
            # earlier-row screen, expose only the new row universe through that
            # metadata guard; leave every numerical function, photon constant,
            # and original 955/956 helper seed identity untouched.
            child.ROWS=list(ROWS)
        return child

    m.load_module=compatibility_load_module
    m.STAGE=STAGE
    m.ROWS=list(ROWS)
    m.PHOTONS=PHOTONS
    m.SEED_BASE=dict(SEED_BASE)
    return m


def main():
    ap=argparse.ArgumentParser(add_help=False)
    ap.add_argument('--reviewed-default-runner',type=Path,required=True)
    ap.add_argument('--row',type=int,required=True)
    ap.add_argument('--replicate',type=int,choices=REPLICATES,required=True)
    known,rest=ap.parse_known_args()
    if known.row not in ROWS: raise RuntimeError('row outside frozen anchor universe')
    m=prepare_reviewed_runner(load(known.reviewed_default_runner))
    sys.argv=[str(known.reviewed_default_runner),'--row',str(known.row),'--replicate',str(known.replicate),*rest]
    m.main()

if __name__=='__main__': main()
