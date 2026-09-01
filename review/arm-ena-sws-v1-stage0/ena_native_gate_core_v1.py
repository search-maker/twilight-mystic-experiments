#!/usr/bin/env python3
"""Frozen result-blind native gate primitives for ARM ENA/SWS V1.

Governance: Issue #60 comments 5488472383, 5488569132.
This module never reads SWS files. It evaluates only atmospheric/support native
NetCDF/CDF files for E2/E3/E4/E5. Missing or ambiguous schema fails closed.
"""
from __future__ import annotations
import datetime as dt, hashlib, math
from pathlib import Path
from typing import Any, Iterable
import netCDF4
import numpy as np

UTC=dt.timezone.utc
CLOUD_BITS=4|8|16|32|64
AEROSOL_BIT=2


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def iso_epoch(x: float) -> str:
    return dt.datetime.fromtimestamp(float(x),UTC).isoformat(timespec='microseconds').replace('+00:00','Z')

def parse_iso(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC).timestamp()

def _decoded_datetime(x: Any) -> dt.datetime:
    return dt.datetime(int(x.year),int(x.month),int(x.day),int(x.hour),int(x.minute),int(x.second),int(getattr(x,'microsecond',0)),tzinfo=UTC)

def decode_times(ds: netCDF4.Dataset) -> np.ndarray:
    if 'time' in ds.variables:
        v=ds.variables['time']; units=getattr(v,'units',None)
        if units:
            raw=np.ma.asarray(v[:]).reshape(-1); data=np.asarray(np.ma.getdata(raw),dtype=float); mask=np.ma.getmaskarray(raw)|~np.isfinite(data)
            out=np.full(data.shape,np.nan); idx=np.flatnonzero(~mask)
            if idx.size:
                vals=netCDF4.num2date(data[idx],units=units,calendar=getattr(v,'calendar','standard'))
                out[idx]=[_decoded_datetime(x).timestamp() for x in vals]
            return out
    if 'base_time' in ds.variables and 'time_offset' in ds.variables:
        base=float(np.ma.asarray(ds.variables['base_time'][:]).squeeze())
        raw=np.ma.asarray(ds.variables['time_offset'][:]).reshape(-1); data=np.asarray(np.ma.getdata(raw),dtype=float); mask=np.ma.getmaskarray(raw)|~np.isfinite(data)
        out=np.full(data.shape,np.nan); out[~mask]=base+data[~mask]; return out
    return np.array([],dtype=float)

def in_window(times: np.ndarray,start: float,end: float) -> np.ndarray:
    return np.flatnonzero(np.isfinite(times)&(times>=start-1e-6)&(times<=end+1e-6))

def continuity(times: np.ndarray,start: float,end: float) -> dict[str,Any]:
    t=np.sort(np.unique(times[np.isfinite(times)]))
    inside=t[(t>=start-1e-6)&(t<=end+1e-6)]
    if t.size<2 or inside.size==0:
        return {'pass':False,'reason':'NO_USABLE_TIMESTAMPS','sample_count':int(inside.size)}
    d=np.diff(t); d=d[np.isfinite(d)&(d>0)]
    med=float(np.median(d)) if d.size else math.nan
    interior=np.diff(inside); maxgap=float(np.max(interior)) if interior.size else 0.0
    bracket=bool(t[0]<=start+1e-6 and t[-1]>=end-1e-6)
    gap_ok=bool(np.isfinite(med) and (maxgap<=2.0*med+1e-6))
    return {'pass':bool(bracket and gap_ok),'reason':('PASS' if bracket and gap_ok else ('NO_BRACKET' if not bracket else 'INTERIOR_GAP')),
            'sample_count':int(inside.size),'median_cadence_s':med,'max_interior_gap_s':maxgap,
            'first_time_utc':iso_epoch(t[0]),'last_time_utc':iso_epoch(t[-1]),'bracket':bracket,'gap_ok':gap_ok}

def _candidate(ds: netCDF4.Dataset,names: Iterable[str]) -> str|None:
    for n in names:
        if n in ds.variables: return n
    return None

def _names_containing(ds: netCDF4.Dataset,*parts: str) -> list[str]:
    out=[]
    for n,v in ds.variables.items():
        text=' '.join([n,str(getattr(v,'long_name','')),str(getattr(v,'standard_name','')),str(getattr(v,'description',''))]).lower()
        if all(p.lower() in text for p in parts): out.append(n)
    return out

