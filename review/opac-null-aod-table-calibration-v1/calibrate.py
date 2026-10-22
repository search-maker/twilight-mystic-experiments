from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any

STAGE_ID = "opac-null-aod-table-calibration-v1"
TARGET_SUM_ABS_TOL = 2.1e-6
ROW_SUM_VS_SUM_LINE_TOL = 7.0e-5
SHAPE_MAX_ABS_TOL = 6.0e-5
SHAPE_L1_TOL = 1.5e-3
EXPECTED_LAYER_COUNT = 49


class CalibrationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _load_dependency(path: Path):
    spec = importlib.util.spec_from_file_location("rh_audit_dependency", path)
    if spec is None or spec.loader is None:
        raise CalibrationError(f"cannot load dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_input(data_dir: Path, repo_root: Path, target_aod550: float | None) -> str:
    grid = (repo_root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat").resolve()
    if not grid.is_file():
        raise CalibrationError(f"frozen wavelength grid missing: {grid}")
    lines = [
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
        "aerosol_species_file continental_average",
    ]
    if target_aod550 is not None:
        if not math.isfinite(target_aod550) or target_aod550 <= 0:
            raise CalibrationError("target AOD550 must be finite and positive")
        lines.append(f"aerosol_set_tau_at_wvl 550 {target_aod550:.6f}")
    lines.extend(["zout atm_levels", "output_user zout rh", "verbose"])
    return "\n".join(lines) + "\n"


def prepare_inputs(archive: Path, runtime_root: Path, repo_root: Path, output: Path, dependency_path: Path) -> dict[str, Any]:
    dep = _load_dependency(dependency_path)
    archive_meta = dep.extract_frozen_archive(archive, runtime_root / "share" / "libRadtran")
    data_dir = runtime_root / "share" / "libRadtran" / "data"
    aliases = dep.prepare_no_extension_aliases(data_dir)
    altitudes = dep.parse_afgl_altitudes(data_dir / "atmmod" / "afglus.dat")
    continental = data_dir / "aerosol" / "OPAC" / "standard_aerosol_files" / "continental_average.dat"
    if not continental.is_file() or sha256_file(continental) != dep.EXPECTED_CONTINENTAL_SHA256:
        raise CalibrationError("continental_average source drift")
    output.mkdir(parents=True, exist_ok=False)
    cases = {"baseline": None, "aod010": 0.10, "aod030": 0.30}
    for name, target in cases.items():
        (output / f"{name}.inp").write_text(render_input(data_dir, repo_root, target))
    meta = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "NULL_AOD_TABLE_CALIBRATION_INPUTS_FROZEN",
        "archive": archive_meta,
        "resolverAliases": aliases,
        "afglSha256": dep.EXPECTED_AFGL_SHA256,
        "continentalAverageSha256": dep.EXPECTED_CONTINENTAL_SHA256,
        "atmosphereAltitudesKm": list(altitudes),
        "cases": {k: {"targetAod550": v} for k, v in cases.items()},
        "rteSolver": "null",
        "wavelengthNm": 550.0,
        "tolerances": {
            "targetSumAbs": TARGET_SUM_ABS_TOL,
            "rowSumVsSumLine": ROW_SUM_VS_SUM_LINE_TOL,
            "shapeMaxAbs": SHAPE_MAX_ABS_TOL,
            "shapeL1": SHAPE_L1_TOL,
        },
        "scientificRadiativeTransferSolved": False,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
    }
    (output / "input-manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def parse_optical_properties(stderr_path: Path) -> dict[str, Any]:
    text = stderr_path.read_text(errors="strict")
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "*** optical_properties()")
    except StopIteration as exc:
        raise CalibrationError(f"optical_properties table missing: {stderr_path}") from exc
    rows: list[dict[str, float | int]] = []
    sum_row: dict[str, float] | None = None
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
            try:
                lc = int(lead)
                z = float(parts[1].strip())
                scatter = float(aerosol_tokens[0])
                absorption = float(aerosol_tokens[1])
            except ValueError as exc:
                raise CalibrationError(f"cannot parse optical row: {raw!r}") from exc
            tau = scatter + absorption
            if not all(math.isfinite(v) for v in (z, scatter, absorption, tau)) or scatter < 0 or absorption < 0:
                raise CalibrationError(f"invalid optical row: {raw!r}")
            rows.append({"layerIndex": lc, "altitudeKm": z, "scatterTau": scatter, "absorptionTau": absorption, "aerosolTau": tau})
        elif lead == "sum":
            try:
                scatter = float(aerosol_tokens[0])
                absorption = float(aerosol_tokens[1])
            except ValueError as exc:
                raise CalibrationError(f"cannot parse optical sum row: {raw!r}") from exc
            sum_row = {"scatterTau": scatter, "absorptionTau": absorption, "aerosolTau": scatter + absorption}
    if len(rows) != EXPECTED_LAYER_COUNT:
        raise CalibrationError(f"expected {EXPECTED_LAYER_COUNT} aerosol optical rows, found {len(rows)}")
    if [r["layerIndex"] for r in rows] != list(range(EXPECTED_LAYER_COUNT)):
        raise CalibrationError("optical layer indices drift")
    altitudes = [float(r["altitudeKm"]) for r in rows]
    if not all(a > b for a, b in zip(altitudes, altitudes[1:])) or altitudes[-1] != 0.0:
        raise CalibrationError("optical table altitude ordering drift")
    if sum_row is None:
        raise CalibrationError("optical sum row missing")
    row_total = math.fsum(float(r["aerosolTau"]) for r in rows)
    if abs(row_total - sum_row["aerosolTau"]) > ROW_SUM_VS_SUM_LINE_TOL:
        raise CalibrationError(f"layer aerosol tau sum disagrees with table sum line: rows={row_total} sum={sum_row['aerosolTau']}")
    if row_total <= 0 or sum_row["aerosolTau"] <= 0:
        raise CalibrationError("nonpositive aerosol optical depth")
    normalized = [float(r["aerosolTau"]) / row_total for r in rows]
    if abs(math.fsum(normalized) - 1.0) > 2e-12:
        raise CalibrationError("normalized aerosol optical rows do not sum to one")
    return {
        "stderrSha256": sha256_file(stderr_path),
        "verboseLineCount": len(lines),
        "layerCount": len(rows),
        "rows": rows,
        "rowTotalAerosolTau": row_total,
        "sumLine": sum_row,
        "normalizedLayerTauFractions": normalized,
    }


def compare_shapes(a: dict[str, Any], b: dict[str, Any], label: str) -> dict[str, Any]:
    za = [r["altitudeKm"] for r in a["rows"]]
    zb = [r["altitudeKm"] for r in b["rows"]]
    if za != zb:
        raise CalibrationError(f"{label}: optical altitude grids differ")
    fa = a["normalizedLayerTauFractions"]
    fb = b["normalizedLayerTauFractions"]
    diffs = [abs(float(x) - float(y)) for x, y in zip(fa, fb)]
    max_abs = max(diffs)
    l1 = math.fsum(diffs)
    if max_abs > SHAPE_MAX_ABS_TOL or l1 > SHAPE_L1_TOL:
        raise CalibrationError(f"{label}: normalized shape changed under AOD rescale: max={max_abs} l1={l1}")
    return {"label": label, "maxAbsFractionDifference": max_abs, "l1FractionDifference": l1, "pass": True}


def freeze_report(evidence: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    parsed = {name: parse_optical_properties(evidence / f"{name}.verbose.err") for name in ("baseline", "aod010", "aod030")}
    for name, target in (("aod010", 0.10), ("aod030", 0.30)):
        got = float(parsed[name]["sumLine"]["aerosolTau"])
        if abs(got - target) > TARGET_SUM_ABS_TOL:
            raise CalibrationError(f"{name}: verbose aerosol scatter+abs sum does not reproduce requested AOD550: {got} vs {target}")
    shape_checks = [
        compare_shapes(parsed["baseline"], parsed["aod010"], "baseline-vs-aod010"),
        compare_shapes(parsed["baseline"], parsed["aod030"], "baseline-vs-aod030"),
        compare_shapes(parsed["aod010"], parsed["aod030"], "aod010-vs-aod030"),
    ]
    ratio = float(parsed["aod030"]["sumLine"]["aerosolTau"]) / float(parsed["aod010"]["sumLine"]["aerosolTau"])
    if abs(ratio - 3.0) > 1e-4:
        raise CalibrationError(f"AOD 0.30/0.10 scaling ratio drift: {ratio}")
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "PASS_VERBOSE_AEROSOL_SCATTER_PLUS_ABS_IS_LAYER_TAU_AND_AOD_RESCALE_PRESERVES_SHAPE",
        "rteSolver": "null",
        "wavelengthNm": 550.0,
        "calibrationMeaning": "At 550 nm, the aerosol scatter+abs columns printed by libRadtran optical_properties() are calibrated as layer aerosol optical depth because their aggregate reproduces aerosol_set_tau_at_wvl targets 0.10 and 0.30 while normalized layer shape is invariant under the column rescale.",
        "cases": parsed,
        "shapeChecks": shape_checks,
        "aod030To010Ratio": ratio,
        "tolerances": manifest["tolerances"],
        "scientificRadiativeTransferSolved": False,
        "mysticExecuted": False,
        "scientificOrdinalAllocated": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "rendererAuthorized": False,
        "interpretationBoundary": "This calibrates the NULL verbose aerosol optical-depth table and column rescale only. It does not yet validate a custom mass-profile renderer against any AVPS target template.",
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["contentSha256"] = hashlib.sha256(canonical).hexdigest()
    (evidence / "calibration-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
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
    f = sub.add_parser("freeze")
    f.add_argument("--evidence", type=Path, required=True)
    f.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "prepare":
        print(json.dumps(prepare_inputs(args.archive, args.runtime_root, args.repo_root, args.output, args.dependency), sort_keys=True))
    else:
        manifest = json.loads(args.manifest.read_text())
        print(json.dumps(freeze_report(args.evidence, manifest), sort_keys=True))


if __name__ == "__main__":
    main()
