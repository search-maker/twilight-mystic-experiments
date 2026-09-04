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

STAGE = "koomen-mono550-cv-sentinel-v1"
EXECUTION_KEY = "koomen-mono550-cv-sentinel-v1:scientific:56"
ROW = 27
BASES = [1601000000, 1602000000, 1603000000, 1604000000, 1605000000, 1606000000]
SEED_OFFSET = 996
PHOTONS = 1_000_000
PROFILE_SOURCE_PHOTONS = 200_000
CAMS_PROFILE_SHA = "6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359"
DIRECTIONS = [
    {"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "label": "center", "role": "center"},
    {"directionIndex": 14, "thetaDeg": 0.375, "relativeAzimuthDeg": 180.0, "label": "mid_180", "role": "target"},
    {"directionIndex": 18, "thetaDeg": 0.75, "relativeAzimuthDeg": 315.0, "label": "edge_315", "role": "target"},
]
CIE_WL = np.arange(380.0, 781.0, 10.0)
V_PHOT = np.array([
    0.00004, 0.00012, 0.0004, 0.0012, 0.0040, 0.0116, 0.023, 0.038, 0.060,
    0.09098, 0.13902, 0.20802, 0.323, 0.503, 0.710, 0.862, 0.954, 0.99495,
    0.995, 0.952, 0.870, 0.757, 0.631, 0.503, 0.381, 0.265, 0.175, 0.107,
    0.061, 0.032, 0.017, 0.00821, 0.004102, 0.002091, 0.001047, 0.00052,
    0.000249, 0.00012, 0.00006, 0.00003, 0.000015,
], float)
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
    if m.get("issue") != 868 or m.get("row") != ROW:
        raise Failure("issue/row changed")
    if m.get("directions") != DIRECTIONS or m.get("cases") != ["baseline", "profile"]:
        raise Failure("geometry/case universe changed")
    if m.get("arms") != ["alis550", "mono550"]:
        raise Failure("arm universe changed")
    if m.get("replicateSeedBases") != BASES or m.get("seedOffset") != SEED_OFFSET:
        raise Failure("seed universe changed")
    if m.get("photonsPerDirectionPerCaseArm") != PHOTONS:
        raise Failure("photon budget changed")
    if m.get("maximumSolverCalls") != 72 or m.get("maximumConfiguredPhotonHistories") != 72_000_000:
        raise Failure("maximum budget changed")
    method = m.get("method", {})
    if method.get("common") != ["mc_spherical 1D", "mc_vroom on", "mc_escape on"]:
        raise Failure("common estimator changed")
    if method.get("alis550") != {"wavelengthNm": [380, 780], "mcSpectralIsNm": 550.0}:
        raise Failure("ALIS arm changed")
    if method.get("mono550") != {"wavelengthNm": [550, 550], "mcSpectralIs": False}:
        raise Failure("mono arm changed")
    if m.get("profileSha256") != CAMS_PROFILE_SHA:
        raise Failure("profile provenance changed")
    a = m.get("analysis", {})
    if a.get("primaryMethodConsistencyToleranceMag") != 0.03 or a.get("precisionTargetSeMag") != 0.03:
        raise Failure("analysis threshold changed")
    if a.get("controlVariateFormula") != "D_CV=(D_CIE-D_A)+D_M":
        raise Failure("control-variate formula changed")
    for key in ("fitTaylor", "fitAcceptance", "fitFov", "fitSpectralResponse", "fitOffset", "fitAtmosphere", "fitAod", "fitProfile", "fitAnyParameter"):
        if a.get(key) is not False:
            raise Failure(f"fitting prohibition changed: {key}")
    b = m.get("boundaries", {})
    for key in ("TaylorResidualUsed", "ordinal54Salvage", "importanceWavelengthRetuned", "historicalAcceptanceInvented", "exactHistoricalSpectralResponseClaimed", "physicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized", "full81DirectionGridAuthorized", "productionAuthorized"):
        if b.get(key) is not False:
            raise Failure(f"boundary changed: {key}")
    return m


def mutate_profile_photons(text: str) -> str:
    old = f"mc_photons {PROFILE_SOURCE_PHOTONS}"
    new = f"mc_photons {PHOTONS}"
    lines = text.splitlines()
    if lines.count(old) != 1:
        raise Failure(f"expected exactly one profile source photon line {old!r}")
    lines = [new if line == old else line for line in lines]
    if lines.count(new) != 1 or old in lines:
        raise Failure("profile photon retarget failed")
    return "\n".join(lines) + "\n"


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
    if out.count("mc_vroom on") != 1 or out.count("mc_escape on") != 1:
        raise Failure("VROOM/escape mutation failed")
    return "\n".join(out) + "\n"


def to_mono550(text: str) -> str:
    lines = text.splitlines()
    if lines.count("wavelength 380 780") != 1:
        raise Failure("expected one 380-780 wavelength line")
    if lines.count("mc_spectral_is 550.0") != 1:
        raise Failure("expected one ALIS 550 importance line")
    if any(line.startswith("wavelength_grid_file ") for line in lines):
        raise Failure("unexpected wavelength_grid_file in frozen source")
    out = []
    for line in lines:
        if line == "wavelength 380 780":
            out.append("wavelength 550 550")
        elif line == "mc_spectral_is 550.0":
            continue
        else:
            out.append(line)
    if out.count("wavelength 550 550") != 1 or any(line.startswith("mc_spectral_is ") for line in out):
        raise Failure("monochromatic mutation failed")
    return "\n".join(out) + "\n"


def common_signature(text: str):
    out = []
    for line in text.splitlines():
        if line.startswith("wavelength ") or line.startswith("mc_spectral_is "):
            continue
        if line.startswith("mc_basename "):
            out.append("mc_basename <OUTPUT>")
        else:
            out.append(line)
    return out


def photopic(wl, radiance) -> float:
    response = np.interp(wl, CIE_WL, V_PHOT, left=0.0, right=0.0)
    q = KM_PHOTOPIC * float(np.trapezoid(radiance * response, wl))
    if not q > 0 or not math.isfinite(q):
        raise Failure("invalid photopic Q")
    return q


def exact_anchor550(wl, radiance) -> float:
    idx = np.where(np.isclose(wl, 550.0, rtol=0.0, atol=1e-9))[0]
    if len(idx) != 1:
        raise Failure(f"expected exactly one ALIS 550-nm sample, got {len(idx)}")
    q = float(radiance[int(idx[0])])
    if not q > 0 or not math.isfinite(q):
        raise Failure("invalid ALIS 550 anchor Q")
    return q


def parse_mono550(path: Path) -> float:
    vals = []
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            w = float(parts[0])
            q = float(parts[-1])
        except ValueError:
            continue
        if abs(w - 550.0) <= 1e-6 and math.isfinite(q):
            vals.append(q)
    if len(vals) != 1:
        raise Failure(f"expected exactly one monochromatic 550 radiance row, got {len(vals)}")
    q = float(vals[0])
    if not q > 0:
        raise Failure("non-positive monochromatic 550 Q")
    return q


def execute_alis(base, uvspec: Path, text: str, case_dir: Path):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "input-resolved.txt").write_text(text)
    started = time.monotonic()
    syntax_seconds = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_seconds = base.run_process(uvspec, text, case_dir, syntax=False)
    wall_seconds = time.monotonic() - started
    rad = case_dir / "mc.rad.spc"
    std = case_dir / "mc.rad.std.spc"
    if not rad.is_file() or not std.is_file():
        raise Failure("missing ALIS spectra")
    wl, radiance = base.parse_spectrum(rad)
    rec = {
        "ciePhotopicQ": photopic(wl, radiance),
        "anchor550Q": exact_anchor550(wl, radiance),
        "syntaxSeconds": syntax_seconds,
        "solverSeconds": solver_seconds,
        "wallSeconds": wall_seconds,
        "spectrumRows": int(len(wl)),
        "wavelengthStartNm": float(wl[0]),
        "wavelengthEndNm": float(wl[-1]),
        "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
        "radianceSha256": sha(rad),
        "stdSha256": sha(std),
    }
    shutil.rmtree(case_dir, ignore_errors=True)
    return rec


