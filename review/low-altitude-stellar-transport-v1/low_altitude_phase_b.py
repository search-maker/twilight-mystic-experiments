#!/usr/bin/env python3
"""Solver-free Phase-B ledger, seam and lower-runtime contract.

No subprocess, uvspec, libRadtran or protected-result opening path exists here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

STATE_ID = "LOWALT-STELLAR-STATE-0001"
BASE_MAIN = "9ef3b3e000d79e1bcca8ada6c5ab76ea4e492cb8"
PHASE_B_FREEZE_COMMENT = 5467228174
PHASE_A_RESULT_COMMENT = 5467224023
V32_SOURCE_COMMIT = "279ba344ab0e868df1319c01291418ec8786d261"
V32_SOURCE_PATH = "generated/level-b-stellar-v32/stellar-transport-v32-zenith-lut.json"
V32_RUNTIME_SHA256 = "0b96bd5868dc0c72d5cd77b504098d35086feaf573d92556c4f8311a163e3ce2"

WAVELENGTH_NM = tuple(range(380, 781))
TRAINING_ALTITUDE_DEG = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5)
SEAM_ALTITUDE_DEG = 5.0
ELEVATION_M = (0.0, 500.0, 1250.0, 2000.0, 2500.0)
AOD550 = (0.05, 0.10, 0.20, 0.30, 0.40)
PROTECTED_ALTITUDE_DEG = (0.34375, 0.59375, 0.84375, 1.1875, 1.6875, 2.1875, 2.6875, 3.1875, 3.6875, 4.1875, 4.6875)
PROTECTED_ELEVATION_M = (187.5, 781.25, 1531.25, 2187.5)
PROTECTED_AOD550 = (0.06875, 0.1375, 0.2375, 0.3375)
PICKLES_LIBRARY_NUMBERS = (1, 26, 45)
EXPECTED_TRAINING_CASES = 275
EXPECTED_SEAM_CASES = 25
EXPECTED_PROTECTED_CASES = 176
EXPECTED_PROTECTED_COMPARISONS = 528
HISTORICAL_PROTECTED_MIN_TARGET_ALTITUDE_DEG = 5.0
MAX_ABS_DELTA_AV_MAG = 0.025
RMS_DELTA_AV_MAG = 0.010


class PhaseBRefusal(RuntimeError):
    pass


def _finite(name: str, value: Any) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise PhaseBRefusal(f"{name} must be finite")
    return x


def _case_id(prefix: str, h: float, e: float, a: float) -> str:
    return f"{prefix}_h{h:.5f}_e{e:.2f}_a{a:.5f}"


def build_training_cases() -> list[dict[str, Any]]:
    rows=[]
    for h in TRAINING_ALTITUDE_DEG:
        for e in ELEVATION_M:
            for a in AOD550:
                rows.append({"caseId":_case_id("train",h,e,a),"targetGeometricAltitudeDeg":h,"sourceZenithAngleDeg":90.0-h,"observerElevationM":e,"aod550":a})
    if len(rows)!=EXPECTED_TRAINING_CASES or len({r['caseId'] for r in rows})!=len(rows):
        raise PhaseBRefusal("training case accounting drift")
    return rows


def build_protected_cases() -> list[dict[str, Any]]:
    rows=[]
    for h in PROTECTED_ALTITUDE_DEG:
        for e in PROTECTED_ELEVATION_M:
            for a in PROTECTED_AOD550:
                rows.append({"caseId":_case_id("protected",h,e,a),"targetGeometricAltitudeDeg":h,"sourceZenithAngleDeg":90.0-h,"observerElevationM":e,"aod550":a})
    if len(rows)!=EXPECTED_PROTECTED_CASES or len({r['caseId'] for r in rows})!=len(rows):
        raise PhaseBRefusal("protected case accounting drift")
    return rows


def prove_disjointness() -> dict[str, Any]:
    train={(r['targetGeometricAltitudeDeg'],r['observerElevationM'],r['aod550']) for r in build_training_cases()}
    protected={(r['targetGeometricAltitudeDeg'],r['observerElevationM'],r['aod550']) for r in build_protected_cases()}
    collisions=train & protected
    if collisions:
        raise PhaseBRefusal(f"fresh training/protected collision: {sorted(collisions)!r}")
    if not all(h < HISTORICAL_PROTECTED_MIN_TARGET_ALTITUDE_DEG for h,_,_ in protected):
        raise PhaseBRefusal("new protected target altitude overlaps historical protected altitude domain")
    return {
        "freshTrainingProtectedCollisionCount":0,
        "historicalProtectedTupleCollisionCountByAltitudeProof":0,
        "historicalProtectedMinTargetAltitudeDeg":HISTORICAL_PROTECTED_MIN_TARGET_ALTITUDE_DEG,
        "newProtectedMaxTargetAltitudeDeg":max(PROTECTED_ALTITUDE_DEG),
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_v32_runtime(path: Path, *, require_authoritative_sha: bool=True) -> dict[str, Any]:
    raw=Path(path).read_bytes()
    actual=sha256_bytes(raw)
    if require_authoritative_sha and actual != V32_RUNTIME_SHA256:
        raise PhaseBRefusal(f"v3.2 runtime SHA drift: {actual}")
    data=json.loads(raw)
    axes=data.get('axes') or {}
    if list(axes.get('observerElevationM') or []) != list(ELEVATION_M):
        raise PhaseBRefusal("v3.2 elevation axis drift")
    if list(axes.get('aod550') or []) != list(AOD550):
        raise PhaseBRefusal("v3.2 AOD axis drift")
    alt=list(axes.get('targetAltitudeDeg') or [])
    if not alt or float(alt[0]) != SEAM_ALTITUDE_DEG:
        raise PhaseBRefusal("v3.2 exact 5-degree seam missing")
    if list(data.get('wavelengthNm') or []) != list(WAVELENGTH_NM):
        raise PhaseBRefusal("v3.2 wavelength grid drift")
    tau=data.get('directOpticalDepth')
    expected=len(alt)*len(ELEVATION_M)*len(AOD550)
    if not isinstance(tau,list) or len(tau)!=expected:
        raise PhaseBRefusal("v3.2 tau row count drift")
    if any(not isinstance(row,list) or len(row)!=len(WAVELENGTH_NM) for row in tau):
        raise PhaseBRefusal("v3.2 spectral row shape drift")
    if any(not math.isfinite(float(v)) or float(v)<0 for row in tau for v in row):
        raise PhaseBRefusal("v3.2 nonfinite/negative tau")
    return data


def extract_exact_5deg_seam(runtime: dict[str, Any]) -> dict[str, Any]:
    axes=runtime['axes']; alt=list(map(float,axes['targetAltitudeDeg']))
    ia=alt.index(SEAM_ALTITUDE_DEG)
    ne=len(ELEVATION_M); na=len(AOD550)
    rows=[]
    for ie,e in enumerate(ELEVATION_M):
        for ja,a in enumerate(AOD550):
            flat=((ia*ne)+ie)*na+ja
            spectrum=[float(v) for v in runtime['directOpticalDepth'][flat]]
            rows.append({"targetGeometricAltitudeDeg":5.0,"observerElevationM":e,"aod550":a,"directOpticalDepth":spectrum})
    if len(rows)!=EXPECTED_SEAM_CASES:
        raise PhaseBRefusal("5-degree seam count drift")
    canonical=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return {"rows":rows,"seamCanonicalSha256":sha256_bytes(canonical),"sourceRuntimeSha256":V32_RUNTIME_SHA256}


def route_provider(target_geometric_altitude_deg: float) -> str:
    h=_finite("targetGeometricAltitudeDeg",target_geometric_altitude_deg)
    if h < TRAINING_ALTITUDE_DEG[0] or h > 90.0:
        raise PhaseBRefusal("STELLAR_SPECTRAL_RUNTIME_OOD")
    if h >= SEAM_ALTITUDE_DEG:
        return "legacy_v32"
    return "lowalt_state_0001"


def _bracket(axis: tuple[float,...], value: float) -> tuple[int,int,float]:
    if value < axis[0] or value > axis[-1]:
        raise PhaseBRefusal("STELLAR_SPECTRAL_RUNTIME_OOD")
    for i,x in enumerate(axis):
        if value == x: return i,i,0.0
        if i+1<len(axis) and x < value < axis[i+1]:
            return i,i+1,(value-x)/(axis[i+1]-x)
    return len(axis)-1,len(axis)-1,0.0


def interpolate_lower_tau(asset: dict[str,Any], *, target_geometric_altitude_deg: float, observer_elevation_m: float, aod550: float) -> list[float]:
    h=_finite("targetGeometricAltitudeDeg",target_geometric_altitude_deg)
    e=_finite("observerElevationM",observer_elevation_m); a=_finite("aod550",aod550)
    if route_provider(h) != "lowalt_state_0001":
        raise PhaseBRefusal("lower interpolator may only serve 0.25 <= h < 5")
    haxis=tuple(float(x) for x in asset['axes']['targetAltitudeDeg'])
    eaxis=tuple(float(x) for x in asset['axes']['observerElevationM'])
    aaxis=tuple(float(x) for x in asset['axes']['aod550'])
    if haxis != TRAINING_ALTITUDE_DEG + (SEAM_ALTITUDE_DEG,) or eaxis != ELEVATION_M or aaxis != AOD550:
        raise PhaseBRefusal("lower asset axis drift")
    rows=asset['directOpticalDepth']; expected=len(haxis)*len(eaxis)*len(aaxis)
    if len(rows)!=expected:
        raise PhaseBRefusal("lower asset row count drift")
    ih0,ih1,th=_bracket(haxis,h); ie0,ie1,te=_bracket(eaxis,e); ia0,ia1,ta=_bracket(aaxis,a)
    def row(ih,ie,ia): return rows[((ih*len(eaxis))+ie)*len(aaxis)+ia]
    out=[]
    for iw in range(len(WAVELENGTH_NM)):
        value=0.0
        for ih,w_h in ((ih0,1-th),(ih1,th)) if ih0!=ih1 else ((ih0,1.0),):
            for ie,w_e in ((ie0,1-te),(ie1,te)) if ie0!=ie1 else ((ie0,1.0),):
                for ia,w_a in ((ia0,1-ta),(ia1,ta)) if ia0!=ia1 else ((ia0,1.0),):
                    tau=_finite("directOpticalDepth",row(ih,ie,ia)[iw])
                    if tau < 0: raise PhaseBRefusal("negative direct optical depth")
                    value += w_h*w_e*w_a*tau
        t=math.exp(-value)
        if not math.isfinite(t) or not 0.0 < t <= 1.0:
            raise PhaseBRefusal("STELLAR_SPECTRAL_RUNTIME_NUMERIC_UNRESOLVED")
        out.append(value)
    return out


def ledger() -> dict[str,Any]:
    disjoint=prove_disjointness()
    payload={
        "schemaVersion":1,"stateId":STATE_ID,"baseMain":BASE_MAIN,
        "phaseBFreezeIssue60Comment":PHASE_B_FREEZE_COMMENT,
        "scientificExecutionAuthorized":False,"protectedResultsOpened":False,
        "representation":{"altitudeCoordinate":"topocentric-vacuum-geometric-deg","interpolatedQuantity":"direct-optical-depth","altitudeInterpolation":"linear","cscExtrapolationBelow5Deg":False,"refractionAppliedInRadiativeTransfer":False},
        "authoritativeV32Seam":{"sourceCommit":V32_SOURCE_COMMIT,"sourcePath":V32_SOURCE_PATH,"runtimeSha256":V32_RUNTIME_SHA256,"exact5AndAboveProvider":"legacy_v32"},
        "counts":{"freshTrainingSpectra":EXPECTED_TRAINING_CASES,"inheritedSeamSpectra":EXPECTED_SEAM_CASES,"protectedSpectra":EXPECTED_PROTECTED_CASES,"protectedJohnsonVComparisons":EXPECTED_PROTECTED_COMPARISONS},
        "trainingCases":build_training_cases(),"protectedCases":build_protected_cases(),"disjointness":disjoint,
        "acceptance":{"maxAbsDeltaAvMag":MAX_ABS_DELTA_AV_MAG,"rmsDeltaAvMag":RMS_DELTA_AV_MAG,"perAltitudeIntervalRequired":True,"postResultRelaxationAllowed":False},
        "failureSemantics":{"zeroTransmission":"NUMERICALLY_UNRESOLVED","epsilonSubstitutionAllowed":False,"sameIdentityRetryAllowed":False,"githubRerunAllowed":False},
    }
    raw=json.dumps(payload,sort_keys=True,separators=(',',':')).encode(); payload['ledgerSha256']=sha256_bytes(raw)
    return payload


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--emit-ledger',action='store_true'); args=p.parse_args()
    if not args.emit_ledger: p.error('review-only CLI requires --emit-ledger; no solver execution action exists')
    print(json.dumps(ledger(),indent=2,sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
