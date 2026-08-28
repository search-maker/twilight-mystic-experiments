from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

STAGE_ID = "opac-species-profile-transport-capability-v2"
SPECIES = "INSO"
AOD550 = 0.10
DISORT_SZA_DEG = 80.0
MYSTIC_SZA_DEG = 96.0
TARGET_ALTITUDE_DEG = 30.0
RELATIVE_AZIMUTH_DEG = 90.0
MYSTIC_PHOTONS = 500_000
MYSTIC_SEED = 730_194_613
WAVELENGTH_START_NM = 540
WAVELENGTH_STOP_NM = 560


class CapabilityInputError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_afgl_heights_km(path: Path) -> tuple[float, ...]:
    rows: list[float] = []
    for raw in path.read_text().splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        try:
            rows.append(float(s.split()[0]))
        except (ValueError, IndexError) as exc:
            raise CapabilityInputError(f"invalid atmosphere altitude row: {raw!r}") from exc
    if len(rows) < 5:
        raise CapabilityInputError("atmosphere needs at least five altitude levels")
    if not all(rows[i] > rows[i + 1] for i in range(len(rows) - 1)):
        raise CapabilityInputError("expected strictly descending AFGL altitude grid")
    if rows[-1] > 1e-9:
        raise CapabilityInputError("capability is frozen to a sea-level atmosphere grid")
    return tuple(rows)


def _trapezoid_integral_descending(z_desc: Iterable[float], y_desc: Iterable[float]) -> float:
    z = list(reversed(tuple(z_desc)))
    y = list(reversed(tuple(y_desc)))
    return math.fsum(0.5 * (y[i] + y[i + 1]) * (z[i + 1] - z[i]) for i in range(len(z) - 1))


def synthetic_density_shape(heights_km: tuple[float, ...], state: str) -> tuple[float, ...]:
    if state == "low":
        raw = [math.exp(-max(z, 0.0) / 0.55) for z in heights_km]
    elif state == "high":
        raw = [math.exp(-0.5 * ((z - 8.0) / 0.75) ** 2) for z in heights_km]
    else:
        raise CapabilityInputError(f"unknown synthetic capability state: {state}")
    integral = _trapezoid_integral_descending(heights_km, raw)
    if not math.isfinite(integral) or integral <= 0:
        raise CapabilityInputError(f"invalid synthetic profile integral: {state}")
    # Equal arbitrary column mass normalization before the independent AOD550 rescale.
    # The absolute mass is not interpreted scientifically in this capability gate.
    target_integral_g_m3_km = 1.0e-6
    scale = target_integral_g_m3_km / integral
    values = tuple(v * scale for v in raw)
    if any((not math.isfinite(v)) or v < 0 for v in values):
        raise CapabilityInputError(f"invalid synthetic profile density: {state}")
    return values


def render_species_profile(heights_km: tuple[float, ...], state: str) -> str:
    values = synthetic_density_shape(heights_km, state)
    lines = [
        f"# {STAGE_ID} synthetic {state} profile; capability only; no climatological meaning",
        f"# altitude_km mass_density_g_m3_{SPECIES}",
    ]
    lines.extend(f"{z:.9f} {v:.17e}" for z, v in zip(heights_km, values))
    return "\n".join(lines) + "\n"


def aerosol_block(profile_path: Path) -> list[str]:
    return [
        "aerosol_default",
        "aerosol_species_library OPAC",
        f"aerosol_species_file {profile_path.resolve()} {SPECIES}",
        f"aerosol_set_tau_at_wvl 550 {AOD550:.6f}",
    ]


