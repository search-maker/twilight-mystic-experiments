#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'review/lunar-scattered-light-source-contract-v1/lunar_mystic_secondary_aod550_anchor_precision_recovery.py'


def load_module():
    spec = importlib.util.spec_from_file_location('lunar_anchor_precision_recovery_tested', MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_outputs(root: Path, cases, *, bad_std_case: str | None = None, nonzero_exit_case: str | None = None) -> None:
    for case in cases:
        d = root / case['caseId']
        d.mkdir(parents=True, exist_ok=True)
        exit_code = 17 if case['caseId'] == nonzero_exit_case else 0
        d.joinpath('uvspec.exitcode').write_text(f'{exit_code}\n', encoding='utf-8')
        if exit_code:
            continue
        target = case['targetWavelengthNm']
        replicate = case['replicate']
        # Tiny deterministic replicate offset: well inside z<=4 for positive sigma.
        target_rad = 1.0e-6 * (1.0 + 0.001 * replicate)
        target_std = 1.0e-8
        if case['caseId'] == bad_std_case:
            target_std = 0.0
        rows_rad = sorted([(target, target_rad), (550.0, 2.0e-6)])
        rows_std = sorted([(target, target_std), (550.0, 2.0e-8)])
        d.joinpath('mc.rad.spc').write_text(''.join(f'{w:.1f} 0 0 0 {v:.12e}\n' for w, v in rows_rad), encoding='utf-8')
        d.joinpath('mc.rad.std.spc').write_text(''.join(f'{w:.1f} 0 0 0 {v:.12e}\n' for w, v in rows_std), encoding='utf-8')


def main() -> None:
    m = load_module()
    contract = m.load_contract()
    cases = m.frozen_cases(contract)
    assert len(cases) == 36
    assert [x['randomSeed'] for x in cases] == list(range(28764001, 28764037))
    assert [x['targetWavelengthNm'] for x in cases[:12]] == [450.0] * 12
    assert [x['targetWavelengthNm'] for x in cases[12:24]] == [650.0] * 12
    assert [x['targetWavelengthNm'] for x in cases[24:]] == [750.0] * 12
    assert all(x['anchorWavelengthNm'] == 550.0 for x in cases)
    assert all(x['photonHistories'] == 5_000_000 for x in cases)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / 'pass'
        root.mkdir()
        write_outputs(root, cases)
        report = m.evaluate_results(root)
        assert report['status'] == 'PASS_SECONDARY_PRECISION_RECOVERY'
        assert report['executionComplete'] is True
        assert report['secondaryPrecisionSupported'] is True
        assert report['combinedParentRecoveryClassification'] == 'COMPUTATIONAL_PRECISION_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'
        assert report['parentV1StatusRemains'] == 'FAIL_COMPUTATIONAL_PRECISION'
        assert report['failedExec001StatusRemains'] == 'EXECUTION_INCOMPLETE'
        assert len(report['replicateChecks']) == 18
        assert report['technicalAnchorExcludedFromPrecisionAcceptance'] is True
        assert report['compatibilityProbeUsedAsPrecisionEvidence'] is False
        assert report['productionAuthorized'] is False

        fail_root = Path(td) / 'precision-fail'
        fail_root.mkdir()
        write_outputs(fail_root, cases, bad_std_case=cases[0]['caseId'])
        failed = m.evaluate_results(fail_root)
        assert failed['status'] == 'FAIL_SECONDARY_PRECISION'
        assert failed['executionComplete'] is True
        assert failed['secondaryPrecisionSupported'] is False
        assert any(x.startswith('NONPOSITIVE_TARGET_MCSTD:') for x in failed['precisionFailures'])

        incomplete_root = Path(td) / 'incomplete'
        incomplete_root.mkdir()
        write_outputs(incomplete_root, cases, nonzero_exit_case=cases[0]['caseId'])
        incomplete = m.evaluate_results(incomplete_root)
        assert incomplete['status'] == 'EXECUTION_INCOMPLETE'
        assert incomplete['executionComplete'] is False
        assert incomplete['secondaryPrecisionSupported'] is False
        assert any(x.startswith('NONZERO_UVSPEC_EXIT:') for x in incomplete['executionFailures'])
        assert incomplete['precisionFailures'] == []

    protected = contract['protectedBoundaries']
    assert all(value is False for value in protected.values())
    assert contract['executionOpeningGate']['solverExecutionAuthorizedByThisFile'] is False
    assert contract['executionOpeningGate']['resultOpeningAuthorizedByThisFile'] is False
    print('PASS test_lunar_mystic_secondary_aod550_anchor_precision_recovery_v1')


if __name__ == '__main__':
    main()
