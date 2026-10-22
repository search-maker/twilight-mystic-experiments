from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

STAGE_ID = "opac-continental-average-multispecies-transport-capability-v1"
SPECIES = ("INSO", "WASO", "SOOT", "SUSO")
AOD550 = 0.10
DISORT_SZA_DEG = 80.0
MYSTIC_SZA_DEG = 96.0
TARGET_ALTITUDE_DEG = 30.0
RELATIVE_AZIMUTH_DEG = 90.0
MYSTIC_PHOTONS = 500_000
MYSTIC_SEED = 730_194_613
WAVELENGTH_START_NM = 540
WAVELENGTH_STOP_NM = 560
CONTINENTAL_SOURCE_REL = Path("aerosol/OPAC/standard_aerosol_files/continental_average.dat")
EXPECTED_CONTINENTAL_SOURCE_SHA256 = "fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469"
SOURCE_ASSETS = {
    "INSO": (Path("aerosol/OPAC/optprop/inso.mie.cdf"), "fe10348cbe585315d6e1db382563fdc054204ad35846f371dc9d8abeead36407"),
    "WASO": (Path("aerosol/OPAC/optprop/waso.mie.cdf"), "b6df493b77019bf5e22456e8fb8858c5a7d502bcc02fe6fc697ebd4844f2d4f5"),
    "SOOT": (Path("aerosol/OPAC/optprop/soot.mie.cdf"), "44a0d2060101ca52c90ae64f005118dfba256b1f89a3049e1f758c55d634aa02"),
    "SUSO": (Path("aerosol/OPAC/optprop/suso.mie.cdf"), "ce0e1bba4219c60af0af14d66a280b0d3d25188276eed0951d31594b947cd472"),
}
ALIAS_TARGETS = {s: Path(f"aerosol/OPAC/optprop/{s}") for s in SPECIES}
FAILED_ALIAS_TARGETS = tuple(
    [Path(f"aerosol/OPAC/optprop/{s}.nc") for s in SPECIES]
    + [Path(f"aerosol/OPAC/{s}.nc") for s in SPECIES]
)
PROFILE_MASS_WEIGHTS = {s: 0.25 for s in SPECIES}


class CapabilityInputError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_continental_average_source(data_dir: Path) -> dict:
    path = data_dir / CONTINENTAL_SOURCE_REL
    if not path.is_file() or path.stat().st_size <= 0:
        raise CapabilityInputError(f"continental_average source missing/empty: {path}")
    digest = sha256_file(path)
    if digest != EXPECTED_CONTINENTAL_SOURCE_SHA256:
        raise CapabilityInputError("continental_average source SHA drift")
    text = path.read_text(errors="strict")
    normalized = " ".join(text.lower().replace("#", " ").split())
    if "z(km) inso waso soot suso" not in normalized:
        raise CapabilityInputError("continental_average species-column header drift")
    numeric = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        vals = tuple(float(x) for x in s.split())
        if len(vals) != 5 or any(not math.isfinite(v) for v in vals):
            raise CapabilityInputError("continental_average numeric row drift")
        numeric.append(vals)
    if len(numeric) != 14:
        raise CapabilityInputError(f"continental_average row-count drift: {len(numeric)}")
    return {
        "relativePath": CONTINENTAL_SOURCE_REL.as_posix(),
        "sha256": digest,
        "byteCount": path.stat().st_size,
        "numericRows": len(numeric),
        "speciesColumns": list(SPECIES),
        "sourceAuditPr": 591,
        "sourceAuditRunId": 33187119926,
        "sourceAuditArtifactId": 9692162280,
        "sourceAuditArtifactDigest": "sha256:cdcb0041a5197e31ff24520b3e653119d11c5d4a1c1b4f727e392ba7e719101e",
    }


