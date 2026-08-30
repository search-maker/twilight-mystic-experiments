#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'review/lunar-scattered-light-source-contract-v1/lunar_mystic_secondary_aod550_anchor_compatibility.py'


def load_module():
    spec = importlib.util.spec_from_file_location('lunar_anchor_compatibility_tested', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    m = load_module()
    contract = m.load_contract()
    cases = m.probe_cases(contract)
    assert [x['targetWavelengthNm'] for x in cases] == [450.0, 650.0, 750.0]
    assert [x['randomSeed'] for x in cases] == [28763001, 28763002, 28763003]
    assert all(x['photonHistories'] == 500000 for x in cases)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        full = root / 'full.dat'
        full.write_text(
            '450.000000 1.111111111111e-03\n'
            '550.000000 2.222222222222e-03\n'
            '650.000000 3.333333333333e-03\n'
            '750.000000 4.444444444444e-03\n',
            encoding='utf-8',
        )
        sparse = root / 'sparse.dat'
        meta = m.write_sparse_anchor_source(full, 650.0, sparse)
        assert meta['wavelengthRowsNm'] == [550.0, 650.0]
        assert sparse.read_text(encoding='utf-8') == (
            '550.000000 2.222222222222e-03\n'
            '650.000000 3.333333333333e-03\n'
        )

        base = '\n'.join([
            'source solar /tmp/sparse.dat',
            'mol_abs_param crs',
            'wavelength 380 780',
            'rte_solver mystic',
            'mc_std',
            'mc_spectral_is 550.0',
            'aerosol_default',
            'aerosol_set_tau_at_wvl 550 0.100000',
            'atm_z_grid /tmp/grid.dat',
            'zout 0.000000',
            '',
        ])
        converted = m.convert_reviewed_input_to_anchor_grid(base, 650.0)
        assert 'wavelength 550.0 650.0' in converted
        assert 'mc_spectral_is' not in converted
        assert converted.count('aerosol_set_tau_at_wvl 550 0.100000') == 1

        result_root = root / 'results'
        result_root.mkdir()
        for case in cases:
            case_dir = result_root / case['caseId']
            case_dir.mkdir()
            case_dir.joinpath('uvspec.exitcode').write_text('0\n', encoding='utf-8')
            target = case['targetWavelengthNm']
            rad_rows = sorted([(target, 1.0e-6), (550.0, 2.0e-6)])
            std_rows = sorted([(target, 1.0e-8), (550.0, 2.0e-8)])
            case_dir.joinpath('mc.rad.spc').write_text(''.join(f'{w:.1f} {v:.12e}\n' for w, v in rad_rows), encoding='utf-8')
            case_dir.joinpath('mc.rad.std.spc').write_text(''.join(f'{w:.1f} {v:.12e}\n' for w, v in std_rows), encoding='utf-8')
        report = m.evaluate_probe(result_root)
        assert report['status'] == 'PASS_TRANSPORT_COMPATIBILITY_ONLY'
        assert report['transportCompatibilityPassed'] is True
        assert report['probeOutputsUsedForPrecisionClassification'] is False
        assert report['secondaryComputationalPrecisionValidated'] is False
        assert report['productionAuthorized'] is False

        first = cases[0]
        first_dir = result_root / first['caseId']
        first_dir.joinpath('mc.rad.std.spc').write_text('450.0 0.0\n550.0 2.0e-8\n', encoding='utf-8')
        failed = m.evaluate_probe(result_root)
        assert failed['status'] == 'FAIL_TRANSPORT_COMPATIBILITY'
        assert any(x.startswith('NONPOSITIVE_TARGET_MCSTD:') for x in failed['failures'])

    protected = contract['protectedBoundaries']
    assert all(value is False for value in protected.values())
    print('PASS test_lunar_mystic_secondary_aod550_anchor_compatibility_v1')


if __name__ == '__main__':
    main()
