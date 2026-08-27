from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

STAGE = "aerosol-vertical-profile-sensitivity-v1"
HERE = Path(__file__).resolve().parent


class BuildRefusal(RuntimeError):
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BuildRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(
    root: Path,
    parent_main: str,
    scientific_ordinal: int,
    preauthorization_report: dict[str, Any],
    seed_authorization_proof: dict[str, Any],
    *,
    preauthorization_artifact_id: int,
    preauthorization_artifact_digest: str,
) -> dict[str, Any]:
    guard = _load("avps_authorization_guard_for_builder", HERE / "authorization_guard.py")
    return guard.build_expected_document(
        root,
        parent_main,
        scientific_ordinal,
        preauthorization_report,
        seed_authorization_proof,
        preauthorization_artifact_id=preauthorization_artifact_id,
        preauthorization_artifact_digest=preauthorization_artifact_digest,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--parent-main", required=True)
    parser.add_argument("--scientific-ordinal", type=int, required=True)
    parser.add_argument("--preauthorization-report", type=Path, required=True)
    parser.add_argument("--seed-authorization-proof", type=Path, required=True)
    parser.add_argument("--preauthorization-artifact-id", type=int, required=True)
    parser.add_argument("--preauthorization-artifact-digest", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    auth = build(
        args.repository_root,
        args.parent_main,
        args.scientific_ordinal,
        json.loads(args.preauthorization_report.read_text()),
        json.loads(args.seed_authorization_proof.read_text()),
        preauthorization_artifact_id=args.preauthorization_artifact_id,
        preauthorization_artifact_digest=args.preauthorization_artifact_digest,
    )
    args.output.write_text(json.dumps(auth, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
