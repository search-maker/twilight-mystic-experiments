#!/usr/bin/env python3
"""Live25 wrapper binding corrected E2-v2, E4-v3, E5-v4 and E3-v5.

Historical orchestration remains for provenance. This wrapper only replaces the
module-global non-SWS native gate core. Protected SWS photometric values are not
opened by this path.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path

import ena_native_gate_core_v5 as gate_core_v5

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ena_native_live25_historical", HERE / "run_ena_native_live25.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load historical live25 runner")
_historical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(_historical)
_historical.G = gate_core_v5


def main() -> int:
    return int(_historical.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
