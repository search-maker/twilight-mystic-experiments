from __future__ import annotations

import importlib.util
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / 'experiments' / 'taylor-broadband-mc-repro-v1'


def load(name: str, filename: str):
    path = PKG / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fresh_seed_universe_is_exact_and_disjoint_from_prior_pair():
    m = load('fresh_runner', 'run_fresh_replicate.py')
    assert m.ROWS == [23, 24, 25]
    assert m.REPLICATES == [3, 4, 5, 6]
    assert m.SEED_BASE == {
        3: 957_000_000,
        4: 958_000_000,
        5: 959_000_000,
        6: 960_000_000,
    }
    assert m.EXPECTED_PHOTONS == 50_000
    new = {
        m.SEED_BASE[rep] + row * 1000 + ray
        for rep in m.REPLICATES
        for row in m.ROWS
        for ray in range(1, 65)
    }
    old = {
        base + row * 1000 + ray
        for base in (955_000_000, 956_000_000)
        for row in m.ROWS
        for ray in range(1, 65)
    }
    assert len(new) == 3 * 4 * 64 == 768
    assert new.isdisjoint(old)
    assert min(new) > max(old)


def test_fresh_preflight_matches_fresh_runner_identity():
    r = load('fresh_runner2', 'run_fresh_replicate.py')
    p = load('fresh_preflight', 'run_fresh_preflight.py')
    assert p.STAGE == r.STAGE
    assert p.ROWS == r.ROWS
    assert p.REPLICATES == r.REPLICATES
    assert p.SEED_BASE == r.SEED_BASE


def test_analysis_universe_and_basic_statistics_are_frozen():
    a = load('analysis', 'analyze_reproducibility.py')
    assert a.ROWS == [23, 24, 25]
    assert a.OLD_REPLICATES == [1, 2]
    assert a.NEW_REPLICATES == [3, 4, 5, 6]
    assert a.ALL_REPLICATES == [1, 2, 3, 4, 5, 6]
    s = a.sample_stats([1, 2, 3, 4, 5, 6])
    assert s['n'] == 6
    assert s['mean'] == 3.5
    assert abs(s['sampleSd'] - statistics.stdev([1, 2, 3, 4, 5, 6])) < 1e-15
    assert a.nearest_rank_p90(list(range(1, 65))) == sorted(range(1, 65))[int(0.9 * 63)]
