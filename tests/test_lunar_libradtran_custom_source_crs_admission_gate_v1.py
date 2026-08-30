#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'review' / 'lunar-scattered-light-source-contract-v1'
CONTRACT = LANE / 'libradtran-custom-source-crs-admission-gate-v1.json'
PROBE = LANE / 'libradtran_custom_source_crs_probe.py'
WORKFLOW = ROOT / '.github' / 'workflows' / 'lunar-custom-source-crs-admission-v1.yml'


def test_contract_is_result_blind_and_runtime_bound() -> None:
    c = json.loads(CONTRACT.read_text(encoding='utf-8'))
    assert c['schemaVersion'] == 1
    assert c['status'] == 'PREREGISTERED_BEFORE_RUNTIME_PROBE'
    runtime = c['exactRuntime']
    assert runtime['versionBuild'] == '2.0.6=py312pl5321he9373c2_1'
    assert runtime['uvspecSha256'] == '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3'
    assert runtime['libRadtranDataTreeSha256'] == 'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7'
    assert c['probe']['classification'] == 'NON_SCIENTIFIC_SOURCE_BINDING_CAPABILITY_PROBE'
    assert c['probe']['mysticExecuted'] is False
    assert c['probe']['realSkyDataOpened'] is False
    assert c['probe']['sourceWavelengthNm'] == [380.0, 550.0, 780.0]
    assert c['probe']['arms']['A']['sourceFluxValues'] == [1.0, 1.0, 1.0]
    assert c['probe']['arms']['B']['sourceFluxValues'] == [7.0, 7.0, 7.0]
    rule = c['frozenDecisionRule']
    assert rule['expectedArmBToArmARatio'] == 7.0
    assert rule['maximumAbsoluteRatioDeviation'] == 0.01
    assert rule['noPostResultToleranceChange'] is True
    assert rule['noSilentFallback'] is True
    assert c['fallbackBoundary']['requireSeparatePreregistrationBeforeUse'] is True
    b = c['scientificBoundaries']
    assert b['noTaylorOrJerusalemResidualUse'] is True
    assert b['noAirLusiResidualOpening'] is True
    assert b['noXshooterResidualOpening'] is True
    assert b['atmosphericScatteredMoonlightValidatedByThisProbe'] is False
    assert b['productionAuthorized'] is False


def test_probe_preserves_problematic_crs_custom_source_combination_and_boundaries() -> None:
    text = PROBE.read_text(encoding='utf-8')
    assert "f'source solar {source}'" in text
    assert "'mol_abs_param crs'" in text
    assert "'wavelength 380 780'" in text
    assert "'rte_solver disort'" in text
    assert "'number_of_streams 4'" in text
    assert "'output_user lambda edir'" in text
    assert "'mysticExecuted': False" in text
    assert "'realSkyDataOpened': False" in text
    assert "'taylorOrJerusalemResidualUsed': False" in text
    assert "'atmosphericScatteredMoonlightValidated': False" in text
    assert "'productionAuthorized': False" in text
    assert 'verify=False' not in text
    assert '_create_unverified_context' not in text


def test_workflow_binds_exact_runtime_and_executes_only_capability_probe() -> None:
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'rubin-libradtran=2.0.6=py312pl5321he9373c2_1' in text
    assert '2b9c7a69e4dfe4e77ade97148b2499b0a2c205c8d8000d3516a29344cc9d2fc3' in text
    assert 'ad30b49177e9c84e46497d69faf0c75e466996b0d0003f1de210289ae9f847d7' in text
    assert 'runtime_probe.py' in text
    assert 'libradtran_custom_source_crs_probe.py' in text
    assert 'GITHUB_RUN_ATTEMPT' in text
    assert 'rte_solver mystic' not in text
    assert 'mc_photons' not in text
    assert 'No MYSTIC' in text
    assert 'no real-sky validation' in text
    assert 'no production authorization' in text


if __name__ == '__main__':
    test_contract_is_result_blind_and_runtime_bound()
    test_probe_preserves_problematic_crs_custom_source_combination_and_boundaries()
    test_workflow_binds_exact_runtime_and_executes_only_capability_probe()
    print('lunar libRadtran custom-source CRS admission gate v1 tests: PASS')
