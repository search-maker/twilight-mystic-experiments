from __future__ import annotations
import importlib.util,pathlib,statistics,types
ROOT=pathlib.Path(__file__).resolve().parents[1]; PKG=ROOT/'experiments'/'taylor-primary-mc-screen-50k-v1'
def load(name,file):
    p=PKG/file; s=importlib.util.spec_from_file_location(name,p); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_anchor_universe_and_fresh_seeds():
    r=load('r','run_anchor_replicate.py'); assert r.ROWS==[1,5,9,13,17,21] and r.REPLICATES==[1,2,3,4,5,6] and r.PHOTONS==50_000
    assert r.SEED_BASE=={1:979_000_000,2:980_000_000,3:981_000_000,4:982_000_000,5:983_000_000,6:984_000_000}
    new={r.SEED_BASE[q]+row*1000+ray for q in r.REPLICATES for row in r.ROWS for ray in range(1,65)}; consumed={base+row*1000+ray for base in range(955_000_000,979_000_000,1_000_000) for row in r.ROWS for ray in range(1,65)}
    assert len(new)==2304 and new.isdisjoint(consumed) and 2304*50_000==115_200_000

def test_preflight_normalizes_only_seed_and_path():
    p=load('p','preflight.py'); a='mc_photons 50000\nmc_randomseed 1\nmc_basename /a\naerosol_set_tau_at_wvl 550 0.3\n'; b='mc_photons 50000\nmc_randomseed 2\nmc_basename /b\naerosol_set_tau_at_wvl 550 0.3\n'; assert p.normalize(a)==p.normalize(b); assert p.normalize(a)!=p.normalize(b.replace('50000','50001'))

def test_analysis_universe_and_stats():
    a=load('a','analyze.py'); assert a.ANCHORS==[1,5,9,13,17,21] and a.REPLICATES==[1,2,3,4,5,6] and abs(a.REPEATABILITY-0.0621462261)<1e-15
    s=a.stats([1,2,3,4,5,6]); assert s['mean']==3.5 and abs(s['sampleSd']-statistics.stdev([1,2,3,4,5,6]))<1e-15

def test_recovery_shim_changes_only_broadband_row_metadata_guard():
    r=load('rshim','run_anchor_replicate.py')
    run_condition=object(); accumulate=object()
    child=types.SimpleNamespace(
        ROWS=[23,24,25], PHOTONS=50_000,
        SEED_BASE={1:955_000_000,2:956_000_000},
        run_condition=run_condition, accumulate=accumulate,
    )
    outer=types.SimpleNamespace(
        STAGE=r.REVIEWED_STAGE,
        ROWS=[23,24,25],
        REPLICATES=[1,2,3,4,5,6],
        PHOTONS=200_000,
        SEED_BASE=dict(r.REVIEWED_SEED_BASE),
        load_module=lambda name,path: child,
    )
    out=r.prepare_reviewed_runner(outer)
    loaded=out.load_module('frozen_reviewed_broadband',pathlib.Path('unused'))
    assert loaded.ROWS==r.ROWS
    assert loaded.PHOTONS==50_000
    assert loaded.SEED_BASE=={1:955_000_000,2:956_000_000}
    assert loaded.run_condition is run_condition and loaded.accumulate is accumulate
    assert out.STAGE==r.STAGE and out.ROWS==r.ROWS and out.PHOTONS==50_000 and out.SEED_BASE==r.SEED_BASE

def test_recovery_shim_does_not_mutate_non_broadband_child():
    r=load('rshim_other','run_anchor_replicate.py')
    other=types.SimpleNamespace(ROWS=['sentinel'])
    outer=types.SimpleNamespace(
        STAGE=r.REVIEWED_STAGE, ROWS=[23,24,25], REPLICATES=[1,2,3,4,5,6], PHOTONS=200_000,
        SEED_BASE=dict(r.REVIEWED_SEED_BASE), load_module=lambda name,path: other,
    )
    out=r.prepare_reviewed_runner(outer)
    assert out.load_module('anything_else',pathlib.Path('unused')).ROWS==['sentinel']
