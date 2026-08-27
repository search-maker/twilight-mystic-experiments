from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'experiments' / 'taylor-cams-broadband-vertical-shape-v1' / 'run_row_replicate.py'


def load_runner():
    spec = importlib.util.spec_from_file_location('taylor_cams_broadband_v1', RUNNER)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_frozen_scientific_universe_and_seeds():
    m = load_runner()
    assert m.ROWS == [23, 24, 25]
    assert m.PHOTONS == 50_000
    assert m.SITE_KM == 0.262
    assert m.SEED_BASE == {1: 951_000_000, 2: 952_000_000}
    assert m.RATIO_MIN == 0.95
    assert m.RATIO_MAX == 1.05
    seeds = []
    for rep in (1, 2):
        for row in m.ROWS:
            for ray in range(1, 65):
                seeds.append(m.SEED_BASE[rep] + row * 1000 + ray)
    assert len(seeds) == 384
    assert len(set(seeds)) == 384


def test_tau_insertion_changes_only_one_physical_line(tmp_path):
    m = load_runner()
    default = '\n'.join([
        'data_files_path /x',
        'mc_randomseed 951023001',
        'mc_basename /work/default/mc',
        'aerosol_default',
        'aerosol_set_tau_at_wvl 550 0.31600000',
        'quiet',
        '',
    ])
    tau = tmp_path / 'tau.dat'
    tau.write_text('120 0\n0.262 1\n')
    cams = m.insert_tau_line(default.replace('/work/default/mc', '/work/cams/mc'), tau)
    assert default.count('aerosol_file tau ') == 0
    assert cams.count('aerosol_file tau ') == 1
    assert m.normalized_render_lines(default) == m.normalized_render_lines(cams)
    assert 'mc_randomseed 951023001' in default
    assert 'mc_randomseed 951023001' in cams


def good_summary():
    return {
        'endpoints': [
            {
                'endpoint': 'analysis00',
                'integratedExtinctionTau532': 0.330,
                'directCamsAOD532': 0.325,
                'directCamsAOD550': 0.312,
                'surfacePressure_Pa': 99000.0,
                'nonzeroLevelCount': 120,
                'integrationToDirectAOD532Ratio': 0.330 / 0.325,
            },
            {
                'endpoint': 'forecast03',
                'integratedExtinctionTau532': 0.290,
                'directCamsAOD532': 0.292,
                'directCamsAOD550': 0.280,
                'surfacePressure_Pa': 99100.0,
                'nonzeroLevelCount': 118,
                'integrationToDirectAOD532Ratio': 0.290 / 0.292,
            },
        ]
    }


def test_endpoint_internal_consistency_gate_passes_only_frozen_window(tmp_path):
    m = load_runner()
    p = tmp_path / 'summary.json'
    p.write_text(json.dumps(good_summary()))
    x = m.load_and_gate_summary(p)
    assert set(x['byEndpoint']) == {'analysis00', 'forecast03'}

    bad = good_summary()
    bad['endpoints'][0]['integratedExtinctionTau532'] = 0.350
    bad['endpoints'][0]['integrationToDirectAOD532Ratio'] = 0.350 / 0.325
    p.write_text(json.dumps(bad))
    with pytest.raises(m.Failure, match='outside frozen gate'):
        m.load_and_gate_summary(p)


def test_zero_endpoint_fails_closed(tmp_path):
    m = load_runner()
    bad = good_summary()
    bad['endpoints'][0]['integratedExtinctionTau532'] = 0.0
    bad['endpoints'][0]['nonzeroLevelCount'] = 0
    bad['endpoints'][0]['integrationToDirectAOD532Ratio'] = 0.0
    p = tmp_path / 'summary.json'
    p.write_text(json.dumps(bad))
    with pytest.raises(m.Failure, match='nonpositive endpoint evidence'):
        m.load_and_gate_summary(p)


def test_no_solver_workflow_is_added_by_review_package():
    workflow_names = {p.name for p in (ROOT / '.github' / 'workflows').glob('*.yml')}
    assert 'taylor-cams-broadband-vertical-shape-v1.yml' not in workflow_names
