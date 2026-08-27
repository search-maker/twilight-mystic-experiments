#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'audit.py'

spec = importlib.util.spec_from_file_location('base_audit', BASE)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot import base audit')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def normalize_runtime_and_basename_recovery(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('data_files_path '):
            out.append('data_files_path <PINNED_DATA_DIR>')
        elif s.startswith('atmosphere_file '):
            path = s[len('atmosphere_file '):]
            if not path.replace('\\', '/').endswith('/atmmod/afglus.dat'):
                raise audit.Refusal(f'unexpected atmosphere runtime path: {path}')
            out.append('atmosphere_file <PINNED_AFGLUS>')
        elif s.startswith('source solar '):
            path = s[len('source solar '):]
            if not path.replace('\\', '/').endswith('/solar_flux/atlas_plus_modtran'):
                raise audit.Refusal(f'unexpected solar-source runtime path: {path}')
            out.append('source solar <PINNED_ATLAS_PLUS_MODTRAN>')
        elif s.startswith('mc_basename '):
            out.append('mc_basename <CASE_BASENAME>')
        else:
            out.append(line)
    return out


audit.normalize_runtime_and_basename = normalize_runtime_and_basename_recovery

if __name__ == '__main__':
    audit.main()
