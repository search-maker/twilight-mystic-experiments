#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np

STAGE = "koomen-support-envelope-v1"
EXECUTION_KEY = "koomen-support-envelope-v1:scientific:50"
ROWS = list(range(18, 28))
PAIR_BASES = [1545000000, 1546000000, 1547000000, 1548000000]
PHOTONS = 200000
RINGS = [0.15, 0.30, 0.45, 0.60, 0.75]
AZIMUTHS = [22.5 * i for i in range(16)]
CAMS_PROFILE_SHA = "6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359"
CIE_WL = np.arange(380.0, 781.0, 10.0)
V_PHOT = np.array([
    0.00004, 0.00012, 0.0004, 0.0012, 0.0040, 0.0116, 0.023, 0.038,
    0.060, 0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.710, 0.862,
    0.954, 0.99495, 0.995, 0.952, 0.870, 0.757, 0.631, 0.503, 0.381,
    0.265, 0.175, 0.107, 0.061, 0.032, 0.017, 0.00821, 0.004102,
    0.002091, 0.001047, 0.00052, 0.000249, 0.00012, 0.00006, 0.00003,
    0.000015,
], dtype=float)
KM_PHOTOPIC = 683.002


class Failure(RuntimeError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Failure(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_manifest(path: Path):
    m = json.loads(path.read_text())
    if m.get("stageId") != STAGE or m.get("executionKey") != EXECUTION_KEY:
        raise Failure("wrong manifest identity")
    if m.get("frozenRows") != ROWS:
        raise Failure("row universe changed")
    if m["directionGrid"]["ringRadiiDeg"] != RINGS or m["directionGrid"]["azimuthsDeg"] != AZIMUTHS:
        raise Failure("direction grid changed")
    if m["directionGrid"]["directionCount"] != 81:
        raise Failure("direction count changed")
    mm = m["mystic"]
    if mm["photonsPerDirectionPerCase"] != PHOTONS or mm["replicateSeedBases"] != PAIR_BASES:
        raise Failure("MYSTIC budget/seed contract changed")
    if m["profileCase"]["profileSha256"] != CAMS_PROFILE_SHA:
        raise Failure("profile provenance changed")
    if not all(m["analysis"][k] is False for k in ("fitTaylor", "fitAcceptanceFunction", "fitFov", "fitOffset", "fitAod", "fitProfile", "fitAnyParameter")):
        raise Failure("fitting prohibition changed")
    return m


def direction_grid():
    out = [{"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "ring": "center"}]
    idx = 0
    for radius in RINGS:
        for az in AZIMUTHS:
            idx += 1
            out.append({"directionIndex": idx, "thetaDeg": radius, "relativeAzimuthDeg": az, "ring": f"r{radius:.2f}"})
    if len(out) != 81 or out[-1]["directionIndex"] != 80:
        raise Failure("internal direction-grid construction changed")
    return out


def baseline_text(baseline_base, data_dir: Path, atmosphere: Path, case_dir: Path, obs, ray, aod, seed):
    return baseline_base.render(data_dir, atmosphere, case_dir, obs, ray, aod, PHOTONS, seed)


def photopic_integral(wl: np.ndarray, radiance: np.ndarray) -> float:
    response = np.interp(wl, CIE_WL, V_PHOT, left=0.0, right=0.0)
    q = KM_PHOTOPIC * float(np.trapezoid(radiance * response, wl))
    if not q > 0 or not math.isfinite(q):
        raise Failure(f"invalid CIE photopic integral {q}")
    return q


def execute_direction(baseline_base, uvspec: Path, text: str, case_dir: Path, theta: float, tables):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "input-resolved.txt").write_text(text)
    t0 = time.monotonic()
    syntax_s = baseline_base.run_process(uvspec, text, case_dir, syntax=True)
    solver_s = baseline_base.run_process(uvspec, text, case_dir, syntax=False)
    wall_s = time.monotonic() - t0
    rad = case_dir / "mc.rad.spc"
    std = case_dir / "mc.rad.std.spc"
    if not rad.is_file() or not std.is_file():
        raise Failure(f"missing MYSTIC spectra in {case_dir}")
    wl, radiance = baseline_base.parse_spectrum(rad)
    q_cie = photopic_integral(wl, radiance)
    q_sqm, q_sqm_std, n, w0, w1 = baseline_base.integrate_ray(rad, std, theta, tables)
    if not q_sqm > 0 or not math.isfinite(q_sqm):
        raise Failure(f"invalid SQM integral {q_sqm}")
    rec = {
        "ciePhotopicQ": q_cie,
        "sqmConditionalQ": q_sqm,
        "sqmStdConservativeNotUsedAsBetweenSeedEstimator": q_sqm_std,
        "syntaxSeconds": syntax_s,
        "solverSeconds": solver_s,
        "wallSeconds": wall_s,
        "spectrumRows": n,
        "wavelengthStartNm": w0,
        "wavelengthEndNm": w1,
        "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
        "radianceSha256": sha(rad),
        "stdSha256": sha(std),
    }
    shutil.rmtree(case_dir, ignore_errors=True)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--baseline-runner", type=Path, required=True)
    ap.add_argument("--profile-runner", type=Path, required=True)
    ap.add_argument("--observations", type=Path, required=True)
    ap.add_argument("--response", type=Path, required=True)
    ap.add_argument("--cams-profile", type=Path, required=True)
    ap.add_argument("--uvspec", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()

    load_manifest(a.manifest)
    if a.row not in ROWS:
        raise Failure("row outside frozen universe")
    if not 1 <= a.replicate <= len(PAIR_BASES):
        raise Failure("replicate outside frozen universe")

    baseline_base = load_module(a.baseline_runner, "taylor_baseline_v1")
    profile_base = load_module(a.profile_runner, "taylor_profile_v1")
    obs = baseline_base.load_observation(a.observations, a.row)
    tables = baseline_base.load_response(a.response)
    profiles, profile_sanity = profile_base.load_cams_profile(a.cams_profile)

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    data = a.data_dir.resolve()
    atmosphere = (data / "atmmod/afglus.dat").resolve()
    uvspec = a.uvspec.resolve()
    tau_path = out / "cams-site-grid-tau.dat"
    t = profile_base.parse_utc(obs["utc"])
    tau_meta = profile_base.write_tau_profile(baseline_base, atmosphere, profiles, t, tau_path)

    aod = float(obs["aod550_primary_frozen"])
    seed = PAIR_BASES[a.replicate - 1] + a.row * 1000 + 950
    directions = direction_grid()
    records = {"baseline": [], "profile": []}

    for d in directions:
        ray = {"thetaDeg": d["thetaDeg"], "relativeAzimuthDeg": d["relativeAzimuthDeg"]}
        bdir = out / "work" / "baseline" / f"dir-{d['directionIndex']:02d}"
        pdir = out / "work" / "profile" / f"dir-{d['directionIndex']:02d}"
        btext = baseline_text(baseline_base, data, atmosphere, bdir, obs, ray, aod, seed)
        ptext = profile_base.render_profile(baseline_base, data, atmosphere, pdir, obs, ray, aod, seed, tau_path)
        br = execute_direction(baseline_base, uvspec, btext, bdir, d["thetaDeg"], tables)
        pr = execute_direction(baseline_base, uvspec, ptext, pdir, d["thetaDeg"], tables)
        common = dict(d)
        records["baseline"].append({**common, **br})
        records["profile"].append({**common, **pr})

    result = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "status": "COMPLETED",
        "row": a.row,
        "replicate": a.replicate,
        "seedBase": PAIR_BASES[a.replicate - 1],
        "intentionalSharedSeedAcrossDirectionsAndCases": seed,
        "utc": obs["utc"],
        "comparisonRole": obs["comparison_role"],
        "sunAltGeometricDeg": float(obs["sun_alt_geometric_deg"]),
        "aod550FrozenIdenticalBetweenCases": aod,
        "surfacePressureHpaFrozenIdenticalBetweenCases": float(obs["surface_pressure_hpa"]),
        "photonsPerDirectionPerCase": PHOTONS,
        "directionCount": len(directions),
        "historicalSupportRadiusDeg": 0.75,
        "spectralDiagnostics": {
            "ciePhotopic": "standard V(lambda) conditional diagnostic; not exact historical filter response",
            "sqmConditional": "original SQM response diagnostic only; not Koomen response"
        },
        "profileSanity": profile_sanity,
        "profileTauMeta": tau_meta,
        "directions": records,
        "scientificExecution": True,
        "exactKoomenOperatorReconstructed": False,
        "continuousSupportExtremaClaimed": False,
        "successDoesNotAuthorizeProduction": True
    }
    (out / "pair-result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "row", "replicate", "sunAltGeometricDeg", "directionCount")}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "stageId": STAGE, "error": str(exc)}), file=sys.stderr)
        raise