def execute_mono(base, uvspec: Path, text: str, case_dir: Path):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "input-resolved.txt").write_text(text)
    started = time.monotonic()
    syntax_seconds = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_seconds = base.run_process(uvspec, text, case_dir, syntax=False)
    wall_seconds = time.monotonic() - started
    rad = case_dir / "mc.rad.spc"
    std = case_dir / "mc.rad.std.spc"
    if not rad.is_file() or not std.is_file():
        raise Failure("missing MONO550 spectra")
    rec = {
        "mono550Q": parse_mono550(rad),
        "syntaxSeconds": syntax_seconds,
        "solverSeconds": solver_seconds,
        "wallSeconds": wall_seconds,
        "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
        "radianceSha256": sha(rad),
        "stdSha256": sha(std),
    }
    shutil.rmtree(case_dir, ignore_errors=True)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicate", type=int, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--baseline-runner", type=Path, required=True)
    ap.add_argument("--profile-runner", type=Path, required=True)
    ap.add_argument("--observations", type=Path, required=True)
    ap.add_argument("--cams-profile", type=Path, required=True)
    ap.add_argument("--uvspec", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()

    load_manifest(a.manifest)
    if not 1 <= a.replicate <= len(BASES):
        raise Failure("replicate outside frozen universe")

    base = load_module(a.baseline_runner, "baseline")
    prof = load_module(a.profile_runner, "profile")
    obs = base.load_observation(a.observations, ROW)
    profiles, sanity = prof.load_cams_profile(a.cams_profile)
    if sha(a.cams_profile) != CAMS_PROFILE_SHA:
        raise Failure("profile SHA changed")

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    data = a.data_dir.resolve()
    atmosphere = (data / "atmmod/afglus.dat").resolve()
    uvspec = a.uvspec.resolve()
    tau_path = out / "cams-site-grid-tau.dat"
    tau_meta = prof.write_tau_profile(base, atmosphere, profiles, prof.parse_utc(obs["utc"]), tau_path)

    aod = float(obs["aod550_primary_frozen"])
    seed = BASES[a.replicate - 1] + ROW * 1000 + SEED_OFFSET
    results = {"alis550": {}, "mono550": {}}

    for case in ("baseline", "profile"):
        results["alis550"][case] = []
        results["mono550"][case] = []
        for direction in DIRECTIONS:
            ray = {"thetaDeg": direction["thetaDeg"], "relativeAzimuthDeg": direction["relativeAzimuthDeg"]}
            alis_dir = out / "work" / "alis550" / case / direction["label"]
            mono_dir = out / "work" / "mono550" / case / direction["label"]

            if case == "baseline":
                alis_text = base.render(data, atmosphere, alis_dir, obs, ray, aod, PHOTONS, seed)
                mono_source = base.render(data, atmosphere, mono_dir, obs, ray, aod, PHOTONS, seed)
            else:
                alis_text = prof.render_profile(base, data, atmosphere, alis_dir, obs, ray, aod, seed, tau_path)
                mono_source = prof.render_profile(base, data, atmosphere, mono_dir, obs, ray, aod, seed, tau_path)
                alis_text = mutate_profile_photons(alis_text)
                mono_source = mutate_profile_photons(mono_source)

            alis_text = force_vroom_escape(alis_text)
            mono_source = force_vroom_escape(mono_source)
            if alis_text.splitlines().count(f"mc_photons {PHOTONS}") != 1 or mono_source.splitlines().count(f"mc_photons {PHOTONS}") != 1:
                raise Failure("photon budget not exact")
            if alis_text.splitlines().count("mc_spectral_is 550.0") != 1:
                raise Failure("ALIS 550 importance center not exact")
            mono_text = to_mono550(mono_source)
            if common_signature(alis_text) != common_signature(mono_text):
                raise Failure("paired arms differ outside frozen spectral execution/output path")

            alis_rec = execute_alis(base, uvspec, alis_text, alis_dir)
            mono_rec = execute_mono(base, uvspec, mono_text, mono_dir)
            results["alis550"][case].append({**direction, **alis_rec})
            results["mono550"][case].append({**direction, **mono_rec})

    payload = {
        "schemaVersion": 1,
        "stageId": STAGE,
        "executionKey": EXECUTION_KEY,
        "status": "COMPLETED",
        "row": ROW,
        "replicate": a.replicate,
        "seedBase": BASES[a.replicate - 1],
        "seed": seed,
        "sunAltGeometricDeg": float(obs["sun_alt_geometric_deg"]),
        "comparisonRole": obs["comparison_role"],
        "aod550FrozenIdentical": aod,
        "photonsPerDirectionPerCaseArm": PHOTONS,
        "commonRandomSeedAcrossArmsCasesDirectionsWithinReplicate": True,
        "methodCommon": "mc_vroom on + mc_escape on",
        "alisImportanceCenterNm": 550.0,
        "monoWavelengthNm": 550.0,
        "camsProfileSha256": CAMS_PROFILE_SHA,
        "camsSanity": sanity,
        "camsTauMeta": tau_meta,
        "directions": DIRECTIONS,
        "results": results,
        "TaylorResidualUsed": False,
        "ordinal54Salvage": False,
        "importanceWavelengthRetuned": False,
        "physicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }
    (out / "sentinel-result.json").write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    shutil.rmtree(out / "work", ignore_errors=True)
    print(json.dumps({"status": "COMPLETED", "replicate": a.replicate, "seed": seed}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "stageId": STAGE, "error": str(exc)}), file=sys.stderr)
        raise