def _qc_for(ds: netCDF4.Dataset,name: str) -> netCDF4.Variable|None:
    for q in ('qc_'+name,name+'_qc'):
        if q in ds.variables: return ds.variables[q]
    return None

def _take_time(var: netCDF4.Variable,idx: np.ndarray,ntime: int) -> np.ma.MaskedArray|None:
    dims=tuple(var.dimensions)
    if 'time' not in dims: return None
    ax=dims.index('time')
    if var.shape[ax]!=ntime: return None
    sl=[slice(None)]*var.ndim; sl[ax]=idx
    return np.ma.asarray(var[tuple(sl)])

def _same_shape_data(arr: np.ma.MaskedArray|None,shape: tuple[int,...]) -> tuple[np.ndarray,np.ndarray]|None:
    if arr is None or arr.shape!=shape: return None
    data=np.asarray(np.ma.getdata(arr),dtype=float); mask=np.ma.getmaskarray(arr)|~np.isfinite(data)
    return data,mask

def analyze_arscl(path: Path,start: float,end: float) -> dict[str,Any]:
    out={'stream':'ARSCL','source_file':path.name,'sha256':sha256_file(path),'positive':False,'clear_evidence':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); idx=in_window(times,start,end); cont=continuity(times,start,end); out['continuity']=cont
        if idx.size==0: out['reason']='NO_GUARD_SAMPLES'; return out
        src=_candidate(ds,['cloud_source_flag']); mpl=_candidate(ds,['cloud_mask_mplzwang'])
        bases=[n for n in ds.variables if any(k in n.lower() for k in ('cloud_layer_base','cloud_base_best_estimate'))]
        if not src: out['reason']='NO_CLOUD_SOURCE_FLAG'; return out
        arr=_take_time(ds.variables[src],idx,times.size)
        if arr is None: out['reason']='CLOUD_SOURCE_LAYOUT_UNSUPPORTED'; return out
        data=np.asarray(np.ma.getdata(arr),dtype=float); mask=np.ma.getmaskarray(arr)|~np.isfinite(data)
        flags=np.where(mask,-999999,data).astype(int)
        out['schema_ok']=True

        missing=int(np.count_nonzero((flags==0)&~mask)); clear=int(np.count_nonzero((flags==1)&~mask))
        direct_supported=((flags==2)|(flags==4))&~mask
        unsupported=((flags==5)|(flags==6))&~mask

        # Radar-only flag 3 is a valid veto only when the same cell has a finite
        # reflectivity estimate whose native QC is explicitly good (QC==0).
        radar_only=(flags==3)&~mask
        radar_valid=np.zeros(flags.shape,dtype=bool)
        radar_schema=None
        for refl_name,qc_name in (('reflectivity_best_estimate','qc_reflectivity_best_estimate'),('reflectivity','qc_reflectivity')):
            if refl_name not in ds.variables or qc_name not in ds.variables: continue
            rpair=_same_shape_data(_take_time(ds.variables[refl_name],idx,times.size),flags.shape)
            qpair=_same_shape_data(_take_time(ds.variables[qc_name],idx,times.size),flags.shape)
            if rpair is None or qpair is None: continue
            rd,rm=rpair; qd,qm=qpair
            radar_valid=radar_only & ~rm & ~qm & (qd==0)
            radar_schema=f'{refl_name}+{qc_name}'
            break
        radar_positive=int(np.count_nonzero(radar_valid))
        radar_unresolved=int(np.count_nonzero(radar_only & ~radar_valid))
        supported_positive=direct_supported|radar_valid
        out.update({
            'cloud_source_supported_positive_cells':int(np.count_nonzero(supported_positive)),
            'cloud_source_radar_only_qc0_positive_cells':radar_positive,
            'cloud_source_radar_only_unresolved_cells':radar_unresolved,
            'cloud_source_unsupported_flag5_6_cells':int(np.count_nonzero(unsupported)),
            'cloud_source_missing_cells':missing,'cloud_source_clear_cells':clear,
            'radar_qc_schema':radar_schema,
        })
        positive=bool(np.any(supported_positive)); mplpos=0
        if mpl:
            marr=_take_time(ds.variables[mpl],idx,times.size)
            if marr is not None:
                md=np.asarray(np.ma.getdata(marr),dtype=float); mm=np.ma.getmaskarray(marr)|~np.isfinite(md); mplpos=int(np.count_nonzero((md==1)&~mm)); positive|=mplpos>0
        out['mpl_cloud_cells']=mplpos
        basepos=0
        for n in bases:
            a=_take_time(ds.variables[n],idx,times.size)
            if a is None: continue
            d=np.asarray(np.ma.getdata(a),dtype=float); m=np.ma.getmaskarray(a)|~np.isfinite(d); basepos+=int(np.count_nonzero((d>=0)&~m))
        out['cloud_base_positive_cells']=basepos; positive|=basepos>0
        unresolved=bool(missing>0 or radar_unresolved>0 or np.any(unsupported))
        out['positive']=positive
        out['clear_evidence']=bool(not positive and not unresolved and clear>0 and cont['pass'])
        out['reason']='CLOUD_OR_HYDROMETEOR_PRESENT' if positive else ('CLEAR' if out['clear_evidence'] else 'EVIDENCE_INSUFFICIENT')
        return out

