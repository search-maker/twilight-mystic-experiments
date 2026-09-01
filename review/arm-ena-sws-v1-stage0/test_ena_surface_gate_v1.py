#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('E6',HERE/'ena_surface_gate_v1.py')
E6=importlib.util.module_from_spec(spec); spec.loader.exec_module(E6)

class FakeVar:
    def __init__(self,data,**attrs): self.data=np.ma.asarray(data); self.__dict__.update(attrs)
    def __getitem__(self,key): return self.data[key]
class FakeDS:
    def __init__(self,variables): self.variables=variables

def rec(center=500.0,n=35,start=0.0,value=1.0):
    return {'epochs':[start+20*i for i in range(n)],'values':[value]*n,'rows':list(range(n)),
            'centers':[center],'center_evidence':[{'ok':True,'center_nm':center,'evidence_type':'TEST'}],'sources':[]}

def main():
    # Frozen global greedy pairing and deterministic tie behavior.
    assert E6.deterministic_pairs([0,10,20],[1,11,21],[0,1,2],[0,1,2]) == [(0,0,1.0),(1,1,1.0),(2,2,1.0)]
    assert E6.deterministic_pairs([0,5],[4],[0,1],[0]) == [(1,0,1.0)]
    assert E6.deterministic_pairs([0],[15.0000001],max_dt_s=15.0) == []

    # Unit-bearing centroid only; no unit means fail closed.
    assert abs(E6.parse_centroid_attribute('413.3 nm')-413.3)<1e-12
    assert abs(E6.parse_centroid_attribute(0.5,'um')-500.0)<1e-12
    assert E6.parse_centroid_attribute(500.0,None) is None
    assert abs(E6.response_weighted_center_nm([400,500],[1,1],'nm')-450.0)<1e-12

    # Native measured-CWL scalar accepted, nominal prose not accepted.
    ds=FakeDS({'hemisp_narrowband_filter2':FakeVar([1,2]),
               'filter2_CWL_measured':FakeVar([500.1],units='nm',long_name='measured center wavelength filter2')})
    c=E6.measured_center_from_dataset(ds,2,'hemisp_narrowband_filter2')
    assert c['ok'] and abs(c['center_nm']-500.1)<1e-12 and c['evidence_type']=='MEASURED_CWL_VARIABLE'
    ds2=FakeDS({'hemisp_narrowband_filter2':FakeVar([1,2],explanation_of_narrowband_channel='nominal center wavelength is 500 nm')})
    assert not E6.measured_center_from_dataset(ds2,2,'hemisp_narrowband_filter2')['ok']

    # Spectral gate: 6 filters, >=30 valid pairs, QC assumed upstream, physical ratios.
    mfr={i:rec(center=400+i*50,n=35,start=0,value=0.2) for i in E6.FILTERS}
    mfrsr={i:rec(center=400+i*50+1,n=35,start=1,value=1.0) for i in E6.FILTERS}
    s=E6.evaluate_spectral_surface(mfr,mfrsr)
    assert s['pass']
    assert all(v['valid_ratio_count']==35 and abs(v['albedo_median']-0.2)<1e-12 for v in s['filters'].values())

    # Center mismatch and insufficient support fail closed.
    bad={i:rec(center=400+i*50+1,n=35,start=1,value=1.0) for i in E6.FILTERS}; bad[3]=rec(center=999,n=35,start=1,value=1.0)
    assert not E6.evaluate_spectral_surface(mfr,bad)['pass']
    short={i:rec(center=400+i*50+1,n=35,start=1,value=1.0) for i in E6.FILTERS}; short[4]=rec(center=601,n=29,start=1,value=1.0)
    assert not E6.evaluate_spectral_surface(mfr,short)['pass']
    print('PASS ENA E6 pure synthetic contracts')

if __name__=='__main__': main()
