from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

STAGE = "aerosol-scenario-interpolation-validation-v1"
AFPF_ADAPTER_REL = Path("experiments/aerosol-full-phase-function-sensitivity-v1/adapter.py")
AFPF_ADAPTER_BLOB = "3f68deb867c8975b00780fcbc503db95d068f338"
ELEVATION_REL = Path("experiments/mystic-batch-v1/twilight_surrogate_tier1_execution_adapter.py")
ELEVATION_BLOB = "b00252709ca9ea41c6bf8b3ab59f8cdb8a2fc7bd"
GRID_REL = Path("experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat")
STATE_MIXTURES = {
    "native-rural-ss": None,
    "opac-continental-average": "continental_average",
    "opac-maritime-clean": "maritime_clean",
    "opac-desert": "desert",
    "opac-desert-spheroids": "desert_spheroids",
}


class AdapterRefusal(RuntimeError):
    pass


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load_bound(name: str, path: Path, expected_blob: str):
    if git_blob_sha1(path) != expected_blob:
        raise AdapterRefusal(f"bound source byte drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AdapterRefusal(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_reference_bindings(repository_root: Path) -> None:
    # AFPF is byte-bound here as the exact scientific provenance of the five-state
    # aerosol directive surface. ASIV reproduces only the AOD-domain-general form.
    _load_bound("asiv_bound_afpf_adapter", repository_root / AFPF_ADAPTER_REL, AFPF_ADAPTER_BLOB)
    _load_bound("asiv_bound_elevation", repository_root / ELEVATION_REL, ELEVATION_BLOB)


def aerosol_block(state_id: str, aod550: float) -> list[str]:
    if state_id not in STATE_MIXTURES:
        raise AdapterRefusal(f"unknown aerosol state: {state_id}")
    if isinstance(aod550, bool) or not isinstance(aod550, (int, float)) or not math.isfinite(float(aod550)) or not 0.05 <= float(aod550) <= 0.40:
        raise AdapterRefusal("AOD550 outside frozen ASIV/Level-B box [0.05,0.40]")
    if state_id == "native-rural-ss":
        return [
            "aerosol_default",
            "aerosol_haze 1",
            "aerosol_vulcan 1",
            "aerosol_season 1",
            f"aerosol_set_tau_at_wvl 550 {float(aod550):.6f}",
        ]
    return [
        "aerosol_default",
        "aerosol_species_library OPAC",
        f"aerosol_species_file {STATE_MIXTURES[state_id]}",
        f"aerosol_set_tau_at_wvl 550 {float(aod550):.6f}",
    ]


def _validate_case(case: dict[str, Any]) -> None:
    if case.get("renderable") is not True or case.get("executionAuthorized") is not True:
        raise AdapterRefusal("case must remain non-renderable until a separate authorization enables it")
    if case.get("numericalMethod") != "reference-vroom-1nm" or case.get("photonHistories") != 20_000_000:
        raise AdapterRefusal("numerical method/photon budget drift")
    if case.get("stateId") not in STATE_MIXTURES:
        raise AdapterRefusal("state universe drift")
    if case.get("replicate") not in (1, 2, 3):
        raise AdapterRefusal("replicate drift")
    for key, low, high in (
        ("sunDepressionDeg", 2.0, 10.5),
        ("targetAltitudeDeg", 5.0, 80.0),
        ("relativeAzimuthDeg", 0.0, 180.0),
        ("observerElevationM", 0.0, 2500.0),
        ("aod550", 0.05, 0.40),
    ):
        value = case.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or not low <= float(value) <= high:
            raise AdapterRefusal(f"physical input outside frozen box: {key}")
    seed = case.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 < seed < 2_147_483_647:
        raise AdapterRefusal("fresh authorized signed-32-bit seed required")
    if case.get("augmentedDataTreeSha256") != "5d8bbf8e6b91ec3d405dee36f21a94afbb6e5ec6cd67da2dd5dd541738199d80":
        raise AdapterRefusal("OPAC data-tree binding drift")


def render_base_input(case: dict[str, Any], data_dir: Path, repository_root: Path, output_root: Path) -> str:
    _validate_case(case)
    dep = float(case["sunDepressionDeg"])
    alt = float(case["targetAltitudeDeg"])
    az = float(case["relativeAzimuthDeg"])
    grid = (repository_root / GRID_REL).resolve()
    if not grid.is_file():
        raise AdapterRefusal("frozen wavelength grid missing")
    lines = [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "mol_abs_param crs",
        f"wavelength_grid_file {grid}",
        "wavelength 380 780",
        f"sza {90.0 + dep:.6f}",
        "phi0 0.00",
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {case['photonHistories']}",
        "mc_vroom on",
        "mc_std",
        f"mc_randomseed {case['seed']}",
        f"mc_basename {(output_root / str(case['caseId']) / 'mc').resolve()}",
        "albedo 0.150000",
        *aerosol_block(str(case["stateId"]), float(case["aod550"])),
        "zout 0.000000",
        f"umu {-math.sin(math.radians(alt)):.8f}",
        f"phi {az:.6f}",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    stripped = [line.strip() for line in text.splitlines() if line.strip()]
    for required in ("wavelength 380 780", "rte_solver mystic", "mc_spherical 1D", "mc_vroom on", "mc_std"):
        if stripped.count(required) != 1:
            raise AdapterRefusal(f"required numerical directive missing/duplicated: {required}")
    if any(line.startswith("mc_spectral_is ") for line in stripped):
        raise AdapterRefusal("ASIV is frozen reference-vroom, not ALIS")
    aerosol_lines = [line for line in stripped if line.startswith("aerosol_")]
    if aerosol_lines != aerosol_block(str(case["stateId"]), float(case["aod550"])):
        raise AdapterRefusal("aerosol directive surface drift")
    return text


def render_case_input(case: dict[str, Any], data_dir: Path, repository_root: Path, output_root: Path) -> tuple[str, dict[str, Any]]:
    verify_reference_bindings(repository_root)
    base = render_base_input(case, data_dir, repository_root, output_root)
    elevation = _load_bound("asiv_bound_elevation_apply", repository_root / ELEVATION_REL, ELEVATION_BLOB)
    text, site_km, grid = elevation.apply_ground_site_atm_z_grid(base, case["observerElevationM"])
    if text.count("atm_z_grid ") != 1 or text.count("zout 0.000000") != 1:
        raise AdapterRefusal("validated local-ground elevation representation drift")
    if "\naltitude " in "\n" + text or "mc_elevation_file" in text:
        raise AdapterRefusal("forbidden elevation shortcut emitted")
    return text, {
        "observerElevationMechanism": "atm_z_grid",
        "siteAltitudeKm": site_km,
        "zoutKmAboveLocalSurface": 0.0,
        "atmosphereGridKm": grid,
        "afpfAerosolReferenceGitBlobSha1": AFPF_ADAPTER_BLOB,
        "elevationTransformGitBlobSha1": ELEVATION_BLOB,
    }
