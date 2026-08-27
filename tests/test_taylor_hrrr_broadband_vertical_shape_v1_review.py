from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'experiments' / 'taylor-hrrr-broadband-vertical-shape-v1' / 'run_row_replicate.py'


def load_runner():
    spec = importlib.util.spec_from_file_location('hrrr_broadband_review', RUNNER)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_frozen_universe_and_fresh_seeds():
    m = load_runner()
    assert m.ROWS == [23, 24, 25]
    assert m.REPLICATES == [1, 2]
    assert m.PHOTONS == 50_000
    assert m.SEED_BASE == {1: 955_000_000, 2: 956_000_000}
    seeds = [
        m.SEED_BASE[rep] + row * 1000 + ray
        for rep in m.REPLICATES
        for row in m.ROWS
        for ray in range(1, 65)
    ]
    assert len(seeds) == 384
    assert len(set(seeds)) == 384


def test_tau_insertion_is_exactly_one_line(tmp_path):
    m = load_runner()
    default = '\n'.join([
        'data_files_path /x',
        'mc_randomseed 955023001',
        'mc_basename /work/default/mc',
        'mc_spectral_is 550.0',
        'albedo 0.150000',
        'aerosol_default',
        'aerosol_set_tau_at_wvl 550 0.31600000',
        'quiet',
        '',
    ])
    tau = tmp_path / 'tau.dat'
    tau.write_text('120 0\n0.262 1\n')
    hrrr = m.insert_tau_line(default.replace('/work/default/mc', '/work/hrrr/mc'), tau)
    assert default.count('aerosol_file tau ') == 0
    assert hrrr.count('aerosol_file tau ') == 1
    assert m.normalized_render_lines(default) == m.normalized_render_lines(hrrr)
    assert 'mc_randomseed 955023001' in default
    assert 'mc_randomseed 955023001' in hrrr
    lines = hrrr.splitlines()
    i = next(i for i, line in enumerate(lines) if line.startswith('aerosol_file tau '))
    assert lines[i - 1] == 'aerosol_default'
    assert lines[i + 1] == 'aerosol_set_tau_at_wvl 550 0.31600000'


def test_hrrr_raw_hash_is_frozen():
    m = load_runner()
    assert m.HRRR_RAW_SHA256 == '929e787c15f8d689bf63a732152eb552e621542325e4942d4d48bf91eb6d75a9'


def test_review_branch_has_no_scientific_workflow():
    names = {p.name for p in (ROOT / '.github' / 'workflows').glob('*.yml')}
    assert 'taylor-hrrr-broadband-vertical-shape-v1.yml' not in names
