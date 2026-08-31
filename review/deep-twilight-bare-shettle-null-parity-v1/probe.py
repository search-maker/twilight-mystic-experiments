from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

STAGE_ID = "deep-twilight-bare-shettle-null-parity-v1"
WAVELENGTHS_NM = (380, 550, 780)
SCALE_FACTORS = (1, 100, 10000)
BASE_AOD550 = 0.15
EXPECTED_LAYER_COUNT = 49
TAU_PRINT_HALF_QUANTUM = 0.5e-6
G_PRINT_HALF_QUANTUM = 0.5e-3
ROW_SUM_VS_SUM_LINE_TOL = 7.0e-5
TARGET_SUM_ABS_TOL = 2.1e-6


class CapabilityError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def case_name(wavelength_nm: int, scale: int) -> str:
    return f"w{wavelength_nm}-f{scale}"


def render_input(data_dir: Path, repo_root: Path, wavelength_nm: int, scale: int) -> str:
    if wavelength_nm not in WAVELENGTHS_NM or scale not in SCALE_FACTORS:
        raise CapabilityError("case outside frozen matrix")
    grid = (repo_root / "experiments/aerosol-family-challenge-v2-r8/wavelength-grid-1nm.dat").resolve()
    if not grid.is_file():
        raise CapabilityError(f"frozen wavelength grid missing: {grid}")
    target_aod = BASE_AOD550 * scale
    lines = [
        f"data_files_path {data_dir.resolve()}",
        f"atmosphere_file {(data_dir / 'atmmod/afglus.dat').resolve()}",
        f"source solar {(data_dir / 'solar_flux/atlas_plus_modtran').resolve()}",
        "mol_abs_param crs",
        f"wavelength_grid_file {grid}",
        f"wavelength {wavelength_nm} {wavelength_nm}",
        "sza 80",
        "albedo 0.15",
        "rte_solver null",
        "aerosol_default",
        f"aerosol_set_tau_at_wvl 550 {target_aod:.6f}",
        "zout atm_levels",
        "output_user zout rh",
        "verbose",
    ]
    return "\n".join(lines) + "\n"


