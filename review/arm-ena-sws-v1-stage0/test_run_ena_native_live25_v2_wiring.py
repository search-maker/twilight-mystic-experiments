#!/usr/bin/env python3
"""Static/import wiring test for the admissible ENA live25 native v2 runner."""
from __future__ import annotations

import ena_native_gate_core_v2 as G2
import run_ena_native_live25 as V1
import run_ena_native_live25_v2 as V2


def main() -> None:
    assert V1.G is G2, V1.G
    assert V2.V1.G is G2, V2.V1.G
    assert V2.main.__module__ == "run_ena_native_live25_v2"
    print("PASS ENA live25 v2 runner wiring")


if __name__ == "__main__":
    main()
