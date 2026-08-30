#!/usr/bin/env python3
"""Deep-twilight independent-renderer capability gates v1 (ZERO-DISPATCH).

Scope and frozen semantics
--------------------------
This module is an evaluator only. It does not execute MYSTIC, Eradiate, uvspec,
or any renderer; allocates no seed/ordinal; and contains no historical exhausted
training radiances or Korkin benchmark radiances.

Gate P -- optical/property/profile parity
* Exact wavelength support after unit-normalized export; no spectral nearest-neighbour remap.
* Extinction and SSA preserved to representation tolerance.
* Every original libRadtran phase-matrix angular node survives the Eradiate
  union-grid conversion with the same value. Inserted union-grid nodes are not
  new physical data and are therefore not used as source parity targets.
* Explicit p11 Legendre moments are preserved.
* The full altitude-dependent aerosol extinction profile, sampled on a
  separately frozen common altitude grid, is compared pointwise and by column
  AOD. Same AOD550 alone never passes.
* Hidden nearest-neighbour humidity/effective-radius selection and conversion-
  time phase renormalization fail closed.

Gate K -- shallow true-spherical sanity
Korkin et al. (2022), JQSRT 287, 108194, DOI 10.1016/j.jqsrt.2022.108194:
multiple-scattering Rayleigh, uniform layer, dark surface, optical thickness
0.25, cos(SZA)=0.1 (SZA about 84.26 deg), Stokes I only. Frozen view subset is
RAz {0,90,180} deg x cos(VZA) {1.0,0.5,0.2}, exactly nine points.

At every point the fresh Eradiate fixed-batch estimate must first establish
RSEM <= 0.1%. Only then may it be compared to the published MYSTIC/MCSSA
midpoint, with frozen pointwise tolerance <= 0.4%. The 0.4% ceiling is a
conservative uncertainty-derived triangle budget: up to 0.1% published
reference numerical/MC uncertainty plus 3 x 0.1% fresh RSEM. Failure to
establish fresh precision is CAPABILITY_UNRESOLVED, not physical disagreement.
No result-dependent extra batches are allowed.

Deep boundary
-------------
The already-frozen synthetic deep matrix 11.5/12.5/14.5/17.0 deg remains
unopened. Gate K is not twilight validation, aerosol validation, or rare-event
validation. No deep scientific identity should be allocated until Gate P and
Gate K both pass and a fresh Issue #60 / Actions / quiescence check permits a
bounded pilot. Ordinary ALIS 500/550/600, VROOM/reference-vroom-1nm, standard
escape/local estimate, and mere photon-count extension do not qualify as a
materially new rare-event method.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

PARITY_TOLERANCES = {
    "wavelength_abs_nm": 1.0e-10,
    "scalar_rtol": 5.0e-12,
    "scalar_atol": 1.0e-14,
    "phase_rtol": 2.0e-10,
    "phase_atol": 2.0e-12,
    "pmom_rtol": 5.0e-12,
    "pmom_atol": 1.0e-14,
    "profile_rtol": 1.0e-8,
    "profile_atol_per_km": 1.0e-12,
    "column_aod_rtol": 1.0e-8,
    "column_aod_atol": 1.0e-12,
}
FROZEN_KORKIN_KEYS = {
    (0.0, 1.0), (0.0, 0.5), (0.0, 0.2),
    (90.0, 1.0), (90.0, 0.5), (90.0, 0.2),
    (180.0, 1.0), (180.0, 0.5), (180.0, 0.2),
}
MAX_FRESH_RSEM = 0.001
MAX_REFERENCE_MIDPOINT_RELDEV = 0.004


def _close(a: float, b: float, rtol: float, atol: float) -> bool:
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


def _max_rel(a: Iterable[float], b: Iterable[float], floor: float = 1e-300) -> float:
    return max((abs(x-y)/max(abs(x),abs(y),floor) for x,y in zip(a,b)), default=0.0)


def _trapz(z: list[float], y: list[float]) -> float:
    if len(z) != len(y) or len(z) < 2:
        raise ValueError("profile arrays must have matching length >= 2")
    return sum(0.5*(y[i]+y[i+1])*(z[i+1]-z[i]) for i in range(len(z)-1))


def _nearest_index(values: list[float], target: float, tol: float) -> int | None:
    if not values: return None
    i=min(range(len(values)), key=lambda k: abs(values[k]-target))
    return i if abs(values[i]-target) <= tol else None


def evaluate_parity(source: dict[str, Any], converted: dict[str, Any], tolerances: dict[str,float] | None=None) -> dict[str,Any]:
    t=dict(PARITY_TOLERANCES)
    if tolerances:
        unknown=set(tolerances)-set(t)
        if unknown: raise ValueError(f"unknown tolerance keys: {sorted(unknown)}")
        t.update(tolerances)
    failures=[]; metrics={}
    sw=list(map(float,source["wavelength_nm"])); cw=list(map(float,converted["wavelength_nm"]))
    if len(sw)!=len(cw): failures.append(f"wavelength length mismatch source={len(sw)} converted={len(cw)}")
    elif any(abs(a-b)>t["wavelength_abs_nm"] for a,b in zip(sw,cw)): failures.append("wavelength support changed")
    metrics["wavelengthMaxAbsNm"]=max((abs(a-b) for a,b in zip(sw,cw)),default=math.inf)
    for name in ("extinction_per_km","ssa"):
        a=list(map(float,source[name])); b=list(map(float,converted[name]))
        if len(a)!=len(b) or len(a)!=len(sw): failures.append(f"{name} length mismatch"); continue
        bad=[i for i,(x,y) in enumerate(zip(a,b)) if not _close(x,y,t["scalar_rtol"],t["scalar_atol"])]
        if bad: failures.append(f"{name} changed at {len(bad)} wavelength(s), first={bad[0]}")
        metrics[f"{name}MaxRel"]=_max_rel(a,b)
    phase_checked=phase_missing=phase_bad=0
    if len(source["phase"])!=len(converted["phase"]): failures.append("phase wavelength dimension mismatch")
    else:
        for iw,(sp,cp) in enumerate(zip(source["phase"],converted["phase"])):
            mu_union=list(map(float,cp["mu"])); comps=cp["components"]
            for cname,scomp in sp["components"].items():
                if cname not in comps: failures.append(f"phase component {cname} missing at wavelength index {iw}"); continue
                cvals=list(map(float,comps[cname]))
                for mu,sval in zip(map(float,scomp["mu"]),map(float,scomp["value"])):
                    phase_checked+=1; idx=_nearest_index(mu_union,mu,5e-13)
                    if idx is None: phase_missing+=1; continue
                    if not _close(sval,cvals[idx],t["phase_rtol"],t["phase_atol"]): phase_bad+=1
    if phase_missing: failures.append(f"{phase_missing}/{phase_checked} original phase angular nodes missing")
    if phase_bad: failures.append(f"{phase_bad}/{phase_checked} original phase values changed")
    metrics.update({"phaseOriginalNodesChecked":phase_checked,"phaseMissing":phase_missing,"phaseValueFailures":phase_bad})
    spm=source.get("pmom_p11",[]); cpm=converted.get("pmom_p11",[]); compared=bad=0
    if len(spm)!=len(cpm): failures.append("pmom wavelength dimension mismatch")
    else:
        for iw,(sa,ca) in enumerate(zip(spm,cpm)):
            if len(sa)!=len(ca): failures.append(f"pmom length mismatch at wavelength index {iw}"); continue
            for x,y in zip(map(float,sa),map(float,ca)):
                compared+=1
                if not _close(x,y,t["pmom_rtol"],t["pmom_atol"]): bad+=1
    if bad: failures.append(f"{bad}/{compared} pmom coefficients changed")
    metrics.update({"pmomCoefficientsChecked":compared,"pmomFailures":bad})
    sprof=source["vertical_profile"]; cprof=converted["vertical_profile"]
    z1=list(map(float,sprof["altitude_km"])); z2=list(map(float,cprof["altitude_km"]))
    if len(z1)!=len(z2) or any(abs(a-b)>1e-10 for a,b in zip(z1,z2)): failures.append("vertical altitude grid changed")
    e1=sprof["extinction_per_km_by_wavelength"]; e2=cprof["extinction_per_km_by_wavelength"]
    max_prof_rel=0.0
    if len(e1)!=len(e2) or len(e1)!=len(sw): failures.append("vertical profile wavelength dimension mismatch")
    else:
        for iw,(a,b) in enumerate(zip(e1,e2)):
            a=list(map(float,a)); b=list(map(float,b))
            if len(a)!=len(z1) or len(b)!=len(z2): failures.append(f"vertical profile shape mismatch at wavelength index {iw}"); continue
            max_prof_rel=max(max_prof_rel,_max_rel(a,b))
            bad_idx=[k for k,(x,y) in enumerate(zip(a,b)) if not _close(x,y,t["profile_rtol"],t["profile_atol_per_km"])]
            if bad_idx: failures.append(f"vertical extinction changed at wavelength index {iw}; first altitude index {bad_idx[0]}")
            if len(z1)>=2 and len(z2)>=2:
                if not _close(_trapz(z1,a),_trapz(z2,b),t["column_aod_rtol"],t["column_aod_atol"]): failures.append(f"column AOD changed at wavelength index {iw}")
    metrics["verticalExtinctionMaxRel"]=max_prof_rel
    metadata=converted.get("translation_metadata",{})
    if metadata.get("nearest_neighbor_dimension_selected",False): failures.append("hidden nearest-neighbour humidity/effective-radius selection recorded")
    if metadata.get("phase_normalized_during_conversion",False): failures.append("phase normalization during conversion is not permitted in parity gate")
    return {"schemaVersion":1,"gate":"P","status":"PASS" if not failures else "FAIL_CLOSED","failures":failures,"metrics":metrics,"tolerances":t}


def _key(row:dict[str,str]) -> tuple[float,float]:
    return (float(row["relative_azimuth_deg"]),float(row["mu_view"]))


def evaluate_korkin(reference_csv:Path,batches_csv:Path) -> dict[str,Any]:
    with reference_csv.open(newline="") as f: refs={_key(r):r for r in csv.DictReader(f)}
    with batches_csv.open(newline="") as f:
        batches={}
        for r in csv.DictReader(f): batches.setdefault(_key(r),[]).append(float(r["eradiate_I"]))
    failures=[]; points=[]
    if set(refs)!=FROZEN_KORKIN_KEYS: failures.append("reference key set differs from frozen 9-point subset")
    if set(batches)!=FROZEN_KORKIN_KEYS: failures.append("batch key set differs from frozen 9-point subset")
    for key in sorted(FROZEN_KORKIN_KEYS):
        if key not in refs or key not in batches: continue
        vals=batches[key]
        if len(vals)<2: failures.append(f"{key}: fewer than two fixed independent batches"); continue
        mean=statistics.fmean(vals); sd=statistics.stdev(vals); rsem=math.inf if mean==0 else abs((sd/math.sqrt(len(vals)))/mean)
        m=float(refs[key]["mystic_I"]); c=float(refs[key]["mcssa_I"]); midpoint=(m+c)/2
        reldiff=math.inf if midpoint==0 else abs(mean-midpoint)/abs(midpoint)
        status="PASS"
        if not math.isfinite(rsem) or rsem>MAX_FRESH_RSEM:
            status="CAPABILITY_UNRESOLVED"; failures.append(f"{key}: RSEM {rsem} > {MAX_FRESH_RSEM}")
        elif not math.isfinite(reldiff) or reldiff>MAX_REFERENCE_MIDPOINT_RELDEV:
            status="REFERENCE_DISAGREEMENT"; failures.append(f"{key}: relative midpoint deviation {reldiff} > {MAX_REFERENCE_MIDPOINT_RELDEV}")
        points.append({"relativeAzimuthDeg":key[0],"muView":key[1],"batchCount":len(vals),"mean":mean,"rsem":rsem,"referenceMidpoint":midpoint,"relativeDeviation":reldiff,"status":status})
    return {"schemaVersion":1,"gate":"K","benchmark":"Korkin-2022-JQSRT-287-108194","frozenCase":{"opticalThickness":0.25,"cosSza":0.1,"surface":"dark","scattering":"Rayleigh multiple-scattering uniform layer","observable":"Stokes-I"},"acceptance":{"maxFreshRsem":MAX_FRESH_RSEM,"maxRelativeDeviationFromMysticMcssaMidpoint":MAX_REFERENCE_MIDPOINT_RELDEV},"status":"PASS" if not failures else "FAIL_CLOSED","failures":failures,"points":points}


def _self_test() -> None:
    src={"wavelength_nm":[500.,550.],"extinction_per_km":[.01,.009],"ssa":[.9,.91],"phase":[{"components":{"11":{"mu":[-1.,0.,1.],"value":[.5,1.,1.5]}}},{"components":{"11":{"mu":[-1.,0.,1.],"value":[.6,1.,1.4]}}}],"pmom_p11":[[1.,.1],[1.,.2]],"vertical_profile":{"altitude_km":[0.,1.,2.],"extinction_per_km_by_wavelength":[[.02,.01,0.],[.018,.009,0.]]}}
    conv=json.loads(json.dumps(src)); conv["phase"]=[{"mu":[-1.,0.,1.],"components":{"11":[.5,1.,1.5]}},{"mu":[-1.,0.,1.],"components":{"11":[.6,1.,1.4]}}]; conv["translation_metadata"]={"nearest_neighbor_dimension_selected":False,"phase_normalized_during_conversion":False}
    assert evaluate_parity(src,conv)["status"]=="PASS"
    bad=json.loads(json.dumps(conv)); bad["vertical_profile"]["extinction_per_km_by_wavelength"][0][1]*=1.01; assert evaluate_parity(src,bad)["status"]=="FAIL_CLOSED"
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        r=Path(d)/"ref.csv"; b=Path(d)/"batch.csv"
        with r.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["relative_azimuth_deg","mu_view","mystic_I","mcssa_I"]); w.writeheader()
            for az,mu in sorted(FROZEN_KORKIN_KEYS): w.writerow({"relative_azimuth_deg":az,"mu_view":mu,"mystic_I":1.,"mcssa_I":1.})
        with b.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["relative_azimuth_deg","mu_view","batch_id","eradiate_I"]); w.writeheader()
            for az,mu in sorted(FROZEN_KORKIN_KEYS):
                for i,v in enumerate([.9998,1.0002]): w.writerow({"relative_azimuth_deg":az,"mu_view":mu,"batch_id":i,"eradiate_I":v})
        assert evaluate_korkin(r,b)["status"]=="PASS"
    print("SELF_TEST_PASS")


def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    q=sub.add_parser("parity"); q.add_argument("source_json",type=Path); q.add_argument("converted_json",type=Path); q.add_argument("--output",type=Path)
    q=sub.add_parser("korkin"); q.add_argument("reference_csv",type=Path); q.add_argument("batches_csv",type=Path); q.add_argument("--output",type=Path)
    sub.add_parser("self-test")
    ns=p.parse_args()
    if ns.cmd=="self-test": _self_test(); return 0
    if ns.cmd=="parity": result=evaluate_parity(json.loads(ns.source_json.read_text()),json.loads(ns.converted_json.read_text()))
    else: result=evaluate_korkin(ns.reference_csv,ns.batches_csv)
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if ns.output: ns.output.write_text(text)
    else: print(text,end="")
    return 0 if result["status"]=="PASS" else 2

if __name__=="__main__": raise SystemExit(main())
