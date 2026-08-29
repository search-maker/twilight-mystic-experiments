from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

STAGE_ID = "avps-four-species-renderer-validation-v1"
SPECIES = ("INSO", "WASO", "SOOT", "SUSO")
EXPECTED_CONTINENTAL_SHA256 = "fc39fda0f8ada2d0a0a872b8b62d684cfccd74f7b0655b5af2dcdec51115e469"
EXPECTED_TEMPLATE_BLOB = "8e8175ae771438b91fc9543b329175c193a215a4"
EXPECTED_PROFILE_STATES = (
    "opac-profile-continental-average",
    "opac-profile-maritime-clean",
    "opac-profile-desert",
    "opac-profile-arctic",
    "opac-profile-antarctic",
)
EXPECTED_LAYER_COUNT = 49
TARGET_AOD_LEVELS = (0.10, 0.30)
AOD_SUM_ABS_TOL = 2.1e-6
ROW_SUM_VS_SUM_LINE_TOL = 7.0e-5
BASELINE_SHAPE_MAX_ABS_TOL = 6.0e-5
BASELINE_SHAPE_L1_TOL = 1.5e-3
TARGET_SHAPE_MAX_ABS_TOL = 6.0e-5
TARGET_SHAPE_L1_TOL = 1.5e-3


class RendererError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RendererError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_standard_mixture(path: Path) -> list[tuple[float, tuple[float, float, float, float]]]:
    if not path.is_file() or sha256_file(path) != EXPECTED_CONTINENTAL_SHA256:
        raise RendererError("continental_average.dat identity drift")
    rows = []
    for line_no, raw in enumerate(path.read_text(errors="strict").splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) != 5:
            raise RendererError(f"unexpected continental_average row {line_no}: {raw!r}")
        try:
            vals = tuple(float(v) for v in parts)
        except ValueError as exc:
            raise RendererError(f"nonnumeric continental_average row {line_no}") from exc
        z = vals[0]
        mix = vals[1:]
        if not math.isfinite(z) or any((not math.isfinite(v)) or v < 0 for v in mix):
            raise RendererError(f"invalid continental_average row {line_no}")
        rows.append((z, mix))
    if len(rows) != 14:
        raise RendererError(f"continental_average numeric row-count drift: {len(rows)}")
    if not all(rows[i][0] > rows[i + 1][0] for i in range(len(rows) - 1)):
        raise RendererError("continental_average altitude order drift")
    if rows[0][0] != 35.0 or rows[-1][0] != 0.0:
        raise RendererError("continental_average altitude boundary drift")
    return rows


def lower_bound_standard_vector(
    z_km: float,
    source_rows_desc: list[tuple[float, tuple[float, float, float, float]]],
) -> tuple[float, float, float, float]:
    if z_km >= 35.0:
        return (0.0, 0.0, 0.0, 0.0)
    candidates = [row for row in source_rows_desc if row[0] <= z_km]
    if not candidates:
        raise RendererError(f"no standard-mixture lower-bound row for z={z_km}")
    z_src, vec = max(candidates, key=lambda row: row[0])
    if z_src >= 35.0:
        return (0.0, 0.0, 0.0, 0.0)
    if math.fsum(vec) <= 0:
        raise RendererError(f"nonpositive standard-mixture vector below 35 km at z={z_km}")
    return vec


def expand_standard_to_afgl(
    altitudes_desc: tuple[float, ...],
    source_rows_desc: list[tuple[float, tuple[float, float, float, float]]],
) -> dict[float, tuple[float, float, float, float]]:
    if len(altitudes_desc) != 50 or not all(a > b for a, b in zip(altitudes_desc, altitudes_desc[1:])):
        raise RendererError("AFGL altitude grid drift")
    if altitudes_desc[-1] != 0.0 or 35.0 not in altitudes_desc:
        raise RendererError("AFGL sea-level/35-km boundary drift")
    return {z: lower_bound_standard_vector(z, source_rows_desc) for z in altitudes_desc}