def analyze_ceil(path: Path,start: float,end: float) -> dict[str,Any]:
    out={'stream':'CEIL','source_file':path.name,'sha256':sha256_file(path),'positive':False,'clear_evidence':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); idx=in_window(times,start,end); cont=continuity(times,start,end); out['continuity']=cont
        det=_candidate(ds,['detection_status']); stat=_candidate(ds,['status_flag'])
        if idx.size==0 or not det or not stat: out['reason']='MISSING_REQUIRED_SCHEMA_OR_SAMPLES'; return out
        d=np.ma.asarray(ds.variables[det][idx]).reshape(-1); s=np.ma.asarray(ds.variables[stat][idx]).reshape(-1)
        dd=np.asarray(np.ma.getdata(d),dtype=float); ss=np.asarray(np.ma.getdata(s),dtype=float); m=np.ma.getmaskarray(d)|np.ma.getmaskarray(s)|~np.isfinite(dd)|~np.isfinite(ss)
        dd=dd[~m].astype(int); ss=ss[~m].astype(int); out['schema_ok']=True
        pos=int(np.count_nonzero(np.isin(dd,[1,2,3,4])&np.isin(ss,[0,1]))); alarms=int(np.count_nonzero(ss==2)); clear=int(np.count_nonzero((dd==0)&np.isin(ss,[0,1])))
        out.update({'positive_samples':pos,'alarm_samples':alarms,'clear_samples':clear}); out['positive']=pos>0
        out['clear_evidence']=bool(pos==0 and alarms==0 and clear==len(dd) and len(dd)>0 and cont['pass'])
        out['reason']='CLOUD_OR_HYDROMETEOR_PRESENT' if pos else ('CLEAR' if out['clear_evidence'] else 'EVIDENCE_INSUFFICIENT'); return out

def _feature_var(ds: netCDF4.Dataset) -> str|None:
    if 'feature_mask' in ds.variables: return 'feature_mask'
    found=_names_containing(ds,'feature','mask'); return found[0] if len(found)==1 else None

