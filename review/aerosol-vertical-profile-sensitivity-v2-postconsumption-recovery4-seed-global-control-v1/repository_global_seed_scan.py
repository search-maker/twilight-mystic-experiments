from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/aerosol-family-challenge-v2/repository_global_seed_scan.py"
EXPECTED_BASE_BLOB = "4c6d704fa24228284780bcb1dd7c52537b4c5b0d"


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


if git_blob_sha1(BASE) != EXPECTED_BASE_BLOB:
    raise SystemExit("bound repository-global seed scanner byte drift")

spec = importlib.util.spec_from_file_location("avps_recovery4_bound_repository_global_seed_scan", BASE)
if spec is None or spec.loader is None:
    raise SystemExit("cannot import bound repository-global seed scanner")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
mod.REVIEW_PROOF_ARTIFACT_NAME = "vertical-profile-v2-postconsumption-recovery4-seed-global-control-proof"

if __name__ == "__main__":
    mod.main()
