#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("wave1_v4_" + name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


c = _load("review_core")
r = _load("preregistration")
z = _load("postprocess")
Refusal = c.Refusal
repository_root = c.repository_root
canonical_sha256 = c.canonical_sha256
raw_sha256 = c.raw_sha256
dump = c.dump
load_json = c.load_json
load_module = c.load_module
_proposal = c.proposal
build_preregistration = r.build_preregistration
validate_preregistration = r.validate_preregistration
authorization_template = r.authorization_template
candidate_review = r.candidate_review
write_generated = r.write_generated
aggregate_wave1 = z.aggregate_wave1
audit_wave1 = z.audit_wave1
analyze_wave1 = z.analyze_wave1
for name in (
    "BASE_PACKAGE_PATH", "V2_WAVE_PACKAGE_PATH", "V3_PACKAGE_PATH", "SEED_PLAN_PATH",
    "DUPLICATE_SNAPSHOT_PATH", "SOURCE_MAIN_SHA", "V3_PREREGISTRATION_SHA256",
    "CANDIDATE_ORDINAL", "CANDIDATE_KEY", "CANDIDATE_TITLE", "CANDIDATE_BRANCH",
    "CANDIDATE_AUTHORIZATION_PATH", "STAGE_ID", "WAVE", "BLOCKS", "CASE_COUNT",
    "GEOMETRY_COUNT", "MAX_CONFIGURED_PHOTON_HISTORIES",
):
    globals()[name] = getattr(c, name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(dump(write_generated(repository_root(), args.output_dir)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
