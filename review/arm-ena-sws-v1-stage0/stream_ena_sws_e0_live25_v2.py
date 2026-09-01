#!/usr/bin/env python3
"""Hard-pin the live25 ARM ENA/SWS E0 stream to the frozen v2 auditor.

Prospective/result-blind orchestration correction.  The historical
``stream_ena_sws_e0_live25.py`` remains intact for provenance, but its CLI
still defaults ``--e0-script`` to the now-prohibited historical E0-v1 auditor.
This wrapper rejects caller overrides and injects the reviewed sibling
``audit_ena_sws_e0_v2.py`` before delegating to the historical streaming
orchestrator.  It does not inspect native data itself and does not change the
holdout firewall or ARM transport.
"""
from __future__ import annotations

import sys
from pathlib import Path

import stream_ena_sws_e0_live25 as BASE

E0_V2 = (Path(__file__).resolve().parent / "audit_ena_sws_e0_v2.py").resolve()


def _reject_e0_script_override(argv: list[str]) -> None:
    for arg in argv:
        if arg == "--e0-script" or arg.startswith("--e0-script="):
            raise SystemExit(
                "E0 live25 v2 hard-pins audit_ena_sws_e0_v2.py; "
                "--e0-script overrides are prohibited"
            )


def main() -> int:
    _reject_e0_script_override(sys.argv[1:])
    if not E0_V2.is_file():
        raise SystemExit(f"required frozen E0 v2 auditor is missing: {E0_V2}")
    sys.argv[1:1] = ["--e0-script", str(E0_V2)]
    return int(BASE.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
