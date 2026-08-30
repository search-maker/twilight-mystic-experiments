#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

STAGE_ID = "arm-sgp-c1-sasze-real-sky-validation-v1-preflight"
EXPECTED_PROFILE_SHA256 = "6c2db68e7ecf15f65860338c946cc0f5456f012b3a46eb8b111809b2184ffdd2"
EXPECTED_CONFIG_SHA256 = "8bced2434c4584b59d00eb47f9f004a46a21ea4a6c77e4cbab7a5036dcfec5ad"
EXPECTED_SCENARIOS_SHA256 = "7ea2fb2cf10e95b3d11c27e20650eeca319ab9aea31141075fede2ee98a9b97f"
PROFILE_TRANSPORT = Path("review/aerosol-vertical-profile-transport-v1/profile_transport.py")


class PreflightRefusal(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PreflightRefusal(f"expected JSON object: {path}")
    return value


def load_transport(repository_root: Path):
    path = repository_root / PROFILE_TRANSPORT
    spec = importlib.util.spec_from_file_location("arm_sgp_profile_transport", path)
    if spec is None or spec.loader is None:
        raise PreflightRefusal(f"cannot import reviewed transport: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def atmosphere_levels_desc(path: Path) -> list[float]:
    levels: list[float] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            z = float(line.split()[0])
        except (ValueError, IndexError) as exc:
            raise PreflightRefusal(f"invalid atmosphere row: {raw}") from exc
        if not math.isfinite(z):
            raise PreflightRefusal("nonfinite atmosphere altitude")
        levels.append(z)
    if len(levels) < 2 or any(a <= b for a, b in zip(levels, levels[1:])):
        raise PreflightRefusal("AFGL atmosphere levels must be strictly descending")
    return levels


def target_edges_m(atmosphere: Path, site_km: float) -> tuple[float, ...]:
    levels = atmosphere_levels_desc(atmosphere)
    if not levels[-1] <= site_km < levels[0]:
        raise PreflightRefusal("site altitude outside atmosphere grid")
    asc_km = [site_km, *sorted(z for z in levels if z > site_km)]
    if any(a >= b for a, b in zip(asc_km, asc_km[1:])):
        raise PreflightRefusal("forced atmosphere grid is not strictly increasing")
    return tuple(z * 1000.0 for z in asc_km)


def load_central_scenario(path: Path) -> dict[str, str]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    matches = [r for r in rows if r.get("scenario_id") == "CORE_CENTRAL"]
    if len(matches) != 1:
        raise PreflightRefusal("CORE_CENTRAL must occur exactly once")
    return matches[0]


def load_profile(path: Path, anchor: str, variant: str, site_m: float) -> tuple[list[float], list[float], str]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    selected = [r for r in rows if r.get("anchor_id") == anchor and r.get("variant") == variant]
    if len(selected) < 2:
        raise PreflightRefusal("frozen FEX profile missing")
    times = {str(r["source_time_utc"]) for r in selected}
    if len(times) != 1:
        raise PreflightRefusal("profile source-time identity is not unique")
    pairs = [(site_m + float(r["height_m_agl"]), float(r["shape_beta"])) for r in selected]
    if any(not math.isfinite(z) or not math.isfinite(v) or v < 0 for z, v in pairs):
        raise PreflightRefusal("invalid frozen FEX profile value")
    if any(a[0] >= b[0] for a, b in zip(pairs, pairs[1:])):
        raise PreflightRefusal("frozen FEX profile altitude not strictly increasing")
    return [z for z, _ in pairs], [v for _, v in pairs], times.pop()


def combine_profile(pt, edges: tuple[float, ...], site_m: float, aod: float, near_ext_mm1: float,
                    z: list[float], beta: list[float], identity: dict[str, Any]):
    slab_top = site_m + 200.0
    slab = pt.remap_normalized_vertical_shape(
        [site_m, slab_top], [1.0, 1.0], edges,
        outside_below_policy="reject", outside_above_policy="zero",
        source_identity={"component": "surface-slab", **identity},
    )
    elevated = pt.remap_normalized_vertical_shape(
        z, beta, edges,
        outside_below_policy="zero", outside_above_policy="zero",
        source_identity={"component": "FEX-backscatter-shape", **identity},
    )
    slab_tau = near_ext_mm1 * 1.0e-3 * 0.2
    if not (0.0 <= slab_tau < aod):
        raise PreflightRefusal(f"surface-slab tau {slab_tau} not in [0,AOD)")
    w_slab = slab_tau / aod
    w_elev = 1.0 - w_slab
    fractions = tuple(w_slab * a + w_elev * b for a, b in zip(slab.layer_tau_fractions, elevated.layer_tau_fractions))
    if abs(math.fsum(fractions) - 1.0) > 1e-12 or any(v < 0 for v in fractions):
        raise PreflightRefusal("combined aerosol tau fractions invalid")
    combined_fingerprint = hashlib.sha256(json.dumps({
        "slab": slab.source_fingerprint_sha256,
        "elevated": elevated.source_fingerprint_sha256,
        "aod": aod,
        "nearSurfaceExtMm1": near_ext_mm1,
        "identity": identity,
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return pt.RemappedProfile(
        target_edges_m=edges,
        layer_tau_fractions=fractions,
        transported_integral=1.0,
        outside_below_policy="component-explicit",
        outside_above_policy="component-explicit",
        source_fingerprint_sha256=combined_fingerprint,
    ), slab_tau


def exact_float(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise PreflightRefusal(f"invalid central scenario field: {key}") from exc
    if not math.isfinite(value):
        raise PreflightRefusal(f"nonfinite central scenario field: {key}")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repository-root", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    root = args.repository_root.resolve()
    stage = root / "experiments/arm-sgp-c1-real-sky-validation-v1"
    config_path = stage / "frozen-config.json"
    scenarios_path = stage / "uncertainty-scenarios.csv"
    profiles_path = stage / "fex-profile-shapes.csv"
    if sha256_file(config_path) != EXPECTED_CONFIG_SHA256:
        raise PreflightRefusal("frozen-config SHA-256 drift")
    if sha256_file(scenarios_path) != EXPECTED_SCENARIOS_SHA256:
        raise PreflightRefusal("uncertainty-scenarios SHA-256 drift")
    if sha256_file(profiles_path) != EXPECTED_PROFILE_SHA256:
        raise PreflightRefusal("FEX profile SHA-256 drift")
    config = load_json(config_path)
    if config.get("status") != "FROZEN_PREREGISTRATION_NO_MYSTIC_RESULTS_OPENED" or config.get("antiFitting") is not True:
        raise PreflightRefusal("preregistration status/anti-fitting boundary drift")
    central = load_central_scenario(scenarios_path)
    anchor_id = "minus7"
    anchor = config["anchors"][anchor_id]
    if central.get("profile_variant") != "central":
        raise PreflightRefusal("central scenario profile variant drift")
    checks = {
        "aod464": config["aerosol"]["aod464"]["central"],
        "ssa464": config["aerosol"]["ssa464"]["central"],
        "g464": config["aerosol"]["g464"]["central"],
        "albedo464": config["surface"]["albedo464"]["central"],
        "near_surface_ext_Mm-1": config["aerosol"]["nearSurfaceDryExtinction_Mm-1"]["central"],
    }
    for key, expected in checks.items():
        got = exact_float(central, key)
        if abs(got - float(expected)) > 5e-12:
            raise PreflightRefusal(f"central scenario/config mismatch {key}: {got} != {expected}")

    data = args.data_dir.resolve()
    atmosphere = data / "atmmod/afglus.dat"
    solar = data / "solar_flux/atlas_plus_modtran"
    if not atmosphere.is_file() or not solar.is_file():
        raise PreflightRefusal("required libRadtran data file missing")
    site_km = float(config["molecularAtmosphere"]["site_altitude_km"])
    site_m = site_km * 1000.0
    edges = target_edges_m(atmosphere, site_km)
    z, beta, source_time = load_profile(profiles_path, anchor_id, "central", site_m)
    expected_time = config["aerosol"]["verticalShape"]["variants_by_anchor"][anchor_id]["central"]
    if source_time != expected_time:
        raise PreflightRefusal("central profile source-time drift")
    pt = load_transport(root)
    remapped, slab_tau = combine_profile(
        pt, edges, site_m, exact_float(central, "aod464"), exact_float(central, "near_surface_ext_Mm-1"),
        z, beta, {"event": config["event"], "anchor": anchor_id, "variant": "central", "sourceTimeUtc": source_time},
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    tau_path = (args.output_dir / "central-minus7-aerosol-tau.dat").resolve()
    tau_path.write_text(pt.render_libradtran_aerosol_tau(remapped, header="ARM SGP frozen central -7 aerosol vertical tau fractions"), encoding="utf-8", newline="\n")
    grid_km = [v / 1000.0 for v in edges]
    wavelength = float(config["solver"]["wavelength_nm"])
    lines = [
        f"data_files_path {data}",
        f"atmosphere_file {atmosphere}",
        f"source solar {solar}",
        "mol_abs_param crs",
        f"wavelength {wavelength:.6f} {wavelength:.6f}",
        f"day_of_year {int(config['molecularAtmosphere']['day_of_year'])}",
        f"sza {float(anchor['sza_deg']):.6f}",
        f"phi0 {float(config['solver']['phi0_deg']):.6f}",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {int(config['solver']['screening_photons_per_case'])}",
        "mc_vroom on",
        "mc_std",
        f"albedo {exact_float(central, 'albedo464'):.12f}",
        "atm_z_grid " + " ".join(f"{zkm:.6f}" for zkm in grid_km),
        "zout 0.000000",
        f"pressure {float(config['molecularAtmosphere']['surface_pressure_hpa']):.9f}",
        f"mol_modify H2O {float(config['molecularAtmosphere']['precipitable_water_mm']):.12f} MM",
        f"mol_modify O3 {float(config['molecularAtmosphere']['ozone_DU']):.6f} DU",
        "aerosol_default",
        f"aerosol_file tau {tau_path}",
        f"aerosol_modify ssa set {exact_float(central, 'ssa464'):.12f}",
        f"aerosol_modify gg set {exact_float(central, 'g464'):.12f}",
        f"aerosol_set_tau_at_wvl {wavelength:.6f} {exact_float(central, 'aod464'):.12f}",
        f"umu {float(config['solver']['umu']):.8f}",
        f"phi {float(config['solver']['phi_deg']):.6f}",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    input_path = args.output_dir / "central-minus7.inp"
    input_path.write_text(text, encoding="utf-8", newline="\n")
    required_prefixes = ["aerosol_file tau ", "aerosol_modify ssa set ", "aerosol_modify gg set ", "aerosol_set_tau_at_wvl "]
    if any(sum(line.startswith(p) for line in lines) != 1 for p in required_prefixes):
        raise PreflightRefusal("aerosol directive cardinality drift")
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARED_SYNTAX_ONLY_NO_SOLVER",
        "anchorId": anchor_id,
        "scenarioId": "CORE_CENTRAL",
        "sourceProfileTimeUtc": source_time,
        "aerosolTauSha256": sha256_file(tau_path),
        "inputSha256": sha256_file(input_path),
        "surfaceSlabTau464": slab_tau,
        "layerFractionSum": math.fsum(remapped.layer_tau_fractions),
        "atmosphereGridKm": grid_km,
        "scientificSolverExecuted": False,
        "saszeRadianceOpened": False,
        "scientificOrdinalAllocated": False,
        "seedAllocated": False,
    }
    (args.output_dir / "preflight-prepared.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "REFUSED", "stageId": STAGE_ID, "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
