#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, tempfile
from pathlib import Path
import netCDF4
import numpy as np
import ena_native_gate_core_v1 as G

UTC=dt.timezone.utc
BASE=dt.datetime(2019,1,1,tzinfo=UTC).timestamp()
START=BASE+100; END=BASE+200

def add_time(ds,n=31,step=10):
    ds.createDimension('time',n); t=ds.createVariable('time','f8',('time',)); t.units='seconds since 1970-01-01 00:00:00 UTC'; t[:]=BASE+np.arange(n)*step

def make_arscl(p,positive=False,missing=False,radar_qc=0,direct_flag=None):
    with netCDF4.Dataset(p,'w') as ds:
        add_time(ds); ds.createDimension('height',2)
        f=ds.createVariable('cloud_source_flag','i4',('time','height'),fill_value=-9999); f[:]=1
        if positive: f[15,0]=3
        if direct_flag is not None: f[15,0]=direct_flag
        if missing: f[16,1]=0
        m=ds.createVariable('cloud_mask_mplzwang','i4',('time','height'),fill_value=-9999); m[:]=0
        b=ds.createVariable('cloud_base_best_estimate','f4',('time',),fill_value=-9999.); b[:]=-9999.
        r=ds.createVariable('reflectivity_best_estimate','f4',('time','height'),fill_value=-9999.); r[:]=-30.0
        q=ds.createVariable('qc_reflectivity_best_estimate','i4',('time','height')); q[:]=0; q[15,0]=radar_qc

def make_ceil(p,positive=False,alarm=False):
    with netCDF4.Dataset(p,'w') as ds:
        add_time(ds); d=ds.createVariable('detection_status','i4',('time',)); s=ds.createVariable('status_flag','i4',('time',)); d[:]=0; s[:]=0
        if positive: d[15]=1
        if alarm: s[15]=2

def make_raman(p,cloud=False,aerosol=True):
    with netCDF4.Dataset(p,'w') as ds:
        add_time(ds); ds.createDimension('height',2)
        f=ds.createVariable('feature_mask','i4',('time','height')); f[:]=2 if aerosol else 1
        if cloud: f[15,0]=4
        e=ds.createVariable('extinction','f4',('time','height'),fill_value=-9999.); e[:]=0.02
        q=ds.createVariable('qc_extinction','i4',('time','height')); q[:]=0
        b=ds.createVariable('particulate_backscatter','f4',('time','height'),fill_value=-9999.); b[:]=0.001
        qb=ds.createVariable('qc_particulate_backscatter','i4',('time','height')); qb[:]=0
        dep=ds.createVariable('depolarization_ratio','f4',('time','height'),fill_value=-9999.); dep[:]=0.1
        qd=ds.createVariable('qc_depolarization_ratio','i4',('time','height')); qd[:]=0

def make_mfrsr(p,vals,qbad=False,cwl=501.5,include_cwl=True):
    with netCDF4.Dataset(p,'w') as ds:
        add_time(ds,n=len(vals),step=20)
        a=ds.createVariable('aerosol_optical_depth_filter2','f4',('time',),fill_value=-9999.); a[:]=vals
        q=ds.createVariable('qc_aerosol_optical_depth_filter2','i4',('time',)); q[:]=1 if qbad else 0
        if include_cwl:
            w=ds.createVariable('filter2_CWL_measured','f4'); w.long_name='measured center wavelength filter2'; w.assignValue(cwl)

def make_sonde(p,launch,top=16000):
    n=20
    with netCDF4.Dataset(p,'w') as ds:
        ds.createDimension('time',n); t=ds.createVariable('time','f8',('time',)); t.units='seconds since 1970-01-01 00:00:00 UTC'; t[:]=launch+np.arange(n)*60
        for name,val in [('pres',np.linspace(1000,100,n)),('tdry',np.linspace(20,-50,n)),('rh',np.linspace(80,10,n)),('alt',np.linspace(0,top,n))]:
            v=ds.createVariable(name,'f4',('time',)); v[:]=val
            if name!='alt':
                q=ds.createVariable('qc_'+name,'i4',('time',)); q[:]=0

