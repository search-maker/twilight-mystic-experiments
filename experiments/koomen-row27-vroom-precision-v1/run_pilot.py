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

STAGE = "koomen-row27-vroom-precision-v1"
EXECUTION_KEY = "koomen-row27-vroom-precision-v1:scientific:53"
ROW = 27
BASES = [1571000000, 1572000000, 1573000000, 1574000000, 1575000000, 1576000000]
PHOTONS = 6_500_000
PROFILE_SOURCE_PHOTONS = 200_000
SEED_OFFSET = 980
DIRECTIONS = [
    {"directionIndex": 0, "thetaDeg": 0.0, "relativeAzimuthDeg": 0.0, "label": "center"},
    {"directionIndex": 1, "thetaDeg": 0.75, "relativeAzimuthDeg": 0.0, "label": "edge_000"},
    {"directionIndex": 2, "thetaDeg": 0.75, "relativeAzimuthDeg": 90.0, "label": "edge_090"},
    {"directionIndex": 3, "thetaDeg": 0.75, "relativeAzimuthDeg": 180.0, "label": "edge_180"},
    {"directionIndex": 4, "thetaDeg": 0.75, "relativeAzimuthDeg": 270.0, "label": "edge_270"},
]
CAMS_PROFILE_SHA = "6c3a3041b6718db415300323f23da0277752b6c9fc6c806e5eff7c493b060359"
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
    if m.get("issue") != 854 or m.get("row") != ROW:
        raise Failure("issue/row changed")
    if m.get("replicateSeedBases") != BASES:
        raise Failure("seed universe changed")
    if m.get("photonsPerDirectionPerCase") != PHOTONS:
        raise Failure("photon budget changed")
    if m.get("fixedDirections") != DIRECTIONS:
        raise Failure("direction universe changed")
    if m.get("method") != "mc_vroom_on" or m.get("mcEscapeExplicit") != "on":
        raise Failure("estimator method changed")
    if m.get("profileSha256") != CAMS_PROFILE_SHA:
        raise Failure("profile provenance changed")
    if m.get("maximumSolverCalls") != 60 or m.get("maximumConfiguredPhotonHistories") != 390_000_000:
        raise Failure("maximum budget changed")
    analysis = m.get("analysis", {})
    if analysis.get("edgeMinusCenterSeThresholdMag") != 0.03 or analysis.get("edgeQuantityCount") != 16:
        raise Failure("precision decision changed")
    for key in ("fitTaylor", "fitAcceptance", "fitFov", "fitOffset", "fitAtmosphere", "fitAod", "fitProfile", "fitAnyParameter"):
        if analysis.get(key) is not False:
            raise Failure(f"fitting prohibition changed: {key}")
    boundaries = m.get("boundaries", {})
    for key in ("TaylorResidualUsed", "historicalKoomenCorrectionComputed", "physicalSupportEnvelopeAuthorized", "full81DirectionGridAuthorized", "productionAuthorized", "priorOrdinalsRerunAuthorized"):
        if boundaries.get(key) is not False:
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


def force_vroom(text: str) -> str:
    old = "mc_vroom off"
    lines = text.splitlines()
    if lines.count(old) != 1:
        raise Failure("expected exactly one mc_vroom off in frozen source render")
    if any(line.startswith("mc_escape ") for line in lines):
        raise Failure("unexpected pre-existing explicit mc_escape")
    out = []
    for line in lines:
        if line == old:
            out.extend(["mc_vroom on", "mc_escape on"])
        else:
            out.append(line)
    if out.count("mc_vroom on") != 1 or out.count("mc_escape on") != 1:
        raise Failure("VROOM mutation failed")
    return "\n".join(out) + "\n"


def photopic(wl, radiance) -> float:
    response = np.interp(wl, CIE_WL, V_PHOT, left=0.0, right=0.0)
    q = KM_PHOTOPIC * float(np.trapezoid(radiance * response, wl))
    if not q > 0 or not math.isfinite(q):
        raise Failure("invalid photopic q")
    return q


