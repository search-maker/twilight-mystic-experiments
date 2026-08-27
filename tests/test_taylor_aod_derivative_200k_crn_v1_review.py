from __future__ import annotations

import importlib.util
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / 'experiments' / 'taylor-aod-derivative-200k-crn-v1'


def load(name: str, filename: str):
    path = PKG / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_universe_and_seed_disjointness():
    r = load('runner', 'run_row_replicate.py')
    assert r.ROWS == [23, 24, 25]
    assert r.REPLICATES == [1, 2, 3, 4, 5, 6]
    assert r.AODS == [0.30, 0.40]
    assert r.PHOTONS == 200_000
    assert r.SEED_BASE == {1:967_000_000,2:968_000_000,3:969_000_000,4:970_000_000,5:971_000_000,6:972_000_000}
    new = {r.SEED_BASE[rep] + row*1000 + ray for rep in r.REPLICATES for row in r.ROWS for ray in range(1,65)}
    consumed = {base + row*1000 + ray for base in range(955_000_000, 967_000_000, 1_000_000) for row in r.ROWS for ray in range(1,65)}
    assert len(new) == 1152
    assert new.isdisjoint(consumed)
    assert 3*6*64*2 == 2304
    assert 2304*200_000 == 460_800_000


def test_preflight_normalizes_only_aod_and_path_within_pair():
    p = load('preflight', 'preflight.py')
    lo = 'mc_photons 200000\nmc_randomseed 1\nmc_basename /lo\naerosol_default\naerosol_set_tau_at_wvl 550 0.30000000\n'
    hi = 'mc_photons 200000\nmc_randomseed 1\nmc_basename /hi\naerosol_default\naerosol_set_tau_at_wvl 550 0.40000000\n'
    assert p.normalize_pair(lo) == p.normalize_pair(hi)
    bad = hi.replace('mc_randomseed 1', 'mc_randomseed 2')
    assert p.normalize_pair(lo) != p.normalize_pair(bad)


def test_analysis_statistics_and_frozen_aod_sigma():
    a = load('analysis', 'analyze.py')
    assert a.ROWS == [23,24,25]
    assert a.REPLICATES == [1,2,3,4,5,6]
    assert abs(a.AOD_SIGMA - 0.049232200070782176) < 1e-18
    s = a.stats([1,2,3,4,5,6])
    assert s['n'] == 6 and s['mean'] == 3.5
    assert abs(s['sampleSd'] - statistics.stdev([1,2,3,4,5,6])) < 1e-15
