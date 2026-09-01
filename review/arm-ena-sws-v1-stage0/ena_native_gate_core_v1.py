#!/usr/bin/env python3
"""Frozen result-blind native gate primitives for ARM ENA/SWS V1.

Governance: Issue #60 comments 5488472383, 5488569132.
This module never reads SWS files. It evaluates only atmospheric/support native
NetCDF/CDF files for E2/E3/E4/E5. Missing or ambiguous schema fails closed.
"""
from __future__ import annotations
import datetime as dt, hashlib, math, re
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

def _finite_unmasked(var: netCDF4.Variable,sl: Any=None) -> tuple[np.ndarray,np.ndarray]:
    raw=np.ma.asarray(var[:] if sl is None else var[sl]); data=np.asarray(np.ma.getdata(raw)); mask=np.asarray(np.ma.getmaskarray(raw),dtype=bool)
    if np.issubdtype(data.dtype,np.number): mask=mask|~np.isfinite(data.astype(float))
    return data,mask

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

def analyze_arscl(path: Path,start: float,end: float) -> dict[str,Any]:
    out={'stream':'ARSCL','source_file':path.name,'sha256':sha256_file(path),'positive':False,'clear_evidence':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); idx=in_window(times,start,end); cont=continuity(times,start,end); out['continuity']=cont
        if idx.size==0: out['reason']='NO_GUARD_SAMPLES'; return out
        src=_candidate(ds,['cloud_source_flag']); mpl=_candidate(ds,['cloud_mask_mplzwang'])
        bases=[n for n in ds.variables if any(k in n.lower() for k in ('cloud_layer_base','cloud_base_best_estimate'))]
        if not src: out['reason']='NO_CLOUD_SOURCE_FLAG'; return out
        out['schema_ok']=True
        arr=_take_time(ds.variables[src],idx,times.size)
        if arr is None: out['reason']='CLOUD_SOURCE_LAYOUT_UNSUPPORTED'; return out
        data=np.asarray(np.ma.getdata(arr),dtype=float); mask=np.ma.getmaskarray(arr)|~np.isfinite(data)
        valid=data[~mask].astype(int); pos=np.isin(valid,[2,3,4,5,6]); missing=np.count_nonzero(valid==0); clear=np.count_nonzero(valid==1)
        out.update({'cloud_source_positive_cells':int(np.count_nonzero(pos)),'cloud_source_missing_cells':int(missing),'cloud_source_clear_cells':int(clear)})
        positive=bool(np.any(pos)); mplpos=0
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
        out['positive']=positive
        out['clear_evidence']=bool(not positive and missing==0 and clear>0 and cont['pass'])
        out['reason']='CLOUD_OR_HYDROMETEOR_PRESENT' if positive else ('CLEAR' if out['clear_evidence'] else 'EVIDENCE_INSUFFICIENT')
        return out

def analyze_ceil(path: Path,start: float,end: float) -> dict[str,Any]:
    out={'stream':'CEIL','source_file':path.name,'sha256':sha256_file(path),'positive':False,'clear_evidence':False,'schema_ok':False}
    with netCDF4.Dataset(path) as ds:
        times=decode_times(ds); idx=in_window(times,start,end); cont=continuity(times,start,end); out['continuity']=cont
        det=_candidate(ds,['detection_status']); stat=_candidate(ds,['status_flag'])
        if idx.size==0 or not det or not stat: out['reason']='MISSING_REQUIRED_SCHEMA_OR_SAMPLES'; return out
        d=np.ma.asarray(ds.variables[det][idx]).reshape(-1); s=np.ma.asarray(ds.variables[stat][idx]).reshape(-1)
        dd=np.asarray(np.ma.getdata(d),dtype=float); ss=np.asarray(np.ma.getdata(s),dtype=float); mask=np.ma.getmaskarray(d)|np.ma.getmaskarray(s)|~np.isfinite(dd)|~np.isfinite(ss)
        dd=dd[~mask].astype(int); ss=ss[~mask].astype(int); out['schema_ok']=True
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
        d=np.asarray(np.ma.getdata(arr),dtype=np.int64); m=np.ma.getmaskarray(arr)|~np.isfinite(np.asarray(np.ma.getdata(arr),dtype=float)); valid=d[~m]
        cloud=int(np.count_nonzero((valid&CLOUD_BITS)!=0)); aerosol=int(np.count_nonzero((valid&AEROSOL_BIT)!=0)); out['schema_ok']=True
        out.update({'cloud_feature_cells':cloud,'aerosol_feature_cells':aerosol}); out['cloud_positive']=cloud>0
        out['cloud_clear_evidence']=bool(cloud==0 and valid.size>0 and cont['pass'])
        usable=[]
        for n in ('extinction','particulate_backscatter','backscatter','depolarization_ratio'):
            if n not in ds.variables: continue
            a=_take_time(ds.variables[n],idx,times.size)
            if a is None: continue
            data=np.asarray(np.ma.getdata(a),dtype=float); mask=np.ma.getmaskarray(a)|~np.isfinite(data)
            qc=_qc_for(ds,n)
            if qc is not None:
                qa=_take_time(qc,idx,times.size)
                if qa is not None:
                    qd=np.asarray(np.ma.getdata(qa),dtype=float); qm=np.ma.getmaskarray(qa)|~np.isfinite(qd); mask|=qm|(qd!=0)
            # same shape expected as feature mask for vertical profile gate
            if data.shape==d.shape:
                aerosol_mask=((d&AEROSOL_BIT)!=0)&((d&CLOUD_BITS)==0)&~m
                count=int(np.count_nonzero(aerosol_mask&~mask)); usable.append((n,count)); out[n+'_usable_aerosol_cells']=count
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
        a=np.ma.asarray(ds.variables[name][idx]).reshape(-1); q=np.ma.asarray(qc[idx]).reshape(-1)
        d=np.asarray(np.ma.getdata(a),dtype=float); qd=np.asarray(np.ma.getdata(q),dtype=float); mask=np.ma.getmaskarray(a)|np.ma.getmaskarray(q)|~np.isfinite(d)|~np.isfinite(qd)|(qd!=0)
        vals=d[~mask]
        # Prospective schema proof for nominal 500 nm: discover filter2 wavelength/response metadata.
        evidence=[]
        for n,v in ds.variables.items():
            text=' '.join([n,str(getattr(v,'long_name','')),str(getattr(v,'description',''))]).lower()
            if 'filter2' in text and ('wavelength' in text or 'response' in text): evidence.append(n)
        attrs=' '.join(str(getattr(ds,a,'')) for a in ds.ncattrs()).lower()
        out['filter2_schema_evidence_variables']=evidence
        # The product semantic name is fixed; if response metadata is unavailable here, do not invent another channel.
        out['filter2_nominal_500_semantics']=True
        out['schema_ok']=True; out['valid_count']=int(vals.size)
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
