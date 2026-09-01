#!/usr/bin/env python3
"""Live25 wrapper binding corrected E2-v2 and E4-MFRSR-v3 semantics.

Historical runners are retained for provenance.  This wrapper changes only the
module-global gate core used by the frozen orchestration; no SWS file is read.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path

import ena_native_gate_core_v3 as gate_core_v3

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ena_native_live25_historical", HERE / "run_ena_native_live25.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load historical live25 runner")
_historical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(_historical)
_historical.G = gate_core_v3


def main() -> int:
    return int(_historical.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
