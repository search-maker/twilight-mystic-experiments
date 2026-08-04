#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


class BundleError(RuntimeError):
    pass


def one(root: Path, name: str) -> Path:
    rows = list(root.rglob(name))
    if len(rows) != 1:
        raise BundleError(f"expected exactly one {name} under {root}, found {len(rows)}")
    return rows[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness-root", type=Path, required=True)
    parser.add_argument("--combined-root", type=Path, required=True)
    parser.add_argument("--source-audit-root", type=Path, required=True)
    parser.add_argument("--provenance-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    mappings = (
        (args.readiness_root, "readiness-decision.json", "readiness-decision.json"),
        (args.readiness_root, "ordinal2-manifest.json", "ordinal2-manifest.json"),
        (args.readiness_root, "ordinal2-recovery-report.json", "ordinal2-recovery-report.json"),
        (args.readiness_root, "source-manifest.json", "source-manifest.json"),
        (args.readiness_root, "ordinal1-audit.json", "ordinal1-audit.json"),
        (args.combined_root, "atm-z-grid-equivalence-proof.json", "combined-proof.json"),
        (args.source_audit_root, "source-audit.json", "source-audit.json"),
        (args.provenance_root, "libradtran-provenance-recovery.json", "provenance-report.json"),
    )
    for root, source_name, target_name in mappings:
        shutil.copy2(one(root, source_name), args.output_dir / target_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