def analyze_raman(path: Path,start: float,end: float) -> dict[str,Any]:
    out={'stream':'RAMAN','source_file':path.name,'sha256':sha256_file(path),'cloud_positive':False,'cloud_clear_evidence':False,'e3_profile_usable':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); idx=in_window(times,start,end); cont=continuity(times,start,end); out['continuity']=cont
        feat=_feature_var(ds)
        if idx.size==0 or not feat: out['reason']='NO_FEATURE_MASK_OR_SAMPLES'; return out
        arr=_take_time(ds.variables[feat],idx,times.size)
        if arr is None: out['reason']='FEATURE_MASK_LAYOUT_UNSUPPORTED'; return out
        raw=np.asarray(np.ma.getdata(arr),dtype=float); m=np.ma.getmaskarray(arr)|~np.isfinite(raw); d=np.where(m,0,raw).astype(np.int64); valid=d[~m]
        cloud=int(np.count_nonzero((valid&CLOUD_BITS)!=0)); aerosol=int(np.count_nonzero((valid&AEROSOL_BIT)!=0)); out['schema_ok']=True
        out.update({'cloud_feature_cells':cloud,'aerosol_feature_cells':aerosol}); out['cloud_positive']=cloud>0
        out['cloud_clear_evidence']=bool(cloud==0 and valid.size>0 and cont['pass'])
        usable=[]
        for n in ('extinction','particulate_backscatter','backscatter','depolarization_ratio'):
            if n not in ds.variables: continue
            a=_take_time(ds.variables[n],idx,times.size)
            if a is None: continue
            vals=np.asarray(np.ma.getdata(a),dtype=float); vm=np.ma.getmaskarray(a)|~np.isfinite(vals)
            qc=_qc_for(ds,n)
            if qc is not None:
                qa=_take_time(qc,idx,times.size)
                if qa is not None and qa.shape==vals.shape:
                    qd=np.asarray(np.ma.getdata(qa),dtype=float); qm=np.ma.getmaskarray(qa)|~np.isfinite(qd); vm|=qm|(qd!=0)
                else:
                    vm|=True
            else:
                vm|=True
            if vals.shape==d.shape:
                aerosol_mask=((d&AEROSOL_BIT)!=0)&((d&CLOUD_BITS)==0)&~m
                count=int(np.count_nonzero(aerosol_mask&~vm)); usable.append((n,count)); out[n+'_usable_aerosol_cells']=count
        out['e3_profile_usable']=bool(cont['pass'] and aerosol>0 and any(c>0 for _,c in usable))
        out['reason']='CLOUD_OR_HYDROMETEOR_PRESENT' if cloud else ('PROFILE_USABLE' if out['e3_profile_usable'] else 'PROFILE_EVIDENCE_INSUFFICIENT')
        return out

def analyze_mfrsr(path: Path,start: float,end: float,aeronet_median: float) -> dict[str,Any]:
    out={'stream':'MFRSR_AOD','source_file':path.name,'sha256':sha256_file(path),'pass':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); idx=in_window(times,start,end)
        name=_candidate(ds,['aerosol_optical_depth_filter2'])
        if idx.size==0 or not name: out['reason']='NO_NATIVE_FILTER2_AOD_OR_SAMPLES'; return out
        qc=_qc_for(ds,name)
        if qc is None: out['reason']='NO_NATIVE_FILTER2_QC'; return out

        # Native 500-nm identity is not inferred from the filter number. The
        # measured center wavelength itself must be present and lie in 495..505 nm.
        cwl_name=_candidate(ds,['filter2_CWL_measured'])
        if not cwl_name:
            out['reason']='FILTER2_WAVELENGTH_UNVERIFIED'; return out
        craw=np.ma.asarray(ds.variables[cwl_name][:]); cd=np.asarray(np.ma.getdata(craw),dtype=float).reshape(-1); cm=np.ma.getmaskarray(craw).reshape(-1)|~np.isfinite(cd)
        cvals=cd[~cm]
        if cvals.size==0:
            out['reason']='FILTER2_WAVELENGTH_UNVERIFIED'; return out
        cwl=float(np.median(cvals)); out['filter2_cwl_measured_nm']=cwl; out['filter2_cwl_sample_count']=int(cvals.size)
        if not (495.0<=cwl<=505.0) or np.any((cvals<495.0)|(cvals>505.0)):
            out['reason']='FILTER2_WAVELENGTH_OUT_OF_FROZEN_500NM_RANGE'; return out

        a=np.ma.asarray(ds.variables[name][idx]).reshape(-1); q=np.ma.asarray(qc[idx]).reshape(-1)
        d=np.asarray(np.ma.getdata(a),dtype=float); qd=np.asarray(np.ma.getdata(q),dtype=float); mask=np.ma.getmaskarray(a)|np.ma.getmaskarray(q)|~np.isfinite(d)|~np.isfinite(qd)|(qd!=0)
        vals=d[~mask]
        evidence=[]
        for n,v in ds.variables.items():
            text=' '.join([n,str(getattr(v,'long_name','')),str(getattr(v,'description',''))]).lower()
            if 'filter2' in text and ('wavelength' in text or 'response' in text or 'cwl' in text): evidence.append(n)
        out['filter2_schema_evidence_variables']=evidence; out['schema_ok']=True; out['valid_count']=int(vals.size)
        if vals.size:
            med=float(np.median(vals)); p10=float(np.percentile(vals,10)); p90=float(np.percentile(vals,90)); spread=p90-p10; diff=abs(med-aeronet_median)
            out.update({'median_aod500':med,'p10_aod500':p10,'p90_aod500':p90,'p90_minus_p10':spread,'abs_median_diff_vs_aeronet':diff})
            out['pass']=bool(vals.size>=15 and spread<=0.015+1e-12 and diff<=0.020+1e-12)
            out['reason']='PASS' if out['pass'] else ('MIN_COUNT' if vals.size<15 else ('STABILITY' if spread>0.015+1e-12 else 'CROSS_SOURCE_DISAGREEMENT'))
        else: out['reason']='NO_VALID_QC0_RETRIEVALS'
        return out

