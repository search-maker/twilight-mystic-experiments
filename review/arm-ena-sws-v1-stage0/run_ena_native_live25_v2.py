#!/usr/bin/env python3
"""Admissible ENA live25 native runner after the prospective E2 v2 correction.

This wrapper deliberately preserves the reviewed retrieval/orchestration in
run_ena_native_live25.py while replacing only its module-global gate core with
ena_native_gate_core_v2 before main() executes.  No science outcome was used to
make this wiring change.  Historical v1 remains available only for provenance;
new ENA native execution must use this v2 entry point (or an exact equivalent
that imports ena_native_gate_core_v2).
"""
from __future__ import annotations

import ena_native_gate_core_v2 as G2
import run_ena_native_live25 as V1

V1.G = G2


def main() -> int:
    return V1.main()


if __name__ == "__main__":
    raise SystemExit(main())