def render_species_profile(
    altitudes_desc: tuple[float, ...],
    vectors: dict[float, tuple[float, float, float, float]],
    header: str,
) -> str:
    lines = [f"# {header}", "# z_km INSO WASO SOOT SUSO; mass concentrations g/m^3"]
    for z in altitudes_desc:
        vec = vectors[z]
        if len(vec) != 4 or any((not math.isfinite(v)) or v < 0 for v in vec):
            raise RendererError(f"invalid rendered vector at z={z}")
        lines.append(f"{z:.6f} " + " ".join(f"{v:.17e}" for v in vec))
    return "\n".join(lines) + "\n"


def render_null_input(data_dir: Path, repo_root: Path, profile: str | Path, target_aod550: float) -> str:
    if target_aod550 not in TARGET_AOD_LEVELS:
        raise RendererError("renderer validation AOD outside frozen pair")
    grid = (repo_root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat").resolve()
    if not grid.is_file():
        raise RendererError(f"frozen wavelength grid missing: {grid}")
    if isinstance(profile, Path):
        species_line = f"aerosol_species_file {profile.resolve()} {' '.join(SPECIES)}"
    else:
        if profile != "continental_average":
            raise RendererError("unknown built-in aerosol species file")
        species_line = "aerosol_species_file continental_average"
    return "\n".join([
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "mol_abs_param crs",
        f"wavelength_grid_file {grid}",
        "wavelength 550 550",
        "sza 80",
        "albedo 0.15",
        "rte_solver null",
        "aerosol_default",
        "aerosol_species_library OPAC",
        species_line,
        f"aerosol_set_tau_at_wvl 550 {target_aod550:.6f}",
        "zout atm_levels",
        "output_user zout rh",
        "verbose",
    ]) + "\n"


def parse_optical_properties(stderr_path: Path) -> dict[str, Any]:
    text = stderr_path.read_text(errors="strict")
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "*** optical_properties()")
    except StopIteration as exc:
        raise RendererError(f"optical_properties table missing: {stderr_path}") from exc
    rows: list[dict[str, float | int]] = []
    sum_row = None
    for raw in lines[start + 1:]:
        stripped = raw.strip()
        if stripped.startswith("*** last solver call"):
            break
        if "|" not in raw:
            continue
        parts = raw.split("|")
        if len(parts) < 7:
            continue
        lead = parts[0].strip()
        aerosol_tokens = parts[3].split()
        if len(aerosol_tokens) < 2:
            continue
        if re.fullmatch(r"\d+", lead):
            lc = int(lead)
            try:
                z = float(parts[1].strip())
                scatter = float(aerosol_tokens[0])
                absorption = float(aerosol_tokens[1])
            except ValueError as exc:
                raise RendererError(f"cannot parse optical row: {raw!r}") from exc
            tau = scatter + absorption
            if not all(math.isfinite(v) for v in (z, scatter, absorption, tau)) or scatter < 0 or absorption < 0:
                raise RendererError(f"invalid optical row: {raw!r}")
            rows.append({"layerIndex": lc, "altitudeKm": z, "aerosolTau": tau})
        elif lead == "sum":
            try:
                scatter = float(aerosol_tokens[0])
                absorption = float(aerosol_tokens[1])
            except ValueError as exc:
                raise RendererError(f"cannot parse optical sum row: {raw!r}") from exc
            sum_row = {"aerosolTau": scatter + absorption}
    if len(rows) != EXPECTED_LAYER_COUNT or [r["layerIndex"] for r in rows] != list(range(EXPECTED_LAYER_COUNT)):
        raise RendererError(f"optical row cardinality/index drift: {len(rows)}")
    altitudes = [float(r["altitudeKm"]) for r in rows]
    if not all(a > b for a, b in zip(altitudes, altitudes[1:])) or altitudes[-1] != 0.0:
        raise RendererError("optical altitude ordering drift")
    if sum_row is None:
        raise RendererError("optical sum row missing")
    row_total = math.fsum(float(r["aerosolTau"]) for r in rows)
    if abs(row_total - float(sum_row["aerosolTau"])) > ROW_SUM_VS_SUM_LINE_TOL:
        raise RendererError("optical row sum disagrees with sum line")
    if row_total <= 0:
        raise RendererError("nonpositive aerosol optical depth")
    fractions = [float(r["aerosolTau"]) / row_total for r in rows]
    return {
        "stderrSha256": sha256_file(stderr_path),
        "layerCount": len(rows),
        "rows": rows,
        "rowTotalAerosolTau": row_total,
        "sumLineAerosolTau": float(sum_row["aerosolTau"]),
        "normalizedLayerTauFractions": fractions,
    }


