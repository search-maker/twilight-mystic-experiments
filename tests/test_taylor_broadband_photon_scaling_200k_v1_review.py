from __future__ import annotations

import importlib.util
import pathlib
import statistics

ROOT=pathlib.Path(__file__).resolve().parents[1]
PKG=ROOT/'experiments'/'taylor-broadband-photon-scaling-200k-v1'


def load(name,filename):
    p=PKG/filename; s=importlib.util.spec_from_file_location(name,p); assert s and s.loader
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def test_frozen_200k_universe_and_fresh_seeds():
    r=load('runner','run_default_replicate.py')
    assert r.ROWS==[23,24,25]
    assert r.REPLICATES==[1,2,3,4,5,6]
    assert r.PHOTONS==200_000
    assert r.SEED_BASE=={1:961_000_000,2:962_000_000,3:963_000_000,4:964_000_000,5:965_000_000,6:966_000_000}
    new={r.SEED_BASE[rep]+row*1000+ray for rep in r.REPLICATES for row in r.ROWS for ray in range(1,65)}
    old={base+row*1000+ray for base in range(955_000_000,961_000_000,1_000_000) for row in r.ROWS for ray in range(1,65)}
    assert len(new)==1152 and len(new)==3*6*64
    assert new.isdisjoint(old)
    assert 1152*200_000==230_400_000


def test_preflight_normalizes_only_intentional_runtime_identity_lines():
    p=load('pre','preflight.py')
    a='aerosol_default\nmc_photons 50000\nmc_randomseed 1\nmc_basename /a\naerosol_set_tau_at_wvl 550 0.3\n'
    b='aerosol_default\nmc_photons 200000\nmc_randomseed 2\nmc_basename /b\naerosol_set_tau_at_wvl 550 0.3\n'
    assert p.normalize(a)==p.normalize(b)
    c=b.replace('aerosol_set_tau_at_wvl 550 0.3','aerosol_set_tau_at_wvl 550 0.31')
    assert p.normalize(a)!=p.normalize(c)


def test_analysis_reference_and_statistics_are_frozen():
    a=load('analysis','analyze_scaling.py')
    assert a.ROWS==[23,24,25]
    assert a.REPLICATES==[1,2,3,4,5,6]
    assert a.PHOTONS==200_000
    s=a.stats([1,2,3,4,5,6])
    assert s['n']==6 and s['mean']==3.5
    assert abs(s['sampleSd']-statistics.stdev([1,2,3,4,5,6]))<1e-15