def analyze_sonde(path: Path) -> dict[str,Any]:
    out={'stream':'SONDE','source_file':path.name,'sha256':sha256_file(path),'usable':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); names={k:_candidate(ds,[k]) for k in ('pres','tdry','rh','alt')}
        if not times.size or any(v is None for v in names.values()): out['reason']='MISSING_REQUIRED_SCHEMA'; return out
        vals={}; mask=None
        for k,n in names.items():
            a=np.ma.asarray(ds.variables[n][:]).reshape(-1); d=np.asarray(np.ma.getdata(a),dtype=float); m=np.ma.getmaskarray(a)|~np.isfinite(d)
            if k in ('pres','tdry','rh'):
                q=_qc_for(ds,n)
                if q is None: out['reason']='MISSING_QC_'+k.upper(); return out
                qa=np.ma.asarray(q[:]).reshape(-1); qd=np.asarray(np.ma.getdata(qa),dtype=float); m|=np.ma.getmaskarray(qa)|~np.isfinite(qd)|(qd!=0)
            vals[k]=d; mask=m.copy() if mask is None else mask|m
        n=min(len(x) for x in vals.values()); mask=mask[:n]
        for k in vals: vals[k]=vals[k][:n]
        good=~mask; out['schema_ok']=True; out['good_profile_samples']=int(np.count_nonzero(good))
        if not np.any(good): out['reason']='NO_QC_GOOD_COMMON_PROFILE'; return out
        gt=times[np.isfinite(times)]; launch=float(np.min(gt)) if gt.size else math.nan
        top=float(np.max(vals['alt'][good])); bottom=float(np.min(vals['alt'][good]))
        out.update({'usable':True,'launch_time_utc':iso_epoch(launch),'launch_epoch':launch,'measured_bottom_alt':bottom,'measured_top_alt':top,'reason':'PASS'}); return out

def choose_sonde_pair(records: list[dict[str,Any]],reference_epoch: float,max_hours: float=6.0) -> dict[str,Any]:
    usable=[r for r in records if r.get('usable') and math.isfinite(float(r.get('launch_epoch',math.nan)))]
    before=[r for r in usable if r['launch_epoch']<reference_epoch and reference_epoch-r['launch_epoch']<=max_hours*3600+1e-6]
    after=[r for r in usable if r['launch_epoch']>reference_epoch and r['launch_epoch']-reference_epoch<=max_hours*3600+1e-6]
    if not before or not after: return {'pass':False,'reason':'NO_TWO_SIDED_SONDE_WITHIN_6H'}
    b=max(before,key=lambda r:r['launch_epoch']); a=min(after,key=lambda r:r['launch_epoch'])
    common_top=min(float(b['measured_top_alt']),float(a['measured_top_alt']))
    return {'pass':True,'reason':'THERMO_TWO_SIDED_SUPPORTED','before_file':b['source_file'],'after_file':a['source_file'],
            'before_offset_hours':(reference_epoch-b['launch_epoch'])/3600.0,'after_offset_hours':(a['launch_epoch']-reference_epoch)/3600.0,
            'common_measured_top_alt':common_top,'above_common_top_label':'ASSUMED_STANDARD_EXTENSION_SENSITIVITY'}

def combine_e2(arscl: dict[str,Any]|None,ceil: dict[str,Any]|None,raman: dict[str,Any]|None) -> dict[str,Any]:
    parts=[x for x in (arscl,ceil,raman) if x is not None]
    if any(bool(x.get('positive') or x.get('cloud_positive')) for x in parts):
        return {'disposition':'CLOUD_OR_HYDROMETEOR_PRESENT','pass':False}
    if arscl and ceil and raman and bool(arscl.get('clear_evidence')) and bool(ceil.get('clear_evidence')) and bool(raman.get('cloud_clear_evidence')):
        return {'disposition':'CLEAR_MULTI_SENSOR','pass':True}
    return {'disposition':'CLEAR_EVIDENCE_INSUFFICIENT','pass':False}