def execute(base, uvspec: Path, text: str, case_dir: Path, theta: float, tables):
    case_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "input-resolved.txt").write_text(text)
    started = time.monotonic()
    syntax_seconds = base.run_process(uvspec, text, case_dir, syntax=True)
    solver_seconds = base.run_process(uvspec, text, case_dir, syntax=False)
    wall_seconds = time.monotonic() - started
    rad = case_dir / "mc.rad.spc"
    std = case_dir / "mc.rad.std.spc"
    if not rad.is_file() or not std.is_file():
        raise Failure("missing spectra")
    wl, radiance = base.parse_spectrum(rad)
    q_cie = photopic(wl, radiance)
    q_sqm, q_std, n, w0, w1 = base.integrate_ray(rad, std, theta, tables)
    if not q_sqm > 0 or not math.isfinite(q_sqm):
        raise Failure("invalid sqm q")
    rec = {
        "ciePhotopicQ": q_cie,
        "sqmConditionalQ": q_sqm,
        "sqmStdDiagnosticNotBetweenSeed": q_std,
        "syntaxSeconds": syntax_seconds,
        "solverSeconds": solver_seconds,
        "wallSeconds": wall_seconds,
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
    if not 1 <= a.replicate <= len(BASES):
        raise Failure("replicate outside frozen universe")

    base = load_module(a.baseline_runner, "baseline")
    prof = load_module(a.profile_runner, "profile")
    obs = base.load_observation(a.observations, ROW)
    tables = base.load_response(a.response)
    profiles, sanity = prof.load_cams_profile(a.cams_profile)
    if sha(a.cams_profile) != CAMS_PROFILE_SHA:
        raise Failure("profile sha changed")

    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    data = a.data_dir.resolve()
    atmosphere = (data / "atmmod/afglus.dat").resolve()
    uvspec = a.uvspec.resolve()
    tau_path = out / "cams-site-grid-tau.dat"
    tau_meta = prof.write_tau_profile(base, atmosphere, profiles, prof.parse_utc(obs["utc"]), tau_path)

    aod = float(obs["aod550_primary_frozen"])
    seed = BASES[a.replicate - 1] + ROW * 1000 + SEED_OFFSET
    results = {}
    for case in ("baseline", "profile"):
        records = []
        for direction in DIRECTIONS:
            ray = {"thetaDeg": direction["thetaDeg"], "relativeAzimuthDeg": direction["relativeAzimuthDeg"]}
            case_dir = out / "work" / case / direction["label"]
            if case == "baseline":
                text = base.render(data, atmosphere, case_dir, obs, ray, aod, PHOTONS, seed)
                if text.splitlines().count(f"mc_photons {PHOTONS}") != 1:
                    raise Failure("baseline render did not preserve high-photon budget")
            else:
                text = prof.render_profile(base, data, atmosphere, case_dir, obs, ray, aod, seed, tau_path)
                text = mutate_profile_photons(text)
            text = force_vroom(text)
            records.append({**direction, **execute(base, uvspec, text, case_dir, direction["thetaDeg"], tables)})
        results[case] = records

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
        "photonsPerDirectionPerCase": PHOTONS,
        "commonRandomNumbersAcrossCasesDirections": True,
        "method": "mc_vroom on + mc_escape on",
        "directions": DIRECTIONS,
        "profileSanity": sanity,
        "profileTauMeta": tau_meta,
        "results": results,
        "TaylorResidualUsed": False,
        "historicalKoomenCorrectionComputed": False,
        "physicalSupportEnvelopeAuthorized": False,
        "full81DirectionGridAuthorized": False,
        "productionAuthorized": False,
    }
    (out / "precision-result.json").write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": "COMPLETED", "replicate": a.replicate, "solverCalls": 10}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "stageId": STAGE, "error": str(exc)}), file=sys.stderr)
        raise
