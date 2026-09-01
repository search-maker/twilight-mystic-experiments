#!/usr/bin/env python3
"""Portable non-interactive one-event ENA/SWS E0-v2 firewall probe.

Credentials are accepted ONLY from ``ARM_USER_ID`` and ``ARM_ACCESS_TOKEN`` in
the inherited environment. They are never printed, written, placed on a command
line, or included in the receipt. The underlying frozen-v2 runner confines raw
SWS bytes to TemporaryDirectory and may inspect only result-blind structural,
time/wavelength, QC/HK/calibration metadata.

This launcher is the cross-platform equivalent of
``run_one_ena_sws_schema_probe_v2.ps1`` for authenticated workers that do not
provide PowerShell. It must run before scaling E0 in a newly attached ARM
runtime.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

FROZEN_UNIVERSE_SHA256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
EXPECTED_PROTOCOL = "ARM_ENA_SWS_V1_STAGE0_E0_RESULT_BLIND_V2"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_safe_probe_output(out_dir: Path) -> dict:
    raw = [p for p in out_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".nc", ".cdf"}]
    if raw:
        raise RuntimeError("HOLDOUT FIREWALL: raw SWS NetCDF/CDF persisted in probe output")
    summary_path = out_dir / "ena_sws_e0_stream_summary.json"
    if not summary_path.is_file():
        raise RuntimeError("probe summary was not produced")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("protocol") != EXPECTED_PROTOCOL:
        raise RuntimeError("expected frozen E0-v2 protocol attestation")
    if summary.get("protected_variable_values_read") is not False:
        raise RuntimeError("HOLDOUT FIREWALL: protected_variable_values_read is not false")
    if summary.get("raw_sws_files_retained") is not False:
        raise RuntimeError("HOLDOUT FIREWALL: raw_sws_files_retained is not false")
    if int(summary.get("processed_event_count", -1)) != 1:
        raise RuntimeError("one-event probe did not process exactly one frozen event")
    if summary.get("stage_b_authorized") is not False:
        raise RuntimeError("probe unexpectedly claims Stage-B authorization")
    return summary


def build_manifest(out_dir: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name != "probe_receipt.json"):
        rows.append({
            "relative_path": path.relative_to(out_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    uid_present = bool(os.environ.get("ARM_USER_ID", "").strip())
    token_present = bool(os.environ.get("ARM_ACCESS_TOKEN", "").strip())
    if not (uid_present and token_present):
        raise SystemExit("existing ARM-authenticated environment is not exposed to this runtime")

    here = Path(__file__).resolve().parent
    runner = here / "run_ena_sws_e0_frozen_v2.py"
    if not runner.is_file():
        raise SystemExit(f"required frozen E0-v2 runner missing: {runner}")

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise SystemExit("probe output directory must be empty to preserve one-run provenance")

    # Credentials are inherited through the environment only; neither value is
    # passed as a subprocess argument or captured in output.
    cmd = [
        sys.executable,
        str(runner),
        "--output-dir", str(out_dir),
        "--stop-after", "1",
        "--probe-aux-schema",
    ]
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"one-event E0-v2 probe failed with exit code {completed.returncode}")

    validate_safe_probe_output(out_dir)
    receipt = {
        "schema": 2,
        "purpose": "ARM_ENA_SWS_V1_E0_V2_ONE_EVENT_SCHEMA_PROBE_PORTABLE",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "frozen_event_universe_sha256": FROZEN_UNIVERSE_SHA256,
        "processed_event_count": 1,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "credentials_persisted": False,
        "credentials_source": "environment_presence_only",
        "stage_b_authorized": False,
        "files": build_manifest(out_dir),
    }
    (out_dir / "probe_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "ONE_EVENT_E0_V2_FIREWALL_PROBE_PASS",
        "processed_event_count": 1,
        "protected_variable_values_read": False,
        "raw_sws_files_retained": False,
        "credentials_persisted": False,
        "stage_b_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
