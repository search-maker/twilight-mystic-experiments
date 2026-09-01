#!/usr/bin/env python3
"""Frozen result-blind E6 surface gate for ARM ENA/SWS V1.

Governance: Issue #60 comments 5488714659 and 5488750527.
This module NEVER opens SWS files. It evaluates only ENA surface-radiation
products needed for the pre-outcome E6 gate.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np

UTC = dt.timezone.utc
SITE_LAT = 39.0916
SITE_LON = -28.0257
SITE_ALT_M = 30.0
MAX_PAIR_DT_S = 15.0
MIN_FILTER_PAIRS = 30
MAX_CENTER_DIFF_NM = 5.0
FILTERS = tuple(range(1, 7))
CONTROL_COMMENTS = ("5488714659", "5488750527")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _nc4():
    import netCDF4
    return netCDF4


def _decoded_datetime(value: Any) -> dt.datetime:
    return dt.datetime(int(value.year), int(value.month), int(value.day), int(value.hour),
                       int(value.minute), int(value.second), int(getattr(value, "microsecond", 0)), tzinfo=UTC)


def decode_times(ds: Any) -> np.ndarray:
    netCDF4 = _nc4()
    if "time" in ds.variables:
        var = ds.variables["time"]
        units = getattr(var, "units", None)
        if units:
            raw = np.ma.asarray(var[:]).reshape(-1)
            data = np.asarray(np.ma.getdata(raw), dtype=float)
            mask = np.ma.getmaskarray(raw) | ~np.isfinite(data)
            out = np.full(data.shape, np.nan, dtype=float)
            idx = np.flatnonzero(~mask)
            if idx.size:
                vals = netCDF4.num2date(data[idx], units=units, calendar=getattr(var, "calendar", "standard"))
                out[idx] = [_decoded_datetime(x).timestamp() for x in vals]
            return out
    if "base_time" in ds.variables and "time_offset" in ds.variables:
        base_raw = np.ma.asarray(ds.variables["base_time"][:]).squeeze()
        if np.asarray(np.ma.getmaskarray(base_raw)).any():
            return np.array([], dtype=float)
        base = float(np.asarray(np.ma.getdata(base_raw)).squeeze())
        raw = np.ma.asarray(ds.variables["time_offset"][:]).reshape(-1)
        data = np.asarray(np.ma.getdata(raw), dtype=float)
        mask = np.ma.getmaskarray(raw) | ~np.isfinite(data)
        out = np.full(data.shape, np.nan, dtype=float)
        out[~mask] = base + data[~mask]
        return out
    return np.array([], dtype=float)


def solar_elevation_deg(epochs: np.ndarray) -> np.ndarray:
    """Frozen ENA SPA convention: pressure=0, altitude=30 m, same as E0/windows."""
    import pandas as pd
    import pvlib
    idx = pd.to_datetime(np.asarray(epochs, dtype=float), unit="s", utc=True)
    pos = pvlib.solarposition.spa_python(idx, latitude=SITE_LAT, longitude=SITE_LON,
        altitude=SITE_ALT_M, pressure=0.0, temperature=12.0, delta_t=None, how="numpy")
    return np.asarray(pos["elevation"], dtype=float)


def deterministic_pairs(left_epochs: Sequence[float], right_epochs: Sequence[float],
                        left_rows: Sequence[int] | None = None, right_rows: Sequence[int] | None = None,
                        max_dt_s: float = MAX_PAIR_DT_S) -> list[tuple[int, int, float]]:
    """Frozen global greedy one-to-one nearest-time matching from #60 5488750527."""
    left = np.asarray(left_epochs, dtype=float)
    right = np.asarray(right_epochs, dtype=float)
    li = np.arange(left.size, dtype=int) if left_rows is None else np.asarray(left_rows, dtype=int)
    ri = np.arange(right.size, dtype=int) if right_rows is None else np.asarray(right_rows, dtype=int)
    if left.size != li.size or right.size != ri.size:
        raise ValueError("row-index arrays must match epoch arrays")
    candidates: list[tuple[float, float, float, int, int, int, int]] = []
    for a in range(left.size):
        if not np.isfinite(left[a]):
            continue
        for b in range(right.size):
            if not np.isfinite(right[b]):
                continue
            delta = abs(float(left[a] - right[b]))
            if delta <= max_dt_s + 1e-9:
                candidates.append((delta, float(left[a]), float(right[b]), int(li[a]), int(ri[b]), a, b))
    candidates.sort()
    used_l: set[int] = set(); used_r: set[int] = set(); out: list[tuple[int, int, float]] = []
    for delta, _le, _re, _lr, _rr, a, b in candidates:
        if a in used_l or b in used_r:
            continue
        used_l.add(a); used_r.add(b); out.append((a, b, float(delta)))
    out.sort(key=lambda x: (float(left[x[0]]), int(li[x[0]]), float(right[x[1]]), int(ri[x[1]])))
    return out


