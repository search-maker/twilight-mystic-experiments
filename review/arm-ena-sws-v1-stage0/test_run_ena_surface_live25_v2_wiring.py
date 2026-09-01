#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    src = (HERE / 'run_ena_surface_live25_v2.py').read_text(encoding='utf-8')
    assert 'import ena_surface_gate_v2 as surface_gate_v2' in src
    assert '_historical.E6 = surface_gate_v2' in src

    gate = (HERE / 'ena_surface_gate_v2.py').read_text(encoding='utf-8')
    # The prospective correction is schema-only: it must not acquire data or
    # introduce any ARM datastream identifiers.
    assert 'adc.arm.gov' not in gate
    assert 'saveData' not in gate
    assert 'urllib' not in gate
    assert 'enamfr' not in gate
    assert 'enasws' not in gate.lower()

    print('PASS ENA E6 v2 live25 wiring/static acquisition boundary')


if __name__ == '__main__':
    main()