def prepare_species_aliases(data_dir: Path) -> dict:
    for rel in FAILED_ALIAS_TARGETS:
        if (data_dir / rel).exists():
            raise CapabilityInputError(f"historical .nc alias unexpectedly exists: {rel}")
    rows = []
    for species in SPECIES:
        source_rel, expected_sha = SOURCE_ASSETS[species]
        target_rel = ALIAS_TARGETS[species]
        source = data_dir / source_rel
        target = data_dir / target_rel
        if not source.is_file() or source.stat().st_size <= 0:
            raise CapabilityInputError(f"official OPAC source missing/empty: {source_rel}")
        source_sha = sha256_file(source)
        if source_sha != expected_sha:
            raise CapabilityInputError(f"official OPAC source SHA drift: {species}")
        if target.exists():
            raise CapabilityInputError(f"no-extension alias unexpectedly preexists: {target_rel}")
        payload = source.read_bytes()
        target.write_bytes(payload)
        if target.read_bytes() != payload:
            raise CapabilityInputError(f"alias byte mismatch: {species}")
        alias_sha = sha256_file(target)
        if alias_sha != expected_sha or target.stat().st_size != source.stat().st_size:
            raise CapabilityInputError(f"alias digest/size mismatch: {species}")
        rows.append({
            "species": species,
            "sourceRelativePath": source_rel.as_posix(),
            "aliasRelativePath": target_rel.as_posix(),
            "sourceSha256": expected_sha,
            "aliasSha256": alias_sha,
            "byteCount": source.stat().st_size,
            "byteIdentical": True,
        })
    for rel in FAILED_ALIAS_TARGETS:
        if (data_dir / rel).exists():
            raise CapabilityInputError(f"historical .nc alias appeared during creation: {rel}")
    return {
        "schemaVersion": 1,
        "status": "FOUR_BYTE_IDENTICAL_NO_EXTENSION_OPAC_ALIASES_CREATED",
        "species": list(SPECIES),
        "aliases": rows,
        "allByteIdentical": all(r["byteIdentical"] for r in rows),
        "traceGeneralizationBoundary": "INSO no-extension path was directly traced in run 33185460954; WASO/SOOT/SUSO analogous no-extension paths are hypotheses tested by this capability, not assumed scientific facts.",
        "singleSpeciesCapabilityRunId": 33186446347,
        "singleSpeciesCapabilityArtifactId": 9691923455,
        "singleSpeciesCapabilityArtifactDigest": "sha256:fed6bb961088232e593159c4f50911758802e9209aed86e2a0eef4b403e4d9b7",
    }


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
    scale = 1.0e-6 / integral
    values = tuple(v * scale for v in raw)
    if any((not math.isfinite(v)) or v < 0 for v in values):
        raise CapabilityInputError(f"invalid synthetic profile density: {state}")
    return values


def render_species_profile(heights_km: tuple[float, ...], state: str) -> str:
    base = synthetic_density_shape(heights_km, state)
    lines = [
        f"# {STAGE_ID} synthetic {state}; transport capability only; no climatological meaning",
        "# altitude_km mass_density_g_m3_INSO mass_density_g_m3_WASO mass_density_g_m3_SOOT mass_density_g_m3_SUSO",
    ]
    for z, density in zip(heights_km, base):
        vals = [density * PROFILE_MASS_WEIGHTS[s] for s in SPECIES]
        lines.append(f"{z:.9f} " + " ".join(f"{v:.17e}" for v in vals))
    return "\n".join(lines) + "\n"


