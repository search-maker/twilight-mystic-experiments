#!/usr/bin/env python3
from __future__ import annotations

import ena_native_gate_core_v4 as G


def rec(name, launch, bottom, top, usable=True):
    return {
        'source_file': name,
        'usable': usable,
        'launch_epoch': float(launch),
        'measured_bottom_alt': float(bottom),
        'measured_top_alt': float(top),
    }


def main():
    t7 = 100000.0

    # Frozen two-sided support with an actual common measured vertical range.
    out = G.choose_sonde_pair([
        rec('before.nc', t7 - 2 * 3600, 10.0, 18000.0),
        rec('after.nc', t7 + 3 * 3600, 25.0, 17500.0),
    ], t7)
    assert out['pass'], out
    assert out['common_measured_bottom_alt'] == 25.0, out
    assert out['common_measured_top_alt'] == 17500.0, out
    assert out['above_common_top_label'] == 'ASSUMED_STANDARD_EXTENSION_SENSITIVITY', out

    # Nearest usable launch on each side is deterministic.
    out = G.choose_sonde_pair([
        rec('old_before.nc', t7 - 5 * 3600, 0.0, 19000.0),
        rec('near_before.nc', t7 - 1 * 3600, 20.0, 18000.0),
        rec('near_after.nc', t7 + 1.5 * 3600, 30.0, 17000.0),
        rec('late_after.nc', t7 + 5 * 3600, 0.0, 19000.0),
    ], t7)
    assert out['pass'], out
    assert out['before_file'] == 'near_before.nc', out
    assert out['after_file'] == 'near_after.nc', out

    # Individually usable profiles with no measured vertical overlap fail closed.
    out = G.choose_sonde_pair([
        rec('before.nc', t7 - 1 * 3600, 10000.0, 12000.0),
        rec('after.nc', t7 + 1 * 3600, 13000.0, 15000.0),
    ], t7)
    assert not out['pass'], out
    assert out['reason'] == 'NO_COMMON_MEASURED_VERTICAL_RANGE', out

    # Touching endpoints are not a finite common vertical range.
    out = G.choose_sonde_pair([
        rec('before.nc', t7 - 1 * 3600, 10000.0, 13000.0),
        rec('after.nc', t7 + 1 * 3600, 13000.0, 15000.0),
    ], t7)
    assert not out['pass'], out
    assert out['reason'] == 'NO_COMMON_MEASURED_VERTICAL_RANGE', out

    # One-sided support and >6 h support remain fail-closed as frozen.
    out = G.choose_sonde_pair([rec('before.nc', t7 - 1 * 3600, 0.0, 18000.0)], t7)
    assert not out['pass'] and out['reason'] == 'NO_TWO_SIDED_SONDE_WITHIN_6H', out
    out = G.choose_sonde_pair([
        rec('before.nc', t7 - 7 * 3600, 0.0, 18000.0),
        rec('after.nc', t7 + 1 * 3600, 0.0, 18000.0),
    ], t7)
    assert not out['pass'] and out['reason'] == 'NO_TWO_SIDED_SONDE_WITHIN_6H', out

    print('PASS ENA native E5 v4 common-vertical-range contracts')


if __name__ == '__main__':
    main()
