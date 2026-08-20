from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from core import SEED_AUDIT_STAGE_ID, validate_design

BASE = Path(__file__).resolve().parent.parent / 'aerosol-family-challenge-v2' / 'merge_seed_proof.py'
EXPECTED_BLOB = '178f3be87fb2c2c41caf2de380e108512bbe9688'

def git_blob_sha1(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

if git_blob_sha1(BASE) != EXPECTED_BLOB:
    raise RuntimeError('R8 refuses: bound R6 seed-proof merger bytes changed')
spec=importlib.util.spec_from_file_location('afc2_r6_merge_seed_proof',BASE)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load bound seed-proof merger')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def _arg(flag: str) -> str:
    try:
        return sys.argv[sys.argv.index(flag)+1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f'missing {flag}') from exc

def main() -> int:
    design_path=Path(_arg('--design'))
    validate_design(json.loads(design_path.read_text()))
    rc=mod.main()
    output=Path(_arg('--output'))
    if output.is_file():
        value=json.loads(output.read_text())
        value['stageId']=SEED_AUDIT_STAGE_ID
        value['continuationReview']='R8_SEEDS_AND_GOVERNANCE_IDENTITY_ONLY'
        output.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    return rc

if __name__=='__main__':
    raise SystemExit(main())