def compare_fraction_vectors(a: list[float], b: list[float], max_tol: float, l1_tol: float, label: str) -> dict[str, Any]:
    if len(a) != len(b):
        raise RendererError(f"{label}: fraction vector length mismatch")
    diffs = [abs(float(x) - float(y)) for x, y in zip(a, b)]
    max_abs = max(diffs)
    l1 = math.fsum(diffs)
    if max_abs > max_tol or l1 > l1_tol:
        raise RendererError(f"{label}: shape mismatch max={max_abs} l1={l1}")
    return {"label": label, "maxAbsFractionDifference": max_abs, "l1FractionDifference": l1, "pass": True}


def prepare(archive: Path, runtime_root: Path, repo_root: Path, output: Path, dependency_path: Path) -> dict[str, Any]:
    dep = _load_module("rh_audit_dependency", dependency_path)
    archive_meta = dep.extract_frozen_archive(archive, runtime_root / "share" / "libRadtran")
    data_dir = runtime_root / "share" / "libRadtran" / "data"
    aliases = dep.prepare_no_extension_aliases(data_dir)
    altitudes = dep.parse_afgl_altitudes(data_dir / "atmmod" / "afglus.dat")
    continental = data_dir / "aerosol" / "OPAC" / "standard_aerosol_files" / "continental_average.dat"
    source_rows = parse_standard_mixture(continental)
    expanded = expand_standard_to_afgl(altitudes, source_rows)
    output.mkdir(parents=True, exist_ok=False)
    profiles = output / "profiles"
    inputs = output / "inputs"
    profiles.mkdir(); inputs.mkdir()
    expanded_path = profiles / "expanded-standard-four-species.dat"
    expanded_path.write_text(render_species_profile(altitudes, expanded, f"{STAGE_ID} expanded standard control"))
    (inputs / "baseline-builtin-aod010.inp").write_text(render_null_input(data_dir, repo_root, "continental_average", 0.10))
    (inputs / "baseline-expanded-aod010.inp").write_text(render_null_input(data_dir, repo_root, expanded_path, 0.10))
    meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PREPARED_BASELINE_LOWER_BOUND_SEMANTICS_CHECK",
        "archive": archive_meta,
        "resolverAliases": aliases,
        "afglSha256": dep.EXPECTED_AFGL_SHA256,
        "continentalAverageSha256": EXPECTED_CONTINENTAL_SHA256,
        "atmosphereAltitudesKm": list(altitudes),
        "species": list(SPECIES),
        "expandedStandardProfileSha256": sha256_file(expanded_path),
        "scientificOrdinalAllocated": False,
        "scientificRadiativeTransferSolved": False,
        "taylorOrJerusalemUsed": False,
    }
    (output / "prepare-manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def render_states(bundle: Path, repo_root: Path, data_dir: Path) -> dict[str, Any]:
    manifest = json.loads((bundle / "prepare-manifest.json").read_text())
    altitudes = tuple(float(v) for v in manifest["atmosphereAltitudesKm"])
    source_rows = parse_standard_mixture(data_dir / "aerosol" / "OPAC" / "standard_aerosol_files" / "continental_average.dat")
    expanded = expand_standard_to_afgl(altitudes, source_rows)
    builtin = parse_optical_properties(bundle / "baseline-builtin-aod010.verbose.err")
    explicit = parse_optical_properties(bundle / "baseline-expanded-aod010.verbose.err")
    if [r["altitudeKm"] for r in builtin["rows"]] != [r["altitudeKm"] for r in explicit["rows"]]:
        raise RendererError("baseline built-in/expanded altitude grids differ")
    baseline_check = compare_fraction_vectors(
        builtin["normalizedLayerTauFractions"], explicit["normalizedLayerTauFractions"],
        BASELINE_SHAPE_MAX_ABS_TOL, BASELINE_SHAPE_L1_TOL, "builtin-vs-expanded-standard"
    )
    if abs(float(builtin["sumLineAerosolTau"]) - 0.10) > AOD_SUM_ABS_TOL or abs(float(explicit["sumLineAerosolTau"]) - 0.10) > AOD_SUM_ABS_TOL:
        raise RendererError("baseline AOD normalization drift")

    template_path = repo_root / "experiments" / "aerosol-vertical-profile-sensitivity-v1" / "opac_vertical_templates.py"
    if git_blob_sha(template_path) != EXPECTED_TEMPLATE_BLOB:
        raise RendererError("frozen AVPS template generator blob drift")
    templates = _load_module("frozen_avps_templates", template_path)
    states = tuple(templates.PROFILE_STATES.keys())
    if states != EXPECTED_PROFILE_STATES:
        raise RendererError(f"frozen AVPS state order/set drift: {states}")
    edges_asc = tuple(reversed(altitudes))
    row_lower_desc = [float(r["altitudeKm"]) for r in explicit["rows"]]
    if row_lower_desc != list(altitudes[1:]):
        raise RendererError("NULL optical rows are not exact AFGL lower layer boundaries")
    baseline_fracs = [float(v) for v in explicit["normalizedLayerTauFractions"]]
    profile_dir = bundle / "profiles"
    input_dir = bundle / "inputs"
    state_meta = {}
    for state in states:
        target_asc = list(templates.layer_tau_fractions(edges_asc, state))
        if len(target_asc) != EXPECTED_LAYER_COUNT:
            raise RendererError("target template layer count drift")
        target_desc = list(reversed(target_asc))
        if abs(math.fsum(target_desc) - 1.0) > 1e-12 or any(v < 0 for v in target_desc):
            raise RendererError(f"invalid target fractions for {state}")
        scales_by_z: dict[float, float] = {}
        vectors: dict[float, tuple[float, float, float, float]] = {altitudes[0]: (0.0, 0.0, 0.0, 0.0)}
        for z, base_frac, target_frac in zip(row_lower_desc, baseline_fracs, target_desc):
            base_vec = expanded[z]
            if target_frac <= 1e-18:
                scale = 0.0
            else:
                if base_frac <= 0:
                    raise RendererError(f"positive target has zero standard baseline support: {state} z={z}")
                scale = target_frac / base_frac
            if not math.isfinite(scale) or scale < 0:
                raise RendererError(f"invalid common scalar: {state} z={z}: {scale}")
            scales_by_z[z] = scale
            vectors[z] = tuple(scale * v for v in base_vec)
        profile_path = profile_dir / f"{state}.four-species.dat"
        profile_path.write_text(render_species_profile(altitudes, vectors, f"{STAGE_ID} {state}; common-scalar standard-mixture renderer"))
        for aod in TARGET_AOD_LEVELS:
            tag = "010" if aod == 0.10 else "030"
            (input_dir / f"{state}-aod{tag}.inp").write_text(render_null_input(data_dir, repo_root, profile_path, aod))
        state_meta[state] = {
            "targetFractionsDescending": target_desc,
            "scaleByLowerBoundaryKm": {f"{z:.6f}": scales_by_z[z] for z in row_lower_desc},
            "profileSha256": sha256_file(profile_path),
            "minScale": min(scales_by_z.values()),
            "maxScale": max(scales_by_z.values()),
        }
    out = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "FIVE_COMMON_SCALAR_FOUR_SPECIES_PROFILES_RENDERED_PENDING_NULL_VALIDATION",
        "baselineSemanticsCheck": baseline_check,
        "templateGeneratorGitBlob": EXPECTED_TEMPLATE_BLOB,
        "states": state_meta,
        "scientificOrdinalAllocated": False,
        "scientificRadiativeTransferSolved": False,
        "taylorOrJerusalemUsed": False,
    }
    (bundle / "render-manifest.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def freeze(bundle: Path) -> dict[str, Any]:
    render_meta = json.loads((bundle / "render-manifest.json").read_text())
    validations = {}
    for state in EXPECTED_PROFILE_STATES:
        target = [float(v) for v in render_meta["states"][state]["targetFractionsDescending"]]
        a010 = parse_optical_properties(bundle / f"{state}-aod010.verbose.err")
        a030 = parse_optical_properties(bundle / f"{state}-aod030.verbose.err")
        for label, parsed, want in (("aod010", a010, 0.10), ("aod030", a030, 0.30)):
            if abs(float(parsed["sumLineAerosolTau"]) - want) > AOD_SUM_ABS_TOL:
                raise RendererError(f"{state} {label}: AOD normalization drift")
        target010 = compare_fraction_vectors(a010["normalizedLayerTauFractions"], target, TARGET_SHAPE_MAX_ABS_TOL, TARGET_SHAPE_L1_TOL, f"{state}-aod010-vs-target")
        target030 = compare_fraction_vectors(a030["normalizedLayerTauFractions"], target, TARGET_SHAPE_MAX_ABS_TOL, TARGET_SHAPE_L1_TOL, f"{state}-aod030-vs-target")
        rescale = compare_fraction_vectors(a010["normalizedLayerTauFractions"], a030["normalizedLayerTauFractions"], TARGET_SHAPE_MAX_ABS_TOL, TARGET_SHAPE_L1_TOL, f"{state}-aod010-vs-aod030")
        validations[state] = {"aod010": a010, "aod030": a030, "target010": target010, "target030": target030, "aodRescaleShape": rescale}
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PASS_FIVE_FROZEN_AVPS_TEMPLATES_RENDERED_AS_COMMON_SCALAR_FOUR_SPECIES_NULL_TAU_SHAPES",
        "baselineSemanticsCheck": render_meta["baselineSemanticsCheck"],
        "states": validations,
        "representation": "At each AFGL lower layer boundary, all INSO/WASO/SOOT/SUSO mass concentrations are one common nonnegative scalar multiple of the locked continental_average layer vector; no aerosol_file tau is used; aerosol_set_tau_at_wvl performs only column normalization.",
        "rteSolver": "null",
        "scientificRadiativeTransferSolved": False,
        "mysticExecuted": False,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "scientificExecutionAuthorized": False,
        "interpretationBoundary": "PASS validates the corrected renderer representation against the actual runtime 550-nm layer-tau table for the five already-frozen independent AVPS templates. It does not quantify twilight effect size and does not allocate/authorize ordinal 41.",
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["contentSha256"] = hashlib.sha256(canonical).hexdigest()
    (bundle / "renderer-validation-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--runtime-root", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--dependency", type=Path, required=True)
    r = sub.add_parser("render")
    r.add_argument("--bundle", type=Path, required=True)
    r.add_argument("--repo-root", type=Path, required=True)
    r.add_argument("--data-dir", type=Path, required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--bundle", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "prepare":
        print(json.dumps(prepare(args.archive, args.runtime_root, args.repo_root, args.output, args.dependency), sort_keys=True))
    elif args.cmd == "render":
        print(json.dumps(render_states(args.bundle, args.repo_root, args.data_dir), sort_keys=True))
    else:
        print(json.dumps(freeze(args.bundle), sort_keys=True))


if __name__ == "__main__":
    main()
