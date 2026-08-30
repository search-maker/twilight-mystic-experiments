#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1'
MODULE_PATH = STAGE / 'lunar_mystic_computational_precision.py'
CONTRACT_PATH = STAGE / 'lunar-mystic-computational-precision-v1.json'

spec = importlib.util.spec_from_file_location('lunar_mystic_computational_precision_tested', MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

contract = mod.load_contract(CONTRACT_PATH)
assert contract['status'] == 'FROZEN_REVIEW_ONLY_NO_SOLVER_EXECUTION'
assert contract['sourceFoundation']['parentReviewHead'] == 'a5955961e228e81db51729dd95f9cb4007a2f66b'
assert contract['runtimeIdentity']['uvspecSha256'] == '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
assert contract['runtimeIdentity']['libRadtranDataTreeSha256'] == 'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7'
assert contract['runtimeIdentity']['solarReference']['relativePath'] == 'solar_flux/atlas_plus_modtran'
assert contract['runtimeIdentity']['solarReference']['fileUnit'] == 'mW m-2 nm-1'
assert contract['numericalDesign']['totalSolverCases'] == 12
assert contract['numericalDesign']['totalPhotonHistories'] == 60000000
assert contract['precisionEvaluation']['primaryPerReplicateRelativeMcStdMax'] == 0.05
assert contract['precisionEvaluation']['secondaryPerReplicateRelativeMcStdMax'] == 0.1
assert contract['precisionEvaluation']['replicateConsistencyZMax'] == 4.0
assert contract['executionOpeningGate']['solverExecutionAuthorizedByThisFile'] is False
assert contract['executionOpeningGate']['resultOpeningAuthorizedByThisFile'] is False
assert contract['protectedBoundaries']['taylorResidualUsed'] is False
assert contract['protectedBoundaries']['jerusalemResidualUsed'] is False
assert contract['protectedBoundaries']['productionAuthorized'] is False

cases = mod.frozen_cases(contract)
assert len(cases) == 12
assert len({case['caseId'] for case in cases}) == 12
assert len({case['randomSeed'] for case in cases}) == 12
assert {case['observerElevationM'] for case in cases} == {0.0, 2000.0}
assert {case['targetRelativeAzimuthToMoonDeg'] for case in cases} == {30.0, 90.0, 150.0}
assert {case['replicate'] for case in cases} == {1, 2}
assert all(case['photonHistories'] == 5000000 for case in cases)

# Solar-reference interpolation is deterministic, result-blind, and bounded.
rows = [(379.0, 900.0), (380.0, 1000.0), (580.0, 1200.0), (780.0, 1400.0), (781.0, 1500.0)]
assert mod.interpolate_spectrum(rows, [380.0, 480.0, 580.0, 680.0, 780.0]) == [1000.0, 1100.0, 1200.0, 1300.0, 1400.0]
try:
    mod.interpolate_spectrum(rows, [378.0, 380.0])
    raise AssertionError('expected out-of-bracket refusal')
except mod.LunarPrecisionError:
    pass

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    atlas = root / 'atlas_plus_modtran'
    atlas.write_text('379 1000\n380 1000\n780 1000\n781 1000\n', encoding='utf-8')
    source = root / 'lunar-source.dat'
    meta = mod.build_lunar_source_from_runtime_atlas(atlas, source, contract)
    assert meta['atlasUnit'] == 'mW m-2 nm-1'
    assert meta['sourceMetadata']['nodeCount'] == 401
    assert meta['sourceMetadata']['startNm'] == 380.0
    assert meta['sourceMetadata']['stopNm'] == 780.0
    assert meta['independentToaValidationClaim'] is False
    assert meta['atmosphericScatteredMoonlightValidationClaim'] is False
    assert meta['productionAuthorized'] is False
    source_rows = [line.split() for line in source.read_text(encoding='utf-8').splitlines()]
    assert len(source_rows) == 401
    assert float(source_rows[0][0]) == 380.0
    assert float(source_rows[-1][0]) == 780.0
    assert all(math.isfinite(float(row[1])) and float(row[1]) >= 0 for row in source_rows)


def write_outputs(root: Path, relative_std: float = 0.02, replicate_shift_sigma: float = 0.0) -> None:
    wavelengths = [450.0, 550.0, 650.0, 750.0]
    for case in cases:
        case_dir = root / case['caseId']
        case_dir.mkdir(parents=True, exist_ok=True)
        base = 1.0e-7 * (1.0 + 0.0001 * case['targetRelativeAzimuthToMoonDeg'] + 0.000001 * case['observerElevationM'])
        sigma = base * relative_std
        shift = replicate_shift_sigma * sigma if case['replicate'] == 2 else 0.0
        rad = ''.join(f'{w:.5f} {base + shift:.12e}\n' for w in wavelengths)
        std = ''.join(f'{w:.5f} {sigma:.12e}\n' for w in wavelengths)
        (case_dir / 'mc.rad.spc').write_text(rad, encoding='utf-8')
        (case_dir / 'mc.rad.std.spc').write_text(std, encoding='utf-8')


with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    write_outputs(root, relative_std=0.02, replicate_shift_sigma=1.0)
    report = mod.evaluate_results(root, contract)
    assert report['status'] == 'PASS_COMPUTATIONAL_PRECISION'
    assert report['computationallyEligibleForFrozenSyntheticGrid'] is True
    assert report['failures'] == []
    assert len(report['replicateChecks']) == 24
    assert report['atmosphericScatteredMoonlightEmpiricallyValidatedByThisResult'] is False
    assert report['finiteMoonDiskModeled'] is False
    assert report['productionAuthorized'] is False

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    write_outputs(root, relative_std=0.2, replicate_shift_sigma=0.0)
    report = mod.evaluate_results(root, contract)
    assert report['status'] == 'FAIL_COMPUTATIONAL_PRECISION'
    assert report['computationallyEligibleForFrozenSyntheticGrid'] is False
    assert any(reason.startswith('PRIMARY_RELATIVE_STD:') for reason in report['failures'])
    assert any(reason.startswith('SECONDARY_RELATIVE_STD:') for reason in report['failures'])

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    write_outputs(root, relative_std=0.02, replicate_shift_sigma=6.0)
    report = mod.evaluate_results(root, contract)
    assert report['status'] == 'FAIL_COMPUTATIONAL_PRECISION'
    assert any(reason.startswith('REPLICATE_Z:') for reason in report['failures'])

print('lunar MYSTIC computational precision v1 contract/runner tests: PASS')
