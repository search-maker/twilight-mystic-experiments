#!/usr/bin/env python3
"""Run frozen ENA/SWS E0-v2 through sanitized ARM transport-v2.

Science semantics remain exactly E0-v2. This prospective orchestration version
changes only the transport binding so authenticated query/download failures
cannot persist request URLs or credentials.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import sys
import tempfile
from pathlib import Path

FROZEN_SHA256 = "87933189ff56322ce2b5d2821a1c2ab8094d0a472ef6c690cfbd90cd0451fa41"
EXPECTED_COUNT = 906
FIRST_CASE = "2017-04-05_dusk"
LAST_CASE = "2019-09-27_dusk"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_and_load(csv_path: Path, e0):
    digest = sha256_file(csv_path)
    if digest != FROZEN_SHA256:
        raise SystemExit(f"frozen event-universe SHA-256 mismatch: {digest}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != EXPECTED_COUNT:
        raise SystemExit(f"expected {EXPECTED_COUNT} frozen events, got {len(rows)}")
    if rows[0].get("case_id") != FIRST_CASE or rows[-1].get("case_id") != LAST_CASE:
        raise SystemExit("frozen event-universe endpoint identity mismatch")
    expected_fields = {
        "case_id", "local_civil_date", "event",
        "t_minus8_utc", "t_minus7_utc", "t_minus6_utc",
    }
    if set(rows[0]) != expected_fields:
        raise SystemExit(f"unexpected frozen event-universe columns: {sorted(rows[0])}")
    events = []
    for row in rows:
        if row["event"] != "dusk":
            raise SystemExit(f"non-dusk row in frozen universe: {row['case_id']}")
        if not (row["t_minus6_utc"] < row["t_minus7_utc"] < row["t_minus8_utc"]):
            raise SystemExit(f"bad anchor order in frozen universe: {row['case_id']}")
        events.append(e0.Event(**row))
    return events


def generate_verified_csv(generator_path: Path, e0, destination: Path):
    gen = load_module("ena_fast_generator_v3", generator_path)
    rows = gen.generate_rows()
    gen.write_csv(destination, rows)
    return verify_and_load(destination, e0)


def main() -> int:
    here = Path(__file__).resolve().parent
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--event-universe", type=Path, default=None)
    pre.add_argument("--dry-validate-universe", action="store_true")
    known, remaining = pre.parse_known_args()

    # Explicit credential CLI is prohibited by the sanitized transport contract.
    for arg in remaining:
        if arg in {"--user-id", "--access-token"} or arg.startswith("--user-id=") or arg.startswith("--access-token="):
            raise SystemExit("frozen E0-v3 accepts ARM credentials from inherited environment only")

    e0_path = here / "audit_ena_sws_e0_v2.py"
    collector_path = here / "stream_ena_sws_e0_from_arm_live_v2.py"
    generator_path = here / "generate_ena_event_universe_fast.py"
    for required in (e0_path, collector_path, generator_path):
        if not required.is_file():
            raise SystemExit(f"required frozen component missing: {required}")
    e0 = load_module("ena_sws_e0_frozen_v3", e0_path)

    temp_ctx = None
    if known.event_universe is not None:
        universe_path = known.event_universe.resolve()
        events = verify_and_load(universe_path, e0)
    else:
        temp_ctx = tempfile.TemporaryDirectory(prefix="ena_frozen_universe_v3_")
        universe_path = Path(temp_ctx.name) / "ena_sws_e0_event_universe.csv"
        events = generate_verified_csv(generator_path, e0, universe_path)

    print(f"FROZEN_EVENT_UNIVERSE_PASS count={len(events)} sha256={FROZEN_SHA256}")
    if known.dry_validate_universe:
        if temp_ctx is not None:
            temp_ctx.cleanup()
        return 0

    collector = load_module("ena_sws_stream_collector_v3", collector_path)
    e0.build_events = lambda: list(events)
    # The sanitized transport's BASE collector receives the already-loaded E0-v2
    # module; this preserves frozen science while changing transport error text only.
    collector.BASE.load_e0 = lambda _path: e0
    sys.argv = [sys.argv[0]] + ["--e0-script", str(e0_path)] + remaining
    try:
        return int(collector.main())
    finally:
        if temp_ctx is not None:
            temp_ctx.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