def aerosol_block(profile_path: Path) -> list[str]:
    return [
        "aerosol_default",
        "aerosol_species_library OPAC",
        f"aerosol_species_file {profile_path.resolve()} {' '.join(SPECIES)}",
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


def assert_corrected_surface(text: str, profile_path: Path, *, mystic: bool) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    aerosol = [line for line in lines if line.startswith("aerosol_")]
    expected = aerosol_block(profile_path)
    if aerosol != expected:
        raise CapabilityInputError(f"multispecies aerosol directive surface drift: {aerosol!r}")
    if any(line.startswith("aerosol_file ") for line in aerosol):
        raise CapabilityInputError("competing aerosol_file directive is forbidden")
    species_lines = [line for line in aerosol if line.startswith("aerosol_species_file ")]
    if len(species_lines) != 1 or not species_lines[0].endswith(" " + " ".join(SPECIES)):
        raise CapabilityInputError("exact four-species binding drift")
    if lines.count(f"aerosol_set_tau_at_wvl 550 {AOD550:.6f}") != 1:
        raise CapabilityInputError("exact fixed AOD550 normalization required")
    if mystic:
        required = {"rte_solver mystic", "mc_spherical 1D", f"mc_photons {MYSTIC_PHOTONS}", f"mc_randomseed {MYSTIC_SEED}"}
        if not required.issubset(set(lines)):
            raise CapabilityInputError("MYSTIC capability surface drift")
    elif "rte_solver disort" not in lines or "number_of_streams 16" not in lines:
        raise CapabilityInputError("DISORT capability surface drift")


def render_disort_input(data_dir: Path, repository_root: Path, profile_path: Path) -> str:
    text = "\n".join([
        *_common_lines(data_dir, repository_root, DISORT_SZA_DEG, profile_path),
        "rte_solver disort", "number_of_streams 16", "output_user lambda uu", "quiet",
    ]) + "\n"
    assert_corrected_surface(text, profile_path, mystic=False)
    return text


def render_mystic_input(data_dir: Path, repository_root: Path, profile_path: Path, run_dir: Path) -> str:
    text = "\n".join([
        *_common_lines(data_dir, repository_root, MYSTIC_SZA_DEG, profile_path),
        "rte_solver mystic", "mc_spherical 1D", f"mc_photons {MYSTIC_PHOTONS}", "mc_vroom on", "mc_std",
        f"mc_randomseed {MYSTIC_SEED}", f"mc_basename {(run_dir / 'mc').resolve()}", "quiet",
    ]) + "\n"
    assert_corrected_surface(text, profile_path, mystic=True)
    return text


def write_bundle(atmosphere_path: Path, data_dir: Path, repository_root: Path, output_root: Path) -> dict:
    if output_root.exists():
        raise CapabilityInputError(f"output already exists: {output_root}")
    source_evidence = verify_continental_average_source(data_dir)
    aliases = prepare_species_aliases(data_dir)
    heights = parse_afgl_heights_km(atmosphere_path)
    profile_dir = output_root / "profiles"
    input_dir = output_root / "inputs"
    run_root = output_root / "runs"
    profile_dir.mkdir(parents=True)
    input_dir.mkdir()
    run_root.mkdir()

    profile_paths: dict[str, Path] = {}
    for state in ("low", "high"):
        path = profile_dir / f"synthetic-{state}-continental-four-species.dat"
        path.write_text(render_species_profile(heights, state))
        profile_paths[state] = path
        (run_root / f"mystic-{state}").mkdir()

    for state in ("low", "high"):
        (input_dir / f"disort-{state}.inp").write_text(render_disort_input(data_dir, repository_root, profile_paths[state]))
        (input_dir / f"mystic-{state}.inp").write_text(render_mystic_input(data_dir, repository_root, profile_paths[state], run_root / f"mystic-{state}"))

    if synthetic_density_shape(heights, "low") == synthetic_density_shape(heights, "high"):
        raise CapabilityInputError("synthetic low/high profiles must differ")

    meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FROZEN_FOUR_SPECIES_SYNTHETIC_CAPABILITY_INPUTS_NO_SCIENTIFIC_INTERPRETATION",
        "species": list(SPECIES),
        "continentalAverageSourceEvidence": source_evidence,
        "resolverAliases": aliases,
        "profileMassWeights": PROFILE_MASS_WEIGHTS,
        "profileWeightInterpretation": "equal positive synthetic mass weights chosen only to force all four resolver dependencies through both solvers; not continental_average composition and not a scientific state",
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
        "levelBInferenceAuthorized": False,
        "humidityInterpretationAuthorized": False,
        "files": {},
    }
    for path in sorted(p for p in output_root.rglob("*") if p.is_file()):
        meta["files"][str(path.relative_to(output_root))] = sha256_file(path)
    (output_root / "input-manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atmosphere", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--repository-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(write_bundle(args.atmosphere, args.data_dir, args.repository_root, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