def _unit_scale_to_nm(units: str) -> float | None:
    u = str(units or "").strip().lower().replace("µ", "u").replace("μ", "u")
    u = re.sub(r"\s+", "", u)
    if u in {"nm", "nanometer", "nanometers", "nanometre", "nanometres"}: return 1.0
    if u in {"um", "micron", "microns", "micrometer", "micrometers", "micrometre", "micrometres"}: return 1000.0
    return None


def parse_centroid_attribute(value: Any, explicit_units: str | None = None) -> float | None:
    if isinstance(value, (int, float, np.integer, np.floating)):
        scale = _unit_scale_to_nm(explicit_units or "")
        return None if scale is None or not np.isfinite(float(value)) else float(value) * scale
    text = str(value).strip().lower().replace("µ", "u").replace("μ", "u")
    m = re.search(r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(nm|um|microns?|nanometers?|nanometres?|micrometers?|micrometres?)\b", text)
    if not m: return None
    scale = _unit_scale_to_nm(m.group(2)); x = float(m.group(1))
    return x * scale if scale is not None and np.isfinite(x) else None


def response_weighted_center_nm(wavelength: Sequence[float], response: Sequence[float], wavelength_units: str) -> float | None:
    w = np.asarray(wavelength, dtype=float).reshape(-1); t = np.asarray(response, dtype=float).reshape(-1)
    scale = _unit_scale_to_nm(wavelength_units)
    if scale is None or w.size == 0 or w.size != t.size: return None
    good = np.isfinite(w) & np.isfinite(t) & (t >= 0)
    if np.count_nonzero(good) < 2: return None
    w = w[good] * scale; t = t[good]; den = float(np.sum(t))
    if not np.isfinite(den) or den <= 0: return None
    center = float(np.sum(w * t) / den)
    return center if np.isfinite(center) and center > 0 else None


def _semantic(name: str, var: Any) -> str:
    return " ".join([name, str(getattr(var,"long_name","")), str(getattr(var,"standard_name","")),
                     str(getattr(var,"description","")), str(getattr(var,"comment",""))]).lower()


def measured_center_from_dataset(ds: Any, filter_n: int, irradiance_var_name: str) -> dict[str, Any]:
    """Fail-closed measured-wavelength evidence hierarchy frozen by #60 5488750527."""
    token = f"filter{filter_n}"
    waves=[]; responses=[]
    for name,var in ds.variables.items():
        s=_semantic(name,var)
        if token not in s or "nominal" in s: continue
        if "wavelength" in s and ("measured" in s or "response" in s or "filter" in s): waves.append((name,var))
        if ("normalized_transmittance" in s or "normalized transmittance" in s or "filter_response" in s or "spectral response" in s): responses.append((name,var))
    for wn,wv in waves:
        for rn,rv in responses:
            try:
                wa=np.ma.asarray(wv[:]).reshape(-1); ra=np.ma.asarray(rv[:]).reshape(-1)
                if wa.size != ra.size or np.any(np.ma.getmaskarray(wa)) or np.any(np.ma.getmaskarray(ra)): continue
                center=response_weighted_center_nm(np.ma.getdata(wa),np.ma.getdata(ra),getattr(wv,"units",""))
            except Exception: continue
            if center is not None: return {"ok":True,"center_nm":center,"evidence_type":"MEASURED_RESPONSE_WEIGHTED","evidence":[wn,rn]}
    for name,var in ds.variables.items():
        s=_semantic(name,var)
        if token not in s or "nominal" in s: continue
        if not (("cwl" in s and "measured" in s) or ("centroid" in s and ("wavelength" in s or "measured" in s))): continue
        try:
            raw=np.ma.asarray(var[:]).reshape(-1); data=np.asarray(np.ma.getdata(raw),dtype=float)
            mask=np.ma.getmaskarray(raw)|~np.isfinite(data); vals=data[~mask]; scale=_unit_scale_to_nm(getattr(var,"units",""))
            if vals.size and scale is not None:
                centers=vals*scale
                if np.all(np.isfinite(centers)) and np.all(centers>0):
                    return {"ok":True,"center_nm":float(np.median(centers)),"evidence_type":"MEASURED_CWL_VARIABLE","evidence":[name],"center_sample_count":int(centers.size)}
        except Exception: continue
    if irradiance_var_name in ds.variables:
        var=ds.variables[irradiance_var_name]
        for attr in ("centroid_wavelength","measured_centroid_wavelength","measured_CWL","measured_cwl"):
            if hasattr(var,attr):
                units=getattr(var,attr+"_units",None) or getattr(var,"wavelength_units",None)
                center=parse_centroid_attribute(getattr(var,attr),units)
                if center is not None:
                    return {"ok":True,"center_nm":center,"evidence_type":"MEASURED_CENTROID_ATTRIBUTE","evidence":[f"{irradiance_var_name}:{attr}"]}
    return {"ok":False,"reason":"MEASURED_WAVELENGTH_EVIDENCE_MISSING_OR_AMBIGUOUS"}


def _qc_good_series(ds: Any, value_name: str) -> tuple[np.ndarray,np.ndarray,np.ndarray] | None:
    qname="qc_"+value_name
    if value_name not in ds.variables or qname not in ds.variables: return None
    times=decode_times(ds); val=np.ma.asarray(ds.variables[value_name][:]).reshape(-1); qc=np.ma.asarray(ds.variables[qname][:]).reshape(-1)
    n=min(times.size,val.size,qc.size)
    if n==0: return None
    times=times[:n]; vd=np.asarray(np.ma.getdata(val[:n]),dtype=float); qd=np.asarray(np.ma.getdata(qc[:n]),dtype=float)
    mask=np.ma.getmaskarray(val[:n])|np.ma.getmaskarray(qc[:n])|~np.isfinite(times)|~np.isfinite(vd)|~np.isfinite(qd)|(qd!=0)
    return times,vd,~mask


def collect_narrowband(paths: Sequence[Path], instrument: str, start: float, end: float) -> dict[int,dict[str,Any]]:
    netCDF4=_nc4()
    if instrument not in {"mfr","mfrsr"}: raise ValueError("instrument must be mfr or mfrsr")
    out={n:{"epochs":[],"values":[],"rows":[],"centers":[],"center_evidence":[],"sources":[]} for n in FILTERS}; offset=0
    for path in sorted(paths,key=lambda p:p.name):
        with netCDF4.Dataset(path,"r") as ds:
            for n in FILTERS:
                name=f"up_hemisp_narrowband_filter{n}" if instrument=="mfr" else f"hemisp_narrowband_filter{n}"
                center=measured_center_from_dataset(ds,n,name)
                if not center.get("ok"): out[n]["center_error"]=center.get("reason"); continue
                series=_qc_good_series(ds,name)
                if series is None: out[n]["series_error"]="VALUE_OR_QC_SCHEMA_MISSING"; continue
                epochs,values,good=series; idx=np.flatnonzero(good&(epochs>=start-1e-6)&(epochs<=end+1e-6))
                if idx.size:
                    elev=solar_elevation_deg(epochs[idx]); idx=idx[np.isfinite(elev)&(elev>=10.0-1e-9)]
                for i in idx.tolist(): out[n]["epochs"].append(float(epochs[i])); out[n]["values"].append(float(values[i])); out[n]["rows"].append(offset+int(i))
                out[n]["centers"].append(float(center["center_nm"])); out[n]["center_evidence"].append(center)
                out[n]["sources"].append({"file":path.name,"sha256":sha256_file(path),"size_bytes":path.stat().st_size})
            offset+=len(decode_times(ds))+1
    return out


def _resolved_center(record: dict[str,Any]) -> dict[str,Any]:
    centers=np.asarray(record.get("centers",[]),dtype=float); centers=centers[np.isfinite(centers)]
    if not centers.size: return {"ok":False,"reason":record.get("center_error","NO_MEASURED_CENTER")}
    if float(np.max(centers)-np.min(centers))>1e-6: return {"ok":False,"reason":"MEASURED_CENTER_CHANGED_ACROSS_SOURCE_FILES","centers_nm":centers.tolist()}
    return {"ok":True,"center_nm":float(centers[0]),"evidence":record.get("center_evidence",[])}


def evaluate_spectral_surface(mfr: dict[int,dict[str,Any]], mfrsr: dict[int,dict[str,Any]]) -> dict[str,Any]:
    filters={}; all_pass=True
    for n in FILTERS:
        up=mfr[n]; dn=mfrsr[n]; cu=_resolved_center(up); cd=_resolved_center(dn); row={"filter":n,"mfr_center":cu,"mfrsr_center":cd}
        if not cu.get("ok") or not cd.get("ok"):
            row.update(pass_=False,reason="MEASURED_WAVELENGTH_UNRESOLVED"); row["pass"]=False; filters[str(n)]=row; all_pass=False; continue
        diff=abs(float(cu["center_nm"])-float(cd["center_nm"])); row["center_diff_nm"]=diff
        if diff>MAX_CENTER_DIFF_NM+1e-12:
            row.update({"pass":False,"reason":"MFR_MFRSR_CENTER_DIFFERENCE_GT_5NM"}); filters[str(n)]=row; all_pass=False; continue
        le=np.asarray(up["epochs"],dtype=float); re=np.asarray(dn["epochs"],dtype=float); lv=np.asarray(up["values"],dtype=float); rv=np.asarray(dn["values"],dtype=float)
        pairs=deterministic_pairs(le,re,up["rows"],dn["rows"]); ratios=[]; invalid=0; deltas=[]
        for a,b,delta in pairs:
            u=float(lv[a]); d=float(rv[b])
            if not(np.isfinite(u) and np.isfinite(d) and d>0 and u>=0): invalid+=1; continue
            ratio=u/d
            if not np.isfinite(ratio) or ratio<0 or ratio>1: invalid+=1; continue
            ratios.append(float(ratio)); deltas.append(float(delta))
        row.update({"paired_candidate_count":len(pairs),"valid_ratio_count":len(ratios),"invalid_ratio_count":invalid,"max_pair_delta_s":max(deltas) if deltas else None})
        if len(ratios)<MIN_FILTER_PAIRS:
            row.update({"pass":False,"reason":"SURFACE_EVIDENCE_INSUFFICIENT"}); filters[str(n)]=row; all_pass=False; continue
        arr=np.asarray(ratios,dtype=float); row.update({"pass":True,"reason":"PASS","albedo_median":float(np.median(arr)),"albedo_p10":float(np.percentile(arr,10)),"albedo_p90":float(np.percentile(arr,90))}); filters[str(n)]=row
    return {"pass":all_pass,"reason":"PASS" if all_pass else "SURFACE_EVIDENCE_INSUFFICIENT","filters":filters}


def _broadband_file(path: Path, value_name: str, start: float, end: float) -> dict[str,Any]:
    netCDF4=_nc4()
    with netCDF4.Dataset(path,"r") as ds:
        series=_qc_good_series(ds,value_name)
        if series is None: return {"ok":False,"reason":"BROADBAND_VALUE_OR_QC_SCHEMA_MISSING","file":path.name}
        epochs,vals,good=series; idx=np.flatnonzero(good&(epochs>=start-1e-6)&(epochs<=end+1e-6))
        if idx.size: idx=idx[solar_elevation_deg(epochs[idx])>=10.0-1e-9]
        return {"ok":True,"epochs":epochs[idx],"values":vals[idx],"rows":idx,"file":path.name,"sha256":sha256_file(path),"size_bytes":path.stat().st_size}


def broadband_corrob_gnd_sky(gnd_paths: Sequence[Path], sky_paths: Sequence[Path], start: float, end: float) -> dict[str,Any]:
    ups=[_broadband_file(p,"up_short_hemisp",start,end) for p in sorted(gnd_paths,key=lambda x:x.name)]
    dns=[_broadband_file(p,"down_short_hemisp",start,end) for p in sorted(sky_paths,key=lambda x:x.name)]
    ue=[];uv=[];ur=[];de=[];dv=[];dr=[];sources=[];offset=0
    for x in ups:
        if not x.get("ok"): continue
        for e,v,r in zip(x["epochs"],x["values"],x["rows"]): ue.append(float(e));uv.append(float(v));ur.append(offset+int(r))
        sources.append({k:x[k] for k in ("file","sha256","size_bytes")}); offset+=len(x["epochs"])+1
    offset=0
    for x in dns:
        if not x.get("ok"): continue
        for e,v,r in zip(x["epochs"],x["values"],x["rows"]): de.append(float(e));dv.append(float(v));dr.append(offset+int(r))
        sources.append({k:x[k] for k in ("file","sha256","size_bytes")}); offset+=len(x["epochs"])+1
    valid=[]
    for a,b,delta in deterministic_pairs(ue,de,ur,dr):
        u=float(uv[a]); d=float(dv[b])
        if np.isfinite(u) and np.isfinite(d) and u>=0 and d>0:
            q=u/d
            if np.isfinite(q) and 0<=q<=1: valid.append((q,delta))
    return {"pass":bool(valid),"method":"GNDRAD_PLUS_SKYRAD","valid_pair_count":len(valid),"example_ratio":float(valid[0][0]) if valid else None,"sources":sources,"reason":"PASS" if valid else "NO_QC_GOOD_PHYSICAL_BROADBAND_PAIR"}


def broadband_corrob_sebs(sebs_paths: Sequence[Path], start: float, end: float) -> dict[str,Any]:
    netCDF4=_nc4(); valid=[]; sources=[]
    for path in sorted(sebs_paths,key=lambda x:x.name):
        with netCDF4.Dataset(path,"r") as ds:
            up=_qc_good_series(ds,"up_short_hemisp"); dn=_qc_good_series(ds,"down_short_hemisp")
            if up is None or dn is None: continue
            ue,uv,ug=up; de,dv,dg=dn; ui=np.flatnonzero(ug&(ue>=start-1e-6)&(ue<=end+1e-6)); di=np.flatnonzero(dg&(de>=start-1e-6)&(de<=end+1e-6))
            if ui.size: ui=ui[solar_elevation_deg(ue[ui])>=10.0-1e-9]
            if di.size: di=di[solar_elevation_deg(de[di])>=10.0-1e-9]
            for a,b,delta in deterministic_pairs(ue[ui],de[di],ui,di):
                u=float(uv[ui[a]]); d=float(dv[di[b]])
                if np.isfinite(u) and np.isfinite(d) and u>=0 and d>0:
                    q=u/d
                    if np.isfinite(q) and 0<=q<=1: valid.append((q,delta,path.name))
            sources.append({"file":path.name,"sha256":sha256_file(path),"size_bytes":path.stat().st_size})
    return {"pass":bool(valid),"method":"SEBS","valid_pair_count":len(valid),"example_ratio":float(valid[0][0]) if valid else None,"sources":sources,"reason":"PASS" if valid else "NO_QC_GOOD_PHYSICAL_BROADBAND_PAIR"}


def evaluate_surface_gate(mfr_paths: Sequence[Path],mfrsr_paths: Sequence[Path],gnd_paths: Sequence[Path],sky_paths: Sequence[Path],sebs_paths: Sequence[Path],start_epoch: float,end_epoch: float) -> dict[str,Any]:
    spectral=evaluate_spectral_surface(collect_narrowband(mfr_paths,"mfr",start_epoch,end_epoch),collect_narrowband(mfrsr_paths,"mfrsr",start_epoch,end_epoch))
    gsky=broadband_corrob_gnd_sky(gnd_paths,sky_paths,start_epoch,end_epoch) if gnd_paths and sky_paths else {"pass":False,"method":"GNDRAD_PLUS_SKYRAD","reason":"FILES_MISSING"}
    sebs=broadband_corrob_sebs(sebs_paths,start_epoch,end_epoch) if sebs_paths else {"pass":False,"method":"SEBS","reason":"FILES_MISSING"}
    corroboration=gsky if gsky.get("pass") else sebs
    disposition="SURFACE_EVIDENCE_INSUFFICIENT" if not spectral.get("pass") else ("SURFACE_CORROBORATION_INSUFFICIENT" if not corroboration.get("pass") else "PASS_SURFACE_RETRIEVED_WITH_BROADBAND_CORROBORATION")
    return {"schema":1,"control_comments":list(CONTROL_COMMENTS),"pass":disposition.startswith("PASS_"),"disposition":disposition,"spectral":spectral,
            "broadband_gnd_sky":gsky,"broadband_sebs":sebs,"selected_corroboration_method":corroboration.get("method"),
            "spectral_completion_label":"INTERPOLATED_BETWEEN_RETRIEVED_CENTERS__ASSUMED_NEAREST_OUTSIDE_SPAN_SENSITIVITY",
            "brdf_label":"ASSUMED_LAMBERTIAN_SENSITIVITY","sws_values_opened":False,"stage_b_authorized":False}
