#!/usr/bin/env python3
"""Hard-pin live25 E0 to frozen E0-v2 plus sanitized ARM transport-v2.

Prospective/result-blind orchestration hardening before any authenticated native
E0 outcome. Historical streamers remain unchanged for provenance. Caller
substitution of either the E0 auditor or ARM transport is prohibited.
"""
from __future__ import annotations

import sys
from pathlib import Path

import stream_ena_sws_e0_live25 as BASE

HERE = Path(__file__).resolve().parent
E0_V2 = (HERE / "audit_ena_sws_e0_v2.py").resolve()
TRANSPORT_V2 = (HERE / "stream_ena_sws_e0_from_arm_live_v2.py").resolve()


def _reject_overrides(argv: list[str]) -> None:
    forbidden = ("--e0-script", "--transport-script")
    for arg in argv:
        if any(arg == key or arg.startswith(key + "=") for key in forbidden):
            raise SystemExit(
                "E0 live25 v3 hard-pins E0-v2 and sanitized transport-v2; overrides prohibited"
            )


def main() -> int:
    _reject_overrides(sys.argv[1:])
    for path in (E0_V2, TRANSPORT_V2):
        if not path.is_file():
            raise SystemExit(f"required frozen execution component missing: {path}")
    sys.argv[1:1] = [
        "--e0-script", str(E0_V2),
        "--transport-script", str(TRANSPORT_V2),
    ]
    return int(BASE.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
