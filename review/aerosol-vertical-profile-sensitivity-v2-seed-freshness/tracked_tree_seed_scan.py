from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "experiments/aerosol-family-challenge-v2/tracked_tree_seed_scan.py"
EXPECTED_BLOB = "1c110d75b516cb7b9d50dc2674080f4a67e55d2a"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


if git_blob_sha1(BASE) != EXPECTED_BLOB:
    raise RuntimeError("AVPS v2 refuses: bound tracked-tree seed scanner bytes changed")
spec = importlib.util.spec_from_file_location("avps_v2_bound_tracked_tree_seed_scan", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load bound tracked-tree seed scanner")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    raise SystemExit(mod.main())
