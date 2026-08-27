from __future__ import annotations
import importlib.util,pathlib,statistics
ROOT=pathlib.Path(__file__).resolve().parents[1]; PKG=ROOT/'experiments'/'taylor-timing-derivative-200k-v1'
def load(name,file):
    p=PKG/file; s=importlib.util.spec_from_file_location(name,p); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_frozen_neighbor_universe_and_seeds():
    r=load('r','run_neighbor_replicate.py'); assert r.ROWS==[22,26] and r.REPLICATES==[1,2,3,4,5,6] and r.PHOTONS==200_000
    assert r.SEED_BASE=={1:973_000_000,2:974_000_000,3:975_000_000,4:976_000_000,5:977_000_000,6:978_000_000}
    new={r.SEED_BASE[q]+row*1000+ray for q in r.REPLICATES for row in r.ROWS for ray in range(1,65)}; consumed={base+row*1000+ray for base in range(955_000_000,973_000_000,1_000_000) for row in r.ROWS for ray in range(1,65)}
    assert len(new)==768 and new.isdisjoint(consumed) and 768*200_000==153_600_000

def test_preflight_normalizes_only_runtime_identity_lines():
    p=load('p','preflight.py'); a='mc_photons 50000\nmc_randomseed 1\nmc_basename /a\naerosol_set_tau_at_wvl 550 0.3\n'; b='mc_photons 200000\nmc_randomseed 2\nmc_basename /b\naerosol_set_tau_at_wvl 550 0.3\n'; assert p.normalize(a)==p.normalize(b)
    assert p.normalize(a)!=p.normalize(b.replace('0.3','0.31'))

def test_analysis_universe_and_statistics():
    a=load('a','analyze.py'); assert a.FIVE_ROWS==[22,23,24,25,26] and a.TARGET_ROWS==[23,24,25] and a.REPLICATES==[1,2,3,4,5,6]
    s=a.sample_stats([1,2,3,4,5,6]); assert s['mean']==3.5 and abs(s['sampleSd']-statistics.stdev([1,2,3,4,5,6]))<1e-15
