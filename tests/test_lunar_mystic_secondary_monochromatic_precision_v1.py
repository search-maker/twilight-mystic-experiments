#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_mystic_secondary_monochromatic_precision.py'
LUNAR_INPUT_PATH = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1' / 'lunar_mystic_input.py'


def load_registered(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


m = load_registered('test_lunar_secondary_precision', MODULE_PATH)
lunar_input = load_registered('test_lunar_secondary_input', LUNAR_INPUT_PATH)
contract = m.load_contract()

assert contract['status'] == 'FROZEN_REVIEW_ONLY_NO_SOLVER_EXECUTION'
assert contract['triggerEvidence']['parentStatus'] == 'FAIL_COMPUTATIONAL_PRECISION'
assert contract['triggerEvidence']['failureCount'] == 18
assert contract['triggerEvidence']['parent550NmAllSixReplicateChecksPassed'] is True
assert contract['numericalDesign']['spectralMode'] == 'MONOCHROMATIC_NO_MC_SPECTRAL_IS'
assert contract['numericalDesign']['photonHistoriesPerReplicate'] == 5_000_000
assert contract['numericalDesign']['totalSolverCases'] == 36
assert contract['numericalDesign']['totalPhotonHistories'] == 180_000_000
assert contract['precisionEvaluation']['perReplicateRelativeMcStdMax'] == 0.1
assert contract['precisionEvaluation']['replicateConsistencyZMax'] == 4.0
assert contract['precisionEvaluation']['mcStdMustBeFiniteAndStrictlyPositive'] is True
assert contract['combinedParentContinuationRule']['parentV1MustRemainImmutableFailed'] is True
assert contract['combinedParentContinuationRule']['combinedClassificationDoesNotMeanParentV1Pass'] is True
assert contract['executionOpeningGate']['solverExecutionAuthorizedByThisFile'] is False
assert contract['executionOpeningGate']['resultOpeningAuthorizedByThisFile'] is False
for key, value in contract['protectedBoundaries'].items():
    assert value is False, (key, value)

cases = m.frozen_cases(contract)
assert len(cases) == 36
assert [c['wavelengthNm'] for c in cases[:12]] == [450.0] * 12
assert [c['wavelengthNm'] for c in cases[12:24]] == [650.0] * 12
assert [c['wavelengthNm'] for c in cases[24:]] == [750.0] * 12
seeds = [c['randomSeed'] for c in cases]
assert seeds == list(range(28762001, 28762037))
assert not set(seeds).intersection(contract['numericalDesign']['parentSeedsConsumedAndForbidden'])
assert all(c['photonHistories'] == 5_000_000 for c in cases)
assert len({(c['wavelengthNm'], c['geometryId']) for c in cases}) == 18
assert all(sum(1 for x in cases if x['wavelengthNm'] == c['wavelengthNm'] and x['geometryId'] == c['geometryId']) == 2 for c in cases)

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    atmosphere = td / 'afglus.dat'
    source = td / 'lunar-source.dat'
    atmosphere.write_text('0 0\n', encoding='utf-8')
    source.write_text('380 1\n780 1\n', encoding='utf-8')
    runtime_identity = {
        'uvspecSha256': contract['sourceAndRuntime']['uvspecSha256'],
        'libRadtranDataTreeSha256': contract['sourceAndRuntime']['libRadtranDataTreeSha256'],
    }
    rendered, metadata = m._render_monochromatic_input(
        lunar_input=lunar_input,
        wavelength_nm=650.0,
        data_dir=td,
        atmosphere_file=atmosphere,
        lunar_source_file=source,
        moon_zenith_deg=30.0,
        target_altitude_deg=45.0,
        target_relative_azimuth_to_moon_deg=90.0,
        observer_elevation_m=2000.0,
        aod550=0.1,
        albedo=0.15,
        photon_histories=5_000_000,
        random_seed=28762025,
        case_dir=td / 'case',
        runtime_identity=runtime_identity,
    )
    assert rendered.count('wavelength 650.0 650.0') == 1
    assert 'wavelength 380 780' not in rendered
    assert 'mc_spectral_is' not in rendered
    assert rendered.count('mc_std') == 1
    assert rendered.count('atm_z_grid ') == 1
    assert rendered.count('zout 0.000000') == 1
    assert 'altitude ' not in rendered
    assert metadata['spectralExecutionMode'] == 'MONOCHROMATIC_NO_MC_SPECTRAL_IS'
    assert metadata['calculationWavelengthNm'] == 650.0
    assert metadata['mcSpectralIsEnabled'] is False
    assert metadata['validatedForAtmosphericScatteredMoonlight'] is False
    assert metadata['productionAuthorized'] is False


def write_synthetic(root: Path, zero_std_case: str | None = None, large_z_key: tuple[float, str] | None = None):
    by_group: dict[tuple[float, str], int] = {}
    for case in cases:
        key = (case['wavelengthNm'], case['geometryId'])
        group_index = by_group.setdefault(key, len(by_group) + 1)
        base = 1e-5 * (1.0 + 0.05 * group_index)
        if case['replicate'] == 1:
            radiance = base
        else:
            radiance = base * (1.005 if key != large_z_key else 1.20)
        sigma = 0.01 * base
        if case['caseId'] == zero_std_case:
            sigma = 0.0
        d = root / case['caseId']
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath('mc.rad.spc').write_text(f"{case['wavelengthNm']:.5f} 0 0 0 {radiance:.12e}\n", encoding='utf-8')
        d.joinpath('mc.rad.std.spc').write_text(f"{case['wavelengthNm']:.5f} 0 0 0 {sigma:.12e}\n", encoding='utf-8')


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    write_synthetic(td)
    report = m.evaluate_results(td, contract)
    assert report['status'] == 'PASS_SECONDARY_MONOCHROMATIC_PRECISION'
    assert report['computationallyEligibleForFrozenSecondaryGrid'] is True
    assert report['combinedParentContinuationClassification'] == 'COMPUTATIONAL_PRECISION_SUPPORTED_FOR_FROZEN_CENTRAL_COLLIMATED_GRID'
    assert report['parentV1StatusRemains'] == 'FAIL_COMPUTATIONAL_PRECISION'
    assert report['parentV1Reclassified'] is False
    assert report['failures'] == []
    assert len(report['replicateChecks']) == 18
    assert all(x['passed'] for x in report['replicateChecks'])
    assert report['toaSourceIndependentlyValidatedByThisResult'] is False
    assert report['atmosphericScatteredMoonlightEmpiricallyValidatedByThisResult'] is False
    assert report['finiteMoonDiskModeled'] is False
    assert report['totalSkyValidated'] is False
    assert report['productionAuthorized'] is False

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    write_synthetic(td, zero_std_case='w450-e0000-az030-r1')
    report = m.evaluate_results(td, contract)
    assert report['status'] == 'FAIL_SECONDARY_MONOCHROMATIC_PRECISION'
    assert report['computationallyEligibleForFrozenSecondaryGrid'] is False
    assert 'NONPOSITIVE_OR_NONFINITE_MCSTD:w450-e0000-az030-r1' in report['failures']
    assert report['parentV1Reclassified'] is False

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    write_synthetic(td, large_z_key=(750.0, 'e2000-az150'))
    report = m.evaluate_results(td, contract)
    assert report['status'] == 'FAIL_SECONDARY_MONOCHROMATIC_PRECISION'
    check = next(x for x in report['replicateChecks'] if x['wavelengthNm'] == 750.0 and x['geometryId'] == 'e2000-az150')
    assert check['replicateConsistencyZ'] > 4.0
    assert check['passed'] is False
    assert 'REPLICATE_Z:750:e2000-az150' in report['failures']

source_text = MODULE_PATH.read_text(encoding='utf-8')
assert 'subprocess' not in source_text
assert 'os.system' not in source_text
assert 'Popen(' not in source_text

print('lunar MYSTIC secondary monochromatic precision v1 tests: PASS')