def main():
    with tempfile.TemporaryDirectory() as td:
        r=Path(td)
        make_arscl(r/'a_clear.nc'); make_arscl(r/'a_cloud.nc',positive=True,radar_qc=0); make_arscl(r/'a_radar_bad.nc',positive=True,radar_qc=1)
        make_arscl(r/'a_missing.nc',missing=True); make_arscl(r/'a_mpl.nc',direct_flag=4); make_arscl(r/'a_unknown.nc',direct_flag=5)
        ac=G.analyze_arscl(r/'a_clear.nc',START,END); ap=G.analyze_arscl(r/'a_cloud.nc',START,END); ab=G.analyze_arscl(r/'a_radar_bad.nc',START,END)
        am=G.analyze_arscl(r/'a_missing.nc',START,END); amp=G.analyze_arscl(r/'a_mpl.nc',START,END); au=G.analyze_arscl(r/'a_unknown.nc',START,END)
        assert ac['clear_evidence'] and not ac['positive']
        assert ap['positive'] and ap['cloud_source_radar_only_qc0_positive_cells']==1
        assert not ab['positive'] and not ab['clear_evidence'] and ab['cloud_source_radar_only_unresolved_cells']==1
        assert not am['clear_evidence']; assert amp['positive']; assert not au['positive'] and not au['clear_evidence']

        make_ceil(r/'c_clear.nc'); make_ceil(r/'c_cloud.nc',positive=True); make_ceil(r/'c_alarm.nc',alarm=True)
        cc=G.analyze_ceil(r/'c_clear.nc',START,END); cp=G.analyze_ceil(r/'c_cloud.nc',START,END); ca=G.analyze_ceil(r/'c_alarm.nc',START,END)
        assert cc['clear_evidence']; assert cp['positive']; assert not ca['clear_evidence']

        make_raman(r/'r_clear.nc'); make_raman(r/'r_cloud.nc',cloud=True)
        rc=G.analyze_raman(r/'r_clear.nc',START,END); rp=G.analyze_raman(r/'r_cloud.nc',START,END)
        assert rc['cloud_clear_evidence'] and rc['e3_profile_usable']; assert rp['cloud_positive']
        assert G.combine_e2(ac,cc,rc)['disposition']=='CLEAR_MULTI_SENSOR'; assert G.combine_e2(ap,cc,rc)['disposition']=='CLOUD_OR_HYDROMETEOR_PRESENT'

        vals=np.full(20,0.08); make_mfrsr(r/'m_pass.nc',vals); m=G.analyze_mfrsr(r/'m_pass.nc',BASE,BASE+1000,0.07); assert m['pass'] and 495<=m['filter2_cwl_measured_nm']<=505
        vals2=np.linspace(0.05,0.10,20); make_mfrsr(r/'m_var.nc',vals2); m2=G.analyze_mfrsr(r/'m_var.nc',BASE,BASE+1000,0.07); assert not m2['pass'] and m2['reason']=='STABILITY'
        make_mfrsr(r/'m_wrongwave.nc',vals,cwl=673.0); mw=G.analyze_mfrsr(r/'m_wrongwave.nc',BASE,BASE+1000,0.07); assert not mw['pass'] and mw['reason']=='FILTER2_WAVELENGTH_OUT_OF_FROZEN_500NM_RANGE'
        make_mfrsr(r/'m_nowave.nc',vals,include_cwl=False); mn=G.analyze_mfrsr(r/'m_nowave.nc',BASE,BASE+1000,0.07); assert not mn['pass'] and mn['reason']=='FILTER2_WAVELENGTH_UNVERIFIED'

        make_sonde(r/'s_before.nc',BASE-3600,15000); make_sonde(r/'s_after.nc',BASE+3600,17000)
        sb=G.analyze_sonde(r/'s_before.nc'); sa=G.analyze_sonde(r/'s_after.nc'); pair=G.choose_sonde_pair([sb,sa],BASE,max_hours=6)
        assert pair['pass'] and abs(pair['common_measured_top_alt']-15000)<1
        print('PASS ENA native gate hardened synthetic contracts')

if __name__=='__main__': main()
