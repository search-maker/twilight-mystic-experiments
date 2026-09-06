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

STAGE = "koomen-81grid-simultaneous-map-v1"
EXECUTION_KEY = "koomen-81grid-simultaneous-map-v1:scientific:59"
ISSUE = 877
ROWS = list(range(18, 28))
CASES = ["baseline", "profile"]
BASES = [1631000000, 1632000000, 1633000000, 1634000000, 1635000000, 1636000000]
SEED_OFFSET = 997
PROFILE_SOURCE_PHOTONS = 200_000
PHOTONS_BY_ROW = {
    18: 1_000_000, 19: 1_000_000, 20: 1_000_000,
    21: 2_000_000, 22: 2_000_000, 23: 2_000_000,
    24: 5_000_000, 25: 5_000_000, 26: 5_000_000, 27: 5_000_000,
}
RINGS = [0.15, 0.30, 0.45, 0.60, 0.75]
FULL_AZ = [22.5 * i for i in range(16)]
EXEC_AZ = [22.5 * i for i in range(9)]
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


def full_grid():
    out = [{"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "ring": "center"}]
    idx = 0
    for radius in RINGS:
        for az in FULL_AZ:
            idx += 1
            out.append({"directionIndex": idx, "thetaDeg": radius, "relativeAzimuthDeg": az, "ring": f"r{radius:.2f}"})
    if len(out) != 81 or out[-1]["directionIndex"] != 80:
        raise Failure("full-grid construction changed")
    return out


def executed_grid():
    full = full_grid()
    out = [full[0]]
    for d in full[1:]:
        if d["relativeAzimuthDeg"] <= 180.0:
            out.append(d)
    if len(out) != 46:
        raise Failure(f"expected 46 symmetry-unique directions, got {len(out)}")
    expected = [0] + [i for base in (1,17,33,49,65) for i in range(base, base + 9)]
    if [d["directionIndex"] for d in out] != expected:
        raise Failure("executed original-grid indices changed")
    return out


def mirror_index_map():
    full = full_grid()
    by = {(round(d["thetaDeg"], 8), round(d["relativeAzimuthDeg"], 8)): d["directionIndex"] for d in full}
    mapping = {}
    for d in full:
        if d["directionIndex"] == 0 or d["relativeAzimuthDeg"] <= 180.0:
            mapping[d["directionIndex"]] = d["directionIndex"]
        else:
            maz = 360.0 - d["relativeAzimuthDeg"]
            mapping[d["directionIndex"]] = by[(round(d["thetaDeg"], 8), round(maz, 8))]
    if len(mapping) != 81 or len(set(mapping.values())) != 46:
        raise Failure("mirror map changed")
    return mapping


def load_manifest(path: Path):
    m = json.loads(path.read_text())
    if m.get("stageId") != STAGE or m.get("executionKey") != EXECUTION_KEY or m.get("issue") != ISSUE:
        raise Failure("wrong manifest identity")
    if m.get("rows") != ROWS or m.get("cases") != CASES:
        raise Failure("row/case universe changed")
    fg = m.get("fullGrid", {})
    if fg.get("ringRadiiDeg") != RINGS or fg.get("azimuthsDeg") != FULL_AZ or fg.get("directionCount") != 81:
        raise Failure("full grid changed")
    sym = m.get("modelSymmetryReduction", {})
    if sym.get("executedAzimuthsDegPerRing") != EXEC_AZ or sym.get("executedDirectionCount") != 46 or sym.get("uniqueNonCenterExpectationCount") != 45 or sym.get("mirroredDirectionCount") != 35:
        raise Failure("symmetry reduction changed")
    mm = m.get("mystic", {})
    if mm.get("replicateSeedBases") != BASES or mm.get("derivedSeedOffset") != SEED_OFFSET:
        raise Failure("seed universe changed")
    got = {int(k): int(v) for k, v in mm.get("photonsPerDirectionPerCaseByRow", {}).items()}
    if got != PHOTONS_BY_ROW:
        raise Failure("photon schedule changed")
    if mm.get("maximumSolverCalls") != 5520 or mm.get("maximumConfiguredPhotonHistories") != 16008000000 or mm.get("adaptiveExtensionAuthorized") is not False:
        raise Failure("maximum budget changed")
    if mm.get("method") != "direct ALIS" or mm.get("wavelengthNm") != [380, 780] or float(mm.get("mcSpectralIsNm", -1)) != 550.0 or mm.get("mcVroom") != "on" or mm.get("mcEscapeExplicit") != "on":
        raise Failure("estimator changed")
    if m.get("profileCase", {}).get("profileSha256") != CAMS_PROFILE_SHA:
        raise Failure("profile provenance changed")
    a = m.get("analysis", {})
    if a.get("familySize") != 45 or a.get("df") != 5 or abs(float(a.get("studentTBonferroniCritical")) - 6.712593092914674) > 1e-14:
        raise Failure("analysis family/critical changed")
    for key in ("fitTaylor", "fitAcceptance", "fitFov", "fitSpectralResponse", "fitOffset", "fitAtmosphere", "fitAod", "fitProfile", "fitAnyParameter"):
        if a.get(key) is not False:
            raise Failure(f"fitting prohibition changed: {key}")
    b = m.get("boundaries", {})
    for key in ("TaylorResidualUsed", "historicalAcceptanceInvented", "exactHistoricalSpectralResponseClaimed", "exactHistoricalTemporalResponseClaimed", "continuousSupportExtremaClaimed", "rawSampledExtremaUsedDecisively", "importanceWavelengthRetuned", "quadraticSurrogateRehabilitated", "causalTaylorKoomenFractionClaimed", "productionAuthorized", "levelBAuthorized", "humanVisionChanged"):
        if b.get(key) is not False:
            raise Failure(f"boundary changed: {key}")
    executed_grid(); mirror_index_map()
    return m


def retarget_profile_photons(text: str, photons: int) -> str:
    old = f"mc_photons {PROFILE_SOURCE_PHOTONS}"
    new = f"mc_photons {photons}"
    lines = text.splitlines()
    if lines.count(old) != 1:
        raise Failure(f"expected exactly one profile photon line {old!r}")
    out = [new if line == old else line for line in lines]
    if out.count(new) != 1 or old in out:
        raise Failure("profile photon retarget failed")
    return "\n".join(out) + "\n"


def force_vroom_escape(text: str) -> str:
    lines = text.splitlines()
    if lines.count("mc_vroom off") != 1:
        raise Failure("expected exactly one mc_vroom off")
    if any(line.startswith("mc_escape ") for line in lines):
        raise Failure("unexpected pre-existing explicit mc_escape")
    out = []
    for line in lines:
        if line == "mc_vroom off":
            out.extend(["mc_vroom on", "mc_escape on"])
        else:
            out.append(line)
    if out.count("mc_vroom on") != 1 or out.count("mc_escape on") != 1 or out.count("mc_spectral_is 550.0") != 1 or out.count("wavelength 380 780") != 1:
        raise Failure("frozen ALIS/VROOM/escape mutation failed")
    return "\n".join(out) + "\n"


def photopic_integral(wl: np.ndarray, radiance: np.ndarray) -> float:
    response = np.interp(wl, CIE_WL, V_PHOT, left=0.0, right=0.0)
    q = KM_PHOTOPIC * float(np.trapezoid(radiance * response, wl))
    if not q > 0 or not math.isfinite(q):
        raise Failure(f"invalid CIE photopic integral {q}")
    return q


def exact_anchor550(wl: np.ndarray, radiance: np.ndarray) -> float:
    idx = np.where(np.isclose(wl, 550.0, rtol=0.0, atol=1e-9))[0]
    if len(idx) != 1:
        raise Failure(f"expected exactly one ALIS 550-nm sample, got {len(idx)}")
    q = float(radiance[int(idx[0])])
    if not q > 0 or not math.isfinite(q):
        raise Failure("invalid 550-nm anchor")
    return q


def execute_direction(base, uvspec: Path, text: str, case_dir: Path, theta: float, tables):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "input-resolved.txt").write_text(text)
    started = time.monotonic()
    syntax_s = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_s = base.run_process(uvspec, text, case_dir, syntax=False)
    wall_s = time.monotonic() - started
    rad = case_dir / "mc.rad.spc"
    std = case_dir / "mc.rad.std.spc"
    if not rad.is_file() or not std.is_file():
        raise Failure(f"missing MYSTIC spectra in {case_dir}")
    wl, radiance = base.parse_spectrum(rad)
    q_cie = photopic_integral(wl, radiance)
    q_sqm, q_sqm_std, n, w0, w1 = base.integrate_ray(rad, std, theta, tables)
    if not q_sqm > 0 or not math.isfinite(q_sqm):
        raise Failure(f"invalid SQM conditional integral {q_sqm}")
    rec = {
        "ciePhotopicQ": q_cie,
        "sqmConditionalQ": q_sqm,
        "anchor550Q": exact_anchor550(wl, radiance),
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
    ap.add_argument("--case", choices=CASES, required=True)
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
    if not 1 <= a.replicate <= len(BASES):
        raise Failure("replicate outside frozen universe")

    base = load_module(a.baseline_runner, "taylor_baseline_v1")
    prof = load_module(a.profile_runner, "taylor_profile_v1")
    obs = base.load_observation(a.observations, a.row)
    tables = base.load_response(a.response)
    if sha(a.cams_profile) != CAMS_PROFILE_SHA:
        raise Failure("CAMS profile checksum changed")
    profiles, profile_sanity = prof.load_cams_profile(a.cams_profile)

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    data = a.data_dir.resolve()
    atmosphere = (data / "atmmod/afglus.dat").resolve()
    uvspec = a.uvspec.resolve()
    aod = float(obs["aod550_primary_frozen"])
    photons = PHOTONS_BY_ROW[a.row]
    seed = BASES[a.replicate - 1] + a.row * 1000 + SEED_OFFSET

    tau_meta = None
    tau_path = out / "cams-site-grid-tau.dat"
    if a.case == "profile":
        tau_meta = prof.write_tau_profile(base, atmosphere, profiles, prof.parse_utc(obs["utc"]), tau_path)

    records = []
    for d in executed_grid():
        ray = {"thetaDeg": d["thetaDeg"], "relativeAzimuthDeg": d["relativeAzimuthDeg"]}
        cdir = out / "work" / f"dir-{d['directionIndex']:02d}"
        if a.case == "baseline":
            text = base.render(data, atmosphere, cdir, obs, ray, aod, photons, seed)
        else:
            text = prof.render_profile(base, data, atmosphere, cdir, obs, ray, aod, seed, tau_path)
            text = retarget_profile_photons(text, photons)
        text = force_vroom_escape(text)
        rec = execute_direction(base, uvspec, text, cdir, d["thetaDeg"], tables)
        records.append({**d, **rec})

    result = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "status": "COMPLETED",
        "row": a.row,
        "replicate": a.replicate,
        "case": a.case,
        "seedBase": BASES[a.replicate - 1],
        "derivedSharedSeedAcrossDirectionsAndCases": seed,
        "utc": obs["utc"],
        "comparisonRole": obs["comparison_role"],
        "sunAltGeometricDeg": float(obs["sun_alt_geometric_deg"]),
        "aod550Frozen": aod,
        "surfacePressureHpaFrozen": float(obs["surface_pressure_hpa"]),
        "photonsPerDirectionPerCase": photons,
        "fullDirectionCount": 81,
        "executedDirectionCount": 46,
        "uniqueNonCenterExpectationCount": 45,
        "modelMirrorSymmetry": "expectation(phi)=expectation(360-phi) under frozen horizontally homogeneous spherical-1D model",
        "mirrorIndexMap": mirror_index_map(),
        "method": "direct ALIS; mc_vroom on; mc_escape on; mc_spectral_is 550.0",
        "operators": {"primary": "ciePhotopicQ", "secondary": "sqmConditionalQ"},
        "profileSanity": profile_sanity,
        "profileTauMeta": tau_meta,
        "directions": records,
        "scientificExecution": True,
        "TaylorResidualUsed": False,
        "historicalAcceptanceInvented": False,
        "exactHistoricalSpectralResponseClaimed": False,
        "continuousSupportExtremaClaimed": False,
        "rawSampledExtremaUsedDecisively": False,
        "productionAuthorized": False,
    }
    (out / "map-result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "row", "replicate", "case", "sunAltGeometricDeg", "photonsPerDirectionPerCase", "executedDirectionCount")}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "stageId": STAGE, "error": str(exc)}), file=sys.stderr)
        raise
