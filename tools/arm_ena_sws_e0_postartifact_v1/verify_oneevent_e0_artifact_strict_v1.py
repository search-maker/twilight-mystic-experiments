#!/usr/bin/env python3
"""Strict entrypoint for the sanitized ARM ENA/SWS one-event E0 artifact.

The frozen producer has a closed seven-file output universe. Refuse every extra
file before delegating to the deeper result-blind verifier so an unexpected
future text payload cannot silently widen the sanitized artifact contract.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import verify_oneevent_e0_artifact_v1 as base


class StrictVerificationError(RuntimeError):
    pass


def verify_strict(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise StrictVerificationError(f"artifact directory does not exist: {root}")
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file()
    }
    if actual != base.REQUIRED_FILES:
        missing = sorted(base.REQUIRED_FILES - actual)
        unexpected = sorted(actual - base.REQUIRED_FILES)
        raise StrictVerificationError(
            f"closed sanitized artifact file-set mismatch missing={missing} unexpected={unexpected}"
        )
    try:
        return base.verify(root)
    except base.VerificationError as exc:
        raise StrictVerificationError(str(exc)) from exc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("artifact_dir", type=Path)
    ap.add_argument("--receipt-out", type=Path, default=None)
    args = ap.parse_args()
    try:
        result = verify_strict(args.artifact_dir)
    except StrictVerificationError as exc:
        print(json.dumps({"status": "REFUSED", "reason": str(exc)}, indent=2, sort_keys=True))
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.receipt_out is not None:
        args.receipt_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
