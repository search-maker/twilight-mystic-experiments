#!/usr/bin/env python3
"""Result-blind live25 orchestration hardening for unresolved ARM acquisition.

This layer preserves the reviewed E2-v2, MFRSR-E4-v3, E5-v4 and E3-v5
science core bound by ``run_ena_native_live25_v5.py``.  It changes only
transport/error disposition before any native ENA outcome is consumed:

* a query error on a preferred datastream is UNRESOLVED, not proof that the
  preferred product is genuinely absent and not permission to fall back;
* an E0 ledger containing ARM Live query/audit errors is UNRESOLVED, not a
  scientific E0 FAIL/MISSING case.

The wrapper therefore aborts without producing downstream science disposition
when either condition occurs.  It never queries or opens SWS itself and never
changes any frozen science threshold.
"""
from __future__ import annotations

import csv
from pathlib import Path

import run_ena_native_live25_v5 as V5


class AcquisitionUnresolved(RuntimeError):
    """Raised when transport state cannot establish native-data disposition."""


BASE = V5._historical
_UNRESOLVED_E0 = {"ARM_LIVE_QUERY_ERROR", "STREAM_AUDIT_ERROR"}


def discover_strict(pair: str, candidates: list[str], days: list[str]):
    """Honor frozen preferred->fallback order only after genuine absence.

    A successful query returning no exact-date files establishes absence for
    that candidate/date set and permits the next frozen fallback.  Any query
    exception leaves availability unresolved and aborts rather than converting
    a transport failure into a terminal science disposition.
    """
    for ds in candidates:
        names: list[str] = []
        for day in days:
            try:
                names.extend(BASE.query_day(pair, ds, day))
            except Exception as exc:
                raise AcquisitionUnresolved(
                    "ARM_LIVE_QUERY_UNRESOLVED "
                    f"datastream={ds} date={day} error_type={type(exc).__name__}"
                ) from None
        names = sorted(set(names))
        if names:
            return ds, names, []
    return None, [], []


def e0_pass_set_strict(path: Path | None):
    """Reject unresolved E0 transport/audit rows before downstream gates."""
    if path is None or not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    unresolved = [
        (r.get("case_id", ""), r.get("disposition", ""))
        for r in rows
        if r.get("disposition", "") in _UNRESOLVED_E0
    ]
    if unresolved:
        detail = ",".join(f"{cid}:{disp}" for cid, disp in unresolved)
        raise AcquisitionUnresolved(f"E0_LEDGER_UNRESOLVED {detail}")
    return {
        r["case_id"]
        for r in rows
        if r.get("disposition") == "E0_PASS_BLIND_CANDIDATE"
    }


def main() -> int:
    # Patch only transport/error interpretation in the already-reviewed v5
    # historical orchestration object; its gate core remains E3-v5 (which
    # transitively preserves E2-v2, E4-v3 and E5-v4).
    BASE.discover = discover_strict
    BASE.e0_pass_set = e0_pass_set_strict
    return int(V5.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