def prepare(data_dir: Path, repo_root: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    cases: list[dict[str, Any]] = []
    for wavelength_nm in WAVELENGTHS_NM:
        for scale in SCALE_FACTORS:
            name = case_name(wavelength_nm, scale)
            text = render_input(data_dir, repo_root, wavelength_nm, scale)
            path = output / f"{name}.inp"
            path.write_text(text)
            cases.append({
                "caseId": name,
                "wavelengthNm": wavelength_nm,
                "aodScaleFactor": scale,
                "requestedAod550": BASE_AOD550 * scale,
                "inputSha256": hashlib.sha256(text.encode()).hexdigest(),
            })
    manifest = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": "BARE_SHETTLE_NULL_PARITY_INPUTS_FROZEN",
        "atmosphere": "AFGL-US",
        "aerosol": "bare libRadtran aerosol_default; no OPAC/species override",
        "baseAod550": BASE_AOD550,
        "wavelengthsNm": list(WAVELENGTHS_NM),
        "aodScaleFactors": list(SCALE_FACTORS),
        "rteSolver": "null",
        "tauPrintedDecimals": 6,
        "gPrintedDecimals": 3,
        "tauPrintHalfQuantum": TAU_PRINT_HALF_QUANTUM,
        "gPrintHalfQuantum": G_PRINT_HALF_QUANTUM,
        "cases": cases,
        "scientificRadiativeTransferSolved": False,
        "mysticExecuted": False,
        "scientificOrdinalAllocated": False,
        "deepRadianceOpened": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
    }
    (output / "input-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def _interval(value: float, half_quantum: float, lower_bound: float = 0.0, upper_bound: float | None = None) -> tuple[float, float]:
    lo = max(lower_bound, value - half_quantum)
    hi = value + half_quantum
    if upper_bound is not None:
        hi = min(upper_bound, hi)
    if hi < lo:
        raise CapabilityError("invalid quantization interval")
    return lo, hi


def _sum_interval(scatter: float, absorption: float) -> tuple[float, float]:
    s = _interval(scatter, TAU_PRINT_HALF_QUANTUM)
    a = _interval(absorption, TAU_PRINT_HALF_QUANTUM)
    return s[0] + a[0], s[1] + a[1]


def _ssa_interval(scatter: float, absorption: float) -> tuple[float, float] | None:
    s_lo, s_hi = _interval(scatter, TAU_PRINT_HALF_QUANTUM)
    a_lo, a_hi = _interval(absorption, TAU_PRINT_HALF_QUANTUM)
    if s_lo + a_lo <= 0.0:
        return None
    lo_den = s_lo + a_hi
    hi_den = s_hi + a_lo
    lo = 0.0 if lo_den <= 0.0 else s_lo / lo_den
    hi = 1.0 if hi_den <= 0.0 else s_hi / hi_den
    return max(0.0, lo), min(1.0, hi)


def _intersection(intervals: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not intervals:
        return None
    lo = max(x[0] for x in intervals)
    hi = min(x[1] for x in intervals)
    return (lo, hi) if lo <= hi else None


def parse_optical_properties(stderr_path: Path) -> dict[str, Any]:
    text = stderr_path.read_text(errors="strict")
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "*** optical_properties()")
    except StopIteration as exc:
        raise CapabilityError(f"optical_properties table missing: {stderr_path}") from exc
    rows: list[dict[str, Any]] = []
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
        if len(aerosol_tokens) < 3:
            continue
        if re.fullmatch(r"\d+", lead):
            try:
                lc = int(lead)
                z = float(parts[1].strip())
                scatter = float(aerosol_tokens[0])
                absorption = float(aerosol_tokens[1])
                g = float(aerosol_tokens[2])
            except ValueError as exc:
                raise CapabilityError(f"cannot parse optical row: {raw!r}") from exc
            if not all(math.isfinite(v) for v in (z, scatter, absorption, g)):
                raise CapabilityError(f"nonfinite optical row: {raw!r}")
            if scatter < 0 or absorption < 0 or g < 0 or g > 1:
                raise CapabilityError(f"out-of-range optical row: {raw!r}")
            tau_lo, tau_hi = _sum_interval(scatter, absorption)
            ssa_interval = _ssa_interval(scatter, absorption)
            rows.append({
                "layerIndex": lc,
                "altitudeKm": z,
                "scatterTauPrinted": scatter,
                "absorptionTauPrinted": absorption,
                "gPrinted": g,
                "aerosolTauPrinted": scatter + absorption,
                "aerosolTauPrintInterval": [tau_lo, tau_hi],
                "ssaPrintInterval": list(ssa_interval) if ssa_interval else None,
                "gPrintInterval": list(_interval(g, G_PRINT_HALF_QUANTUM, 0.0, 1.0)),
            })
        elif lead == "sum":
            try:
                scatter = float(aerosol_tokens[0])
                absorption = float(aerosol_tokens[1])
            except ValueError as exc:
                raise CapabilityError(f"cannot parse optical sum row: {raw!r}") from exc
            if not all(math.isfinite(v) and v >= 0 for v in (scatter, absorption)):
                raise CapabilityError("invalid optical sum")
            sum_row = {"scatterTauPrinted": scatter, "absorptionTauPrinted": absorption, "aerosolTauPrinted": scatter + absorption}
    if len(rows) != EXPECTED_LAYER_COUNT:
        raise CapabilityError(f"expected {EXPECTED_LAYER_COUNT} optical rows, found {len(rows)}")
    if [r["layerIndex"] for r in rows] != list(range(EXPECTED_LAYER_COUNT)):
        raise CapabilityError("optical layer indices drift")
    altitudes = [float(r["altitudeKm"]) for r in rows]
    if not all(a > b for a, b in zip(altitudes, altitudes[1:])) or altitudes[-1] != 0.0:
        raise CapabilityError("optical altitude ordering drift")
    if sum_row is None:
        raise CapabilityError("optical sum row missing")
    row_total = math.fsum(float(r["aerosolTauPrinted"]) for r in rows)
    if abs(row_total - sum_row["aerosolTauPrinted"]) > ROW_SUM_VS_SUM_LINE_TOL:
        raise CapabilityError(f"row/sum aerosol tau disagreement: {row_total} vs {sum_row['aerosolTauPrinted']}")
    return {
        "stderrSha256": sha256_file(stderr_path),
        "verboseLineCount": len(lines),
        "layerCount": len(rows),
        "rows": rows,
        "rowTotalAerosolTauPrinted": row_total,
        "sumLine": sum_row,
    }


def _scaled_tau_interval(row: dict[str, Any], scale: int) -> tuple[float, float]:
    lo, hi = (float(v) for v in row["aerosolTauPrintInterval"])
    return lo / scale, hi / scale


def _resolved_ssa_interval(row: dict[str, Any]) -> tuple[float, float] | None:
    x = row["ssaPrintInterval"]
    return None if x is None else (float(x[0]), float(x[1]))


def compare_wavelength(cases: dict[int, dict[str, Any]], wavelength_nm: int) -> dict[str, Any]:
    altitude_grids = [[float(r["altitudeKm"]) for r in cases[s]["rows"]] for s in SCALE_FACTORS]
    if any(g != altitude_grids[0] for g in altitude_grids[1:]):
        raise CapabilityError(f"{wavelength_nm}: altitude grid changes with AOD scale")
    layer_checks: list[dict[str, Any]] = []
    unresolved_tau_layers: list[int] = []
    unresolved_ssa_layers: list[int] = []
    unresolved_g_layers: list[int] = []
    for i in range(EXPECTED_LAYER_COUNT):
        tau_intervals = [_scaled_tau_interval(cases[s]["rows"][i], s) for s in SCALE_FACTORS]
        tau_common = _intersection(tau_intervals)
        if tau_common is None:
            unresolved_tau_layers.append(i)
        resolved_scales = [s for s in SCALE_FACTORS if _scaled_tau_interval(cases[s]["rows"][i], s)[0] > 0.0]
        ssa_intervals = [x for s in resolved_scales if (x := _resolved_ssa_interval(cases[s]["rows"][i])) is not None]
        ssa_common = _intersection(ssa_intervals) if len(ssa_intervals) >= 2 else None
        if len(resolved_scales) >= 2 and ssa_common is None:
            unresolved_ssa_layers.append(i)
        g_intervals = [tuple(float(v) for v in cases[s]["rows"][i]["gPrintInterval"]) for s in resolved_scales]
        g_common = _intersection(g_intervals) if len(g_intervals) >= 2 else None
        if len(resolved_scales) >= 2 and g_common is None:
            unresolved_g_layers.append(i)
        layer_checks.append({
            "layerIndex": i,
            "altitudeKm": altitude_grids[0][i],
            "baseTauIntervalsByScale": {str(s): list(tau_intervals[j]) for j, s in enumerate(SCALE_FACTORS)},
            "baseTauCommonInterval": list(tau_common) if tau_common else None,
            "resolvedScalesForSsaAndG": resolved_scales,
            "ssaCommonInterval": list(ssa_common) if ssa_common else None,
            "gCommonInterval": list(g_common) if g_common else None,
        })
    return {
        "wavelengthNm": wavelength_nm,
        "layerChecks": layer_checks,
        "tauIntervalMismatchLayers": unresolved_tau_layers,
        "ssaIntervalMismatchLayers": unresolved_ssa_layers,
        "gIntervalMismatchLayers": unresolved_g_layers,
        "pass": not (unresolved_tau_layers or unresolved_ssa_layers or unresolved_g_layers),
    }


def freeze(evidence: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[int, dict[int, dict[str, Any]]] = {}
    for wavelength_nm in WAVELENGTHS_NM:
        parsed[wavelength_nm] = {}
        for scale in SCALE_FACTORS:
            parsed[wavelength_nm][scale] = parse_optical_properties(evidence / f"{case_name(wavelength_nm, scale)}.verbose.err")
    for scale in SCALE_FACTORS:
        target = BASE_AOD550 * scale
        got = float(parsed[550][scale]["sumLine"]["aerosolTauPrinted"])
        if abs(got - target) > TARGET_SUM_ABS_TOL:
            raise CapabilityError(f"550nm/F={scale}: requested AOD550 not reproduced: {got} vs {target}")
    wavelength_checks = [compare_wavelength(parsed[w], w) for w in WAVELENGTHS_NM]
    passed = all(x["pass"] for x in wavelength_checks)
    status = "PASS_BARE_SHETTLE_FIXED_AMPLIFICATION_PARITY" if passed else "AMPLIFICATION_PARITY_CAPABILITY_UNRESOLVED"
    report = {
        "schemaVersion": 1,
        "stageId": STAGE_ID,
        "status": status,
        "rteSolver": "null",
        "aerosol": "bare libRadtran aerosol_default",
        "wavelengthsNm": list(WAVELENGTHS_NM),
        "baseAod550": BASE_AOD550,
        "aodScaleFactors": list(SCALE_FACTORS),
        "quantizationSemantics": {
            "tauPrintedDecimals": 6,
            "tauHalfQuantum": TAU_PRINT_HALF_QUANTUM,
            "gPrintedDecimals": 3,
            "gHalfQuantum": G_PRINT_HALF_QUANTUM,
            "printedZeroMeaning": "censored interval/upper bound, never physical zero",
        },
        "cases": {case_name(w, s): parsed[w][s] for w in WAVELENGTHS_NM for s in SCALE_FACTORS},
        "wavelengthChecks": wavelength_checks,
        "scientificRadiativeTransferSolved": False,
        "mysticExecuted": False,
        "scientificOrdinalAllocated": False,
        "deepRadianceOpened": False,
        "rendererAuthorized": False,
        "eradiateRadianceAuthorized": False,
        "levelBV1Changed": False,
        "taylorOrJerusalemUsed": False,
        "productionAuthorized": False,
        "interpretationBoundary": "This is a zero-radiance capability gate for extracting bare aerosol_default layer optical properties through fixed AOD amplification. PASS establishes print-resolution/scaling consistency only; it does not validate Eradiate, deep-twilight radiance, a rare-event estimator, or any support extension.",
        "nextOnFailure": "Do not add/adapt amplification scales. Use only the separately preregistered tiny post-redistribution diagnostic serializer path.",
        "nextOnPass": "Translate the bounded layerwise tau/SSA/g evidence into an Eradiate optical-property parity object, then run the separately preregistered shallow spherical benchmark before any deep radiance.",
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["contentSha256"] = hashlib.sha256(canonical).hexdigest()
    (evidence / "parity-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--evidence", type=Path, required=True)
    f.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "prepare":
        print(json.dumps(prepare(args.data_dir, args.repo_root, args.output), sort_keys=True))
    else:
        manifest = json.loads(args.manifest.read_text())
        print(json.dumps(freeze(args.evidence, manifest), sort_keys=True))


if __name__ == "__main__":
    main()
