#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    src = (HERE / 'run_ena_native_live25_v4.py').read_text(encoding='utf-8')
    assert 'import ena_native_gate_core_v4 as gate_core_v4' in src
    assert '_historical.G = gate_core_v4' in src

    core = (HERE / 'ena_native_gate_core_v4.py').read_text(encoding='utf-8').lower()
    # v4 is a pure disposition layer; it must not introduce acquisition or SWS
    # protected-value paths.
    for forbidden in ('adc.arm.gov', 'savedata', 'urllib', 'requests.', 'enasws'):
        assert forbidden not in core, forbidden

    print('PASS ENA native E5 v4 live25 wiring/static acquisition boundary')


if __name__ == '__main__':
    main()
