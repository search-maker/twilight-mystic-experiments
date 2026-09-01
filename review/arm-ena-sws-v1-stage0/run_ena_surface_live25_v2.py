#!/usr/bin/env python3
"""Live25 E6 wrapper binding the prospective measured-wavelength v2 schema.

Historical E6 orchestration is retained for provenance.  This wrapper changes
only the module-global surface gate used by that orchestration.  No SWS file is
queried or read by E6.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import ena_surface_gate_v2 as surface_gate_v2

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ena_surface_live25_historical", HERE / "run_ena_surface_live25.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load historical E6 live25 runner")
_historical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(_historical)
_historical.E6 = surface_gate_v2


def main() -> int:
    return int(_historical.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
