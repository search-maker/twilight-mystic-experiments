#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    src = (HERE / 'run_ena_native_live25_v5.py').read_text(encoding='utf-8')
    assert 'import ena_native_gate_core_v5 as gate_core_v5' in src
    assert '_historical.G = gate_core_v5' in src

    core = (HERE / 'ena_native_gate_core_v5.py').read_text(encoding='utf-8').lower()
    # v5 is a non-SWS schema/disposition layer only; no acquisition or protected
    # photometric path may be introduced here.
    for forbidden in ('adc.arm.gov', 'savedata', 'urllib', 'requests.', 'enasws'):
        assert forbidden not in core, forbidden

    print('PASS ENA native E3 v5 live25 wiring/static acquisition boundary')


if __name__ == '__main__':
    main()
