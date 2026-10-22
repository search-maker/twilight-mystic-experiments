from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORE_PATH = HERE / "build_authorization_core.py"
EXPECTED_CORE_BLOB = "6905eb13c06f99775f044ae7b3c05aaf8543edb7"
CONTROL_DIR = ROOT / "review/aerosol-vertical-profile-sensitivity-v2-control-v1"
BOUND_BLOBS = {
    CONTROL_DIR / "control_package.py": "62bacf15d145051fcc5259a24c310eac761d0e74",
    CONTROL_DIR / "adapter.py": "c245eac2fe5b5d026e46ec4253bc377c5fde97ec",
    CONTROL_DIR / "runtime_stage.py": "0d3ac10f3ef7d22f0205854233a6c37cbba03f7c",
}


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load_core():
    if not CORE_PATH.is_file() or git_blob_sha1(CORE_PATH) != EXPECTED_CORE_BLOB:
        raise RuntimeError("authorization core byte drift")
    spec = importlib.util.spec_from_file_location("avps_v2_authorization_core_v4", CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import authorization core")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.CONTROL_DIR = CONTROL_DIR
    module.BOUND_BLOBS = dict(BOUND_BLOBS)
    return module


_core = _load_core()

Refusal = _core.Refusal
canonical_sha256 = _core.canonical_sha256
validate_preauthorization = _core.validate_preauthorization
validate_control_receipt = _core.validate_control_receipt
validate_live_surface = _core.validate_live_surface
validate_bound_sources = _core.validate_bound_sources
build_document = _core.build_document
validate_document = _core.validate_document
main = _core.main


if __name__ == "__main__":
    raise SystemExit(main())
