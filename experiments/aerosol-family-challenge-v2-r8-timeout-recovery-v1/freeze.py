from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

STAGE = "aerosol-family-challenge-v2-r8-timeout-recovery-v1"
SOURCE_MANIFEST_SHA256 = "c031d6daf6a0e37240b93786394036d12bebecbba7894b6aebbad62b45a2016f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expected_bytes(root: Path) -> bytes:
    package = root / "experiments/aerosol-family-challenge-v2-r8-timeout-recovery-v1"
    source_path = root / "evidence/aerosol-family-challenge-v2-r8/manifest.frozen.json"
    if sha(source_path) != SOURCE_MANIFEST_SHA256:
        raise RuntimeError("source R8 manifest raw bytes drift")
    core = load("afc2_r8_timeout_recovery_freeze_core", package / "core.py")
    protocol = json.loads((package / "protocol.review.json").read_text())
    source = json.loads(source_path.read_text())
    manifest = core.build_recovery_manifest(protocol, source)
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()
    data = expected_bytes(root)
    frozen = root / "evidence/aerosol-family-challenge-v2-r8-timeout-recovery-v1/manifest.frozen.json"
    if args.verify:
        if not frozen.is_file() or frozen.read_bytes() != data:
            raise SystemExit("committed recovery manifest differs from deterministic source-bound regeneration")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
    print(hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