def _common_lines(data_dir: Path, repository_root: Path, sza_deg: float, profile_path: Path) -> list[str]:
    grid = (repository_root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat").resolve()
    if not grid.is_file():
        raise CapabilityInputError(f"frozen wavelength grid missing: {grid}")
    return [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "mol_abs_param crs",
        f"wavelength_grid_file {grid}",
        f"wavelength {WAVELENGTH_START_NM} {WAVELENGTH_STOP_NM}",
        f"sza {sza_deg:.6f}",
        "phi0 0.000000",
        "albedo 0.150000",
        *aerosol_block(profile_path),
        "zout 0.000000",
        f"umu {-math.sin(math.radians(TARGET_ALTITUDE_DEG)):.8f}",
        f"phi {RELATIVE_AZIMUTH_DEG:.6f}",
    ]


def render_disort_input(data_dir: Path, repository_root: Path, profile_path: Path) -> str:
    lines = [
        *_common_lines(data_dir, repository_root, DISORT_SZA_DEG, profile_path),
        "rte_solver disort",
        "number_of_streams 16",
        "output_user lambda uu",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    assert_corrected_surface(text, profile_path, mystic=False)
    return text


def render_mystic_input(data_dir: Path, repository_root: Path, profile_path: Path, run_dir: Path) -> str:
    lines = [
        *_common_lines(data_dir, repository_root, MYSTIC_SZA_DEG, profile_path),
        "rte_solver mystic",
        "mc_spherical 1D",
        f"mc_photons {MYSTIC_PHOTONS}",
        "mc_vroom on",
        "mc_std",
        f"mc_randomseed {MYSTIC_SEED}",
        f"mc_basename {(run_dir / 'mc').resolve()}",
        "quiet",
    ]
    text = "\n".join(lines) + "\n"
    assert_corrected_surface(text, profile_path, mystic=True)
    return text


def assert_corrected_surface(text: str, profile_path: Path, *, mystic: bool) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    aerosol = [line for line in lines if line.startswith("aerosol_")]
    expected = aerosol_block(profile_path)
    if aerosol != expected:
        raise CapabilityInputError(f"corrected aerosol directive surface drift: {aerosol!r}")
    if any(line.startswith("aerosol_file ") for line in aerosol):
        raise CapabilityInputError("corrected capability must not combine aerosol_file with aerosol_species_file")
    if sum(line.startswith("aerosol_species_file ") for line in aerosol) != 1:
        raise CapabilityInputError("exactly one custom aerosol_species_file is required")
    if not aerosol[2].endswith(f" {SPECIES}"):
        raise CapabilityInputError("single frozen INSO species binding drift")
    if lines.count(f"aerosol_set_tau_at_wvl 550 {AOD550:.6f}") != 1:
        raise CapabilityInputError("exact fixed AOD550 normalization required")
    if mystic:
        required = {
            "rte_solver mystic",
            "mc_spherical 1D",
            f"mc_photons {MYSTIC_PHOTONS}",
            f"mc_randomseed {MYSTIC_SEED}",
        }
        if not required.issubset(set(lines)):
            raise CapabilityInputError("MYSTIC capability surface drift")
    else:
        if "rte_solver disort" not in lines or "number_of_streams 16" not in lines:
            raise CapabilityInputError("DISORT capability surface drift")


def write_bundle(atmosphere_path: Path, data_dir: Path, repository_root: Path, output_root: Path) -> dict:
    if output_root.exists():
        raise CapabilityInputError(f"output already exists: {output_root}")
    heights = parse_afgl_heights_km(atmosphere_path)
    profile_dir = output_root / "profiles"
    input_dir = output_root / "inputs"
    run_root = output_root / "runs"
    profile_dir.mkdir(parents=True)
    input_dir.mkdir()
    run_root.mkdir()

    profile_paths: dict[str, Path] = {}
    for state in ("low", "high"):
        path = profile_dir / f"synthetic-{state}-{SPECIES.lower()}.dat"
        path.write_text(render_species_profile(heights, state))
        profile_paths[state] = path
        (run_root / f"mystic-{state}").mkdir()

    for state in ("low", "high"):
        (input_dir / f"disort-{state}.inp").write_text(
            render_disort_input(data_dir, repository_root, profile_paths[state])
        )
        (input_dir / f"mystic-{state}.inp").write_text(
            render_mystic_input(data_dir, repository_root, profile_paths[state], run_root / f"mystic-{state}")
        )

    low_values = synthetic_density_shape(heights, "low")
    high_values = synthetic_density_shape(heights, "high")
    if low_values == high_values:
        raise CapabilityInputError("synthetic low/high profiles must differ before execution")
    meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FROZEN_SYNTHETIC_CAPABILITY_INPUTS_NO_SCIENTIFIC_INTERPRETATION",
        "species": SPECIES,
        "speciesReason": "single insoluble OPAC species avoids soluble-species humidity-growth variation in this transport capability test",
        "aod550": AOD550,
        "wavelengthRangeNm": [WAVELENGTH_START_NM, WAVELENGTH_STOP_NM],
        "disortSzaDeg": DISORT_SZA_DEG,
        "mysticSzaDeg": MYSTIC_SZA_DEG,
        "targetAltitudeDeg": TARGET_ALTITUDE_DEG,
        "relativeAzimuthDeg": RELATIVE_AZIMUTH_DEG,
        "mysticPhotons": MYSTIC_PHOTONS,
        "mysticSeed": MYSTIC_SEED,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "profileDefinitions": {
            "low": "exp(-z/0.55 km), normalized to equal arbitrary column mass before AOD rescale",
            "high": "Gaussian centered 8.0 km with sigma 0.75 km, normalized to equal arbitrary column mass before AOD rescale",
        },
        "files": {},
    }
    for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
        meta["files"][str(path.relative_to(output_root))] = sha256_file(path)
    (output_root / "input-manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atmosphere", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    meta = write_bundle(args.atmosphere, args.data_dir, args.repository_root, args.output)
    print(json.dumps(meta, sort_keys=True))


if __name__ == "__main__":
    main()
