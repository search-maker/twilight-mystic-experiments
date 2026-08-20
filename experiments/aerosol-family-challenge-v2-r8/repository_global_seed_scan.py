from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / 'aerosol-family-challenge-v2' / 'repository_global_seed_scan.py'
EXPECTED_BLOB = '4c6d704fa24228284780bcb1dd7c52537b4c5b0d'

def git_blob_sha1(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

if git_blob_sha1(BASE) != EXPECTED_BLOB:
    raise RuntimeError('R8 refuses: bound R6 repository-global scanner bytes changed')
spec=importlib.util.spec_from_file_location('afc2_r6_repository_global_seed_scan',BASE)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load bound repository-global seed scanner')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
mod.REVIEW_PROOF_ARTIFACT_NAME='aerosol-family-v2-r8-freeze-proof'

if __name__=='__main__':
    raise SystemExit(mod.main())
